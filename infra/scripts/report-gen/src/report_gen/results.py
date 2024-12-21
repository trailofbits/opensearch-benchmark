"""Calculate Results."""

import logging
from collections import defaultdict
from dataclasses import dataclass
from itertools import cycle, product
from pathlib import Path
from statistics import mean, median, stdev, variance
from typing import TYPE_CHECKING

from packaging import version

from .common import get_category, get_category_operation_map
from .download import BenchmarkResult
from .google_sheets import (
    LIGHT_BLUE,
    LIGHT_GRAY,
    LIGHT_GREEN,
    LIGHT_ORANGE,
    LIGHT_PURPLE,
    LIGHT_YELLOW,
    SheetBuilder,
    SpreadSheetBuilder,
)

if TYPE_CHECKING:
    from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VersionPair:
    """A pair of OS/ES versions to be compared."""

    os_version: str
    es_version: str


@dataclass
class Result:
    """Store Results."""

    workload: str
    category: str
    operation: str

    os_version: str
    os_subtype: str
    os_std_50: float
    os_std_90: float
    os_avg_50: float
    os_avg_90: float
    os_rsd_50: float
    os_rsd_90: float

    es_version: str
    es_subtype: str
    es_std_50: float
    es_std_90: float
    es_avg_50: float
    es_avg_90: float
    es_rsd_50: float
    es_rsd_90: float
    comparison: float

    @property
    def relative_diff(self) -> float:
        """(ES-OS) / AVG(ES,OS)."""
        es = self.es_avg_90
        os = self.os_avg_90
        return (es - os) / mean([es, os])

    @property
    def ratio(self) -> float:
        """ES / OS."""
        return self.es_avg_90 / self.os_avg_90


