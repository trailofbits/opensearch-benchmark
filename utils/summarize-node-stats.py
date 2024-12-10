"""
Summarize JSON responses from the node-stats API
"""
import argparse
import json
from pathlib import Path
import sys
import logging
import pandas as pd

logging.basicConfig()

def get_node_stats(json_path: Path) -> dict:
    node_stats_raw = json.loads(json_path.read_text())
    node_stats_summary = {}
    for _, node_stats in node_stats_raw['nodes'].items():
        node_stats_values = {}
        node_name = node_stats['name']
        request_cache = node_stats['indices']['request_cache']
        query_cache = node_stats['indices']['query_cache']
        io_stats = node_stats['fs']['io_stats']['total']
        for k, v in request_cache.items():
            node_stats_values[f"request_cache.{k}"] = v
        for k, v in query_cache.items():
            node_stats_values[f"query_cache.{k}"] = v
        for k, v in io_stats.items():
            node_stats_values[f"io_stats.{k}"] = v
        node_stats_summary[node_name] = node_stats_values
    return node_stats_summary

def main():
    parser = argparse.ArgumentParser(usage="Create table summarizing node stats for each run")
    parser.add_argument("json_dir", help="Directory containing node-stats JSONs", type=Path)
    parser.add_argument('-t', '--totals', action='store_true', default=False, help="Show cumulative totals for each sample, instead of the default diff behavior")
    args = parser.parse_args()
    json_dir = args.json_dir
    totals = args.totals
    if not json_dir.is_dir():
        logging.error(f"Error: Must be a directory: {json_dir}")
        return 1
    rows = []
    for sample in ["initial", "0", "1", "2", "3", "4"]:
        json_path = json_dir / f"node-stats-{sample}.json"
        if not json_path.exists():
            logging.warning(f"Missing expected node stats sample: {json_path}")
            continue
        parsed = get_node_stats(json_path)
        for k, v in parsed.items():
            flattened = v
            if sample == 'initial':
                flattened['run'] = "-1"
            else:
                flattened['run'] = sample
            flattened['node'] = k
            rows.append(flattened)
    df = pd.DataFrame.from_records(rows)
    df = df.sort_values(by=['node', 'run'])
    df = df.set_index(['node', 'run'])
    if not totals:
        df = df.groupby(level=0).diff()

    print(df.to_csv(index=True, header=True))


if __name__ == "__main__":
    sys.exit(main())
