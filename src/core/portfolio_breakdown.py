"""Calculator for portfolio breakdown metrics by period."""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class PortfolioBreakdownCalculator:
    """Calculate breakdown metrics from portfolio equity curves.

    Takes equity curve DataFrames (with date, pnl, equity, peak, drawdown columns)
    and computes period-level metrics for yearly and monthly breakdowns.
    """

    def __init__(self, starting_capital: float = 10000.0) -> None:
        """Initialize calculator.

        Args:
            starting_capital: Account starting value for percentage calculations.
        """
        self._starting_capital = starting_capital

    def calculate_yearly(
        self, equity_df: pd.DataFrame
    ) -> dict[int, dict[str, float]]:
        """Calculate metrics for each year in the equity curve.

        Args:
            equity_df: DataFrame with columns: date, pnl, equity, peak, drawdown

        Returns:
            Dict mapping year to metrics dict with keys:
            - total_gain_pct: Sum of PnL as % of period start equity
            - total_gain_dollars: Sum of PnL in dollars
            - account_growth_pct: Cumulative growth from starting capital (e.g., 400% = 4x)
            - max_dd_pct: Maximum drawdown as % of peak
            - max_dd_dollars: Maximum drawdown in dollars
            - win_rate_pct: Winning trades / total trades * 100
            - trade_count: Number of trades
            - dd_duration_days: Longest drawdown streak in trading days
        """
        if equity_df.empty:
            return {}

        df = equity_df.copy()
        df["_year"] = pd.to_datetime(df["date"], dayfirst=True, format="mixed", errors="coerce").dt.year

        results: dict[int, dict[str, float]] = {}

        for year, year_df in df.groupby("_year", sort=True):
            results[int(year)] = self._calculate_period_metrics(
                year_df, self._starting_capital
            )

        return results

    def _calculate_period_metrics(
        self, df: pd.DataFrame, starting_capital: float
    ) -> dict[str, float]:
        """Calculate metrics for a single period.

        Args:
            df: DataFrame for the period.
            starting_capital: Original account starting capital for cumulative growth.

        Returns:
            Dict with all 8 metrics.
        """
        pnl_values = df["pnl"].to_numpy()
        equity_values = df["equity"].to_numpy()
        peak_values = df["peak"].to_numpy()
        drawdown_values = df["drawdown"].to_numpy()

        # Get period start equity (equity before first trade = equity - pnl)
        period_start = equity_values[0] - pnl_values[0]
        period_end = equity_values[-1]

        # Total gain (sum of raw trade gain percentages)
        total_gain_dollars = float(pnl_values.sum())
        if "gain_pct" in df.columns:
            # Use raw trade gain percentages (already in percentage form)
            total_gain_pct = float(df["gain_pct"].sum())
        else:
            # Fallback to account return if gain_pct not available
            total_gain_pct = (total_gain_dollars / period_start * 100) if period_start > 0 else 0.0

        

        # Account growth (cumulative growth from reference capital)
        # Shows the % gain/loss from the reference point
        # e.g., 100% means account doubled, -50% means lost half
        account_growth_pct = ((period_end - starting_capital) / starting_capital * 100) if starting_capital > 0 else 0.0

        # Max drawdown
        max_dd_dollars = float(drawdown_values.min()) if len(drawdown_values) > 0 else 0.0
        # Calculate DD% at each point relative to peak at that point
        # Guard against division by zero when peak_values contains zeros
        with np.errstate(divide='ignore', invalid='ignore'):
            dd_pct_at_each = np.where(peak_values != 0, drawdown_values / peak_values * 100, 0.0)
        max_dd_pct = float(np.min(dd_pct_at_each)) if len(dd_pct_at_each) > 0 else 0.0

        # Win rate
        trade_count = len(df)
        wins = (pnl_values > 0).sum()
        win_rate_pct = (wins / trade_count * 100) if trade_count > 0 else 0.0

        # Drawdown duration (consecutive trades in drawdown)
        dd_duration_days = self._calculate_dd_duration(equity_values, peak_values)

        return {
            "total_gain_pct": total_gain_pct,
            "total_gain_dollars": total_gain_dollars,
            "account_growth_pct": account_growth_pct,
            "max_dd_pct": max_dd_pct,
            "max_dd_dollars": max_dd_dollars,
            "win_rate_pct": win_rate_pct,
            "trade_count": trade_count,
            "dd_duration_days": dd_duration_days,
        }

    def calculate_monthly(
        self, equity_df: pd.DataFrame, year: int
    ) -> dict[int, dict[str, float]]:
        """Calculate metrics for each month in the given year.

        Args:
            equity_df: DataFrame with columns: date, pnl, equity, peak, drawdown
            year: Year to filter data for

        Returns:
            Dict mapping month (1-12) to metrics dict.
        """
        if equity_df.empty:
            return {}

        df = equity_df.copy()
        df["_date"] = pd.to_datetime(df["date"], dayfirst=True, format="mixed", errors="coerce")
        df["_year"] = df["_date"].dt.year
        df["_month"] = df["_date"].dt.month

        # Filter to requested year
        # Sort by date and trade_num to ensure consistent ordering with Portfolio Metrics
        sort_cols = ["_date"]
        if "trade_num" in df.columns:
            sort_cols.append("trade_num")
        year_df = df[df["_year"] == year].sort_values(sort_cols)
        if year_df.empty:
            return {}

        # Calculate start-of-year equity (equity before first trade of the year)
        # This is used for monthly account_growth_pct to show growth within the year
        first_row = year_df.iloc[0]
        start_of_year_equity = first_row["equity"] - first_row["pnl"]

        results: dict[int, dict[str, float]] = {}

        for month, month_df in year_df.groupby("_month", sort=True):
            results[int(month)] = self._calculate_period_metrics(
                month_df, start_of_year_equity
            )

        

        return results

    def get_available_years(self, equity_df: pd.DataFrame) -> list[int]:
        """Get sorted list of years present in the equity data.

        Args:
            equity_df: DataFrame with date column.

        Returns:
            Sorted list of unique years.
        """
        if equity_df.empty:
            return []

        years = pd.to_datetime(equity_df["date"], dayfirst=True, format="mixed", errors="coerce").dt.year.unique()
        return sorted(int(y) for y in years)

    def _calculate_dd_duration(
        self, equity: list | pd.Series, peak: list | pd.Series
    ) -> int:
        """Calculate longest consecutive drawdown streak.

        Args:
            equity: Equity values.
            peak: Peak equity values.

        Returns:
            Longest streak where equity < peak (in trading days/trades).
        """
        max_streak = 0
        current_streak = 0

        for e, p in zip(equity, peak):
            if e < p:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        return max_streak
