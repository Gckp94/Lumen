"""Unit tests for BinningEngine class."""

import time

import numpy as np
import pandas as pd
import pytest

from src.core.binning_engine import BinningEngine
from src.core.models import BinConfig, BinDefinition, BinMetrics


class TestBinAssignmentLessThan:
    """Tests for < operator bin assignment."""

    def test_less_than_assigns_correctly(self) -> None:
        """< operator assigns values below threshold."""
        engine = BinningEngine()
        df = pd.DataFrame({"value": [5, 10, 15, 20, 25]})
        bins = [BinDefinition(operator="<", value1=15, label="Low")]

        result = engine.assign_bins(df, "value", bins)

        assert result.iloc[0] == "Low"  # 5 < 15
        assert result.iloc[1] == "Low"  # 10 < 15
        assert result.iloc[2] == "Uncategorized"  # 15 not < 15
        assert result.iloc[3] == "Uncategorized"  # 20 not < 15
        assert result.iloc[4] == "Uncategorized"  # 25 not < 15

    def test_less_than_boundary_value(self) -> None:
        """< operator excludes exact boundary value."""
        engine = BinningEngine()
        df = pd.DataFrame({"value": [14.99, 15.0, 15.01]})
        bins = [BinDefinition(operator="<", value1=15, label="Low")]

        result = engine.assign_bins(df, "value", bins)

        assert result.iloc[0] == "Low"  # 14.99 < 15
        assert result.iloc[1] == "Uncategorized"  # 15.0 not < 15
        assert result.iloc[2] == "Uncategorized"  # 15.01 not < 15

    def test_less_than_with_negative_values(self) -> None:
        """< operator works with negative values."""
        engine = BinningEngine()
        df = pd.DataFrame({"value": [-10, -5, 0, 5]})
        bins = [BinDefinition(operator="<", value1=0, label="Negative")]

        result = engine.assign_bins(df, "value", bins)

        assert result.iloc[0] == "Negative"  # -10 < 0
        assert result.iloc[1] == "Negative"  # -5 < 0
        assert result.iloc[2] == "Uncategorized"  # 0 not < 0
        assert result.iloc[3] == "Uncategorized"  # 5 not < 0


class TestBinAssignmentGreaterThan:
    """Tests for > operator bin assignment."""

    def test_greater_than_assigns_correctly(self) -> None:
        """> operator assigns values above threshold."""
        engine = BinningEngine()
        df = pd.DataFrame({"value": [5, 10, 15, 20, 25]})
        bins = [BinDefinition(operator=">", value1=15, label="High")]

        result = engine.assign_bins(df, "value", bins)

        assert result.iloc[0] == "Uncategorized"  # 5 not > 15
        assert result.iloc[1] == "Uncategorized"  # 10 not > 15
        assert result.iloc[2] == "Uncategorized"  # 15 not > 15
        assert result.iloc[3] == "High"  # 20 > 15
        assert result.iloc[4] == "High"  # 25 > 15

    def test_greater_than_boundary_value(self) -> None:
        """> operator excludes exact boundary value."""
        engine = BinningEngine()
        df = pd.DataFrame({"value": [14.99, 15.0, 15.01]})
        bins = [BinDefinition(operator=">", value1=15, label="High")]

        result = engine.assign_bins(df, "value", bins)

        assert result.iloc[0] == "Uncategorized"  # 14.99 not > 15
        assert result.iloc[1] == "Uncategorized"  # 15.0 not > 15
        assert result.iloc[2] == "High"  # 15.01 > 15


