#! /bin/bash

/usr/bin/iperf3 \
    -J -s -D \
    -p 6001 \
    --logfile "/var/log/KOLLAPS_server1.log" &
/usr/bin/iperf3 \
    -J -s -D \
    -p 6002 \
    --logfile "/var/log/KOLLAPS_server2.log" &
tcpdump \
    -n -i eth0 \
    -B 4096 \
    -G 100 \
    -W 1 -w /tmp/server.pcap "tcp port 6001 or port 6002"
