"""Filter engine for bounds-based DataFrame filtering."""

import logging
from datetime import time as dt_time

import numpy as np
import pandas as pd

from .models import FilterCriteria

logger = logging.getLogger(__name__)


def time_to_minutes(series: pd.Series) -> pd.Series:
    """Convert a time series to minutes since midnight.

    Handles multiple time formats:
    - HH:MM:SS strings (e.g., "09:30:00")
    - HH:MM strings (e.g., "09:30")
    - Integer HHMMSS (e.g., 93000)
    - Excel serial time (float 0-1)
    - datetime.time objects

    Args:
        series: Pandas Series containing time values in any supported format.

    Returns:
        Pandas Series of float values representing minutes since midnight.
        NaN values in input are preserved as NaN in output.
    """
    if series.empty:
        return pd.Series([], dtype=float)

    result = pd.Series(index=series.index, dtype=float)

    # Get first non-null value to determine format
    first_val = series.dropna().iloc[0] if series.notna().any() else None

    if first_val is None:
        return result

    # Strategy 1: datetime.time objects
    if isinstance(first_val, dt_time):
        result = series.apply(
            lambda x: x.hour * 60 + x.minute + x.second / 60 if pd.notna(x) else np.nan
        )

    # Strategy 2: Excel serial time (float between 0 and 1)
    elif pd.api.types.is_float_dtype(series):
        col_values = series.dropna()
        if len(col_values) > 0 and col_values.between(0, 1).all():
            result = series * 24 * 60  # Convert fraction of day to minutes

    # Strategy 3: Integer HHMMSS format
    elif pd.api.types.is_integer_dtype(series):
        def int_to_minutes(val):
            if pd.isna(val):
                return np.nan
            val_str = str(int(val)).zfill(6)
            hours = int(val_str[:2])
            mins = int(val_str[2:4])
            secs = int(val_str[4:6])
            return hours * 60 + mins + secs / 60
        result = series.apply(int_to_minutes)

    # Strategy 4: String formats
    else:
        def parse_time_string(val):
            if pd.isna(val) or val == "":
                return np.nan
            val_str = str(val).strip()
            if ":" in val_str:
                parts = val_str.split(":")
                hours = int(parts[0])
                mins = int(parts[1])
                secs = int(parts[2]) if len(parts) > 2 else 0
                return hours * 60 + mins + secs / 60
            # Try integer format
            val_str = val_str.zfill(6)
            hours = int(val_str[:2])
            mins = int(val_str[2:4])
            secs = int(val_str[4:6])
            return hours * 60 + mins + secs / 60
        result = series.apply(parse_time_string)

    return result


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

        # Get raw time values for diagnostic
        raw_values = df[time_col].head(5).tolist()
        first_val = df[time_col].iloc[0] if len(df) > 0 else None
        logger.info(
            "Time filter: column '%s', dtype=%s, sample values: %s, first_val type: %s",
            time_col, df[time_col].dtype, raw_values, type(first_val).__name__
        )

        # Try multiple parsing strategies
        time_series = None

        # Strategy 1: Check if column already contains datetime.time objects
        if first_val is not None and isinstance(first_val, dt_time):
            # Already time objects - use directly
            time_series = df[time_col]
            logger.info("Time filter: column already contains time objects")

        # Strategy 2: Check if column contains datetime objects (extract time)
        elif first_val is not None and hasattr(first_val, 'time') and callable(first_val.time):
            # datetime objects - extract time component
            time_series = df[time_col].apply(lambda x: x.time() if pd.notna(x) else None)
            logger.info("Time filter: extracted time from datetime objects")

        # Strategy 3: Check if it's a pandas datetime dtype
        elif pd.api.types.is_datetime64_any_dtype(df[time_col]):
            time_series = pd.to_datetime(df[time_col]).dt.time
            logger.info("Time filter: extracted time from datetime64 column")

        # Strategy 4: Check if it's Excel serial time (float between 0 and 1)
        elif pd.api.types.is_float_dtype(df[time_col]):
            col_values = df[time_col].dropna()
            if len(col_values) > 0 and col_values.between(0, 1).all():
                # Excel serial time: fraction of 24 hours
                # Convert to timedelta, then extract time (handle NaN values)
                total_seconds = df[time_col].fillna(0) * 24 * 60 * 60
                hours = (total_seconds // 3600).astype(int) % 24
                minutes = ((total_seconds % 3600) // 60).astype(int)
                seconds = (total_seconds % 60).astype(int)
                time_strings = hours.astype(str) + ":" + minutes.astype(str) + ":" + seconds.astype(str)
                # Set NaN positions back to NaT
                time_series = pd.to_datetime(time_strings, format="%H:%M:%S", errors="coerce").dt.time
                time_series = time_series.where(df[time_col].notna(), None)
                logger.info("Time filter: converted from Excel serial time (float 0-1)")
            else:
                logger.warning(
                    "Time filter: float column '%s' values not in 0-1 range for Excel time. "
                    "Sample: %s",
                    time_col, raw_values
                )
                return df.copy()

        else:
            # Strategy 4: Parse string formats
            try:
                # Try HH:MM:SS format first
                parsed = pd.to_datetime(df[time_col], format="%H:%M:%S", errors="coerce")
                if parsed.notna().sum() > 0:
                    time_series = parsed.dt.time
                    logger.info("Time filter: parsed using HH:MM:SS format")
                else:
                    # Try HH:MM format (no seconds)
                    parsed = pd.to_datetime(df[time_col], format="%H:%M", errors="coerce")
                    if parsed.notna().sum() > 0:
                        time_series = parsed.dt.time
                        logger.info("Time filter: parsed using HH:MM format")
                    else:
                        # Try mixed format as last resort
                        parsed = pd.to_datetime(df[time_col], format="mixed", errors="coerce")
                        if parsed.notna().sum() > 0:
                            time_series = parsed.dt.time
                            logger.info("Time filter: parsed using mixed format")
                        else:
                            logger.warning(
                                "Time filter: could not parse any values from '%s'. "
                                "Sample: %s",
                                time_col, raw_values
                            )
                            return df.copy()
            except Exception as e:
                logger.warning("Time filter: failed to parse column '%s': %s", time_col, e)
                return df.copy()

        if time_series is None:
            logger.warning("Time filter: could not parse column '%s'", time_col)
            return df.copy()

        # Check how many values parsed successfully
        valid_count = time_series.notna().sum()
        logger.info(
            "Time filter: %d of %d values parsed successfully",
            valid_count, len(df)
        )

        if valid_count == 0:
            logger.warning(
                "Time filter: 0 values parsed from column '%s'. "
                "Sample values: %s. Check time format.",
                time_col, raw_values
            )
            return df.copy()

        mask = pd.Series(True, index=df.index)

        if start_time is not None:
            # Handle both string and datetime.time inputs
            start = start_time if isinstance(start_time, dt_time) else dt_time.fromisoformat(start_time)
            mask &= time_series >= start

        if end_time is not None:
            # Handle both string and datetime.time inputs
            end = end_time if isinstance(end_time, dt_time) else dt_time.fromisoformat(end_time)
            mask &= time_series <= end

        result_count = mask.sum()
        logger.debug(
            "Time filter: %d of %d rows match range %s to %s",
            result_count, len(df), start_time, end_time
        )

        return df[mask].copy()
