"""Script to generate the matrix for the GitHub Workflow"""

import json
import sys

DEFAULT_WORKLOAD_PARAMS = {
    "big5": {
        "max_num_segments": 10,
    },
    "vectorsearch-faiss": {
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
        "query_body": {"docvalue_fields": ["_id"], "stored_fields": "_none_"},
        "query_data_set_format": "hdf5",
        "query_data_set_corpus": "cohere-1m",
        "query_count": 10000,
    },
    "vectorsearch-lucene": {
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
        "query_body": {"docvalue_fields": ["_id"], "stored_fields": "_none_"},
        "query_data_set_format": "hdf5",
        "query_data_set_corpus": "cohere-1m",
        "query_count": 10000,
    },
}


def main() -> None:
    workloads = [x.lower() for x in sys.argv[1].split(",")]
    workload_params = json.loads(sys.argv[2])
    cluster_types = sys.argv[3].split(",")
    benchmark_type = sys.argv[4]

    if not all(
        x in ["opensearch", "elasticsearch"] for x in [x.lower() for x in cluster_types]
    ):
        print("Invalid cluster type. Must be one of: OpenSearch, ElasticSearch")
        sys.exit(1)

    if not all(x in ["dev", "official"] for x in [benchmark_type]):
        print("Invalid benchmark type. Must be one of: dev, official")
        sys.exit(1)

    includes = []

    # Setup the right cluster types
    for cluster_type in ["OpenSearch", "ElasticSearch"]:
        if cluster_type.lower() in cluster_types:
            includes.insert(0, {"cluster_type": cluster_type})

    # Associate a name with the workload
    for workload in workloads:
        if not workload.startswith("vectorsearch"):
            includes.insert(0, {"name": workload, "workload": workload})

    # Default to the input benchmark type
    includes.insert(0, {"benchmark_type": benchmark_type})

    # big5 requires extra workload params
    if "big5" in workloads:
        params = {
            **DEFAULT_WORKLOAD_PARAMS.get("big5", {}),
            **workload_params,
        }
        includes.insert(
            0, {"workload": "big5", "workload_params": str(json.dumps(params))}
        )

    # noaa requires a specific test procedure
    if "noaa" in workloads:
        includes.insert(0, {"workload": "noaa", "test_procedure": "aggs"})

    # vectorsearch requires specific workload params
    if "vectorsearch-faiss" in workloads or "vectorsearch" in workloads:
        params = DEFAULT_WORKLOAD_PARAMS.get("vectorsearch-faiss", {})
        includes.insert(
            0,
            {
                "name": "vectorsearch-faiss",
                "workload": "vectorsearch",
                "workload_params": str(json.dumps(params)),
                "benchmark_type": "dev",
            },
        )
    if "vectorsearch-lucene" in workloads or "vectorsearch" in workloads:
        params = DEFAULT_WORKLOAD_PARAMS.get("vectorsearch-lucene", {})
        includes.insert(
            0,
            {
                "name": "vectorsearch-lucene",
                "workload": "vectorsearch",
                "workload_params": str(json.dumps(params)),
                "benchmark_type": "dev",
            },
        )

    includes.insert(0, {"workload_params": str(json.dumps(workload_params))})

    output = {
        "cluster_type": cluster_types,
        "workload": workloads,
        "name": [""],
        "include": includes,
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
