#!/bin/bash
trap 'exit 0' INT

sleep 2

echo $1 >> /tmp/log

echo "Launched!"
host=$(hostname)

#obtain the service identifier
service="$1-$KOLLAPS_UUID"

#debug
echo ID $host_id >> /tmp/log
#debug
echo Service $service >> /tmp/log

server_ip=$(host $service | grep -oE '\d+\.\d+\.\d+\.\d+' | sort -u | sed -n ${host_id}p)
#debug
echo SERVER_IP $server_ip >> /tmp/log
mkdir /eval/
#write the target latency
echo $3 > /eval/$(hostname).ping
ping \
    -w $2 \
    $server_ip >> /eval/$(hostname).ping &
