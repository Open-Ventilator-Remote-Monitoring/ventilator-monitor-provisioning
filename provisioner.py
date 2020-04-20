import os
import uuid
from pathlib import Path
from argparse import Namespace
from codenamize import codenamize
from jinja2 import Environment, FileSystemLoader
from yaml import load, Loader


class Provisioner(object):
    def __init__(self, out_folder, template_folder="./templates"):
        self.out_folder = out_folder
        self.data = self._load_data()
        self.template_env = Environment(
            loader=FileSystemLoader(template_folder),
            keep_trailing_newline=True)

    def process(self, scheme_file):
        self.scheme = load(open(scheme_file, 'r'), Loader=Loader)
        self._log(f'Loaded scheme: {self.scheme}')
        for key, item in self.scheme.items():
            self._log(f'Processing {key} spec')
            if 'templates' in item:
                self._process_templates(item['templates'])

        return self.data

    def _log(self, msg):
        print(msg)

    def _load_data(self):
        data = {}
        data['unique_id'] = str(uuid.uuid4())
        data['host'] = {}
        data['host']['hostname'] = codenamize(data['unique_id'], adjectives=2,
                                              max_item_chars=0, join='-',
                                              hash_algo='sha3_512')
        data['api_key'] = {}
        data['api_key']['key'] = str(uuid.uuid4())
        self._log(f"Loaded data: {data}")

        return data

    def _process_templates(self, template_specs):
        for template_spec in template_specs:
            out_file_name = self._write_template(template_spec)
            if 'mode' in template_spec:
                self._process_mode(out_file_name, template_spec['mode'])
            if 'owner' in template_spec:
                self._process_chown(out_file_name, template_spec['owner'])

    def _write_template(self, template_spec):
        # self._log(template_spec)
        filename = template_spec['name']
        template = self.template_env.get_template(filename)
        out = template.render(self.data)
        out_file_name = os.path.join(self.out_folder, filename)
        out_path = Path(os.path.dirname(out_file_name))
        out_path.mkdir(parents=True, exist_ok=True)
        with open(out_file_name, 'w') as out_file:
            out_file.write(out)
        self._log(f"wrote {out_file_name}")

        return out_file_name

    def _process_mode(self, file_path, mode_spec):
        self._log(f"processing chmod {mode_spec} {file_path}")
        os.chmod(file_path, int(mode_spec, base=8))

    def _process_chown(self, file_path, chown_spec):
        self._log(f"processing chown {chown_spec} {file_path}")
        uid = chown_spec['uid'] if 'uid' in chown_spec else -1
        gid = chown_spec['gid'] if 'gid' in chown_spec else -1
        os.chown(file_path, uid, gid)
