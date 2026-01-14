"""Number formatting utilities for UI display."""

from __future__ import annotations

import math


def format_number_abbreviated(value: float) -> str:
    """Format a number with K/M/B abbreviations for readability.

    Converts large numbers to human-readable format:
    - 1,500,000,000 -> "1.5B"
    - 25,000,000 -> "25M"
    - 1,500 -> "1.5K"
    - 500 -> "500"

    Args:
        value: Numeric value to format.

    Returns:
        Formatted string with appropriate suffix (K, M, or B).
    """
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "inf" if value > 0 else "-inf"

    abs_value = abs(value)
    sign = "-" if value < 0 else ""

    if abs_value >= 1_000_000_000:
        formatted = abs_value / 1_000_000_000
        suffix = "B"
    elif abs_value >= 1_000_000:
        formatted = abs_value / 1_000_000
        suffix = "M"
    elif abs_value >= 1_000:
        formatted = abs_value / 1_000
        suffix = "K"
    else:
        # Small numbers: show as-is with reasonable precision
        if abs_value == 0:
            return "0"
        elif abs_value < 0.01:
            return f"{value:.3g}"
        elif abs_value < 1:
            formatted_str = f"{abs_value:.2f}".rstrip("0").rstrip(".")
            return f"{sign}{formatted_str}"
        else:
            if abs_value == int(abs_value):
                return f"{sign}{int(abs_value)}"
            else:
                return f"{sign}{abs_value:.1f}"

    # Format with suffix, removing unnecessary decimals
    rounded = round(formatted, 2)
    if rounded == int(rounded):
        return f"{sign}{int(rounded)}{suffix}"
    elif round(rounded * 10) == rounded * 10:
        return f"{sign}{rounded:.1f}{suffix}"
    else:
        return f"{sign}{rounded:.2f}{suffix}"
