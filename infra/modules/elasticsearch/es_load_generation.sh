#!/bin/bash

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

CLUSTER_HOST=$1
CLUSTER_PASSWORD=$2
CLUSTER_USER=elastic

WORKLOAD="big5"
CLIENT_OPTIONS="basic_auth_user:$CLUSTER_USER,basic_auth_password:$CLUSTER_PASSWORD,use_ssl:true,verify_certs:false"

export PATH=$PATH:~/.local/bin
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64/
export BENCHMARK_HOME=/mnt

echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc
echo 'export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64/' >> ~/.bashrc
echo 'export BENCHMARK_HOME=/mnt' >> ~/.bashrc
echo "export CLUSTER_HOST=$CLUSTER_HOST" >> ~/.bashrc
echo "export CLUSTER_USER=$CLUSTER_USER" >> ~/.bashrc

pip install opensearch-benchmark

# wait for ES to be up
echo "CLUSTER_HOST: $CLUSTER_HOST"
while ! curl --max-time 5 -ku "$CLUSTER_USER:$CLUSTER_PASSWORD" "$CLUSTER_HOST"; do
    echo "Waiting for ES to be up"
    sleep 2
done

opensearch-benchmark execute-test \
    --pipeline=benchmark-only \
    --workload=$WORKLOAD \
    --target-hosts="$CLUSTER_HOST" \
    --client-options="$CLIENT_OPTIONS" \
    --test-mode \
    --workload-params=number_of_replicas:0 \
    --distribution-version=8.15.0 \
    --kill-running-processes \
    '--include-tasks=""'

# Replace workload index.json file with one for the correct ES version
CURRENT_ES_VERSION=$(curl -ku "$CLUSTER_USER:$CLUSTER_PASSWORD" "$CLUSTER_HOST" | jq -r '.version.number')
cp "$SCRIPT_DIR/es_indexes/es_index_$CURRENT_ES_VERSION.json" "$BENCHMARK_HOME/.benchmark/benchmarks/workloads/default/$WORKLOAD/index.json"

echo "Load Generation host setup"
