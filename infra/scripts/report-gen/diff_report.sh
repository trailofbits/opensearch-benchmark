#!/bin/bash

if [ "$#" -ne 2 ]; then
    echo "usage: $0 /benchmarkA/ /benchmarkB/"
    exit 1
fi

make run ARGS=" diff \
    --a $1 \
    --b $2
"
