"""Integration tests for column detection edge cases."""

import pandas as pd
import pytest

from src.core.column_mapper import ColumnMapper
from src.core.metrics import MetricsCalculator
from src.core.models import AdjustmentParams


class TestColumnDetectionWithSimilarNames:
    """Test auto-detection when columns have similar names."""

    def test_gain_pct_vs_gain_pct_from_low(self) -> None:
        """Should select 'gain_pct' over 'gain_pct_from_low'."""
        # Simulate the problematic column structure
        columns = [
            "ticker",
            "date",
            "trigger_time_et",
            "gain_pct_from_low",  # Wrong - huge values
            "gain_pct",  # Correct - decimal percentages
            "mae_pct",
            "mfe_pct",
        ]

        mapper = ColumnMapper()
        result = mapper.auto_detect(columns)

        assert result.mapping is not None
        assert result.mapping.gain_pct == "gain_pct"
        assert result.mapping.time == "trigger_time_et"  # Only time-like column

    def test_metrics_with_correct_column(self) -> None:
        """Metrics calculation should work with correctly detected column."""
        # Create test data mimicking the real data structure
        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL", "MSFT"],
            "date": ["2024-01-01", "2024-01-01", "2024-01-02"],
            "trigger_time_et": ["09:30:00", "10:00:00", "09:35:00"],
            "gain_pct_from_low": [50.0, -80.0, 120.0],  # Wrong column - huge values
            "gain_pct": [0.05, -0.03, 0.08],  # Correct column - decimal percentages
            "mae_pct": [0.02, 0.05, 0.01],
            "mfe_pct": [0.10, 0.02, 0.12],
        })

        mapper = ColumnMapper()
        result = mapper.auto_detect(list(df.columns))

        assert result.mapping is not None
        assert result.mapping.gain_pct == "gain_pct"

        # Calculate metrics
        calc = MetricsCalculator()
        metrics, _, _ = calc.calculate(
            df=df,
            gain_col=result.mapping.gain_pct,
            derived=True,
            breakeven_is_win=False,
        )

        # With correct column: 2 winners (0.05, 0.08), 1 loser (-0.03)
        assert metrics.winner_count == 2
        assert metrics.loser_count == 1
        assert metrics.win_rate == pytest.approx(66.67, rel=0.01)


class TestAdjustmentWithDecimalGains:
    """Test adjustment calculations with decimal-format gain data."""

    def test_adjustment_produces_valid_metrics(self) -> None:
        """Metrics should be valid after adjustment with decimal gains."""
        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL", "MSFT", "AMZN"],
            "date": ["2024-01-01"] * 4,
            "time": ["09:30:00"] * 4,
            "gain_pct": [0.20, -0.05, 0.03, 0.15],  # Decimal: 20%, -5%, 3%, 15%
            "mae_pct": [5.0, 3.0, 2.0, 12.0],  # Percentage format
        })

        calc = MetricsCalculator()
        adj = AdjustmentParams(stop_loss=8.0, efficiency=5.0)

        metrics, _, _ = calc.calculate(
            df=df,
            gain_col="gain_pct",
            mae_col="mae_pct",
            derived=True,
            breakeven_is_win=False,
            adjustment_params=adj,
        )

        # After adjustment:
        # Trade 1: 20% - 5% = 15% (winner)
        # Trade 2: -5% - 5% = -10% (loser)
        # Trade 3: 3% - 5% = -2% (loser, was winner)
        # Trade 4: -8% (stop) - 5% = -13% (loser, hit stop)

        assert metrics.winner_count == 1, "Should have 1 winner after adjustment"
        assert metrics.loser_count == 3, "Should have 3 losers after adjustment"
        assert metrics.win_rate == pytest.approx(25.0, rel=0.01)
        assert metrics.avg_winner is not None, "avg_winner should not be None"
        assert metrics.avg_winner == pytest.approx(15.0, rel=0.01)  # 15%
