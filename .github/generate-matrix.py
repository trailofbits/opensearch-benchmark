"""Script to generate the matrix for the GitHub Workflow"""

import json
import sys

workloads = [x.lower() for x in sys.argv[1].split(',')]
workload_params = sys.argv[2]
cluster_types = sys.argv[3].split(',')

if not all(x in ["OpenSearch", "ElasticSearch"] for x in cluster_types):
    print("Invalid cluster type. Must be one of: OpenSearch, ElasticSearch")
    sys.exit(1)

includes = []

# OpenSearch requires a specific s3_bucket_name
if "OpenSearch" in cluster_types:
    includes += [
        {
            "cluster_type": "OpenSearch",
            "s3_bucket_name": "os-snapshots-osb"
        }
    ]

# ElasticSearch requires a specific s3_bucket_name
if "ElasticSearch" in cluster_types:
    includes += [
        {
            "cluster_type": "ElasticSearch",
            "s3_bucket_name": "es-snapshots-osb"
        }
    ]

# big5 requires extra workload params
if "big5" in workloads:
    includes += [
        {
            "workload": "big5",
            "workload_params": "max_num_segments:10,index_merge_policy:tiered," + workload_params
        }
    ]

# noaa requires a specific test procedure
if "noaa" in workloads:
    includes += [
        {
            "workload": "noaa",
            "test_procedure": "aggs",
        }
    ]

includes += [
    {
      "workload_params": workload_params
    }
]

output = {
  "cluster_type": cluster_types,
  "workload": workloads,
  "include": includes,
}
print(json.dumps(output))
