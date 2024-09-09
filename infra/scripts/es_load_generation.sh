#!/bin/bash

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

ES_HOST=$1
ES_USER=$2
ES_PASSWORD=$3

WORKLOAD="big5"
WORKLOAD_PARAMS="number_of_replicas:0,bulk_indexing_clients:1,max_num_segments:10,target_throughput:\"\""
CLIENT_OPTIONS="basic_auth_user:$ES_USER,basic_auth_password:$ES_PASSWORD,use_ssl:true,verify_certs:false"

INGESTION_RESULTS=/mnt/ingestion_results

sudo apt update && sudo apt install -y pbzip2 jq

export PATH=$PATH:~/.local/bin
echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc

sudo apt install -y python3-pip python3-venv git

pip install opensearch-benchmark

# NOTE: is this really necessary?
sudo sysctl -w vm.max_map_count=262144
sudo sysctl -p

sudo apt install -y openjdk-17-jdk-headless
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64/
echo 'export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64/' >> ~/.bashrc

export BENCHMARK_HOME=/mnt
echo 'export BENCHMARK_HOME=/mnt' >> ~/.bashrc

curl -ku "$ES_USER:$ES_PASSWORD" "$ES_HOST" || exit 1

# NOTE: check this, how to download the workload without getting stuck?
opensearch-benchmark execute-test \
    --pipeline=benchmark-only \
    --workload=$WORKLOAD \
    --target-hosts="$ES_HOST" \
    --client-options="$CLIENT_OPTIONS" \
    --test-mode \
    --workload-params=number_of_replicas:0 \
    --distribution-version=8.0.0 \
    --kill-running-processes \
    '--include-tasks=""'

# Replace workload index.json file with one for the correct ES version
ES_VERSION=$(curl -ku "$ES_USER:$ES_PASSWORD" "$ES_HOST" | jq -r '.version.number')
cp "$SCRIPT_DIR/es_indexes/es_index_$ES_VERSION.json" "$BENCHMARK_HOME/.benchmark/benchmarks/workloads/default/$WORKLOAD/index.json"


set -x

# Ingest data in the ES cluster
opensearch-benchmark execute-test \
    --pipeline=benchmark-only \
    --workload=$WORKLOAD \
    --target-hosts="$ES_HOST" \
    --workload-params="$WORKLOAD_PARAMS" \
    --client-options="$CLIENT_OPTIONS" \
    --kill-running-processes \
    --results-file=$INGESTION_RESULTS \
    --test-execution-id=ingestion \
    --distribution-version=8.0.0 \
    --exclude-tasks="type:search"

TEST_EXECUTION_ID="es-query-benchmark"
RESULTS_FILE="/mnt/$TEST_EXECUTION_ID"

# Queries only
echo "Running Queries Only"
for i in $(seq 0 3)
do
        opensearch-benchmark execute-test \
                --pipeline=benchmark-only \
                --workload=$WORKLOAD  \
                --target-hosts="$ES_HOST" \
                --workload-params="$WORKLOAD_PARAMS" \
                --client-options="$CLIENT_OPTIONS" \
                --kill-running-processes \
                --include-tasks="type:search" \
                --results-file="$RESULTS_FILE-$i" \
                --test-execution-id="$TEST_EXECUTION_ID-$i" \
                --distribution-version=8.0.0
done