def build_results(data: list[BenchmarkResult], comparisons: list[VersionPair]) -> list[Result]:  # noqa: C901, PLR0912, PLR0915
    """Build the results data from the raw benchmark results."""
    sub_groups: dict[str, dict[str, list[BenchmarkResult]]] = defaultdict(lambda: defaultdict(list))

    # Filter down to relevant runs, storing rows by their workload and operation
    for row in data:
        # Do not use the first run in our statistics and only include service_time metrics
        if row.Run == "0" or row.MetricName != "service_time":
            continue
        workload = row.Workload
        operation = row.Operation
        sub_groups[workload][operation] += [row]

    # Get all subtypes once
    subtypes = sorted({d.WorkloadSubType for d in data})

    results = []
    for workload, operations in sub_groups.items():
        for operation, rows in operations.items():
            category = get_category(workload, operation)
            if category is None:
                raise RuntimeError(f"No category for {workload} {operation}")  # noqa: TRY003, EM102

            os_rows = [row for row in rows if row.Engine == "OS"]
            es_rows = [row for row in rows if row.Engine == "ES"]
            for compare in comparisons:
                os_data = [row for row in os_rows if row.EngineVersion == compare.os_version]
                if len(os_data) == 0:
                    raise RuntimeError(f"No data for OS {compare.os_version}")  # noqa: TRY003, EM102
                es_data = [row for row in es_rows if row.EngineVersion == compare.es_version]
                if len(es_data) == 0:
                    raise RuntimeError(f"No data for OS {compare.es_version}")  # noqa: TRY003, EM102

                def verify_data(engine: str, workload: str, operation: str, data: list[BenchmarkResult]) -> None:
                    """Check assumptions about the data before reporting stats."""
                    runs = defaultdict(set)
                    for d in data:
                        runs[d.RunGroup].add(d.Run)
                    # We expect each run group to have 4 data points
                    # Technically 5 but we disregard run 0
                    for group, run_counts in runs.items():
                        if run_counts != {"1", "2", "3", "4"}:
                            msg = f"{engine}-{workload}-{operation} {group} expected 4 runs but got {run_counts}"
                            raise RuntimeError(msg)

                verify_data("OS", workload, operation, os_data)
                verify_data("ES", workload, operation, es_data)

                def build_result(  # noqa: PLR0913
                    workload: str,
                    category: str,
                    operation: str,
                    os_version: str,
                    os_data: list[BenchmarkResult],
                    es_version: str,
                    es_data: list[BenchmarkResult],
                    os_subtype: str = "",
                    es_subtype: str = "",
                ) -> Result:
                    os_std_50 = stdev(float(row.P50) for row in os_data)
                    os_std_90 = stdev(float(row.P90) for row in os_data)
                    os_avg_50 = mean(float(row.P50) for row in os_data)
                    os_avg_90 = mean(float(row.P90) for row in os_data)
                    os_rsd_50 = os_std_50 / os_avg_50
                    os_rsd_90 = os_std_90 / os_avg_90

                    es_std_50 = stdev(float(row.P50) for row in es_data)
                    es_std_90 = stdev(float(row.P90) for row in es_data)
                    es_avg_50 = mean(float(row.P50) for row in es_data)
                    es_avg_90 = mean(float(row.P90) for row in es_data)
                    es_rsd_50 = es_std_50 / es_avg_50
                    es_rsd_90 = es_std_90 / es_avg_90

                    comparison = es_avg_90 / os_avg_90
                    return Result(
                        workload=workload,
                        category=category,
                        operation=operation,
                        os_version=os_version,
                        os_subtype=os_subtype,
                        os_std_50=os_std_50,
                        os_std_90=os_std_90,
                        os_avg_50=os_avg_50,
                        os_avg_90=os_avg_90,
                        os_rsd_50=os_rsd_50,
                        os_rsd_90=os_rsd_90,
                        es_version=es_version,
                        es_subtype=es_subtype,
                        es_std_50=es_std_50,
                        es_std_90=es_std_90,
                        es_avg_50=es_avg_50,
                        es_avg_90=es_avg_90,
                        es_rsd_50=es_rsd_50,
                        es_rsd_90=es_rsd_90,
                        comparison=comparison,
                    )

                # NOTE: Consider not hardcoding this in the future
                if workload == "vectorsearch":
                    for os_workload_subtype in subtypes:
                        # Get size to compare
                        es_workload_subtype = "lucene-cohere-"
                        if "-1m" in os_workload_subtype:
                            es_workload_subtype = f"{es_workload_subtype}1m"
                        elif "-10m" in os_workload_subtype:
                            es_workload_subtype = f"{es_workload_subtype}10m"
                        else:
                            es_workload_subtype = f"{es_workload_subtype}1m"

                        os_subtype_data = [d for d in os_data if d.WorkloadSubType == os_workload_subtype]
                        es_subtype_data = [d for d in os_data if d.WorkloadSubType == es_workload_subtype]
                        if len(os_subtype_data) == 0 and len(es_subtype_data) == 0:
                            continue
                        results.append(
                            build_result(
                                workload,
                                category,
                                operation,
                                compare.os_version,
                                os_subtype_data,
                                compare.es_version,
                                es_subtype_data,
                                os_workload_subtype,
                                es_workload_subtype,
                            )
                        )

                else:
                    results.append(
                        build_result(
                            workload, category, operation, compare.os_version, os_data, compare.es_version, es_data
                        )
                    )

    return results


def dump_results(results: list[Result], sheet: SheetBuilder) -> None:
    """Fill the supplied sheet with data from Results."""
    header = [
        [
            "Workload",
            "Category",
            "Operation",
            "Comparison\nES/OS",
            "",
            "OS version",
            "OS SubType",
            "OS: STDEV 50",
            "OS: STDEV 90",
            "OS: Average 50",
            "OS: Average 90",
            "OS: RSD 50",
            "OS: RSD 90",
            "",
            "ES version",
            "ES SubType",
            "ES: STDEV 50",
            "ES: STDEV 90",
            "ES: Average 50",
            "ES: Average 90",
            "ES: RSD 50",
            "ES: RSD 90",
        ]
    ]
    sheet_rows = header + [
        [
            row.workload,
            row.category,
            row.operation,
            str(row.comparison),
            "",
            row.os_version,
            row.os_subtype,
            str(row.os_std_50),
            str(row.os_std_90),
            str(row.os_avg_50),
            str(row.os_avg_90),
            str(row.os_rsd_50),
            str(row.os_rsd_90),
            "",
            row.os_version,
            row.es_subtype,
            str(row.os_std_50),
            str(row.os_std_90),
            str(row.os_avg_50),
            str(row.os_avg_90),
            str(row.os_rsd_50),
            str(row.os_rsd_90),
        ]
        for row in results
    ]

    nrows = len(sheet_rows)

    sheet.insert_rows("A1", sheet_rows)
    fmt = sheet.format_builder()
    fmt.bold_font("A1:V1")
    fmt.freeze_row(1)
    fmt.freeze_col(4)
    for r in [f"D2:D{nrows}", f"G2:G{nrows}", f"O2:T{nrows}"]:
        fmt.style_float(r)
    fmt.color_comparison(f"D2:D{nrows}")
    fmt.rsd(f"L2:M{nrows}")
    fmt.rsd(f"U2:V{nrows}")
    fmt.apply()


