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
