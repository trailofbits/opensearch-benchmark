"""Run t-test on pairs of run groups"""
import argparse
import os
import requests
import scipy.stats
from typing import TypedDict, NotRequired, Generator
from tabulate import tabulate
from collections import defaultdict
import warnings

warnings.filterwarnings("ignore", category=requests.packages.urllib3.exceptions.InsecureRequestWarning)

class Meta(TypedDict):
    distribution_version: NotRequired[str]

Source = TypedDict(
    "Source",
    {
        "@timestamp": str,
        "test-execution-id": str,
        "test-execution-timestamp": str,
        "environment": str,
        "workload": str,
        "name": str,
        "value": NotRequired[float],
        "sample-type": NotRequired[str],
        "task": NotRequired[str],
        "meta": NotRequired[Meta],
    },
)

class Hit(TypedDict):
    _index: str
    _id: str
    _source: Source

class Hits(TypedDict):
    hits: list[Hit]

class OSResponse(TypedDict):
    _scroll_id: str
    hits: Hits

def _get_hits(host: str, user: str, password: str, run_group_id: str) -> Generator[Hit, None, None]:
    """
    Get service time metrics for a run group

    Exclude warmup samples and runs.
    """
    index = "benchmark-metrics*"
    response: OSResponse = requests.get(
        url=f"https://{host}/{index}/_search",
        params={"scroll": "1m"},
        json={
            "size": 1000,
            "query": {
                "bool": {
                    "must": [
                        {
                            "term": {
                                "meta.tag_run-group": run_group_id
                            },
                        },
                        {
                            "term": {
                                "name": "service_time"
                            }
                        },
                        {
                            "term": {
                                "sample-type": "normal"
                            }
                        }
                    ],
                    "must_not": [
                        {
                            "term": {
                                "meta.tag_run-type": "warmup"
                            }
                        }
                    ]
                }
            }
        },
        auth=(user, password),
        verify=False,
    ).json()
    num_hits = len(response["hits"]["hits"])
    try:
        while num_hits > 0:
            for hit in response["hits"]["hits"]:
                yield hit
            response = requests.get(
                url=f"https://{host}/_search/scroll",
                json={"scroll": "1m", "scroll_id": response["_scroll_id"]},
                auth=(user, password),
                verify=False,
            ).json()
            num_hits = len(response["hits"]["hits"])
    finally:
        response = requests.delete(
            url=f"https://{host}/_search/scroll",
            json={"scroll_id": response["_scroll_id"]},
            auth=(user, password),
            verify=False,
        ).json()

def get_metrics(host: str, user: str, password: str, run_group_id: str) -> dict:
    """
    Return combined metrics for each task in the run group

    The dictionary is formatted like so:
    {
        "task": [value1, value2, ....],
        ...
    }
    """
    metrics = defaultdict(list)
    for hit in _get_hits(host, user, password, run_group_id):
        metric_entry = hit["_source"]
        task = metric_entry['task']
        value = metric_entry['value']
        metrics[task].append(value)
    return metrics

def do_t_test(group0_metrics: dict, group1_metrics: dict) -> list[list]:
    """Do t-test for all tasks in the groups"""
    assert(group0_metrics.keys() == group1_metrics.keys())
    results = []
    for key in group0_metrics.keys():
        group0_values = group0_metrics[key]
        group1_values = group1_metrics[key]
        assert(len(group0_values) == len(group1_values))
        res = scipy.stats.ttest_ind(group0_values, group1_values, equal_var=False)
        pvalue_formatted = f"{res.pvalue:.4f}"
        statistic_formatted = f"{res.statistic:.4f}"
        results.append([key, len(group0_values), statistic_formatted, pvalue_formatted])
    results.sort(key=lambda x: x[0])
    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_group0", type=str)
    parser.add_argument("run_group1", type=str)
    args = parser.parse_args()
    run_group0 = args.run_group0
    run_group1 = args.run_group1

    host = os.environ.get("DS_HOSTNAME")
    username = os.environ.get("DS_USERNAME")
    password = os.environ.get("DS_PASSWORD")
    if host is None or username is None or password is None:
        print("Set environment variables: DS_HOSTNAME, DS_USERNAME, and DS_PASSWORD")
        exit(1)

    run_group0_metrics = get_metrics(host, username, password, run_group0)
    run_group1_metrics = get_metrics(host, username, password, run_group1)
    t_test_results = do_t_test(run_group0_metrics, run_group1_metrics)
    header = ["task", "count", "statistic", "p-value"]
    t_test_results.insert(0, header)
    print(f"T-test Results for {run_group0} and {run_group1}")
    print(tabulate(t_test_results))

if __name__ == "__main__":
    main()
