"""Common helper functions."""

import logging

from googleapiclient.discovery import Resource
from packaging.version import Version

logger = logging.getLogger(__name__)


def get_category_operation_map() -> list[dict]:
    """Return the category/operation map."""
    spec_list: list[dict] = [
        {
            "workload": "big5",
            "categories": {
                "General Operations": [
                    "default",
                    "scroll",
                ],
                "Date Histogram": [
                    "composite-date_histogram-daily",
                    "date_histogram_hourly_agg",
                    "date_histogram_minute_agg",
                    "range-auto-date-histo",
                    "range-auto-date-histo-with-metrics",
                ],
                "Range Queries": [
                    "range",
                    "keyword-in-range",
                    "range_field_conjunction_big_range_big_term_query",
                    "range_field_conjunction_small_range_big_term_query",
                    "range_field_conjunction_small_range_small_term_query",
                    "range_field_disjunction_big_range_small_term_query",
                    "range-agg-1",
                    "range-agg-2",
                    "range-numeric",
                ],
                "Sorting": [
                    "asc_sort_timestamp",
                    "asc_sort_timestamp_can_match_shortcut",
                    "asc_sort_timestamp_no_can_match_shortcut",
                    "asc_sort_with_after_timestamp",
                    "desc_sort_timestamp",
                    "desc_sort_timestamp_can_match_shortcut",
                    "desc_sort_timestamp_no_can_match_shortcut",
                    "sort_keyword_can_match_shortcut",
                    "desc_sort_with_after_timestamp",
                    "sort_keyword_no_can_match_shortcut",
                    "sort_numeric_asc",
                    "sort_numeric_asc_with_match",
                    "sort_numeric_desc",
                    "sort_numeric_desc_with_match",
                ],
                "Term Aggregations": [
                    "cardinality-agg-high",
                    "cardinality-agg-low",
                    "composite_terms-keyword",
                    "composite-terms",
                    "keyword-terms",
                    "keyword-terms-low-cardinality",
                    "multi_terms-keyword",
                ],
                "Text Querying": [
                    "query-string-on-message",
                    "query-string-on-message-filtered",
                    "query-string-on-message-filtered-sorted-num",
                    "term",
                ],
            },
        },
        {
            "workload": "noaa",
            "categories": {
                "Date Histogram": [
                    "date-histo-entire-range",
                    "date-histo-geohash-grid",
                    "date-histo-geotile-grid",
                    "date-histo-histo",
                    "date-histo-numeric-terms",
                    "date-histo-string-significant-terms-via-default-strategy",
                    "date-histo-string-significant-terms-via-global-ords",
                    "date-histo-string-significant-terms-via-map",
                    "date-histo-string-terms-via-default-strategy",
                    "date-histo-string-terms-via-global-ords",
                    "date-histo-string-terms-via-map",
                ],
                "Range & Date Histogram": [
                    "range-auto-date-histo",
                    "range-auto-date-histo-with-metrics",
                    "range-auto-date-histo-with-time-zone",
                    "range-date-histo",
                    "range-date-histo-with-metrics",
                ],
                "Range Queries": [
                    "range-aggregation",
                    "range-numeric-significant-terms",
                ],
                "Term Aggregations": [
                    "keyword-terms",
                    "keyword-terms-low-cardinality",
                    "keyword-terms-low-cardinality-min",
                    "keyword-terms-min",
                    "keyword-terms-numeric-terms",
                    "numeric-terms-numeric-terms",
                ],
            },
        },
        {
            "workload": "nyc_taxis",
            "categories": {
                "General Operations": [
                    "default",
                ],
                "Aggregation": [
                    "distance_amount_agg",
                    "date_histogram_agg",
                    "autohisto_agg",
                ],
                "Range Queries": [
                    "range",
                ],
                "Sorting": [
                    "desc_sort_tip_amount",
                    "asc_sort_tip_amount",
                ],
            },
        },
        {
            "workload": "pmc",
            "categories": {
                "General Operations": [
                    "default",
                    "scroll",
                ],
                "Aggregation": [
                    "articles_monthly_agg_uncached",
                    "articles_monthly_agg_cached",
                ],
                "Text Querying": [
                    "term",
                    "phrase",
                ],
            },
        },
        {
            "workload": "noaa_semantic_search",
            "categories": {
               "Aggregation": [
                    "aggs-query-date-histo-geohash-grid-hybrid",
                    "aggs-query-date-histo-geohash-grid-hybrid-one-subquery",
                    "aggs-query-date-histo-geohash-grid-hybrid-one-subquery-large-subset",
                    "aggs-query-date-histo-geohash-grid-hybrid-one-subquery-medium-subset",
                    "aggs-query-min-avg-sum-hybrid",
                    "aggs-query-min-avg-sum-hybrid-one-subquery",
                    "aggs-query-min-avg-sum-hybrid-one-subquery-large-subset",
                    "aggs-query-min-avg-sum-hybrid-one-subquery-medium-subset",
                    "aggs-query-range-numeric-significant-terms-hybrid",
                    "aggs-query-range-numeric-significant-terms-hybrid-one-subquery",
                    "aggs-query-range-numeric-significant-terms-hybrid-one-subquery-large-subset",
                    "aggs-query-range-numeric-significant-terms-hybrid-one-subquery-medium-subset",
                    "aggs-query-term-min-hybrid",
                    "aggs-query-term-min-hybrid-one-subquery",
                    "aggs-query-term-min-hybrid-one-subquery-large-subset",
                    "aggs-query-term-min-hybrid-one-subquery-medium-subset",
               ],
               "Hybrid Query": [
                    "hybrid-query-only-range",
                    "hybrid-query-only-range-large-subset",
                    "hybrid-query-only-range-medium-subset",
                    "hybrid-query-only-term-range-date",
               ],
            },
        },
    ]
    return spec_list


