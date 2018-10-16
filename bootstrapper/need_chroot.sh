#! /bin/sh
mkdir -p /opt/NEEDrw
cp -aHr /opt/NEED/chroot/* /opt/NEEDrw/ 
chroot /opt/NEEDrw /usr/bin/NEEDemucore
