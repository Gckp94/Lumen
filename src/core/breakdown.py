"""Breakdown metrics calculation for yearly and monthly aggregations."""

import logging

import numpy as np
import pandas as pd

from src.core.equity import EquityCalculator

logger = logging.getLogger(__name__)


class BreakdownCalculator:
    """Calculate breakdown metrics for yearly and monthly periods.

    Computes aggregated statistics including total gain, flat stake PnL,
    max drawdown, trade count, win rate, and average winner/loser.
    """

    def __init__(self, stake: float = 1000.0, start_capital: float = 10000.0) -> None:
        """Initialize calculator with position sizing parameters.

        Args:
            stake: Fixed stake amount for flat stake calculations.
            start_capital: Starting capital for equity curves.
        """
        self._stake = stake
        self._start_capital = start_capital
        self._equity_calc = EquityCalculator()

    def calculate_yearly(
        self,
        df: pd.DataFrame,
        date_col: str,
        gain_col: str,
        win_loss_col: str | None,
    ) -> dict[str, dict]:
        """Calculate yearly breakdown metrics.

        Args:
            df: DataFrame containing trade data.
            date_col: Column name for trade date.
            gain_col: Column name for gain percentage.
            win_loss_col: Column name for win/loss indicator (optional).

        Returns:
            Dict mapping year string to metrics dict.
        """
        if df.empty:
            return {}

        # Ensure date column is datetime
        df = df.copy()
        df["_year"] = pd.to_datetime(df[date_col]).dt.year

        result = {}
        for year, group in df.groupby("_year"):
            result[str(year)] = self._calculate_period_metrics(
                group, gain_col, win_loss_col
            )

        return result

    def calculate_monthly(
        self,
        df: pd.DataFrame,
        year: int,
        date_col: str,
        gain_col: str,
        win_loss_col: str | None,
    ) -> dict[str, dict]:
        """Calculate monthly breakdown metrics for a specific year.

        Args:
            df: DataFrame containing trade data.
            year: Year to filter for.
            date_col: Column name for trade date.
            gain_col: Column name for gain percentage.
            win_loss_col: Column name for win/loss indicator (optional).

        Returns:
            Dict mapping month string (e.g., "Jan", "Feb") to metrics dict.
        """
        if df.empty:
            return {}

        # Filter to specific year
        df = df.copy()
        dates = pd.to_datetime(df[date_col])
        df = df[dates.dt.year == year].copy()

        if df.empty:
            return {}

        df["_month"] = pd.to_datetime(df[date_col]).dt.month

        month_names = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
        ]

        result = {}
        for month, group in df.groupby("_month"):
            month_name = month_names[int(month) - 1]
            result[month_name] = self._calculate_period_metrics(
                group, gain_col, win_loss_col, include_avg_winner_loser=True
            )

        return result

    def _calculate_period_metrics(
        self,
        df: pd.DataFrame,
        gain_col: str,
        win_loss_col: str | None,
        include_avg_winner_loser: bool = False,
    ) -> dict:
        """Calculate metrics for a single period (year or month).

        Args:
            df: DataFrame for the period.
            gain_col: Column name for gain percentage.
            win_loss_col: Column name for win/loss indicator.
            include_avg_winner_loser: Whether to include avg winner/loser.

        Returns:
            Dict with calculated metrics.
        """
        gains = df[gain_col].to_numpy(dtype=float)

        # Total gain %
        total_gain_pct = float(np.sum(gains))

        # Total flat stake gain $
        total_flat_stake = float(np.sum(self._stake * (gains / 100.0)))

        # Count
        count = len(df)

        # Win rate
        if win_loss_col and win_loss_col in df.columns:
            wins = df[win_loss_col].isin(["W", "w", "Win", "WIN", 1, True]).sum()
        else:
            wins = (gains > 0).sum()
        win_rate = (wins / count * 100) if count > 0 else 0.0

        # Max DD (calculate equity curve for this period)
        equity_df = self._equity_calc.calculate_flat_stake(
            df.reset_index(drop=True),
            gain_col,
            self._stake,
            self._start_capital,
        )
        max_dd_dollars, max_dd_pct, _ = self._equity_calc.calculate_drawdown_metrics(equity_df)

        metrics = {
            "total_gain_pct": total_gain_pct,
            "total_flat_stake": total_flat_stake,
            "max_dd_pct": max_dd_pct if max_dd_pct is not None else 0.0,
            "max_dd_dollars": max_dd_dollars if max_dd_dollars is not None else 0.0,
            "count": count,
            "win_rate": win_rate,
        }

        if include_avg_winner_loser:
            winners = gains[gains > 0]
            losers = gains[gains < 0]
            metrics["avg_winner_pct"] = float(np.mean(winners)) if len(winners) > 0 else 0.0
            metrics["avg_loser_pct"] = float(np.mean(losers)) if len(losers) > 0 else 0.0

        return metrics

    def get_available_years(self, df: pd.DataFrame, date_col: str) -> list[int]:
        """Get sorted list of years in the dataset.

        Args:
            df: DataFrame containing trade data.
            date_col: Column name for trade date.

        Returns:
            Sorted list of year integers.
        """
        if df.empty:
            return []

        years = pd.to_datetime(df[date_col]).dt.year.unique()
        return sorted(years.tolist())
