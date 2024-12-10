"""Helpers for diffing folders of benchmark results."""

import csv
import logging
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


def get_service_times(file: Path) -> dict[str, list[float]]:
    """Retrieve service_times for each operation from file."""
    row_list: list[list[str]]
    with file.open() as csv_file:
        csv_reader = csv.reader(csv_file)
        row_list = list(csv_reader)

    input_columns: dict[str, int] = {header_column: index for index, header_column in enumerate(row_list[0])}

    # When changing this, make sure to update the formulas
    output_column_order: list[str] = [
        "operation",
        "value\\.90_0",
    ]

    data = defaultdict(list)

    for row_index, row in enumerate(row_list):
        if row_index == 0:
            continue

        # Ignore run 0 (warmup)
        source_column_index: int | None = input_columns.get("user-tags\\.run")
        if not source_column_index:
            continue
        if row[source_column_index] == "0":
            continue

        # Get service_time row
        source_column_index = input_columns.get("name")
        if not source_column_index:
            continue
        if row[source_column_index] != "service_time":
            continue

        # Get p90 service_time values for each operation
        processed_row: list[str] = []
        for column_name in output_column_order:
            source_column_index = input_columns.get(column_name)
            column_value: str = "(null)" if source_column_index is None else row[source_column_index]
            processed_row.append(column_value)
        data[processed_row[0]].append(float(processed_row[1]))

    return data


def similar(file_name: str, folder: Path) -> list[Path]:
    """Find similar files in a folder."""
    rv: list[Path] = []
    for file in sorted(folder.iterdir()):
        if file.name.endswith(file_name):
            rv.extend([file])
    return rv


def match(folder_a: Path, folder_b: Path) -> list[tuple[Path, Path]]:
    """Match files to compare from folders."""
    files = []
    for file_a in folder_a.iterdir():
        file_name = "-".join(file_a.name.split("-")[3:])
        files_b = similar(file_name, folder_b)
        if files_b:
            files.extend([(file_a, file_b) for file_b in files_b if file_b.exists()])
        else:
            logger.warning("File %s not found in %s", file_a, folder_b)
    return files


def diff_folders(folder_a: Path, folder_b: Path) -> None:
    """Diffs two folders of benchmark results."""
    logger.info("Diffing folders %s and %s", folder_a, folder_b)

    # Match files to compare from folders
    files = match(folder_a, folder_b)

    def get_bounds(data: list[float]) -> tuple[float, float]:
        """Get lower and upper bounds."""
        return 0, max(data) * 1.5

    def is_outlier(data: list[float], lower_bound: float, upper_bound: float) -> bool:
        """Check if data contains an outlier."""
        outliers = [x for x in data if x < lower_bound or x > upper_bound]
        if len(outliers) > 0:
            logger.info("Data B: %s", data)
            logger.info("Lower bound: %s | Upper bound: %s", lower_bound, upper_bound)
        return len(outliers) > 0

    def has_outlier(file_a: Path, file_b: Path, data_a: dict[str, list[float]], data_b: dict[str, list[float]]) -> bool:
        """Check if data_a has outliers compared to data_b."""
        rv: bool = False

        # For each operation
        for operation, values_a in data_a.items():
            if operation not in data_b:
                continue

            # Check if data_b has outliers compared to data_a
            values_b = data_b[operation]
            if is_outlier(values_b, *get_bounds(values_a)):
                logger.info("Data A: %s", values_a)
                logger.warning(
                    "Outlier detected for %s in %s (B) compared to %s (A)", operation, file_b.name, file_a.name
                )
                logger.info("+" * 100)
                rv = True
        return rv

    workloads: set = set()

    # For each file (a benchmark test) to compare
    for file_a, file_b in files:
        # Get workload names
        workload = file_a.name.split("-")[5]

        # Retrieve data from files
        data_a = get_service_times(file_a)
        data_b = get_service_times(file_b)

        # Check if data_b has outliers compared to data_a
        if has_outlier(file_a, file_b, data_a, data_b) or has_outlier(file_b, file_a, data_b, data_a):
            workloads.add(workload)

    logger.info("Summary: Workloads with outliers detected: %s", workloads)
