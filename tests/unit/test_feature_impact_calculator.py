# tests/unit/test_feature_impact_calculator.py
"""Tests for feature impact calculator."""

import numpy as np
import pandas as pd
import pytest

from src.core.feature_impact_calculator import (
    FeatureImpactCalculator,
    FeatureImpactResult,
)


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


class TestFeatureImpactCalculator:
    """Tests for FeatureImpactCalculator."""

    @pytest.fixture
    def sample_df(self) -> pd.DataFrame:
        """Create sample trade data with clear feature-outcome relationship."""
        np.random.seed(42)
        n = 100
        # Feature where higher values correlate with wins
        feature_vals = np.random.uniform(0, 10, n)
        # Trades with feature > 5 have 80% win rate, below have 40% win rate
        gains = []
        for f in feature_vals:
            if f > 5:
                gains.append(np.random.choice([0.05, -0.02], p=[0.8, 0.2]))
            else:
                gains.append(np.random.choice([0.05, -0.02], p=[0.4, 0.6]))
        return pd.DataFrame({
            "feature_a": feature_vals,
            "gain_pct": gains,
        })

    def test_calculate_single_feature(self, sample_df: pd.DataFrame):
        """Test calculating impact for a single feature."""
        calculator = FeatureImpactCalculator()
        result = calculator.calculate_single_feature(
            df=sample_df,
            feature_col="feature_a",
            gain_col="gain_pct",
        )
        assert isinstance(result, FeatureImpactResult)
        assert result.feature_name == "feature_a"
        # Threshold should be around 5 (where win rate changes)
        assert 4.0 < result.optimal_threshold < 6.0
        # Win rate lift should be positive (above is better)
        assert result.win_rate_lift > 0
        assert result.threshold_direction == "above"

    def test_calculate_single_feature_negative_correlation(self):
        """Test feature where lower values are better."""
        np.random.seed(42)
        n = 100
        feature_vals = np.random.uniform(0, 10, n)
        # Lower feature values = higher win rate
        gains = []
        for f in feature_vals:
            if f < 5:
                gains.append(np.random.choice([0.05, -0.02], p=[0.8, 0.2]))
            else:
                gains.append(np.random.choice([0.05, -0.02], p=[0.4, 0.6]))
        df = pd.DataFrame({"feature_b": feature_vals, "gain_pct": gains})

        calculator = FeatureImpactCalculator()
        result = calculator.calculate_single_feature(
            df=df, feature_col="feature_b", gain_col="gain_pct"
        )
        assert result.threshold_direction == "below"
        assert result.win_rate_lift > 0


class TestFeatureImpactCalculatorMultiFeature:
    """Tests for multi-feature analysis."""

    @pytest.fixture
    def multi_feature_df(self) -> pd.DataFrame:
        """Create sample data with multiple features."""
        np.random.seed(42)
        n = 200
        return pd.DataFrame({
            "good_feature": np.random.uniform(0, 10, n),
            "weak_feature": np.random.uniform(0, 10, n),
            "no_signal": np.random.uniform(0, 10, n),
            "gain_pct": np.random.choice([0.05, -0.02], n, p=[0.6, 0.4]),
            "ticker": ["AAPL"] * n,  # Non-numeric, should be excluded
            "date": pd.date_range("2024-01-01", periods=n),  # Should be excluded
        })

    def test_calculate_all_features(self, multi_feature_df: pd.DataFrame):
        """Test analyzing all numeric features at once."""
        calculator = FeatureImpactCalculator()
        results = calculator.calculate_all_features(
            df=multi_feature_df,
            gain_col="gain_pct",
            excluded_cols=["ticker", "date", "gain_pct"],
        )
        assert len(results) == 3  # good_feature, weak_feature, no_signal
        assert all(isinstance(r, FeatureImpactResult) for r in results)
        feature_names = [r.feature_name for r in results]
        assert "good_feature" in feature_names
        assert "ticker" not in feature_names
        assert "date" not in feature_names

    def test_calculate_impact_scores(self, multi_feature_df: pd.DataFrame):
        """Test composite impact score calculation."""
        calculator = FeatureImpactCalculator()
        results = calculator.calculate_all_features(
            df=multi_feature_df,
            gain_col="gain_pct",
            excluded_cols=["ticker", "date", "gain_pct"],
        )
        scores = calculator.calculate_impact_scores(results)
        assert len(scores) == len(results)
        # Scores should be between 0 and 1
        assert all(0 <= s <= 1 for s in scores.values())

    def test_results_sorted_by_impact_score(self, multi_feature_df: pd.DataFrame):
        """Test that results can be sorted by impact score."""
        calculator = FeatureImpactCalculator()
        results = calculator.calculate_all_features(
            df=multi_feature_df,
            gain_col="gain_pct",
            excluded_cols=["ticker", "date", "gain_pct"],
        )
        scores = calculator.calculate_impact_scores(results)
        sorted_results = sorted(
            results, key=lambda r: scores[r.feature_name], reverse=True
        )
        # First result should have highest score
        first_score = scores[sorted_results[0].feature_name]
        last_score = scores[sorted_results[-1].feature_name]
        assert first_score >= last_score
