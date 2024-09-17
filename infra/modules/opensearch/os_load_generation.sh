#!/bin/bash

CLUSTER_HOST=$1
CLUSTER_PASSWORD=$2
CLUSTER_VERSION=$3
CLUSTER_USER=admin

# TODO:Make configurable in the future
WORKLOAD="big5"
CLIENT_OPTIONS="basic_auth_user:$CLUSTER_USER,basic_auth_password:$CLUSTER_PASSWORD,use_ssl:true,verify_certs:false"

export PATH=$PATH:~/.local/bin
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64/
export BENCHMARK_HOME=/mnt

echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc
echo 'export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64/' >> ~/.bashrc
echo "export BENCHMARK_HOME=$BENCHMARK_HOME" >> ~/.bashrc
# For convenient access later on
echo "export CLUSTER_HOST=$CLUSTER_HOST" >> ~/.bashrc
echo "export CLUSTER_USER=$CLUSTER_USER" >> ~/.bashrc

pip install opensearch-benchmark

# wait for OS to be up
echo "CLUSTER_HOST: $CLUSTER_HOST"
while ! curl --max-time 5 -ku "$CLUSTER_USER:$CLUSTER_PASSWORD" "$CLUSTER_HOST"; do
    echo "Waiting for OS to be up"
    sleep 2
done

opensearch-benchmark execute-test \
    --pipeline=benchmark-only \
    --workload=$WORKLOAD \
    --target-hosts="$CLUSTER_HOST" \
    --client-options="$CLIENT_OPTIONS" \
    --test-mode \
    --workload-params=number_of_replicas:0 \
    --distribution-version=$CLUSTER_VERSION \
    --kill-running-processes \
    '--include-tasks=""'

echo "Load Generation host setup"
