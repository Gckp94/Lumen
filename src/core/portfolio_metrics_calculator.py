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
