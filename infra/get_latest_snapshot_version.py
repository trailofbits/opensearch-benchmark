import subprocess
import sys
import json
from datetime import datetime
import re

input_map = json.loads(input())

s3_prefix = f"{input_map['cluster_type']}/{input_map['cluster_version']}/{input_map['workload']}/"
cmd = [
    "aws",
    "s3api",
    "list-objects-v2",
    "--bucket",
    input_map["s3_bucket_name"],
    "--prefix",
    s3_prefix,
    "--query",
    "sort_by(Contents, &LastModified)[-1].Key",
    "--output",
    "text"
]
try:
    res = subprocess.check_output(cmd, universal_newlines=True).strip()
    latest_version = res.split('/')[3] if len(res.split('/')) > 3 else None
except subprocess.CalledProcessError:
    latest_version = None
    print(f"Error while calling aws s3api list-objects-v2", file=sys.stderr)

# Ensure that $LATEST_VERSION is in a date format '%Y-%m-%d_%H-%M-%S'
if latest_version is None or not re.match(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}', latest_version):
    # Default to current date
    latest_version = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    print(f"Could not find a valid latest version, defaulting to {latest_version}", file=sys.stderr)

output = {
    "latest_version": latest_version
}
print(f"Latest version: {latest_version}", file=sys.stderr)
print(json.dumps(output))
