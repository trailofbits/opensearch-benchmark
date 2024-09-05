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
# Does not install JDK (osb dependency for deploying opensearch clusters)
pip install opensearch-benchmark
opensearch-benchmark -h
