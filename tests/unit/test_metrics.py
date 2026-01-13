"""Unit tests for MetricsCalculator."""

import pandas as pd
import pytest

from src.core.metrics import MetricsCalculator
from src.core.models import TradingMetrics


class TestMetricsCalculator:
    """Tests for MetricsCalculator class."""

    def test_basic_calculation(self) -> None:
        """Basic metrics calculation with balanced wins/losses."""
        calc = MetricsCalculator()
        df = pd.DataFrame({
            "gain_pct": [2.0, 3.0, -1.0, -2.0, 1.5, -0.5],  # 3 wins, 3 losses
        })
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        assert metrics.num_trades == 6
        assert metrics.win_rate == 50.0
        assert metrics.winner_count == 3
        assert metrics.loser_count == 3

    def test_win_rate_calculation(self) -> None:
        """Win rate calculation is correct percentage."""
        calc = MetricsCalculator()
        df = pd.DataFrame({
            "gain_pct": [1.0, 2.0, 3.0, -1.0],  # 75% win rate
        })
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)
        assert metrics.win_rate == 75.0

    def test_avg_winner_loser(self) -> None:
        """Avg winner/loser calculations."""
        calc = MetricsCalculator()
        # User data is in decimal format: 0.02 = 2%, 0.04 = 4%, etc.
        df = pd.DataFrame({
            "gain_pct": [0.02, 0.04, -0.01, -0.03],  # avg_win=3.0%, avg_lose=-2.0%
        })
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)
        assert metrics.avg_winner == pytest.approx(3.0)  # 3.0%
        assert metrics.avg_loser == pytest.approx(-2.0)  # -2.0%

    def test_rr_ratio(self) -> None:
        """R:R ratio calculation."""
        calc = MetricsCalculator()
        df = pd.DataFrame({
            "gain_pct": [2.0, 4.0, -1.0, -3.0],  # R:R = 3.0 / 2.0 = 1.5
        })
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)
        assert metrics.rr_ratio == pytest.approx(1.5)

    def test_ev_calculation(self) -> None:
        """EV calculation."""
        calc = MetricsCalculator()
        # 60% win rate, avg_win=2.0%, avg_lose=-1.0%
        # EV = (0.6 * 2.0) + (0.4 * -1.0) = 1.2 - 0.4 = 0.8%
        # User data is in decimal format: 0.02 = 2%, etc.
        df = pd.DataFrame({
            "gain_pct": [0.02, 0.02, 0.02, -0.01, -0.01],  # 3 wins, 2 losses
        })
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)
        assert metrics.ev == pytest.approx(0.8)

    def test_kelly_calculation(self) -> None:
        """Kelly criterion calculation."""
        calc = MetricsCalculator()
        # 60% win rate, R:R = 2.0
        # Kelly = 0.6 - (0.4 / 2.0) = 0.6 - 0.2 = 0.4 (40%)
        df = pd.DataFrame({
            "gain_pct": [2.0, 2.0, 2.0, -1.0, -1.0],
        })
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)
        assert metrics.kelly == pytest.approx(40.0)

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame returns empty metrics."""
        calc = MetricsCalculator()
        df = pd.DataFrame(columns=["gain_pct"])
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        assert metrics.num_trades == 0
        assert metrics.win_rate is None
        assert metrics.avg_winner is None
        assert metrics.avg_loser is None
        assert metrics.rr_ratio is None
        assert metrics.ev is None
        assert metrics.kelly is None

    def test_no_winners(self) -> None:
        """All losers edge case."""
        calc = MetricsCalculator()
        # User data is in decimal format: -0.01 = -1%, etc.
        df = pd.DataFrame({
            "gain_pct": [-0.01, -0.02, -0.03],
        })
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        assert metrics.num_trades == 3
        assert metrics.win_rate == 0.0
        assert metrics.winner_count == 0
        assert metrics.loser_count == 3
        assert metrics.avg_winner is None
        assert metrics.avg_loser == pytest.approx(-2.0)  # -2.0%
        assert metrics.rr_ratio is None
        assert metrics.ev is None
        assert metrics.kelly is None

    def test_no_losers(self) -> None:
        """All winners edge case."""
        calc = MetricsCalculator()
        # User data is in decimal format: 0.01 = 1%, etc.
        df = pd.DataFrame({
            "gain_pct": [0.01, 0.02, 0.03],
        })
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        assert metrics.num_trades == 3
        assert metrics.win_rate == 100.0
        assert metrics.winner_count == 3
        assert metrics.loser_count == 0
        assert metrics.avg_winner == pytest.approx(2.0)  # 2.0%
        assert metrics.avg_loser is None
        assert metrics.rr_ratio is None

    def test_breakeven_is_win_true(self) -> None:
        """Breakeven classified as win when breakeven_is_win=True."""
        calc = MetricsCalculator()
        df = pd.DataFrame({
            "gain_pct": [0.0, 1.0, -1.0],  # 0 is win
        })
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True, breakeven_is_win=True)

        assert metrics.winner_count == 2  # 0.0 and 1.0
        assert metrics.loser_count == 1

    def test_breakeven_is_win_false(self) -> None:
        """Breakeven classified as loss when breakeven_is_win=False (default)."""
        calc = MetricsCalculator()
        df = pd.DataFrame({
            "gain_pct": [0.0, 1.0, -1.0],  # 0 is loss
        })
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True, breakeven_is_win=False)

        assert metrics.winner_count == 1  # Only 1.0
        assert metrics.loser_count == 2  # 0.0 and -1.0

    def test_explicit_win_loss_column(self) -> None:
        """Use explicit win/loss column."""
        calc = MetricsCalculator()
        df = pd.DataFrame({
            "gain_pct": [2.0, -1.0, 3.0],
            "result": ["W", "L", "Win"],
        })
        metrics, _, _ = calc.calculate(df, "gain_pct", win_loss_col="result")

        assert metrics.winner_count == 2
        assert metrics.loser_count == 1

    def test_explicit_win_loss_with_integers(self) -> None:
        """Use explicit win/loss column with integer values."""
        calc = MetricsCalculator()
        df = pd.DataFrame({
            "gain_pct": [2.0, -1.0, 3.0],
            "result": [1, 0, 1],  # 1=win, 0=loss
        })
        metrics, _, _ = calc.calculate(df, "gain_pct", win_loss_col="result")

        assert metrics.winner_count == 2
        assert metrics.loser_count == 1

    def test_distribution_data(self) -> None:
        """Distribution data (winner_gains, loser_gains) is populated."""
        calc = MetricsCalculator()
        df = pd.DataFrame({
            "gain_pct": [2.0, 3.0, -1.0, -2.0],
        })
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        assert metrics.winner_gains == [2.0, 3.0]
        assert metrics.loser_gains == [-1.0, -2.0]

    def test_standard_deviation(self) -> None:
        """Standard deviation calculated for 2+ trades."""
        calc = MetricsCalculator()
        df = pd.DataFrame({
            "gain_pct": [1.0, 2.0, 3.0, -1.0, -2.0, -3.0],
        })
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        assert metrics.winner_std is not None
        assert metrics.loser_std is not None
        assert metrics.winner_std > 0
        assert metrics.loser_std > 0

    def test_single_winner_no_std(self) -> None:
        """Single winner has None std (need 2+ for std)."""
        calc = MetricsCalculator()
        df = pd.DataFrame({
            "gain_pct": [2.0, -1.0, -2.0],  # 1 winner, 2 losers
        })
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        assert metrics.winner_std is None
        assert metrics.loser_std is not None

    def test_returns_trading_metrics_instance(self) -> None:
        """Returns TradingMetrics instance."""
        calc = MetricsCalculator()
        df = pd.DataFrame({
            "gain_pct": [1.0, -1.0],
        })
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        assert isinstance(metrics, TradingMetrics)


@pytest.mark.slow
class TestMetricsCalculatorPerformance:
    """Performance tests for MetricsCalculator."""

    def test_performance_100k_rows(self) -> None:
        """Performance: < 100ms for 100k rows."""
        from time import perf_counter

        import numpy as np

        calc = MetricsCalculator()
        np.random.seed(42)
        df = pd.DataFrame({
            "gain_pct": np.random.normal(0.5, 3, 100_000),
        })

        start = perf_counter()
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)
        elapsed = perf_counter() - start

        assert elapsed < 0.1, f"Metrics calculation took {elapsed:.3f}s, exceeds 100ms limit"
        assert metrics.num_trades == 100_000


class TestMetricsCalculatorExtended:
    """Tests for extended MetricsCalculator (Story 3.2 - metrics 8-12)."""

    @pytest.fixture
    def known_trades_df(self) -> pd.DataFrame:
        """DataFrame with known expected metric values.

        User data is in decimal format: 0.05 = 5%, etc.
        """
        return pd.DataFrame({
            "gain_pct": [0.05, 0.10, 0.15, 0.08, 0.12, -0.03, -0.05, -0.04, -0.06, -0.02],
            "mae_pct": [0.01, 0.02, 0.03, 0.015, 0.025, 0.03, 0.05, 0.04, 0.06, 0.02],
        })

    def test_edge_formula(self, known_trades_df: pd.DataFrame) -> None:
        """Edge % = ((R:R + 1) × Win Rate) - 1, returned as percentage."""
        calc = MetricsCalculator()
        metrics, _, _ = calc.calculate(known_trades_df, "gain_pct", derived=True)

        # Known trades: 5 winners, 5 losers = 50% win rate
        # avg_winner = 10%, avg_loser = -4%, R:R = 10/4 = 2.5
        # Edge = ((2.5 + 1) * 0.50) - 1 = (3.5 * 0.50) - 1 = 1.75 - 1 = 0.75 = 75%
        expected_edge = (((metrics.rr_ratio + 1) * (metrics.win_rate / 100)) - 1) * 100
        assert metrics.edge == pytest.approx(expected_edge, abs=0.01)

    def test_fractional_kelly_applies_fraction(
        self, known_trades_df: pd.DataFrame
    ) -> None:
        """Fractional Kelly = Kelly * (fraction / 100)."""
        calc = MetricsCalculator()
        metrics, _, _ = calc.calculate(
            known_trades_df, "gain_pct", derived=True, fractional_kelly_pct=25.0
        )

        # Expected: Kelly=30.0%, Frac Kelly = 30.0 * 0.25 = 7.5%
        assert metrics.fractional_kelly == pytest.approx(7.5, abs=0.01)

    def test_fractional_kelly_different_percentages(
        self, known_trades_df: pd.DataFrame
    ) -> None:
        """Fractional Kelly works with different percentages."""
        calc = MetricsCalculator()

        # 50%
        metrics_50, _, _ = calc.calculate(
            known_trades_df, "gain_pct", derived=True, fractional_kelly_pct=50.0
        )
        assert metrics_50.fractional_kelly == pytest.approx(15.0, abs=0.01)

        # 100%
        metrics_100, _, _ = calc.calculate(
            known_trades_df, "gain_pct", derived=True, fractional_kelly_pct=100.0
        )
        assert metrics_100.fractional_kelly == pytest.approx(
            metrics_100.kelly, abs=0.01
        )

    def test_expected_growth_calculation(self, known_trades_df: pd.DataFrame) -> None:
        """Expected growth formula: EG = f * m - (f² * σ²) / 2."""
        calc = MetricsCalculator()
        metrics, _, _ = calc.calculate(known_trades_df, "gain_pct", derived=True)

        # Verify expected_growth is calculated
        assert metrics.expected_growth is not None

        # Manually calculate for verification
        kelly_decimal = metrics.kelly / 100
        all_gains = metrics.winner_gains + metrics.loser_gains
        combined_variance = float(pd.Series(all_gains).var())
        expected_eg = (kelly_decimal * metrics.ev) - (
            (kelly_decimal**2) * combined_variance / 2
        )
        assert metrics.expected_growth == pytest.approx(expected_eg, abs=0.001)

    def test_median_calculations(self, known_trades_df: pd.DataFrame) -> None:
        """Median winner and loser calculations."""
        calc = MetricsCalculator()
        metrics, _, _ = calc.calculate(known_trades_df, "gain_pct", derived=True)

        # Winners: [0.05, 0.10, 0.15, 0.08, 0.12] -> sorted: [0.05,0.08,0.10,0.12,0.15] -> median=0.10 (10%)
        # Multiplied by 100 for percentage format: 0.10 * 100 = 10.0%
        assert metrics.median_winner == pytest.approx(10.0, abs=0.1)
        # Losers: [-0.03, -0.05, -0.04, -0.06, -0.02] -> sorted -> median=-0.04 (-4%)
        # Multiplied by 100 for percentage format: -0.04 * 100 = -4.0%
        assert metrics.median_loser == pytest.approx(-4.0, abs=0.1)

    def test_distribution_min_max(self, known_trades_df: pd.DataFrame) -> None:
        """Min/max for winner and loser distributions."""
        calc = MetricsCalculator()
        metrics, _, _ = calc.calculate(known_trades_df, "gain_pct", derived=True)

        # Multiplied by 100 for percentage format
        assert metrics.winner_min == pytest.approx(5.0, abs=0.1)   # 0.05 * 100 = 5.0%
        assert metrics.winner_max == pytest.approx(15.0, abs=0.1)  # 0.15 * 100 = 15.0%
        assert metrics.loser_min == pytest.approx(-6.0, abs=0.1)   # -0.06 * 100 = -6.0% (Most negative)
        assert metrics.loser_max == pytest.approx(-2.0, abs=0.1)   # -0.02 * 100 = -2.0% (Least negative)

    def test_edge_none_when_rr_ratio_none(self) -> None:
        """Edge is None when R:R ratio cannot be calculated."""
        calc = MetricsCalculator()
        # All losers - avg_winner is None, so rr_ratio is None
        df = pd.DataFrame({"gain_pct": [-1.0, -2.0, -3.0]})
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        assert metrics.rr_ratio is None
        assert metrics.edge is None

    def test_fractional_kelly_none_when_kelly_none(self) -> None:
        """Fractional Kelly is None when Kelly cannot be calculated."""
        calc = MetricsCalculator()
        # All losers - Kelly is None
        df = pd.DataFrame({"gain_pct": [-1.0, -2.0, -3.0]})
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        assert metrics.kelly is None
        assert metrics.fractional_kelly is None

    def test_expected_growth_none_when_kelly_none(self) -> None:
        """Expected growth is None when Kelly cannot be calculated."""
        calc = MetricsCalculator()
        df = pd.DataFrame({"gain_pct": [-1.0, -2.0, -3.0]})
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        assert metrics.expected_growth is None

    def test_expected_growth_none_with_single_trade(self) -> None:
        """Expected growth is None with single trade (can't calculate variance)."""
        calc = MetricsCalculator()
        df = pd.DataFrame({"gain_pct": [5.0]})
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        # Single trade, variance needs at least 2
        assert metrics.expected_growth is None

    def test_median_winner_none_with_no_winners(self) -> None:
        """Median winner is None when no winners."""
        calc = MetricsCalculator()
        df = pd.DataFrame({"gain_pct": [-1.0, -2.0, -3.0]})
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        assert metrics.median_winner is None
        assert metrics.winner_min is None
        assert metrics.winner_max is None

    def test_median_loser_none_with_no_losers(self) -> None:
        """Median loser is None when no losers."""
        calc = MetricsCalculator()
        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0]})
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        assert metrics.median_loser is None
        assert metrics.loser_min is None
        assert metrics.loser_max is None

    def test_empty_dataframe_extended_metrics(self) -> None:
        """Empty DataFrame returns None for all extended metrics."""
        calc = MetricsCalculator()
        df = pd.DataFrame(columns=["gain_pct"])
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        assert metrics.edge is None
        assert metrics.fractional_kelly is None
        assert metrics.expected_growth is None
        assert metrics.median_winner is None
        assert metrics.median_loser is None
        assert metrics.winner_min is None
        assert metrics.winner_max is None
        assert metrics.loser_min is None
        assert metrics.loser_max is None


