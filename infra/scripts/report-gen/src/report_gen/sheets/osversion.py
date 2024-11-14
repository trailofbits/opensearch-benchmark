"""Class for creating OS Versions sheet."""

import logging
from dataclasses import dataclass

from googleapiclient.discovery import Resource

from .common import (
    adjust_sheet_columns,
    convert_range_to_dict,
    get_sheet_id,
    get_workload_operations,
    get_workload_operation_categories,
    get_workloads,
)

logger = logging.getLogger(__name__)


@dataclass
class OSVersion:
    """Class for creating OS Version sheets."""

    service: Resource
    spreadsheet_id: str
    sheet_id: int | None = None
    sheet: dict | None = None

    def get(self) -> bool:
        """Retrieve data to fill in OS Version sheets."""
        workload_str = "big5"
        # NOTE(Evan): These correspond to the OS version sheet names in _create_spreadsheet() in __init__.py
        os_versions = ["2.16.0", "2.17.0", "2.18.0"]

        # Retrieve workload to process and compare
        workloads: dict[str, dict[str, list[str]]] = get_workloads(self.service, self.spreadsheet_id)

        if workload_str not in workloads:
            logger.error(f"Error, workload {workload_str} not found.")
            return False

        # Retrieve operations for workload
        operations = get_workload_operations(workload_str)
        if len(operations) == 0:
            logger.error(f"Error, no operations found for workload {workload_str}")
            return False

        # Retrieve operations categories for workload
        categories = get_workload_operation_categories(workload_str)
        if len(categories) == 0:
            logger.error(f"Error, no operation categories found for workload {workload_str}")
            return False

        # For each OS version
        for osv in os_versions:
            if osv not in workloads[workload_str]["OS"]:
                continue
            logger.info(f"Version: {osv}")

        return True
