#!/usr/bin/env python3

import sqlite3
from enum import Enum
import csv
import scipy.stats
from collections import defaultdict


class Metric(Enum):
    latency = "latency"
    processing_time = "processing_time"
    client_processing_time = "client_processing_time"
    service_time = "service_time"
    throughput = "throughput"


def _get_pop(
    db: sqlite3.Connection, *, metric: Metric, workload: str, task: str, dist_ver: str
) -> list[float]:
    cur = db.execute(
        f"""
        SELECT value FROM runs JOIN "{metric}" ON "{metric}".run_id = runs.id
        WHERE
            runs.workload = :workload AND
            runs.distribution_version=:dist_ver AND
            "{metric}".task=:task AND
            "{metric}".sample_type='normal';
        """,
        {
            "workload": workload,
            "dist_ver": dist_ver,
            "task": task,
        },
    )
    return [value for (value,) in cur.fetchall()]


def _get_workloads(db: sqlite3.Connection):
    cur = db.execute(
        "SELECT DISTINCT workload, task FROM runs JOIN tasks on run_id = id"
    )
    res: dict[str, list[str]] = defaultdict(list)
    for workload, task in cur.fetchall():
        res[workload].append(task)
    return res


def _t_test(db: sqlite3.Connection, *, metric: Metric, workload: str, task: str):
    pop_es = _get_pop(
        db, metric=metric, workload=workload, task=task, dist_ver="8.15.0"
    )
    pop_os = _get_pop(
        db, metric=metric, workload=workload, task=task, dist_ver="2.16.0"
    )
    res = scipy.stats.ttest_ind(pop_es, pop_os, equal_var=False)
    return {
        "metric": metric,
        "workload": workload,
        "task": task,
        "statistic": res.statistic,
        "pvalue": res.pvalue,
    }


def _main():
    import os

    input_file = os.environ.get("INPUT_DB", "data.db")
    with sqlite3.connect(input_file) as db:
        with open("results.csv", mode="w") as file:
            writer = csv.DictWriter(
                file, ["metric", "workload", "task", "statistic", "pvalue"]
            )
            writer.writeheader()
            workloads = _get_workloads(db)
            for metric in (
                "latency",
                "processing_time",
                "client_processing_time",
                "service_time",
                "throughput",
            ):
                for workload, tasks in workloads.items():
                    for task in tasks:
                        writer.writerow(
                            _t_test(db, metric=metric, workload=workload, task=task)
                        )


if __name__ == "__main__":
    _main()
