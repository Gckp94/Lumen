"""DataFrame utilities for memory optimization.

This module provides utilities for efficient DataFrame operations,
including copy-on-write optimization and memory-efficient filtering.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def enable_copy_on_write() -> None:
    """Enable pandas Copy-on-Write mode for memory optimization.

    Copy-on-Write (CoW) defers copying until data is actually modified,
    significantly reducing memory usage for read-only operations.

    This should be called at application startup.
    """
    try:
        # pandas 2.0+ has CoW support
        pd.options.mode.copy_on_write = True
        logger.info("Pandas Copy-on-Write mode enabled")
    except Exception:
        logger.debug("Copy-on-Write not available in this pandas version")


def lazy_copy(df: pd.DataFrame) -> pd.DataFrame:
    """Create a lazy copy of a DataFrame.

    If Copy-on-Write is enabled, this is nearly free.
    Otherwise, creates a shallow copy.

    Args:
        df: DataFrame to copy.

    Returns:
        Copy of the DataFrame.
    """
    try:
        # With CoW, copy() is lazy
        return df.copy()
    except Exception:
        return df.copy(deep=False)


def filter_with_mask(
    df: pd.DataFrame,
    mask: pd.Series | np.ndarray,
    copy: bool = True,
) -> pd.DataFrame:
    """Filter DataFrame using a boolean mask efficiently.

    Args:
        df: DataFrame to filter.
        mask: Boolean mask (True = keep).
        copy: If True, return a copy; if False, return a view.

    Returns:
        Filtered DataFrame.
    """
    result = df.loc[mask]
    if copy:
        return lazy_copy(result)
    return result


def select_columns(
    df: pd.DataFrame,
    columns: list[str],
    copy: bool = False,
) -> pd.DataFrame:
    """Select columns from DataFrame efficiently.

    Args:
        df: Source DataFrame.
        columns: List of column names to select.
        copy: If True, return a copy; if False, return a view.

    Returns:
        DataFrame with selected columns.
    """
    # Filter to existing columns only
    existing = [c for c in columns if c in df.columns]
    result = df[existing]
    if copy:
        return lazy_copy(result)
    return result


@contextmanager
def temporary_column(
    df: pd.DataFrame,
    name: str,
    values: pd.Series | np.ndarray | list,
) -> Generator[pd.DataFrame, None, None]:
    """Context manager for temporary column operations.

    Adds a column, yields the DataFrame, then removes the column.
    Useful for calculations that need a temporary column without
    permanently modifying the DataFrame.

    Args:
        df: DataFrame to modify.
        name: Name for the temporary column.
        values: Values for the temporary column.

    Yields:
        DataFrame with temporary column added.
    """
    had_column = name in df.columns
    old_values = df[name].copy() if had_column else None

    try:
        df[name] = values
        yield df
    finally:
        if had_column and old_values is not None:
            df[name] = old_values
        elif name in df.columns:
            df.drop(columns=[name], inplace=True)


def optimize_memory(df: pd.DataFrame, inplace: bool = True) -> pd.DataFrame:
    """Optimize DataFrame memory usage by downcasting numeric types.

    Args:
        df: DataFrame to optimize.
        inplace: If True, modify in place; if False, return a copy.

    Returns:
        Optimized DataFrame.
    """
    if not inplace:
        df = df.copy()

    for col in df.columns:
        col_type = df[col].dtype

        if col_type == "float64":
            # Try float32 if values fit
            col_min = df[col].min()
            col_max = df[col].max()
            if col_min > np.finfo(np.float32).min and col_max < np.finfo(np.float32).max:
                df[col] = df[col].astype(np.float32)

        elif col_type == "int64":
            # Try smaller int types
            col_min = df[col].min()
            col_max = df[col].max()

            if col_min >= 0:
                if col_max < 255:
                    df[col] = df[col].astype(np.uint8)
                elif col_max < 65535:
                    df[col] = df[col].astype(np.uint16)
                elif col_max < 4294967295:
                    df[col] = df[col].astype(np.uint32)
            else:
                if col_min > -128 and col_max < 127:
                    df[col] = df[col].astype(np.int8)
                elif col_min > -32768 and col_max < 32767:
                    df[col] = df[col].astype(np.int16)
                elif col_min > -2147483648 and col_max < 2147483647:
                    df[col] = df[col].astype(np.int32)

        elif col_type == "object":
            # Try converting to category for low-cardinality columns
            n_unique = df[col].nunique()
            n_total = len(df[col])
            if n_unique / n_total < 0.5:  # Less than 50% unique values
                df[col] = df[col].astype("category")

    return df


def get_memory_usage(df: pd.DataFrame) -> dict[str, float]:
    """Get memory usage breakdown for a DataFrame.

    Args:
        df: DataFrame to analyze.

    Returns:
        Dict with memory usage in MB for total, columns, and index.
    """
    memory_usage = df.memory_usage(deep=True)

    return {
        "total_mb": memory_usage.sum() / (1024 * 1024),
        "columns_mb": memory_usage.drop("Index").sum() / (1024 * 1024),
        "index_mb": memory_usage["Index"] / (1024 * 1024),
    }


def chunk_iterator(
    df: pd.DataFrame,
    chunk_size: int = 10000,
) -> Generator[pd.DataFrame, None, None]:
    """Iterate over DataFrame in chunks.

    Useful for processing large DataFrames without loading
    everything into memory at once.

    Args:
        df: DataFrame to iterate.
        chunk_size: Number of rows per chunk.

    Yields:
        DataFrame chunks.
    """
    n_rows = len(df)
    for start in range(0, n_rows, chunk_size):
        end = min(start + chunk_size, n_rows)
        yield df.iloc[start:end]
