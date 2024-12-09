#!/usr/bin/env python3

import sqlite3
from typing import TypedDict

Source = TypedDict(
    "Source",
    {
        "@timestamp": str,
        "test-execution-id": str,
        "test-execution-timestamp": str,
        "environment": str,
        "workload": str,
        "name": str,
        "value": float,
        "sample-type": str,
        "task": str,
        "meta": dict[str, str],
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
        CREATE TABLE IF NOT EXISTS runs       (id, index_name, exec_time, environment, workload, distribution_version, PRIMARY KEY(id));
        CREATE TABLE IF NOT EXISTS tasks      (run_id, task, timestamp, PRIMARY KEY(run_id, task));
        CREATE TABLE IF NOT EXISTS metrics    (id, name, run_id, task, sample_type, value, PRIMARY KEY(id));
        CREATE TABLE IF NOT EXISTS tags       (run_id, name, value, PRIMARY KEY(run_id, name));
        CREATE TABLE IF NOT EXISTS attributes (run_id, name, value, PRIMARY KEY(run_id, name));
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
                            "term": {
                                "meta.success": True,
                            },
                        },
                        {
                            "terms": {
                                "name": [
                                    "service_time",
                                ],
                            },
                        },
                        {
                            "exists": {
                                "field": "task",
                            },
                        },
                        {
                            "exists": {
                                "field": "value",
                            },
                        },
                        {
                            "exists": {
                                "field": "sample-type",
                            },
                        },
                        {
                            "exists": {
                                "field": "meta.distribution_version",
                            },
                        },
                        {
                            "prefix": {
                                "environment": "gh-nightly-",
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
                "distribution_version": meta["distribution_version"],
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
            """
            INSERT OR IGNORE INTO metrics (id, name, run_id, task, sample_type, value) VALUES(:id, :name, :run_id, :task, :sample_type, :value)
            """,
            {
                "id": hit["_id"],
                "name": source["name"],
                "run_id": source["test-execution-id"],
                "task": source["task"],
                "value": source["value"],
                "sample_type": source["sample-type"],
            },
        )

        db.executemany(
            "INSERT OR IGNORE INTO tags(run_id, name, value) VALUES(:id, :name, :value)",
            [
                {
                    "id": source["test-execution-id"],
                    "name": tag_name[4:],
                    "value": tag_value,
                }
                for tag_name, tag_value in meta.items()
                if tag_name.startswith("tag_")
            ],
        )

        db.executemany(
            "INSERT OR IGNORE INTO attributes(run_id, name, value) VALUES(:id, :name, :value)",
            [
                {
                    "id": source["test-execution-id"],
                    "name": attr_name[10:],
                    "value": attr_value,
                }
                for attr_name, attr_value in meta.items()
                if attr_name.startswith("attribute_")
            ],
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
