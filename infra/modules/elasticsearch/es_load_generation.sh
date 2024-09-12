#!/bin/bash

USER=ubuntu

if [ $UID -eq 0 ]; then
  exec sudo -u "$USER" "$0" "$@"
  # nothing will be executed from root beyond that line,
  # because exec replaces running process with the new one
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

ES_HOST=$1
ES_PASSWORD=$2
ES_USER=elastic

WORKLOAD="big5"
CLIENT_OPTIONS="basic_auth_user:$ES_USER,basic_auth_password:$ES_PASSWORD,use_ssl:true,verify_certs:false"

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

# wait for ES to be up
echo "ES_HOST: $ES_HOST"
while ! curl --max-time 5 -ku "$ES_USER:$ES_PASSWORD" "$ES_HOST"; do
    echo "Waiting for ES to be up"
    sleep 2
done

opensearch-benchmark execute-test \
    --pipeline=benchmark-only \
    --workload=$WORKLOAD \
    --target-hosts="$ES_HOST" \
    --client-options="$CLIENT_OPTIONS" \
    --test-mode \
    --workload-params=number_of_replicas:0 \
    --distribution-version=8.15.0 \
    --kill-running-processes \
    '--include-tasks=""'

# Replace workload index.json file with one for the correct ES version
ES_VERSION=$(curl -ku "$ES_USER:$ES_PASSWORD" "$ES_HOST" | jq -r '.version.number')
# wait for es_indexes directory to be copied
while [ ! -d "$SCRIPT_DIR/es_indexes" ]; do
    echo "Waiting for es_index_$ES_VERSION.json to be copied"
    sleep 2
done
cp "$SCRIPT_DIR/es_indexes/es_index_$ES_VERSION.json" "$BENCHMARK_HOME/.benchmark/benchmarks/workloads/default/$WORKLOAD/index.json"

echo "Load Generation host setup"
