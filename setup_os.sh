#!/bin/bash
# This script installs OpenSearch and OpenSearch Benchmark.
# It configures OpenSearch and runs a test workload to validate the installation.
# Usage: bash setup_os.sh
# Tested on Ubuntu 22.04
# Environment variables:
#   OS_PASSWORD: password for opensearch
#   CLUSTER_IP: IP address for cluster. Recommend the private IP from `hostname -I`.
set -ex
if [ -z "${OS_PASSWORD}" ]; then
    echo "OS_PASSWORD environment variable is empty or unset"
    exit 1
fi
if [ -z "${CLUSTER_IP}" ]; then
    echo "CLUSTER_IP environment variable is empty or unset"
    exit 1
fi

JVM_MIN_HEAP="-Xms4g"
JVM_MAX_HEAP="-Xmx4g"

sudo apt-get update
sudo apt-get -y install python3-venv

python3 -m venv env
source env/bin/activate
python -m pip install --upgrade pip

# Install opensearch benchmark
pip install opensearch-benchmark
opensearch-benchmark -h

sudo apt-get -y install openjdk-17-jdk-headless
update-alternatives --list java
export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64/"

sudo sysctl -w vm.max_map_count=262144
sudo sysctl -p

# Install opensearch (might not be needed)
sudo apt-get -y install lsb-release ca-certificates curl gnupg2
curl -o- https://artifacts.opensearch.org/publickeys/opensearch.pgp | sudo gpg --dearmor --batch --yes -o /usr/share/keyrings/opensearch-keyring
echo "deb [signed-by=/usr/share/keyrings/opensearch-keyring] https://artifacts.opensearch.org/releases/bundle/opensearch/2.x/apt stable main" | sudo tee /etc/apt/sources.list.d/opensearch-2.x.list

sudo apt-get update
sudo apt list -a opensearch
sudo env OPENSEARCH_INITIAL_ADMIN_PASSWORD="$OS_PASSWORD" apt-get -y install opensearch=2.16.0

# add user to opensearch group so they can read the config files
sudo adduser $(whoami) opensearch
# Modify configuration files https://opensearch.org/docs/latest/install-and-configure/install-opensearch/debian/#step-3-set-up-opensearch-in-your-environment
echo "Modifying: /etc/opensearch/opensearch.yml"
echo "### Begin user configuration ###" | sudo tee -a /etc/opensearch/opensearch.yml
echo "discovery.type: single-node" | sudo tee -a /etc/opensearch/opensearch.yml
echo "plugins.security.disabled: false" | sudo tee -a /etc/opensearch/opensearch.yml
sudo sed -i -e "/network.host:/c\network.host: $CLUSTER_IP # user modified" /etc/opensearch/opensearch.yml
echo "### End user configuration ###" | sudo tee -a /etc/opensearch/opensearch.yml

echo "Modifying: /etc/opensearch/jvm.options"
sudo sed -i -e "s/^-Xms[0-9a-z]*$/$JVM_MIN_HEAP/g" /etc/opensearch/jvm.options
sudo sed -i -e "s/^-Xmx[0-9a-z]*$/$JVM_MAX_HEAP/g" /etc/opensearch/jvm.options

sudo systemctl daemon-reload
sudo systemctl enable opensearch.service
sudo systemctl start opensearch.service
sudo systemctl status --no-pager opensearch.service

apt show opensearch

curl -X GET https://$CLUSTER_IP:9200 -u "admin:$OS_PASSWORD" --insecure
curl -X GET https://$CLUSTER_IP:9200/_cat/plugins?v -u "admin:$OS_PASSWORD" --insecure

# Test OSB (check for errors)
opensearch-benchmark execute-test --distribution-version=2.16.0 --workload=big5 --workload-params corpus_size:100,number_of_replicas:0,target_throughput:"" --test-mode

# stop opensearch service
sudo systemctl restart opensearch
