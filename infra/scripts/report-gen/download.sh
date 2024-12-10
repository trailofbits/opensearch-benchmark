#!/bin/bash


if [ -z ${DS_PASSWORD+x} ]; then
    echo "DS_PASSWORD is unset" >&2
    exit 1
fi

if [ -z ${DS_URL+x} ]; then
    echo "DS_URL is unset"
    exit 1
fi

source_flag="scheduled"
while [[ $# -gt 0 ]]; do
    case $1 in
        --source|-source)
            if [ -z "$2" ] || [[ "$2" == --* ]]; then
                echo "Error: --source requires an argument" >&2
                exit 1
            fi
            source_flag="$2"
            shift 2 # move past flag and value
            ;;
        *)
            # break the loop if no more flags
            if [[ "$1" != --* ]] && [[ "$1" != -* ]]; then
                break
            fi
            echo "Error: Unknown flag $1" >&2
            exit 1
            ;;
    esac
done

SRC_OPTS="[nightly|manual|dev]"
if [ $# -ne 2 ]; then
    echo "usage: $0 --source $SRC_OPTS <start_date [YYYY-MM-DD]> <end_date [YYYY-MM-DD]>"
    exit 1
fi

start="$1"
end="$2" 

cmd_flags=""
case $source_flag in
    nightly)
        cmd_flags="--source ci-scheduled"
        ;;
    manual)
        cmd_flags="--source ci-manual"
        ;;
    dev)
        cmd_flags="--run-type dev --source ci-manual other"
        ;;
    *)
        echo "invalid source flag '$source_flag'. Expected one of $SRC_OPTS"
        ;;
esac

folder="download_${source_flag}_${start}_${end}"
mkdir -p $folder
make run ARGS=" download \
    --host $DS_URL \
    --benchmark-data $folder \
    $cmd_flags \
    --from $start \
    --to $end
"