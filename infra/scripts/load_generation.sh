#!/bin/bash

source /mnt/utils.sh

# Get script directory
CLUSTER_HOST_SSH=$1
CLUSTER_HOST=https://$CLUSTER_HOST_SSH:9200
CLUSTER_USER=$2
CLUSTER_PASSWORD=$3
DISTRIBUTION_VERSION=$4
CLUSTER_VERSION=$5
ENGINE_TYPE=$6
INSTANCE_TYPE=$7
CLUSTER_INSTANCE_ID=$8

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
WORKLOAD="${workload}"

# This comes from the `main.tf` configuration file
# shellcheck disable=SC2154
AWS_USERID="${aws_userid}"

CLIENT_OPTIONS=$(join_by , "basic_auth_user:$CLUSTER_USER,basic_auth_password:$CLUSTER_PASSWORD,use_ssl:true,verify_certs:false" $EXTRA_CLIENT_OPTIONS)

export PATH=$PATH:~/.local/bin
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64/
export BENCHMARK_HOME=/mnt

echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc
echo 'export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64/' >> ~/.bashrc
echo 'export BENCHMARK_HOME=/mnt' >> ~/.bashrc
echo "export CLUSTER_HOST_SSH=$CLUSTER_HOST_SSH" >> ~/.bashrc
echo "export CLUSTER_HOST=$CLUSTER_HOST" >> ~/.bashrc
echo "export CLUSTER_USER=$CLUSTER_USER" >> ~/.bashrc
echo "export DISTRIBUTION_VERSION=$DISTRIBUTION_VERSION" >> ~/.bashrc
echo "export ENGINE_TYPE=$ENGINE_TYPE" >> ~/.bashrc
echo "export INSTANCE_TYPE=$INSTANCE_TYPE" >> ~/.bashrc
echo "export CLUSTER_VERSION=$CLUSTER_VERSION" >> ~/.bashrc
echo "export CLUSTER_PASSWORD=$CLUSTER_PASSWORD" >> ~/.bashrc
echo "export AWS_USERID=$AWS_USERID" >> ~/.bashrc
echo "export CLUSTER_INSTANCE_ID=$CLUSTER_INSTANCE_ID" >> ~/.bashrc

pip install opensearch-benchmark

# wait for the cluster to be up (break after 20 times)
echo "CLUSTER_HOST: $CLUSTER_HOST"
tries=0
while ! curl --max-time 5 -ku "$CLUSTER_USER:$CLUSTER_PASSWORD" "$CLUSTER_HOST"; do
    echo "Waiting for the cluster to be up ($tries)"
    sleep 2
    ((tries++))
    if [ $tries -eq 20 ]; then
        echo "Failed to start OpenSearch"
        exit 1
    fi
done

opensearch-benchmark execute-test \
    --pipeline=benchmark-only \
    --workload=$WORKLOAD \
    --target-hosts="$CLUSTER_HOST" \
    --client-options="$CLIENT_OPTIONS" \
    --test-mode \
    --distribution-version=$DISTRIBUTION_VERSION \
    --kill-running-processes \
    '--include-tasks=""'

echo "Load Generation host setup"
