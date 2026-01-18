# tests/unit/test_feature_analyzer.py
"""Tests for feature analyzer module."""

import numpy as np
import pandas as pd

from src.core.feature_analyzer import (
    FeatureAnalysisResult,
    FeatureAnalyzerConfig,
    FeatureAnalyzerResults,
    FeatureRangeResult,
    RangeClassification,
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


class TestMutualInformation:
    """Test mutual information calculation."""

    def test_perfect_correlation_high_mi(self):
        """Perfectly correlated data should have high MI."""
        from src.core.feature_analyzer import calculate_mutual_information

        # Feature perfectly predicts gain sign
        feature = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10] * 10)
        gains = feature * 0.01  # Linear relationship

        mi = calculate_mutual_information(feature, gains)
        assert mi > 0.5  # High MI expected

    def test_random_data_low_mi(self):
        """Random uncorrelated data should have low MI."""
        from src.core.feature_analyzer import calculate_mutual_information

        np.random.seed(42)
        feature = np.random.randn(200)
        gains = np.random.randn(200)  # Independent

        mi = calculate_mutual_information(feature, gains)
        assert mi < 0.2  # Low MI expected

    def test_nonlinear_relationship_detected(self):
        """MI should detect non-linear relationships."""
        from src.core.feature_analyzer import calculate_mutual_information

        # U-shaped relationship: gains high at extremes
        feature = np.linspace(-5, 5, 200)
        gains = feature**2 * 0.01  # Quadratic - low correlation but high MI

        mi = calculate_mutual_information(feature, gains)
        assert mi > 0.3  # Should detect the relationship


class TestRankCorrelation:
    """Test rank correlation calculation."""

    def test_perfect_positive_correlation(self):
        """Perfectly correlated data should have correlation ~1."""
        from src.core.feature_analyzer import calculate_rank_correlation

        feature = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        gains = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])

        corr = calculate_rank_correlation(feature, gains)
        assert corr > 0.99

    def test_perfect_negative_correlation(self):
        """Inversely correlated data should have correlation ~-1."""
        from src.core.feature_analyzer import calculate_rank_correlation

        feature = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        gains = np.array([1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1])

        corr = calculate_rank_correlation(feature, gains)
        assert corr < -0.99

    def test_random_data_low_correlation(self):
        """Random data should have correlation near 0."""
        from src.core.feature_analyzer import calculate_rank_correlation

        np.random.seed(42)
        feature = np.random.randn(200)
        gains = np.random.randn(200)

        corr = calculate_rank_correlation(feature, gains)
        assert abs(corr) < 0.2


class TestConditionalVariance:
    """Test conditional mean variance calculation."""

    def test_feature_affects_mean_high_variance(self):
        """When feature affects mean gain, variance should be high."""
        from src.core.feature_analyzer import calculate_conditional_variance

        # Low feature values -> low gains, high feature values -> high gains
        feature = np.concatenate([np.ones(50) * 1, np.ones(50) * 10])
        gains = np.concatenate([np.ones(50) * -0.02, np.ones(50) * 0.05])

        variance = calculate_conditional_variance(feature, gains)
        assert variance > 0.001  # Should be substantial

    def test_feature_no_effect_low_variance(self):
        """When feature doesn't affect mean, variance should be low."""
        from src.core.feature_analyzer import calculate_conditional_variance

        np.random.seed(42)
        feature = np.random.randn(200)
        gains = np.random.randn(200) * 0.01  # Random, no relationship

        variance = calculate_conditional_variance(feature, gains)
        assert variance < 0.0001  # Should be small


class TestImpactScore:
    """Test combined impact score calculation."""

    def test_high_all_metrics_high_score(self):
        """High MI, correlation, and variance should give high score."""
        from src.core.feature_analyzer import calculate_impact_score

        score = calculate_impact_score(
            mutual_info=0.8,
            rank_corr=0.7,
            cond_variance=0.005,
            baseline_variance=0.001,
        )
        assert score > 70

    def test_low_all_metrics_low_score(self):
        """Low metrics should give low score."""
        from src.core.feature_analyzer import calculate_impact_score

        score = calculate_impact_score(
            mutual_info=0.05,
            rank_corr=0.05,
            cond_variance=0.0001,
            baseline_variance=0.001,
        )
        assert score < 30

    def test_score_in_valid_range(self):
        """Score should always be 0-100."""
        from src.core.feature_analyzer import calculate_impact_score

        for _ in range(100):
            mi = np.random.random()
            corr = np.random.random() * 2 - 1
            var = np.random.random() * 0.01
            base_var = np.random.random() * 0.01 + 0.001

            score = calculate_impact_score(mi, corr, var, base_var)
            assert 0 <= score <= 100