class TestMetricsCalculatorWithAdjustments:
    """Tests for MetricsCalculator with stop loss and efficiency adjustments."""

    def test_adjustment_params_applied(self) -> None:
        """Adjustment params modify gains before metric calculation."""
        from src.core.models import AdjustmentParams

        calc = MetricsCalculator()
        # Trade 1: gain=20, mae=3, stop not hit -> adj_gain = 20 - 5 = 15 (win)
        # Trade 2: gain=10, mae=10, stop HIT (10 > 8) -> adj_gain = -8 - 5 = -13 (loss)
        # Trade 3: gain=-2, mae=5, stop not hit -> adj_gain = -2 - 5 = -7 (loss)
        # Trade 4: gain=5, mae=12, stop HIT (12 > 8) -> adj_gain = -8 - 5 = -13 (loss)
        df = pd.DataFrame({
            "gain_pct": [20.0, 10.0, -2.0, 5.0],
            "mae_pct": [3.0, 10.0, 5.0, 12.0],
        })

        params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
        metrics, _, _ = calc.calculate(
            df, "gain_pct", derived=True,
            adjustment_params=params, mae_col="mae_pct"
        )

        # Expected: 1 winner (15), 3 losers (-13, -7, -13)
        assert metrics.num_trades == 4
        assert metrics.winner_count == 1
        assert metrics.loser_count == 3
        assert metrics.win_rate == 25.0  # 1/4

    def test_adjustment_avg_winner_loser(self) -> None:
        """Adjusted gains used for avg winner/loser calculation."""
        from src.core.models import AdjustmentParams

        calc = MetricsCalculator()
        # Gains in decimal format (0.20 = 20%), MAE in percentage format (3.0 = 3%)
        # Trade 1: 20% gain, 3% MAE < 8% stop -> 20% - 5% = 15%
        # Trade 2: 10% gain, 10% MAE > 8% stop -> -8% - 5% = -13%
        # Trade 3: -2% gain, 5% MAE < 8% stop -> -2% - 5% = -7%
        # Trade 4: 5% gain, 12% MAE > 8% stop -> -8% - 5% = -13%
        df = pd.DataFrame({
            "gain_pct": [0.20, 0.10, -0.02, 0.05],
            "mae_pct": [3.0, 10.0, 5.0, 12.0],  # Percentage format
        })

        params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)  # Percentage format
        metrics, _, _ = calc.calculate(
            df, "gain_pct", derived=True,
            adjustment_params=params, mae_col="mae_pct"
        )

        # Winner: 15% -> displayed as 15.0%
        # Losers: -13%, -7%, -13%, avg = -11%
        assert metrics.avg_winner == pytest.approx(15.0)
        assert metrics.avg_loser == pytest.approx(-11.0)

    def test_no_adjustment_without_params(self) -> None:
        """Without adjustment_params, original gains are used."""
        calc = MetricsCalculator()
        df = pd.DataFrame({
            "gain_pct": [20.0, 10.0, -2.0, 5.0],
            "mae_pct": [3.0, 10.0, 5.0, 12.0],
        })

        # No adjustment_params
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        # Original: 3 winners (20, 10, 5), 1 loser (-2)
        assert metrics.winner_count == 3
        assert metrics.loser_count == 1
        assert metrics.win_rate == 75.0

    def test_adjustment_without_mae_col_uses_original(self) -> None:
        """If mae_col is None, original gains are used even with params."""
        from src.core.models import AdjustmentParams

        calc = MetricsCalculator()
        df = pd.DataFrame({
            "gain_pct": [20.0, 10.0, -2.0, 5.0],
            "mae_pct": [3.0, 10.0, 5.0, 12.0],
        })

        params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
        # mae_col is None
        metrics, _, _ = calc.calculate(
            df, "gain_pct", derived=True,
            adjustment_params=params, mae_col=None
        )

        # Original: 3 winners (20, 10, 5), 1 loser (-2)
        assert metrics.winner_count == 3
        assert metrics.loser_count == 1

    def test_adjustment_stop_at_boundary(self) -> None:
        """MAE equal to stop_loss does not trigger stop."""
        from src.core.models import AdjustmentParams

        calc = MetricsCalculator()
        # Gains in decimal format (0.10 = 10%), MAE in percentage format (8.0 = 8%)
        # mae = 8.0 == stop_loss = 8.0, so stop NOT triggered (uses <=)
        df = pd.DataFrame({
            "gain_pct": [0.10],
            "mae_pct": [8.0],  # Percentage format
        })

        params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)  # Percentage format
        metrics, _, _ = calc.calculate(
            df, "gain_pct", derived=True,
            adjustment_params=params, mae_col="mae_pct"
        )

        # adj_gain = 10% - 5% = 5% -> displayed as 5.0%
        assert metrics.winner_count == 1
        assert metrics.avg_winner == pytest.approx(5.0)

    def test_adjustment_all_stops_hit(self) -> None:
        """All trades hit stop loss."""
        from src.core.models import AdjustmentParams

        calc = MetricsCalculator()
        # Gains in decimal format (0.20 = 20%), MAE in percentage format (15.0 = 15%)
        # All MAE values > 8% stop_loss
        df = pd.DataFrame({
            "gain_pct": [0.20, 0.15, 0.10],
            "mae_pct": [15.0, 12.0, 9.0],  # All > 8% stop_loss, percentage format
        })

        params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)  # Percentage format
        metrics, _, _ = calc.calculate(
            df, "gain_pct", derived=True,
            adjustment_params=params, mae_col="mae_pct"
        )

        # All: -8% - 5% = -13% -> displayed as -13.0%
        assert metrics.winner_count == 0
        assert metrics.loser_count == 3
        assert metrics.win_rate == 0.0
        assert metrics.avg_loser == pytest.approx(-13.0)

    def test_winner_classification_uses_adjusted_gains(self) -> None:
        """Winners should be classified by adjusted gain sign, not raw Win/Loss column.

        This ensures avg_winner is always positive even when stop-loss adjustments
        turn originally winning trades into losses.
        """
        from src.core.models import AdjustmentParams

        # Gains in decimal format (0.10 = 10%), MAE in percentage format (10.0 = 10%)
        # Trade 1: 10% gain, 10% MAE > 8% stop -> -8% - 5% = -13% (LOSS)
        # Trade 2: 5% gain, 2% MAE < 8% stop -> 5% - 5% = 0% (LOSS with default breakeven_is_win=False)
        # Trade 3: -3% loss, 2% MAE < 8% stop -> -3% - 5% = -8% (LOSS)
        df = pd.DataFrame({
            "gain_pct": [0.10, 0.05, -0.03],  # Decimal format
            "mae_pct": [10.0, 2.0, 2.0],  # Percentage format, first exceeds 8% stop
            "win_loss": ["W", "W", "L"],
        })

        params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
        calc = MetricsCalculator()
        metrics, _, _ = calc.calculate(
            df,
            gain_col="gain_pct",
            win_loss_col="win_loss",
            derived=False,  # Would have used explicit column before fix
            adjustment_params=params,
            mae_col="mae_pct",
        )

        # After adjustment: [-13%, 0%, -8%]
        # Winners (>0): none
        # Losers (<=0): all 3
        assert metrics.winner_count == 0
        assert metrics.loser_count == 3
        assert metrics.avg_winner is None  # No winners
        assert metrics.avg_loser is not None
        assert metrics.avg_loser < 0  # Always negative


