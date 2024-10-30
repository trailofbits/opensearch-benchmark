#!/bin/bash

CLUSTER_PASSWORD=$1
CLUSTER_VERSION=$2
OS_SNAPSHOT_AWS_ACCESS_KEY_ID=$3
OS_SNAPSHOT_AWS_SECRET_ACCESS_KEY=$4

INSTALL_ROOT=/mnt/opensearch
INSTALL_PATH=$INSTALL_ROOT/opensearch-$CLUSTER_VERSION
INSTALL_FILENAME=opensearch-$CLUSTER_VERSION-linux-x64.tar.gz
DOWNLOAD_URL=https://artifacts.opensearch.org/releases/bundle/opensearch/$CLUSTER_VERSION/$INSTALL_FILENAME
CONFIG_FILE=$INSTALL_PATH/config/opensearch.yml
JVM_CONFIG=$INSTALL_PATH/config/jvm.options

cd /mnt || exit 1

# Download and install OpenSearch then remove installer
mkdir -p $INSTALL_PATH
wget $DOWNLOAD_URL
tar -xvf $INSTALL_FILENAME -C $INSTALL_ROOT
rm $INSTALL_FILENAME


# Specify directories for storage and update the configuration to allow incoming connections.
# Also a config that is needed to make the s3 client successfully locate the snapshot bucket
cat <<EOF > $CONFIG_FILE
discovery.type: single-node
network.host: 0.0.0.0
path.repo: ["/mnt/backup"]
path.data: /mnt/data
path.logs: /mnt/logs
s3.client.default.region: us-east-1
EOF

sudo mkdir /mnt/backup && sudo chmod ugo+rwx /mnt/backup
sudo mkdir /mnt/data && sudo chmod ugo+rwx /mnt/data
sudo mkdir /mnt/logs && sudo chmod ugo+rwx /mnt/logs


# JDK location
export OPENSEARCH_JAVA_HOME=$INSTALL_PATH/jdk
echo "export OPENSEARCH_JAVA_HOME=$OPENSEARCH_JAVA_HOME" >> ~/.bashrc

# Fix the JVM size
GB=$(echo "$(cat /proc/meminfo | grep MemTotal | awk '{print $2}') / (1024*1024*2)" | bc)
sed -i "s/-Xms1g/-Xms${GB}g/" $JVM_CONFIG
sed -i "s/-Xmx1g/-Xmx${GB}g/" $JVM_CONFIG

# Install and configure pre-requisites for S3 snapshot buckets
sudo $INSTALL_PATH/bin/opensearch-plugin install -b -s repository-s3
echo "$OS_SNAPSHOT_AWS_ACCESS_KEY_ID" | $INSTALL_PATH/bin/opensearch-keystore add -s -f -x s3.client.default.access_key
echo "$OS_SNAPSHOT_AWS_SECRET_ACCESS_KEY" | $INSTALL_PATH/bin/opensearch-keystore add -s -f -x s3.client.default.secret_key

# Run opensearch startup script with security demo configuration
OPENSEARCH_INITIAL_ADMIN_PASSWORD=$CLUSTER_PASSWORD $INSTALL_PATH/opensearch-tar-install.sh &> opensearch.log &
SERVER_PID=$!

# Record the pid
echo $SERVER_PID > /mnt/pid

echo "Waiting for server to boot"
# Wait for OpenSearch to start
while ! curl --max-time 5 -ks https://localhost:9200 > /dev/null 2>&1 ; do
    echo "Waiting for OpenSearch to start"
    sleep 1
done 

echo "OpenSearch responds on port 9200, now verify credentials"
curl -X GET https://localhost:9200 -u "admin:$CLUSTER_PASSWORD" --insecure || (echo "Failed to query server" && false)
echo
echo "Server up and running (pid $SERVER_PID)"

cd /mnt || exit 1
wget https://github.com/async-profiler/async-profiler/releases/download/v3.0/async-profiler-3.0-linux-x64.tar.gz
tar -xvf async-profiler-3.0-linux-x64.tar.gz
cd async-profiler-3.0-linux-x64 || exit 1
