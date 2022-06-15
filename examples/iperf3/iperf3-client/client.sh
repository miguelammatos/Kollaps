#!/bin/bash
trap 'exit 0' INT

sleep 2

echo $1 >> /tmp/log

echo "Launched!"
#host=$(hostname)
#n=$((${#host}-1))
host_id="$2"

#obtain the service identifier
service="$1-$KOLLAPS_UUID"

echo ID $host_id >> /tmp/log
echo Service $service >> /tmp/log

#find out the IP of the servers through the experiment UUID 
#nth client should connect to nth server
server_ip=$(host $service | grep -oE '\d+\.\d+\.\d+\.\d+' | sort -u | sed -n ${host_id}p)
echo SERVER_IP $server_ip >> /tmp/log
iperf3 \
    -c $server_ip \
    -t 120 \
    -p 6001 \
    --logfile "/var/log/KOLLAPS_client$host_id.log" &