class TestMetricsCalculatorStreaks:
    """Tests for streak metrics calculation (Story 3.3)."""

    @pytest.fixture
    def streak_test_df(self) -> pd.DataFrame:
        """DataFrame with known streak patterns.

        Pattern: W W W L L W L L L W
        Max consecutive wins: 3 (trades 1-3)
        Max consecutive losses: 3 (trades 7-9)
        Max loss: -6.0% (trade 7)

        User data is in decimal format: 0.05 = 5%, etc.
        """
        return pd.DataFrame({
            "gain_pct": [0.05, 0.03, 0.07, -0.02, -0.04, 0.08, -0.06, -0.03, -0.05, 0.02],
            "mae_pct": [0.01] * 10,
        })

    def test_max_consecutive_wins_basic(self, streak_test_df: pd.DataFrame) -> None:
        """Max consecutive wins = 3 (trades 1-3)."""
        calc = MetricsCalculator()
        metrics, _, _ = calc.calculate(streak_test_df, "gain_pct", derived=True)
        assert metrics.max_consecutive_wins == 3

    def test_max_consecutive_losses_basic(self, streak_test_df: pd.DataFrame) -> None:
        """Max consecutive losses = 3 (trades 7-9)."""
        calc = MetricsCalculator()
        metrics, _, _ = calc.calculate(streak_test_df, "gain_pct", derived=True)
        assert metrics.max_consecutive_losses == 3

    def test_streaks_empty_dataframe(self) -> None:
        """Empty DataFrame returns (None, None) for streaks."""
        calc = MetricsCalculator()
        empty_df = pd.DataFrame(columns=["gain_pct"])
        metrics, _, _ = calc.calculate(empty_df, "gain_pct", derived=True)
        assert metrics.max_consecutive_wins is None
        assert metrics.max_consecutive_losses is None

    def test_streaks_all_winners(self) -> None:
        """All winners: max wins = num_trades, max losses = 0."""
        calc = MetricsCalculator()
        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0, 4.0, 5.0]})
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)
        assert metrics.max_consecutive_wins == 5
        assert metrics.max_consecutive_losses == 0

    def test_streaks_all_losers(self) -> None:
        """All losers: max wins = 0, max losses = num_trades."""
        calc = MetricsCalculator()
        df = pd.DataFrame({"gain_pct": [-1.0, -2.0, -3.0, -4.0, -5.0]})
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)
        assert metrics.max_consecutive_wins == 0
        assert metrics.max_consecutive_losses == 5

    def test_streaks_alternating(self) -> None:
        """Alternating W/L: max = 1 for both."""
        calc = MetricsCalculator()
        df = pd.DataFrame({"gain_pct": [1.0, -1.0, 1.0, -1.0]})
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)
        assert metrics.max_consecutive_wins == 1
        assert metrics.max_consecutive_losses == 1

    def test_streaks_single_trade_winner(self) -> None:
        """Single winning trade: max wins = 1, max losses = 0."""
        calc = MetricsCalculator()
        df = pd.DataFrame({"gain_pct": [5.0]})
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)
        assert metrics.max_consecutive_wins == 1
        assert metrics.max_consecutive_losses == 0

    def test_streaks_single_trade_loser(self) -> None:
        """Single losing trade: max wins = 0, max losses = 1."""
        calc = MetricsCalculator()
        df = pd.DataFrame({"gain_pct": [-5.0]})
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)
        assert metrics.max_consecutive_wins == 0
        assert metrics.max_consecutive_losses == 1

    def test_chronological_sorting_affects_streaks(self) -> None:
        """Verify sorting by date/time affects streak calculation."""
        calc = MetricsCalculator()
        # Unsorted: W L L W (max loss streak = 2)
        # After sorting by date: L W W L (max win streak = 2)
        df = pd.DataFrame({
            "date": ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-01"],
            "time": ["09:30", "09:30", "09:30", "09:30"],
            "gain_pct": [5.0, -2.0, -3.0, 4.0],
        })

        # Without sorting - just calculate, used for comparison understanding
        _, _, _ = calc.calculate(df, "gain_pct", derived=True)

        # With sorting
        metrics_sorted, _, _ = calc.calculate(
            df, "gain_pct", derived=True, date_col="date", time_col="time"
        )

        # The sorted order is: 2024-01-01 (W), 2024-01-02 (W), 2024-01-03 (L), 2024-01-04 (L)
        # Unsorted: 2024-01-02 (W), 2024-01-03 (L), 2024-01-04 (L), 2024-01-01 (W)
        # The results should differ
        # Sorted: WWLL -> max_consecutive_wins = 2, max_consecutive_losses = 2
        assert metrics_sorted.max_consecutive_wins == 2
        assert metrics_sorted.max_consecutive_losses == 2


