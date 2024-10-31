from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from itertools import product

from report_generator.common import get_workload_operations

from googleapiclient.discovery import Resource

@dataclass
class Summary:
    """Class for creating Summary sheet"""

    service: Resource
    spreadsheet_id: str


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

        #TODO
        # For each workload, summarize results
        for workload,engines in workloads.items():
            print(f"Processing {workload}")

        #TODO
        # Create all categories table

        #TODO
        # Create overall results table

        return True