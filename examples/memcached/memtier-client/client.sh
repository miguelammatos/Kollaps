#!/bin/bash
trap 'exit 0' INT

sleep 2

echo $1 >> /tmp/log

host=$(hostname)
n=$((${#host}-1))
host_id="${host:$n:1}"

echo "$host_id: Memtier Client Launched!"
#obtain the service identifier
service="$1-$KOLLAPS_UUID"

echo ID $host_id >> /tmp/log
echo Service $service >> /tmp/log

#find out the IP of the servers through the experiment UUID 
#nth client should connect to nth server
server_ip=$(host $service | grep -oE '\d+\.\d+\.\d+\.\d+' | sort -u) 
echo SERVER_IP $server_ip >> /tmp/log

/memtier_benchmark -s $server_ip -p 11211 -P memcache_binary > /tmp/memtier-out 2> /tmp/memtier-err