@dataclass
class VersionCompareTable:
    """Represents a table comparing a single OS and ES version."""

    @dataclass
    class Row:
        """One row of data in the table."""

        category: str
        operation: str
        es_p90_st: float
        es_p90_rsd: float
        os_p90_st: float
        os_p90_rsd: float

        @property
        def relative_diff(self) -> float:
            """(es - os) / avg(es, os)."""
            es = self.es_p90_st
            os = self.os_p90_st
            return (es - os) / mean([es, os])

        @property
        def ratio(self) -> float:
            """ES / OS."""
            return self.es_p90_st / self.os_p90_st

    comparison: VersionPair
    workload: str
    rows: list["VersionCompareTable.Row"]


def build_version_compare_tables(workload: str, results: list[Result]) -> list[VersionCompareTable]:
    """Build a version comparison table for each OS version pair in results."""
    grouped = defaultdict(list)
    for row in results:
        if row.workload == workload:
            grouped[VersionPair(row.os_version, row.es_version)].append(row)

    return [
        VersionCompareTable(
            comparison,
            workload,
            [
                VersionCompareTable.Row(
                    category=row.category,
                    operation=row.operation,
                    es_p90_st=row.es_avg_90,
                    es_p90_rsd=row.es_rsd_90,
                    os_p90_st=row.os_avg_90,
                    os_p90_rsd=row.os_rsd_90,
                )
                for row in rows
            ],
        )
        for comparison, rows in grouped.items()
    ]


def dump_version_compare_table(table: VersionCompareTable, sheet: SheetBuilder) -> None:
    """Fill the table data into the provided sheet."""
    fmt = sheet.format_builder()
    # Top Header Row
    sheet.insert_rows("A1", [["Results"]])
    fmt.merge("A1:F1")
    fmt.bold_font("A1:I1")
    fmt.color("A1:F1", LIGHT_GRAY)
    # 2nd header row
    sheet.insert_rows(
        "A2",
        [
            [
                "Category",
                "Operation",
                f"ES {table.comparison.es_version} P90 ST (AVG)",
                "RSD",
                f"OS {table.comparison.os_version} P90 ST (AVG)",
                "RSD",
                "Relative Difference\n(ES-OS)/AVG(ES,OS)",
                f"Ratio ES {table.comparison.es_version} / OS {table.comparison.os_version}",
                "Comments",
            ]
        ],
    )
    fmt.bold_font("A2:I2")
    fmt.merge("G1:G2")
    fmt.merge("H1:H2")
    fmt.color("A2:I2", LIGHT_GRAY)
    fmt.color("G1:G2", LIGHT_YELLOW)
    fmt.color("H1:H2", LIGHT_BLUE)

    # Group data by category
    grouped = defaultdict(list)
    for row in table.rows:
        grouped[row.category].append(row)

    offset = 3
    for category, rows in sorted(grouped.items()):
        sheet.insert_rows(
            f"A{offset}",
            [
                [
                    category,
                    row.operation,
                    str(row.es_p90_st),
                    str(row.es_p90_rsd),
                    str(row.os_p90_st),
                    str(row.os_p90_rsd),
                    str(row.relative_diff),
                    str(row.ratio),
                ]
                for row in sorted(rows, key=lambda r: r.operation)
            ],
        )
        end = offset + len(rows)
        fmt.merge(f"A{offset}:A{end-1}")
        fmt.bold_font(f"A{offset}:A{end-1}")
        fmt.color(f"A{offset}:A{end-1}", LIGHT_GRAY)
        offset = end

    # Format all data as float
    fmt.style_float(f"C3:H{offset+1}")
    # Format Relative Diff Column
    fmt.color_relative_difference(f"G3:G{offset+1}")
    # Format Ratio Column
    fmt.color_comparison(f"H3:H{offset+1}")

    fmt.apply()


