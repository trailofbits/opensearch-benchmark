"""Helpers for downloading batches of benchmark results from an OpenSearch datastore."""

import csv
import itertools
import json
import logging
from collections.abc import Collection, Mapping
from datetime import datetime
from enum import Enum
from operator import attrgetter
from pathlib import Path
from typing import TYPE_CHECKING, Any

from opensearchpy import OpenSearch
from opensearchpy.transport import Transport

if TYPE_CHECKING:
    import _csv
    from io import TextIOWrapper

logger = logging.getLogger(__name__)


FIELDS_SORT_PRIORITY = [
    "RunGroup",
    "Engine",
    "EngineVersion",
    "Environment",
    "SnapshotBucket",
    "SnapshotBasePath",
    "Workload",
    "WorkloadSubType",
    "TestProcedure",
    "Run",
    "MetricName",
]


class BenchmarkResult:
    """Store a single row's data from a benchmark run."""

    def __init__(  # noqa: PLR0913
        self,
        run_group: datetime,
        engine: str,
        engine_version: str,
        environment: str,
        benchmark_source: str,
        run: str,
        snapshot_bucket: str,
        snapshot_base_path: str,
        workload: str,
        workload_subtype: str,
        test_procedure: str,
        workload_params: dict[str, str],
        shard_count: int,
        replica_count: int,
        operation: str,
        metric_name: str,
        p50: str,
        p90: str,
    ) -> None:
        self.RunGroup: datetime = run_group
        self.Engine = engine
        self.EngineVersion = engine_version
        self.Environment = environment
        self.BenchmarkSource = benchmark_source
        self.Run = run
        self.SnapshotBucket = snapshot_bucket
        self.SnapshotBasePath = snapshot_base_path
        self.Workload = workload
        self.WorkloadSubType = workload_subtype
        self.TestProcedure = test_procedure
        self.WorkloadParams = workload_params
        self.ShardCount = shard_count
        self.ReplicaCount = replica_count
        self.Operation = operation
        self.MetricName = metric_name
        self.P50 = p50
        self.P90 = p90


