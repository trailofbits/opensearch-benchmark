#!/bin/bash

source /mnt/utils.sh

# This comes from the user `terraform.tfvars` configuration file
# shellcheck disable=SC2154
WORKLOAD="$${WORKLOAD:-${workload}}"

# Commands to install specific java-version
CORRETTO=amazon-corretto-21-x64-linux-jdk.deb
ssh ubuntu@$CLUSTER_HOST_SSH "
    wget https://corretto.aws/downloads/latest/$CORRETTO
    sudo apt install -y -f ./$CORRETTO
    export JAVA_HOME=/usr/lib/jvm/java-21-amazon-corretto/
    echo JAVA_HOME=/usr/lib/jvm/java-21-amazon-corretto/ >> ~/.bashrc
    java --version
" || error_exit "Failed to install java"

# Detect if target is elasticsearch, if so get the version. Needed for later changes.
ES_VERSION=$(ssh ubuntu@$CLUSTER_HOST_SSH ls /mnt/ | sed -r  -n "s/elasticsearch-([0-9]+\.[0-9]+\.[0-9]+)$/\1/p")

# Get the workload index path and lucene version
INDEX_NAME=$(workload_index_name $WORKLOAD)
# shellcheck disable=SC2034
INDEX_UUID=$(index_uuid $INDEX_NAME)
echo "Workload $${WORKLOAD}: Index name $${INDEX_NAME}, UUID: $${INDEX_UUID}"
# shellcheck disable=SC2034
INDEX_PATH="\\/mnt\\/data\\/nodes\\/0"
# shellcheck disable=SC2034
LUCENE_VERSION=$(ssh ubuntu@$CLUSTER_HOST_SSH ls /mnt/opensearch/opensearch-*/lib/ | sed -r  -n "s/lucene-core-([0-9]+\.[0-9]+\.[0-9]+).jar$/\1/p")
if [ $ES_VERSION ]; then
    # shellcheck disable=SC2034
    INDEX_PATH="\\/mnt\\/data"
    # shellcheck disable=SC2034
    LUCENE_VERSION=$(ssh ubuntu@$CLUSTER_HOST_SSH ls /mnt/elasticsearch-*/lib/ | sed -r  -n "s/lucene-core-([0-9]+\.[0-9]+\.[0-9]+).jar$/\1/p")
fi


# Build and run the script to extract timestamps.
# Update the path to refer to the current index on disk,
# and take into account column name variation. TODO: Unclear why?
ssh ubuntu@$CLUSTER_HOST_SSH "
    git clone https://github.com/IanHoang/lucene-university.git
    cd lucene-university
    git checkout update-visualize-point-tree-program
    rm src/main/java/example/basic/BottomUpIndexReader.java
    sed -i 's/Path tmpDir = .*/Path tmpDir = Paths.get\\(\"$${INDEX_PATH}\\/indices\\/$${INDEX_UUID}\\/0\\/index\"\\);/' src/main/java/example/points/VisualizePointTree.java
    sed -i 's/PointValues.PointTree pointTree =.*/PointValues pv = lr.getPointValues\\(\"@timestamp\"\\); if \\(pv == null\\) { pv = lr.getPointValues(\"timestamp\");}PointValues.PointTree pointTree = pv.getPointTree\\(\\);/' src/main/java/example/points/VisualizePointTree.java
"

# For ES we need to add additional dependencies
if [ $ES_VERSION ]; then
    echo "
run {
  classpath += files('/mnt/elasticsearch-$${ES_VERSION}/lib/elasticsearch-$${ES_VERSION}.jar', '/mnt/elasticsearch-$${ES_VERSION}/lib/elasticsearch-core-$${ES_VERSION}.jar')
}
" | ssh ubuntu@$CLUSTER_HOST_SSH "cat - >> lucene-university/build.gradle"
fi

ssh ubuntu@$CLUSTER_HOST_SSH "
    cd lucene-university
    ./gradlew build -Dlucene.version=$${LUCENE_VERSION}
    ./gradlew run -PclassToExecute=example.points.VisualizePointTree -Dlucene.version=$${LUCENE_VERSION} > out.txt
" || error_exit "Failed to build and run timestamp extraction"

# Postprocess the timestamps
ssh ubuntu@$CLUSTER_HOST_SSH "
    cd lucene-university
    wget https://raw.githubusercontent.com/IanHoang/opensearch-variance-analysis/refs/heads/main/scripts/lucene-segment-timestamp-parser.py
    sed -i 's/int(date_components\[0\])/int(date_components\[0\])-1/' lucene-segment-timestamp-parser.py
    python3 lucene-segment-timestamp-parser.py --file out.txt
" || error_exit "Failed to postprocess timestamps"

# Get the results file
scp ubuntu@$CLUSTER_HOST_SSH:lucene-university/converted-out.txt segment-timestamps.txt
