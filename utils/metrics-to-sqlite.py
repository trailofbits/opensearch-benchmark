#!/usr/bin/env python3

import sqlite3
from typing import TypedDict, NotRequired

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


def _define_schema(db: sqlite3.Connection):
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs(id, index_name, exec_time, environment, workload, distribution_version, PRIMARY KEY(id));
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
        params={"scroll": "1m"},
        json={
            "size": 1000,
            "query": {
                "match_all": {},
            },
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

def _ingest_data(db: sqlite3.Connection, host: str, index: str, user: str, password: str):
    for hit in _get_hits(host, index, user, password):
        source = hit["_source"]
        if "meta" not in source:
            continue

        if "task" not in source or "sample-type" not in source:
            continue

        if "value" not in source or source["name"] not in ("latency", "service_time", "processing_time", "client_processing_time", "throughput"):
            continue

        db.execute(
            """
            INSERT OR IGNORE INTO runs(id, index_name, exec_time, environment, workload, distribution_version)
            VALUES(:exec_id, :index, :exec_time, :environment, :workload, :distribution_version)
            """,
            {
                "exec_id": source["test-execution-id"],
                "index": hit["_index"],
                "exec_time": source["test-execution-timestamp"],
                "environment": source["environment"],
                "workload": source["workload"],
                "distribution_version": source["meta"].get("distribution_version", None)
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
            }
        )

        db.execute(
            f"""
            INSERT INTO "{source["name"]}"(id, run_id, task, sample_type, value) VALUES(:id, :run_id, :task, :sample_type, :value)
            """,
            {
                "id": hit["_id"],
                "run_id": source["test-execution-id"],
                "task": source["task"],
                "value": source["value"],
                "sample_type": source["sample-type"],
            }
        )

        db.commit()


def _main():
    import os
    host = os.environ.get("DS_HOSTNAME", "opense-clust-aeqazh9qc4u7-dcbe5cce2775e15e.elb.us-east-1.amazonaws.com")
    index = os.environ.get("INDEX_NAME", "benchmark-metrics-2024-09")
    user = os.environ["DS_USERNAME"]
    password = os.environ["DS_PASSWORD"]
    output_file = os.environ.get("OUTPUT_DB", "data.db")
    with sqlite3.connect(output_file) as db:
        _define_schema(db)
        _ingest_data(db, host, index, user, password)


if __name__ == "__main__":
    _main()
