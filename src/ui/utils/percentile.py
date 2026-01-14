"""Percentile calculation utilities for axis bounds."""

from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_percentile_bounds(
    data: pd.Series,
    percentile: float,
) -> tuple[float | None, float | None]:
    """Calculate symmetric percentile bounds for data.

    Computes the lower and upper bounds that contain the specified
    percentile of data points, clipping outliers from both tails.

    For example, percentile=95.0 returns the 2.5th and 97.5th percentiles,
    excluding the most extreme 5% of values (2.5% from each tail).

    Args:
        data: Series of numeric values to analyze.
        percentile: Percentage of data to include (e.g., 95.0, 99.0, 99.9).
            Must be between 0 and 100.

    Returns:
        Tuple of (lower_bound, upper_bound). Returns (None, None) if
        data is empty or contains only NaN/inf values.
    """
    # Filter out NaN and infinite values
    clean_data = data.replace([np.inf, -np.inf], np.nan).dropna()

    if len(clean_data) == 0:
        return None, None

    # Calculate tail percentage (symmetric clipping)
    tail_pct = (100.0 - percentile) / 2.0
    lower_pct = tail_pct
    upper_pct = 100.0 - tail_pct

    lower = float(np.percentile(clean_data, lower_pct))
    upper = float(np.percentile(clean_data, upper_pct))

    return lower, upper


def calculate_iqr_bounds(
    data: pd.Series,
    multiplier: float = 1.5,
) -> tuple[float | None, float | None]:
    """Calculate bounds using IQR-based outlier detection.

    Uses the Interquartile Range (IQR) method to detect outliers.
    Bounds are set at Q1 - multiplier*IQR and Q3 + multiplier*IQR.

    This is the "Tukey fence" method commonly used in box plots.
    Default multiplier of 1.5 identifies mild outliers.

    Args:
        data: Series of numeric values to analyze.
        multiplier: IQR multiplier for fence calculation. Default 1.5.
            Use 1.0 for tighter bounds, 3.0 for very loose bounds.

    Returns:
        Tuple of (lower_bound, upper_bound). Returns (None, None) if
        data is empty or contains only NaN/inf values.
    """
    # Filter out NaN and infinite values
    clean_data = data.replace([np.inf, -np.inf], np.nan).dropna()

    if len(clean_data) == 0:
        return None, None

    q1 = float(np.percentile(clean_data, 25))
    q3 = float(np.percentile(clean_data, 75))
    iqr = q3 - q1

    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr

    # Clamp to actual data range (don't extend beyond data)
    data_min = float(clean_data.min())
    data_max = float(clean_data.max())
    lower = max(lower, data_min)
    upper = min(upper, data_max)

    return lower, upper
