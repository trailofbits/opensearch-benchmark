from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from itertools import product

from report_generator.common import get_workload_operations,get_workload_operation_categories

from googleapiclient.discovery import Resource

@dataclass
class Summary:
    """Class for creating Summary sheet"""

    service: Resource
    spreadsheet_id: str


    def create_summary_table(self, workload: str, os_version: str, es_version: str) -> list[list[str]]:
        """Creates a summary table for a workload and OS vs. ES engine version"""
        rows: list[list[str]] = []

        number_of_operations=len(get_workload_operations(workload))

        # Add overview of results
        rows.append([f"{workload}",f"ES v{es_version}",""])
        rows.append(["Total Tasks",f"=ROWS(UNIQUE(FILTER(Results!$C$2:$C,Results!$A$2:$A=\"{workload}\")))"])
        rows.append(["Tasks faster than ES",f"=COUNTIFS(Results!$A$2:$A,\"{workload}\", Results!$D$2:$D,\">1\")"])
        rows.append(["Fast Outliers (> 2)",f"=COUNTIFS(Results!$A$2:$A,\"{workload}\", Results!$D$2:$D,\">2\")"])
        rows.append(["Slow Outliers (< 0.5)",f"=COUNTIFS(Results!$A$2:$A,\"{workload}\", Results!$D$2:$D,\"<0.5\")"])
        rows.append([])

        # Add categories OS is faster
        rows.append(["",f"Categories: OS v{os_version} is Faster",""])
        rows.append(["Category","Count","Total"])

        categories = get_workload_operation_categories(workload)
        if categories is None:
            return []

        row = [f"=SORT(UNIQUE(FILTER(Results!$B$2:$B,Results!$A$2:$A=\"{workload}\")))"]
        for _ in categories:
            row.append(
                f"=COUNTIFS(Results!$A$2:$A,\"{workload}\", Results!$B$2:$B,INDIRECT(ADDRESS(ROW(),COLUMN()-1)), Results!$D$2:$D,\">1\")"
            )
            row.append(
                f"=COUNTIFS(Results!$A$2:$A,\"{workload}\", Results!$B$2:$B,INDIRECT(ADDRESS(ROW(),COLUMN()-2)))"
            )
            rows.append(row)
            row = [""]
        rows.append([])
        size = len(categories)+1
        rows.append(["Total",
                     f"=SUM(INDIRECT( ADDRESS(ROW()-{size},COLUMN())&\":\"&ADDRESS(ROW()-2,COLUMN()) ))",
                     f"=SUM(INDIRECT( ADDRESS(ROW()-{size},COLUMN())&\":\"&ADDRESS(ROW()-2,COLUMN()) ))"
                   ])
        rows.append([])

        # Add operations OS is faster
        rows.append(["",f"Operations: OS v{os_version} is Faster",""])
        rows.append(["Category","Operation","ES/OS"])
        rows.append([f"=SORT(SORT(FILTER(Results!$B$2:$D, Results!$A$2:$A=\"{workload}\", Results!$D$2:$D > 1), 3, FALSE), 1, TRUE)","",""])
        for _ in range(number_of_operations):
            rows.append([])
        rows.append([])

        # Add operations OS is slower
        rows.append(["",f"Operations: OS v{os_version} is Slower",""])
        rows.append(["Category","Operation","ES/OS"])
        rows.append([f"=SORT(SORT(FILTER(Results!$B$2:$D, Results!$A$2:$A=\"{workload}\", Results!$D$2:$D < 1), 3, FALSE), 1, TRUE)","",""])
        for _ in range(number_of_operations):
            rows.append([])
        rows.append([])

        return rows


    def create_summary_tables(self, workload: str, engines: dict[str,set[str]], index: int) -> int:
        """Creates summary tables for each engine for this workload"""
        if "OS" not in engines:
            print("Error, no OS engines found")
            return index
        if "ES" not in engines:
            print("Error, no ES engines found")
            return index

        rows: list[list[str]] = []

        # Get most recent version of os_version
        os_version = sorted(engines["OS"])[0]

        for es_version in sorted(engines["ES"],reverse=True):
            # Retrieve operation comparison
            col = self.create_summary_table(workload,os_version,es_version)
            rows.extend(col)

        # Append table to Result sheet
        request_properties: dict = {
            "majorDimension": "ROWS",
            "values": rows,
        }
        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"Summary!F{index}",
            valueInputOption="USER_ENTERED",
            body=request_properties,
        ).execute()

        return index+len(rows)


    def get_workload_engines(self, workload: str, engines: dict[str,set[str]], index: int) -> tuple[list[list[str]], int]:
        """Retrieves list of engines and versions for a workload"""
        rows: list[list[str]] = []

        raw_sheet = "raw"

        for engine,versions in engines.items():
            for version in versions:
                row: list[str] = [
                    engine,
                    version,
                    workload,
                    f"=COUNTA(IFNA(UNIQUE(FILTER({raw_sheet}!$A$2:$A,{raw_sheet}!$C$2:$C=$A{index},{raw_sheet}!$D$2:$D=$B{index},{raw_sheet}!$E$2:$E=$C{index}))))"
                ]

                index += 1

                rows.append(row)

        return rows,index


    def create_overview_table(self, workloads: dict[str,dict[str,set[str]]]) -> None:
        """Creates Overview table in Summary sheet"""
        rows: list[list[str]] = []

        rows.append(["Engine","Version","Workload","Number of Tests"])

        index = 2

        for workload,engines in workloads.items():
            row,index = self.get_workload_engines(workload, engines, index)
            rows.extend(row)

        # Add table to Result sheet
        request_properties: dict = {
            "majorDimension": "ROWS",
            "values": rows,
        }
        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range="Summary!A1",
            valueInputOption="USER_ENTERED",
            body=request_properties,
        ).execute()


    def get_workloads(self) -> dict[str,dict[str,set[str]]]:
        """Retrieves tuples of (engine,version,workload) for benchmarks in the spreadsheet"""

        rv: dict[str,dict[str,set[str]]] = {}

        result: dict = (
            self.service.spreadsheets()
            .values()
            .get(spreadsheetId=self.spreadsheet_id, range="Results!A2:N")
            .execute()
        )
        row_list: list[list[str]] = result.get("values", [])
        for index, row in enumerate(row_list):
            workload,_,_,_,_,os_version,_,_,_,_,_,_,_,es_version = row
            if workload not in rv:
                rv[workload] = dict()

            if "OS" not in rv[workload]:
                rv[workload]["OS"] = set()
            rv[workload]["OS"].add(os_version)

            if "ES" not in rv[workload]:
                rv[workload]["ES"] = set()
            rv[workload]["ES"].add(es_version)

        return rv


    def get(self) -> bool:
        """Processes data in Results sheet to fill in Summary sheet"""

        # Retrieve workload to process and compare
        workloads: dict[str,dict[str,set[str]]] = self.get_workloads()

        # Create overview table
        self.create_overview_table(workloads)

        # For each workload, summarize results
        index = 1
        for workload,engines in workloads.items():
            print(f"Processing {workload}")
            index = self.create_summary_tables(workload,engines,index)

        #TODO
        # Create all categories table

        #TODO
        # Create overall results table

        return True