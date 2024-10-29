#!/usr/bin/env bash

SCRIPT_VERSION="@SOURCE_REPOSITORY_COMMIT_ID@"
PHORONIX_TEST_SUITE_VERSION="10.8.4"
PHORONIX_TEST_SUITE_URL="https://github.com/phoronix-test-suite/phoronix-test-suite/releases/download/v${PHORONIX_TEST_SUITE_VERSION}/phoronix-test-suite_${PHORONIX_TEST_SUITE_VERSION}_all.deb"
#PHORONIX_BENCHMARK_LIST=("pts/hpcg" "pts/npb" "system/openssl" "pts/memcached" "pts/leveldb" "pts/unpack-linux" "pts/speedtest-cli")
PHORONIX_BENCHMARK_LIST=("pts/speedtest-cli")
PHORONIX_BENCHMARK_DEPENDENCY_LIST=("libevent-dev" "cmake" "openmpi-bin" "gfortran" "libgmock-dev" "libopenmpi-dev")

main() {
  printf "Log file: ${LOG_FILE}\n"
  printf "Report path: ${REPORT_PATH}\n"
  printf "Script version: ${SCRIPT_VERSION}\n"

  installPrerequisites
  installTestSuite
  collectBaseSystemInfo
  executeBenchmarks

  return 0
}

installPrerequisites() {
  local package_name_list=("curl" "sysstat" "zip" "coreutils" "lshw" "procps")

  for package_name in "${package_name_list[@]}" ; do
    local package_version
    if ! package_version="$(dpkg-query --show --showformat='${Version}\n' ${package_name})" ; then
      trace "Installing '${package_name}'..."

      if ! apt install -y "${package_name}" ; then
        terminate "Failed to install the package"
      fi
    else
      trace "Using package ${package_name} at version ${package_version}"
    fi
  done
}

trace() {
  if [[ $# != 1 ]] ; then
    printf "trace() called with no parameters\n"
    exit 1
  fi

  local message="$1"
  printf "%s: %s\n" "$(date)" "${message}" | tee "${LOG_FILE}"
}

terminate() {
  trace "An error has occurred and the script has been terminated"

  if [[ $# == 1 ]] ; then
    local message="$1"
    trace "Error message: ${message}"
  else
    trace "No error message provided"
  fi

  exit 1
}

installTestSuite() {
  trace "Installing the phoronix test suite..."

  local package_version
  if ! package_version="$(dpkg-query --show --showformat='${Version}\n' phoronix-test-suite)" ; then
    trace "Installing the Phoronix test suite..."

    local download_folder
    if ! download_folder=$(mktemp -d) ; then
      terminate "Failed to create the temporary download folder"
    fi

    local package_file_path="${download_folder}/phoronix-test-suite.deb"
    if ! curl -L "${PHORONIX_TEST_SUITE_URL}" -o "${package_file_path}" ; then
      terminate "Failed to download the phoronix test suite"
    fi

    trace "Installing the phoronix test suite.."
    if ! apt install -y "${download_folder}/phoronix-test-suite.deb" ; then
      terminate "Failed to install the deb package"
    fi

    if ! dpkg -l "phoronix-test-suite" > /dev/null 2>&1 ; then
      terminate "The phoronix test suite could not be installed"
    fi

  else
    trace "The phoronix test suite is already installed at version ${package_version}"
  fi

  trace "Installing the tests..."

  if ! apt install -y "${PHORONIX_BENCHMARK_DEPENDENCY_LIST[@]}" ; then
    terminate "Failed to install the test dependencies"
  fi

  if ! phoronix-test-suite batch-install "${PHORONIX_BENCHMARK_LIST[@]}" ; then
    terminate "Failed to install the phoronix tests"
  fi
}

collectBaseSystemInfo() {
  trace "Collecting system information"

  if ! echo "${SCRIPT_VERSION}" > "${REPORT_PATH}/script_version" ; then
    terminate "Failed to save the script version"
  fi

  local file_path_list=("/proc/cpuinfo")
  for file_path in "${file_path_list[@]}" ; do
    local file_name="$(echo ${file_path} | tr '/' '_')"
    trace "  '${file_path}' => '${file_name}'"

    if ! cat "${file_path}" > "${REPORT_PATH}/${file_name}" ; then
      terminate "Failed to save '${file_path}'"
    fi
  done

  local command_list=("hostname" "lshw" "free -h" "iostat" "phoronix-test-suite system-info" "phoronix-test-suite system-properties" "ip addr" "hostname")
  for command in "${command_list[@]}" ; do
    local file_name="$(echo ${command} | tr ' ' '_')"
    trace "  '${command}' => '${file_name}'"

    if ! ${command} > "${REPORT_PATH}/${file_name}" ; then
      terminate "The '${command_name}' command could not be run correctly"
    fi
  done
}

executeBenchmarks() {
  trace "Executing benchmarks..."

  if ! printf "y\nn\nn\nn\nn\nn\ny\n" | phoronix-test-suite batch-setup ; then
    terminate "Failed to initialize the batch settings"
  fi

  if ! phoronix-test-suite batch-benchmark "${PHORONIX_BENCHMARK_LIST[@]}" ; then
    terminate "Failed to execute the benchmarks"
  fi

  local report_folder_name
  if ! report_folder_name=$(ls -Art "/var/lib/phoronix-test-suite/test-results" | tail -n 1) ; then
    terminate "Failed to locate the report folder"
  fi

  local report_path="/var/lib/phoronix-test-suite/test-results/${report_folder_name}"
  if ! ( cd / && zip -r9 "pts-report.zip" "${report_path}" ) ; then
    terminate "Failed to create the report archive"
  fi
}

STARTUP_COMMAND_LIST=("mktemp" "sudo")
for command_name in "${STARTUP_COMMAND_LIST[@]}" ; do
  if ! command -v "${command_name}" > /dev/null 2>&1 ; then
    terminate "The command named '${command_name}' was not found"
  fi
done

if [[ "$EUID" != 0 ]] ; then
  printf "Rerunning the script as root...\n"

  sudo \
    -H \
    -i \
    "$(realpath ${BASH_SOURCE[0]})" "$@"

  exit $?
fi

LOG_FILE="$(mktemp)"
REPORT_PATH="$(mktemp -d)"

main "$@"
exit $?
