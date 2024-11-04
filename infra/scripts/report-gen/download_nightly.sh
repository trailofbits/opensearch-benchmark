#!/bin/bash

if [ -z ${DS_PASSWORD+x} ]; then
    echo "DS_PASSWORD is unset"
    exit 1
fi

if [ "$#" -ne 2 ]; then
    echo "usage: $0 <start_date [YYYY-MM-DD]> <end_date [YYYY-MM-DD]>"
    exit 1
fi

start="$1"
end="$2"

folder="download_nightly_${start}_${end}"
mkdir -p $folder
make run ARGS=" download \
    --host opense-clust-AEqAZh9qc4u7-dcbe5cce2775e15e.elb.us-east-1.amazonaws.com \
    --benchmark-data $folder \
    --source ci-scheduled \
    --from $start \
    --to $end
"