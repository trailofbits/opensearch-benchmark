#!/bin/bash

hostnamectl set-hostname "${hostname}"

INSTALL_ROOT=/mnt
USER=ubuntu
SCRIPT_DIR=/home/$USER

if [ -z "$INSTALL_ROOT" ]; then
    echo "Please provide the path to the directory to mount"
    exit 1
fi

# install root does not exist, assuming we'll have to make a new fs and mount
# TODO: Ideally, these could be computed automatically
DISK=nvme1n1
PARTITION=nvme1n1p1
echo "Attempt to partition and mount local disk"
lsblk | grep $DISK || (echo "Couldn't find $DISK. Abort" && false) 
sudo parted /dev/$DISK mklabel gpt 
sudo parted --align opt /dev/$DISK mkpart data 1 100% 
sudo mkfs.xfs /dev/$PARTITION

sudo mkdir $INSTALL_ROOT || echo "$INSTALL_ROOT already exists, will still mount"
sudo mount /dev/$PARTITION $INSTALL_ROOT
sudo chown -R $USER $INSTALL_ROOT
echo "Done"

# Wait until scripts are copied by provisioners
while [ ! -f "$SCRIPT_DIR/init_machine.sh" ]; do
    echo "Waiting for init_machine.sh to be copied"
    sleep 2
done

chmod +x "$SCRIPT_DIR/init_machine.sh"
"$SCRIPT_DIR/init_machine.sh" ${args} || exit 1

exit 0
