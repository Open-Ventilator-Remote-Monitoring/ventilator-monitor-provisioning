# -*- coding: utf-8 -*-
"""Mounter module file"""

import os
from pathlib import Path

MOUNT_CMD = "./scripts/mount.sh"
UNMOUNT_CMD = "./scripts/unmount.sh"


class Mounter:
    """Handles mounting and unmounting disk images."""
    def __init__(self, image_file, work_folder):
        self.image_file = image_file
        self.work_folder = work_folder
        image_filename = os.path.basename(self.image_file)
        self.mount_pathname = os.path.join(self.work_folder, image_filename)

    def mount(self):
        """Mount the disk image."""
        mount_path = Path(self.mount_pathname)
        mount_path.mkdir(parents=True, exist_ok=True)
        if len(list(mount_path.iterdir())) > 0:
            raise RuntimeError(f"Mount path {self.mount_pathname} must be empty.")

        os.system(f"{MOUNT_CMD} {self.image_file} {self.mount_pathname}")

    def unmount(self):
        """Unmount the disk image."""
        print(f"Unmounting {self.mount_pathname}")
        os.system(f"{UNMOUNT_CMD} {self.mount_pathname}")
