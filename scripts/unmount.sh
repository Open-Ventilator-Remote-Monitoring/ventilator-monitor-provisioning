#!/bin/sh

# This script should be installed into /opt/provisioning/bin, and should be
# owned by root, with permissions 700.

if [ "$#" -ne 1 ]; then
    echo "Usage"
    echo $0 MOUNT_POINT
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root or equivalent."
   exit 1
fi

umount ${1}