@dataclass
class OverallSpread:
    """Represents a table comparing multiple ES/OS versions for a single workload."""

    p90s: dict[str, dict[str, dict[str, float]]]
    """Map category -> operation -> engine+version to raw p90 vals"""

    relative_diffs: dict[str, dict[str, dict[str, float]]]
    """Map category -> operation -> engine+version comparison to relative diffs"""

    ratios: dict[str, dict[str, dict[str, float]]]
    """Map category -> operation -> engine+version comparison to ratios"""

    @property
    def p90_headers(self) -> list[str]:
        """Sorted list of engine versions in this table."""
        return sorted({e for ops in self.p90s.values() for engines in ops.values() for e in engines})

    @property
    def relative_diff_headers(self) -> list[str]:
        """Sorted list of relative difference labels in this table."""
        return sorted({e for ops in self.relative_diffs.values() for engines in ops.values() for e in engines})

    @property
    def ratio_headers(self) -> list[str]:
        """Sorted list of ratio labels in this table."""
        return sorted({e for ops in self.ratios.values() for engines in ops.values() for e in engines})

    workload: str


def build_overall(tables: list[VersionCompareTable]) -> OverallSpread:
    """Create an overall spread from version comparison tables of a single workload."""
    combined = defaultdict(list)

    workloads = {t.workload for t in tables}
    if len(workloads) != 1:
        msg = "Assumed only one workload is compared at a time"
        raise RuntimeError(msg)
    workload = next(iter(workloads))

    for table in tables:
        es_version = table.comparison.es_version
        os_version = table.comparison.os_version
        for row in table.rows:
            combined[(row.category, row.operation)].append((es_version, os_version, row))

    p90s: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    relative_diffs: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    ratios: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

    for (category, operation), rows in combined.items():
        for es_version, os_version, row in rows:
            p90s[category][operation][f"ES {es_version}"] = row.es_p90_st
            p90s[category][operation][f"OS {os_version}"] = row.os_p90_st
            relative_diffs[category][operation][f"ES {es_version} vs OS {os_version}"] = row.relative_diff
            ratios[category][operation][f"ES {es_version} /\n OS {os_version}"] = row.ratio

    return OverallSpread(p90s, relative_diffs, ratios, workload)


