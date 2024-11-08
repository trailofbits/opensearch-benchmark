"""Functions for formatting numbers."""


def format_number_float(range_dict: dict) -> dict:
    """Format float numbers."""
    return {
        "repeatCell": {
            "range": range_dict,
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0.000"}}},
            "fields": "userEnteredFormat.numberFormat",
        }
    }
