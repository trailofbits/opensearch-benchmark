"""Color functions for Google Sheets."""


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


def format_color_comparison(range_dict: dict) -> list[dict]:
    """Conditionally formats comparison (ES/OS)."""
    rv: list[dict] = []

    # Value is less than 0.5
    rv.append(
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [range_dict],
                    "booleanRule": {
                        "condition": {"type": "NUMBER_LESS", "values": [{"userEnteredValue": "0.5"}]},
                        "format": {"backgroundColor": get_dark_red()},
                    },
                },
                "index": 0,
            }
        }
    )

    # Value is between 0.5 and 1
    rv.append(
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [range_dict],
                    "booleanRule": {
                        "condition": {
                            "type": "NUMBER_BETWEEN",
                            "values": [{"userEnteredValue": "0.5"}, {"userEnteredValue": "1"}],
                        },
                        "format": {"backgroundColor": get_light_red()},
                    },
                },
                "index": 1,
            }
        }
    )

    # Value is between 1 and 2
    rv.append(
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [range_dict],
                    "booleanRule": {
                        "condition": {
                            "type": "NUMBER_BETWEEN",
                            "values": [{"userEnteredValue": "1"}, {"userEnteredValue": "2"}],
                        },
                        "format": {"backgroundColor": get_light_green()},
                    },
                },
                "index": 2,
            }
        }
    )

    # Value is greater than 2
    rv.append(
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [range_dict],
                    "booleanRule": {
                        "condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "2"}]},
                        "format": {"backgroundColor": get_dark_green()},
                    },
                },
                "index": 3,
            }
        }
    )

    return rv


def format_color_rsd(range_dict: dict) -> dict:
    """Conditionally formats RSD."""
    return {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [range_dict],
                "booleanRule": {
                    "condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "0.05"}]},
                    "format": {"backgroundColor": get_light_red()},
                },
            },
            "index": 0,
        }
    }
