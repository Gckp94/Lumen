"""First trigger algorithm implementation."""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


class FirstTriggerEngine:
    """First trigger algorithm implementation.

    Identifies the first signal per ticker-date combination from trade data.
    Uses vectorized pandas operations for performance on large datasets.
    """

    def apply(
        self,
        df: pd.DataFrame,
        ticker_col: str,
        date_col: str,
        time_col: str,
    ) -> pd.DataFrame:
        """Identify first signal per ticker-date combination.

        Algorithm:
        1. Group by ticker + date
        2. Sort by time within groups (nulls first)
        3. Keep first row per group

        Args:
            df: Input DataFrame with trade data.
            ticker_col: Column name for ticker/symbol.
            date_col: Column name for trade date.
            time_col: Column name for trade time.

        Returns:
            DataFrame with one row per ticker-date (first trigger only).
        """
        if len(df) == 0:
            logger.debug("Empty DataFrame, returning empty result")
            return df.copy()

        # Sort by ticker, date, time (nulls first within each group)
        sorted_df = df.sort_values(
            by=[ticker_col, date_col, time_col],
            na_position="first",
        )

        # Keep first row per ticker-date combination
        result = sorted_df.drop_duplicates(
            subset=[ticker_col, date_col],
            keep="first",
        )

        logger.info(
            "First trigger applied: %d baseline rows from %d total",
            len(result),
            len(df),
        )

        return result

    def apply_filtered(
        self,
        df: pd.DataFrame,
        ticker_col: str,
        date_col: str,
        time_col: str,
    ) -> pd.DataFrame:
        """Apply first trigger to already-filtered data.

        Same algorithm as apply(), but intended for use on pre-filtered data
        to identify first triggers within filtered results.

        Args:
            df: Input DataFrame (already filtered).
            ticker_col: Column name for ticker/symbol.
            date_col: Column name for trade date.
            time_col: Column name for trade time.

        Returns:
            DataFrame copy with one row per ticker-date (first trigger only).
        """
        if len(df) == 0:
            logger.debug("Empty DataFrame, returning empty result")
            return df.copy()

        # Sort by ticker, date, time (nulls first within each group)
        sorted_df = df.sort_values(
            by=[ticker_col, date_col, time_col],
            na_position="first",
        )

        # Keep first row per ticker-date combination
        result = sorted_df.drop_duplicates(
            subset=[ticker_col, date_col],
            keep="first",
        )

        logger.debug(
            "First trigger on filtered: %d first triggers from %d filtered rows",
            len(result),
            len(df),
        )

        return result.copy()
