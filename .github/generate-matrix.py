"""Script to generate the matrix for the GitHub Workflow"""

import json
import sys

workloads = [x.lower() for x in sys.argv[1].split(',')]
workload_params = json.loads(sys.argv[2])
cluster_types = sys.argv[3].split(',')

if not all(x in ["OpenSearch", "ElasticSearch"] for x in cluster_types):
    print("Invalid cluster type. Must be one of: OpenSearch, ElasticSearch")
    sys.exit(1)

includes = []

if "OpenSearch" in cluster_types:
    includes = [
        {
            "cluster_type": "OpenSearch",
        }
    ] + includes

if "ElasticSearch" in cluster_types:
    includes = [
        {
            "cluster_type": "ElasticSearch",
        }
    ] + includes

# big5 requires extra workload params
if "big5" in workloads:
    params = {
        "max_num_segments": 10,
        **workload_params,
    }
    includes = [
        {
            "workload": "big5",
            "workload_params": json.dumps(params),
        }
    ] + includes

# noaa requires a specific test procedure
if "noaa" in workloads:
    includes = [
        {
            "workload": "noaa",
            "test_procedure": "aggs",
        }
    ] + includes

includes = [
    {
      "workload_params": workload_params
    }
] + includes

output = {
  "cluster_type": cluster_types,
  "workload": workloads,
  "include": includes,
}
print(json.dumps(output))
