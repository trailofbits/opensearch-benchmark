import _csv
import argparse
import csv
import itertools
import json
import logging
import os
from collections.abc import Collection, Mapping
from datetime import datetime
from io import TextIOWrapper
from operator import attrgetter
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from opensearchpy import OpenSearch
from opensearchpy.transport import Transport


class BenchmarkResult:
    def __init__(
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
        test_procedure: str,
        workload_params: dict[str, str],
        shard_count: int,
        replica_count: int,
        operation: str,
        metric_name: str,
        p50: str,
        p90: str,
    ):
        self.RunGroup: datetime = run_group
        self.Engine = engine
        self.EngineVersion = engine_version
        self.Environment = environment
        self.BenchmarkSource = benchmark_source
        self.Run = run
        self.SnapshotBucket = snapshot_bucket
        self.SnapshotBasePath = snapshot_base_path
        self.Workload = workload
        self.TestProcedure = test_procedure
        self.WorkloadParams = workload_params
        self.ShardCount = shard_count
        self.ReplicaCount = replica_count
        self.Operation = operation
        self.MetricName = metric_name
        self.P50 = p50
        self.P90 = p90


class VerboseTransport(Transport):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.Logger = logging.getLogger(__name__)
        super().__init__(*args, **kwargs)

    def perform_request(
        self,
        method: str,
        url: str,
        params: Mapping[str, Any] | None = None,
        body: Any = None,
        timeout: int | float | None = None,
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


def handle_results_response(
    response: Any,
    debug_response: bool,
    results: list[BenchmarkResult],
    all_workload_params_names_set: set[str],
) -> bool:
    if response is None:
        print(f"Failed to get results: { response }")
        return False

    hits = response.get("hits")

    if hits is None:
        print("Failed to find the top hits key")
        return False

    documents = hits.get("hits")

    if documents is None:
        print("Failed to get any documents")
        return False

    if debug_response:
        print(f"Documents: {len(documents)}")
        print(json.dumps(response))

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
        p50 = metric_value["50_0"]
        p90 = metric_value["90_0"]
        user_tags = source["user-tags"]
        run = user_tags["run"]
        engine = user_tags["engine-type"]
        run_group_str = user_tags["run-group"]
        shard_count = user_tags["shard-count"]
        replica_count = user_tags["replica-count"]
        snapshot_bucket = user_tags["snapshot-s3-bucket"]
        snapshot_base_path = user_tags["snapshot-base-path"]

        benchmark_source = user_tags.get("ci")

        if benchmark_source is None:
            # Keep empty to not confuse this with the runs that started setting the tag
            benchmark_source = ""

        # Parse into a proper date for sorting purposes
        run_group_date = datetime.strptime(run_group_str, "%Y_%m_%d_%H_%M_%S")

        for workload_param in workload_params_dict:
            all_workload_params_names_set.add(f"workload\\.{workload_param}")

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

    return True


def benchmark_source_to_tag(source: str) -> str:
    source_to_tag: dict[str, str] = {
        "ci-scheduled": "scheduled",
        "ci-manual": "manual",
        "other": "not-used",
    }

    return source_to_tag[source]


def build_source_query(sources: str) -> dict[str, Any]:
    should_clauses: list[dict[str, Any]] = []

    if "other" in sources:
        # user-tags.ci not exists OR
        should_clauses.append(
            {"bool": {"must_not": {"exists": {"field": "user-tags.ci"}}}},
        )

    # <user-tags.ci == "scheduled"> OR <user-tags.ci == "manual"> OR <user-tags.ci == "not-used">
    source_tag_values: list[str] = []
    for source in sources:
        source_tag_values.append(benchmark_source_to_tag(source))

    should_clauses.append({"terms": {"user-tags.ci": source_tag_values}}),

    return {"should": should_clauses, "minimum_should_match": 1}


def main() -> int:
    args_parser = argparse.ArgumentParser(
        description="Downloads benchmark results from an OpenSearch datastore as CSVs "
        "with the format <run-group>-<engine>-<engine version>-<workload>-<test-procedure>.csv "
        "into a provided folder"
    )

    args_parser.add_argument(
        "--host",
        help="Hostname of the datastore to download the benchmark results from",
        required=True,
        type=str,
    )
    args_parser.add_argument(
        "--port",
        help="Port of the datastore to download the benchmark results from (default: %(default)s)",
        type=int,
        default=443,
    )
    args_parser.add_argument(
        "--benchmark-data",
        help="Path to an existing folder to download the benchmark data to",
        type=Path,
        required=True,
    )
    args_parser.add_argument(
        "--from",
        help="Download results starting from this date (inclusive). "
        "Format is YYYY-MM-DD or YYYY-MM-DD hh:mm:ssZ",
        dest="from_arg",
        type=str,
        required=True,
    )
    args_parser.add_argument(
        "--to",
        help="Download results up to this date (inclusive). "
        "Format is YYYY-MM-DD or YYYY-MM-DD hh:mm:ssZ. Default is now",
        dest="to_arg",
        type=str,
        default=None,
    )
    args_parser.add_argument(
        "--run-type",
        help="Which benchmark data run type (normally dev or official) to download "
        "(default: %(default)s)",
        type=str,
        default="official",
    )
    args_parser.add_argument(
        "--environment",
        help="Which environment prefix to download (default: %(default)s)",
        type=str,
        default="",
    )
    args_parser.add_argument(
        "--source",
        metavar="SOURCE",
        help="Space separated list of sources of the benchmark results. "
        "Can be any combination of ['ci-scheduled', 'ci-manual', 'other'] (default: %(default)s)",
        nargs="+",
        choices=["ci-scheduled", "ci-manual", "other"],
        default=["ci-scheduled"],
    )
    args_parser.add_argument(
        "--debug-request",
        help="Logs in stdout the query request (default: %(default)s)",
        action="store_true",
        default=False,
    )
    args_parser.add_argument(
        "--debug-response",
        help="Logs in stdout the JSON response (default: %(default)s)",
        action="store_true",
        default=False,
    )

    args = args_parser.parse_args()

    password = os.environ.get("DS_PASSWORD")

    if password is None:
        print("Datastore password missing, please pass it as the DS_PASSWORD environment variable")
        return 1

    benchmark_data_folder: Path = args.benchmark_data

    if not benchmark_data_folder.exists():
        print(f"Could not find the provided benchmark data folder at {benchmark_data_folder}")
        return 1

    try:
        start_date_str = args.from_arg
        if "T" not in start_date_str:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(
                tzinfo=ZoneInfo("UTC")
            )
        else:
            start_date = datetime.fromisoformat(start_date_str)
    except ValueError:
        print(
            "Wrong format for the 'from' parameter, "
            "please use a date in YYYY-MM-DD or YYYY-MM-DD hh:mm:ssZ format"
        )
        return 1

    if args.to_arg is None:
        end_date = datetime.now(tz=ZoneInfo("UTC"))
    else:
        try:
            end_date_str = args.to_arg
            if "T" not in end_date_str:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(
                    tzinfo=ZoneInfo("UTC")
                )
            else:
                end_date = datetime.fromisoformat(end_date_str)
        except ValueError:
            print(
                "Wrong format for the 'to' parameter, "
                "please use a date in YYYY-MM-DD or YYYY-MM-DD hh:mm:ssZ format"
            )
            return 1

    if start_date > end_date:
        print("Wrong date range. The date in --from needs to be the same or before the one in --to")
        return 1

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
                    {"prefix": {"environment": {"value": args.environment}}},
                    {"terms": {"user-tags.run-type": [args.run_type]}},
                    {"exists": {"field": "operation"}},
                    {"exists": {"field": "value.50_0"}},
                    {"exists": {"field": "value.90_0"}},
                    {"exists": {"field": "user-tags.run-group"}},
                    {"exists": {"field": "user-tags.run"}},
                    {"exists": {"field": "user-tags.engine-type"}},
                    {"exists": {"field": "user-tags.shard-count"}},
                    {"exists": {"field": "user-tags.replica-count"}},
                    {"exists": {"field": "user-tags.snapshot-base-path"}},
                    {"exists": {"field": "user-tags.snapshot-s3-bucket"}},
                ],
            },
        },
    }

    query["query"]["bool"].update(build_source_query(args.source))

    # Use VerboseTransport to print more information on the request being done
    transport_class = VerboseTransport if args.debug_request else Transport

    client = OpenSearch(
        hosts=[{"host": args.host, "port": args.port}],
        http_compress=True,
        http_auth=("admin", password),
        use_ssl=True,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
        transport_class=transport_class,
    )

    all_workload_params_names_set: set[str] = set()
    all_workload_params_names: list[str] = []
    workload_params_name_to_pos: dict[str, int] = {}
    results: list[BenchmarkResult] = []

    response = client.count(body=query)
    if args.debug_response:
        print(json.dumps(response))

    documents_count = response["count"]

    print(f"Found {documents_count} documents to download")

    if documents_count == 0:
        return 0

    # Request batches of 10000 documents, which is the maximum
    query.update({"size": 10000})

    # If we have less than 10000 documents use the normal search
    if documents_count < 10000:
        response = client.search(body=query, index="benchmark-results*")
        if not handle_results_response(
            response, args.debug_response, results, all_workload_params_names_set
        ):
            return 1
    else:
        # Otherwise use the scroll request
        response = client.search(body=query, scroll="1m", index="benchmark-results*")
        if not handle_results_response(
            response, args.debug_response, results, all_workload_params_names_set
        ):
            return 1
        pagination_id = response["_scroll_id"]

        while len(response["hits"]["hits"]) > 0:
            response = client.scroll(scroll_id=pagination_id, scroll="1m")
            if not handle_results_response(
                response, args.debug_response, results, all_workload_params_names_set
            ):
                return 1

    results_count = len(results)
    print(f"Received {results_count} results")

    all_workload_params_names = list(all_workload_params_names_set)

    for index in range(len(all_workload_params_names)):
        workload_params_name_to_pos[all_workload_params_names[index]] = index

    fields_sort_priority = [
        "RunGroup",
        "Engine",
        "EngineVersion",
        "Environment",
        "SnapshotBucket",
        "SnapshotBasePath",
        "Workload",
        "TestProcedure",
        "WorkloadParams",
        "Run",
        "MetricName",
    ]
    sorted_benchmark_results: list[BenchmarkResult] = sorted(
        results, key=attrgetter(*fields_sort_priority)
    )

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
    current_test_procedure: str | None = None
    csv_file: TextIOWrapper | None = None
    csv_writer: _csv._writer | None = None

    all_workload_params_len = len(all_workload_params_names)
    for result in sorted_benchmark_results:
        new_run_group = result.RunGroup
        new_engine = result.Engine
        new_engine_version = result.EngineVersion
        new_workload = result.Workload
        new_test_procedure = result.TestProcedure

        # Every time any of these columns changes values, we open a new file.
        # This is given the sorting of fields in fields_sort_priority,
        # which guarantees we should not find results from the same batch later.
        if (
            current_run_group != new_run_group
            or current_engine != new_engine
            or current_engine_version != new_engine_version
            or current_workload != new_workload
            or current_test_procedure != current_test_procedure
        ):
            current_run_group = new_run_group
            current_engine = new_engine
            current_engine_version = new_engine_version
            current_workload = new_workload
            current_test_procedure = new_test_procedure

            if csv_file is not None:
                csv_file.close()
            csv_file_path = (
                benchmark_data_folder
                / f"{current_run_group.strftime("%Y-%m-%dT%H%M%SZ")}-{current_engine}"
                f"-{current_engine_version}-{current_workload}-{current_test_procedure}.csv"
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

        assert csv_writer is not None
        csv_writer.writerow(values)

    if results_count > 0:
        print(f"Written all results to {benchmark_data_folder}")

    return 0


if __name__ == "__main__":
    main()
