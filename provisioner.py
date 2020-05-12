# -*- coding: utf-8 -*-
"""Provisioner module file"""

import copy
import os
import uuid
from pathlib import Path
from subprocess import Popen
from codenamize import codenamize
from jinja2 import Environment, FileSystemLoader
from yaml import load, Loader

OPENSSL_CMD = "/usr/bin/openssl"

class Provisioner:
    """Class responsible for doing the heavy lifting of the provisioning process."""
    def __init__(self, out_folder, config_data, scheme_file, csv_log_writer, password, template_folder="./templates"):
        self.out_folder = out_folder
        self.config_data = config_data
        self.scheme_file = scheme_file
        self.csv_log_writer = csv_log_writer
        self.scheme = load(open(scheme_file, "r"), Loader=Loader)
        self._log(f"Loaded scheme: {self.scheme}")
        self.data = self._load_data()
        self.password = password
        self.template_env = Environment(
            loader=FileSystemLoader(template_folder),
            lstrip_blocks=True,
            trim_blocks=True,
            keep_trailing_newline=True)

    def process(self):
        """Execute the provisioning process"""
        for key, item in self.scheme.items():
            self._log(f"Processing {key} spec")
            if "templates" in item:
                self._process_templates(item["templates"])
            if "ssl_cert" in item:
                self._process_cert(item["ssl_cert"])
            if "rm" in item:
                self._process_rm(item["rm"])

        return self.data

    @classmethod
    def _log(cls, msg):
        print(msg)

    def _load_data(self):
        data = {}
        data["config"] = self.config_data
        data["unique_id"] = str(uuid.uuid4())
        data["host"] = {}
        data["host"]["hostname"] = codenamize(data['unique_id'], adjectives=2, max_item_chars=0, join='-',
                                              hash_algo="sha3_512")
        data["api_key"] = str(uuid.uuid4())
        self._log(f"Loaded data: {data}")

        self.csv_log_writer.writerow([self.config_data.org["name"], self.config_data.org["cluster"],
                                      self.config_data.output_image, data["unique_id"], data["host"]["hostname"],
                                      data["api_key"]])

        return data

    def _process_templates(self, template_specs):
        for template_spec in template_specs:
            out_file_name = self._write_template(template_spec)
            if "mode" in template_spec:
                self._process_mode(out_file_name, template_spec["mode"])
            if "owner" in template_spec:
                self._process_chown(out_file_name, template_spec["owner"])

    def _write_template(self, template_spec):
        filename = template_spec["path"]
        template = self.template_env.get_template(filename)
        out = template.render(self.data)
        out_file_name = os.path.join(self.out_folder, filename)
        out_path = Path(os.path.dirname(out_file_name))
        out_path.mkdir(parents=True, exist_ok=True)
        with open(out_file_name, "w") as out_file:
            out_file.write(out)
        self._log(f"wrote {out_file_name}")

        return out_file_name

    def _process_mode(self, file_path, mode_spec):
        self._log(f"processing chmod {mode_spec} {file_path}")
        os.chmod(file_path, int(mode_spec, base=8))

    def _process_chown(self, file_path, chown_spec):
        self._log(f"processing chown {chown_spec} {file_path}")
        uid = chown_spec["uid"] if "uid" in chown_spec else -1
        gid = chown_spec["gid"] if "gid" in chown_spec else -1
        os.chown(file_path, uid, gid)

    def _process_cert(self, ssl_cert_spec):
        self._log(f"Processing ssl_cert {ssl_cert_spec}")

        # Grab values out of the spec and data.
        cert_folder = ssl_cert_spec["folder"]
        ca_cert_pem_file = os.path.join(cert_folder, ssl_cert_spec["ca_cert_pem_file"])
        ca_cert_key_file = os.path.join(cert_folder, ssl_cert_spec["ca_cert_key_file"])
        cert_dest = ssl_cert_spec["dest"]
        hostname = self._get_hostname()

        # 1. Create a <hostname>.csr.cnf from the template.
        server_csr_path = os.path.join(cert_folder, f"{hostname}.csr.cnf")
        csr_template = self.template_env.get_template(ssl_cert_spec["server_csr_cnf_template"])
        csr_out = csr_template.render(self.data)
        with open(server_csr_path, 'w') as csr_out_file:
            csr_out_file.write(csr_out)

        # 2. Create a <host>-v3.ext file from the template.
        v3_ext_path = os.path.join(cert_folder, f"{hostname}-v3.ext")
        v3_ext_template = self.template_env.get_template(ssl_cert_spec["v3_ext_template"])
        v3_ext_out = v3_ext_template.render(self.data)
        with open(v3_ext_path, "w") as v3_ext_out_file:
            v3_ext_out_file.write(v3_ext_out)

        # 3. Create certificate key for this image. <hostname>.key
        # openssl req -new -sha256 -nodes -out server.csr -newkey rsa:2048 -keyout server.key -config <hostname>.csr.cnf
        key_cmd = (f"{OPENSSL_CMD} req -new -sha256 -nodes -out {cert_folder}/{hostname}.csr -newkey rsa:2048 "
                   f"-keyout {cert_folder}/{hostname}.key -config {server_csr_path}")
        os.system(key_cmd)

        # 4. Create a security certificate for this image <host>
        # openssl x509 -req -in server.csr -CA rootCA.pem -CAkey rootCA.key -CAcreateserial \
        #         -out server.crt -days 500 -sha256 -extfile v3.ext
        cert_cmd = (f"{OPENSSL_CMD} x509 -req -in {cert_folder}/{hostname}.csr -CA {ca_cert_pem_file} "
                    f"-CAkey {ca_cert_key_file} -CAcreateserial -out {cert_folder}/{hostname}.crt -days 500 -sha256 "
                    f"-extfile {v3_ext_path} -passin env:X_PASSPHRASE")

        my_env = copy.deepcopy(os.environ)
        my_env["X_PASSPHRASE"] = self.password
        process = Popen(cert_cmd.split(), env=my_env)

        # TODO check for error exit code here. How best to handle this kind of error?
        process.wait()

        os.system(f"cp {cert_folder}/{hostname}.crt {self.out_folder}/{cert_dest}/server.crt")
        os.system(f"cp {cert_folder}/{hostname}.key {self.out_folder}/{cert_dest}/server.key")

    def _get_hostname(self):
        return self.data['host']['hostname']

    def _process_rm(self, rm_spec):
        self._log(f"processing rm {rm_spec}")
        for item in rm_spec:
            path = item["path"]
            if path.startswith("/"):
                path = path[1:]
            rm_file_name = os.path.join(self.out_folder, path)
            os.remove(rm_file_name)
