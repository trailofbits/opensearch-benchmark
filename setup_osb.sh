#!/bin/bash
# This script installs OpenSearch Benchmark.
# Usage: bash setup_osb.sh
# Tested on Ubuntu 22.04

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

# Test OSB (check for errors)
opensearch-benchmark execute-test \
    --distribution-version="$OPENSEARCH_VERSION" \
    --pipeline=from-distribution \
    --workload=big5 \
    --workload-params corpus_size:100,number_of_replicas:0,target_throughput:"" \
    --test-mode
