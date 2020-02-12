#! /bin/bash

trap 'exit 0' INT

while true; do
    sleep 10000
    echo "logger is up!"
done
