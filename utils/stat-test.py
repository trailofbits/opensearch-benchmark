"""Statistically test for differences between runs or run groups"""
import argparse
import os
import requests
import pingouin as pg
import pandas as pd
from typing import TypedDict, NotRequired, Generator
from tabulate import tabulate
from collections import defaultdict
import warnings
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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

def get_metrics_run_group(host: str, user: str, password: str, run_group_id: str) -> dict:
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

def get_metrics_run_group_by_run(host: str, user: str, password: str, run_group_id: str) -> dict:
    """
    Return combined metrics for each task in the run group, grouped by run.

    The dictionary is formatted like so:
    {
        "task": {
            "run_0": [value1, value2, ...],
            ...
        },
        ...
    }
    """
    metrics = defaultdict(lambda: defaultdict(list))
    for hit in _get_hits(host, user, password, run_group_id):
        metric_entry = hit["_source"]
        task = metric_entry['task']
        value = metric_entry['value']
        run_num = metric_entry['meta']['tag_run']
        metrics[task][run_num].append(value)
    return metrics

# currently unused
def do_t_test(group0_metrics: dict, group1_metrics: dict) -> list[list]:
    """Do t-test for all tasks in the groups"""
    assert(group0_metrics.keys() == group1_metrics.keys())
    results = []
    for key in group0_metrics.keys():
        group0_values = group0_metrics[key]
        group1_values = group1_metrics[key]
        assert(len(group0_values) == len(group1_values))
        res = pg.ttest(group0_values, group1_values)
        pvalue = float(res['p-val'].iloc[0])
        statistic = float(res['T'].iloc[0])
        cohens_d = float(res['cohen-d'].iloc[0])
        group0_mean = sum(group0_values)/len(group0_values)
        group1_mean = sum(group1_values)/len(group1_values)
        results.append([key, len(group0_values), group0_mean, group1_mean, statistic, pvalue, cohens_d])
    results.sort(key=lambda x: x[0])
    p_vals_uncorrected = [result[5] for result in results]
    significant_list, p_vals_corrected = pg.multicomp(p_vals_uncorrected)
    for result, p_val_corrected, significant in zip(results, p_vals_corrected, significant_list):
        result.append(float(p_val_corrected))
        result.append(bool(significant))
    return results

def do_run_groups_test(run_group0, run_group1, host, username, password):
    """Do t-test between pairs of run groups"""
    run_group0_metrics = get_metrics_run_group(host, username, password, run_group0)
    run_group1_metrics = get_metrics_run_group(host, username, password, run_group1)
    run_group_metrics = defaultdict(lambda: defaultdict(list))
    # combine metrics
    for k,v in run_group0_metrics.items():
        run_group_metrics[k][run_group0] = v
    for k,v in run_group1_metrics.items():
        run_group_metrics[k][run_group1] = v
    t_test_results = do_anova_test(run_group_metrics)
    print(f"1-Way ANOVA Between Run Groups: {run_group0}, {run_group1}" )
    results_header = ["task", "count", "F", "p-val-uncorrected", "np2", "p-val-corrected", "significant"]
    print(f"T-test Results for {run_group0} and {run_group1}")
    print(tabulate(t_test_results, headers=results_header, floatfmt=".4f"))

def do_anova_test(run_group_metrics: dict):
    """Do anova test on run group runs"""
    results = []
    for key in run_group_metrics.keys():
        task_values = run_group_metrics[key]
        task_df = pd.melt(pd.DataFrame(task_values), var_name="run", value_name="value")
        anova = pg.anova(data=task_df, dv="value", between="run")
        f = float(anova['F'].iloc[0])
        p_val_uncorrected = float(anova['p-unc'].iloc[0])
        np2 = float(anova['np2'].iloc[0])
        counts = [len(value) for value in task_values.values()]
        assert len(set(counts)) == 1 # make sure counts are the same
        row = [key, counts[0], f, p_val_uncorrected, np2]
        results.append(row)
    results.sort(key=lambda x: x[0])
    p_vals_uncorrected = [result[3] for result in results]
    significant_list, p_vals_corrected = pg.multicomp(p_vals_uncorrected)
    for result, p_val_corrected, significant in zip(results, p_vals_corrected, significant_list):
        result.append(float(p_val_corrected))
        result.append(bool(significant))
    return results

def do_runs_test(run_group: str, host: str, username: str, password: str):
    """Do anova test for runs in a run group"""
    run_group_metrics = get_metrics_run_group_by_run(host, username, password, run_group)
    anova_results = do_anova_test(run_group_metrics)
    print(f"1-Way ANOVA Across Runs for: {run_group}" )
    results_header = ["task", "count", "F", "p-val-uncorrected", "np2", "p-val-corrected", "significant"]
    print(tabulate(anova_results, headers=results_header, floatfmt=".4f"))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "run_groups",
        type=str,
        nargs="+",
        help="If 1 run group passed, analyze variance of runs. If >1 group passed, analyze variance of run groups.")
    args = parser.parse_args()
    run_groups = args.run_groups
    if len(run_groups) > 2:
        logger.error("Currently no more than 2 run groups are supported")
        exit(1)
    host = os.environ.get("DS_HOSTNAME")
    username = os.environ.get("DS_USERNAME")
    password = os.environ.get("DS_PASSWORD")
    if host is None or username is None or password is None:
        logger.error("Set environment variables: DS_HOSTNAME, DS_USERNAME, and DS_PASSWORD")
        exit(1)
    if len(run_groups) == 1:
        run_group = run_groups[0]
        do_runs_test(run_group, host, username, password)
    elif len(run_groups) == 2:
        run_group0 = run_groups[0]
        run_group1 = run_groups[1]
        do_run_groups_test(run_group0, run_group1, host, username, password)

if __name__ == "__main__":
    main()
