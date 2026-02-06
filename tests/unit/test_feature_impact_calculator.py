# tests/unit/test_feature_impact_calculator.py
"""Tests for feature impact calculator."""

import pytest
from src.core.feature_impact_calculator import FeatureImpactResult


class TestFeatureImpactResult:
    """Tests for the FeatureImpactResult dataclass."""

    def test_feature_impact_result_creation(self):
        """Test creating a FeatureImpactResult with all fields."""
        result = FeatureImpactResult(
            feature_name="gap_pct",
            correlation=0.15,
            optimal_threshold=2.35,
            threshold_direction="above",
            win_rate_baseline=54.2,
            win_rate_above=66.5,
            win_rate_below=48.1,
            win_rate_lift=12.3,
            expectancy_baseline=0.32,
            expectancy_above=0.77,
            expectancy_below=0.15,
            expectancy_lift=0.45,
            trades_above=939,
            trades_below=1402,
            trades_total=2341,
            percentile_win_rates=[50.0, 52.0, 55.0, 60.0, 65.0],
        )
        assert result.feature_name == "gap_pct"
        assert result.correlation == 0.15
        assert result.win_rate_lift == 12.3
        assert result.expectancy_lift == 0.45