def dump_overall(overall: OverallSpread, sheet: SheetBuilder) -> None:
    """Fill in the provided sheet with data from the overall spread table."""
    fmt = sheet.format_builder()

    # top header
    sheet.insert_rows(
        "A1",
        [
            ["Results"]
            + [""]
            + [""] * len(overall.p90_headers)
            + ["Relative Difference\n(ES-OS)/AVG(ES,OS)"]
            + [""] * (len(overall.relative_diff_headers) - 1)
            + ["Ratio ES/OS"]
            + [""] * (len(overall.ratio_headers) - 1)
        ],
    )

    def itoa(i: int) -> str:
        return chr(ord("A") + i)

    results_end = len(overall.p90_headers) + 1
    results_range = f"A1:{itoa(results_end)}1"

    relative_diff_start = results_end + 1
    relative_diff_end = relative_diff_start + len(overall.relative_diff_headers) - 1
    rd_range = f"{itoa(relative_diff_start)}1:{itoa(relative_diff_end)}1"

    ratios_start = relative_diff_end + 1
    ratios_end = ratios_start + len(overall.relative_diff_headers) - 1
    ratios_range = f"{itoa(ratios_start)}1:{itoa(ratios_end)}1"

    fmt.merge(results_range)
    fmt.color(results_range, LIGHT_GRAY)

    fmt.merge(rd_range)
    fmt.color(rd_range, LIGHT_YELLOW)

    fmt.merge(ratios_range)
    fmt.color(ratios_range, LIGHT_BLUE)

    fmt.bold_font(f"A1:{itoa(ratios_end)}1")

    # second header
    row2 = (
        ["Category", "Operation"]
        + [f"{e} P90 ST" for e in overall.p90_headers]
        + [f"Relative Difference\n{e}" for e in overall.relative_diff_headers]
        + [f"Ratio {e}" for e in overall.ratio_headers]
    )
    sheet.insert_rows(
        "A2",
        [row2],
    )
    row2_range = f"A2:{itoa(len(row2))}2"
    fmt.bold_font(row2_range)
    fmt.color(row2_range, LIGHT_GRAY)

    offset = 3
    for category in sorted(overall.p90s):
        operations = sorted(overall.p90s[category])
        rows = []
        for operation in operations:
            p90s = [str(overall.p90s[category][operation][e]) for e in overall.p90_headers]
            diffs = [str(overall.relative_diffs[category][operation][e]) for e in overall.relative_diff_headers]
            ratios = [str(overall.ratios[category][operation][e]) for e in overall.ratio_headers]
            rows.append([category, operation, *p90s, *diffs, *ratios])
        sheet.insert_rows(f"A{offset}", rows)
        end = offset + len(rows)
        fmt.merge(f"A{offset}:A{end-1}")
        fmt.bold_font(f"A{offset}:A{end-1}")
        fmt.color(f"A{offset}:A{end-1}", LIGHT_GRAY)
        offset = end

    # Format all data as float
    fmt.style_float(f"C3:{itoa(ratios_end)}{offset+1}")
    # Format Relative Diff Column
    fmt.color_relative_difference(f"{itoa(relative_diff_start)}3:{itoa(relative_diff_end)}{offset+1}")
    # Format Ratio Column
    fmt.color_comparison(f"{itoa(ratios_start)}3:{itoa(ratios_end)}{offset+1}")

    fmt.apply()


def dump_raw(data: list[BenchmarkResult], sheet: SheetBuilder) -> None:
    """Fill the provided sheet with raw data."""
    header = [
        [
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
            "user-tags\\.shard-count",
            "user-tags\\.replica-count",
            "workload\\.target_throughput",
            "workload\\.number_of_replicas",
            "workload\\.bulk_indexing_clients",
            "workload\\.max_num_segments",
            "workload\\.query_data_set_corpus",
            "workload\\.target_index_body",
        ]
    ]
    rows: list[list[str]] = [
        [
            str(result.RunGroup),
            result.Environment,
            result.Engine,
            result.EngineVersion,
            result.Workload,
            result.WorkloadSubType,
            result.TestProcedure,
            result.Run,
            result.Operation,
            result.MetricName,
            result.P50,
            result.P90,
            str(result.ShardCount),
            str(result.ReplicaCount),
            result.WorkloadParams["target_throughput"],
            result.WorkloadParams["number_of_replicas"],
            result.WorkloadParams["bulk_indexing_clients"],
            result.WorkloadParams["max_num_segments"],
            result.WorkloadParams["query_data_set_corpus"],
            result.WorkloadParams["target_index_body"],
        ]
        for result in data
    ]

    sheet.insert_rows("A1", header + rows)


def dump_categories(sheet: SheetBuilder) -> None:
    """Fill the provided sheet with categories data."""
    # Generate the rows in the spreadsheet
    spec_list: list[dict] = get_category_operation_map()
    row_list: list[list[str]] = [["Workload", "Operation", "Category"]]

    for spec in spec_list:
        workload_name: str = spec["workload"]

        for category_name in spec["categories"]:
            for operation_name in spec["categories"][category_name]:
                row_list.append([workload_name, operation_name, category_name])  # noqa: PERF401

    sheet.insert_rows("A1", row_list)


