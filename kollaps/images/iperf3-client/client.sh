#!/bin/bash

trap 'exit 0' INT

sleep 2

echo "Launched!"
host=$(hostname)
n=$((${#host}-1))
host_id="${host:$n:1}"

service="$1-$NEED_UUID"
for ip in $(host $service | grep -oE '\d+\.\d+\.\d+\.\d+' | head -n 1);
do
    echo $ip
    port="600${host_id}"
    echo $port
    iperf3 \
        -J -c $ip \
        -t 100 \
        -p $port \
        --logfile "/var/log/KOLLAPS_client$host_id.log" &
    tcpdump \
        -n -i eth0 \
        -B 4096 \
        -G 100 \
        -W 1 \
        -w "/var/log/KOLLAPS_client$host_id.pcap" tcp port $port
done
