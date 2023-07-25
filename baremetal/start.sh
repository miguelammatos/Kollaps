#! /bin/sh
sudo rm /remote_ips.txt
sudo rm /tmp/topoinfo
sudo rm /tmp/topoinfodashboard
sudo rm /tmp/pipe*
sudo rm /tmp/logs.txt
sudo rm /logs.txt
sudo rm /ips.txt
# cd kollaps/emulationcore
# cargo build --release
# cd ..
# cd ..
# cd kollaps/controller
# cargo build --release
# cd ..
# cd ..
sudo cp libTCAL.so /usr/local/bin/libTCAL.so
sudo ./emulationcore $1 communicationmanager eth0 baremetal
