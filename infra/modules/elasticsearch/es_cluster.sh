#!/bin/bash

USER=ubuntu

if [ $UID -eq 0 ]; then
  exec sudo -u "$USER" "$0" "$@"
  # nothing will be executed from root beyond that line,
  # because exec replaces running process with the new one
fi

ELASTIC_PASSWORD=$1
cd /mnt || exit 1


sudo apt update && sudo -E DEBIAN_FRONTEND=noninteractive apt install -y socat

wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.15.0-linux-x86_64.tar.gz
wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.15.0-linux-x86_64.tar.gz.sha512
shasum -a 512 -c elasticsearch-8.15.0-linux-x86_64.tar.gz.sha512
tar -xzf elasticsearch-8.15.0-linux-x86_64.tar.gz
cd elasticsearch-8.15.0/ || exit 1

cat <<EOF > config/elasticsearch.yml
discovery.type: single-node
network.host: 0.0.0.0 # set this as appropriate
path.repo: ["/mnt/es-backup"]
path.data: /mnt/es-data
path.logs: /mnt/es-logs
EOF

sudo mkdir /mnt/es-backup && sudo chmod ugo+rwx /mnt/es-backup
sudo mkdir /mnt/es-data && sudo chmod ugo+rwx /mnt/es-data
sudo mkdir /mnt/es-logs && sudo chmod ugo+rwx /mnt/es-logs

# Open ports on firewall
sudo ufw allow 9200/tcp
sudo ufw allow 9300/tcp

# Start Elasticsearch
./bin/elasticsearch -d -p /mnt/es_pid

# Wait for Elasticsearch to start
while ! curl --max-time 5 -ks https://localhost:9200 2>&1 >/dev/null ; do
    echo "Waiting for Elasticsearch to start"
    sleep 1
done 

# Reset password to a known value
CURRENT_ELASTIC_PASSWORD=$(./bin/elasticsearch-reset-password -u elastic -b -s)
curl -ku elastic:$CURRENT_ELASTIC_PASSWORD https://localhost:9200

echo "Current: $CURRENT_ELASTIC_PASSWORD , New: $ELASTIC_PASSWORD"

curl -k -X POST "https://localhost:9200/_security/user/elastic/_password" -u elastic:$CURRENT_ELASTIC_PASSWORD -H "Content-Type: application/json" -d "{
  \"password\": \"$ELASTIC_PASSWORD\"
}"

curl -ku elastic:$ELASTIC_PASSWORD https://localhost:9200
