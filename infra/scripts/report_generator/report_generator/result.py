from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from itertools import product

from report_generator.common import get_workload_operations, get_sheet_id, adjust_sheet_columns
from report_generator.common import get_light_red, get_dark_red, get_light_green, get_dark_green

from googleapiclient.discovery import Resource

@dataclass
class Result:
    """Class for creating Result sheet"""

    service: Resource
    spreadsheet_id: str
    sheet_id: int | None = None


    def format_comparison(self) -> list[dict]:
        """Conditionally formats comparison (ES/OS)"""
        rv: list[dict] = []

        # Value is less than 0.5
        rv.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": self.sheet_id,
                                "startRowIndex": 1,     # Start from second row to avoid headers
                                "startColumnIndex": 3, # Column D
                                "endColumnIndex": 4    # Column E
                            },
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "NUMBER_LESS",
                                "values": [
                                    {"userEnteredValue": "0.5"}
                                ]
                            },
                            "format": {
                                "backgroundColor": get_dark_red()
                            },
                        }
                    },
                    "index": 0
                }
            })

        # Value is between 0.5 and 1
        rv.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": self.sheet_id,
                                "startRowIndex": 1,     # Start from second row to avoid headers
                                "startColumnIndex": 3, # Column D
                                "endColumnIndex": 4    # Column E
                            },
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "NUMBER_BETWEEN",
                                "values": [
                                    {"userEnteredValue": "0.5"},
                                    {"userEnteredValue": "1"}
                                ]
                            },
                            "format": {
                                "backgroundColor": get_light_red()
                            },
                        }
                    },
                    "index": 1
                }
            })

        # Value is between 1 and 2
        rv.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": self.sheet_id,
                                "startRowIndex": 1,     # Start from second row to avoid headers
                                "startColumnIndex": 3, # Column D
                                "endColumnIndex": 4    # Column E
                            },
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "NUMBER_BETWEEN",
                                "values": [
                                    {"userEnteredValue": "1"},
                                    {"userEnteredValue": "2"}
                                ]
                            },
                            "format": {
                                "backgroundColor": get_light_green()
                            },
                        }
                    },
                    "index": 2
                }
            })

        # Value is greater than 2
        rv.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": self.sheet_id,
                                "startRowIndex": 1,     # Start from second row to avoid headers
                                "startColumnIndex": 3, # Column D
                                "endColumnIndex": 4    # Column E
                            },
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "NUMBER_GREATER",
                                "values": [
                                    {"userEnteredValue": "2"}
                                ]
                            },
                            "format": {
                                "backgroundColor": get_dark_green()
                            },
                        }
                    },
                    "index": 3
                }
            })


        return rv


    def format_rsd(self) -> dict:
        """Conditionally formats RSD columns"""

        return {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": self.sheet_id,
                                "startRowIndex": 1,     # Start from second row to avoid headers
                                "startColumnIndex": 10, # Column K
                                "endColumnIndex": 12    # Column L
                            },
                            {
                                "sheetId": self.sheet_id,
                                "startRowIndex": 1,     # Start from second row to avoid headers
                                "startColumnIndex": 18, # Column S
                                "endColumnIndex": 20    # Column T
                            }
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "NUMBER_GREATER",
                                "values": [
                                    {
                                        "userEnteredValue": "0.05"
                                    }
                                ]
                            },
                            "format": {
                                "backgroundColor": get_light_red()
                            }
                        }
                    },
                    "index": 0
                }
            }


    def format_freeze_row(self) -> dict:
        """Freezes rows"""

        return {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": self.sheet_id,
                    "gridProperties": {
                        "frozenRowCount": 1
                    }
                },
                "fields": "gridProperties.frozenRowCount"
            }
        }


    def format_freeze_col(self) -> dict:
        """Freezes columns"""

        return {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": self.sheet_id,
                    "gridProperties": {
                        "frozenColumnCount": 4
                    }
                },
                "fields": "gridProperties.frozenColumnCount"
            }
        }


    def format_first_row(self) -> dict:
        """Formats first row"""
        return {
                "repeatCell": {
                    "range": {
                        "sheetId": self.sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {
                                "bold": True
                            }
                        }
                    },
                    "fields": "userEnteredFormat.textFormat.bold"
                }
            }


    def format(self):
        """Format Result sheet"""

        requests = []
        requests.append(self.format_first_row())
        requests.append(self.format_freeze_row())
        requests.append(self.format_freeze_col())
        requests.append(self.format_rsd())
        requests.append(self.format_comparison())

        body = {
            "requests": requests
        }
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body=body
        ).execute()


    def get_workload_operations(self, index: int, workload: str, os: str, es: str, operations: list[str]) -> list[list[str]]:
        """Retrieves workload operation results for one OS/ES engine combination"""
        rows: list[list[str]] = []

        # For each operation, retrieve OS/ES engine results
        for op in operations:
            raw_sheet = "raw"

            # Match workload name, non-zeroth run, operation name, and service_time
            base = f"{raw_sheet}!$E$2:$E=$A{index}," \
                   f"{raw_sheet}!$G$2:$G<>0," \
                   f"{raw_sheet}!$H$2:$H=$C{index}," \
                   f"{raw_sheet}!$I$2:$I=\"service_time\""

            # Match above, plus OS engine and version
            os_stat = f"{raw_sheet}!$C$2:$C=\"OS\"," \
                      f"{raw_sheet}!$D$2:$D=\"{os}\"," \
                      + base

            # Match above, plus ES engine and version
            es_stat = f"{raw_sheet}!$C$2:$C=\"ES\"," \
                      f"{raw_sheet}!$D$2:$D=\"{es}\","\
                      + base

            cell_os_p50_stdev = f"G{index}"
            cell_os_p90_stdev = f"H{index}"
            cell_os_p50_avg = f"I{index}"
            cell_os_p90_avg = f"J{index}"
            cell_os_p50_rsd = f"K{index}"
            cell_os_p90_rsd = f"L{index}"

            cell_es_p50_stdev = f"O{index}"
            cell_es_p90_stdev = f"P{index}"
            cell_es_p50_avg = f"Q{index}"
            cell_es_p90_avg = f"R{index}"
            cell_es_p50_rsd = f"S{index}"
            cell_es_p90_rsd = f"T{index}"
            
            row: list[str] = [
                workload,   # Workload column
                f"=VLOOKUP(C{index}, FILTER(Categories!$B$2:$C, Categories!$A2:$A = $A{index}), 2, FALSE)",  # Category column
                op,         # Operation column
                f"={cell_es_p90_avg}/{cell_os_p90_avg}",  # ES/OS comparison column
                "",         # Blank column
                os,   # OS version column
                f"=STDEV.S(FILTER({raw_sheet}!$J$2:$J, {os_stat}))", # p50 stdev
                f"=STDEV.S(FILTER({raw_sheet}!$K$2:$K, {os_stat}))", # p90 stdev
                f"=AVERAGE(FILTER({raw_sheet}!$J$2:$J, {os_stat}))", # p50 avg
                f"=AVERAGE(FILTER({raw_sheet}!$K$2:$K, {os_stat}))", # p90 avg
                f"={cell_os_p50_stdev}/{cell_os_p50_avg}",  # p50 rsd
                f"={cell_os_p90_stdev}/{cell_os_p90_avg}",  # p50 rsd
                "",         # Blank column
                es,   # ES version column
                f"=STDEV.S(FILTER({raw_sheet}!$J$2:$J, {es_stat}))", # p50 stdev
                f"=STDEV.S(FILTER({raw_sheet}!$K$2:$K, {es_stat}))", # p90 stdev
                f"=AVERAGE(FILTER({raw_sheet}!$J$2:$J, {es_stat}))", # p50 avg
                f"=AVERAGE(FILTER({raw_sheet}!$K$2:$K, {es_stat}))", # p90 avg
                f"={cell_es_p50_stdev}/{cell_es_p50_avg}",  # p50 rsd
                f"={cell_es_p90_stdev}/{cell_es_p90_avg}",  # p50 rsd
            ]

            rows.append(row)
            index += 1

        return rows


    def compare_engine(self, offset: int, workload: str, operations: list[str], engines: dict[str,set[str]]) -> int:
        """
        Fills in Result sheet with combination of engine comparisons.
        Returns the number of rows written.
        """

        if "OS" not in engines:
            print("Error, no OS engines found")
            return 0
        if "ES" not in engines:
            print("Error, no ES engines found")
            return 0

        # For each combination of OS/ES engines
        for os,es in product(engines["OS"], engines["ES"]):
            print(f"\tComparing OS {os} versus ES {es}")

            # Retrieve operation comparison
            rows = self.get_workload_operations(offset,workload,os,es,operations)

            # Append table to Result sheet
            request_properties: dict = {
                "majorDimension": "ROWS",
                "values": rows,
            }
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range="Results!A1",
                valueInputOption="USER_ENTERED",
                body=request_properties,
            ).execute()

            offset += len(rows)

        return offset


    def get_workloads(self) -> dict[str,dict[str,set[str]]]:
        """Retrieves tuples of (engine,version,workload) for all benchmarks in the spreadsheet"""

        rv: dict[str,dict[str,set[str]]] = {}

        result: dict = (
            self.service.spreadsheets()
            .values()
            .get(spreadsheetId=self.spreadsheet_id, range="raw!C2:E")
            .execute()
        )
        row_list: list[list[str]] = result.get("values", [])
        for index, row in enumerate(row_list):
            engine,version,workload = row
            if workload not in rv:
                rv[workload] = dict()
            if engine not in rv[workload]:
                rv[workload][engine] = set()
            rv[workload][engine].add(version)

        return rv


    def get(self) -> bool:
        """Processes data in raw sheet to fill in Results sheet"""

        # Get sheet ID for Results sheet
        self.sheet_id = get_sheet_id(self.service, self.spreadsheet_id, "Results")

        # Retrieve workload to process and compare
        workloads: dict[str,dict[str,set[str]]] = self.get_workloads()

        # Offset for keeping track of the number of rows we've filled in
        # We start with 2 because the header row is already filled in
        offset: int = 2

        # For each workload, process engine results
        for workload,engines in workloads.items():
            print(f"Processing {workload}")

            # Retrieve operations for this workload
            operations = get_workload_operations(workload)
            if operations is None:
                print("Error, no operations found for workload")
                continue

            # Output engine comparisons in Result sheet
            offset = self.compare_engine(offset,workload,operations,engines)

        # Format Result sheet
        self.format()

        # Adjust columns
        adjust_sheet_columns(self.service, self.spreadsheet_id, "Results")

        return True