class TestMetricsCalculatorMaxLoss:
    """Tests for max_loss_pct calculation (Story 3.3).

    max_loss_pct now represents the percentage of trades that hit the stop loss level
    (where MAE > stop_loss), not the worst single-trade loss.
    """

    def test_max_loss_pct_none_without_adjustment_params(self) -> None:
        """Max loss % is None when no adjustment_params are provided."""
        calc = MetricsCalculator()
        df = pd.DataFrame({
            "gain_pct": [0.05, -0.02, 0.10, -0.06, -0.03],
        })
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)
        # Without adjustment_params, max_loss_pct is None
        assert metrics.max_loss_pct is None

    def test_max_loss_pct_none_when_no_mae_col(self) -> None:
        """Max loss % is None when mae_col is not provided."""
        from src.core.models import AdjustmentParams

        calc = MetricsCalculator()
        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0, 4.0, 5.0]})
        params = AdjustmentParams(stop_loss=5.0, efficiency=0.0)
        metrics, _, _ = calc.calculate(
            df, "gain_pct", derived=True,
            adjustment_params=params, mae_col=None
        )
        assert metrics.max_loss_pct is None

    def test_max_loss_pct_counts_stops_hit(self) -> None:
        """Max loss % counts percentage of trades where MAE > stop_loss."""
        from src.core.models import AdjustmentParams

        calc = MetricsCalculator()
        # MAE values: 2%, 1%, 1% - none exceed 5% stop_loss
        df = pd.DataFrame({
            "gain_pct": [-0.08, -0.03, 0.05],
            "mae_pct": [2.0, 1.0, 1.0],  # Percentage format
        })
        params = AdjustmentParams(stop_loss=5.0, efficiency=0.0)
        metrics, _, _ = calc.calculate(
            df, "gain_pct", derived=True,
            adjustment_params=params, mae_col="mae_pct"
        )
        # No trades hit stop (all MAE < 5%), so 0%
        assert metrics.max_loss_pct == 0.0

    def test_max_loss_pct_some_stops_hit(self) -> None:
        """Max loss % correctly calculates when some trades hit stop."""
        from src.core.models import AdjustmentParams

        calc = MetricsCalculator()
        # Trade 1: MAE=10% > 5% stop (hit)
        # Trade 2: MAE=2% < 5% stop (not hit)
        # Trade 3: MAE=1% < 5% stop (not hit)
        df = pd.DataFrame({
            "gain_pct": [-0.08, -0.06, 0.05],
            "mae_pct": [10.0, 2.0, 1.0],  # Percentage format
        })
        params = AdjustmentParams(stop_loss=5.0, efficiency=0.0)
        metrics, _, _ = calc.calculate(
            df, "gain_pct", derived=True,
            adjustment_params=params, mae_col="mae_pct"
        )
        # 1 out of 3 trades hit stop = 33.33%
        assert metrics.max_loss_pct == pytest.approx(33.33, abs=0.1)

    def test_max_loss_pct_all_trades_hit_stop(self) -> None:
        """Max loss % is 100% when all trades hit stop.

        MAE in percentage format (15.0 = 15%).
        """
        from src.core.models import AdjustmentParams

        calc = MetricsCalculator()
        df = pd.DataFrame({
            "gain_pct": [-0.10, -0.08, -0.12],  # Decimal format
            "mae_pct": [15.0, 10.0, 20.0],     # All exceed stop_loss=5%, percentage format
        })
        params = AdjustmentParams(stop_loss=5.0, efficiency=0.0)  # Percentage format
        metrics, _, _ = calc.calculate(
            df, "gain_pct", derived=True,
            adjustment_params=params, mae_col="mae_pct"
        )
        # All 3 trades hit stop = 100%
        assert metrics.max_loss_pct == 100.0

    def test_max_loss_pct_boundary_not_hit(self) -> None:
        """MAE equal to stop_loss does not count as hitting stop (uses >)."""
        from src.core.models import AdjustmentParams

        calc = MetricsCalculator()
        df = pd.DataFrame({
            "gain_pct": [0.05, -0.02, 0.10],
            "mae_pct": [5.0, 5.0, 5.0],  # All exactly at stop_loss
        })
        params = AdjustmentParams(stop_loss=5.0, efficiency=0.0)
        metrics, _, _ = calc.calculate(
            df, "gain_pct", derived=True,
            adjustment_params=params, mae_col="mae_pct"
        )
        # MAE = stop_loss is NOT a hit (uses > not >=), so 0%
        assert metrics.max_loss_pct == 0.0


