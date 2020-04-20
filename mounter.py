import os
from pathlib import Path

MOUNT_CMD = "/opt/provisioning/bin/mount.sh"
UNMOUNT_CMD = "/opt/provisioning/bin/unmount.sh"


class Mounter:
    def __init__(self, image_file, work_folder):
        self.image_file = image_file
        self.work_folder = work_folder

    def mount(self):
        image_filename = os.path.basename(self.image_file)
        self.mount_pathname = os.path.join(self.work_folder, image_filename)
        mount_path = Path(self.mount_pathname)
        mount_path.mkdir(parents=True, exist_ok=True)
        if len(list(mount_path.iterdir())) > 0:
            raise Error(f"Mount path {mount_pathname} must be empty.")

        os.system(f"{MOUNT_CMD} {self.image_file} {self.mount_pathname}")

    def unmount(self):
        os.system(f"{UNMOUNT_CMD} {self.mount_pathname}")
