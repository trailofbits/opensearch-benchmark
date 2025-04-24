#!/bin/bash

CLUSTER_HOST=$1
CLUSTER_USER=$2
CLUSTER_PASSWORD=$3

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
WORKLOAD="${workload}"

BENCHMARK_HOME="/mnt"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "$${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Replace workload index.json file with one for the correct ES version
CURRENT_ES_VERSION=$(curl -ku "$CLUSTER_USER:$CLUSTER_PASSWORD" "$CLUSTER_HOST" | jq -r '.version.number')
# Get only the first 2 numbers of the version (e.g. "7.10.2" -> "7.10")
CURRENT_ES_VERSION=$(echo "$CURRENT_ES_VERSION" | cut -d. -f1-2)
# Check if there is a replacement index.json file for the current ES version
if [ ! -f "$SCRIPT_DIR/es_indexes/$WORKLOAD/es_index_$CURRENT_ES_VERSION.json" ]; then
    # Get only the first number of the version (e.g. "7.10.2" -> "7")
    CURRENT_ES_VERSION=$(echo "$CURRENT_ES_VERSION" | cut -d. -f1)
    if [ ! -f "$SCRIPT_DIR/es_indexes/$WORKLOAD/es_index_$CURRENT_ES_VERSION.json" ]; then
        echo "No index.json file found for Workload $WORKLOAD ES version $CURRENT_ES_VERSION"
        exit 0
    fi
fi

echo "Using index.json file for Workload $WORKLOAD ES version $CURRENT_ES_VERSION"

cp "$SCRIPT_DIR/es_indexes/$WORKLOAD/es_index_$CURRENT_ES_VERSION.json" "$BENCHMARK_HOME/.osb/benchmarks/workloads/default/$WORKLOAD/index.json"
echo "Fixing index.json for Workload $WORKLOAD ES version $CURRENT_ES_VERSION"

#   # Fix OSB to be compatible with the ES KNN API
#   OSB_INSTALL_DIR="$(pip list -v | grep opensearch-benchmark | awk '{print $3}')"
#   PATCH_FILE="/es_files/osb-1.11.0-knn.patch"
#   patch -p0 -d "$OSB_INSTALL_DIR" < "$PATCH_FILE"

#   # Fix OSB vectorsearch workload to pass extra ES KNN API parameters
#   OSB_WORKLOAD_DIR="/mnt/.osb/benchmarks/workloads/default"
#   PATCH_FILE="/es_files/vectorsearch-task.patch"
#   patch -p0 -d "$OSB_WORKLOAD_DIR" < "$PATCH_FILE"