class TestBinAssignmentRange:
    """Tests for range operator bin assignment."""

    def test_range_assigns_correctly(self) -> None:
        """range operator assigns values within range (inclusive)."""
        engine = BinningEngine()
        df = pd.DataFrame({"value": [5, 10, 15, 20, 25]})
        bins = [BinDefinition(operator="range", value1=10, value2=20, label="Mid")]

        result = engine.assign_bins(df, "value", bins)

        assert result.iloc[0] == "Uncategorized"  # 5 not in [10, 20]
        assert result.iloc[1] == "Mid"  # 10 in [10, 20]
        assert result.iloc[2] == "Mid"  # 15 in [10, 20]
        assert result.iloc[3] == "Mid"  # 20 in [10, 20]
        assert result.iloc[4] == "Uncategorized"  # 25 not in [10, 20]

    def test_range_boundary_inclusive(self) -> None:
        """range operator includes both boundary values."""
        engine = BinningEngine()
        df = pd.DataFrame({"value": [9.99, 10.0, 20.0, 20.01]})
        bins = [BinDefinition(operator="range", value1=10, value2=20, label="Mid")]

        result = engine.assign_bins(df, "value", bins)

        assert result.iloc[0] == "Uncategorized"  # 9.99 < 10
        assert result.iloc[1] == "Mid"  # 10.0 == 10 (inclusive)
        assert result.iloc[2] == "Mid"  # 20.0 == 20 (inclusive)
        assert result.iloc[3] == "Uncategorized"  # 20.01 > 20


class TestBinAssignmentNulls:
    """Tests for nulls operator bin assignment."""

    def test_nulls_assigns_nan_values(self) -> None:
        """nulls operator assigns NaN values."""
        engine = BinningEngine()
        df = pd.DataFrame({"value": [1.0, np.nan, 3.0, None, 5.0]})
        bins = [BinDefinition(operator="nulls", label="Nulls")]

        result = engine.assign_bins(df, "value", bins)

        assert result.iloc[0] == "Uncategorized"  # 1.0 not null
        assert result.iloc[1] == "Nulls"  # NaN is null
        assert result.iloc[2] == "Uncategorized"  # 3.0 not null
        assert result.iloc[3] == "Nulls"  # None is null
        assert result.iloc[4] == "Uncategorized"  # 5.0 not null

    def test_nulls_with_all_null_column(self) -> None:
        """nulls operator handles all-null column."""
        engine = BinningEngine()
        df = pd.DataFrame({"value": [np.nan, np.nan, np.nan]})
        bins = [BinDefinition(operator="nulls", label="Nulls")]

        result = engine.assign_bins(df, "value", bins)

        assert all(result == "Nulls")


class TestBinAssignmentFirstMatchWins:
    """Tests for first-match-wins behavior."""

    def test_first_match_wins_overlapping_bins(self) -> None:
        """First matching bin definition wins on overlap."""
        engine = BinningEngine()
        df = pd.DataFrame({"value": [5, 15, 25]})
        bins = [
            BinDefinition(operator="<", value1=20, label="First"),
            BinDefinition(operator="<", value1=30, label="Second"),
        ]

        result = engine.assign_bins(df, "value", bins)

        # 5 matches both < 20 and < 30, but First should win
        assert result.iloc[0] == "First"
        assert result.iloc[1] == "First"  # 15 < 20
        assert result.iloc[2] == "Second"  # 25 not < 20, but < 30

    def test_bin_order_preserved(self) -> None:
        """Bins are processed in definition order."""
        engine = BinningEngine()
        df = pd.DataFrame({"value": [5, 15, 25, 35]})
        bins = [
            BinDefinition(operator="<", value1=10, label="Low"),
            BinDefinition(operator="range", value1=10, value2=20, label="Mid"),
            BinDefinition(operator=">", value1=20, label="High"),
        ]

        result = engine.assign_bins(df, "value", bins)

        assert result.iloc[0] == "Low"  # 5 < 10
        assert result.iloc[1] == "Mid"  # 10 <= 15 <= 20
        assert result.iloc[2] == "High"  # 25 > 20
        assert result.iloc[3] == "High"  # 35 > 20


