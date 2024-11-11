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

DEFAULT_EXTRA_PARAMS = {
    "noaa": {
        "test_procedure": "aggs",
    }
}


def get_available_cluster_types(cluster_types: list[str]) -> list[str]:
    """Get the cluster types"""
    return [
        cluster_type
        for cluster_type in ["OpenSearch", "ElasticSearch"]
        if cluster_type.lower() in (x.lower() for x in cluster_types)
    ]


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

    # vectorsearch refers to both vectorsearch-faiss and vectorsearch-lucene
    if "vectorsearch" in workloads:
        workloads = [x for x in workloads if x != "vectorsearch"] + ["vectorsearch-faiss", "vectorsearch-lucene"]

    for workload in workloads:
        for cluster_type in get_available_cluster_types(cluster_types):
            # vectorsearch workload requires completely different workload params
            params = {} if workload.startswith("vectorsearch") else workload_params
            params.update(DEFAULT_WORKLOAD_PARAMS.get(workload, {}))

            extra_params = DEFAULT_EXTRA_PARAMS.get(workload, {})
            workflow_benchmark_type = "dev" if workload.startswith("vectorsearch") else benchmark_type

            includes.insert(0, {
                "workload": workload,
                "workload_params": str(json.dumps(params)),
                "benchmark_type": workflow_benchmark_type,
                "cluster_type": cluster_type,
                **extra_params,
            })

    output = {
        "include": includes,
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
