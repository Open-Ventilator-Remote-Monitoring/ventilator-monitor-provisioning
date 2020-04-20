#!/usr/bin/env python

import argparse
import re
import os
from pathlib import Path
from provisioner import Provisioner
from yaml import load, Loader
from argparse import Namespace
from mounter import Mounter

# The MVP requirements for this image provisioning tool are:
# 1. Automatically generated hostname ✔
# 2. Automatically generated api-key ✔
# 3. Automatically generated, signed key (server.key) and cert (server.crt)
# 4. Create proper production config yaml file and put it in the right place
# 5. Remove dev responders and configuration files

# Future enhancements:
# 1. TODO Randomly generated password
# 2. TODO Start from baseline raspbian image instead of our customized image


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Provision pi images.')
    parser.add_argument("--scheme-file", "-s", required=True)
    parser.add_argument("--config-file", '-c', required=True)
    parser.add_argument("--output-folder", "-o", default="./out")
    parser.add_argument("--work-folder", "-w", default="./work")
    parser.add_argument("--n-units", "-n", type=int, default=1)
    parser.add_argument("--no-unmount", "-x", action="store_true",
                        default=False)
    args = parser.parse_args()

    config = Namespace(**load(open(args.config_file, 'r'), Loader=Loader))
    print(config)

    for n in range(args.n_units):
        org_name = config.org['name'].lower()
        org_cluster = config.org['cluster'].lower()
        output_image = f"{org_name}-{org_cluster}-{str(n + 1).zfill(4)}.img"
        output_image = re.sub(r"\s+", "_", output_image, flags=re.UNICODE)
        print(output_image)
        output_image_path = os.path.join(args.output_folder, output_image)

        print(f"copying {config.source_image} to {output_image_path}")
        os.system(f"cp {config.source_image} {output_image_path}")

        mounter = Mounter(output_image_path, args.work_folder)
        mounter.mount()

        provisioner = Provisioner(mounter.mount_pathname)
        provisioner.process(args.scheme_file)

        if not args.no_unmount:
            mounter.unmount()
