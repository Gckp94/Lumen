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
        pnl_above=300.0,
        pnl_below=-100.0,
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
        pnl_above=15.0,
        pnl_below=-5.0,
        percentile_win_rates=[50.0] * 20,
    )

    calculator = FeatureImpactCalculator()
    scores = calculator.calculate_impact_scores([large_sample, small_sample])

    # Large sample should score higher due to sample size penalty on small
    assert scores["large_sample"] > scores["small_sample"]


def test_pnl_above_below_calculated():
    """Total PnL above and below threshold should be calculated."""
    import pandas as pd
    import numpy as np

    calculator = FeatureImpactCalculator()

    # Create test data with known PnL
    df = pd.DataFrame({
        "feature": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "gain_pct": [2.0, 1.5, -1.0, 3.0, -0.5, 2.5, -2.0, 1.0, -1.5, 4.0],
    })

    result = calculator.calculate_single_feature(df, "feature", "gain_pct")

    # Check that PnL fields exist and are reasonable
    assert hasattr(result, "pnl_above")
    assert hasattr(result, "pnl_below")
    assert result.pnl_above is not None
    assert result.pnl_below is not None
    # Total should equal sum of all gains
    total_pnl = df["gain_pct"].sum()
    assert abs((result.pnl_above + result.pnl_below) - total_pnl) < 0.01
