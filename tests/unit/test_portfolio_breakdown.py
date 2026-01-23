"""Tests for PortfolioBreakdownCalculator."""

import pandas as pd
import pytest

from src.core.portfolio_breakdown import PortfolioBreakdownCalculator


class TestPortfolioBreakdownCalculatorYearly:
    """Tests for yearly breakdown calculations."""

    @pytest.fixture
    def calculator(self) -> PortfolioBreakdownCalculator:
        """Create calculator instance."""
        return PortfolioBreakdownCalculator()

    @pytest.fixture
    def sample_equity_df(self) -> pd.DataFrame:
        """Create sample equity curve data spanning 2 years."""
        return pd.DataFrame({
            "date": pd.to_datetime([
                "2023-01-15", "2023-06-15", "2023-12-15",
                "2024-03-15", "2024-09-15",
            ]),
            "pnl": [100.0, -50.0, 150.0, 200.0, -30.0],
            "equity": [10100.0, 10050.0, 10200.0, 10400.0, 10370.0],
            "peak": [10100.0, 10100.0, 10200.0, 10400.0, 10400.0],
            "drawdown": [0.0, -50.0, 0.0, 0.0, -30.0],
        })

    def test_calculate_yearly_returns_dict_per_year(
        self, calculator: PortfolioBreakdownCalculator, sample_equity_df: pd.DataFrame
    ) -> None:
        """Verify yearly calculation returns metrics for each year."""
        result = calculator.calculate_yearly(sample_equity_df)

        assert 2023 in result
        assert 2024 in result
        assert "total_gain_pct" in result[2023]
        assert "total_gain_dollars" in result[2023]
        assert "account_growth_pct" in result[2023]
        assert "max_dd_pct" in result[2023]
        assert "max_dd_dollars" in result[2023]
        assert "win_rate_pct" in result[2023]
        assert "trade_count" in result[2023]
        assert "dd_duration_days" in result[2023]

    def test_calculate_yearly_total_gain_pct(
        self, calculator: PortfolioBreakdownCalculator, sample_equity_df: pd.DataFrame
    ) -> None:
        """Verify total gain % calculation."""
        result = calculator.calculate_yearly(sample_equity_df)

        # 2023: pnl sum = 100 - 50 + 150 = 200, start equity = 10000
        # total_gain_pct = 200 / 10000 * 100 = 2.0%
        assert result[2023]["total_gain_pct"] == pytest.approx(2.0, rel=0.01)

    def test_calculate_yearly_trade_count(
        self, calculator: PortfolioBreakdownCalculator, sample_equity_df: pd.DataFrame
    ) -> None:
        """Verify trade count per year."""
        result = calculator.calculate_yearly(sample_equity_df)

        assert result[2023]["trade_count"] == 3
        assert result[2024]["trade_count"] == 2

    def test_calculate_yearly_win_rate(
        self, calculator: PortfolioBreakdownCalculator, sample_equity_df: pd.DataFrame
    ) -> None:
        """Verify win rate calculation."""
        result = calculator.calculate_yearly(sample_equity_df)

        # 2023: 2 wins (100, 150), 1 loss (-50) = 66.67%
        assert result[2023]["win_rate_pct"] == pytest.approx(66.67, rel=0.01)
        # 2024: 1 win (200), 1 loss (-30) = 50%
        assert result[2024]["win_rate_pct"] == pytest.approx(50.0, rel=0.01)

    def test_calculate_yearly_empty_df(
        self, calculator: PortfolioBreakdownCalculator
    ) -> None:
        """Verify empty DataFrame returns empty dict."""
        empty_df = pd.DataFrame(columns=["date", "pnl", "equity", "peak", "drawdown"])
        result = calculator.calculate_yearly(empty_df)

        assert result == {}