class EngineTable:
    """Table showing the number of tests run for each Engine/Version/Workload combo."""

    @dataclass
    class Row:
        """Single Row in the Engine Table."""

        engine: str
        version: str
        workload: str
        test_count: int

    rows: list[Row]

    def __init__(self, results: list[BenchmarkResult]) -> None:
        # Sort the results by Engine/Version/Workload to be counted
        filtered: dict[tuple[str, str, str], set[datetime]] = defaultdict(set)
        for r in results:
            key = (r.Engine, r.EngineVersion, r.Workload)
            filtered[key].add(r.RunGroup)

        self.rows = [
            EngineTable.Row(
                engine=engine,
                version=version,
                workload=workload,
                test_count=len(grouped_results),
            )
            for (engine, version, workload), grouped_results in filtered.items()
        ]


class AllCategoriesFaster:
    """All Categories Table."""

    @dataclass
    class Row:
        """Row in All Categories Table."""

        category: str
        count: int
        total: int
        percentage: float

    os_version: str
    es_version: str

    total_count: int
    total_total: int
    total_percentage: float

    rows: list[Row]

    def __init__(self, os_version: str, es_version: str, results: list[Result]) -> None:
        by_category = defaultdict(list)
        for row in results:
            if row.os_version != os_version or row.es_version != es_version:
                continue
            by_category[row.category].append(row)

        rows = []
        for category, data in by_category.items():
            count = len([d for d in data if d.comparison > 1])
            total = len(data)
            percentage = (count / total) * 100
            rows.append(AllCategoriesFaster.Row(category=category, count=count, total=total, percentage=percentage))

        self.es_version = es_version
        self.os_version = os_version
        self.total_count = sum([r.count for r in rows])
        self.total_total = sum([r.total for r in rows])
        self.total_percentage = (self.total_count / self.total_total) * 100
        self.rows = rows


class StatsCompareTable:
    """Table comparing overall stats between two versions."""

    class Row:
        """Single row in comparison table."""

        avg: float
        median: float
        mmax: float
        mmin: float
        stdev: float
        variance: float

        def __init__(self, data: list[float]) -> None:
            self.avg = mean(data)
            self.median = median(data)
            self.mmax = max(data)
            self.mmin = min(data)
            self.stdev = stdev(data)
            self.variance = variance(data)

    os_version: str
    es_version: str

    faster: Row
    slower: Row

    def __init__(self, os_version: str, es_version: str, results: list[Result]) -> None:
        version_filtered = [row for row in results if row.os_version == os_version and row.es_version == es_version]
        os_faster = [row.comparison for row in version_filtered if row.comparison > 1]
        os_slower = [row.comparison for row in version_filtered if row.comparison < 1]

        self.os_version = os_version
        self.es_version = es_version
        self.faster = StatsCompareTable.Row(os_faster)
        self.slower = StatsCompareTable.Row(os_slower)


