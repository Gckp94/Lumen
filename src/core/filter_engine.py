"""Filter engine for bounds-based DataFrame filtering."""

import logging
from datetime import time as dt_time

import pandas as pd

from .models import FilterCriteria

logger = logging.getLogger(__name__)


class FilterEngine:
    """Apply bounds-based filters to DataFrames."""

    def apply_filters(
        self,
        df: pd.DataFrame,
        filters: list[FilterCriteria],
    ) -> pd.DataFrame:
        """Apply all filters with AND logic.

        Args:
            df: Source DataFrame to filter.
            filters: List of filter criteria to apply.

        Returns:
            Filtered DataFrame (copy, not view).
        """
        if not filters:
            return df.copy()

        mask = pd.Series(True, index=df.index)
        for criteria in filters:
            mask &= criteria.apply(df)

        logger.debug(
            "Filter applied: %d rows match out of %d", mask.sum(), len(df)
        )
        return df[mask].copy()

    def apply_date_range(
        self,
        df: pd.DataFrame,
        date_col: str,
        start: str | None = None,
        end: str | None = None,
        all_dates: bool = False,
    ) -> pd.DataFrame:
        """Filter by date range.

        Args:
            df: Source DataFrame.
            date_col: Name of the date column.
            start: Start date ISO string (inclusive), None for no lower bound.
            end: End date ISO string (inclusive), None for no upper bound.
            all_dates: If True, skip date filtering entirely.

        Returns:
            Filtered DataFrame (copy).
        """
        if all_dates or (start is None and end is None):
            return df.copy()

        if date_col not in df.columns:
            logger.warning("Date column '%s' not found in DataFrame", date_col)
            return df.copy()

        col = pd.to_datetime(df[date_col], errors="coerce")
        mask = pd.Series(True, index=df.index)

        if start is not None:
            mask &= col >= pd.Timestamp(start)
        if end is not None:
            mask &= col <= pd.Timestamp(end)

        logger.debug("Date filter: %d rows match out of %d", mask.sum(), len(df))
        return df[mask].copy()

    @staticmethod
    def apply_time_range(
        df: pd.DataFrame,
        time_col: str,
        start_time: str | None,
        end_time: str | None,
    ) -> pd.DataFrame:
        """Filter DataFrame by time-of-day range.

        Args:
            df: DataFrame to filter.
            time_col: Column containing time values.
            start_time: Start time in HH:MM:SS format, or None for no lower bound.
            end_time: End time in HH:MM:SS format, or None for no upper bound.

        Returns:
            Filtered DataFrame.
        """
        if start_time is None and end_time is None:
            return df.copy()

        if time_col not in df.columns:
            logger.warning("Time column '%s' not found, skipping time filter", time_col)
            return df.copy()

        # Convert time column to comparable format
        # Handle various time formats: "HH:MM:SS", "HH:MM", datetime objects
        time_series = pd.to_datetime(df[time_col], format="mixed", errors="coerce").dt.time

        mask = pd.Series(True, index=df.index)

        if start_time is not None:
            # Handle both string and datetime.time inputs
            start = start_time if isinstance(start_time, dt_time) else dt_time.fromisoformat(start_time)
            mask &= time_series >= start

        if end_time is not None:
            # Handle both string and datetime.time inputs
            end = end_time if isinstance(end_time, dt_time) else dt_time.fromisoformat(end_time)
            mask &= time_series <= end

        return df[mask].copy()
