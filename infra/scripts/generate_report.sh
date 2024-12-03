#!/bin/bash

if [ -z ${DS_PASSWORD+x} ]; then
    echo "DS_PASSWORD is unset"
    exit 1
fi

if [ -z ${DS_URL+x} ]; then
    echo "DS_URL is unset"
    exit 1
fi

if [ "$#" -ne 3 ]; then
    echo "usage: $0 <start_date [YYYY-MM-DD]> <end_date [YYYY-MM-DD]> /path/to/credentials.json"
    exit 1
fi

start="$1"
end="$2"
creds="$3"

# Download the raw data from the data store
# TODO: should source also be an argument?
folder="download_nightly_${start}_${end}"
mkdir -p folder
make run ARGS=" download \
    --host $url \
    --benchmark-data $folder
    --source ci-scheduled \
    --from $start \
    --to $end
"

# Upload the report to google sheets
token_file="token.json"
make run ARGS="create --benchmark-data $folder --token $token_file --credentials $creds"

# Cleanup
rm $token_file
rm -rf $folder