def dump_summary(raw: list[BenchmarkResult], results: list[Result], sheet: SheetBuilder) -> None:  # noqa: PLR0915
    """Fill the provided sheet with summary of Results."""
    # # # # # # # # # # # #
    #   Engine Table      #
    # # # # # # # # # # # #
    engine_table = EngineTable(raw)
    fmt = sheet.format_builder()
    engine_table_rows = [["Engine", "Version", "Workload", "Number of Tests"]] + [
        [
            row.engine,
            row.version,
            row.workload,
            str(row.test_count),
        ]
        for row in sorted(engine_table.rows, key=lambda r: (r.workload, r.version, r.engine))
    ]
    sheet.insert_rows("A1", engine_table_rows)
    # format header
    fmt.color("A1:D1", LIGHT_BLUE)
    fmt.bold_font("A1:D1")
    # color each set of workloads
    colors = cycle([LIGHT_ORANGE, LIGHT_GREEN, LIGHT_PURPLE, LIGHT_YELLOW])
    workload_count: dict[str, int] = defaultdict(int)
    for row in engine_table.rows:
        workload_count[row.workload] += 1
    offset = 2  # skip header row
    for workload in sorted(workload_count):
        count = workload_count[workload]
        fmt.color(f"A{offset}:D{offset+count-1}", next(colors))
        offset += count

    latest_os = str(max([r.os_version for r in results], key=version.parse))
    latest_es = str(max([r.es_version for r in results], key=version.parse))
    logger.info(f"Comparing latest versions: OS {latest_os} - ES {latest_es}")

    # # # # # # # # # # # #
    #   All Categories    #
    # # # # # # # # # # # #
    fast = AllCategoriesFaster(latest_os, latest_es, results)
    fast_rows = (
        [
            [f"All Categories: OS {latest_os} is faster than ES {latest_es}"],
            ["Category", "Count", "Total", "Percentage (%)"],
        ]
        + [
            [
                row.category,
                str(row.count),
                str(row.total),
                str(row.percentage),
            ]
            for row in sorted(fast.rows, key=lambda r: r.category)
        ]
        + [["Total", str(fast.total_count), str(fast.total_total), str(fast.total_percentage)]]
    )
    fast_start_row = len(engine_table_rows) + 2
    sheet.insert_rows(f"A{fast_start_row}", fast_rows)
    # Style Header
    fast_header_range = f"A{fast_start_row}:D{fast_start_row}"
    fmt.bold_font(fast_header_range)
    fmt.merge(fast_header_range)
    fmt.color(fast_header_range, LIGHT_BLUE)
    # Style percentage row
    fmt.style_float(f"D{fast_start_row+2}:D{fast_start_row+len(fast_rows)}")

    # # # # # # # # # # # #
    #   Stats Compare     #
    # # # # # # # # # # # #
    stats = StatsCompareTable(latest_os, latest_es, results)
    stats_rows = [
        [f"Statistics comparing: OS {latest_os} and ES {latest_es}"],
        ["ES/OS", "Average", "Median", "Max", "Min", "Stdev", "Variance"],
        [
            "When OS is faster\n(OS service_time is smaller)",
            str(stats.faster.avg),
            str(stats.faster.median),
            str(stats.faster.mmax),
            str(stats.faster.mmin),
            str(stats.faster.stdev),
            str(stats.faster.variance),
        ],
        [
            "When OS is slower\n(OS service_time is larger)",
            str(stats.slower.avg),
            str(stats.slower.median),
            str(stats.slower.mmax),
            str(stats.slower.mmin),
            str(stats.slower.stdev),
            str(stats.slower.variance),
        ],
    ]
    stat_start_row = fast_start_row + len(fast_rows) + 1
    sheet.insert_rows(f"A{stat_start_row}", stats_rows)
    # Style Header
    stat_header_range = f"A{stat_start_row}:G{stat_start_row}"
    fmt.bold_font(stat_header_range)
    fmt.merge(stat_header_range)
    fmt.color(stat_header_range, LIGHT_BLUE)
    # Style data as float
    fmt.style_float(f"B{stat_start_row+2}:G{stat_start_row+3}")

    # # # # # # # # # # # #
    #  Workload Summaries #
    # # # # # # # # # # # #

    offset = 1
    for workload in sorted({r.workload for r in results}):
        logger.info(f"Summarizing {workload}")
        workload_results = [
            r for r in results if r.workload == workload and r.os_version == latest_os and r.es_version == latest_es
        ]

        # Total Tasks table
        total_tasks = len(workload_results)
        fast_bar = 2
        slow_bar = 0.5
        faster_than_es = len([r for r in workload_results if r.comparison > 1])
        fast_outliers = len([r for r in workload_results if r.comparison > fast_bar])
        slow_outliers = len([r for r in workload_results if r.comparison < slow_bar])
        sheet.insert_rows(
            f"I{offset}",
            [
                [f"{workload}", f"ES {latest_es}"],
                ["Total Tasks", str(total_tasks)],
                ["Tasks faster than ES", str(faster_than_es)],
                [f"Fast Outliers (>{fast_bar})", str(fast_outliers)],
                [f"Slow Outliers (<{slow_bar})", str(slow_outliers)],
            ],
        )
        fmt.bold_font(f"I{offset}:J{offset}")
        fmt.color(f"I{offset}:J{offset}", LIGHT_BLUE)
        offset += 6

        categories = sorted({r.category for r in workload_results})

        faster_ops: dict[str, dict[str, float]] = defaultdict(dict)
        slower_ops: dict[str, dict[str, float]] = defaultdict(dict)
        total_ops: dict[str, int] = defaultdict(int)
        for category in categories:
            for result in workload_results:
                if result.category != category:
                    continue
                total_ops[result.category] += 1
                if result.comparison > 1:
                    faster_ops[category][result.operation] = result.comparison
                elif result.comparison < 1:
                    slower_ops[category][result.operation] = result.comparison

        # Workload Categories Table
        faster_categories_rows = [
            [f"{workload}", f"Categories: OS {latest_os} is faster"],
            ["Category", "Count", "Total"],
        ] + [[c, str(len(faster_ops[c])), str(total_ops[c])] for c in categories]
        sheet.insert_rows(f"I{offset}", faster_categories_rows)
        fmt.bold_font(f"I{offset}:K{offset}")
        fmt.color(f"I{offset}:K{offset}", LIGHT_BLUE)
        offset += 2 + len(faster_categories_rows)

        # Workload Faster Operations Table
        faster_op_rows = [
            [f"{workload}", f"Operations: OS {latest_os} is Faster"],
            ["Category", "Operation", "ES/OS"],
            *sorted([[cat, op, str(val)] for cat, ops in faster_ops.items() for op, val in ops.items()]),
        ]
        sheet.insert_rows(f"I{offset}", faster_op_rows)
        fmt.bold_font(f"I{offset}:K{offset}")
        fmt.color(f"I{offset}:K{offset}", LIGHT_BLUE)
        fmt.style_float(f"K{offset+2}:K{offset+len(faster_op_rows)}")
        offset += 2 + len(faster_op_rows)

        # Workload Slower Operations Table
        slower_op_rows = [
            [f"{workload}", f"Operations: OS {latest_os} if Slower"],
            ["Category", "Operation", "ES/OS"],
            *sorted([[cat, op, str(val)] for cat, ops in slower_ops.items() for op, val in ops.items()]),
        ]
        sheet.insert_rows(f"I{offset}", slower_op_rows)
        fmt.bold_font(f"I{offset}:K{offset}")
        fmt.color(f"I{offset}:K{offset}", LIGHT_BLUE)
        fmt.style_float(f"K{offset+2}:K{offset+len(slower_op_rows)}")
        offset += 2 + len(slower_op_rows)

        # Buffer between workloads
        offset += 4

    fmt.apply()


