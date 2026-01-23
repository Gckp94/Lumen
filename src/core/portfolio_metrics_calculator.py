# src/core/portfolio_metrics_calculator.py
"""Portfolio metrics calculator for quantitative strategy evaluation.

Calculates comprehensive metrics from equity curve data including:
- Standalone quality metrics (CAGR, Sharpe, Sortino, Calmar, etc.)
- Period-based metrics (day/week/month win rates and returns)
- Risk metrics (VaR, CVaR, max drawdown)
"""
import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class PeriodMetrics:
    """Metrics for a specific time period (day/week/month)."""

    avg_green_pct: float | None  # Average return on winning periods
    avg_red_pct: float | None  # Average return on losing periods
    win_pct: float | None  # Percentage of winning periods
    rr_ratio: float | None  # Reward:Risk ratio
    max_win_pct: float | None  # Maximum winning period return
    max_loss_pct: float | None  # Maximum losing period return


@dataclass
class PortfolioMetrics:
    """Complete portfolio metrics."""

    # Core statistics
    cagr: float | None
    sharpe_ratio: float | None
    sortino_ratio: float | None
    calmar_ratio: float | None
    win_rate: float | None
    profit_factor: float | None

    # Drawdown metrics
    max_drawdown_pct: float | None
    max_drawdown_dollars: float | None
    max_dd_duration_days: int | None
    time_underwater_pct: float | None

    # Statistical metrics
    t_statistic: float | None
    p_value: float | None

    # Period metrics
    daily: PeriodMetrics | None
    weekly: PeriodMetrics | None
    monthly: PeriodMetrics | None

    # Additional ratios
    var_95: float | None  # 95% Value at Risk
    cvar_95: float | None  # 95% Conditional VaR (Expected Shortfall)


