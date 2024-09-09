#!/bin/bash

OPENSEARCH_VERSION=2.16.0
INSTALL_ROOT=/mnt/opensearch
INSTALL_PATH=$INSTALL_ROOT/opensearch-$OPENSEARCH_VERSION

# Query for an opensearch password
read -s -p "Enter OpenSearch admin password: " password 

# JDK location
export OPENSEARCH_JAVA_HOME=$INSTALL_PATH/jdk
OPENSEARCH_INITIAL_ADMIN_PASSWORD=$password $INSTALL_PATH/opensearch-tar-install.sh
