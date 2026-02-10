"""Tests for FeatureImpactCalculator."""

import pytest

from src.core.feature_impact_calculator import FeatureImpactCalculator, FeatureImpactResult


def test_sample_size_penalty_reduces_small_sample_scores():
    """Features with fewer trades should have penalized scores."""
    # Two features with identical metrics except trade count
    large_sample = FeatureImpactResult(
        feature_name="large_sample",
        correlation=0.3,
        optimal_threshold=10.0,
        threshold_direction="above",
        win_rate_baseline=50.0,
        win_rate_above=70.0,
        win_rate_below=30.0,
        win_rate_lift=20.0,
        expectancy_baseline=0.5,
        expectancy_above=1.5,
        expectancy_below=-0.5,
        expectancy_lift=1.0,
        trades_above=200,  # Large sample
        trades_below=200,
        trades_total=400,
        percentile_win_rates=[50.0] * 20,
    )

    small_sample = FeatureImpactResult(
        feature_name="small_sample",
        correlation=0.3,
        optimal_threshold=10.0,
        threshold_direction="above",
        win_rate_baseline=50.0,
        win_rate_above=70.0,
        win_rate_below=30.0,
        win_rate_lift=20.0,
        expectancy_baseline=0.5,
        expectancy_above=1.5,
        expectancy_below=-0.5,
        expectancy_lift=1.0,
        trades_above=10,  # Small sample
        trades_below=10,
        trades_total=20,
        percentile_win_rates=[50.0] * 20,
    )

    calculator = FeatureImpactCalculator()
    scores = calculator.calculate_impact_scores([large_sample, small_sample])

    # Large sample should score higher due to sample size penalty on small
    assert scores["large_sample"] > scores["small_sample"]
