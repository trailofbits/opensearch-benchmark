#!/bin/bash

if [ "$#" -ne 2 ]; then
    echo "usage: $0 /path/to/benchmark/results/ /path/to/credentials.json"
    exit 1
fi

if [ -f "token.json" ]; then
    make run ARGS="create --benchmark-data $1 --token token.json"
else
    make run ARGS="create --benchmark-data $1 --token token.json --credentials $2"
fi