def create_google_sheet(raw: list[BenchmarkResult], token: Path, credentials: Path | None = None) -> None:
    """Export data to a google sheet."""
    os_versions = {r.EngineVersion for r in raw if r.Engine == "OS"}
    es_versions = {r.EngineVersion for r in raw if r.Engine == "ES"}
    comparisons = [VersionPair(os_version=os, es_version=es) for os, es in product(os_versions, es_versions)]

    workload = "big5"

    logger.info("Building results table")
    results = build_results(raw, comparisons)
    logger.info("Building individual comparison tables")
    version_tables = build_version_compare_tables(workload, results)
    logger.info("Building Overall Spread table")
    overall = build_overall(version_tables)

    spreadsheet = SpreadSheetBuilder("Report", token, credentials)

    logger.info("Exporting Overall Spread table")
    dump_overall(overall, spreadsheet.create_sheet(f"Overall Spread - {workload}"))

    logger.info("Exporting individual comparison tables")
    for table in sorted(version_tables, key=lambda t: t.comparison.os_version):
        os_sheet_name = f"OS {table.comparison.os_version} - {table.workload}"
        logger.info(f"\t{os_sheet_name}")
        os_sheet = spreadsheet.create_sheet(os_sheet_name)
        dump_version_compare_table(table, os_sheet)

    logger.info("Exporting Summary Sheet")
    dump_summary(raw, results, spreadsheet.create_sheet("Summary"))

    logger.info("Exporting results table")
    dump_results(results, spreadsheet.create_sheet("Results"))

    logger.info("Exporting categories")
    dump_categories(spreadsheet.create_sheet("Categories"))

    logger.info("Exporting raw")
    dump_raw(raw, spreadsheet.create_sheet("raw"))

    # Try deleting the initial empty sheet Google creates
    spreadsheet.delete_sheet("Sheet1")

    # Output spreadsheet URL for ease
    report_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet.spreadsheet_id}"
    logger.info(f"Report URL: {report_url}")
