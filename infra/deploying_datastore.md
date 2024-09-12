# Using an OpenSearch Service as the Metric Datastore
This document describes how to deploy an [OpenSearch Service](https://aws.amazon.com/opensearch-service/) to serve as a datastore for OpenSearch Benchmark.

## Deploying the Datastore
First, deploy a VPC with at least 3 subnets in 3 different Availability Zones. The terraform in this directory deploys 3 additional subnets for the evaluation VPC.

Next, deploy an OpenSearch Service from the AWS web console:
- Select "Create Domain"
- Set and/or confirm the following configuration options:
    - "Standard Create" for Domain Creation Method
    - Production template
    - Select "VPC access" for Network
    - Select "IPV4 only" for IP Address Type
    - Set the VPC to the VPC with the subnets
        - If you are using the terraform it's the same VPC the test cluster is on
    - Select the 3 new subnets you created
        - These subnets should not have other machines using them.
    - Add the VPC's security group
        - Note the security group needs to allow HTTPS traffic internally
    - Select "Enable fine-grained access control" for Fine-grained Access Control
    - Create a master user
    - Select "Do not set domain level access policy" for Access Policy
- Deploy the domain
### Check the connection
- Port forward the OpenSearch service
ssh ubuntu@aws-load-gen -N -L 8443:OPENSEARCH_SERVICE_HOSTNAME:443
- open https://localhost:8443/_dashboards
- Accept the security warning and login as the master user
## Connecting to the Datastore from OSB
- Optional: create a new user in OpenSearch Service for OSB
    - User requires some permissions
    - Shortcut is to give the new user the `all_access` role, slightly less permissioned than admin.
- update ~/.benchmark/benchmark.ini
```
[results_publishing]
datastore.type = opensearch
datastore.host = OPENSEARCH_SERVICE_HOSTNAME
datastore.port = 443
datastore.secure = True
datastore.user = OPENSEARCH_USER
datastore.password = OPENSEARCH_PASSWORD
```
- run OSB
```
opensearch-benchmark execute-test \
    --distribution-version="2.16.0" \
    --pipeline=from-distribution \
    --workload=big5 \
    --workload-params corpus_size:100,number_of_replicas:0,target_throughput:"" \
    --test-mode
```
- check the dashboard to see if data was ingested
