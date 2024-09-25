#!/usr/bin/env bash

#
# Copyright (c) 2024-present, Trail of Bits
# All rights reserved.
#
# This source code is licensed in accordance with the terms specified in
# the LICENSE file found in the root directory of this source tree.
#

# Global log file
LOG_FILE=$(mktemp)

# Benchmark data
BENCHMARK_DATA="/mnt/.benchmark/benchmarks/data"

main() {
    # Common parameters that are applied to all the workloads
    local common_workload_params="number_of_replicas:0,target_throughput:0"

    # A list of "<workflow_name>;<workflow_params>" pairs
    local workload_descriptor_list=(
        "big5;${common_workload_params},max_num_segments:10,bulk_indexing_clients:8"
        "pmc;${common_workload_params},bulk_indexing_clients:1"
        "noaa;${common_workload_params},bulk_indexing_clients:1"
        "nyc_taxis;${common_workload_params},bulk_indexing_clients:1"
    )

    trace "New session started"

    for workload_descriptor in "${workload_descriptor_list[@]}" ; do
        local workflow_name
        if ! workflow_name=$(echo "${workload_descriptor}" | cut -d ';' -f 1) ; then
            terminate "The following workload descriptor is malformed: ${workload_descriptor}"
        fi

        local workflow_params
        if ! workflow_params=$(echo "${workload_descriptor}" | cut -d ';' -f 2) ; then
            terminate "The following workload descriptor is malformed: ${workload_descriptor}"
        fi

        trace "> ${workflow_name} / ${workflow_params}"

        if ! generateWorkloadIndexSnapshot "${workflow_name}" "${workflow_params}" ; then
            terminate "Failed to generate a snapshot for the following workflow: ${workflow_name} (${workflow_params})"
        fi
    done

    return 0
}

# Ensures that all required commands are present. Does not return in case
# of failure
checkForPrerequisites() {
    local command_name_list=(
        "tee"
    )

    for command_name in "${command_name_list[@]}" ; do
        if ! command -v "${command_name}" > /dev/null 2>&1 ; then
            terminate "The following command is missing: ${command_name}\n"
        fi
    done

    # Additionally, ensure that we are being run in the same directory as the
    # "ingest.sh" script
    #
    # Dot not change the working directory as this will create problems for
    # callers
    if [[ ! -f "ingest.sh" ]] ; then
        terminate "The script should be run in the same folder as the 'ingest.sh' script"
    fi
}

# Prints a message to screen and to the log file
trace() {
    if [[ $# != 1 ]] ; then
        printf "Usage:\n\ttrace <message>\n"
        return 1
    fi

    local message="$1"
    printf "$(date): %s\n" "${message}" | tee "${LOG_FILE}"

    return 0
}

# A wrapper around the 'ingest.sh' script, which is used to verify parameters, environment, exit status
# and standard output
generateWorkloadIndexSnapshot() {
    local required_environment_var_list=(
        "CLUSTER_HOST"
        "DISTRIBUTION_VERSION"
        "CLUSTER_USER"
        "CLUSTER_PASSWORD"
    )

    # Validate the parameters
    if [[ $# != 2 ]] ; then
        trace "Usage:\n\tgenerateWorkloadIndexSnapshot <osb_workload_name> <osb_workload_params>"

        trace "Required environment variables:"
        for required_environment_var in "${required_environment_var_list[@]}" ; do
            trace "\t${required_environment_var}"
        done

        trace "Invalid arguments passed to generateWorkloadIndexSnapshot"
        return 1
    fi

    # Validate the environment
    for required_environment_var in "${required_environment_var_list[@]}" ; do
        if ! env | grep -E "^${required_environment_var}=" > /dev/null 2>&1 ; then
            trace "The following required environment variable is not defined: ${required_environment_var}"
            return 1
        fi
    done

    local osb_workload_name="$1"
    local osb_workload_params="$2"

    # TODO: External environment variables should be uppercase, and shellcheck will
    # warn about it. For the time being, alias it to a local variable with the
    # same name
    local s3_bucket_name="${s3_bucket_name}"

    # Delete the previous workflow data, since disk space is limited
    if [[ -d "${BENCHMARK_DATA}" ]] ; then
        trace "Found existing benchmark data at ${BENCHMARK_DATA}. Deleting..."

        if ! rm -rf "${BENCHMARK_DATA}" ; then
            trace "Failed to create the temporary log file for the ingest.sh script"
            return 1
        fi
    fi

    # We can't easily redirect the stdout/stderr without causing problems. It would have been
    # useful to check for errors or successes (such as whether a snapshot was created or not)
    export WORKLOAD="${osb_workload_name}"
    export WORKLOAD_PARAMS="${osb_workload_params}"
    export FORCE_INGESTION="1"

    if ! ./ingest.sh ; then
        trace "It seems like the ingest script has returned an error"
        return 1
    fi

    return 0
}

# Terminates the script with an error message, dumping the contents of LOG_FILE to screen. Does not return
terminate() {
    if [[ $# != 1 ]] ; then
        trace "Usage:\n\tterminate <error_message>"
        exit 1
    fi

    local error_message="$1"
    trace "An error has occurred and the script has been terminated: ${error_message}"

    read -rp "Press any key to dump the log file (${LOG_FILE})... or CTRL+C to halt the script" -n1 -s
    cat "${LOG_FILE}"

    exit 1
}

checkForPrerequisites
main "$@"
exit $?
