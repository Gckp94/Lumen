# tests/unit/test_portfolio_metrics_calculator.py
"""Unit tests for PortfolioMetricsCalculator."""
import pandas as pd
import numpy as np
import pytest
from datetime import date, timedelta

from src.core.portfolio_metrics_calculator import PortfolioMetricsCalculator, PortfolioMetrics


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

    def test_calculate_period_metrics_daily(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Daily period metrics aggregation."""
        # Create 20 trading days with multiple trades per day
        dates = []
        for d in range(20):
            dates.extend([date(2024, 1, 2) + timedelta(days=d)] * 3)

        # Create returns that aggregate to known daily values
        pnls = []
        for d in range(20):
            if d % 2 == 0:  # Even days: green days
                pnls.extend([500, 300, 200])  # +$1000 total
            else:  # Odd days: red days
                pnls.extend([-200, -300, -100])  # -$600 total

        equities = list(np.cumsum([100_000] + pnls))[1:]

        df = pd.DataFrame({
            "date": dates,
            "trade_num": range(1, 61),
            "pnl": pnls,
            "equity": equities,
            "peak": np.maximum.accumulate(equities),
            "drawdown": [0] * 60,
            "win": [p > 0 for p in pnls],
        })

        daily = calculator.calculate_period_metrics(df, "daily")

        assert daily is not None
        assert daily.win_pct == pytest.approx(50.0, rel=0.01)  # 10 green, 10 red
        assert daily.avg_green_pct is not None
        assert daily.avg_green_pct > 0
        assert daily.avg_red_pct is not None
        assert daily.avg_red_pct < 0

    def test_calculate_period_metrics_weekly(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Weekly period metrics with ISO week aggregation."""
        # Create 4 weeks of data
        dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(28)]
        np.random.seed(42)
        pnls = np.random.normal(100, 500, 28)
        equities = list(np.cumsum([100_000] + list(pnls)))[1:]

        df = pd.DataFrame({
            "date": dates,
            "trade_num": range(1, 29),
            "pnl": pnls,
            "equity": equities,
            "peak": np.maximum.accumulate(equities),
            "drawdown": [0] * 28,
            "win": [p > 0 for p in pnls],
        })

        weekly = calculator.calculate_period_metrics(df, "weekly")

        assert weekly is not None
        assert weekly.win_pct is not None
        assert 0 <= weekly.win_pct <= 100

    def test_calculate_period_metrics_monthly(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Monthly period metrics aggregation."""
        # Create 3 months of data
        dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(90)]
        np.random.seed(42)
        pnls = np.random.normal(200, 1000, 90)
        equities = list(np.cumsum([100_000] + list(pnls)))[1:]

        df = pd.DataFrame({
            "date": dates,
            "trade_num": range(1, 91),
            "pnl": pnls,
            "equity": equities,
            "peak": np.maximum.accumulate(equities),
            "drawdown": [0] * 90,
            "win": [p > 0 for p in pnls],
        })

        monthly = calculator.calculate_period_metrics(df, "monthly")

        assert monthly is not None
        assert monthly.max_win_pct is not None
        assert monthly.max_loss_pct is not None

    def test_calculate_all_metrics(
        self, calculator: PortfolioMetricsCalculator, sample_equity_curve: pd.DataFrame
    ) -> None:
        """Full metrics calculation returns PortfolioMetrics dataclass."""
        metrics = calculator.calculate_all_metrics(sample_equity_curve)

        assert metrics is not None
        assert isinstance(metrics, PortfolioMetrics)

        # Core metrics should be populated
        assert metrics.cagr is not None
        assert metrics.sharpe_ratio is not None
        assert metrics.max_drawdown_pct is not None

        # Period metrics should be populated
        assert metrics.daily is not None
        assert metrics.weekly is not None
        assert metrics.monthly is not None

    def test_calculate_period_metrics_start_equity_uses_first_pnl(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Verify start_equity is calculated using first trade's PnL, not total period PnL.

        This tests a bug fix where the old code used:
            start_equity = first_equity - total_period_pnl  (WRONG)
        Instead of:
            start_equity = first_equity - first_trade_pnl   (CORRECT)

        The bug caused inflated return percentages when total period PnL >> first trade PnL.
        """
        # Create a month with 3 trades where total PnL is much larger than first PnL
        # Starting capital: $100,000
        # Trade 1: +$100 PnL, equity = $100,100
        # Trade 2: +$9,000 PnL, equity = $109,100
        # Trade 3: +$900 PnL, equity = $110,000
        # Total month PnL = $10,000
        dates = [date(2024, 1, 15), date(2024, 1, 20), date(2024, 1, 25)]
        pnls = [100, 9000, 900]  # Total = 10,000
        equities = [100_100, 109_100, 110_000]  # Cumulative from $100,000 start

        df = pd.DataFrame({
            "date": dates,
            "trade_num": [1, 2, 3],
            "pnl": pnls,
            "equity": equities,
            "peak": [100_100, 109_100, 110_000],
            "drawdown": [0, 0, 0],
            "win": [True, True, True],
        })

        monthly = calculator.calculate_period_metrics(df, "monthly")

        assert monthly is not None

        # Correct calculation:
        # start_equity = first_equity - first_pnl = 100,100 - 100 = 100,000
        # return = total_pnl / start_equity = 10,000 / 100,000 = 10%
        #
        # OLD BUG calculation (would be wrong):
        # start_equity = first_equity - total_pnl = 100,100 - 10,000 = 90,100
        # return = 10,000 / 90,100 = 11.1%
        assert monthly.max_win_pct == pytest.approx(10.0, rel=0.01)  # 10%, not 11.1%

    def test_calculate_pearson_correlation(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Pearson correlation between two equity curves."""
        dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(100)]

        # Create correlated equity curves (r ~ 0.8)
        np.random.seed(42)
        base_returns = np.random.normal(0.001, 0.02, 100)
        # Correlated returns: 80% from base + 20% noise
        corr_returns = 0.8 * base_returns + 0.2 * np.random.normal(0.001, 0.02, 100)

        baseline_eq = [100_000]
        combined_eq = [100_000]
        for br, cr in zip(base_returns, corr_returns):
            baseline_eq.append(baseline_eq[-1] * (1 + br))
            combined_eq.append(combined_eq[-1] * (1 + cr))

        baseline_df = pd.DataFrame({
            "date": dates,
            "equity": baseline_eq[1:],
            "pnl": np.diff(baseline_eq),
            "peak": np.maximum.accumulate(baseline_eq[1:]),
            "drawdown": [0] * 100,
            "win": [True] * 100,
        })
        combined_df = baseline_df.copy()
        combined_df["equity"] = combined_eq[1:]
        combined_df["pnl"] = np.diff(combined_eq)

        corr = calculator.calculate_pearson_correlation(baseline_df, combined_df)

        assert corr is not None
        assert 0.5 < corr < 1.0  # Should be positively correlated

    def test_calculate_rolling_correlation(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Rolling 60-day correlation tracks time-varying relationship."""
        dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(120)]
        np.random.seed(42)

        # First 60 days: high correlation, next 60 days: lower correlation
        base_returns = np.random.normal(0.001, 0.02, 120)
        corr_returns = np.concatenate([
            0.9 * base_returns[:60] + 0.1 * np.random.normal(0, 0.02, 60),  # High corr
            0.3 * base_returns[60:] + 0.7 * np.random.normal(0, 0.02, 60),  # Low corr
        ])

        baseline_eq = [100_000]
        combined_eq = [100_000]
        for br, cr in zip(base_returns, corr_returns):
            baseline_eq.append(baseline_eq[-1] * (1 + br))
            combined_eq.append(combined_eq[-1] * (1 + cr))

        baseline_df = pd.DataFrame({
            "date": dates,
            "equity": baseline_eq[1:],
            "pnl": np.diff(baseline_eq),
            "peak": np.maximum.accumulate(baseline_eq[1:]),
            "drawdown": [0] * 120,
            "win": [True] * 120,
        })
        combined_df = baseline_df.copy()
        combined_df["equity"] = combined_eq[1:]

        current, min_val, max_val, series = calculator.calculate_rolling_correlation(
            baseline_df, combined_df, window=60
        )

        assert current is not None
        assert min_val is not None
        assert max_val is not None
        assert series is not None
        assert len(series) > 0
        assert min_val < max_val  # Should vary over time

    def test_calculate_tail_correlation(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Tail correlation measures correlation during stress periods."""
        dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(200)]
        np.random.seed(42)

        # Normal days: low correlation. Bad days: high correlation (correlated losses)
        base_returns = np.random.normal(0.001, 0.02, 200)
        combined_returns = np.random.normal(0.001, 0.02, 200)

        # Inject correlated bad days
        bad_day_indices = [10, 50, 100, 150]
        for idx in bad_day_indices:
            base_returns[idx] = -0.05
            combined_returns[idx] = -0.04  # Correlated loss

        baseline_eq = [100_000]
        combined_eq = [100_000]
        for br, cr in zip(base_returns, combined_returns):
            baseline_eq.append(baseline_eq[-1] * (1 + br))
            combined_eq.append(combined_eq[-1] * (1 + cr))

        baseline_df = pd.DataFrame({
            "date": dates,
            "equity": baseline_eq[1:],
            "pnl": np.diff(baseline_eq),
            "peak": np.maximum.accumulate(baseline_eq[1:]),
            "drawdown": [0] * 200,
            "win": [r > 0 for r in base_returns],
        })
        combined_df = baseline_df.copy()
        combined_df["equity"] = combined_eq[1:]

        tail_corr = calculator.calculate_tail_correlation(baseline_df, combined_df)

        assert tail_corr is not None
        # Tail correlation should be higher than overall correlation
        overall_corr = calculator.calculate_pearson_correlation(baseline_df, combined_df)
        assert tail_corr > overall_corr  # More correlated in bad times

    def test_calculate_drawdown_correlation(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Drawdown correlation measures if strategies suffer simultaneously."""
        dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(100)]

        # Create equity curves with correlated drawdowns
        baseline_eq = [100_000, 105_000, 110_000, 108_000, 105_000,  # drawdown starts
                       103_000, 100_000, 102_000, 105_000, 110_000]  # recovery
        baseline_eq.extend([110_000 + i * 100 for i in range(90)])

        combined_eq = [100_000, 103_000, 108_000, 106_000, 104_000,  # correlated DD
                       101_000, 99_000, 101_000, 104_000, 108_000]
        combined_eq.extend([108_000 + i * 80 for i in range(90)])

        baseline_peaks = np.maximum.accumulate(baseline_eq)
        combined_peaks = np.maximum.accumulate(combined_eq)

        baseline_df = pd.DataFrame({
            "date": dates,
            "equity": baseline_eq,
            "pnl": np.diff([100_000] + baseline_eq),
            "peak": baseline_peaks,
            "drawdown": np.array(baseline_eq) - baseline_peaks,
            "win": [True] * 100,
        })
        combined_df = pd.DataFrame({
            "date": dates,
            "equity": combined_eq,
            "pnl": np.diff([100_000] + combined_eq),
            "peak": combined_peaks,
            "drawdown": np.array(combined_eq) - combined_peaks,
            "win": [True] * 100,
        })

        dd_corr = calculator.calculate_drawdown_correlation(baseline_df, combined_df)

        assert dd_corr is not None
        assert dd_corr > 0.5  # Should be positively correlated drawdowns

    def test_calculate_lower_tail_dependence(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Lower tail dependence measures joint extreme loss probability."""
        dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(200)]
        np.random.seed(42)

        # Create returns with tail dependence
        base_returns = np.random.normal(0.001, 0.02, 200)
        combined_returns = np.random.normal(0.001, 0.02, 200)

        # When baseline is in worst 10%, combined is also in worst 10% (35% of time)
        # This is higher than the 10% expected under independence
        worst_baseline_idx = np.argsort(base_returns)[:20]  # Worst 10%
        for idx in worst_baseline_idx[:7]:  # 7 of 20 = 35%
            combined_returns[idx] = np.random.uniform(-0.05, -0.03)

        baseline_eq = [100_000]
        combined_eq = [100_000]
        for br, cr in zip(base_returns, combined_returns):
            baseline_eq.append(baseline_eq[-1] * (1 + br))
            combined_eq.append(combined_eq[-1] * (1 + cr))

        baseline_df = pd.DataFrame({
            "date": dates,
            "equity": baseline_eq[1:],
            "pnl": np.diff(baseline_eq),
            "peak": np.maximum.accumulate(baseline_eq[1:]),
            "drawdown": [0] * 200,
            "win": [r > 0 for r in base_returns],
        })
        combined_df = baseline_df.copy()
        combined_df["equity"] = combined_eq[1:]

        ltd = calculator.calculate_lower_tail_dependence(baseline_df, combined_df)

        assert ltd is not None
        assert 0 <= ltd <= 1
        assert ltd > 0.10  # Should be higher than independence (0.10)

    def test_calculate_marginal_sharpe_contribution(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Marginal Sharpe contribution shows if adding strategy improves Sharpe."""
        dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(252)]
        np.random.seed(42)

        # Baseline: moderate Sharpe
        base_returns = np.random.normal(0.0005, 0.015, 252)
        # Combined: slightly better Sharpe (uncorrelated alpha)
        combined_returns = base_returns + np.random.normal(0.0002, 0.005, 252)

        baseline_eq = [100_000]
        combined_eq = [100_000]
        for br, cr in zip(base_returns, combined_returns):
            baseline_eq.append(baseline_eq[-1] * (1 + br))
            combined_eq.append(combined_eq[-1] * (1 + cr))

        baseline_df = pd.DataFrame({
            "date": dates,
            "equity": baseline_eq[1:],
            "pnl": np.diff(baseline_eq),
            "peak": np.maximum.accumulate(baseline_eq[1:]),
            "drawdown": [0] * 252,
            "win": [r > 0 for r in base_returns],
        })
        combined_df = baseline_df.copy()
        combined_df["equity"] = combined_eq[1:]

        result = calculator.calculate_marginal_sharpe_contribution(baseline_df, combined_df)

        assert result is not None
        assert "sharpe_baseline" in result
        assert "sharpe_combined" in result
        assert "sharpe_improvement" in result
        assert result["sharpe_improvement"] > 0  # Combined should be better

    def test_calculate_var_cvar_contribution(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """VaR and CVaR contribution measures change in tail risk."""
        dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(200)]
        np.random.seed(42)

        base_returns = np.random.normal(0.001, 0.02, 200)
        # Combined has lower tail risk (less negative outliers)
        combined_returns = np.random.normal(0.001, 0.015, 200)

        baseline_eq = [100_000]
        combined_eq = [100_000]
        for br, cr in zip(base_returns, combined_returns):
            baseline_eq.append(baseline_eq[-1] * (1 + br))
            combined_eq.append(combined_eq[-1] * (1 + cr))

        baseline_df = pd.DataFrame({
            "date": dates,
            "equity": baseline_eq[1:],
            "pnl": np.diff(baseline_eq),
            "peak": np.maximum.accumulate(baseline_eq[1:]),
            "drawdown": [0] * 200,
            "win": [r > 0 for r in base_returns],
        })
        combined_df = baseline_df.copy()
        combined_df["equity"] = combined_eq[1:]

        var_result = calculator.calculate_var_contribution(baseline_df, combined_df)
        cvar_result = calculator.calculate_cvar_contribution(baseline_df, combined_df)

        assert var_result is not None
        assert cvar_result is not None
        # Marginal should be positive (improved = less negative VaR)
        assert var_result["var_marginal"] > 0

    def test_calculate_edge_decay(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Edge decay analysis detects declining Sharpe ratio over time."""
        dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(504)]  # 2 years
        np.random.seed(42)

        # First year: high returns, second year: lower returns (decay)
        returns_y1 = np.random.normal(0.002, 0.015, 252)  # ~50% annual, Sharpe ~2
        returns_y2 = np.random.normal(0.0005, 0.015, 252)  # ~12% annual, Sharpe ~0.5
        returns = np.concatenate([returns_y1, returns_y2])

        equities = [100_000]
        for r in returns:
            equities.append(equities[-1] * (1 + r))

        df = pd.DataFrame({
            "date": dates,
            "equity": equities[1:],
            "pnl": np.diff(equities),
            "peak": np.maximum.accumulate(equities[1:]),
            "drawdown": [0] * 504,
            "win": [r > 0 for r in returns],
        })

        result = calculator.calculate_edge_decay(df, window=252)

        assert result is not None
        assert "rolling_sharpe_current" in result
        assert "rolling_sharpe_early" in result
        assert "decay_pct" in result
        assert "rolling_sharpe_series" in result
        # Early period should have higher Sharpe than recent
        assert result["rolling_sharpe_early"] > result["rolling_sharpe_current"]
        assert result["decay_pct"] < 0  # Negative = decay

    def test_calculate_edge_decay_gain_metrics(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Edge decay analysis includes avg and median gain change metrics."""
        dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(504)]  # 2 years
        np.random.seed(42)

        # First year: high gains, second year: lower gains (decay)
        gains_y1 = np.random.normal(0.02, 0.03, 252)  # 2% avg gain
        gains_y2 = np.random.normal(0.005, 0.03, 252)  # 0.5% avg gain
        gains = np.concatenate([gains_y1, gains_y2])

        # Convert gains to equity curve
        equities = [100_000]
        pnls = []
        for g in gains:
            pnl = equities[-1] * g
            pnls.append(pnl)
            equities.append(equities[-1] + pnl)

        df = pd.DataFrame({
            "date": dates,
            "gain_pct": gains * 100,  # Store as percentage
            "equity": equities[1:],
            "pnl": pnls,
            "peak": np.maximum.accumulate(equities[1:]),
            "drawdown": [0] * 504,
            "win": [g > 0 for g in gains],
        })

        result = calculator.calculate_edge_decay(df, window=252)

        assert result is not None
        # New keys must exist
        assert "avg_gain_early" in result
        assert "avg_gain_recent" in result
        assert "avg_gain_change_pct" in result
        assert "median_gain_early" in result
        assert "median_gain_recent" in result
        assert "median_gain_change_pct" in result
        # Early period should have higher gains than recent
        assert result["avg_gain_early"] > result["avg_gain_recent"]
        assert result["avg_gain_change_pct"] < 0  # Negative = decay
        assert result["median_gain_early"] > result["median_gain_recent"]
        assert result["median_gain_change_pct"] < 0  # Negative = decay

    def test_calculate_edge_decay_without_gain_pct(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Edge decay works without gain_pct column (Sharpe only)."""
        dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(504)]
        np.random.seed(42)

        returns = np.random.normal(0.001, 0.015, 504)
        equities = [100_000]
        for r in returns:
            equities.append(equities[-1] * (1 + r))

        # No gain_pct column
        df = pd.DataFrame({
            "date": dates,
            "equity": equities[1:],
            "pnl": np.diff(equities),
            "peak": np.maximum.accumulate(equities[1:]),
            "drawdown": [0] * 504,
            "win": [r > 0 for r in returns],
        })

        result = calculator.calculate_edge_decay(df, window=252)

        assert result is not None
        # Sharpe metrics should exist
        assert "rolling_sharpe_current" in result
        assert "decay_pct" in result
        # Gain metrics should NOT exist
        assert "avg_gain_early" not in result
        assert "median_gain_early" not in result

    def test_calculate_ticker_overlap(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Ticker overlap measures how often strategies trade same securities."""
        dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(20)]

        # Baseline trades: AAPL, MSFT, GOOG (3 unique)
        baseline_df = pd.DataFrame({
            "date": dates[:10],
            "ticker": ["AAPL", "MSFT", "GOOG", "AAPL", "MSFT",
                       "GOOG", "AAPL", "MSFT", "GOOG", "AAPL"],
            "equity": [100_000 + i * 100 for i in range(10)],
            "pnl": [100] * 10,
            "peak": [100_000 + i * 100 for i in range(10)],
            "drawdown": [0] * 10,
            "win": [True] * 10,
        })

        # Combined trades: AAPL, MSFT, TSLA, NVDA (4 unique, 2 overlap)
        combined_df = pd.DataFrame({
            "date": dates[10:],
            "ticker": ["AAPL", "MSFT", "TSLA", "NVDA", "AAPL",
                       "TSLA", "NVDA", "MSFT", "TSLA", "NVDA"],
            "equity": [101_000 + i * 100 for i in range(10)],
            "pnl": [100] * 10,
            "peak": [101_000 + i * 100 for i in range(10)],
            "drawdown": [0] * 10,
            "win": [True] * 10,
        })

        result = calculator.calculate_ticker_overlap(baseline_df, combined_df)

        assert result is not None
        assert result["baseline_ticker_count"] == 3
        assert result["combined_ticker_count"] == 4
        assert result["overlapping_count"] == 2  # AAPL, MSFT
        assert result["overlap_pct"] == pytest.approx(66.67, rel=0.01)  # 2/3

    def test_calculate_concurrent_exposure(
        self, calculator: PortfolioMetricsCalculator
    ) -> None:
        """Concurrent exposure measures same-day same-ticker trades."""
        # Baseline: AAPL on Jan 2, MSFT on Jan 3
        baseline_df = pd.DataFrame({
            "date": [date(2024, 1, 2), date(2024, 1, 3)],
            "ticker": ["AAPL", "MSFT"],
            "equity": [100_000, 100_100],
            "pnl": [100, 100],
            "peak": [100_000, 100_100],
            "drawdown": [0, 0],
            "win": [True, True],
        })

        # Combined: AAPL on Jan 2 (concurrent!), GOOG on Jan 3
        combined_df = pd.DataFrame({
            "date": [date(2024, 1, 2), date(2024, 1, 3)],
            "ticker": ["AAPL", "GOOG"],
            "equity": [100_000, 100_100],
            "pnl": [100, 100],
            "peak": [100_000, 100_100],
            "drawdown": [0, 0],
            "win": [True, True],
        })

        result = calculator.calculate_concurrent_exposure(baseline_df, combined_df)

        assert result is not None
        assert result["concurrent_count"] == 1  # AAPL on Jan 2
        assert result["concurrent_pct"] > 0
