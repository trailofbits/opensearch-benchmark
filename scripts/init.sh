#!/bin/bash

if [ `id -u` -ne 0 ]; then
    echo "must be root."
    exit 2
fi

sysctl -w vm.max_map_count=262144
sysctl -p