class TestOptimalBinning:
    """Test optimal binning algorithm."""

    def test_respects_max_bins(self):
        """Should not create more bins than max_bins."""
        from src.core.feature_analyzer import find_optimal_bins

        np.random.seed(42)
        feature = np.random.randn(500)
        gains = np.random.randn(500)

        bins = find_optimal_bins(feature, gains, max_bins=3, min_bin_size=30)
        assert len(bins) <= 3

    def test_respects_min_bin_size(self):
        """Each bin should have at least min_bin_size trades."""
        from src.core.feature_analyzer import find_optimal_bins

        np.random.seed(42)
        feature = np.random.randn(200)
        gains = np.random.randn(200)

        bins = find_optimal_bins(feature, gains, max_bins=5, min_bin_size=30)

        for bin_min, bin_max in bins:
            count = ((feature >= bin_min) & (feature < bin_max)).sum()
            # Last bin includes upper edge
            if bin_max == bins[-1][1]:
                count = ((feature >= bin_min) & (feature <= bin_max)).sum()
            assert count >= 30 or len(bins) == 1  # Single bin if can't split

    def test_bins_cover_all_data(self):
        """Bins should cover entire feature range."""
        from src.core.feature_analyzer import find_optimal_bins

        np.random.seed(42)
        feature = np.random.randn(300)
        gains = np.random.randn(300)

        bins = find_optimal_bins(feature, gains, max_bins=4, min_bin_size=30)

        # First bin starts at or before min
        assert bins[0][0] <= feature.min()
        # Last bin ends at or after max
        assert bins[-1][1] >= feature.max()

    def test_bins_are_contiguous(self):
        """Bins should be contiguous (no gaps)."""
        from src.core.feature_analyzer import find_optimal_bins

        np.random.seed(42)
        feature = np.random.randn(300)
        gains = np.random.randn(300)

        bins = find_optimal_bins(feature, gains, max_bins=4, min_bin_size=30)

        for i in range(len(bins) - 1):
            assert bins[i][1] == bins[i + 1][0]  # End of one = start of next


class TestBinAnalysis:
    """Test bin analysis and classification."""

    def test_favorable_classification(self):
        """Bin with significantly better EV should be FAVORABLE."""
        from src.core.feature_analyzer import (
            FeatureAnalyzerConfig,
            RangeClassification,
            analyze_bin,
        )

        config = FeatureAnalyzerConfig()
        # All gains are positive and high
        gains = np.array([0.05, 0.04, 0.06, 0.03, 0.05] * 20)
        baseline_ev = 0.01  # Low baseline

        result, classification = analyze_bin(gains, baseline_ev, config)

        assert classification == RangeClassification.FAVORABLE
        assert result["ev"] > baseline_ev

    def test_unfavorable_classification(self):
        """Bin with significantly worse EV should be UNFAVORABLE."""
        from src.core.feature_analyzer import (
            FeatureAnalyzerConfig,
            RangeClassification,
            analyze_bin,
        )

        config = FeatureAnalyzerConfig()
        # All gains are negative
        gains = np.array([-0.03, -0.04, -0.02, -0.05, -0.03] * 20)
        baseline_ev = 0.01  # Positive baseline

        result, classification = analyze_bin(gains, baseline_ev, config)

        assert classification == RangeClassification.UNFAVORABLE
        assert result["ev"] < baseline_ev

    def test_insufficient_classification(self):
        """Bin with too few trades should be INSUFFICIENT."""
        from src.core.feature_analyzer import (
            FeatureAnalyzerConfig,
            RangeClassification,
            analyze_bin,
        )

        config = FeatureAnalyzerConfig(min_bin_size=30)
        gains = np.array([0.05, 0.04, 0.06])  # Only 3 trades
        baseline_ev = 0.01

        result, classification = analyze_bin(gains, baseline_ev, config)

        assert classification == RangeClassification.INSUFFICIENT

    def test_neutral_classification(self):
        """Bin similar to baseline should be NEUTRAL."""
        from src.core.feature_analyzer import (
            FeatureAnalyzerConfig,
            RangeClassification,
            analyze_bin,
        )

        config = FeatureAnalyzerConfig()
        np.random.seed(42)
        # Gains similar to baseline
        gains = np.random.randn(100) * 0.02 + 0.01
        baseline_ev = 0.01

        result, classification = analyze_bin(gains, baseline_ev, config)

        assert classification == RangeClassification.NEUTRAL

    def test_confidence_interval_calculated(self):
        """Should calculate confidence intervals."""
        from src.core.feature_analyzer import FeatureAnalyzerConfig, analyze_bin

        config = FeatureAnalyzerConfig(bootstrap_iterations=500)
        gains = np.array([0.05, 0.04, 0.06, 0.03, 0.05] * 20)
        baseline_ev = 0.01

        result, _ = analyze_bin(gains, baseline_ev, config)

        assert result["confidence_lower"] is not None
        assert result["confidence_upper"] is not None
        assert result["confidence_lower"] < result["ev"] < result["confidence_upper"]