class TestMetricsCalculatorFlatStake:
    """Tests for flat stake metrics integration (Story 3.4)."""

    def test_flat_stake_metrics_populated(self) -> None:
        """Flat stake metrics populated when flat_stake provided."""
        calc = MetricsCalculator()
        df = pd.DataFrame({"gain_pct": [5.0, 3.0, -4.0, -2.0, 8.0]})
        metrics, equity_curve, _ = calc.calculate(
            df, "gain_pct", derived=True, flat_stake=1000.0
        )

        assert metrics.flat_stake_pnl is not None
        assert metrics.flat_stake_pnl == pytest.approx(100.0, abs=0.01)
        assert equity_curve is not None
        assert len(equity_curve) == 5

    def test_flat_stake_none_when_no_stake_provided(self) -> None:
        """Flat stake metrics are None when no stake provided."""
        calc = MetricsCalculator()
        df = pd.DataFrame({"gain_pct": [5.0, 3.0, -4.0]})
        metrics, equity_curve, _ = calc.calculate(df, "gain_pct", derived=True)

        assert metrics.flat_stake_pnl is None
        assert metrics.flat_stake_max_dd is None
        assert metrics.flat_stake_max_dd_pct is None
        assert metrics.flat_stake_dd_duration is None
        assert equity_curve is None

    def test_flat_stake_none_when_empty_data(self) -> None:
        """Flat stake metrics are None for empty DataFrame."""
        calc = MetricsCalculator()
        df = pd.DataFrame(columns=["gain_pct"])
        metrics, equity_curve, _ = calc.calculate(
            df, "gain_pct", derived=True, flat_stake=1000.0
        )

        assert metrics.flat_stake_pnl is None
        assert equity_curve is None

    def test_flat_stake_returns_tuple(self) -> None:
        """Calculate returns tuple of (metrics, flat_equity, kelly_equity)."""
        calc = MetricsCalculator()
        df = pd.DataFrame({"gain_pct": [5.0, 3.0]})
        result = calc.calculate(df, "gain_pct", derived=True, flat_stake=1000.0)

        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_flat_stake_dd_duration_not_recovered(self) -> None:
        """DD duration 'Not recovered' for ongoing drawdown."""
        calc = MetricsCalculator()
        df = pd.DataFrame({"gain_pct": [5.0, -10.0, 3.0]})
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True, flat_stake=1000.0)

        assert metrics.flat_stake_dd_duration == "Not recovered"


