# src/core/feature_analyzer.py
"""Feature analysis engine for identifying impactful features and ranges.

This module implements a multi-criteria approach that:
1. Ranks features by their relationship to gains (not predictive power)
2. Identifies favorable/unfavorable ranges with practical constraints
3. Validates findings through bootstrap resampling
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy import stats


class RangeClassification(Enum):
    """Classification of a feature range relative to baseline."""

    FAVORABLE = "favorable"  # Significantly better than baseline
    NEUTRAL = "neutral"  # Not significantly different
    UNFAVORABLE = "unfavorable"  # Significantly worse than baseline
    INSUFFICIENT = "insufficient"  # Not enough trades to classify


@dataclass
class FeatureRangeResult:
    """Result for a single feature range (bin)."""

    range_min: float | None
    range_max: float | None
    range_label: str
    classification: RangeClassification

    # Core metrics
    trade_count: int
    ev: float | None  # Expected value (mean gain %)
    win_rate: float | None  # Percentage of winning trades
    total_pnl: float  # Sum of gains

    # Statistical confidence
    confidence_lower: float | None  # 95% CI lower bound for EV
    confidence_upper: float | None  # 95% CI upper bound for EV
    p_value: float | None  # vs baseline EV

    # Composite score (accounts for sample size)
    viability_score: float


@dataclass
class FeatureAnalysisResult:
    """Complete analysis result for a single feature."""

    feature_name: str
    impact_score: float  # 0-100 score of feature importance

    # Component scores for transparency
    mutual_information: float
    rank_correlation: float
    conditional_variance: float

    # Range analysis
    ranges: list[FeatureRangeResult]

    # Validation metrics
    bootstrap_stability: float  # How consistent across resamples (0-1)
    time_consistency: float | None  # Consistency across years (if available)

    # Warnings
    warnings: list[str]


@dataclass
class FeatureAnalyzerConfig:
    """Configuration for feature analysis."""

    # Phase 1: Feature ranking
    min_unique_values: int = 5  # Skip features with fewer unique values
    top_n_features: int = 10  # Analyze top N features by impact

    # Phase 2: Range identification
    max_bins: int = 5  # Maximum bins per feature
    min_bin_size: int = 30  # Minimum trades per bin

    # Phase 3: Validation
    bootstrap_iterations: int = 1000  # Number of bootstrap samples
    confidence_level: float = 0.95  # Confidence interval level
    significance_threshold: float = 0.05  # p-value threshold

    # Classification thresholds (in percentage points)
    favorable_threshold: float = 0.5  # EV must be this much better than baseline
    unfavorable_threshold: float = -0.5  # EV must be this much worse

    # Column exclusion (lookahead bias prevention)
    exclude_columns: set[str] = field(default_factory=set)


@dataclass
class FeatureAnalyzerResults:
    """Complete results from feature analysis."""

    config: FeatureAnalyzerConfig
    baseline_ev: float
    baseline_win_rate: float
    baseline_trade_count: int

    # Results per feature (sorted by impact score)
    features: list[FeatureAnalysisResult]

    # Cross-feature insights
    feature_correlations: dict[tuple[str, str], float]

    # Overall confidence
    data_quality_score: float  # 0-100 based on sample size
    warnings: list[str]


def calculate_mutual_information(
    feature: NDArray[np.float64],
    gains: NDArray[np.float64],
    n_bins: int = 20,
) -> float:
    """Calculate mutual information between feature and gains.

    MI(X;Y) = H(Y) - H(Y|X)

    Higher MI means knowing the feature value reduces uncertainty about gains.

    Args:
        feature: Array of feature values.
        gains: Array of gain values (same length as feature).
        n_bins: Number of bins for discretization.

    Returns:
        Mutual information in bits (0 = independent, higher = more dependent).
    """
    if len(feature) != len(gains) or len(feature) == 0:
        return 0.0

    # Handle constant arrays
    if np.std(feature) == 0 or np.std(gains) == 0:
        return 0.0

    # Adjust bins based on sample size to avoid overfitting
    # Rule of thumb: at least 5 samples per cell on average
    n_samples = len(feature)
    max_bins_for_sample = max(2, int(np.sqrt(n_samples / 5)))
    actual_bins = min(n_bins, max_bins_for_sample)

    # Discretize into bins using percentiles (handles outliers better)
    try:
        feature_percentiles = np.percentile(feature, np.linspace(0, 100, actual_bins + 1))
        gains_percentiles = np.percentile(gains, np.linspace(0, 100, actual_bins + 1))

        # Make edges unique
        feature_edges = np.unique(feature_percentiles)
        gains_edges = np.unique(gains_percentiles)

        if len(feature_edges) < 2 or len(gains_edges) < 2:
            return 0.0

        feature_bins = np.digitize(feature, feature_edges[1:-1])
        gains_bins = np.digitize(gains, gains_edges[1:-1])
    except Exception:
        return 0.0

    # Calculate joint histogram
    n_feature_bins = len(feature_edges) - 1
    n_gains_bins = len(gains_edges) - 1

    joint_hist = np.zeros((n_feature_bins, n_gains_bins))
    for f_bin, g_bin in zip(feature_bins, gains_bins, strict=False):
        f_idx = min(f_bin, n_feature_bins - 1)
        g_idx = min(g_bin, n_gains_bins - 1)
        joint_hist[f_idx, g_idx] += 1

    # Convert to probabilities
    total = joint_hist.sum()
    if total == 0:
        return 0.0

    joint_prob = joint_hist / total
    feature_prob = joint_prob.sum(axis=1)
    gains_prob = joint_prob.sum(axis=0)

    # Calculate MI: sum of p(x,y) * log2(p(x,y) / (p(x) * p(y)))
    mi = 0.0
    for i in range(n_feature_bins):
        for j in range(n_gains_bins):
            if joint_prob[i, j] > 0 and feature_prob[i] > 0 and gains_prob[j] > 0:
                mi += joint_prob[i, j] * np.log2(
                    joint_prob[i, j] / (feature_prob[i] * gains_prob[j])
                )

    # Apply Miller-Madow bias correction for small samples
    # Bias ~ (|X|-1)(|Y|-1) / (2*N*ln(2))
    non_zero_cells = np.sum(joint_hist > 0)
    bias_correction = (non_zero_cells - 1) / (2 * n_samples * np.log(2))
    mi_corrected = mi - bias_correction

    return max(0.0, mi_corrected)  # MI is non-negative


def calculate_rank_correlation(
    feature: NDArray[np.float64],
    gains: NDArray[np.float64],
) -> float:
    """Calculate Spearman rank correlation between feature and gains.

    Rank correlation is robust to outliers and non-linear monotonic relationships.

    Args:
        feature: Array of feature values.
        gains: Array of gain values.

    Returns:
        Correlation coefficient (-1 to 1).
    """
    if len(feature) != len(gains) or len(feature) < 3:
        return 0.0

    # Handle constant arrays
    if np.std(feature) == 0 or np.std(gains) == 0:
        return 0.0

    try:
        result = stats.spearmanr(feature, gains)
        corr = result.correlation
        return corr if np.isfinite(corr) else 0.0
    except Exception:
        return 0.0


def calculate_conditional_variance(
    feature: NDArray[np.float64],
    gains: NDArray[np.float64],
    n_quantiles: int = 10,
) -> float:
    """Measure how much the mean gain varies across feature quantiles.

    High variance indicates the feature strongly affects expected gains.

    Args:
        feature: Array of feature values.
        gains: Array of gain values.
        n_quantiles: Number of quantiles to divide feature into.

    Returns:
        Variance of conditional means.
    """
    if len(feature) != len(gains) or len(feature) < n_quantiles:
        return 0.0

    # Handle constant feature
    if np.std(feature) == 0:
        return 0.0

    try:
        quantile_edges = np.percentile(feature, np.linspace(0, 100, n_quantiles + 1))
        quantile_means = []

        for i in range(n_quantiles):
            if i == n_quantiles - 1:
                # Last bin includes upper edge
                mask = (feature >= quantile_edges[i]) & (feature <= quantile_edges[i + 1])
            else:
                mask = (feature >= quantile_edges[i]) & (feature < quantile_edges[i + 1])

            if mask.sum() > 0:
                quantile_means.append(gains[mask].mean())

        if len(quantile_means) < 2:
            return 0.0

        return float(np.var(quantile_means))
    except Exception:
        return 0.0


def calculate_impact_score(
    mutual_info: float,
    rank_corr: float,
    cond_variance: float,
    baseline_variance: float,
    weights: tuple[float, float, float] = (0.4, 0.3, 0.3),
) -> float:
    """Combine metrics into single 0-100 impact score.

    Args:
        mutual_info: Mutual information score (typically 0-1).
        rank_corr: Rank correlation (-1 to 1).
        cond_variance: Conditional mean variance.
        baseline_variance: Overall gains variance for normalization.
        weights: Relative weights for (MI, correlation, variance).

    Returns:
        Combined score from 0-100.
    """
    # Normalize mutual information (cap at 1.0)
    mi_norm = min(mutual_info / 1.0, 1.0)

    # Normalize correlation (use absolute value, already 0-1)
    corr_norm = abs(rank_corr)

    # Normalize conditional variance relative to baseline
    var_norm = min(cond_variance / baseline_variance, 1.0) if baseline_variance > 0 else 0.0

    # Weighted combination
    combined = weights[0] * mi_norm + weights[1] * corr_norm + weights[2] * var_norm

    # Scale to 0-100
    return min(100.0, max(0.0, combined * 100))


def find_optimal_bins(
    feature: NDArray[np.float64],
    gains: NDArray[np.float64],
    max_bins: int = 5,
    min_bin_size: int = 30,
) -> list[tuple[float, float]]:
    """Find optimal bin boundaries using chi-squared based merging.

    Algorithm:
    1. Start with quantile-based bins
    2. Merge adjacent bins with most similar gain distributions
    3. Continue until max_bins reached
    4. Enforce minimum bin size

    Args:
        feature: Array of feature values.
        gains: Array of gain values.
        max_bins: Maximum number of bins.
        min_bin_size: Minimum trades per bin.

    Returns:
        List of (min, max) tuples defining bin boundaries.
    """
    n = len(feature)
    if n < min_bin_size:
        return [(float(feature.min()), float(feature.max()))]

    # Start with more granular bins
    initial_bins = min(20, n // min_bin_size)
    if initial_bins < 2:
        return [(float(feature.min()), float(feature.max()))]

    # Create initial bins using percentiles
    percentiles = np.linspace(0, 100, initial_bins + 1)
    edges = np.percentile(feature, percentiles)
    edges = np.unique(edges)  # Remove duplicates

    if len(edges) < 2:
        return [(float(feature.min()), float(feature.max()))]

    # Assign bin labels
    bin_labels = np.digitize(feature, edges[1:-1])

    def get_bin_chi2(labels: NDArray, idx1: int, idx2: int) -> float:
        """Calculate chi-squared between adjacent bins."""
        mask1 = labels == idx1
        mask2 = labels == idx2

        if mask1.sum() == 0 or mask2.sum() == 0:
            return 0.0

        wins1 = (gains[mask1] > 0).sum()
        losses1 = mask1.sum() - wins1
        wins2 = (gains[mask2] > 0).sum()
        losses2 = mask2.sum() - wins2

        total = wins1 + losses1 + wins2 + losses2
        if total == 0:
            return 0.0

        total_wins = wins1 + wins2
        total_losses = losses1 + losses2
        n1 = wins1 + losses1
        n2 = wins2 + losses2

        if total_wins == 0 or total_losses == 0:
            return 0.0

        exp_wins1 = n1 * total_wins / total
        exp_losses1 = n1 * total_losses / total
        exp_wins2 = n2 * total_wins / total
        exp_losses2 = n2 * total_losses / total

        chi2 = 0.0
        for obs, exp in [
            (wins1, exp_wins1),
            (losses1, exp_losses1),
            (wins2, exp_wins2),
            (losses2, exp_losses2),
        ]:
            if exp > 0:
                chi2 += (obs - exp) ** 2 / exp

        return chi2

    # Iteratively merge most similar adjacent bins
    while len(np.unique(bin_labels)) > max_bins:
        unique_labels = sorted(np.unique(bin_labels))
        if len(unique_labels) <= 1:
            break

        min_chi2 = float("inf")
        merge_pair = (unique_labels[0], unique_labels[1])

        for i in range(len(unique_labels) - 1):
            chi2 = get_bin_chi2(bin_labels, unique_labels[i], unique_labels[i + 1])
            if chi2 < min_chi2:
                min_chi2 = chi2
                merge_pair = (unique_labels[i], unique_labels[i + 1])

        # Merge bins
        bin_labels[bin_labels == merge_pair[1]] = merge_pair[0]

    # Enforce minimum bin size by further merging
    while True:
        unique_labels = sorted(np.unique(bin_labels))
        merged = False

        for label in unique_labels:
            count = (bin_labels == label).sum()
            if count < min_bin_size and len(unique_labels) > 1:
                # Find adjacent bin to merge with
                idx = unique_labels.index(label)
                if idx == 0:
                    merge_target = unique_labels[1]
                elif idx == len(unique_labels) - 1:
                    merge_target = unique_labels[-2]
                else:
                    # Merge with smaller neighbor
                    left_count = (bin_labels == unique_labels[idx - 1]).sum()
                    right_count = (bin_labels == unique_labels[idx + 1]).sum()
                    merge_target = (
                        unique_labels[idx - 1]
                        if left_count <= right_count
                        else unique_labels[idx + 1]
                    )

                bin_labels[bin_labels == label] = merge_target
                merged = True
                break

        if not merged:
            break

    # Convert to (min, max) ranges
    unique_labels = sorted(np.unique(bin_labels))
    bins = []

    for i, label in enumerate(unique_labels):
        mask = bin_labels == label
        bin_min = float(feature[mask].min())
        bin_max = float(feature[mask].max())

        # Extend edges to cover full range
        if i == 0:
            bin_min = float(feature.min())
        if i == len(unique_labels) - 1:
            bin_max = float(feature.max())

        bins.append((bin_min, bin_max))

    # Make bins contiguous
    for i in range(len(bins) - 1):
        bins[i] = (bins[i][0], bins[i + 1][0])

    return bins


def analyze_bin(
    gains: NDArray[np.float64],
    baseline_ev: float,
    config: FeatureAnalyzerConfig,
) -> tuple[dict[str, float | int | None], RangeClassification]:
    """Analyze a bin and classify it relative to baseline.

    Args:
        gains: Array of gains for trades in this bin.
        baseline_ev: Baseline expected value for comparison.
        config: Configuration with thresholds.

    Returns:
        Tuple of (metrics dict, classification).
    """
    n = len(gains)

    # Insufficient data
    if n < config.min_bin_size:
        return {
            "trade_count": n,
            "ev": float(gains.mean()) if n > 0 else None,
            "win_rate": float((gains > 0).mean() * 100) if n > 0 else None,
            "total_pnl": float(gains.sum()),
            "confidence_lower": None,
            "confidence_upper": None,
            "p_value": None,
            "viability_score": 0.0,
        }, RangeClassification.INSUFFICIENT

    # Calculate core metrics
    ev = float(gains.mean())
    win_rate = float((gains > 0).mean() * 100)
    total_pnl = float(gains.sum())

    # Bootstrap confidence interval for EV
    bootstrap_evs = []
    rng = np.random.default_rng(42)  # Reproducible
    for _ in range(config.bootstrap_iterations):
        sample = rng.choice(gains, size=n, replace=True)
        bootstrap_evs.append(sample.mean())

    alpha = 1 - config.confidence_level
    ci_lower = float(np.percentile(bootstrap_evs, alpha / 2 * 100))
    ci_upper = float(np.percentile(bootstrap_evs, (1 - alpha / 2) * 100))

    # Statistical test vs baseline (one-sample t-test)
    t_stat, p_value = stats.ttest_1samp(gains, baseline_ev)
    p_value = float(p_value)

    # Viability score: EV advantage weighted by sample size
    ev_diff = ev - baseline_ev
    # Convert to percentage points (* 100) for meaningful scale
    viability_score = float(ev_diff * 100 * np.sqrt(n))

    # Classification
    ev_diff_pct = (ev - baseline_ev) * 100  # Convert to percentage points

    if n < config.min_bin_size:
        classification = RangeClassification.INSUFFICIENT
    elif ev_diff_pct > config.favorable_threshold and p_value < config.significance_threshold:
        classification = RangeClassification.FAVORABLE
    elif ev_diff_pct < config.unfavorable_threshold and p_value < config.significance_threshold:
        classification = RangeClassification.UNFAVORABLE
    else:
        classification = RangeClassification.NEUTRAL

    return {
        "trade_count": n,
        "ev": ev,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "confidence_lower": ci_lower,
        "confidence_upper": ci_upper,
        "p_value": p_value,
        "viability_score": viability_score,
    }, classification


class FeatureAnalyzer:
    """Main feature analyzer that orchestrates the analysis pipeline.

    The analyzer performs three phases:
    1. Calculate impact scores for all features
    2. Run optimal binning for top N features
    3. Analyze each bin and calculate bootstrap stability

    Args:
        config: Configuration for the analysis.
    """

    def __init__(self, config: FeatureAnalyzerConfig | None = None) -> None:
        """Initialize analyzer with configuration.

        Args:
            config: Configuration for the analysis. Uses defaults if None.
        """
        self.config = config or FeatureAnalyzerConfig()
        self._logger = logging.getLogger(__name__)

    def get_analyzable_columns(self, df: pd.DataFrame) -> list[str]:
        """Get list of columns that can be analyzed.

        Filters out:
        - Columns in config.exclude_columns
        - Non-numeric columns
        - Columns with fewer unique values than config.min_unique_values

        Args:
            df: DataFrame to analyze.

        Returns:
            List of column names that can be analyzed.
        """
        analyzable = []

        for col in df.columns:
            # Skip excluded columns
            if col in self.config.exclude_columns:
                continue

            # Skip non-numeric columns
            if not pd.api.types.is_numeric_dtype(df[col]):
                continue

            # Skip columns with too few unique values
            if df[col].nunique() < self.config.min_unique_values:
                continue

            analyzable.append(col)

        return analyzable

    def run(
        self,
        df: pd.DataFrame,
        gain_col: str,
        date_col: str | None = None,
    ) -> FeatureAnalyzerResults:
        """Run the full analysis pipeline.

        Args:
            df: DataFrame with feature and gain data.
            gain_col: Name of the column containing gains.
            date_col: Optional name of the column containing dates (for time consistency).

        Returns:
            Complete analysis results.
        """
        warnings: list[str] = []

        # Calculate baseline metrics
        gains = df[gain_col].values.astype(np.float64)
        baseline_ev = float(np.mean(gains))
        baseline_win_rate = float((gains > 0).mean() * 100)
        baseline_trade_count = len(gains)
        baseline_variance = float(np.var(gains))

        self._logger.info(
            f"Baseline: EV={baseline_ev:.4f}, WinRate={baseline_win_rate:.1f}%, "
            f"Trades={baseline_trade_count}"
        )

        # Get analyzable columns
        columns = self.get_analyzable_columns(df)
        if not columns:
            warnings.append("No analyzable columns found")
            return FeatureAnalyzerResults(
                config=self.config,
                baseline_ev=baseline_ev,
                baseline_win_rate=baseline_win_rate,
                baseline_trade_count=baseline_trade_count,
                features=[],
                feature_correlations={},
                data_quality_score=0.0,
                warnings=warnings,
            )

        # Phase 1: Calculate impact scores for all features
        self._logger.info(f"Phase 1: Calculating impact scores for {len(columns)} features")
        feature_scores: list[tuple[str, float, float, float, float]] = []

        for col in columns:
            feature_values = df[col].values.astype(np.float64)

            # Skip features with missing values
            valid_mask = ~np.isnan(feature_values) & ~np.isnan(gains)
            if valid_mask.sum() < self.config.min_bin_size:
                continue

            valid_feature = feature_values[valid_mask]
            valid_gains = gains[valid_mask]

            mi = calculate_mutual_information(valid_feature, valid_gains)
            corr = calculate_rank_correlation(valid_feature, valid_gains)
            cond_var = calculate_conditional_variance(valid_feature, valid_gains)

            score = calculate_impact_score(mi, corr, cond_var, baseline_variance)
            feature_scores.append((col, score, mi, corr, cond_var))

        # Sort by impact score and take top N
        feature_scores.sort(key=lambda x: x[1], reverse=True)
        top_features = feature_scores[: self.config.top_n_features]

        self._logger.info(f"Top features: {[f[0] for f in top_features[:5]]}")

        # Phase 2 & 3: Optimal binning and range analysis for top features
        feature_results: list[FeatureAnalysisResult] = []

        for col, score, mi, corr, cond_var in top_features:
            self._logger.debug(f"Analyzing feature: {col} (score={score:.1f})")

            feature_values = df[col].values.astype(np.float64)
            valid_mask = ~np.isnan(feature_values) & ~np.isnan(gains)
            valid_feature = feature_values[valid_mask]
            valid_gains = gains[valid_mask]

            # Find optimal bins
            bins = find_optimal_bins(
                valid_feature,
                valid_gains,
                max_bins=self.config.max_bins,
                min_bin_size=self.config.min_bin_size,
            )

            # Analyze each bin
            range_results: list[FeatureRangeResult] = []
            for bin_min, bin_max in bins:
                # Get trades in this bin
                if bin_max == bins[-1][1]:  # Last bin includes upper edge
                    bin_mask = (valid_feature >= bin_min) & (valid_feature <= bin_max)
                else:
                    bin_mask = (valid_feature >= bin_min) & (valid_feature < bin_max)

                bin_gains = valid_gains[bin_mask]

                # Analyze the bin
                metrics, classification = analyze_bin(bin_gains, baseline_ev, self.config)

                range_label = f"{bin_min:.2f} - {bin_max:.2f}"
                range_result = FeatureRangeResult(
                    range_min=bin_min,
                    range_max=bin_max,
                    range_label=range_label,
                    classification=classification,
                    trade_count=metrics["trade_count"],
                    ev=metrics["ev"],
                    win_rate=metrics["win_rate"],
                    total_pnl=metrics["total_pnl"],
                    confidence_lower=metrics["confidence_lower"],
                    confidence_upper=metrics["confidence_upper"],
                    p_value=metrics["p_value"],
                    viability_score=metrics["viability_score"],
                )
                range_results.append(range_result)

            # Calculate bootstrap stability
            bootstrap_stability = self._calculate_bootstrap_stability(
                valid_feature, valid_gains, bins, baseline_ev
            )

            # Calculate time consistency if date column provided
            time_consistency = None
            if date_col is not None and date_col in df.columns:
                time_consistency = self._calculate_time_consistency(
                    df, col, gain_col, date_col, bins, baseline_ev
                )

            feature_result = FeatureAnalysisResult(
                feature_name=col,
                impact_score=score,
                mutual_information=mi,
                rank_correlation=corr,
                conditional_variance=cond_var,
                ranges=range_results,
                bootstrap_stability=bootstrap_stability,
                time_consistency=time_consistency,
                warnings=[],
            )
            feature_results.append(feature_result)

        # Calculate feature correlations
        feature_correlations = self._calculate_feature_correlations(
            df, [f.feature_name for f in feature_results]
        )

        # Calculate data quality score
        data_quality_score = self._calculate_data_quality_score(baseline_trade_count)

        return FeatureAnalyzerResults(
            config=self.config,
            baseline_ev=baseline_ev,
            baseline_win_rate=baseline_win_rate,
            baseline_trade_count=baseline_trade_count,
            features=feature_results,
            feature_correlations=feature_correlations,
            data_quality_score=data_quality_score,
            warnings=warnings,
        )

    def _calculate_bootstrap_stability(
        self,
        feature: NDArray[np.float64],
        gains: NDArray[np.float64],
        bins: list[tuple[float, float]],
        baseline_ev: float,
    ) -> float:
        """Calculate how stable bin classifications are across bootstrap samples.

        Args:
            feature: Array of feature values.
            gains: Array of gains.
            bins: List of (min, max) bin boundaries.
            baseline_ev: Baseline expected value.

        Returns:
            Stability score from 0 to 1 (1 = perfectly stable).
        """
        n = len(feature)
        n_iterations = min(100, self.config.bootstrap_iterations)  # Reduced for speed
        rng = np.random.default_rng(42)

        # Track classification consistency for each bin
        classifications_per_bin: list[list[RangeClassification]] = [[] for _ in bins]

        for _ in range(n_iterations):
            # Bootstrap sample
            indices = rng.choice(n, size=n, replace=True)
            sample_feature = feature[indices]
            sample_gains = gains[indices]

            for i, (bin_min, bin_max) in enumerate(bins):
                if bin_max == bins[-1][1]:
                    bin_mask = (sample_feature >= bin_min) & (sample_feature <= bin_max)
                else:
                    bin_mask = (sample_feature >= bin_min) & (sample_feature < bin_max)

                bin_gains = sample_gains[bin_mask]
                if len(bin_gains) < self.config.min_bin_size:
                    classifications_per_bin[i].append(RangeClassification.INSUFFICIENT)
                else:
                    _, classification = analyze_bin(bin_gains, baseline_ev, self.config)
                    classifications_per_bin[i].append(classification)

        # Calculate stability as fraction of samples matching modal classification
        total_stability = 0.0
        for classifications in classifications_per_bin:
            if classifications:
                from collections import Counter

                counter = Counter(classifications)
                mode_count = counter.most_common(1)[0][1]
                total_stability += mode_count / len(classifications)

        return total_stability / len(bins) if bins else 0.0

    def _calculate_time_consistency(
        self,
        df: pd.DataFrame,
        feature_col: str,
        gain_col: str,
        date_col: str,
        bins: list[tuple[float, float]],
        baseline_ev: float,
    ) -> float | None:
        """Calculate consistency of classifications across years.

        Args:
            df: Full DataFrame.
            feature_col: Name of feature column.
            gain_col: Name of gain column.
            date_col: Name of date column.
            bins: List of (min, max) bin boundaries.
            baseline_ev: Baseline expected value.

        Returns:
            Consistency score from 0 to 1, or None if insufficient data.
        """
        try:
            dates = pd.to_datetime(df[date_col])
            years = dates.dt.year.unique()

            if len(years) < 2:
                return None

            # Track classifications per year for each bin
            classifications_per_bin: list[list[RangeClassification]] = [[] for _ in bins]

            for year in years:
                year_mask = dates.dt.year == year
                year_df = df[year_mask]

                if len(year_df) < self.config.min_bin_size * len(bins):
                    continue

                year_feature = year_df[feature_col].values.astype(np.float64)
                year_gains = year_df[gain_col].values.astype(np.float64)

                for i, (bin_min, bin_max) in enumerate(bins):
                    if bin_max == bins[-1][1]:
                        bin_mask = (year_feature >= bin_min) & (year_feature <= bin_max)
                    else:
                        bin_mask = (year_feature >= bin_min) & (year_feature < bin_max)

                    bin_gains = year_gains[bin_mask]
                    if len(bin_gains) >= self.config.min_bin_size // 2:  # Relaxed for yearly
                        _, classification = analyze_bin(bin_gains, baseline_ev, self.config)
                        classifications_per_bin[i].append(classification)

            # Calculate consistency
            total_consistency = 0.0
            valid_bins = 0

            for classifications in classifications_per_bin:
                if len(classifications) >= 2:
                    from collections import Counter

                    counter = Counter(classifications)
                    mode_count = counter.most_common(1)[0][1]
                    total_consistency += mode_count / len(classifications)
                    valid_bins += 1

            return total_consistency / valid_bins if valid_bins > 0 else None

        except Exception:
            return None

    def _calculate_feature_correlations(
        self,
        df: pd.DataFrame,
        feature_names: list[str],
    ) -> dict[tuple[str, str], float]:
        """Calculate pairwise correlations between analyzed features.

        Args:
            df: DataFrame with features.
            feature_names: List of feature names to correlate.

        Returns:
            Dictionary mapping (feature1, feature2) to correlation.
        """
        correlations: dict[tuple[str, str], float] = {}

        for i, f1 in enumerate(feature_names):
            for f2 in feature_names[i + 1 :]:
                try:
                    corr = df[f1].corr(df[f2])
                    if np.isfinite(corr):
                        correlations[(f1, f2)] = float(corr)
                except Exception:
                    pass

        return correlations

    def _calculate_data_quality_score(self, trade_count: int) -> float:
        """Calculate data quality score based on sample size.

        Args:
            trade_count: Number of trades in the dataset.

        Returns:
            Quality score from 0 to 100.
        """
        # Heuristic: 100 trades = 50 score, 1000 trades = 90 score
        if trade_count < 30:
            return 0.0
        elif trade_count < 100:
            return 10.0 + (trade_count - 30) * 40.0 / 70.0
        elif trade_count < 1000:
            return 50.0 + (trade_count - 100) * 40.0 / 900.0
        else:
            return min(100.0, 90.0 + (trade_count - 1000) * 10.0 / 9000.0)
