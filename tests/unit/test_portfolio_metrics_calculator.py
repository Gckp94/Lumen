# tests/unit/test_portfolio_metrics_calculator.py
"""Unit tests for PortfolioMetricsCalculator."""
import pandas as pd
import numpy as np
import pytest
from datetime import date, timedelta

from src.core.portfolio_metrics_calculator import PortfolioMetricsCalculator


class TestPortfolioMetricsCalculator:
    """Tests for portfolio metrics calculations."""

    @pytest.fixture
    def calculator(self) -> PortfolioMetricsCalculator:
        """Create calculator with $100,000 starting capital."""
        return PortfolioMetricsCalculator(starting_capital=100_000)

    @pytest.fixture
    def sample_equity_curve(self) -> pd.DataFrame:
        """Create sample equity curve spanning 1 year with known returns."""
        # 365 calendar days, ending at $150,000 (50% total return)
        # Using 365 days so CAGR ~= 50% for a 50% return over 1 year
        dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(365)]
        equities = np.linspace(100_000, 150_000, 365)
        pnls = np.diff(equities, prepend=100_000)
        peaks = np.maximum.accumulate(equities)
        drawdowns = equities - peaks
        wins = pnls > 0

        return pd.DataFrame({
            "date": dates,
            "trade_num": range(1, 366),
            "pnl": pnls,
            "equity": equities,
            "peak": peaks,
            "drawdown": drawdowns,
            "win": wins,
        })

    def test_calculate_cagr_one_year_50_percent(
        self, calculator: PortfolioMetricsCalculator, sample_equity_curve: pd.DataFrame
    ) -> None:
        """CAGR for 50% return over 1 year should be ~50%."""
        cagr = calculator.calculate_cagr(sample_equity_curve)
        assert cagr == pytest.approx(50.0, rel=0.05)  # 50% +/- 5%