def get_workloads(service: Resource, spreadsheet_id: str) -> dict[str, dict[str, list[str]]]:
    """Retrieve tuples of (engine,version,workload) for all benchmarks in the spreadsheet."""
    rv: dict[str, dict[str, list[str]]] = {}

    result: dict = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range="raw!C2:E").execute()
    row_list: list[list[str]] = result.get("values", [])
    for row in row_list:
        engine, version, workload = row
        if workload not in rv:
            rv[workload] = {}
        if engine not in rv[workload]:
            rv[workload][engine] = []
        if version not in rv[workload][engine]:
            rv[workload][engine].append(version)
            rv[workload][engine].sort(key=Version)
    return rv


def get_workload_operations(workload: str) -> list[str]:
    """Return all the operations for the given workload."""
    operation_list: list[str] = []

    spec_list: list[dict] = get_category_operation_map()
    for spec in spec_list:
        if spec["workload"] == workload:
            # Combine the operation lists for each category
            operation_list = sum(spec["categories"].values(), [])  # noqa: RUF017
            break

    return sorted(operation_list)


def get_workload_operation_categories(workload: str) -> list[str]:
    """Return all the operation categories for the given workload."""
    category_list: list[str] = []

    spec_list: list[dict] = get_category_operation_map()
    for spec in spec_list:
        if spec["workload"] == workload:
            category_list = list(spec["categories"].keys())
            break

    return sorted(category_list)


def get_sheet_id(service: Resource, spreadsheet_id: str, sheet_name: str) -> tuple[int | None, dict]:
    """Return the sheet ID for the given sheet name."""
    # Get the spreadsheet metadata to find the sheetId
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

    # Find the sheetId by sheet name
    sheet_id = None
    for sheet in spreadsheet["sheets"]:
        if sheet["properties"]["title"] == sheet_name:
            sheet_id = sheet["properties"]["sheetId"]
            break

    return sheet_id, sheet


def adjust_sheet_columns(service: Resource, spreadsheet_id: str, sheet_id: int, sheet: dict) -> None:
    """Adjust the columns in the given sheet according to their contents."""
    sheet_properties: dict = sheet["properties"]
    column_count: int = sheet_properties.get("gridProperties", {}).get("columnCount", 0)

    requests: list[dict] = [
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": column_count,
                }
            }
        }
    ]

    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests}).execute()


def convert_range_to_dict(range_str: str) -> dict:
    """Convert range string to dictionary."""
    # Example updated_range: 'Sheet1!A5:D5'
    # Split the sheet name from the range
    _, cell_range = range_str.split("!")

    # Split start and end cells (e.g., 'A5:D5')
    start_cell, end_cell = cell_range.split(":")

    # Function to convert column letters to index
    def column_to_index(col: str) -> int:
        index = 0
        for char in col:
            index = index * 26 + (ord(char.upper()) - ord("A")) + 1
        return index - 1  # Convert to 0-indexed

    rv: dict = {}

    # Extract the column letters and row numbers
    import re

    m = re.search(r"\d+", start_cell)
    if m:
        start_row = int(m.group()) - 1  # Convert to 0-indexed
        rv["startRowIndex"] = start_row

    m = re.search(r"\d+", end_cell)
    if m:
        end_row = int(m.group())  # No need to subtract 1 since it's non-inclusive
        rv["endRowIndex"] = end_row

    m = re.match(r"[A-Z]+", start_cell)
    if m:
        start_col = m.group()
        start_column_index = column_to_index(start_col)
        rv["startColumnIndex"] = start_column_index

    m = re.match(r"[A-Z]+", end_cell)
    if m:
        end_col = m.group()
        end_column_index = column_to_index(end_col) + 1  # End is non-inclusive, so add 1
        rv["endColumnIndex"] = end_column_index

    # Construct the range dictionary
    return rv


def column_add(col: str, value: int) -> str:
    """Increases value to column letter."""
    cols = list(col)
    for _ in range(value):
        if cols[-1] == "Z":
            cols[-1] = "A"
            cols.append("A")
        else:
            cols[-1] = chr(ord(cols[-1]) + 1)

    return "".join(cols)
