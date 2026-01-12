"""Tests for AdjustmentParams calculation."""

import pandas as pd
import pytest

from src.core.models import AdjustmentParams


class TestAdjustmentCalculation:
    """Tests for adjustment calculation with decimal-format gains."""

    def test_adjustment_preserves_decimal_format(self) -> None:
        """Adjusted gains should remain in decimal format."""
        df = pd.DataFrame({
            "gain_pct": [0.20, -0.05, 0.10],  # 20%, -5%, 10%
            "mae_pct": [5.0, 3.0, 2.0],  # All below 8% stop loss
        })

        adj = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
        result = adj.calculate_adjusted_gains(df, "gain_pct", "mae_pct")

        # Expected: gains converted to %, subtract 5% efficiency, convert back
        # 20% - 5% = 15% -> 0.15
        # -5% - 5% = -10% -> -0.10
        # 10% - 5% = 5% -> 0.05
        expected = [0.15, -0.10, 0.05]

        assert result.tolist() == pytest.approx(expected, rel=1e-6), (
            f"Expected {expected}, got {result.tolist()}. "
            "Adjustment should work with decimal-format gains."
        )

    def test_stop_loss_triggers_correctly(self) -> None:
        """Stop loss should trigger when MAE exceeds threshold."""
        df = pd.DataFrame({
            "gain_pct": [0.20, 0.30],  # 20%, 30%
            "mae_pct": [5.0, 15.0],  # First survives, second hits stop
        })

        adj = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
        result = adj.calculate_adjusted_gains(df, "gain_pct", "mae_pct")

        # First trade: 20% - 5% = 15% -> 0.15
        # Second trade: -8% (stop loss) - 5% = -13% -> -0.13
        expected = [0.15, -0.13]

        assert result.tolist() == pytest.approx(expected, rel=1e-6)

    def test_winner_becomes_loser_after_efficiency(self) -> None:
        """Small winner should become loser after efficiency adjustment."""
        df = pd.DataFrame({
            "gain_pct": [0.03],  # 3% gain
            "mae_pct": [2.0],  # Survives stop loss
        })

        adj = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
        result = adj.calculate_adjusted_gains(df, "gain_pct", "mae_pct")

        # 3% - 5% = -2% -> -0.02
        expected = [-0.02]

        assert result.tolist() == pytest.approx(expected, rel=1e-6)
