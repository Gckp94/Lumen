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

    def test_calculate_sharpe_ratio(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Sharpe ratio calculation with known returns."""
        # Create equity curve with consistent daily returns
        dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(252)]
        # 0.1% daily return = ~25% annual, low volatility
        daily_return = 0.001
        equities = [100_000 * (1 + daily_return) ** i for i in range(252)]
        pnls = np.diff(equities, prepend=100_000)
        peaks = np.maximum.accumulate(equities)
        drawdowns = np.array(equities) - peaks

        df = pd.DataFrame({
            "date": dates,
            "trade_num": range(1, 253),
            "pnl": pnls,
            "equity": equities,
            "peak": peaks,
            "drawdown": drawdowns,
            "win": [True] * 252,
        })

        sharpe = calculator.calculate_sharpe_ratio(df)
        # With consistent positive returns and low vol, Sharpe should be high
        assert sharpe is not None
        assert sharpe > 2.0  # High Sharpe for consistent returns

    def test_calculate_sortino_ratio(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Sortino ratio penalizes only downside volatility."""
        dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(100)]
        # Alternating returns: +2%, -1%, creating positive skew
        returns = [0.02 if i % 2 == 0 else -0.01 for i in range(100)]
        equities = [100_000]
        for r in returns:
            equities.append(equities[-1] * (1 + r))
        equities = equities[1:]  # Remove starting capital
        pnls = np.diff([100_000] + equities)
        peaks = np.maximum.accumulate(equities)
        drawdowns = np.array(equities) - peaks

        df = pd.DataFrame({
            "date": dates,
            "trade_num": range(1, 101),
            "pnl": pnls,
            "equity": equities,
            "peak": peaks,
            "drawdown": drawdowns,
            "win": [r > 0 for r in returns],
        })

        sortino = calculator.calculate_sortino_ratio(df)
        sharpe = calculator.calculate_sharpe_ratio(df)

        assert sortino is not None
        assert sharpe is not None
        # Sortino should be higher than Sharpe for positive skew
        assert sortino > sharpe

    def test_calculate_max_drawdown(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Max drawdown from peak to trough."""
        dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(10)]
        # Peak at 150k, drops to 120k = 20% drawdown
        equities = [100_000, 120_000, 150_000, 140_000, 130_000,
                    120_000, 125_000, 130_000, 140_000, 145_000]
        pnls = np.diff([100_000] + equities)
        peaks = np.maximum.accumulate(equities)
        drawdowns = np.array(equities) - peaks

        df = pd.DataFrame({
            "date": dates,
            "trade_num": range(1, 11),
            "pnl": pnls,
            "equity": equities,
            "peak": peaks,
            "drawdown": drawdowns,
            "win": [p > 0 for p in pnls],
        })

        max_dd_pct, max_dd_dollars = calculator.calculate_max_drawdown(df)

        assert max_dd_pct == pytest.approx(20.0, rel=0.01)  # 20%
        assert max_dd_dollars == pytest.approx(30_000, rel=0.01)  # $30k

    def test_calculate_calmar_ratio(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Calmar = CAGR / |Max Drawdown|."""
        dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(365)]
        # 20% return with 10% max drawdown = Calmar of 2.0
        equities = list(np.linspace(100_000, 120_000, 365))
        # Inject a 10% drawdown mid-way
        peak_idx = 180
        equities[peak_idx] = 115_000  # Peak
        equities[peak_idx + 1] = 103_500  # 10% drop from peak
        for i in range(peak_idx + 2, 365):
            equities[i] = equities[i-1] * 1.0003  # Recover
        equities[-1] = 120_000  # End at 20% gain

        pnls = np.diff([100_000] + equities)
        peaks = np.maximum.accumulate(equities)
        drawdowns = np.array(equities) - peaks

        df = pd.DataFrame({
            "date": dates,
            "trade_num": range(1, 366),
            "pnl": pnls,
            "equity": equities,
            "peak": peaks,
            "drawdown": drawdowns,
            "win": [p > 0 for p in pnls],
        })

        calmar = calculator.calculate_calmar_ratio(df)
        assert calmar is not None
        assert calmar > 1.5  # Should be around 2.0

    def test_calculate_win_rate(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Win rate from PnL data."""
        dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(10)]
        pnls = [100, -50, 200, -100, 150, -75, 300, -25, 100, 50]  # 6 wins, 4 losses
        equities = list(np.cumsum([100_000] + pnls))[1:]

        df = pd.DataFrame({
            "date": dates,
            "trade_num": range(1, 11),
            "pnl": pnls,
            "equity": equities,
            "peak": np.maximum.accumulate(equities),
            "drawdown": [0] * 10,
            "win": [p > 0 for p in pnls],
        })

        win_rate = calculator.calculate_win_rate(df)
        assert win_rate == pytest.approx(60.0, rel=0.01)  # 60%

    def test_calculate_profit_factor(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Profit factor = gross profits / gross losses."""
        dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(6)]
        # Profits: 100 + 200 + 300 = 600, Losses: 50 + 100 = 150
        # PF = 600 / 150 = 4.0
        pnls = [100, -50, 200, -100, 300, 50]
        equities = list(np.cumsum([100_000] + pnls))[1:]

        df = pd.DataFrame({
            "date": dates,
            "trade_num": range(1, 7),
            "pnl": pnls,
            "equity": equities,
            "peak": np.maximum.accumulate(equities),
            "drawdown": [0] * 6,
            "win": [p > 0 for p in pnls],
        })

        pf = calculator.calculate_profit_factor(df)
        assert pf == pytest.approx(4.33, rel=0.01)  # (100+200+300+50)/(50+100) = 650/150

    def test_calculate_t_statistic(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """T-statistic tests if mean return differs from zero."""
        dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(100)]
        # Consistent positive returns should have high t-stat
        np.random.seed(0)  # Seed 0 gives clearly positive sample mean
        returns = np.random.normal(0.001, 0.01, 100)  # Mean 0.1%, std 1%
        equities = [100_000]
        for r in returns:
            equities.append(equities[-1] * (1 + r))
        equities = equities[1:]

        df = pd.DataFrame({
            "date": dates,
            "trade_num": range(1, 101),
            "pnl": np.diff([100_000] + equities),
            "equity": equities,
            "peak": np.maximum.accumulate(equities),
            "drawdown": [0] * 100,
            "win": [True] * 100,
        })

        t_stat, p_value = calculator.calculate_t_statistic(df)
        assert t_stat is not None
        assert p_value is not None
        # With mean > 0, t-stat should be positive
        assert t_stat > 0

    def test_calculate_var_cvar(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """VaR and CVaR at 95% confidence."""
        dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(100)]
        np.random.seed(42)
        # Returns with some tail events
        returns = np.random.normal(0, 0.02, 100)
        returns[10] = -0.10  # 10% loss event
        returns[50] = -0.08  # 8% loss event

        equities = [100_000]
        for r in returns:
            equities.append(equities[-1] * (1 + r))
        equities = equities[1:]

        df = pd.DataFrame({
            "date": dates,
            "trade_num": range(1, 101),
            "pnl": np.diff([100_000] + equities),
            "equity": equities,
            "peak": np.maximum.accumulate(equities),
            "drawdown": [0] * 100,
            "win": [r > 0 for r in returns],
        })

        var_95, cvar_95 = calculator.calculate_var_cvar(df)
        assert var_95 is not None
        assert cvar_95 is not None
        # CVaR should be worse (more negative) than VaR
        assert cvar_95 < var_95
