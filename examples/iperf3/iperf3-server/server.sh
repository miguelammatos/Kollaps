#! /bin/bash

/usr/bin/iperf3 \
    -J -s -D \
    -p 6001 \
    --logfile "/var/log/KOLLAPS_server.log" &
