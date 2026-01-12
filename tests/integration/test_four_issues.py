"""Integration tests for the four-issues fix."""

from datetime import time

import pandas as pd
import pytest

from src.core.filter_engine import FilterEngine
from src.core.metrics import MetricsCalculator
from src.core.models import AdjustmentParams


class TestIssue1InitialStopLoss:
    """Test that initial metrics apply default stop-loss."""

    def test_metrics_change_when_stop_loss_applied(self) -> None:
        """Metrics with 100% stop-loss should differ from 8% stop-loss."""
        # Trade 1: 20% gain, 3% MAE - under stop, stays as 20%
        # Trade 2: -10% loss, 15% MAE - over 8% stop, capped to -8%
        # Trade 3: 15% gain, 5% MAE - under stop, stays as 15%
        # Trade 4: -50% loss, 60% MAE - over 8% stop, capped to -8%
        df = pd.DataFrame({
            "gain_pct": [0.20, -0.10, 0.15, -0.50],  # Decimal format
            "mae_pct": [3.0, 15.0, 5.0, 60.0],  # Percentage format
        })

        calc = MetricsCalculator()

        # No adjustment (effectively 100% stop-loss)
        metrics_no_adj, _, _ = calc.calculate(df, "gain_pct", derived=True)

        # With 8% stop-loss, 5% efficiency
        params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
        metrics_adj, _, _ = calc.calculate(
            df, "gain_pct", derived=True,
            adjustment_params=params, mae_col="mae_pct"
        )

        # Without adjustment: 2 winners (20%, 15%), 2 losers (-10%, -50%)
        assert metrics_no_adj.winner_count == 2
        assert metrics_no_adj.loser_count == 2

        # With adjustment:
        # Trade 1: 20% - 5% = 15% (winner)
        # Trade 2: -8% - 5% = -13% (loser, stop hit)
        # Trade 3: 15% - 5% = 10% (winner)
        # Trade 4: -8% - 5% = -13% (loser, stop hit)
        assert metrics_adj.winner_count == 2
        assert metrics_adj.loser_count == 2

        # The avg loser values should differ due to stop-loss capping
        # Without: avg_loser = (-10 + -50) / 2 = -30%
        # With: avg_loser = (-13 + -13) / 2 = -13%
        assert metrics_no_adj.avg_loser != metrics_adj.avg_loser
        assert metrics_adj.avg_loser == pytest.approx(-13.0)


class TestIssue2AdjustedGainColumn:
    """Test that adjusted_gain_pct column is added."""

    def test_adjusted_gain_column_calculation(self) -> None:
        """Verify adjusted gain calculation is correct."""
        params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
        df = pd.DataFrame({
            "gain_pct": [0.10, -0.05],  # Decimal format: 10%, -5%
            "mae_pct": [5.0, 12.0],  # Percentage format: 5%, 12%
        })

        adjusted_gains = params.calculate_adjusted_gains(df, "gain_pct", "mae_pct")
        df["adjusted_gain_pct"] = adjusted_gains

        assert "adjusted_gain_pct" in df.columns
        # Trade 1: 10% gain, 5% MAE < 8% stop -> 10% - 5% = 5% = 0.05
        assert abs(df["adjusted_gain_pct"].iloc[0] - 0.05) < 0.001
        # Trade 2: -5% gain, 12% MAE > 8% stop -> -8% - 5% = -13% = -0.13
        assert abs(df["adjusted_gain_pct"].iloc[1] - (-0.13)) < 0.001


class TestIssue4TimeFilter:
    """Test time range filter with various formats."""

    def test_filter_04_30_to_12_00(self) -> None:
        """Filter should include times from 04:30 to 12:00."""
        df = pd.DataFrame({
            "time": ["04:30:00", "09:30:00", "12:00:00", "16:00:00"],
            "value": [1, 2, 3, 4],
        })

        result = FilterEngine.apply_time_range(df, "time", "04:30:00", "12:00:00")

        assert len(result) == 3
        assert list(result["value"]) == [1, 2, 3]

    def test_filter_with_datetime_time_objects(self) -> None:
        """Filter should work with datetime.time objects."""
        df = pd.DataFrame({
            "time": [time(4, 30), time(9, 30), time(12, 0), time(16, 0)],
            "value": [1, 2, 3, 4],
        })

        result = FilterEngine.apply_time_range(df, "time", "04:30:00", "12:00:00")

        assert len(result) == 3
        assert list(result["value"]) == [1, 2, 3]

    def test_filter_returns_empty_when_no_match(self) -> None:
        """Filter returns empty DataFrame when no times match."""
        df = pd.DataFrame({
            "time": ["09:30:00", "10:00:00"],
            "value": [1, 2],
        })

        result = FilterEngine.apply_time_range(df, "time", "20:00:00", "23:00:00")

        assert len(result) == 0
