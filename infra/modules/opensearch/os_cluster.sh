#!/bin/bash

CLUSTER_PASSWORD=$1
CLUSTER_VERSION=$2

INSTALL_ROOT=/mnt/opensearch
INSTALL_PATH=$INSTALL_ROOT/opensearch-$CLUSTER_VERSION
INSTALL_FILENAME=opensearch-$CLUSTER_VERSION-linux-x64.tar.gz
DOWNLOAD_URL=https://artifacts.opensearch.org/releases/bundle/opensearch/$CLUSTER_VERSION/$INSTALL_FILENAME
CONFIG_FILE=$INSTALL_PATH/config/opensearch.yml
JVM_CONFIG=$INSTALL_PATH/config/jvm.options

cd /mnt || exit 1

#Download and install OpenSearch 2.16.0 then remove installer
mkdir -p $INSTALL_PATH
wget $DOWNLOAD_URL
tar -xvf $INSTALL_FILENAME -C $INSTALL_ROOT
rm $INSTALL_FILENAME

# Update the configuration to allow incoming connections
sed -i "s/#network.host: .*/network.host: 0.0.0.0/" $CONFIG_FILE 
echo "discovery.type: single-node" >> $CONFIG_FILE

# JDK location
export OPENSEARCH_JAVA_HOME=$INSTALL_PATH/jdk
echo "export OPENSEARCH_JAVA_HOME=$OPENSEARCH_JAVA_HOME" >> ~/.bashrc

# Fix the JVM size
GB=$(echo "$(cat /proc/meminfo | grep MemTotal | awk '{print $2}') / (1024*1024*2)" | bc)
sed -i "s/-Xms1g/-Xms${GB}g/" $JVM_CONFIG
sed -i "s/-Xmx1g/-Xmx${GB}g/" $JVM_CONFIG

# Run opensearch startup script with security demo configuration
OPENSEARCH_INITIAL_ADMIN_PASSWORD=$CLUSTER_PASSWORD $INSTALL_PATH/opensearch-tar-install.sh &> opensearch.log &
SERVER_PID=$!

echo "Waiting for server to boot"

echo "Waiting for server to boot"
# Wait for OpenSearch to start
while ! curl --max-time 5 -ks https://localhost:9200 2>&1 >/dev/null ; do
    echo "Waiting for OpenSearch to start"
    sleep 1
done 

echo "OpenSearch responds on port 9200, now verify credentials"
curl -X GET https://localhost:9200 -u "admin:$CLUSTER_PASSWORD" --insecure || (echo "Failed to query server" && false)
echo
echo "Server up and running (pid $SERVER_PID)"
