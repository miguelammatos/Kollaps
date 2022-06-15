#! /bin/bash
base_port=5000

host_id=$1

num_servers=$2

echo $num_servers >> /tmp/log

for i in `seq 1 $num_servers`; do

    if [ "$i" = "$host_id" ];
    then
        continue
    fi
	# Set server port
	server_port=$(($base_port+$i));

	/usr/bin/iperf3 \
     -s -D \
    -p $server_port \
    --logfile "tmp/KOLLAPS_server$i.log" &

done

echo ID $host_id >> /tmp/log

sleep 5

for i in `seq 1 $num_servers`; do

    if [ "$i" = "$host_id" ];
    then
        continue
    fi
    server_ip=$(host "client"$i | grep -oE '\d+\.\d+\.\d+\.\d+')


    iperf3 \
    -c $server_ip \
    -t 120 \
    -p $(($base_port+$host_id)) \
    --logfile "/var/log/$server_ip.log" &

done