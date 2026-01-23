"""Calculator for portfolio breakdown metrics by period."""

import logging

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
            - account_growth_pct: (end - start) / start * 100
            - max_dd_pct: Maximum drawdown as % of peak
            - max_dd_dollars: Maximum drawdown in dollars
            - win_rate_pct: Winning trades / total trades * 100
            - trade_count: Number of trades
            - dd_duration_days: Longest drawdown streak in trading days
        """
        if equity_df.empty:
            return {}

        df = equity_df.copy()
        df["_year"] = pd.to_datetime(df["date"]).dt.year

        results: dict[int, dict[str, float]] = {}

        for year, year_df in df.groupby("_year", sort=True):
            results[int(year)] = self._calculate_period_metrics(year_df)

        return results

    def _calculate_period_metrics(self, df: pd.DataFrame) -> dict[str, float]:
        """Calculate metrics for a single period.

        Args:
            df: DataFrame for the period.

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

        # Total gain
        total_gain_dollars = float(pnl_values.sum())
        total_gain_pct = (total_gain_dollars / period_start * 100) if period_start > 0 else 0.0

        # Account growth
        account_growth_pct = ((period_end - period_start) / period_start * 100) if period_start > 0 else 0.0

        # Max drawdown
        max_dd_dollars = float(drawdown_values.min()) if len(drawdown_values) > 0 else 0.0
        # Calculate DD% at each point relative to peak at that point
        dd_pct_at_each = (drawdown_values / peak_values * 100) if len(peak_values) > 0 else [0.0]
        max_dd_pct = float(min(dd_pct_at_each)) if len(dd_pct_at_each) > 0 else 0.0

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