class PortfolioMetricsCalculator:
    """Calculates comprehensive portfolio metrics from equity curves."""

    def __init__(self, starting_capital: float = 100_000) -> None:
        """Initialize calculator.

        Args:
            starting_capital: Initial account value for calculations.
        """
        self.starting_capital = starting_capital

    def calculate_cagr(self, equity_curve: pd.DataFrame) -> float | None:
        """Calculate Compound Annual Growth Rate.

        CAGR = (Ending Value / Beginning Value)^(1/Years) - 1

        Args:
            equity_curve: DataFrame with 'equity' and 'date' columns.

        Returns:
            CAGR as percentage (e.g., 15.5 for 15.5%), or None if insufficient data.
        """
        if equity_curve.empty or len(equity_curve) < 2:
            return None

        beginning_value = self.starting_capital
        ending_value = equity_curve["equity"].iloc[-1]

        # Calculate years from date range
        dates = pd.to_datetime(equity_curve["date"])
        days = (dates.max() - dates.min()).days
        if days == 0:
            return None

        years = days / 365.25

        if beginning_value <= 0:
            return None

        # Handle negative ending value (blown account)
        if ending_value <= 0:
            return -100.0

        cagr = (ending_value / beginning_value) ** (1 / years) - 1
        return cagr * 100  # Convert to percentage

    def _calculate_daily_returns(self, equity_curve: pd.DataFrame) -> pd.Series:
        """Calculate daily returns from equity curve.

        Args:
            equity_curve: DataFrame with 'equity' column.

        Returns:
            Series of daily returns as decimals.
        """
        equities = equity_curve["equity"].astype(float)
        # Prepend starting capital for first return calculation
        with_start = pd.concat([pd.Series([self.starting_capital]), equities])
        returns = with_start.pct_change().dropna()
        return returns.reset_index(drop=True)

    def calculate_sharpe_ratio(
        self, equity_curve: pd.DataFrame, rf_rate: float = 0.0
    ) -> float | None:
        """Calculate annualized Sharpe ratio.

        Sharpe = (Mean Return - Risk Free Rate) / Std Dev of Returns
        Annualized = Daily Sharpe * sqrt(252)

        Args:
            equity_curve: DataFrame with 'equity' column.
            rf_rate: Annual risk-free rate (default 0).

        Returns:
            Annualized Sharpe ratio, or None if insufficient data.
        """
        returns = self._calculate_daily_returns(equity_curve)
        if len(returns) < 2:
            return None

        daily_rf = rf_rate / 252
        excess_returns = returns - daily_rf

        std = excess_returns.std()
        if std == 0:
            return None

        daily_sharpe = excess_returns.mean() / std
        return float(daily_sharpe * np.sqrt(252))

    def calculate_sortino_ratio(
        self, equity_curve: pd.DataFrame, target: float = 0.0
    ) -> float | None:
        """Calculate annualized Sortino ratio.

        Sortino = (Mean Return - Target) / Downside Deviation
        Downside deviation only considers returns below target.

        Args:
            equity_curve: DataFrame with 'equity' column.
            target: Target return (default 0).

        Returns:
            Annualized Sortino ratio, or None if insufficient data.
        """
        returns = self._calculate_daily_returns(equity_curve)
        if len(returns) < 2:
            return None

        # Calculate downside deviation (only negative deviations from target)
        downside = np.minimum(returns - target, 0)
        downside_std = np.sqrt(np.mean(downside**2))

        if downside_std == 0:
            return None

        daily_sortino = (returns.mean() - target) / downside_std
        return float(daily_sortino * np.sqrt(252))

    def calculate_max_drawdown(
        self, equity_curve: pd.DataFrame
    ) -> tuple[float | None, float | None]:
        """Calculate maximum drawdown in percentage and dollars.

        Args:
            equity_curve: DataFrame with 'equity' and 'peak' columns.

        Returns:
            Tuple of (max_dd_percent, max_dd_dollars), or (None, None) if no data.
        """
        if equity_curve.empty:
            return None, None

        equities = equity_curve["equity"].astype(float)
        peaks = equity_curve["peak"].astype(float)

        # Calculate drawdown at each point
        dd_dollars = equities - peaks
        dd_percent = (dd_dollars / peaks) * 100

        # Find maximum drawdown (most negative)
        max_dd_dollars = float(dd_dollars.min())
        max_dd_pct = float(dd_percent.min())

        return abs(max_dd_pct), abs(max_dd_dollars)

    def calculate_drawdown_duration(
        self, equity_curve: pd.DataFrame
    ) -> tuple[int | None, float | None]:
        """Calculate max drawdown duration and time underwater.

        Args:
            equity_curve: DataFrame with 'equity', 'peak', and 'date' columns.

        Returns:
            Tuple of (max_duration_days, time_underwater_pct).
        """
        if equity_curve.empty or len(equity_curve) < 2:
            return None, None

        equities = equity_curve["equity"].astype(float)
        peaks = equity_curve["peak"].astype(float)

        # Underwater when equity < peak
        underwater = equities < peaks
        time_underwater_pct = float(underwater.sum() / len(underwater) * 100)

        # Calculate drawdown periods (consecutive underwater days)
        periods = []
        current_period = 0
        for uw in underwater:
            if uw:
                current_period += 1
            else:
                if current_period > 0:
                    periods.append(current_period)
                current_period = 0
        if current_period > 0:
            periods.append(current_period)

        max_duration = max(periods) if periods else 0

        return max_duration, time_underwater_pct

    def calculate_calmar_ratio(self, equity_curve: pd.DataFrame) -> float | None:
        """Calculate Calmar ratio (CAGR / Max Drawdown).

        Args:
            equity_curve: DataFrame with equity data.

        Returns:
            Calmar ratio, or None if cannot be calculated.
        """
        cagr = self.calculate_cagr(equity_curve)
        max_dd_pct, _ = self.calculate_max_drawdown(equity_curve)

        if cagr is None or max_dd_pct is None or max_dd_pct == 0:
            return None

        return cagr / max_dd_pct

    def calculate_win_rate(self, equity_curve: pd.DataFrame) -> float | None:
        """Calculate win rate percentage.

        Args:
            equity_curve: DataFrame with 'pnl' or 'win' column.

        Returns:
            Win rate as percentage (e.g., 65.0 for 65%), or None.
        """
        if equity_curve.empty:
            return None

        if "win" in equity_curve.columns:
            wins = equity_curve["win"].sum()
            total = len(equity_curve)
        elif "pnl" in equity_curve.columns:
            pnls = equity_curve["pnl"].astype(float)
            wins = (pnls > 0).sum()
            total = len(pnls)
        else:
            return None

        if total == 0:
            return None

        return float(wins / total * 100)

    def calculate_profit_factor(self, equity_curve: pd.DataFrame) -> float | None:
        """Calculate profit factor (gross profits / gross losses).

        Args:
            equity_curve: DataFrame with 'pnl' column.

        Returns:
            Profit factor, or None if no losses.
        """
        if equity_curve.empty or "pnl" not in equity_curve.columns:
            return None

        pnls = equity_curve["pnl"].astype(float)
        gross_profit = pnls[pnls > 0].sum()
        gross_loss = abs(pnls[pnls < 0].sum())

        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else None

        return float(gross_profit / gross_loss)

    def calculate_t_statistic(
        self, equity_curve: pd.DataFrame
    ) -> tuple[float | None, float | None]:
        """Calculate t-statistic testing if mean return differs from zero.

        Args:
            equity_curve: DataFrame with equity data.

        Returns:
            Tuple of (t_statistic, p_value), or (None, None).
        """
        returns = self._calculate_daily_returns(equity_curve)
        if len(returns) < 2:
            return None, None

        t_stat, p_value = stats.ttest_1samp(returns, 0)
        return float(t_stat), float(p_value)

    def calculate_var_cvar(
        self, equity_curve: pd.DataFrame, confidence: float = 0.95
    ) -> tuple[float | None, float | None]:
        """Calculate Value at Risk and Conditional VaR (Expected Shortfall).

        Args:
            equity_curve: DataFrame with equity data.
            confidence: Confidence level (default 0.95 for 95%).

        Returns:
            Tuple of (VaR, CVaR) as percentages, or (None, None).
        """
        returns = self._calculate_daily_returns(equity_curve)
        if len(returns) < 2:
            return None, None

        # VaR is the quantile at (1 - confidence)
        var = float(returns.quantile(1 - confidence) * 100)

        # CVaR is mean of returns worse than VaR
        threshold = returns.quantile(1 - confidence)
        tail_returns = returns[returns <= threshold]
        if len(tail_returns) == 0:
            cvar = var
        else:
            cvar = float(tail_returns.mean() * 100)

        return var, cvar

    def calculate_period_metrics(
        self, equity_curve: pd.DataFrame, period: str
    ) -> PeriodMetrics | None:
        """Calculate metrics for a specific time period.

        Args:
            equity_curve: DataFrame with date, pnl, equity columns.
            period: "daily", "weekly", or "monthly".

        Returns:
            PeriodMetrics dataclass, or None if insufficient data.
        """
        if equity_curve.empty or "pnl" not in equity_curve.columns:
            return None

        df = equity_curve.copy()
        df["date"] = pd.to_datetime(df["date"])

        # Group by period
        if period == "daily":
            df["period"] = df["date"].dt.date
        elif period == "weekly":
            df["period"] = df["date"].dt.isocalendar().week.astype(str) + "-" + df["date"].dt.year.astype(str)
        elif period == "monthly":
            df["period"] = df["date"].dt.to_period("M")
        else:
            return None

        # Aggregate PnL by period and calculate return %
        period_data = df.groupby("period").agg({
            "pnl": "sum",
            "equity": "first",  # Starting equity for the period
        }).reset_index()

        # Calculate period return % based on starting equity
        # Use equity from start of period (before PnL)
        period_data["start_equity"] = period_data["equity"] - period_data["pnl"]
        period_data["return_pct"] = (period_data["pnl"] / period_data["start_equity"]) * 100

        returns = period_data["return_pct"]

        if len(returns) == 0:
            return None

        green_returns = returns[returns > 0]
        red_returns = returns[returns < 0]

        # Calculate metrics
        avg_green = float(green_returns.mean()) if len(green_returns) > 0 else None
        avg_red = float(red_returns.mean()) if len(red_returns) > 0 else None
        win_pct = float(len(green_returns) / len(returns) * 100) if len(returns) > 0 else None

        # R:R ratio
        if avg_green is not None and avg_red is not None and avg_red != 0:
            rr_ratio = abs(avg_green / avg_red)
        else:
            rr_ratio = None

        max_win = float(returns.max()) if len(returns) > 0 else None
        max_loss = float(returns.min()) if len(returns) > 0 else None

        return PeriodMetrics(
            avg_green_pct=avg_green,
            avg_red_pct=avg_red,
            win_pct=win_pct,
            rr_ratio=rr_ratio,
            max_win_pct=max_win,
            max_loss_pct=max_loss,
        )
