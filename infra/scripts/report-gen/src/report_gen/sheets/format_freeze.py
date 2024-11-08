"""Functions for freezing rows and columns."""


def format_freeze_row(sheet_id: int | None, row_count: int) -> dict | None:
    """Freeze rows."""
    if sheet_id is None:
        return None
    return {
        "updateSheetProperties": {
            "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": row_count}},
            "fields": "gridProperties.frozenRowCount",
        }
    }


def format_freeze_col(sheet_id: int | None, col_count: int) -> dict | None:
    """Freeze columns."""
    if sheet_id is None:
        return None
    return {
        "updateSheetProperties": {
            "properties": {"sheetId": sheet_id, "gridProperties": {"frozenColumnCount": col_count}},
            "fields": "gridProperties.frozenColumnCount",
        }
    }
