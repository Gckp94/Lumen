"""Filter engine for bounds-based DataFrame filtering."""

import logging

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
