"""Integration tests for initial metrics calculation with stop-loss adjustment.

Verifies that initial metrics calculation (on "Continue" after column mapping)
correctly applies stop-loss and efficiency adjustments.
"""

import pandas as pd
import pytest

from src.core.metrics import MetricsCalculator
from src.core.models import AdjustmentParams


class TestInitialMetricsWithAdjustment:
    """Tests that initial metrics calculation applies default stop-loss."""

    def test_metrics_change_when_stop_loss_applied(self) -> None:
        """Metrics with 100% stop-loss should differ from 8% stop-loss.

        This verifies that passing adjustment_params to MetricsCalculator
        actually changes the results (prerequisite for Task 1 fix).
        """
        # Trade 1: 20% gain, 3% MAE - under stop, stays as 20%
        # Trade 2: -10% loss, 15% MAE - over 8% stop, capped to -8%
        # Trade 3: 15% gain, 5% MAE - under stop, stays as 15%
        # Trade 4: -50% loss, 60% MAE - over 8% stop, capped to -8%
        df = pd.DataFrame({
            'gain_pct': [20.0, -10.0, 15.0, -50.0],
            'mae_pct': [3.0, 15.0, 5.0, 60.0],
        })

        calc = MetricsCalculator()

        # No adjustment (effectively 100% stop-loss)
        metrics_no_adj, _, _ = calc.calculate(df, 'gain_pct', derived=True)

        # With 8% stop-loss, 5% efficiency (default)
        params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
        metrics_adj, _, _ = calc.calculate(
            df, 'gain_pct', derived=True,
            adjustment_params=params, mae_col='mae_pct'
        )

        # Without adjustment: 2 winners (20%, 15%), 2 losers (-10%, -50%)
        assert metrics_no_adj.winner_count == 2
        assert metrics_no_adj.loser_count == 2
        assert metrics_no_adj.win_rate == 50.0

        # With adjustment:
        # Trade 1: 20% - 5% = 15% (winner)
        # Trade 2: -8% - 5% = -13% (loser, stop hit)
        # Trade 3: 15% - 5% = 10% (winner)
        # Trade 4: -8% - 5% = -13% (loser, stop hit)
        # Still 2 winners, 2 losers, but different avg values
        assert metrics_adj.winner_count == 2
        assert metrics_adj.loser_count == 2
        assert metrics_adj.win_rate == 50.0

        # The avg values should differ due to stop-loss capping
        # Without: avg_loser = (-10 + -50) / 2 = -30%
        # With: avg_loser = (-13 + -13) / 2 = -13%
        assert metrics_no_adj.avg_loser != metrics_adj.avg_loser
        assert metrics_adj.avg_loser == pytest.approx(-13.0)

    def test_default_adjustment_params_values(self) -> None:
        """Verify default AdjustmentParams are 100% stop-loss (disabled) and 5% efficiency."""
        params = AdjustmentParams()
        assert params.stop_loss == 100.0
        assert params.efficiency == 5.0
        assert params.is_short is True

    def test_initial_metrics_should_use_adjustment_scenario(self) -> None:
        """Scenario test: initial load should apply default adjustments.

        This test documents the expected behavior after Task 1 fix:
        When a user clicks "Continue" after column mapping, the initial
        metrics should use the default stop-loss (100% = disabled) and efficiency (5%).

        With 100% stop-loss, no trades are stopped out, only efficiency is applied.
        """
        # Simulates the data that would be loaded
        df = pd.DataFrame({
            'ticker': ['AAPL', 'AAPL'],
            'date': ['2024-01-01', '2024-01-02'],
            'time': ['09:30:00', '09:30:00'],
            'gain_pct': [0.10, -0.05],  # 10% gain, 5% loss (decimal format)
            'mae_pct': [5.0, 12.0],  # MAE doesn't matter with 100% stop-loss
        })

        calc = MetricsCalculator()

        # Default adjustment: stop_loss=100% (disabled), efficiency=5%
        params = AdjustmentParams()

        metrics, _, _ = calc.calculate(
            df, 'gain_pct', derived=True,
            adjustment_params=params, mae_col='mae_pct'
        )

        # Trade 1: 10% gain, 5% MAE < 100% stop -> stays 10%, adjusted = 10% - 5% = 5%
        # Trade 2: -5% loss, 12% MAE < 100% stop -> stays -5%, adjusted = -5% - 5% = -10%
        # Result: 1 winner (5%), 1 loser (-10%)
        assert metrics.winner_count == 1
        assert metrics.loser_count == 1
        assert metrics.win_rate == 50.0
        assert metrics.avg_winner == pytest.approx(5.0)
        assert metrics.avg_loser == pytest.approx(-10.0)
