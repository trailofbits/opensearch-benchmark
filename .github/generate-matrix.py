"""Script to generate the matrix for the GitHub Workflow"""

from pathlib import Path
import json
import sys
import logging

logger = logging.getLogger(__name__)

WORKLOAD_NAME_MAP = {
    "vectorsearch-faiss": "vectorsearch",
    "vectorsearch-lucene": "vectorsearch",
    "vectorsearch-nmslib": "vectorsearch",
}

DEFAULT_EXTRA_PARAMS = {
    "noaa": {
        "test_procedure": "aggs",
    },
    "noaa_semantic_search": {
        "test_procedure": "hybrid-query-aggs-no-index",
    },
}

OS_ONLY_WORKLOADS = {"vectorsearch-faiss", "vectorsearch-nmslib"}

def get_available_cluster_types(cluster_types: list[str]) -> list[str]:
    """Get the cluster types"""
    return [
        cluster_type
        for cluster_type in ["OpenSearch", "ElasticSearch"]
        if cluster_type.lower() in (x.lower() for x in cluster_types)
    ]


def _cluster_part(cluster_type: str) -> str:
    return "es" if cluster_type.lower() == "elasticsearch" else "os"


def get_workload_params(
    cluster_type: str, version: str, workload_name: str, overwrite_workload_params: dict
) -> dict | None:
    """Generate the workload parameters"""
    cluster_part = _cluster_part(cluster_type)
    if f"{workload_name}-{cluster_part}-{version}" in overwrite_workload_params:
        return overwrite_workload_params.get(f"{workload_name}-{cluster_part}-{version}", {})
    elif f"{workload_name}-{cluster_part}" in overwrite_workload_params:
        return overwrite_workload_params.get(f"{workload_name}-{cluster_part}", {})
    elif workload_name in overwrite_workload_params:
        return overwrite_workload_params.get(workload_name, {})
    else:
        return read_default_workload_params(cluster_type, workload_name)


def read_default_workload_params(cluster_type: str, workload_name: str) -> dict | None:
    """Read the default workload parameters"""
    # Get the script path (with Path)
    script_path = Path(__file__).parent.resolve()
    workload_params_path = script_path / "../infra/workload_params_default/"
    cluster_part = _cluster_part(cluster_type)
    if (workload_params_path / f"{workload_name}.json").exists():
        return json.load(open(workload_params_path / f"{workload_name}.json"))
    elif (workload_params_path / f"{workload_name}-{cluster_part}.json").exists():
        return json.load(
            open(workload_params_path / f"{workload_name}-{cluster_part}.json")
        )
    else:
        return None


def main() -> None:
    workloads = [x.lower() for x in sys.argv[1].split(",")]
    overwrite_workload_params = json.loads(sys.argv[2])
    cluster_types = sys.argv[3].split(",")
    os_versions = sys.argv[4].split(",")
    es_versions = sys.argv[5].split(",")
    benchmark_type = sys.argv[6]

    if not all(
        x in ["opensearch", "elasticsearch"] for x in [x.lower() for x in cluster_types]
    ):
        print("Invalid cluster type. Must be one of: OpenSearch, ElasticSearch")
        sys.exit(1)

    if not all(x in ["dev", "official"] for x in [benchmark_type]):
        print("Invalid benchmark type. Must be one of: dev, official")
        sys.exit(1)

    cluster_versions = {
        "OpenSearch": ("os_version", os_versions),
        "ElasticSearch": ("es_version", es_versions),
    }

    includes = []

    # vectorsearch refers to vectorsearch-faiss, vectorsearch-lucene, and vectorsearch-nmslib
    if "vectorsearch" in workloads:
        workloads = [x for x in workloads if x != "vectorsearch"] + [
            "vectorsearch-faiss",
            "vectorsearch-lucene",
            "vectorsearch-nmslib",
        ]

    for workload_name in workloads:
        for cluster_type in get_available_cluster_types(cluster_types):
            # skip OS-only workloads for ES
            if cluster_type == "ElasticSearch" and workload_name in OS_ONLY_WORKLOADS:
                continue
            extra_params = DEFAULT_EXTRA_PARAMS.get(workload_name, {})
            workflow_benchmark_type = (
                "dev" if workload_name.startswith("vectorsearch") else benchmark_type
            )
            workload = WORKLOAD_NAME_MAP.get(workload_name, workload_name)
            version_key, versions = cluster_versions[cluster_type]

            # We should still set the os_version even for ES because it is used
            # to determine the distribution_version in OSB
            os_version = os_versions[0] if os_versions else "2.18.0"
            if version_key != cluster_versions["OpenSearch"][0]:
                extra_params["os_version"] = os_version

            for version in versions:
                params = get_workload_params(
                    cluster_type, version, workload_name, overwrite_workload_params
                )
                if params is None:
                    logger.warning(
                        f"Workload parameters not found for {cluster_type}/{version}/{workload_name}"
                    )
                    continue

                includes.append(
                    {
                        "name": workload_name,
                        "cluster_type": cluster_type,
                        version_key: version,
                        "workload": workload,
                        "workload_params": str(json.dumps(params)),
                        "benchmark_type": workflow_benchmark_type,
                        **extra_params,
                    }
                )

    output = {
        "include": includes,
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
