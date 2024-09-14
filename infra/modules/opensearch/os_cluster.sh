#!/bin/bash

USER=ubuntu

if [ $UID -eq 0 ]; then
  exec sudo -u "$USER" "$0" "$@"
  # nothing will be executed from root beyond that line,
  # because exec replaces running process with the new one
fi

OS_PASSWORD=$1
OS_VERSION=$2

INSTALL_ROOT=/mnt/opensearch
INSTALL_PATH=$INSTALL_ROOT/opensearch-$OS_VERSION
INSTALL_FILENAME=opensearch-$OS_VERSION-linux-x64.tar.gz
DOWNLOAD_URL=https://artifacts.opensearch.org/releases/bundle/opensearch/$OS_VERSION/$INSTALL_FILENAME
CONFIG_FILE=$INSTALL_PATH/config/opensearch.yml
JVM_CONFIG=$INSTALL_PATH/config/jvm.options

cd $HOME

# Ensure map count is the expected
# TODO: This won't survive a reboot. Consider persisting to /etc/sysctl.conf
sudo sysctl -w vm.max_map_count=262144

# Disable swap
sudo swapoff -a

#Download and install OpenSearch 2.16.0 then remove installer
mkdir -p $INSTALL_PATH
wget $DOWNLOAD_URL
tar -xvf $INSTALL_FILENAME -C $INSTALL_ROOT
ls -la $INSTALL_PATH > a.tmp
rm $INSTALL_FILENAME

# Update the configuration to allow incoming connections
sed -i "s/#network.host: .*/network.host: 0.0.0.0/" $CONFIG_FILE 
echo "discovery.type: single-node" >> $CONFIG_FILE

touch b
# JDK location
export OPENSEARCH_JAVA_HOME=$INSTALL_PATH/jdk
echo "export OPENSEARCH_JAVA_HOME=$$OPENSEARCH_JAVA_HOME" >> ~/.bashrc

touch c
# Fix the JVM size
GB=$(echo "$(cat /proc/meminfo | grep MemTotal | awk '{print $2}') / (1024*1024*2)" | bc)
sed -i "s/-Xms1g/-Xms${GB}g/" $JVM_CONFIG
sed -i "s/-Xmx1g/-Xmx${GB}g/" $JVM_CONFIG
touch d

# Open firewall ports
sudo ufw allow 9200/tcp
sudo ufw allow 9300/tcp

touch e
# Run opensearch startup script with security demo configuration
OPENSEARCH_INITIAL_ADMIN_PASSWORD=$OS_PASSWORD $INSTALL_PATH/opensearch-tar-install.sh &> opensearch.log &
SERVER_PID=$!

touch f
echo "Waiting for server to boot"

echo "Waiting for server to boot"
# Wait for OpenSearch to start
while ! curl --max-time 5 -ks https://localhost:9200 2>&1 >/dev/null ; do
    touch g
    echo "Waiting for OpenSearch to start"
    sleep 1
done 
touch h

echo "OpenSearch responds on port 9200, now verify credentials"
curl -X GET https://localhost:9200 -u "admin:$OS_PASSWORD" --insecure || (echo "Failed to query server" && false)
echo
echo "Server up and running (pid $SERVER_PID)"
# kill $SERVER_PID

# cd /mnt || exit 1


#sudo apt update && sudo -E DEBIAN_FRONTEND=noninteractive apt install -y socat