# tests/unit/test_feature_analyzer.py
"""Tests for feature analyzer module."""

import pytest
from src.core.feature_analyzer import (
    RangeClassification,
    FeatureRangeResult,
    FeatureAnalysisResult,
    FeatureAnalyzerConfig,
    FeatureAnalyzerResults,
)


class TestDataModels:
    """Test data model instantiation and defaults."""

    def test_range_classification_enum(self):
        """RangeClassification has expected values."""
        assert RangeClassification.FAVORABLE.value == "favorable"
        assert RangeClassification.NEUTRAL.value == "neutral"
        assert RangeClassification.UNFAVORABLE.value == "unfavorable"
        assert RangeClassification.INSUFFICIENT.value == "insufficient"

    def test_feature_analyzer_config_defaults(self):
        """FeatureAnalyzerConfig has sensible defaults."""
        config = FeatureAnalyzerConfig()
        assert config.min_unique_values == 5
        assert config.top_n_features == 10
        assert config.max_bins == 5
        assert config.min_bin_size == 30
        assert config.min_bin_pct == 5.0
        assert config.bootstrap_iterations == 1000
        assert config.confidence_level == 0.95
        assert config.exclude_columns == set()

    def test_feature_range_result_creation(self):
        """FeatureRangeResult can be created with all fields."""
        result = FeatureRangeResult(
            range_min=0.0,
            range_max=10.0,
            range_label="0.0 - 10.0",
            classification=RangeClassification.FAVORABLE,
            trade_count=50,
            ev=2.5,
            win_rate=60.0,
            total_pnl=125.0,
            confidence_lower=1.5,
            confidence_upper=3.5,
            p_value=0.02,
            viability_score=17.7,
        )
        assert result.trade_count == 50
        assert result.classification == RangeClassification.FAVORABLE

    def test_feature_analysis_result_creation(self):
        """FeatureAnalysisResult can be created."""
        result = FeatureAnalysisResult(
            feature_name="gap_percent",
            impact_score=72.5,
            mutual_information=0.45,
            rank_correlation=0.32,
            conditional_variance=0.0012,
            ranges=[],
            bootstrap_stability=0.85,
            time_consistency=None,
            warnings=[],
        )
        assert result.feature_name == "gap_percent"
        assert result.impact_score == 72.5
