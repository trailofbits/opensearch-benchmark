"""Functions for formatting numbers."""


def format_float(range_dict: dict) -> dict:
    """Format float numbers."""
    return {
        "repeatCell": {
            "range": range_dict,
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0.0##"}}},
            "fields": "userEnteredFormat.numberFormat",
        }
    }


def format_integer(range_dict: dict) -> dict:
    """Format integer numbers."""
    return {
        "repeatCell": {
            "range": range_dict,
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}}},
            "fields": "userEnteredFormat.numberFormat",
        }
    }
