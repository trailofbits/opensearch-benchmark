"""Common helper functions."""

import logging

from googleapiclient.discovery import Resource

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
    ]
    return spec_list


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


def get_sheet_id(service: Resource, spreadsheet_id: str, name: str) -> int | None:
    """Return the sheet ID for the given sheet name."""
    # Get the spreadsheet metadata to find the sheetId
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

    # Find the sheetId by sheet name
    sheet_id = None
    for sheet in spreadsheet["sheets"]:
        if sheet["properties"]["title"] == name:
            sheet_id = sheet["properties"]["sheetId"]
            break

    return sheet_id


def get_light_red() -> dict:
    """Return the light red color."""
    return {"red": 244 / 255, "green": 199 / 255, "blue": 195 / 255}


def get_dark_red() -> dict:
    """Return the dark red color.."""
    return {"red": 244 / 255, "green": 102 / 255, "blue": 102 / 255}


def get_light_green() -> dict:
    """Return the light green color."""
    return {"red": 183 / 255, "green": 225 / 255, "blue": 205 / 255}


def get_dark_green() -> dict:
    """Return the dark green color."""
    return {"red": 87 / 255, "green": 187 / 255, "blue": 138 / 255}


def get_light_blue() -> dict:
    """Return the light blue color."""
    return {"red": 207 / 255, "green": 226 / 255, "blue": 243 / 255}


def get_light_orange() -> dict:
    """Return the light orange color."""
    return {"red": 252 / 255, "green": 229 / 255, "blue": 205 / 255}


def get_light_cyan() -> dict:
    """Return the light cyan color."""
    return {"red": 208 / 255, "green": 224 / 255, "blue": 227 / 255}


def get_light_purple() -> dict:
    """Return the light purple color."""
    return {"red": 217 / 255, "green": 210 / 255, "blue": 233 / 255}


def get_light_yellow() -> dict:
    """Return the light yellow color."""
    return {"red": 255 / 255, "green": 242 / 255, "blue": 204 / 255}


def adjust_sheet_columns(service: Resource, spreadsheet_id: str, sheet_name: str) -> None:
    """Adjust the columns in the given sheet according to their contents."""
    spreadsheet_properties: dict = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

    sheet_id: int | None = None
    for sheet in spreadsheet_properties.get("sheets", ""):
        if sheet["properties"]["title"] == sheet_name:
            sheet_id = sheet["properties"]["sheetId"]
            break

    if sheet_id is None:
        logger.error(f"Failed to locate the sheet named '{sheet_name}'. Formatting has failed")
        return

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


def hide_columns(service: Resource, spreadsheet_id: str, sheet_name: str, column_list: list[str]) -> None:
    """Hide the specified columns in the given sheet."""
    sheet_id = get_sheet_id(service, spreadsheet_id, sheet_name)
    if sheet_id is None:
        logger.error(f"Failed to locate the sheet named '{sheet_name}'. Failed to hide the columns")
        return

    request_list = [
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": ord(column) - ord("A"),
                    "endIndex": ord(column) - ord("A") + 1,
                },
                "properties": {"hiddenByUser": True},
                "fields": "hiddenByUser",
            }
        }
        for column in column_list
    ]

    body: dict = {"requests": request_list}
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()


def convert_range_to_dict(range_str: str) -> dict:
    """Convert range string to dictionary."""
    # Example updated_range: 'Sheet1!A5:D5'
    # Split the sheet name from the range
    sheet_name, cell_range = range_str.split("!")

    # Split start and end cells (e.g., 'A5:D5')
    start_cell, end_cell = cell_range.split(":")

    # Function to convert column letters to index
    def column_to_index(col: str) -> int:
        index = 0
        for char in col:
            index = index * 26 + (ord(char.upper()) - ord("A")) + 1
        return index - 1  # Convert to 0-indexed

    # Extract the column letters and row numbers
    import re

    m = re.match(r"[A-Z]+", start_cell)
    if m:
        start_col = m.group()

    m = re.search(r"\d+", start_cell)
    if m:
        start_row = int(m.group()) - 1  # Convert to 0-indexed

    m = re.match(r"[A-Z]+", end_cell)
    if m:
        end_col = m.group()

    m = re.search(r"\d+", end_cell)
    if m:
        end_row = int(m.group())  # No need to subtract 1 since it's non-inclusive

    # Convert column letters to 0-indexed numbers
    start_column_index = column_to_index(start_col)
    end_column_index = column_to_index(end_col) + 1  # End is non-inclusive, so add 1

    # Construct the range dictionary
    return {
        "startRowIndex": start_row,
        "endRowIndex": end_row,
        "startColumnIndex": start_column_index,
        "endColumnIndex": end_column_index,
    }


def sheet_add(cell: str, value: int) -> str:
    """Increases value to column letter."""
    cells = list(cell)
    for _ in range(value):
        if cells[-1] == "Z":
            cells[-1] = "A"
            cells.append("A")
        else:
            cells[-1] = chr(ord(cells[-1]) + 1)

    return "".join(cells)
