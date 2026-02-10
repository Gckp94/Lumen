"""Breakdown metrics calculation for yearly and monthly aggregations."""

import logging

import numpy as np
import pandas as pd

from src.core.equity import EquityCalculator
from src.core.models import AdjustmentParams

logger = logging.getLogger(__name__)


class BreakdownCalculator:
    """Calculate breakdown metrics for yearly and monthly periods.

    Computes aggregated statistics including total gain, flat stake PnL,
    max drawdown, trade count, win rate, and average winner/loser.
    """

    def __init__(
        self,
        stake: float = 1000.0,
        start_capital: float = 10000.0,
        adjustment_params: "AdjustmentParams | None" = None,
        mae_col: str | None = None,
    ) -> None:
        """Initialize calculator with position sizing parameters.

        Args:
            stake: Fixed stake amount for flat stake calculations.
            start_capital: Starting capital for equity curves.
            adjustment_params: Optional adjustment parameters for stop loss/efficiency.
            mae_col: Column name for MAE (required if adjustment_params provided).
        """
        self._stake = stake
        self._start_capital = start_capital
        self._adjustment_params = adjustment_params
        self._mae_col = mae_col
        self._equity_calc = EquityCalculator()

    def calculate_yearly(
        self,
        df: pd.DataFrame,
        date_col: str,
        gain_col: str,
        win_loss_col: str | None,
    ) -> dict[str, dict]:
        """Calculate yearly breakdown metrics.

        Uses full equity curve context - drawdowns are calculated relative to
        all-time peaks, not just within-year peaks.

        If adjustment_params was provided at initialization, applies stop loss
        and efficiency adjustments to gains before calculating metrics.

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

        # Sort by date to ensure correct equity curve calculation
        df = df.copy()
        df = df.sort_values(date_col).reset_index(drop=True)
        df["_year"] = pd.to_datetime(df[date_col], dayfirst=True, format="mixed").dt.year

        # Apply adjustments if configured, otherwise use raw gains
        # Store in temporary column for use in calculations
        if self._adjustment_params is not None and self._mae_col is not None:
            # calculate_adjusted_gains returns decimal format
            df["_calc_gains"] = self._adjustment_params.calculate_adjusted_gains(
                df, gain_col, self._mae_col
            )
            logger.debug(
                "Breakdown using adjusted gains (stop=%.1f%%, eff=%.1f%%): "
                "range [%.4f, %.4f] (decimal)",
                self._adjustment_params.stop_loss,
                self._adjustment_params.efficiency,
                df["_calc_gains"].min(),
                df["_calc_gains"].max(),
            )
        else:
            df["_calc_gains"] = df[gain_col].astype(float)

        # Convert gains to percentage format for equity calculation
        gains_pct = df["_calc_gains"].to_numpy(dtype=float) * 100.0
        df["_gains_pct"] = gains_pct

        # Calculate FULL equity curve across ALL data
        full_equity = self._equity_calc.calculate_flat_stake(
            df,
            "_gains_pct",
            self._stake,
            self._start_capital,
        )
        # Add year info to equity curve
        full_equity["_year"] = df["_year"].values

        result = {}
        for year, group in df.groupby("_year"):
            # Get equity curve portion for this year
            year_equity = full_equity[full_equity["_year"] == year].copy()

            # Calculate period metrics with the year-specific equity curve
            # Use _calc_gains (decimal format) - the method converts to percentage
            result[str(year)] = self._calculate_period_metrics_with_equity(
                group, "_calc_gains", win_loss_col, year_equity, include_avg_winner_loser=True
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

        Uses full equity curve context - drawdowns are calculated relative to
        all-time peaks, not just within-year or within-month peaks.

        If adjustment_params was provided at initialization, applies stop loss
        and efficiency adjustments to gains before calculating metrics.

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

        # Sort by date to ensure correct equity curve calculation
        df = df.copy()
        df = df.sort_values(date_col).reset_index(drop=True)
        dates = pd.to_datetime(df[date_col], dayfirst=True, format="mixed")

        df["_year"] = dates.dt.year
        df["_month"] = dates.dt.month

        # Apply adjustments if configured, otherwise use raw gains
        if self._adjustment_params is not None and self._mae_col is not None:
            # calculate_adjusted_gains returns decimal format
            df["_calc_gains"] = self._adjustment_params.calculate_adjusted_gains(
                df, gain_col, self._mae_col
            )
        else:
            df["_calc_gains"] = df[gain_col].astype(float)

        # Convert gains to percentage format for equity calculation
        gains_pct = df["_calc_gains"].to_numpy(dtype=float) * 100.0
        df["_gains_pct"] = gains_pct

        # Calculate FULL equity curve across ALL data (not just the target year)
        # This ensures monthly DD metrics reflect all-time peaks
        full_equity = self._equity_calc.calculate_flat_stake(
            df,
            "_gains_pct",
            self._stake,
            self._start_capital,
        )
        # Add year and month info to equity curve
        full_equity["_year"] = df["_year"].values
        full_equity["_month"] = df["_month"].values

        # Filter to specific year for results
        year_df = df[df["_year"] == year]
        if year_df.empty:
            return {}

        month_names = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
        ]

        result = {}
        for month, group in year_df.groupby("_month"):
            month_name = month_names[int(month) - 1]
            # Get equity curve portion for this month
            month_equity = full_equity[
                (full_equity["_year"] == year) & (full_equity["_month"] == month)
            ].copy()

            result[month_name] = self._calculate_period_metrics_with_equity(
                group, "_calc_gains", win_loss_col, month_equity, include_avg_winner_loser=True
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
            gain_col: Column name for gain percentage (decimal format, e.g., 0.05 = 5%).
            win_loss_col: Column name for win/loss indicator.
            include_avg_winner_loser: Whether to include avg winner/loser.

        Returns:
            Dict with calculated metrics.
        """
        gains = df[gain_col].to_numpy(dtype=float)

        # Convert from decimal format (0.05 = 5%) to percentage format (5.0 = 5%)
        # This matches the format expected by MetricsCalculator
        gains_pct = gains * 100.0

        # Total gain % (sum of all trade gains in percentage format)
        total_gain_pct = float(np.sum(gains_pct))

        # Total flat stake gain $ (stake * gain_pct / 100)
        total_flat_stake = float(np.sum(self._stake * (gains_pct / 100.0)))

        # Count
        count = len(df)

        # Win rate
        if win_loss_col and win_loss_col in df.columns:
            wins = df[win_loss_col].isin(["W", "w", "Win", "WIN", 1, True]).sum()
        else:
            wins = (gains > 0).sum()
        win_rate = (wins / count * 100) if count > 0 else 0.0

        # Max DD (calculate equity curve for this period)
        # Create a copy with gains in percentage format for equity calculator
        equity_df = df.copy()
        equity_df["_gains_pct"] = gains_pct
        equity_curve = self._equity_calc.calculate_flat_stake(
            equity_df.reset_index(drop=True),
            "_gains_pct",
            self._stake,
            self._start_capital,
        )
        max_dd_dollars, max_dd_pct, _ = self._equity_calc.calculate_drawdown_metrics(equity_curve)

        metrics = {
            "total_gain_pct": total_gain_pct,
            "total_flat_stake": total_flat_stake,
            "max_dd_pct": max_dd_pct if max_dd_pct is not None else 0.0,
            "max_dd_dollars": max_dd_dollars if max_dd_dollars is not None else 0.0,
            "count": count,
            "win_rate": win_rate,
            "ev_pct": total_gain_pct / count if count > 0 else 0.0,
        }

        if include_avg_winner_loser:
            winners = gains_pct[gains_pct > 0]
            losers = gains_pct[gains_pct < 0]
            metrics["avg_winner_pct"] = float(np.mean(winners)) if len(winners) > 0 else 0.0
            metrics["avg_loser_pct"] = float(np.mean(losers)) if len(losers) > 0 else 0.0

        return metrics

    def _calculate_period_metrics_with_equity(
        self,
        df: pd.DataFrame,
        gain_col: str,
        win_loss_col: str | None,
        equity_df: pd.DataFrame,
        include_avg_winner_loser: bool = False,
    ) -> dict:
        """Calculate metrics for a period using pre-calculated equity curve.

        This method uses a slice of the full equity curve, preserving all-time
        peaks for accurate drawdown calculation.

        Args:
            df: DataFrame for the period.
            gain_col: Column name for gain percentage (decimal format, e.g., 0.05 = 5%).
            win_loss_col: Column name for win/loss indicator.
            equity_df: Pre-calculated equity curve slice for this period.
            include_avg_winner_loser: Whether to include avg winner/loser.

        Returns:
            Dict with calculated metrics.
        """
        gains = df[gain_col].to_numpy(dtype=float)

        # Convert from decimal format (0.05 = 5%) to percentage format (5.0 = 5%)
        gains_pct = gains * 100.0

        # Total gain % (sum of all trade gains in percentage format)
        total_gain_pct = float(np.sum(gains_pct))

        # Total flat stake gain $ (stake * gain_pct / 100)
        total_flat_stake = float(np.sum(self._stake * (gains_pct / 100.0)))

        # Count
        count = len(df)

        # Win rate
        if win_loss_col and win_loss_col in df.columns:
            wins = df[win_loss_col].isin(["W", "w", "Win", "WIN", 1, True]).sum()
        else:
            wins = (gains > 0).sum()
        win_rate = (wins / count * 100) if count > 0 else 0.0

        # Max DD from pre-calculated equity curve (preserves all-time peaks)
        max_dd_dollars, max_dd_pct, _ = self._equity_calc.calculate_drawdown_metrics(equity_df)

        metrics = {
            "total_gain_pct": total_gain_pct,
            "total_flat_stake": total_flat_stake,
            "max_dd_pct": max_dd_pct if max_dd_pct is not None else 0.0,
            "max_dd_dollars": max_dd_dollars if max_dd_dollars is not None else 0.0,
            "count": count,
            "win_rate": win_rate,
            "ev_pct": total_gain_pct / count if count > 0 else 0.0,
        }

        if include_avg_winner_loser:
            winners = gains_pct[gains_pct > 0]
            losers = gains_pct[gains_pct < 0]
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

        years = pd.to_datetime(df[date_col], dayfirst=True, format="mixed").dt.year.unique()
        return sorted(years.tolist())
