"""Tests to verify baseline metrics use only first triggers."""

import pandas as pd
import pytest

from src.core.metrics import MetricsCalculator
from src.core.first_trigger import FirstTriggerEngine


class TestBaselineMetricsFirstTriggerOnly:
    """Verify baseline metrics exclude trigger_number > 1."""

    def test_metrics_calculated_from_first_triggers_only(self):
        """Metrics should use only trigger_number == 1 rows."""
        engine = FirstTriggerEngine()
        calculator = MetricsCalculator()

        # Create data: AAPL has 3 triggers, MSFT has 2 triggers
        # First triggers: AAPL +10%, MSFT +5% -> 2 wins, avg 7.5%
        # Later triggers: AAPL +20%, +30%, MSFT -5% -> would skew metrics if included
        # Note: gain values are in decimal format (0.10 = 10%)
        df = pd.DataFrame({
            "ticker": ["AAPL", "AAPL", "AAPL", "MSFT", "MSFT"],
            "date": ["2024-01-01"] * 5,
            "time": ["09:30", "09:45", "10:00", "09:30", "09:35"],
            "gain_pct": [0.10, 0.20, 0.30, 0.05, -0.05],
        })

        # Assign trigger numbers
        df = engine.assign_trigger_numbers(df, "ticker", "date", "time")

        # Filter to first triggers for metrics (this is what data_input.py should do)
        first_triggers_df = df[df["trigger_number"] == 1].copy()

        # Calculate metrics from first triggers only
        metrics, _, _ = calculator.calculate(
            df=first_triggers_df,
            gain_col="gain_pct",
        )

        # Should have 2 trades (both first triggers are wins)
        assert metrics.num_trades == 2
        assert metrics.win_rate == 100.0  # Both first triggers are wins
        # Average winner = (10 + 5) / 2 = 7.5% (after *100 conversion)
        assert metrics.avg_winner == pytest.approx(7.5, abs=0.01)

    def test_metrics_differ_when_including_all_triggers(self):
        """Demonstrate that including all triggers gives different results."""
        engine = FirstTriggerEngine()
        calculator = MetricsCalculator()

        # Note: gain values are in decimal format (0.10 = 10%)
        df = pd.DataFrame({
            "ticker": ["AAPL", "AAPL", "MSFT", "MSFT"],
            "date": ["2024-01-01"] * 4,
            "time": ["09:30", "09:45", "09:30", "09:35"],
            "gain_pct": [0.10, -0.15, 0.05, -0.10],  # First triggers win, later lose
        })

        df = engine.assign_trigger_numbers(df, "ticker", "date", "time")

        # Metrics from ALL triggers (incorrect - old behavior)
        all_metrics, _, _ = calculator.calculate(df=df, gain_col="gain_pct")

        # Metrics from FIRST triggers only (correct - new behavior)
        first_only = df[df["trigger_number"] == 1].copy()
        first_metrics, _, _ = calculator.calculate(df=first_only, gain_col="gain_pct")

        # All triggers: 2 wins, 2 losses -> 50% win rate
        assert all_metrics.num_trades == 4
        assert all_metrics.win_rate == 50.0

        # First triggers only: 2 wins, 0 losses -> 100% win rate
        assert first_metrics.num_trades == 2
        assert first_metrics.win_rate == 100.0
