#!/bin/bash

CLUSTER_HOST=$1
CLUSTER_USER=$2
CLUSTER_PASSWORD=$3
WORKLOAD="big5"
BENCHMARK_HOME="/mnt"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Replace workload index.json file with one for the correct ES version
CURRENT_ES_VERSION=$(curl -ku "$CLUSTER_USER:$CLUSTER_PASSWORD" "$CLUSTER_HOST" | jq -r '.version.number')
cp "$SCRIPT_DIR/es_indexes/es_index_$CURRENT_ES_VERSION.json" "$BENCHMARK_HOME/.benchmark/benchmarks/workloads/default/$WORKLOAD/index.json"

echo "Fixing index.json for ES version $CURRENT_ES_VERSION"
