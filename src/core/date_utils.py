"""Date format detection and normalization utilities."""

from enum import Enum
import pandas as pd
import re


class DateFormat(Enum):
    """Detected date format types."""
    ISO = "YYYY-MM-DD"
    DAY_FIRST = "DD/MM/YYYY"
    MONTH_FIRST = "MM/DD/YYYY"
    UNKNOWN = "Unknown"


def detect_date_format(date_series: pd.Series) -> DateFormat:
    """Detect the date format used in a series of date strings.

    Analyzes a sample of dates to determine the format:
    - ISO: YYYY-MM-DD (unambiguous)
    - DAY_FIRST: DD/MM/YYYY (European)
    - MONTH_FIRST: MM/DD/YYYY (US)

    Args:
        date_series: Series of date strings to analyze.

    Returns:
        Detected DateFormat enum value.
    """
    if date_series.empty:
        return DateFormat.UNKNOWN

    # Sample up to 100 non-null values
    sample = date_series.dropna().head(100).astype(str)

    if sample.empty:
        return DateFormat.UNKNOWN

    first_date = sample.iloc[0]

    # Check for ISO format (YYYY-MM-DD)
    if re.match(r'^\d{4}-\d{2}-\d{2}', first_date):
        return DateFormat.ISO

    # Check for slash-separated format
    if '/' in first_date:
        # Analyze values to determine day-first vs month-first
        for date_str in sample:
            parts = date_str.split('/')
            if len(parts) >= 2:
                try:
                    first_part = int(parts[0])
                    second_part = int(parts[1])

                    # If first part > 12, it must be a day (DAY_FIRST)
                    if first_part > 12:
                        return DateFormat.DAY_FIRST

                    # If second part > 12, it must be a day (MONTH_FIRST)
                    if second_part > 12:
                        return DateFormat.MONTH_FIRST
                except ValueError:
                    continue

        # Ambiguous - default to DAY_FIRST (matches existing dayfirst=True behavior)
        return DateFormat.DAY_FIRST

    # Check for dash-separated non-ISO (DD-MM-YYYY)
    if '-' in first_date and not re.match(r'^\d{4}-', first_date):
        return DateFormat.DAY_FIRST

    return DateFormat.UNKNOWN
