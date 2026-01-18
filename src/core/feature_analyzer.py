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
