# src/core/feature_analyzer.py
"""Feature analysis engine for identifying impactful features and ranges.

This module implements a multi-criteria approach that:
1. Ranks features by their relationship to gains (not predictive power)
2. Identifies favorable/unfavorable ranges with practical constraints
3. Validates findings through bootstrap resampling
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np
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
    min_bin_pct: float = 5.0  # Minimum % of trades per bin

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
        feature_percentiles = np.percentile(
            feature, np.linspace(0, 100, actual_bins + 1)
        )
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
    for f_bin, g_bin in zip(feature_bins, gains_bins):
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
    if baseline_variance > 0:
        var_norm = min(cond_variance / baseline_variance, 1.0)
    else:
        var_norm = 0.0

    # Weighted combination
    combined = (
        weights[0] * mi_norm + weights[1] * corr_norm + weights[2] * var_norm
    )

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
