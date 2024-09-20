#!/usr/bin/env bash

check_prerequisites () {
    local program_list=("curl" "jq" "wget" "shasum" "tar" "sudo" "sed" "opensearch-benchmark" "scp")

    for program in "${program_list[@]}" ; do
        if ! command -v "${program}" > /dev/null 2>&1 ; then
            echo "The following program is required but was not found: ${program}"
            return 1
        fi
    done

    return 0
}

check_value () {
    local name=$1
    local expected=$2
    local actual=$3

    if [[ "$expected" != "$actual" ]]; then
        printf 'Incorrect %s value, expected %s, actual %s\n' "$name" "$expected" "$actual"
        exit 1
    fi
}

check_params () {
    local user=$1
    local password=$2
    local host=$3

    read -r doc_count shards_total shards_failed shards_skipped < <( \
        curl \
            --silent \
            --insecure \
            --user "$user:$password" \
            --request GET "$host/big5/_count" \
        | jq --raw-output '"\(.count) \(._shards.total) \(._shards.failed) \(._shards.skipped)"' \
    )

    check_value "document count" "$${DOC_COUNT:-116000000}" "$doc_count"
    check_value "total shards count" "$${TOTAL_SHARDS:-1}" "$shards_total"
    check_value "failed shards count" "$${FAILED_SHARDS:-0}" "$shards_failed"
    check_value "skipped shards count" "$${SKIPPED_SHARDS:-0}" "$shards_skipped"
}

# Ensure that sourcing this script will trigger the prerequisites check
check_prerequisites || exit 1
