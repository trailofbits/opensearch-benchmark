#!/bin/bash
set -ex

if [ $# -ne 1 ]; then
    echo "Error: Exactly one argument is required."
    echo "Usage: $0 <opensearch_admin_passworrd>"
    exit 1
fi

ADMIN_PASSWORD=$1

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
sudo apt-get update && sudo apt-get -y install lsb-release ca-certificates curl gnupg2
curl -o- https://artifacts.opensearch.org/publickeys/opensearch.pgp | sudo gpg --dearmor --batch --yes -o /usr/share/keyrings/opensearch-keyring
echo "deb [signed-by=/usr/share/keyrings/opensearch-keyring] https://artifacts.opensearch.org/releases/bundle/opensearch/2.x/apt stable main" | sudo tee /etc/apt/sources.list.d/opensearch-2.x.list

sudo apt-get update
sudo apt list -a opensearch
sudo env OPENSEARCH_INITIAL_ADMIN_PASSWORD="$ADMIN_PASSWORD" apt-get -y install opensearch=2.16.0

sudo systemctl daemon-reload
sudo systemctl enable opensearch.service
sudo systemctl start opensearch.service
sudo systemctl status --no-pager opensearch.service

apt show opensearch

curl -X GET https://localhost:9200 -u "admin:$ADMIN_PASSWORD" --insecure
curl -X GET https://localhost:9200/_cat/plugins?v -u "admin:$ADMIN_PASSWORD" --insecure

# Modify opensearch.yml: https://opensearch.org/docs/latest/install-and-configure/install-opensearch/debian/#step-3-set-up-opensearch-in-your-environment
sudo systemctl restart opensearch

# Test OSB (check for errors)
opensearch-benchmark execute-test --distribution-version=2.16.0 --workload=big5 --workload-params corpus_size:100,number_of_replicas:0,target_throughput:"" --test-mode
