#!/bin/bash

curl -ku $CLUSTER_USER:$CLUSTER_PASSWORD $CLUSTER_HOST/_stats/store?level=indices
curl -ku $CLUSTER_USER:$CLUSTER_PASSWORD $CLUSTER_HOST/_cat/indices?v\&h=index,store.size,pri.store.size,rep
curl -ku $CLUSTER_USER:$CLUSTER_PASSWORD $CLUSTER_HOST/_cat/shards?v\&h=index,shard,prirep,state,unassigned.reason
