"""Functions for formatting cell fonts."""


def bold(range_dict: dict) -> dict:
    """Format bolds in a range of cells."""
    return {
        "repeatCell": {
            "range": range_dict,
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat.bold",
        }
    }
