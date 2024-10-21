#!/usr/bin/env python3

import sqlite3
from typing import TypedDict, NotRequired

Meta = TypedDict(
    "Meta",
    {
        "distribution_version": NotRequired[str],
        "tag_run-group": NotRequired[str],
        "tag_engine-type": NotRequired[str],
        "tag_run-type": NotRequired[str],
    },
)

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


def _define_schema(db: sqlite3.Connection):
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs(id, index_name, exec_time, environment, workload, distribution_version, run_group, engine_type, run_type, PRIMARY KEY(id));
        CREATE TABLE IF NOT EXISTS tasks                    (run_id, task, timestamp, PRIMARY KEY(run_id, task));
        CREATE TABLE IF NOT EXISTS latency                  (id, run_id, task, sample_type, value, PRIMARY KEY(id));
        CREATE TABLE IF NOT EXISTS service_time             (id, run_id, task, sample_type, value, PRIMARY KEY(id));
        CREATE TABLE IF NOT EXISTS processing_time          (id, run_id, task, sample_type, value, PRIMARY KEY(id));
        CREATE TABLE IF NOT EXISTS client_processing_time   (id, run_id, task, sample_type, value, PRIMARY KEY(id));
        CREATE TABLE IF NOT EXISTS throughput               (id, run_id, task, sample_type, value, PRIMARY KEY(id));
        """
    )
    db.commit()


def _get_hits(host: str, index: str, user: str, password: str):
    import requests

    response: OSResponse = requests.get(
        url=f"https://{host}/{index}/_search",
        params={"scroll": "10m"},
        json={
            "size": 10000,
            "query": {
                "bool": {
                    "must": [
                        {
                            "terms": {
                                "meta.tag_run-type": [
                                    "official",
                                    "dev",
                                ],
                            },
                        },
                        {
                            "terms": {
                                "name": [
                                    "latency",
                                    "service_time",
                                    "processing_time",
                                    "client_processing_time",
                                    "throughput",
                                ],
                            },
                        },
                        {
                            "term": {
                                "sample-type": "normal",
                            },
                        },
                        {
                            "exists": {
                                "field": "task",
                            },
                        },
                    ],
                    "must_not": [
                        {
                            "term": {
                                "meta.tag_run": "0"
                            },
                        },
                    ],
                }
            },
        },
        auth=(user, password),
        verify=False,
    ).json()
    num_hits = len(response["hits"]["hits"])
    i = 1
    total_hits = num_hits
    try:
        while num_hits > 0:
            print(f"Request {i}: {num_hits} hits (total: {total_hits})")
            for hit in response["hits"]["hits"]:
                yield hit
            response = requests.get(
                url=f"https://{host}/_search/scroll",
                json={"scroll": "10m", "scroll_id": response["_scroll_id"]},
                auth=(user, password),
                verify=False,
            ).json()
            num_hits = len(response["hits"]["hits"])
            i += 1
            total_hits += num_hits
    finally:
        response = requests.delete(
            url=f"https://{host}/_search/scroll",
            json={"scroll_id": response["_scroll_id"]},
            auth=(user, password),
            verify=False,
        ).json()


def _ingest_data(
    db: sqlite3.Connection, host: str, index: str, user: str, password: str
):
    for hit in _get_hits(host, index, user, password):
        source = hit["_source"]
        meta = source["meta"]

        if "value" not in source:
            continue

        db.execute(
            """
            INSERT OR IGNORE INTO runs(id, index_name, exec_time, environment, workload, distribution_version, run_group, engine_type, run_type)
            VALUES(:exec_id, :index, :exec_time, :environment, :workload, :distribution_version, :run_group, :engine_type, :run_type)
            """,
            {
                "exec_id": source["test-execution-id"],
                "index": hit["_index"],
                "exec_time": source["test-execution-timestamp"],
                "environment": source["environment"],
                "workload": source["workload"],
                "distribution_version": meta.get("distribution_version", None),
                "run_group": meta.get("tag_run-group", None),
                "engine_type": meta.get("tag_engine-type", None),
                "run_type": meta.get("tag_run-type", None),
            },
        )

        db.execute(
            """
            INSERT OR IGNORE INTO tasks (run_id, task, timestamp) VALUES (:run_id, :task, :timestamp)
            """,
            {
                "run_id": source["test-execution-id"],
                "task": source["task"],
                "timestamp": source["@timestamp"],
            },
        )

        db.execute(
            f"""
            INSERT OR IGNORE INTO "{source["name"]}"(id, run_id, task, sample_type, value) VALUES(:id, :run_id, :task, :sample_type, :value)
            """,
            {
                "id": hit["_id"],
                "run_id": source["test-execution-id"],
                "task": source["task"],
                "value": source["value"],
                "sample_type": source["sample-type"],
            },
        )

        db.commit()


def _main():
    import os
    from datetime import datetime

    now = datetime.now()
    host = os.environ.get(
        "DS_HOSTNAME",
        "opense-clust-aeqazh9qc4u7-dcbe5cce2775e15e.elb.us-east-1.amazonaws.com",
    )
    index = os.environ.get("INDEX_NAME", "benchmark-metrics*")
    user = os.environ["DS_USERNAME"]
    password = os.environ["DS_PASSWORD"]
    output_file = os.environ.get(
        "OUTPUT_DB", now.strftime("amz_benchmark_data_%Y%m%d.sqlite")
    )
    with sqlite3.connect(output_file) as db:
        _define_schema(db)
        _ingest_data(db, host, index, user, password)


if __name__ == "__main__":
    _main()
