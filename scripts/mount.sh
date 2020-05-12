#!/bin/sh

if [ "$#" -ne 2 ]; then
    echo "Usage"
    echo $0 IMAGE_FILE MOUNT_POINT
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root or equivalent."
   exit 1
fi

IMAGE_FILE=${1}
MOUNT_POINT=${2}
LOOP=$(losetup --show -fP "${IMAGE_FILE}")
sudo mount ${LOOP}p2 ${MOUNT_POINT}
