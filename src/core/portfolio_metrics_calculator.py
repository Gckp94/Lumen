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
