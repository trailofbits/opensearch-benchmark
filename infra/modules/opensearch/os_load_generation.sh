#!/bin/bash

USER=ubuntu

if [ $UID -eq 0 ]; then
  exec sudo -u "$USER" "$0" "$@"
  # nothing will be executed from root beyond that line,
  # because exec replaces running process with the new one
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

OS_HOST=$1
OS_PASSWORD=$2
OS_VERSION=$3
OS_USER=admin

# TODO:Make configurable in the future
WORKLOAD="big5"
CLIENT_OPTIONS="basic_auth_user:$OS_USER,basic_auth_password:$OS_PASSWORD,use_ssl:true,verify_certs:false"

sudo apt update && sudo apt install -y pbzip2 jq

export PATH=$PATH:~/.local/bin
echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc

sudo apt install -y python3-pip python3-venv git

pip install opensearch-benchmark

# Ensure map count is the expected
# TODO: This won't survive a reboot. Consider persisting to /etc/sysctl.conf
sudo sysctl -w vm.max_map_count=262144

sudo apt install -y openjdk-17-jdk-headless
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64/
echo 'export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64/' >> ~/.bashrc

export BENCHMARK_HOME=/mnt
echo "export BENCHMARK_HOME=$BENCHMARK_HOME" >> ~/.bashrc

# For convenient access later on
echo "export OS_HOST=$OS_HOST" >> ~/.bashrc

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