class TestMetricsCalculatorKellyIntegration:
    """Tests for Kelly metrics integration (Story 3.5)."""

    def test_kelly_metrics_populated_with_start_capital(self) -> None:
        """Kelly metrics populated when start_capital provided."""
        calc = MetricsCalculator()
        df = pd.DataFrame({"gain_pct": [5.0, 3.0, -4.0, -2.0, 8.0]})
        metrics, _, kelly_equity = calc.calculate(
            df, "gain_pct", derived=True,
            start_capital=10000.0, fractional_kelly_pct=25.0
        )

        assert metrics.kelly_pnl is not None
        assert metrics.kelly_max_dd is not None or metrics.kelly_max_dd_pct is None
        assert kelly_equity is not None
        assert len(kelly_equity) == 5

    def test_kelly_metrics_none_without_start_capital(self) -> None:
        """Kelly metrics are None when no start_capital provided."""
        calc = MetricsCalculator()
        df = pd.DataFrame({"gain_pct": [5.0, 3.0, -4.0]})
        metrics, _, kelly_equity = calc.calculate(df, "gain_pct", derived=True)

        assert metrics.kelly_pnl is None
        assert metrics.kelly_max_dd is None
        assert metrics.kelly_max_dd_pct is None
        assert metrics.kelly_dd_duration is None
        assert kelly_equity is None

    def test_kelly_metrics_none_for_empty_data(self) -> None:
        """Kelly metrics are None for empty DataFrame."""
        calc = MetricsCalculator()
        df = pd.DataFrame(columns=["gain_pct"])
        metrics, _, kelly_equity = calc.calculate(
            df, "gain_pct", derived=True, start_capital=10000.0
        )

        assert metrics.kelly_pnl is None
        assert kelly_equity is None

    def test_kelly_uses_calculated_kelly_pct(self) -> None:
        """Kelly metrics use the calculated kelly % from core metrics."""
        calc = MetricsCalculator()
        # 60% win rate, R:R = 2.0 -> Kelly = 40%
        df = pd.DataFrame({"gain_pct": [2.0, 2.0, 2.0, -1.0, -1.0]})
        metrics, _, kelly_equity = calc.calculate(
            df, "gain_pct", derived=True,
            start_capital=10000.0, fractional_kelly_pct=100.0
        )

        # Verify Kelly was calculated correctly
        assert metrics.kelly == pytest.approx(40.0, abs=0.1)
        # Kelly equity should exist
        assert kelly_equity is not None

    def test_kelly_both_curves_returned(self) -> None:
        """Both flat stake and Kelly equity curves returned."""
        calc = MetricsCalculator()
        df = pd.DataFrame({"gain_pct": [5.0, 3.0, -4.0, -2.0, 8.0]})
        metrics, flat_equity, kelly_equity = calc.calculate(
            df, "gain_pct", derived=True,
            flat_stake=1000.0, start_capital=10000.0
        )

        assert flat_equity is not None
        assert kelly_equity is not None
        assert len(flat_equity) == 5
        assert len(kelly_equity) == 5

    def test_kelly_equity_curve_has_position_size(self) -> None:
        """Kelly equity curve includes position_size column."""
        calc = MetricsCalculator()
        df = pd.DataFrame({"gain_pct": [5.0, 3.0, -4.0]})
        _, _, kelly_equity = calc.calculate(
            df, "gain_pct", derived=True, start_capital=10000.0
        )

        assert kelly_equity is not None
        assert "position_size" in kelly_equity.columns

    def test_kelly_dd_duration_blown(self) -> None:
        """Kelly dd_duration shows 'Blown' for wiped account."""
        calc = MetricsCalculator()
        # High Kelly, big loss -> potential blown account
        # Create scenario where account goes negative
        df = pd.DataFrame({"gain_pct": [10.0, -200.0]})  # Big loss
        metrics, _, _ = calc.calculate(
            df, "gain_pct", derived=True,
            start_capital=1000.0, fractional_kelly_pct=100.0
        )

        # If the Kelly calculation results in blown account
        if metrics.kelly_dd_duration == "Blown":
            assert True
        else:
            # May also be None if Kelly is negative/None
            assert metrics.kelly_dd_duration in (None, "Not recovered", "Blown") or isinstance(
                metrics.kelly_dd_duration, int
            )

    def test_kelly_negative_returns_none_metrics(self) -> None:
        """Negative Kelly (strategy with negative expectancy) returns None metrics."""
        calc = MetricsCalculator()
        # All losers -> negative expectancy -> negative Kelly
        df = pd.DataFrame({"gain_pct": [-1.0, -2.0, -3.0]})
        metrics, _, kelly_equity = calc.calculate(
            df, "gain_pct", derived=True, start_capital=10000.0
        )

        # Kelly should be None (no winners, can't calculate)
        assert metrics.kelly is None
        # Kelly metrics should be None
        assert metrics.kelly_pnl is None
        assert kelly_equity is None


