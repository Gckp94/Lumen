"""Tests for BinningEngine."""

import pandas as pd
import pytest

from src.core.binning_engine import BinningEngine
from src.core.models import BinDefinition, BinMetrics


class TestBinMetricsTotalGain:
    """Tests for total_gain field in BinMetrics."""

    def test_bin_metrics_has_total_gain_field(self) -> None:
        """Test that BinMetrics includes total_gain field."""
        metrics = BinMetrics(
            label="Test",
            count=10,
            average=5.0,
            median=4.5,
            win_rate=60.0,
            total_gain=50.0,  # New field
        )

        assert metrics.total_gain == 50.0

    def test_bin_metrics_total_gain_defaults_to_none(self) -> None:
        """Test that total_gain defaults to None if not specified."""
        metrics = BinMetrics(
            label="Test",
            count=10,
            average=5.0,
            median=4.5,
            win_rate=60.0,
        )

        assert metrics.total_gain is None


class TestBinningEngineTotalGainCalculation:
    """Tests for total_gain calculation in BinningEngine."""

    def test_calculate_bin_metrics_includes_total_gain(self) -> None:
        """Test that calculate_bin_metrics computes total_gain (sum of metric column)."""
        engine = BinningEngine()

        df = pd.DataFrame({
            "value": [10, 20, 30, 40, 50],
            "gain_pct": [5.0, -2.0, 10.0, 3.0, -1.0],  # Total: 15.0
        })

        bin_defs = [
            BinDefinition(operator="<", value1=25, label="Low"),
            BinDefinition(operator=">", value1=25, label="High"),
        ]

        assignments = engine.assign_bins(df, "value", bin_defs)
        metrics = engine.calculate_bin_metrics(df, assignments, "gain_pct")

        # Low bin: rows 0,1 -> gains 5.0, -2.0 -> total 3.0
        assert metrics["Low"].total_gain == 3.0

        # High bin: rows 2,3,4 -> gains 10.0, 3.0, -1.0 -> total 12.0
        assert metrics["High"].total_gain == 12.0

    def test_calculate_bin_metrics_total_gain_empty_bin(self) -> None:
        """Test that total_gain is 0.0 for empty bins."""
        engine = BinningEngine()

        df = pd.DataFrame({
            "value": [100, 200, 300],
            "gain_pct": [5.0, -2.0, 10.0],
        })

        bin_defs = [
            BinDefinition(operator="<", value1=50, label="Empty"),  # No matching rows
            BinDefinition(operator=">", value1=50, label="All"),
        ]

        assignments = engine.assign_bins(df, "value", bin_defs)
        metrics = engine.calculate_bin_metrics(df, assignments, "gain_pct")

        # All values are in "All" bin
        assert metrics["All"].total_gain == 13.0  # 5.0 + (-2.0) + 10.0

    def test_calculate_bin_metrics_total_gain_with_nan_values(self) -> None:
        """Test that total_gain handles NaN values correctly (excludes them)."""
        engine = BinningEngine()

        df = pd.DataFrame({
            "value": [10, 20, 30, 40],
            "gain_pct": [5.0, None, 10.0, 3.0],  # NaN in position 1
        })

        bin_defs = [
            BinDefinition(operator="<", value1=25, label="Low"),
            BinDefinition(operator=">", value1=25, label="High"),
        ]

        assignments = engine.assign_bins(df, "value", bin_defs)
        metrics = engine.calculate_bin_metrics(df, assignments, "gain_pct")

        # Low bin: rows 0,1 -> gains 5.0, NaN -> total 5.0 (NaN excluded from sum)
        assert metrics["Low"].total_gain == 5.0

        # High bin: rows 2,3 -> gains 10.0, 3.0 -> total 13.0
        assert metrics["High"].total_gain == 13.0


