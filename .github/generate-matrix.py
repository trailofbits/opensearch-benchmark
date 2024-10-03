import json
import sys

workloads = sys.argv[1].split(',')
workload_params = sys.argv[2]
test_procedure = sys.argv[3]
cluster_types = sys.argv[4].split(',')

includes = [
    {
      "workload_params": workload_params
    },
    {
      "test_procedure": test_procedure
    }
]

if "OpenSearch" in cluster_types:
    includes = [
        {
            "cluster_type": "OpenSearch",
            "s3_bucket_name": "os-snapshots-osb"
        }
    ] + includes
if "ElasticSearch" in cluster_types:
    includes = [
        {
            "cluster_type": "ElasticSearch",
            "s3_bucket_name": "es-snapshots-osb"
        }
    ] + includes

output = {
  "cluster_type": cluster_types,
  "workload": workloads,
  "include": includes,
}
print(json.dumps(output))
