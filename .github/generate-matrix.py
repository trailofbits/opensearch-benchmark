import json
import sys

workloads = sys.argv[1].split(',')
workload_params = sys.argv[2]
cluster_types = sys.argv[3].split(',')

output = {
  "cluster_type": cluster_types,
  "workload": workloads,
  "include": [
    {
      "cluster_type": "OpenSearch",
      "s3_bucket_name": "os-snapshots-osb"
    },
    {
      "cluster_type": "ElasticSearch",
      "s3_bucket_name": "es-snapshots-osb"
    },
    {
      "workload_params": workload_params
    }
  ]
}
print(json.dumps(output))