class TestFeatureAnalyzer:
    """Test main FeatureAnalyzer class."""

    def test_excludes_configured_columns(self):
        """Should exclude columns in config.exclude_columns."""
        from src.core.feature_analyzer import FeatureAnalyzer, FeatureAnalyzerConfig

        df = pd.DataFrame(
            {
                "feature1": np.random.randn(100),
                "feature2": np.random.randn(100),
                "gain_pct": np.random.randn(100) * 0.02,
                "mae_pct": np.random.randn(100) * 0.01,
            }
        )

        config = FeatureAnalyzerConfig(exclude_columns={"gain_pct", "mae_pct"})
        analyzer = FeatureAnalyzer(config)

        columns = analyzer.get_analyzable_columns(df)

        assert "feature1" in columns
        assert "feature2" in columns
        assert "gain_pct" not in columns
        assert "mae_pct" not in columns

    def test_excludes_non_numeric_columns(self):
        """Should exclude non-numeric columns."""
        from src.core.feature_analyzer import FeatureAnalyzer, FeatureAnalyzerConfig

        df = pd.DataFrame(
            {
                "feature1": np.random.randn(100),
                "ticker": ["AAPL"] * 100,
                "date": pd.date_range("2024-01-01", periods=100),
            }
        )

        config = FeatureAnalyzerConfig()
        analyzer = FeatureAnalyzer(config)

        columns = analyzer.get_analyzable_columns(df)

        assert "feature1" in columns
        assert "ticker" not in columns
        assert "date" not in columns

    def test_run_returns_results(self):
        """run() should return FeatureAnalyzerResults."""
        from src.core.feature_analyzer import (
            FeatureAnalyzer,
            FeatureAnalyzerConfig,
        )

        np.random.seed(42)
        df = pd.DataFrame(
            {
                "feature1": np.random.randn(200),
                "feature2": np.random.randn(200),
                "gain_pct": np.random.randn(200) * 0.02,
            }
        )

        config = FeatureAnalyzerConfig(
            exclude_columns={"gain_pct"},
            top_n_features=2,
            bootstrap_iterations=100,  # Faster for test
        )
        analyzer = FeatureAnalyzer(config)

        results = analyzer.run(df, gain_col="gain_pct")

        assert isinstance(results, FeatureAnalyzerResults)
        assert results.baseline_trade_count == 200
        assert len(results.features) <= 2

    def test_run_with_impactful_feature(self):
        """Feature with strong relationship should rank higher."""
        from src.core.feature_analyzer import FeatureAnalyzer, FeatureAnalyzerConfig

        np.random.seed(42)
        n = 300

        # Feature that predicts gains
        important_feature = np.random.randn(n)
        gains = important_feature * 0.02 + np.random.randn(n) * 0.005

        # Random feature
        random_feature = np.random.randn(n)

        df = pd.DataFrame(
            {
                "important": important_feature,
                "random": random_feature,
                "gain_pct": gains,
            }
        )

        config = FeatureAnalyzerConfig(
            exclude_columns={"gain_pct"},
            top_n_features=2,
            bootstrap_iterations=100,
        )
        analyzer = FeatureAnalyzer(config)

        results = analyzer.run(df, gain_col="gain_pct")

        # Important feature should rank first
        assert results.features[0].feature_name == "important"
        assert results.features[0].impact_score > results.features[1].impact_score
