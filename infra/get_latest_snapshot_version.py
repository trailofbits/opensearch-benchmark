import subprocess
import sys
import json
from datetime import datetime
import re


def new_snapshot_version() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def is_version_format(version: str) -> bool:
    return re.match(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}", version)


input_map = json.loads(input())

s3_prefix = f"{input_map['cluster_type']}/{input_map['cluster_version']}/{input_map['workload']}"
if input_map["snapshot_version"] == "latest":
    cmd = [
        "aws",
        "s3",
        "ls",
        f"s3://{input_map['s3_bucket_name']}/{s3_prefix}/",
    ]
    try:
        res = subprocess.check_output(cmd, universal_newlines=True).strip()
        subdirs = [
            x.split()[1] for x in res.splitlines() if x.strip() and len(x.split()) == 2
        ]
        subdirs = [x[:-1] for x in subdirs if x.endswith("/")]
        versions = [x for x in subdirs if is_version_format(x)]
        sorted_versions = (
            x
            for x in sorted(
                versions,
                key=lambda x: datetime.strptime(x, "%Y-%m-%d_%H-%M-%S"),
                reverse=True,
            )
        )
        latest_version = next(sorted_versions, None)
    except subprocess.CalledProcessError as e:
        print(f"Error while calling aws s3 ls: {e}", file=sys.stderr)
        sys.exit(1)
elif input_map["snapshot_version"] == "new":
    latest_version = new_snapshot_version()
else:
    latest_version = input_map["snapshot_version"]
    cmd = [
        "aws",
        "s3",
        "ls",
        f"s3://{input_map['s3_bucket_name']}/{s3_prefix}/{latest_version}",
    ]
    try:
        res = subprocess.check_output(cmd, universal_newlines=True).strip()
        subdirs = [
            x.split()[1] for x in res.splitlines() if x.strip() and len(x.split()) == 2
        ]
        subdirs = [x[:-1] for x in subdirs if x.endswith("/")]
        if len(subdirs) != 1:
            print(f"Snapshot version {latest_version} not found", file=sys.stderr)
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        print(f"Error while calling aws s3 ls: {e}", file=sys.stderr)
        sys.exit(1)

output = {"latest_version": latest_version}
print(f"Latest version: {latest_version}", file=sys.stderr)
print(json.dumps(output))
