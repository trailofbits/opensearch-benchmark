#!/bin/bash

# built for  Ubuntu 22.04

# Instructions: https://opensearch.org/docs/latest/benchmark/user-guide/installing-benchmark/

OPENSEARCH_VERSION=2.16.0
INSTALL_ROOT=/mnt/opensearch-bench
INSTALL_PATH=$INSTALL_ROOT/opensearch-$OPENSEARCH_VERSION

mkdir -p $INSTALL_ROOT

# Prerequisites
sudo apt update && apt install -y python3-pip openjdk-17-jdk-headless
python3 --version || false
pip --version || false
git --version || false

export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64/

# Benchmark directory
export BENCHMARK_HOME=/mnt/opensearch-bench

pip install opensearch-benchmark

# Make the OpenSearch Benchmark available on the path
export PATH=$PATH:$HOME/.local/bin

# Test a single bench
opensearch-benchmark execute-test --distribution-version=$OPENSEARCH_VERSION --workload=geonames --test-mode


