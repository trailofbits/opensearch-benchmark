#!/bin/bash

CLUSTER_PASSWORD=$1
CLUSTER_VERSION=$2
CLUSTER_ARCH=$3
OS_SNAPSHOT_AWS_ACCESS_KEY_ID=$4
OS_SNAPSHOT_AWS_SECRET_ACCESS_KEY=$5
CLUSTER_IPS=$6
NODE_NAME=$7
NODES_TYPE=$8

INSTALL_ROOT=/mnt/opensearch
INSTALL_PATH=$INSTALL_ROOT/opensearch-$CLUSTER_VERSION
INSTALL_FILENAME=opensearch-$CLUSTER_VERSION-linux-$CLUSTER_ARCH.tar.gz
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
network.host: 0.0.0.0
node.name: $NODE_NAME
path.repo: ["/mnt/backup"]
path.data: /mnt/data
path.logs: /mnt/logs
s3.client.default.region: us-east-1
EOF

if [[ "$NODES_TYPE" == "multi" ]]; then
    # multi-node settings
    cat <<EOF >> $CONFIG_FILE
cluster.initial_cluster_manager_nodes: main-node
discovery.seed_hosts: [$CLUSTER_IPS]
EOF
else
    # single node settings
    echo "discovery.type: single-node" >> $CONFIG_FILE
fi

cp /mnt/jvm.options $JVM_CONFIG

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

# Manually run security demo config to modify it
OPENSEARCH_INITIAL_ADMIN_PASSWORD=$CLUSTER_PASSWORD bash $INSTALL_PATH/plugins/opensearch-security/tools/install_demo_configuration.sh -y -i -s || exit 1
# Set allowed TLS protocols to fix: https://github.com/opensearch-project/security/issues/3299
echo 'plugins.security.ssl.http.enabled_protocols: ["TLSv1.2"]' >> $CONFIG_FILE

# Run opensearch startup script with security demo configuration
OPENSEARCH_INITIAL_ADMIN_PASSWORD=$CLUSTER_PASSWORD $INSTALL_PATH/opensearch-tar-install.sh &> opensearch.log &
SERVER_PID=$!

# Record the pid
echo $SERVER_PID > /mnt/pid

echo "Waiting for server to boot"
# Wait for OpenSearch to start (break after 20 tries)
tries=0
while ! curl --max-time 5 -ks https://localhost:9200 > /dev/null 2>&1 ; do
    echo "Waiting for OpenSearch to start ($tries)"
    ((tries++))
    sleep $tries
    if [ $tries -eq 20 ]; then
        echo "Failed to start OpenSearch"
        exit 1
    fi
done 

echo "OpenSearch responds on port 9200, now verify credentials"
curl -X GET https://localhost:9200 -u "admin:$CLUSTER_PASSWORD" --insecure || (echo "Failed to query server" && false)
echo

echo "Setting concurrent_segment_search.mode to auto..."
curl -XPUT "https://localhost:9200/_cluster/settings" -u "admin:$CLUSTER_PASSWORD" --insecure -H 'Content-Type: application/json' -d'
{
   "persistent":{
      "search.concurrent_segment_search.mode": "auto"
   }
}
'
echo "Set concurrent_segment_search.mode to auto"

echo "Server up and running (pid $SERVER_PID)"
