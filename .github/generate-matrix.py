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
            "workload_params": str(json.dumps(params)),
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

if "vectorsearch-faiss" in workloads or "vectorsearch" in workloads:
    params = {
        "target_index_name": "target_index",
        "target_field_name": "target_field",
        "target_index_body": "indices/faiss-index.json",
        "target_index_primary_shards": 3,
        "target_index_dimension": 768,
        "target_index_space_type": "innerproduct",

        "target_index_bulk_size": 100,
        "target_index_bulk_index_data_set_format": "hdf5",
        "target_index_bulk_index_data_set_corpus": "cohere-1m",
        "target_index_bulk_indexing_clients": 10,

        "target_index_max_num_segments": 1,
        "hnsw_ef_search": 256,
        "hnsw_ef_construction": 256,

        "query_k": 100,
        "query_body": {
            "docvalue_fields" : ["_id"],
            "stored_fields" : "_none_"
        },

        "query_data_set_format": "hdf5",
        "query_data_set_corpus": "cohere-1m",
        "query_count": 10000
        # TODO support user-specified workload params
    }
    includes = [
        {
            "name": "vectorsearch-faiss",
            "workload": "vectorsearch",
            "workload_params": str(json.dumps(params)),
            "benchmark_type": "dev",
        }
    ] + includes

if "vectorsearch-lucene" in workloads or "vectorsearch" in workloads:
    params = {
        "target_index_name": "target_index",
        "target_field_name": "target_field",
        "target_index_body": "indices/lucene-index.json",
        "target_index_primary_shards": 3,
        "target_index_dimension": 768,
        "target_index_space_type": "innerproduct",

        "target_index_bulk_size": 100,
        "target_index_bulk_index_data_set_format": "hdf5",
        "target_index_bulk_index_data_set_corpus": "cohere-1m",
        "target_index_bulk_indexing_clients": 10,

        "target_index_max_num_segments": 1,
        "hnsw_ef_search": 256,
        "hnsw_ef_construction": 256,

        "query_k": 100,
        "query_body": {
            "docvalue_fields" : ["_id"],
            "stored_fields" : "_none_"
        },

        "query_data_set_format": "hdf5",
        "query_data_set_corpus": "cohere-1m",
        "query_count": 10000
        # TODO support user-specified workload params
    }
    includes = [
        {
            "name": "vectorsearch-lucene",
            "workload": "vectorsearch",
            "workload_params": str(json.dumps(params)),
            "benchmark_type": "dev",
        }
    ] + includes

includes = [
    {
      "workload_params": str(json.dumps(workload_params))
    }
] + includes

output = {
  "cluster_type": cluster_types,
  "workload": workloads,
  "include": includes,
}
print(json.dumps(output))