class TestBinningEngineAssignBins:
    """Tests for bin assignment functionality."""

    def test_assign_bins_less_than(self) -> None:
        """Test less than operator assigns correctly."""
        engine = BinningEngine()

        df = pd.DataFrame({"value": [5, 10, 15, 20]})
        bin_defs = [BinDefinition(operator="<", value1=12, label="Low")]

        result = engine.assign_bins(df, "value", bin_defs)

        assert result.iloc[0] == "Low"
        assert result.iloc[1] == "Low"
        assert result.iloc[2] == engine.UNCATEGORIZED
        assert result.iloc[3] == engine.UNCATEGORIZED

    def test_assign_bins_greater_than(self) -> None:
        """Test greater than operator assigns correctly."""
        engine = BinningEngine()

        df = pd.DataFrame({"value": [5, 10, 15, 20]})
        bin_defs = [BinDefinition(operator=">", value1=12, label="High")]

        result = engine.assign_bins(df, "value", bin_defs)

        assert result.iloc[0] == engine.UNCATEGORIZED
        assert result.iloc[1] == engine.UNCATEGORIZED
        assert result.iloc[2] == "High"
        assert result.iloc[3] == "High"

    def test_assign_bins_range(self) -> None:
        """Test range operator assigns correctly."""
        engine = BinningEngine()

        df = pd.DataFrame({"value": [5, 10, 15, 20]})
        bin_defs = [BinDefinition(operator="range", value1=8, value2=17, label="Mid")]

        result = engine.assign_bins(df, "value", bin_defs)

        assert result.iloc[0] == engine.UNCATEGORIZED
        assert result.iloc[1] == "Mid"
        assert result.iloc[2] == "Mid"
        assert result.iloc[3] == engine.UNCATEGORIZED

    def test_assign_bins_nulls(self) -> None:
        """Test nulls operator assigns correctly."""
        engine = BinningEngine()

        df = pd.DataFrame({"value": [5, None, 15, None]})
        bin_defs = [BinDefinition(operator="nulls", label="Missing")]

        result = engine.assign_bins(df, "value", bin_defs)

        assert result.iloc[0] == engine.UNCATEGORIZED
        assert result.iloc[1] == "Missing"
        assert result.iloc[2] == engine.UNCATEGORIZED
        assert result.iloc[3] == "Missing"

    def test_assign_bins_first_match_wins(self) -> None:
        """Test that first matching bin definition wins."""
        engine = BinningEngine()

        df = pd.DataFrame({"value": [5, 10, 15, 20]})
        bin_defs = [
            BinDefinition(operator="<", value1=12, label="First"),
            BinDefinition(operator="<", value1=18, label="Second"),
        ]

        result = engine.assign_bins(df, "value", bin_defs)

        # Value 5 and 10 match both, but first should win
        assert result.iloc[0] == "First"
        assert result.iloc[1] == "First"
        # Value 15 only matches second
        assert result.iloc[2] == "Second"
        # Value 20 matches neither
        assert result.iloc[3] == engine.UNCATEGORIZED


class TestBinningEngineCalculateMetrics:
    """Tests for metric calculation functionality."""

    def test_calculate_metrics_average(self) -> None:
        """Test average calculation."""
        engine = BinningEngine()

        df = pd.DataFrame({
            "value": [10, 20, 30],
            "gain_pct": [2.0, 4.0, 6.0],
        })
        bin_defs = [BinDefinition(operator=">", value1=5, label="All")]

        assignments = engine.assign_bins(df, "value", bin_defs)
        metrics = engine.calculate_bin_metrics(df, assignments, "gain_pct")

        assert metrics["All"].average == 4.0  # (2 + 4 + 6) / 3

    def test_calculate_metrics_median(self) -> None:
        """Test median calculation."""
        engine = BinningEngine()

        df = pd.DataFrame({
            "value": [10, 20, 30],
            "gain_pct": [1.0, 5.0, 9.0],
        })
        bin_defs = [BinDefinition(operator=">", value1=5, label="All")]

        assignments = engine.assign_bins(df, "value", bin_defs)
        metrics = engine.calculate_bin_metrics(df, assignments, "gain_pct")

        assert metrics["All"].median == 5.0

    def test_calculate_metrics_win_rate(self) -> None:
        """Test win rate calculation (percentage of positive values)."""
        engine = BinningEngine()

        df = pd.DataFrame({
            "value": [10, 20, 30, 40, 50],
            "gain_pct": [1.0, -1.0, 2.0, -2.0, 3.0],  # 3 positive, 2 negative
        })
        bin_defs = [BinDefinition(operator=">", value1=5, label="All")]

        assignments = engine.assign_bins(df, "value", bin_defs)
        metrics = engine.calculate_bin_metrics(df, assignments, "gain_pct")

        assert metrics["All"].win_rate == 60.0  # 3/5 * 100

    def test_calculate_metrics_count(self) -> None:
        """Test count calculation."""
        engine = BinningEngine()

        df = pd.DataFrame({
            "value": [10, 20, 30, 40],
            "gain_pct": [1.0, 2.0, 3.0, 4.0],
        })
        bin_defs = [
            BinDefinition(operator="<", value1=25, label="Low"),
            BinDefinition(operator=">", value1=25, label="High"),
        ]

        assignments = engine.assign_bins(df, "value", bin_defs)
        metrics = engine.calculate_bin_metrics(df, assignments, "gain_pct")

        assert metrics["Low"].count == 2
        assert metrics["High"].count == 2
