#!/bin/bash

if [ "$#" -ne 2 ]; then
    echo "usage: $0 /path/to/credentials.json"
    exit 1
fi

if [ -f "token.json" ]; then
    make run ARGS="create ./download_versioned --token token.json"
else
    make run ARGS="create ./download_versioned --token token.json --credentials $1"
fi