class TestBinAssignmentEdgeCases:
    """Tests for edge cases in bin assignment."""

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame returns empty Series."""
        engine = BinningEngine()
        df = pd.DataFrame({"value": []})
        bins = [BinDefinition(operator="<", value1=10, label="Low")]

        result = engine.assign_bins(df, "value", bins)

        assert len(result) == 0

    def test_no_bins_defined(self) -> None:
        """No bins returns empty Series."""
        engine = BinningEngine()
        df = pd.DataFrame({"value": [1, 2, 3]})
        bins: list[BinDefinition] = []

        result = engine.assign_bins(df, "value", bins)

        assert len(result) == 0

    def test_no_matching_bins(self) -> None:
        """All rows assigned to Uncategorized when no bins match."""
        engine = BinningEngine()
        df = pd.DataFrame({"value": [50, 60, 70]})
        bins = [BinDefinition(operator="<", value1=10, label="Low")]

        result = engine.assign_bins(df, "value", bins)

        assert all(result == "Uncategorized")

    def test_auto_generated_labels(self) -> None:
        """Labels are auto-generated when not provided."""
        engine = BinningEngine()
        df = pd.DataFrame({"value": [5, 15, 25]})
        bins = [
            BinDefinition(operator="<", value1=10),
            BinDefinition(operator=">", value1=20),
            BinDefinition(operator="range", value1=10, value2=20),
        ]

        result = engine.assign_bins(df, "value", bins)

        assert result.iloc[0] == "< 10"
        assert result.iloc[1] == "10 - 20"
        assert result.iloc[2] == "> 20"


class TestBinMetricsCalculation:
    """Tests for bin metrics calculation."""

    def test_metrics_calculation_accuracy(self) -> None:
        """Metrics are calculated correctly for each bin."""
        engine = BinningEngine()
        df = pd.DataFrame({
            "value": [5, 10, 15, 20, 25],
            "gain_pct": [1.0, 2.0, -1.0, 3.0, -2.0],
        })
        bins = [
            BinDefinition(operator="<", value1=15, label="Low"),
            BinDefinition(operator=">=", value1=15, label="High"),  # Will be uncategorized
        ]
        bin_labels = engine.assign_bins(df, "value", bins)

        metrics = engine.calculate_bin_metrics(df, bin_labels, "gain_pct")

        # Low bin: values 5, 10 with gains 1.0, 2.0
        assert "Low" in metrics
        assert metrics["Low"].count == 2
        assert metrics["Low"].average == 1.5  # (1.0 + 2.0) / 2
        assert metrics["Low"].median == 1.5
        assert metrics["Low"].win_rate == 100.0  # Both positive

    def test_win_rate_calculation(self) -> None:
        """Win rate correctly counts positive values."""
        engine = BinningEngine()
        df = pd.DataFrame({
            "value": [1, 2, 3, 4],
            "gain_pct": [1.0, -1.0, 2.0, -2.0],
        })
        bin_labels = pd.Series(["All", "All", "All", "All"])

        metrics = engine.calculate_bin_metrics(df, bin_labels, "gain_pct")

        assert metrics["All"].win_rate == 50.0  # 2 wins out of 4

    def test_metrics_with_empty_bin(self) -> None:
        """Empty bins have None metrics."""
        engine = BinningEngine()
        df = pd.DataFrame({
            "value": [5, 10],
            "gain_pct": [1.0, 2.0],
        })
        bins = [BinDefinition(operator=">", value1=100, label="High")]
        bin_labels = engine.assign_bins(df, "value", bins)

        metrics = engine.calculate_bin_metrics(df, bin_labels, "gain_pct")

        # No rows match "High", only Uncategorized
        assert "High" not in metrics
        assert "Uncategorized" in metrics

    def test_metrics_with_nan_values(self) -> None:
        """NaN values in metric column are handled gracefully."""
        engine = BinningEngine()
        df = pd.DataFrame({
            "value": [1, 2, 3, 4],
            "gain_pct": [1.0, np.nan, 2.0, np.nan],
        })
        bin_labels = pd.Series(["All", "All", "All", "All"])

        metrics = engine.calculate_bin_metrics(df, bin_labels, "gain_pct")

        # Count includes all rows, but metrics calculated on valid values
        assert metrics["All"].count == 4
        assert metrics["All"].average == 1.5  # (1.0 + 2.0) / 2
        assert metrics["All"].win_rate == 100.0  # Both valid values positive

    def test_metrics_empty_dataframe(self) -> None:
        """Empty DataFrame returns empty metrics dict."""
        engine = BinningEngine()
        df = pd.DataFrame({"value": [], "gain_pct": []})
        bin_labels = pd.Series(dtype=str)

        metrics = engine.calculate_bin_metrics(df, bin_labels, "gain_pct")

        assert metrics == {}


class TestBinAssignmentPerformance:
    """Performance tests for bin assignment."""

    @pytest.mark.slow
    def test_bin_assignment_performance_100k_rows(self) -> None:
        """Bin assignment completes in < 250ms for 100k rows."""
        engine = BinningEngine()
        np.random.seed(42)
        df = pd.DataFrame({"value": np.random.randn(100_000)})
        bins = [
            BinDefinition(operator="<", value1=-1, label="Low"),
            BinDefinition(operator="range", value1=-1, value2=1, label="Mid"),
            BinDefinition(operator=">", value1=1, label="High"),
        ]

        start = time.perf_counter()
        engine.assign_bins(df, "value", bins)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.25, f"Took {elapsed:.3f}s, exceeds 250ms limit"

    @pytest.mark.slow
    def test_metrics_calculation_performance_100k_rows(self) -> None:
        """Metrics calculation completes in < 250ms for 100k rows."""
        engine = BinningEngine()
        np.random.seed(42)
        df = pd.DataFrame({
            "value": np.random.randn(100_000),
            "gain_pct": np.random.randn(100_000),
        })
        bins = [
            BinDefinition(operator="<", value1=-1, label="Low"),
            BinDefinition(operator="range", value1=-1, value2=1, label="Mid"),
            BinDefinition(operator=">", value1=1, label="High"),
        ]
        bin_labels = engine.assign_bins(df, "value", bins)

        start = time.perf_counter()
        engine.calculate_bin_metrics(df, bin_labels, "gain_pct")
        elapsed = time.perf_counter() - start

        assert elapsed < 0.25, f"Took {elapsed:.3f}s, exceeds 250ms limit"

    @pytest.mark.slow
    def test_combined_operation_performance_100k_rows(self) -> None:
        """Combined bin assignment + metrics completes in < 500ms for 100k rows."""
        engine = BinningEngine()
        np.random.seed(42)
        df = pd.DataFrame({
            "value": np.random.randn(100_000),
            "gain_pct": np.random.randn(100_000),
        })
        bins = [
            BinDefinition(operator="<", value1=-1, label="Low"),
            BinDefinition(operator="range", value1=-1, value2=1, label="Mid"),
            BinDefinition(operator=">", value1=1, label="High"),
            BinDefinition(operator="nulls", label="Nulls"),
        ]

        start = time.perf_counter()
        bin_labels = engine.assign_bins(df, "value", bins)
        engine.calculate_bin_metrics(df, bin_labels, "gain_pct")
        elapsed = time.perf_counter() - start

        assert elapsed < 0.5, f"Took {elapsed:.3f}s, exceeds 500ms limit"


class TestBinMetricsDataclass:
    """Tests for BinMetrics dataclass."""

    def test_bin_metrics_creation(self) -> None:
        """BinMetrics can be created with all fields."""
        metrics = BinMetrics(
            label="Test",
            count=100,
            average=1.5,
            median=1.2,
            win_rate=65.0,
        )

        assert metrics.label == "Test"
        assert metrics.count == 100
        assert metrics.average == 1.5
        assert metrics.median == 1.2
        assert metrics.win_rate == 65.0

    def test_bin_metrics_with_none_values(self) -> None:
        """BinMetrics can have None values for empty bins."""
        metrics = BinMetrics(
            label="Empty",
            count=0,
            average=None,
            median=None,
            win_rate=None,
        )

        assert metrics.count == 0
        assert metrics.average is None
        assert metrics.median is None
        assert metrics.win_rate is None



class TestBinConfigDataclass:
    """Tests for BinConfig dataclass serialization and validation."""

    def test_bin_config_to_dict(self) -> None:
        """to_dict produces JSON-serializable output."""
        import json

        bins = [BinDefinition(operator="<", value1=100, label="Low")]
        config = BinConfig(column="volume", bins=bins, metric_column="gain_pct")

        result = config.to_dict()

        assert result["column"] == "volume"
        assert len(result["bins"]) == 1
        assert result["bins"][0]["operator"] == "<"
        assert result["bins"][0]["value1"] == 100
        assert result["bins"][0]["label"] == "Low"
        assert result["metric_column"] == "gain_pct"
        # Verify JSON-serializable
        json.dumps(result)  # Should not raise

    def test_bin_config_from_dict(self) -> None:
        """from_dict correctly reconstructs BinConfig."""
        data = {
            "column": "volume",
            "bins": [{"operator": "<", "value1": 100, "label": "Low"}],
            "metric_column": "gain_pct",
        }

        config = BinConfig.from_dict(data)

        assert config.column == "volume"
        assert len(config.bins) == 1
        assert config.bins[0].operator == "<"
        assert config.bins[0].value1 == 100
        assert config.bins[0].label == "Low"
        assert config.metric_column == "gain_pct"

    def test_bin_config_validate_missing_column(self) -> None:
        """validate catches missing column."""
        bins = [BinDefinition(operator="<", value1=100)]
        config = BinConfig(column="", bins=bins, metric_column="gain_pct")

        errors = config.validate()

        assert any("column" in e.lower() for e in errors)

    def test_bin_config_validate_empty_bins(self) -> None:
        """validate catches empty bins list."""
        config = BinConfig(column="volume", bins=[], metric_column="gain_pct")

        errors = config.validate()

        assert any("bin" in e.lower() for e in errors)

    def test_bin_config_validate_invalid_metric(self) -> None:
        """validate catches invalid metric_column values."""
        bins = [BinDefinition(operator="<", value1=100)]
        config = BinConfig(column="volume", bins=bins, metric_column="invalid_metric")

        errors = config.validate()

        assert any("metric" in e.lower() for e in errors)

    def test_bin_config_roundtrip(self) -> None:
        """Round-trip serialization preserves data."""
        bins = [
            BinDefinition(operator="<", value1=100, label="Low"),
            BinDefinition(operator="range", value1=100, value2=1000, label="Mid"),
            BinDefinition(operator=">", value1=1000, label="High"),
            BinDefinition(operator="nulls", label="Missing"),
        ]
        original = BinConfig(column="volume", bins=bins, metric_column="adjusted_gain_pct")

        restored = BinConfig.from_dict(original.to_dict())

        assert restored.column == original.column
        assert len(restored.bins) == len(original.bins)
        assert restored.metric_column == original.metric_column
        for orig_bin, rest_bin in zip(original.bins, restored.bins, strict=True):
            assert orig_bin.operator == rest_bin.operator
            assert orig_bin.value1 == rest_bin.value1
            assert orig_bin.value2 == rest_bin.value2
            assert orig_bin.label == rest_bin.label

    def test_bin_config_default_metric_column(self) -> None:
        """from_dict uses default metric_column when not specified."""
        data = {
            "column": "volume",
            "bins": [{"operator": "<", "value1": 100}],
        }

        config = BinConfig.from_dict(data)

        assert config.metric_column == "adjusted_gain_pct"

    def test_bin_config_from_dict_missing_label(self) -> None:
        """from_dict handles missing label field gracefully."""
        data = {
            "column": "volume",
            "bins": [{"operator": "<", "value1": 100}],
            "metric_column": "gain_pct",
        }

        config = BinConfig.from_dict(data)

        assert config.bins[0].label == ""
