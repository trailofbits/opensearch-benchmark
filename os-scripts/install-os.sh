#!/bin/bash

# Installation instructions from https://opensearch.org/docs/latest/install-and-configure/install-opensearch/tar#step-1-download-and-unpack-opensearch


OPENSEARCH_VERSION=2.16.0
INSTALL_ROOT=/mnt/opensearch
INSTALL_PATH=$INSTALL_ROOT/opensearch-$OPENSEARCH_VERSION
INSTALL_FILENAME=opensearch-$OPENSEARCH_VERSION-linux-x64.tar.gz
DOWNLOAD_URL=https://artifacts.opensearch.org/releases/bundle/opensearch/$OPENSEARCH_VERSION/$INSTALL_FILENAME
CONFIG_FILE=$INSTALL_PATH/config/opensearch.yml
JVM_CONFIG=$INSTALL_PATH/config/jvm.options

# Query for an opensearch password
read -s -p "Enter OpenSearch admin password: " password 

mkdir -p $INSTALL_PATH

MAP_COUNT=$(cat /proc/sys/vm/max_map_count)
WANTED_MAP_COUNT=262144
if [ "$MAP_COUNT" != "$WANTED_MAP_COUNT" ]; then
  sudo sh -c "echo \"\n# Increase memory maps for open search\nvm.max_map_count=$WANTED_MAP_COUNT\" >> /etc/sysctl.conf"
  sudo sysctl -p
  MAP_COUNT=$(cat /proc/sys/vm/max_map_count)
  [ "$MAP_COUNT" == "$WANTED_MAP_COUNT" ] || (echo "Map count update failed" && false)
fi

#Download and install OpenSearch 2.16.0 
wget $DOWNLOAD_URL

# Unpack and remove installer
tar -xvf $INSTALL_FILENAME -C $INSTALL_ROOT
rm $INSTALL_FILENAME

# Disable swap
sudo swapoff -a

# Update the configuration to allow incoming connections
sed -i "s/#network.host: .*/network.host: 0.0.0.0/" $CONFIG_FILE 
echo "discovery.type: single-node" >> $CONFIG_FILE

# Fix the JVM size
GB=$(echo "$(cat /proc/meminfo | grep MemTotal | awk '{print $2}') / (1024*1024*2)" | bc)
sed -i "s/-Xms1g/-Xms${GB}g/" $JVM_CONFIG
sed -i "s/-Xmx1g/-Xmx${GB}g/" $JVM_CONFIG

# Open firewall ports
sudo ufw allow 9200/tcp
sudo ufw allow 9300/tcp

# JDK location
export OPENSEARCH_JAVA_HOME=$INSTALL_PATH/jdk


# Run opensearch startup script with security demo configuration
OPENSEARCH_INITIAL_ADMIN_PASSWORD=$password $INSTALL_PATH/opensearch-tar-install.sh &> opensearch.log &
SERVER_PID=$!

echo "Waiting for server to boot"
sleep 60
echo "Attempting query"
curl -X GET https://localhost:9200 -u "admin:$password" --insecure || (echo "Failed to query server" && false)
echo
echo "Server up and running. Stopping it now."
kill $SERVER_PID


