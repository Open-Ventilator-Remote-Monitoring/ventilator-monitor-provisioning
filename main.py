#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This is the main script."""

import argparse
import csv
import getpass
import glob
import re
import os
from argparse import Namespace

from yaml import load, Loader

from mounter import Mounter
from provisioner import Provisioner


# The MVP requirements for this image provisioning tool are:
# 1. Automatically generated hostname ✔
# 2. Automatically generated api-key ✔
# 3. Automatically generated, signed key (server.key) and cert (server.crt) ✔
# 4. Create proper production config yaml file and put it in the right place ✔
# 5. Remove dev responders and configuration files (Note, can't be done until we are doing conditional imports in the
#    python code)
#     communication/random_ventilator.py
#     plugin/alarm_sound_plugin/random_alarm.py
#     application-development.yml
#     application-desktop-development.yml
# 6. Logging to a CSV file ✔
# 7. Update to the latest code ✔
# 8. Remove the current auto-hostname ✔

# Future enhancements:
# 1. TODO Randomly generated password
# 2. TODO Start from baseline raspbian image instead of our customized image
# 3. TODO Need a way to generate a replacement image for a given device (with serial number, etc. as input)
# 4. TODO Optional .xz compression on the resulting image(s). (On my system it will add )


def main():
    """
    Main function for main script.
    """
    parser = argparse.ArgumentParser(description='Provision pi images.')
    parser.add_argument("--scheme-file", "-s", required=True)
    parser.add_argument("--config-file", '-c', required=True)
    parser.add_argument("--output-folder", "-o", default="./out")
    parser.add_argument("--work-folder", "-w", default="./work")
    parser.add_argument("--n-units", "-n", type=int, default=1)
    parser.add_argument("--no-unmount", "-x", action="store_true",
                        default=False)
    parser.add_argument("--log-file", "-l")
    args = parser.parse_args()

    config = Namespace(**load(open(args.config_file, 'r'), Loader=Loader))

    if not args.log_file:
        args.log_file = "provisioning.csv"

    log_open_mode = "w"
    log_write_header = True
    if os.path.exists(args.log_file):
        log_open_mode = "a"
        log_write_header = False

    with open(args.log_file, log_open_mode) as log_file:
        log_writer = csv.writer(log_file, dialect=csv.excel)
        if log_write_header:
            log_writer.writerow(['Org Name', 'Cluster', 'Image File', 'Unique ID', 'Host Name', 'API Key'])

        org_name = config.org['name'].lower()
        org_cluster = config.org['cluster'].lower()

        start_seq = _find_starting_seq(args.output_folder, org_name, org_cluster)

        # Prompt for the root CA password. NOTE that this is not ideal for automation, but security needs to be thought
        # about before we get this value from elsewhere.
        password = getpass.getpass("CA root password: ")

        for file_seq in range(start_seq, start_seq + args.n_units):
            output_image = f"{org_name}-{org_cluster}-{str(file_seq + 1).zfill(4)}.img"
            output_image = re.sub(r"\s+", "_", output_image, flags=re.UNICODE)
            config.output_image = output_image
            output_image_path = os.path.join(args.output_folder, output_image)

            os.system(f"cp {config.source_image} {output_image_path}")

            mounter = Mounter(output_image_path, args.work_folder)
            mounter.mount()

            provisioner = Provisioner(mounter.mount_pathname, config, args.scheme_file, log_writer, password)
            provisioner.process()

            if not args.no_unmount:
                mounter.unmount()

def _find_starting_seq(output_folder, org_name, org_cluster):
    """
    Finds the starting sequence number by globbing the path pattern we're using and then finding the max sequence
    number on the existing image files.
    """
    if output_folder.endswith("/"):
        output_folder = output_folder[:-1]
    prefix = f"{org_name}-{org_cluster}-"
    prefix = re.sub(r"\s+", "_", prefix, flags=re.UNICODE)
    path = f"{output_folder}/{prefix}*.img"
    max_seq = 0
    for seq in glob.glob(path):
        seq = seq.replace(f"{output_folder}/", "")
        seq = seq.replace(prefix, "")
        seq = seq.replace(".img", "")
        num = int(seq, base=10)
        max_seq = max([max_seq, num])

    return max_seq

if __name__ == "__main__":
    main()
