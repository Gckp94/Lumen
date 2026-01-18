# tests/integration/test_feature_insights.py
"""Integration tests for feature insights functionality."""

import numpy as np
import pandas as pd
import pytest

from src.core.feature_analyzer import (
    FeatureAnalyzer,
    FeatureAnalyzerConfig,
    RangeClassification,
)


class TestFeatureInsightsIntegration:
    """Integration tests for the complete feature analysis flow."""

    @pytest.fixture
    def sample_trading_data(self):
        """Generate realistic trading data with known patterns."""
        np.random.seed(42)
        n = 500

        # Create a feature that genuinely impacts gains
        time_minutes = np.random.uniform(0, 390, n)

        # Early trades (first 60 min) perform better
        gains = np.where(
            time_minutes < 60,
            np.random.normal(0.02, 0.03, n),  # Positive EV
            np.random.normal(-0.005, 0.03, n),  # Negative EV
        )

        return pd.DataFrame({
            "time_minutes": time_minutes,
            "random_feature": np.random.randn(n),
            "gain_pct": gains,
            "mae_pct": np.abs(np.random.randn(n) * 0.02),
        })

    def test_identifies_impactful_feature(self, sample_trading_data):
        """Should rank time_minutes higher than random_feature."""
        config = FeatureAnalyzerConfig(
            exclude_columns={"gain_pct", "mae_pct"},
            top_n_features=2,
            bootstrap_iterations=100,
        )

        analyzer = FeatureAnalyzer(config)
        results = analyzer.run(sample_trading_data, gain_col="gain_pct")

        # time_minutes should be more impactful
        assert results.features[0].feature_name == "time_minutes"
        assert results.features[0].impact_score > results.features[1].impact_score

    def test_identifies_favorable_range(self, sample_trading_data):
        """Should identify early morning as favorable."""
        config = FeatureAnalyzerConfig(
            exclude_columns={"gain_pct", "mae_pct"},
            top_n_features=1,
            bootstrap_iterations=100,
        )

        analyzer = FeatureAnalyzer(config)
        results = analyzer.run(sample_trading_data, gain_col="gain_pct")

        time_feature = results.features[0]

        # Should have at least one favorable range in early times
        favorable_ranges = [
            r for r in time_feature.ranges
            if r.classification == RangeClassification.FAVORABLE
        ]
        assert len(favorable_ranges) > 0

        # The favorable range should be in early morning
        for r in favorable_ranges:
            assert r.range_min < 100  # Early in the day
