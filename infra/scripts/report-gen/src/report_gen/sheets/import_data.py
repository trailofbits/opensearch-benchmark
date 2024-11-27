"""Class for importing benchmark data."""

import csv
import logging
from dataclasses import dataclass
from pathlib import Path

from googleapiclient.discovery import Resource

logger = logging.getLogger(__name__)


@dataclass
class ImportData:
    """Class for importing benchmark data."""

    service: Resource
    spreadsheet_id: str
    folder: Path

    @staticmethod
    def workload_subtype(processed_row: list[str]) -> str:
        """Get a subtype for a workload.

        This is relevant for workloads which have multiple configurations (vectorsearch).
        """
        engine_type = processed_row[2]
        workload = processed_row[4]
        if workload != "vectorsearch":
            return ""

        query_data_set_corpus = processed_row[18]
        target_index_body = processed_row[19]
        vector_index_body_lookup = {
            "indices/faiss-index.json": "faiss",
            "indices/nmslib-index.json": "nmslib",
            "indices/lucene-index.json": "lucene",
        }
        if engine_type == "ES":
            subtype_dataset = "lucene"
        else:
            subtype_dataset = vector_index_body_lookup.get(target_index_body, "unknown")
        return f"{subtype_dataset}-{query_data_set_corpus}"

    def read_rows(self, csv_path: Path) -> list[list[str]]:
        """Read CSV data."""
        row_list: list[list[str]]
        with csv_path.open() as csv_file:
            csv_reader = csv.reader(csv_file)
            row_list = list(csv_reader)

        input_columns: dict[str, int] = {header_column: index for index, header_column in enumerate(row_list[0])}

        # When changing this, make sure to update the formulas
        output_column_order: list[str] = [
            "user-tags\\.run-group",
            "environment",
            "user-tags\\.engine-type",
            "distribution-version",
            "workload",
            "workload_subtype",
            "test-procedure",
            "user-tags\\.run",
            "operation",
            "name",
            "value\\.50_0",
            "value\\.90_0",
            "workload\\.target_throughput",
            "workload\\.number_of_replicas",
            "workload\\.bulk_indexing_clients",
            "workload\\.max_num_segments",
            "user-tags\\.shard-count",
            "user-tags\\.replica-count",
            "workload\\.query_data_set_corpus",
            "workload\\.target_index_body",
        ]

        processed_row_list: list[list[str]] = [output_column_order]

        for row_index, row in enumerate(row_list):
            if row_index == 0:
                continue

            processed_row: list[str] = []
            for column_name in output_column_order:
                source_column_index: int | None = input_columns.get(column_name)
                column_value: str = "(null)" if source_column_index is None else row[source_column_index]
                processed_row.append(column_value)

            workload_subtype = ImportData.workload_subtype(processed_row)
            processed_row[5] = workload_subtype
            processed_row_list.append(processed_row)

        return processed_row_list

    def get(self) -> bool:
        """Import benchmark data into spreadsheet."""
        # Get CSV files
        csv_files = self.folder.glob("*.csv")

        # Read rows in files
        raw_data: list[list[str]] = []
        for fn in csv_files:
            logging.info(f"Processing {fn.name}")

            rows = self.read_rows(fn)

            # Add the header row
            if not raw_data:
                raw_data.extend([rows[0]])
            # Add the data rows
            raw_data.extend(rows[1:])

        # Import data to spreadsheet
        request_properties: dict = {
            "majorDimension": "ROWS",
            "values": raw_data,
        }
        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range="raw!A1",
            valueInputOption="USER_ENTERED",
            body=request_properties,
        ).execute()

        return True