class VerboseTransport(Transport):
    """Extend the Transport class to log information about the request."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Set up logging
        self.Logger = logger
        super().__init__(*args, **kwargs)

    def perform_request(  # noqa: D102, PLR0913
        self,
        method: str,
        url: str,
        params: Mapping[str, Any] | None = None,
        body: Any = None,
        timeout: float | None = None,
        ignore: Collection = (),
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        # Log the request details
        self.Logger.info(f"Request Method: {method}")
        self.Logger.info(f"Request URL: {url}")
        self.Logger.info(f"Request Headers: {headers}")
        self.Logger.info(f"Request Params: {params}")
        if body:
            self.Logger.info(f"Request Body: {json.dumps(body, indent=2)}")

        self.Logger.info(f"Hosts: {self.hosts}")

        # Perform the actual request
        return super().perform_request(method, url, params, body, timeout, ignore, headers)


class Source(Enum):
    """Sources of benchmark data."""

    Scheduled = "scheduled"
    Manual = "manual"
    Other = "not-used"


def download(  # noqa: PLR0913
    *,
    start_date: datetime,
    end_date: datetime,
    host: str,
    port: int = 443,
    password: str,
    environment: str = "",
    run_type: str = "official",
    engine_type: str | None,
    distribution_version: str | None,
    sources: list[Source],
) -> list[BenchmarkResult]:
    """Download the specified benchmark results."""
    if start_date > end_date:
        msg = f"Wrong date range. start date {start_date} is after end date {end_date}."
        raise ValueError(msg)

    query: dict[str, Any] = {
        "query": {
            "bool": {
                "must": [
                    {
                        "range": {
                            "test-execution-timestamp": {
                                "gte": start_date.isoformat(timespec="seconds"),
                                "lte": end_date.isoformat(timespec="seconds"),
                                "format": "strict_date_time_no_millis",
                            }
                        }
                    },
                    {"prefix": {"environment": {"value": environment}}},
                    {"terms": {"user-tags.run-type": [run_type]}},
                    {"exists": {"field": "operation"}},
                    {"exists": {"field": "value.50_0"}},
                    {"exists": {"field": "value.90_0"}},
                    {"exists": {"field": "user-tags.run-group"}},
                    {"exists": {"field": "user-tags.run"}},
                    {"exists": {"field": "user-tags.engine-type"}},
                    {"exists": {"field": "user-tags.shard-count"}},
                    {"exists": {"field": "user-tags.replica-count"}},
                ],
            },
        },
    }

    if engine_type is not None:
        query["query"]["bool"]["must"].append({"term": {"user-tags.engine-type": {"value": engine_type}}})

    if distribution_version is not None:
        query["query"]["bool"]["must"].append({"term": {"distribution-version": {"value": distribution_version}}})

    query["query"]["bool"].update(_build_source_query(sources))

    transport_class = VerboseTransport if logger.isEnabledFor(logging.DEBUG) else Transport

    client = OpenSearch(
        hosts=[{"host": host, "port": port}],
        http_compress=True,
        http_auth=("admin", password),
        use_ssl=True,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
        transport_class=transport_class,
    )

    response = client.count(body=query)
    logger.debug(json.dumps(response))

    documents_count = response["count"]
    logger.info(f"Found {documents_count} documents to download")

    if documents_count == 0:
        return []

    # Request batches of 10000 documents, which is the maximum
    query.update({"size": 10000})

    results: list[BenchmarkResult] = []

    # If we have less than 10000 documents use the normal search
    if documents_count < 10000:  # noqa: PLR2004
        response = client.search(body=query, index="benchmark-results*")
        results = _handle_results_response(response)
    else:
        # Otherwise use the scroll request
        response = client.search(body=query, scroll="1m", index="benchmark-results*")
        results = _handle_results_response(response)
        pagination_id = response["_scroll_id"]
        while len(response["hits"]["hits"]) > 0:
            response = client.scroll(scroll_id=pagination_id, scroll="1m")
            results += _handle_results_response(response)

    results_count = len(results)
    logger.info(f"Received {results_count} results")

    sorted_benchmark_results: list[BenchmarkResult] = sorted(results, key=attrgetter(*FIELDS_SORT_PRIORITY))

    return sorted_benchmark_results


def _build_source_query(sources: list[Source]) -> dict[str, Any]:
    should_clauses: list[dict[str, Any]] = []

    if Source.Other in sources:
        # user-tags.ci not exists OR
        should_clauses.append(
            {"bool": {"must_not": {"exists": {"field": "user-tags.ci"}}}},
        )

    should_clauses.append({"terms": {"user-tags.ci": [source.value for source in sources]}})

    return {"should": should_clauses, "minimum_should_match": 1}


def _handle_results_response(
    response: Any,
) -> list[BenchmarkResult]:
    if response is None:
        msg = "Failed to get results"
        raise ValueError(msg)

    hits = response.get("hits")

    if hits is None:
        msg = "Failed to find the top hits key"
        raise ValueError(msg)

    documents = hits.get("hits")

    if documents is None:
        msg = "Failed to get any documents"
        raise ValueError(msg)

    logger.debug(f"Documents: {len(documents)}")
    logger.debug("%s", json.dumps(response))

    results = []
    for document in documents:
        source = document["_source"]
        engine_version = source["distribution-version"]
        environment = source["environment"]
        workload = source["workload"]
        operation = source["operation"]
        metric_name = source["name"]
        metric_value = source["value"]
        test_procedure = source["test_procedure"]
        workload_params_dict = source["workload-params"]
        workload_subtype = workload_params_dict.get("query_data_set_corpus", "")
        p50 = metric_value["50_0"]
        p90 = metric_value["90_0"]
        user_tags = source["user-tags"]
        run = user_tags["run"]
        engine = user_tags["engine-type"]
        run_group_str = user_tags["run-group"]
        shard_count = user_tags["shard-count"]
        replica_count = user_tags["replica-count"]
        snapshot_bucket = user_tags.get("snapshot-s3-bucket")  # optional
        snapshot_base_path = user_tags.get("snapshot-base-path")  # optional

        benchmark_source = user_tags.get("ci")

        if benchmark_source is None:
            # Keep empty to not confuse this with the runs that started setting the tag
            benchmark_source = ""

        # Parse into a proper date for sorting purposes
        run_group_date = datetime.strptime(run_group_str, "%Y_%m_%d_%H_%M_%S")  # noqa: DTZ007

        results.append(
            BenchmarkResult(
                run_group_date,
                engine,
                engine_version,
                environment,
                benchmark_source,
                run,
                snapshot_bucket,
                snapshot_base_path,
                workload,
                workload_subtype,
                test_procedure,
                workload_params_dict,
                shard_count,
                replica_count,
                operation,
                metric_name,
                p50,
                p90,
            )
        )

    return results


def dump_csv_files(results: list[BenchmarkResult], folder: Path) -> None:
    """Dump benchmark results to csv files in the specified folder."""
    sorted_benchmark_results: list[BenchmarkResult] = sorted(results, key=attrgetter(*FIELDS_SORT_PRIORITY))

    all_workload_params_names_set = set()
    for result in results:
        for workload_param in result.WorkloadParams:
            all_workload_params_names_set.add(f"workload\\.{workload_param}")
    all_workload_params_names = list(all_workload_params_names_set)

    workload_params_name_to_pos = {}
    for index in range(len(all_workload_params_names)):
        workload_params_name_to_pos[all_workload_params_names[index]] = index

    # These pre and post headers exists to support a dynamic number of columns
    # of workload params which will be placed in between
    headers_pre = [
        "user-tags\\.run-group",
        "environment",
        "user-tags\\.ci",
        "user-tags\\.engine-type",
        "distribution-version",
        "user-tags\\.snapshot-s3-bucket",
        "user-tags\\.snapshot-base-path",
        "workload",
        "test-procedure",
    ]

    headers_post = [
        "user-tags\\.shard-count",
        "user-tags\\.replica-count",
        "user-tags\\.run",
        "operation",
        "name",
        "value\\.50_0",
        "value\\.90_0",
    ]

    current_run_group: datetime | None = None
    current_engine: str | None = None
    current_engine_version: str | None = None
    current_workload: str | None = None
    current_workload_subtype: str | None = None
    current_test_procedure: str | None = None
    csv_file: TextIOWrapper | None = None
    csv_writer: _csv._writer | None = None

    all_workload_params_len = len(all_workload_params_names)
    for result in sorted_benchmark_results:
        new_run_group = result.RunGroup
        new_engine = result.Engine
        new_engine_version = result.EngineVersion
        new_workload = result.Workload
        new_workload_subtype = result.WorkloadSubType
        new_test_procedure = result.TestProcedure

        # Every time any of these columns changes values, we open a new file.
        # This is given the sorting of fields in fields_sort_priority,
        # which guarantees we should not find results from the same batch later.
        if (
            current_run_group != new_run_group
            or current_engine != new_engine
            or current_engine_version != new_engine_version
            or current_workload != new_workload
            or current_workload_subtype != new_workload_subtype
            or current_test_procedure != new_test_procedure
        ):
            current_run_group = new_run_group
            current_engine = new_engine
            current_engine_version = new_engine_version
            current_workload = new_workload
            current_workload_subtype = new_workload_subtype
            current_test_procedure = new_test_procedure

            if csv_file is not None:
                csv_file.close()
            csv_file_path = (
                folder / f"{current_run_group.strftime("%Y-%m-%dT%H%M%SZ")}-{current_engine}"
                f"-{current_engine_version}-{current_workload}-{current_workload_subtype}-{current_test_procedure}.csv"
            )
            csv_file = csv_file_path.open("w", newline="")
            csv_writer = csv.writer(csv_file, delimiter=",", quotechar='"')
            headers = itertools.chain(headers_pre, all_workload_params_names, headers_post)
            csv_writer.writerow(headers)

        values_pre = [
            result.RunGroup,
            result.Environment,
            result.BenchmarkSource,
            result.Engine,
            result.EngineVersion,
            result.SnapshotBucket,
            result.SnapshotBasePath,
            result.Workload,
            result.TestProcedure,
        ]
        values_post = [
            result.ShardCount,
            result.ReplicaCount,
            result.Run,
            result.Operation,
            result.MetricName,
            result.P50,
            result.P90,
        ]

        # Ensure the size is equal to the list of all workload params we encountered
        workload_params_values = [""] * all_workload_params_len

        # Then match the workload param name to the correct column position
        for key, value in result.WorkloadParams.items():
            workload_params_values[workload_params_name_to_pos[f"workload\\.{key}"]] = value

        values = itertools.chain(values_pre, workload_params_values, values_post)

        if csv_writer is None:
            msg = "missing csv writer"
            raise ValueError(msg)
        csv_writer.writerow(values)

    if len(results) > 0:
        logger.info(f"Written all results to {folder}")


def say_download() -> None:
    """Say hello."""
    logger.info("download")