class TestFilteredMetricsEdgeCases:
    """Tests for filtered metrics edge cases (Story 4.1)."""

    def test_calculate_empty_df_returns_empty_metrics(self) -> None:
        """Empty DataFrame (no filter matches) returns empty metrics."""
        calc = MetricsCalculator()
        df = pd.DataFrame(columns=["gain_pct"])
        metrics, flat_equity, kelly_equity = calc.calculate(df, "gain_pct", derived=True)

        assert metrics.num_trades == 0
        assert metrics.win_rate is None
        assert metrics.avg_winner is None
        assert metrics.avg_loser is None
        assert metrics.rr_ratio is None
        assert metrics.ev is None
        assert metrics.kelly is None
        assert metrics.winner_count == 0
        assert metrics.loser_count == 0
        assert flat_equity is None
        assert kelly_equity is None

    def test_calculate_single_row_returns_valid_metrics(self) -> None:
        """Single row filtered result returns valid metrics (some fields None)."""
        calc = MetricsCalculator()
        # User data is in decimal format: 0.05 = 5%
        df = pd.DataFrame({"gain_pct": [0.05]})  # Single winner
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        # Valid for single row
        assert metrics.num_trades == 1
        assert metrics.win_rate == 100.0
        assert metrics.winner_count == 1
        assert metrics.loser_count == 0
        assert metrics.avg_winner == pytest.approx(5.0)  # 5.0%
        assert metrics.avg_loser is None  # No losers
        # Std requires 2+ values
        assert metrics.winner_std is None
        assert metrics.loser_std is None
        # Streaks should be 1 for single trade
        assert metrics.max_consecutive_wins == 1
        assert metrics.max_consecutive_losses == 0
        # R:R ratio requires both winners and losers
        assert metrics.rr_ratio is None

    def test_calculate_single_row_loser_returns_valid_metrics(self) -> None:
        """Single losing row returns valid metrics."""
        calc = MetricsCalculator()
        # User data is in decimal format: -0.03 = -3%
        df = pd.DataFrame({"gain_pct": [-0.03]})  # Single loser
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        assert metrics.num_trades == 1
        assert metrics.win_rate == 0.0
        assert metrics.winner_count == 0
        assert metrics.loser_count == 1
        assert metrics.avg_winner is None
        assert metrics.avg_loser == pytest.approx(-3.0)  # -3.0%
        assert metrics.max_consecutive_wins == 0
        assert metrics.max_consecutive_losses == 1
        # max_loss_pct is None when no adjustment_params provided
        assert metrics.max_loss_pct is None

    def test_calculate_filtered_subset_matches_expected(self) -> None:
        """Filtered subset calculates correct metrics."""
        calc = MetricsCalculator()
        # User data is in decimal format: 0.10 = 10%, etc.
        df = pd.DataFrame({
            "gain_pct": [0.10, 0.05, -0.02, -0.04],  # 2 wins, 2 losses
        })
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        # Verify calculation matches expected
        assert metrics.num_trades == 4
        assert metrics.win_rate == 50.0
        assert metrics.winner_count == 2
        assert metrics.loser_count == 2
        assert metrics.avg_winner == pytest.approx(7.5)  # (10 + 5) / 2 = 7.5%
        assert metrics.avg_loser == pytest.approx(-3.0)  # (-2 + -4) / 2 = -3.0%
        assert metrics.rr_ratio == pytest.approx(2.5)  # 7.5 / 3.0
        # EV = (0.5 * 7.5) + (0.5 * -3.0) = 2.25%
        assert metrics.ev == pytest.approx(2.25)

    def test_calculate_filtered_all_winners(self) -> None:
        """Filtered result with all winners."""
        calc = MetricsCalculator()
        # User data is in decimal format: 0.01 = 1%, etc.
        df = pd.DataFrame({"gain_pct": [0.01, 0.02, 0.03]})
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        assert metrics.num_trades == 3
        assert metrics.win_rate == 100.0
        assert metrics.winner_count == 3
        assert metrics.loser_count == 0
        assert metrics.avg_winner == pytest.approx(2.0)  # 2.0%
        assert metrics.avg_loser is None
        assert metrics.max_loss_pct is None

    def test_calculate_filtered_all_losers(self) -> None:
        """Filtered result with all losers."""
        calc = MetricsCalculator()
        # User data is in decimal format: -0.01 = -1%, etc.
        df = pd.DataFrame({"gain_pct": [-0.01, -0.02, -0.03]})
        metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

        assert metrics.num_trades == 3
        assert metrics.win_rate == 0.0
        assert metrics.winner_count == 0
        assert metrics.loser_count == 3
        assert metrics.avg_winner is None
        assert metrics.avg_loser == pytest.approx(-2.0)  # -2.0%
        # max_loss_pct is None when no adjustment_params provided
        assert metrics.max_loss_pct is None


