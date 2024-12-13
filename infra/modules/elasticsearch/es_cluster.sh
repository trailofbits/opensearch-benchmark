#!/bin/bash

CLUSTER_PASSWORD=$1
CLUSTER_VERSION=$2
CLUSTER_ARCH=$3
ES_SNAPSHOT_AWS_ACCESS_KEY_ID=$4
ES_SNAPSHOT_AWS_SECRET_ACCESS_KEY=$5
CLUSTER_IPS=$6
NODE_NAME=$7
NODES_TYPE=$8

cd /mnt || exit 1

# Install ElasticSearch from .tar.gz
wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-$CLUSTER_VERSION-linux-$CLUSTER_ARCH.tar.gz
wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-$CLUSTER_VERSION-linux-$CLUSTER_ARCH.tar.gz.sha512
shasum -a 512 -c elasticsearch-$CLUSTER_VERSION-linux-$CLUSTER_ARCH.tar.gz.sha512
tar -xzf elasticsearch-$CLUSTER_VERSION-linux-$CLUSTER_ARCH.tar.gz
cd elasticsearch-$CLUSTER_VERSION/ || exit 1
CONFIG_FILE="config/elasticsearch.yml"

cat <<EOF > $CONFIG_FILE
network.host: 0.0.0.0
node.name: $NODE_NAME
path.repo: ["/mnt/backup"]
path.data: /mnt/data
path.logs: /mnt/logs

xpack.security.enabled: true
xpack.security.enrollment.enabled: true

xpack.security.http.ssl.enabled: true
xpack.security.http.ssl.key: es-cert.key
xpack.security.http.ssl.certificate: es-cert.crt

xpack.security.transport.ssl.enabled: true
xpack.security.transport.ssl.key: es-cert.key
xpack.security.transport.ssl.certificate: es-cert.crt
EOF

if [[ "$NODES_TYPE" == "multi" ]]; then
    # multi-node settings
    cat <<EOF >> $CONFIG_FILE
cluster.initial_master_nodes: main-node
discovery.seed_hosts: [$CLUSTER_IPS]
EOF
else
    # single node settings
    echo "discovery.type: single-node" >> $CONFIG_FILE
fi

JVM_CONFIG=config/jvm.options
cp /mnt/jvm.options $JVM_CONFIG

sudo mkdir /mnt/backup && sudo chmod ugo+rwx /mnt/backup
sudo mkdir /mnt/data && sudo chmod ugo+rwx /mnt/data
sudo mkdir /mnt/logs && sudo chmod ugo+rwx /mnt/logs

# Fix the JVM size to 32 GB
GB="32"
sed -i "s/-Xms1g/-Xms${GB}g/" $JVM_CONFIG
sed -i "s/-Xmx1g/-Xmx${GB}g/" $JVM_CONFIG

# Setup SSL Transport across cluster nodes
mv /es-cert.crt config/
mv /es-cert.key config/

# Setup S3 snapshot repository
echo "$ES_SNAPSHOT_AWS_ACCESS_KEY_ID" | ./bin/elasticsearch-keystore add -s -f -x s3.client.default.access_key
echo "$ES_SNAPSHOT_AWS_SECRET_ACCESS_KEY" | bin/elasticsearch-keystore add -s -f -x s3.client.default.secret_key

# Start Elasticsearch
./bin/elasticsearch -d -p /mnt/pid

# Wait for Elasticsearch to start (break after 20 tries)
tries=0
while ! curl --max-time 5 -ks https://localhost:9200 > /dev/null 2>&1 ; do
    echo "Waiting for Elasticsearch to start"
    ((tries++))
    sleep $tries
    if [ $tries -eq 20 ]; then
        echo "Failed to start ElasticSearch"
        exit 1
    fi
done 

# Reset password to a known value
CURRENT_ELASTIC_PASSWORD=$(./bin/elasticsearch-reset-password -u elastic -b -s)
curl -ku elastic:$CURRENT_ELASTIC_PASSWORD https://localhost:9200

echo "Current: $CURRENT_ELASTIC_PASSWORD , New: $CLUSTER_PASSWORD"

curl -k -X POST "https://localhost:9200/_security/user/elastic/_password" -u elastic:$CURRENT_ELASTIC_PASSWORD -H "Content-Type: application/json" -d "{
  \"password\": \"$CLUSTER_PASSWORD\"
}"

curl -ku elastic:$CLUSTER_PASSWORD https://localhost:9200
