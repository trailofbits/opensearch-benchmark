#!/bin/bash

OS_HOST=$1
OS_PASSWORD=$2
OS_VERSION=$3
OS_USER=elastic

# TODO:Make configurable in the future
WORKLOAD="big5"
CLIENT_OPTIONS="basic_auth_user:$OS_USER,basic_auth_password:$OS_PASSWORD,use_ssl:true,verify_certs:false"

export PATH=$PATH:~/.local/bin
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64/
export BENCHMARK_HOME=/mnt

echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc
echo 'export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64/' >> ~/.bashrc
echo "export BENCHMARK_HOME=$BENCHMARK_HOME" >> ~/.bashrc
# For convenient access later on
echo "export OS_HOST=$OS_HOST" >> ~/.bashrc

pip install opensearch-benchmark

# wait for OS to be up
echo "OS_HOST: $OS_HOST"
while ! curl --max-time 5 -ku "$OS_USER:$OS_PASSWORD" "$OS_HOST"; do
    echo "Waiting for OS to be up"
    sleep 2
done

opensearch-benchmark execute-test \
    --pipeline=benchmark-only \
    --workload=$WORKLOAD \
    --target-hosts="$OS_HOST" \
    --client-options="$CLIENT_OPTIONS" \
    --test-mode \
    --workload-params=number_of_replicas:0 \
    --distribution-version=$OS_VERSION \
    --kill-running-processes \
    '--include-tasks=""'

echo "Load Generation host setup"