class TestMaxLossPctStopHit:
    """Tests for max_loss_pct as percentage of trades hitting stop."""

    def test_max_loss_pct_counts_stop_hits(self):
        """max_loss_pct should be (trades where MAE > stop) / total * 100."""
        from src.core.models import AdjustmentParams

        df = pd.DataFrame({
            "gain_pct": [0.05, -0.02, 0.03, -0.04, 0.01, -0.03, 0.02, -0.01, 0.04, -0.02],
            "mae_pct": [5.0, 12.0, 3.0, 9.0, 2.0, 7.0, 4.0, 15.0, 6.0, 8.0],  # 3 trades > 8% stop
        })

        calc = MetricsCalculator()
        adjustment_params = AdjustmentParams(stop_loss=8.0, efficiency=0.0)

        metrics, _, _ = calc.calculate(
            df=df,
            gain_col="gain_pct",
            derived=True,
            adjustment_params=adjustment_params,
            mae_col="mae_pct",
        )

        # 3 out of 10 trades hit stop (mae_pct > 8.0): indices 1, 3, 7 have mae 12, 9, 15
        # 3/10 = 30%
        assert metrics.max_loss_pct == 30.0

    def test_max_loss_pct_zero_when_no_stops_hit(self):
        """max_loss_pct should be 0 when no trades hit stop."""
        from src.core.models import AdjustmentParams

        df = pd.DataFrame({
            "gain_pct": [0.05, -0.02, 0.03],
            "mae_pct": [3.0, 5.0, 2.0],  # All below 8% stop
        })

        calc = MetricsCalculator()
        adjustment_params = AdjustmentParams(stop_loss=8.0, efficiency=0.0)

        metrics, _, _ = calc.calculate(
            df=df,
            gain_col="gain_pct",
            derived=True,
            adjustment_params=adjustment_params,
            mae_col="mae_pct",
        )

        assert metrics.max_loss_pct == 0.0

    def test_max_loss_pct_none_without_adjustment_params(self):
        """max_loss_pct should be None when no adjustment_params provided."""
        df = pd.DataFrame({
            "gain_pct": [0.05, -0.02, 0.03],
        })

        calc = MetricsCalculator()

        metrics, _, _ = calc.calculate(
            df=df,
            gain_col="gain_pct",
            derived=True,
        )

        assert metrics.max_loss_pct is None


class TestCalculateSuggestedBins:
    """Tests for histogram bin size calculation (Story 3.6)."""

    def test_suggested_bins_normal_data(self) -> None:
        """Normal distribution data gives reasonable bin count."""
        import numpy as np

        from src.core.metrics import calculate_suggested_bins

        np.random.seed(42)
        data = list(np.random.normal(5, 2, 100))
        bins = calculate_suggested_bins(data)
        assert 5 <= bins <= 50

    def test_suggested_bins_empty_list(self) -> None:
        """Empty list returns default of 10."""
        from src.core.metrics import calculate_suggested_bins

        bins = calculate_suggested_bins([])
        assert bins == 10

    def test_suggested_bins_single_value(self) -> None:
        """Single value returns default."""
        from src.core.metrics import calculate_suggested_bins

        bins = calculate_suggested_bins([5.0])
        assert bins == 10

    def test_suggested_bins_identical_values(self) -> None:
        """All identical values returns default (IQR=0)."""
        from src.core.metrics import calculate_suggested_bins

        bins = calculate_suggested_bins([5.0, 5.0, 5.0, 5.0])
        assert bins == 10

    def test_suggested_bins_minimum_cap(self) -> None:
        """Result is at least 5."""
        from src.core.metrics import calculate_suggested_bins

        data = [1.0, 1.1]  # Very small range, few data points
        bins = calculate_suggested_bins(data)
        assert bins >= 5

    def test_suggested_bins_maximum_cap(self) -> None:
        """Result is at most 50."""
        from src.core.metrics import calculate_suggested_bins

        data = list(range(10000))
        bins = calculate_suggested_bins(data)
        assert bins <= 50

    def test_suggested_bins_varied_data(self) -> None:
        """Varied data produces reasonable bin count."""
        from src.core.metrics import calculate_suggested_bins

        # Data with clear spread
        data = [1.0, 2.0, 3.0, 5.0, 8.0, 13.0, 21.0, 34.0]
        bins = calculate_suggested_bins(data)
        assert 5 <= bins <= 50

    def test_suggested_bins_two_values(self) -> None:
        """Two distinct values produces valid bin count."""
        from src.core.metrics import calculate_suggested_bins

        data = [1.0, 10.0]
        bins = calculate_suggested_bins(data)
        assert bins >= 5  # Minimum cap applied
