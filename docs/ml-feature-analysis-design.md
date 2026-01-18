# Machine Learning Feature Analysis for Lumen

## Executive Summary

This document presents a comprehensive solution for incorporating machine learning into Lumen to identify which features (columns) impact trading gains, what ranges are favorable, and what ranges to avoid. The solution specifically addresses the critical concerns of **overfitting** and **practical viability** (ensuring recommendations consider trade count and total PnL, not just maximum gains).

**Key Insight**: The solution frames this as a **statistical analysis problem with practical constraints**, NOT a prediction problem. This fundamental distinction eliminates the primary source of overfitting while delivering actionable insights.

---

## Table of Contents

1. [Problem Analysis](#problem-analysis)
2. [Why Traditional ML Approaches Fail Here](#why-traditional-ml-approaches-fail-here)
3. [Recommended Solution: Multi-Criteria Feature Analysis](#recommended-solution-multi-criteria-feature-analysis)
4. [Technical Architecture](#technical-architecture)
5. [Algorithm Details](#algorithm-details)
6. [Output Interpretation Guide](#output-interpretation-guide)
7. [UI/UX Design](#uiux-design)
8. [Dependencies and Performance](#dependencies-and-performance)
9. [Implementation Roadmap](#implementation-roadmap)

---

## Problem Analysis

### What We're Actually Trying to Answer

1. **Feature Importance**: Which columns in the trade data have a meaningful relationship with trading gains?
2. **Favorable Ranges**: For important features, what value ranges are associated with better-than-average performance?
3. **Unfavorable Ranges**: What value ranges should be avoided due to poor performance?
4. **Practical Viability**: Are these ranges based on enough trades to be statistically reliable?

### The Overfitting Trap

Traditional ML approaches try to **predict** future gains from features. This is problematic because:

1. **Markets are non-stationary**: Patterns that worked historically may not persist
2. **Small sample sizes**: Typical backtest datasets have hundreds to thousands of trades, not millions
3. **Feature snooping**: With many features, some will show spurious correlations by chance
4. **Optimization bias**: ML models will find the parameters that maximize backtest performance, not future performance

### The "Max Gain" Trap

A naive approach might:
- Find the 10 trades with highest gains
- Identify what features they share
- Recommend those feature ranges

This fails because:
- 10 trades is not statistically significant
- Total PnL might be negative (a few big winners, many small losers)
- The pattern might not be consistent across time periods

---

## Why Traditional ML Approaches Fail Here

### Approach 1: Random Forest / Gradient Boosting for Prediction

```
❌ Problems:
- Trains to minimize prediction error, not maximize trading viability
- Feature importance doesn't directly give actionable ranges
- Requires train/test split that may not match trading reality
- Model complexity makes overfitting hard to detect
```

### Approach 2: Decision Tree Splits as Ranges

```
⚠️ Partial Solution:
- Trees do find split points (ranges)
- But single trees are unstable
- Depth must be severely constrained
- Doesn't consider trade count in splits
```

### Approach 3: Pure Correlation Analysis

```
⚠️ Partial Solution:
- Simple and interpretable
- But misses non-linear relationships
- Doesn't provide ranges
- Single metric doesn't capture complexity
```

---

## Recommended Solution: Multi-Criteria Feature Analysis

### Core Philosophy

**Don't predict gains. Analyze the statistical properties of gains conditioned on feature values, with practical constraints built into the scoring.**

### The Three-Phase Framework

```
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 1: FEATURE RANKING                      │
│  "Which features have meaningful relationships with gains?"      │
├─────────────────────────────────────────────────────────────────┤
│  • Mutual Information (captures non-linear relationships)        │
│  • Rank Correlation (robust to outliers)                        │
│  • Conditional Mean Variance (how much does mean gain vary?)    │
│  • Aggregate into single "Impact Score"                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PHASE 2: RANGE IDENTIFICATION                   │
│  "For important features, what ranges are favorable/unfavorable?"│
├─────────────────────────────────────────────────────────────────┤
│  • Optimal binning (Chi-squared based)                          │
│  • Per-bin metrics: EV, win rate, count, total PnL              │
│  • Composite scoring with trade count penalty                   │
│  • Classification: Favorable / Neutral / Avoid                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PHASE 3: VALIDATION                             │
│  "How confident should we be in these findings?"                 │
├─────────────────────────────────────────────────────────────────┤
│  • Bootstrap resampling for confidence intervals                │
│  • Time-based consistency check (if dates available)            │
│  • Statistical significance testing                             │
│  • Sample size warnings                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technical Architecture

### New Module: `src/core/feature_analyzer.py`

```python
"""
Feature analysis engine for identifying impactful features and ranges.

This module implements a multi-criteria approach that:
1. Ranks features by their relationship to gains (not predictive power)
2. Identifies favorable/unfavorable ranges with practical constraints
3. Validates findings through resampling
"""

from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd
from scipy import stats


class RangeClassification(Enum):
    FAVORABLE = "favorable"      # Significantly better than baseline
    NEUTRAL = "neutral"          # Not significantly different
    UNFAVORABLE = "unfavorable"  # Significantly worse than baseline
    INSUFFICIENT = "insufficient" # Not enough trades to classify


@dataclass
class FeatureRangeResult:
    """Result for a single feature range (bin)."""
    range_min: float | None
    range_max: float | None
    range_label: str
    classification: RangeClassification
    
    # Core metrics
    trade_count: int
    ev: float | None           # Expected value (mean gain)
    win_rate: float | None     # Percentage of winning trades
    total_pnl: float           # Sum of gains
    
    # Statistical confidence
    confidence_lower: float | None  # 95% CI lower bound for EV
    confidence_upper: float | None  # 95% CI upper bound for EV
    p_value: float | None           # vs baseline EV
    
    # Composite score (accounts for sample size)
    viability_score: float


@dataclass
class FeatureAnalysisResult:
    """Complete analysis result for a single feature."""
    feature_name: str
    impact_score: float        # 0-100 score of feature importance
    
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
    min_unique_values: int = 5         # Skip features with fewer unique values
    top_n_features: int = 10           # Analyze top N features by impact
    
    # Phase 2: Range identification  
    max_bins: int = 5                  # Maximum bins per feature
    min_bin_size: int = 30             # Minimum trades per bin
    min_bin_pct: float = 5.0           # Minimum % of trades per bin
    
    # Phase 3: Validation
    bootstrap_iterations: int = 1000   # Number of bootstrap samples
    confidence_level: float = 0.95     # Confidence interval level
    significance_threshold: float = 0.05  # p-value threshold
    
    # Classification thresholds
    favorable_ev_threshold: float = 0.5   # EV must be this much better than baseline (in %)
    unfavorable_ev_threshold: float = -0.5  # EV must be this much worse than baseline


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
    feature_correlations: dict[tuple[str, str], float]  # Correlation between top features
    
    # Overall confidence
    data_quality_score: float  # 0-100 based on sample size, feature quality
    warnings: list[str]
```

### New Tab: `src/tabs/feature_insights.py`

This tab will display the ML feature analysis results with clear visualizations and interpretations.

---

## Algorithm Details

### Phase 1: Feature Ranking

#### 1.1 Mutual Information Score

Mutual information captures both linear and non-linear relationships between a feature and gains.

```python
def calculate_mutual_information(feature: np.ndarray, gains: np.ndarray, n_bins: int = 20) -> float:
    """
    Calculate mutual information between feature and gains.
    
    MI(X;Y) = H(Y) - H(Y|X)
    
    Higher MI means knowing the feature value reduces uncertainty about gains.
    """
    # Discretize continuous values into bins
    feature_bins = np.digitize(feature, np.percentile(feature, np.linspace(0, 100, n_bins)))
    gains_bins = np.digitize(gains, np.percentile(gains, np.linspace(0, 100, n_bins)))
    
    # Calculate joint and marginal entropies
    joint_hist, _, _ = np.histogram2d(feature_bins, gains_bins, bins=n_bins)
    joint_prob = joint_hist / joint_hist.sum()
    
    feature_prob = joint_prob.sum(axis=1)
    gains_prob = joint_prob.sum(axis=0)
    
    # MI = sum over all bins of p(x,y) * log(p(x,y) / (p(x) * p(y)))
    mi = 0.0
    for i in range(n_bins):
        for j in range(n_bins):
            if joint_prob[i, j] > 0 and feature_prob[i] > 0 and gains_prob[j] > 0:
                mi += joint_prob[i, j] * np.log2(
                    joint_prob[i, j] / (feature_prob[i] * gains_prob[j])
                )
    
    return mi
```

#### 1.2 Rank Correlation (Spearman)

More robust to outliers than Pearson correlation.

```python
def calculate_rank_correlation(feature: np.ndarray, gains: np.ndarray) -> float:
    """Spearman rank correlation - robust to outliers."""
    return stats.spearmanr(feature, gains).correlation
```

#### 1.3 Conditional Mean Variance

How much does the expected gain vary across different feature values?

```python
def calculate_conditional_variance(feature: np.ndarray, gains: np.ndarray, n_quantiles: int = 10) -> float:
    """
    Measure how much the mean gain varies across feature quantiles.
    
    High variance = feature strongly affects expected gains.
    """
    quantile_means = []
    quantile_edges = np.percentile(feature, np.linspace(0, 100, n_quantiles + 1))
    
    for i in range(n_quantiles):
        mask = (feature >= quantile_edges[i]) & (feature < quantile_edges[i + 1])
        if mask.sum() > 0:
            quantile_means.append(gains[mask].mean())
    
    return np.var(quantile_means) if quantile_means else 0.0
```

#### 1.4 Combined Impact Score

```python
def calculate_impact_score(
    mutual_info: float,
    rank_corr: float,
    cond_variance: float,
    weights: tuple[float, float, float] = (0.4, 0.3, 0.3)
) -> float:
    """
    Combine metrics into single 0-100 impact score.
    
    Weights can be tuned based on what matters most to the user.
    """
    # Normalize each component to 0-1 range
    # (actual normalization would be relative to all features)
    mi_norm = min(mutual_info / 1.0, 1.0)  # MI typically 0-1 for well-behaved data
    corr_norm = abs(rank_corr)  # Already 0-1
    var_norm = min(cond_variance / np.var(gains), 1.0)  # Relative to overall variance
    
    combined = (
        weights[0] * mi_norm +
        weights[1] * corr_norm +
        weights[2] * var_norm
    )
    
    return combined * 100
```

### Phase 2: Range Identification

#### 2.1 Optimal Binning Algorithm

The goal is to find bin boundaries that maximize the difference in gain distribution between bins while respecting minimum sample size constraints.

```python
def find_optimal_bins(
    feature: np.ndarray,
    gains: np.ndarray,
    max_bins: int = 5,
    min_bin_size: int = 30
) -> list[tuple[float, float]]:
    """
    Find optimal bin boundaries using chi-squared based merging.
    
    Algorithm:
    1. Start with many small bins (e.g., deciles)
    2. Calculate chi-squared statistic between adjacent bins
    3. Merge adjacent bins with lowest chi-squared (most similar)
    4. Repeat until max_bins reached or all bins significantly different
    5. Ensure minimum bin size constraint
    """
    # Start with percentile-based bins
    initial_bins = 20
    percentiles = np.percentile(feature, np.linspace(0, 100, initial_bins + 1))
    
    # Assign initial bin labels
    bin_labels = np.digitize(feature, percentiles[1:-1])
    
    # Iteratively merge most similar adjacent bins
    while len(np.unique(bin_labels)) > max_bins:
        unique_bins = sorted(np.unique(bin_labels))
        min_chi2 = float('inf')
        merge_idx = 0
        
        for i in range(len(unique_bins) - 1):
            # Calculate chi-squared between adjacent bins
            mask1 = bin_labels == unique_bins[i]
            mask2 = bin_labels == unique_bins[i + 1]
            
            gains1 = gains[mask1]
            gains2 = gains[mask2]
            
            chi2 = calculate_bin_chi2(gains1, gains2)
            
            if chi2 < min_chi2:
                min_chi2 = chi2
                merge_idx = i
        
        # Merge bins
        bin_labels[bin_labels == unique_bins[merge_idx + 1]] = unique_bins[merge_idx]
    
    # Enforce minimum bin size by further merging small bins
    bin_labels = enforce_min_bin_size(bin_labels, feature, min_bin_size)
    
    # Convert to (min, max) tuples
    return extract_bin_ranges(bin_labels, feature)


def calculate_bin_chi2(gains1: np.ndarray, gains2: np.ndarray) -> float:
    """Chi-squared statistic for comparing two gain distributions."""
    # Categorize gains as win/loss for chi-squared
    wins1 = (gains1 > 0).sum()
    losses1 = (gains1 <= 0).sum()
    wins2 = (gains2 > 0).sum()
    losses2 = (gains2 <= 0).sum()
    
    # Expected frequencies under null hypothesis (same win rate)
    total = wins1 + losses1 + wins2 + losses2
    total_wins = wins1 + wins2
    total_losses = losses1 + losses2
    n1 = wins1 + losses1
    n2 = wins2 + losses2
    
    if total == 0 or total_wins == 0 or total_losses == 0:
        return 0.0
    
    exp_wins1 = n1 * total_wins / total
    exp_losses1 = n1 * total_losses / total
    exp_wins2 = n2 * total_wins / total
    exp_losses2 = n2 * total_losses / total
    
    chi2 = 0.0
    for obs, exp in [(wins1, exp_wins1), (losses1, exp_losses1),
                     (wins2, exp_wins2), (losses2, exp_losses2)]:
        if exp > 0:
            chi2 += (obs - exp) ** 2 / exp
    
    return chi2
```

#### 2.2 Per-Bin Metrics and Classification

```python
def analyze_bin(
    gains: np.ndarray,
    baseline_ev: float,
    baseline_win_rate: float,
    config: FeatureAnalyzerConfig
) -> tuple[dict, RangeClassification]:
    """
    Calculate metrics for a bin and classify it.
    
    Returns metrics dict and classification.
    """
    n = len(gains)
    
    # Insufficient data
    if n < config.min_bin_size:
        return {
            'trade_count': n,
            'ev': gains.mean() if n > 0 else None,
            'win_rate': (gains > 0).mean() * 100 if n > 0 else None,
            'total_pnl': gains.sum(),
            'viability_score': 0.0
        }, RangeClassification.INSUFFICIENT
    
    # Calculate metrics
    ev = gains.mean()
    win_rate = (gains > 0).mean() * 100
    total_pnl = gains.sum()
    
    # Bootstrap confidence interval for EV
    bootstrap_evs = []
    for _ in range(config.bootstrap_iterations):
        sample = np.random.choice(gains, size=n, replace=True)
        bootstrap_evs.append(sample.mean())
    
    ci_lower = np.percentile(bootstrap_evs, (1 - config.confidence_level) / 2 * 100)
    ci_upper = np.percentile(bootstrap_evs, (1 + config.confidence_level) / 2 * 100)
    
    # Statistical test vs baseline
    t_stat, p_value = stats.ttest_1samp(gains, baseline_ev)
    
    # Viability score: combines EV advantage with sample size
    # Score = (EV - baseline) * sqrt(n) * (1 if positive else 0.5)
    ev_diff = ev - baseline_ev
    viability_score = ev_diff * np.sqrt(n) * (1.0 if ev > baseline_ev else 0.5)
    
    # Classification
    if ev > baseline_ev + config.favorable_ev_threshold and p_value < config.significance_threshold:
        classification = RangeClassification.FAVORABLE
    elif ev < baseline_ev + config.unfavorable_ev_threshold and p_value < config.significance_threshold:
        classification = RangeClassification.UNFAVORABLE
    else:
        classification = RangeClassification.NEUTRAL
    
    return {
        'trade_count': n,
        'ev': ev,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'confidence_lower': ci_lower,
        'confidence_upper': ci_upper,
        'p_value': p_value,
        'viability_score': viability_score
    }, classification
```

### Phase 3: Validation

#### 3.1 Bootstrap Stability

```python
def calculate_bootstrap_stability(
    feature: np.ndarray,
    gains: np.ndarray,
    bin_boundaries: list[tuple[float, float]],
    n_iterations: int = 1000
) -> float:
    """
    How often does each bin maintain the same classification across bootstrap samples?
    
    Returns stability score 0-1 (1 = perfectly stable classifications).
    """
    original_classifications = []
    for (lo, hi) in bin_boundaries:
        mask = (feature >= lo) & (feature < hi)
        _, classification = analyze_bin(gains[mask], gains.mean(), ...)
        original_classifications.append(classification)
    
    agreement_count = 0
    for _ in range(n_iterations):
        # Bootstrap sample
        indices = np.random.choice(len(feature), size=len(feature), replace=True)
        boot_feature = feature[indices]
        boot_gains = gains[indices]
        
        for i, (lo, hi) in enumerate(bin_boundaries):
            mask = (boot_feature >= lo) & (boot_feature < hi)
            if mask.sum() >= min_bin_size:
                _, classification = analyze_bin(boot_gains[mask], boot_gains.mean(), ...)
                if classification == original_classifications[i]:
                    agreement_count += 1
    
    return agreement_count / (n_iterations * len(bin_boundaries))
```

#### 3.2 Time Consistency Check

```python
def calculate_time_consistency(
    df: pd.DataFrame,
    feature_col: str,
    gain_col: str,
    date_col: str,
    bin_boundaries: list[tuple[float, float]]
) -> float:
    """
    Check if classifications are consistent across different time periods.
    
    Returns consistency score 0-1.
    """
    # Get year from date column
    years = df[date_col].dt.year.unique()
    
    if len(years) < 2:
        return None  # Not enough data for time-based validation
    
    # Get classification for each year
    year_classifications = {}
    for year in years:
        year_mask = df[date_col].dt.year == year
        year_df = df[year_mask]
        
        classifications = []
        for (lo, hi) in bin_boundaries:
            bin_mask = (year_df[feature_col] >= lo) & (year_df[feature_col] < hi)
            if bin_mask.sum() >= 10:  # Lower threshold for per-year
                _, classification = analyze_bin(year_df.loc[bin_mask, gain_col].values, ...)
                classifications.append(classification)
            else:
                classifications.append(None)
        
        year_classifications[year] = classifications
    
    # Count agreement across years
    agreements = 0
    comparisons = 0
    for i in range(len(bin_boundaries)):
        valid_years = [y for y in years if year_classifications[y][i] is not None]
        if len(valid_years) >= 2:
            for j in range(len(valid_years)):
                for k in range(j + 1, len(valid_years)):
                    comparisons += 1
                    if year_classifications[valid_years[j]][i] == year_classifications[valid_years[k]][i]:
                        agreements += 1
    
    return agreements / comparisons if comparisons > 0 else None
```

---

## Output Interpretation Guide

### For Users: How to Read the Results

#### Feature Impact Score (0-100)

| Score | Interpretation |
|-------|----------------|
| 80-100 | **Strong Impact**: This feature has a clear, consistent relationship with gains |
| 60-79 | **Moderate Impact**: Meaningful relationship, worth considering in filters |
| 40-59 | **Weak Impact**: Some relationship exists but may not be actionable |
| 0-39 | **Minimal Impact**: No strong evidence this feature affects gains |

#### Range Classifications

| Classification | What It Means | Action |
|----------------|---------------|--------|
| **Favorable** | Trades in this range have significantly better EV than baseline, with sufficient sample size | Consider filtering TO this range |
| **Neutral** | No significant difference from baseline | No action needed |
| **Unfavorable** | Trades in this range have significantly worse EV than baseline | Consider filtering OUT this range |
| **Insufficient** | Not enough trades to make a reliable determination | Need more data |

#### Confidence Indicators

- **Confidence Interval**: The range where true EV likely falls (95% confidence)
- **P-Value**: <0.05 means statistically significant, <0.01 means highly significant
- **Bootstrap Stability**: How likely classifications would hold with different data sample
- **Time Consistency**: Do findings hold across different years?

#### Warning Flags

| Warning | Meaning |
|---------|---------|
| "Low sample size" | Results may not generalize; need more trades |
| "High feature correlation" | This feature overlaps with another; don't double-filter |
| "Inconsistent across time" | Pattern may be temporary; proceed with caution |
| "Near significance threshold" | Classification could change with small data changes |

### Example Output Interpretation

```
Feature: time_minutes
Impact Score: 72/100 (Moderate-High Impact)
Bootstrap Stability: 0.85 (Good)
Time Consistency: 0.78 (Acceptable)

Ranges:
┌─────────────────┬──────────┬───────────┬──────────┬────────────────┐
│ Range           │ Trades   │ EV        │ Win Rate │ Classification │
├─────────────────┼──────────┼───────────┼──────────┼────────────────┤
│ 0 - 60 min      │ 342      │ +2.1%     │ 58%      │ FAVORABLE      │
│ 60 - 180 min    │ 518      │ +0.3%     │ 51%      │ NEUTRAL        │
│ 180 - 390 min   │ 287      │ -1.4%     │ 44%      │ UNFAVORABLE    │
└─────────────────┴──────────┴───────────┴──────────┴────────────────┘

Interpretation:
- Early morning trades (0-60 min) show significantly better performance
- EV of +2.1% vs baseline of +0.5% with 342 trades is statistically significant
- Consider filtering to early morning trades if this fits your strategy
- Afternoon trades (180-390 min) underperform; consider avoiding
```

---

## UI/UX Design

### New Tab: "Feature Insights"

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Feature Insights                                                    [Run] 🔄 │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Configuration                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Min Trades per Range: [30 ▼]   Max Ranges per Feature: [5 ▼]          │ │
│  │ Confidence Level: [95% ▼]      Top Features to Analyze: [10 ▼]        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ Data Quality ─────────────────────────────────────────────────────────┐ │
│  │ 📊 1,247 trades analyzed  │  📈 Baseline EV: +0.52%  │  Score: 78/100  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  Feature Rankings                                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ 1. time_minutes        ████████████████████████░░░░░░  72/100         │ │
│  │ 2. gap_percent         ███████████████████░░░░░░░░░░░  65/100         │ │
│  │ 3. volume_ratio        ██████████████████░░░░░░░░░░░░  61/100         │ │
│  │ 4. atr_14              █████████████░░░░░░░░░░░░░░░░░  45/100         │ │
│  │ 5. prev_close_dist     ████████████░░░░░░░░░░░░░░░░░░  42/100         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  Selected Feature: time_minutes                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        RANGE ANALYSIS                                  │ │
│  │  ┌────────┬────────┬────────┬────────┬────────────┬─────────────────┐ │ │
│  │  │ Range  │ Trades │ EV     │ WinRate│ Total PnL  │ Classification  │ │ │
│  │  ├────────┼────────┼────────┼────────┼────────────┼─────────────────┤ │ │
│  │  │ 0-60   │ 342    │ +2.1%  │ 58%    │ +$7,182    │ 🟢 FAVORABLE   │ │ │
│  │  │ 60-180 │ 518    │ +0.3%  │ 51%    │ +$1,554    │ ⚪ NEUTRAL     │ │ │
│  │  │ 180-390│ 287    │ -1.4%  │ 44%    │ -$4,018    │ 🔴 UNFAVORABLE │ │ │
│  │  └────────┴────────┴────────┴────────┴────────────┴─────────────────┘ │ │
│  │                                                                        │ │
│  │  Validation:                                                           │ │
│  │  • Bootstrap Stability: 85% (Good)                                     │ │
│  │  • Time Consistency: 78% (Acceptable)                                  │ │
│  │  • P-values: 0-60 range p<0.01, 180-390 range p<0.05                  │ │
│  │                                                                        │ │
│  │  ⚠️ Warning: Feature correlated with 'gap_percent' (r=0.42)           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  Visualization                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │     EV by Range                    │    Trade Distribution            │ │
│  │   +3% │     ██                     │   500 │        ██                │ │
│  │   +2% │     ██                     │   400 │        ██                │ │
│  │   +1% │     ██  ▓▓                 │   300 │  ██    ██    ██          │ │
│  │    0% │─────██──▓▓─────            │   200 │  ██    ██    ██          │ │
│  │   -1% │         ▓▓  ░░             │   100 │  ██    ██    ██          │ │
│  │   -2% │             ░░             │     0 └──────────────────         │ │
│  │       └─────────────────           │         0-60 60-180 180+         │ │
│  │         0-60 60-180 180+           │                                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  [Apply as Filter]  [Export Results]  [Detailed Report]                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Key UI Features

1. **Impact Score Bar Chart**: Quick visual ranking of features
2. **Color-Coded Classifications**: Green (Favorable), Gray (Neutral), Red (Unfavorable)
3. **Confidence Indicators**: Clear display of statistical confidence
4. **Warning Badges**: Prominent display of any concerns
5. **One-Click Filter**: Apply favorable/unfavorable ranges directly to filter panel
6. **Detailed Report**: Exportable analysis for further review

---

## Lookahead Bias Prevention

### The Problem

Some columns in trade data are only known **after** the trade exits:

| Column Type | Examples | Why It's Lookahead |
|-------------|----------|-------------------|
| **Outcome columns** | `gain_pct`, `mae_pct`, `mfe_pct`, `win_loss` | These ARE the outcome - can't filter before trade |
| **Exit-time columns** | `close`, `exit_price`, `exit_time` | Only known when trade closes |
| **Post-trade metrics** | `holding_period`, `actual_slippage` | Calculated after exit |

Using these to identify "favorable ranges" is useless - you can't filter trades before entering them based on information you only have after exiting.

### Solution: User-Configured Column Exclusion

Simple and direct - you know your data best. The UI provides a checklist of all numeric columns, and you select which ones to exclude from analysis.

```python
@dataclass
class FeatureAnalyzerConfig:
    # ... existing fields ...
    
    # Column selection
    exclude_columns: set[str] = field(default_factory=set)  # User-specified exclusions
```

### UI Integration

Add a column selection panel in the Feature Insights tab:

```
┌─ Column Selection ─────────────────────────────────────────────────────────┐
│                                                                            │
│  Select columns to EXCLUDE from analysis:                                  │
│  (Exclude any columns with lookahead bias - data only known after exit)   │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ ☑ gain_pct            ☑ mae_pct             ☑ close                 │ │
│  │ ☑ exit_price          ☑ mfe_pct             ☑ holding_period        │ │
│  │ ☐ gap_percent         ☐ time_minutes        ☐ volume_ratio          │ │
│  │ ☐ atr_14              ☐ prev_close_dist     ☐ market_cap            │ │
│  │ ☐ float_shares        ☐ premarket_volume    ☐ relative_volume       │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  [Select All]  [Deselect All]  [Save as Default]                          │
└────────────────────────────────────────────────────────────────────────────┘
```

### Implementation

```python
class FeatureAnalyzer:
    def __init__(
        self,
        config: FeatureAnalyzerConfig,
        column_mapping: ColumnMapping,
    ):
        self.config = config
        self.column_mapping = column_mapping
    
    def get_analyzable_columns(self, df: pd.DataFrame) -> list[str]:
        """Get columns available for analysis (numeric, not excluded)."""
        analyzable = []
        
        for col in df.columns:
            # Skip user-excluded columns
            if col in self.config.exclude_columns:
                continue
            
            # Skip non-numeric columns
            if not pd.api.types.is_numeric_dtype(df[col]):
                continue
            
            analyzable.append(col)
        
        return analyzable
```

### Persistence

The exclusion list can be saved to the app's config so users don't have to re-select every time:

```python
# In app config/settings
feature_analysis_excluded_columns: list[str] = [
    "gain_pct", "mae_pct", "mfe_pct", "close", "exit_price", 
    "holding_period", "win_loss"
]
```

### Guidance for Users

When selecting columns to exclude, ask: **"Do I know this value BEFORE I enter the trade?"**

**Keep (don't exclude):**
- Pre-market data: `gap_percent`, `premarket_volume`
- Static fundamentals: `market_cap`, `float_shares`, `sector`
- Technical indicators at entry: `atr_14`, `rsi_14`
- Time-based: `time_minutes`, `day_of_week`

**Exclude:**
- Exit prices: `close`, `exit_price`
- Outcome metrics: `gain_pct`, `mae_pct`, `mfe_pct`, `pnl`
- Duration: `holding_period`, `bars_held`

---

## Dependencies and Performance

### Required Dependencies

```toml
# Add to pyproject.toml
dependencies = [
    # Existing...
    "scipy>=1.11.0",  # Already likely installed with pandas, but pin version
]
```

**Note**: The solution deliberately avoids sklearn/scikit-learn and other heavy ML libraries. All algorithms are implemented using scipy and numpy, which are already dependencies (pandas requires numpy).

### Performance Considerations

| Operation | Complexity | Typical Time (1000 trades, 20 features) |
|-----------|------------|----------------------------------------|
| Mutual Information (all features) | O(n * f * bins²) | ~200ms |
| Rank Correlation (all features) | O(n * f * log(n)) | ~50ms |
| Optimal Binning (per feature) | O(n * bins * merges) | ~100ms per feature |
| Bootstrap Validation (1000 iterations) | O(iterations * n) | ~2s per feature |
| **Total Analysis** | | **~5-10 seconds** |

### Caching Strategy

```python
# Cache analysis results keyed by:
# - DataFrame hash (content fingerprint)
# - Config hash
# - Gain column name
# - Feature columns included

cache_key = f"{df_hash}_{config_hash}_{gain_col}_{sorted(feature_cols)}"
```

---

## Implementation Roadmap

### Epic: Feature Insights Tab

#### Story 8.1: Core Feature Analyzer Engine

**Files:**
- Create: `src/core/feature_analyzer.py`
- Create: `tests/unit/test_feature_analyzer.py`

**Scope:**
- Implement `FeatureAnalyzerConfig`, `FeatureAnalysisResult`, `FeatureAnalyzerResults` dataclasses
- Implement `FeatureAnalyzer` class with:
  - `calculate_mutual_information()`
  - `calculate_rank_correlation()`
  - `calculate_conditional_variance()`
  - `calculate_impact_score()`
  - `find_optimal_bins()`
  - `analyze_bin()`
  - `run()` method that orchestrates all phases

**Acceptance Criteria:**
- Mutual information captures non-linear relationships
- Optimal binning respects minimum sample size
- Bootstrap confidence intervals are accurate
- All calculations complete in <10 seconds for typical datasets

#### Story 8.2: Validation and Confidence Metrics

**Files:**
- Modify: `src/core/feature_analyzer.py`
- Add: `tests/unit/test_feature_analyzer_validation.py`

**Scope:**
- Implement `calculate_bootstrap_stability()`
- Implement `calculate_time_consistency()`
- Implement statistical significance testing
- Add warning generation logic

**Acceptance Criteria:**
- Bootstrap stability correlates with classification reliability
- Time consistency check works with date column
- Warnings are generated for low confidence scenarios

#### Story 8.3: Feature Insights Tab UI

**Files:**
- Create: `src/tabs/feature_insights.py`
- Create: `src/ui/components/feature_impact_chart.py`
- Create: `src/ui/components/range_analysis_table.py`
- Modify: `src/ui/main_window.py`
- Add: `tests/widget/test_feature_insights_tab.py`

**Scope:**
- Create Feature Insights tab with configuration panel
- Implement feature ranking visualization (bar chart)
- Implement range analysis table with color coding
- Implement EV by range chart
- Implement trade distribution chart

**Acceptance Criteria:**
- Tab displays feature rankings sorted by impact score
- Range table clearly shows classifications with colors
- Charts update when different feature is selected
- All metrics displayed with confidence indicators

#### Story 8.4: Integration with Filters

**Files:**
- Modify: `src/tabs/feature_insights.py`
- Modify: `src/core/app_state.py`
- Modify: `src/ui/components/filter_panel.py`

**Scope:**
- "Apply as Filter" button creates filter criteria from selected ranges
- Integration with existing filter system
- Bidirectional sync (filters affect analysis data)

**Acceptance Criteria:**
- Clicking "Apply Favorable" creates appropriate filter
- Clicking "Exclude Unfavorable" creates appropriate filter
- Analysis updates when filtered_df changes (uses filtered data)

#### Story 8.5: Export and Reporting

**Files:**
- Modify: `src/tabs/feature_insights.py`
- Create: `src/core/feature_analyzer_export.py`

**Scope:**
- Export results to CSV/JSON
- Generate detailed report (markdown or PDF)
- Include all metrics, validations, and warnings

**Acceptance Criteria:**
- Export includes all feature analyses
- Report is human-readable with interpretations
- Export includes raw data for further analysis

---

## Appendix: Mathematical Foundations

### Why Mutual Information Works

Mutual Information I(X;Y) measures how much knowing X reduces uncertainty about Y:

```
I(X;Y) = H(Y) - H(Y|X)
```

Where:
- H(Y) is the entropy (uncertainty) of Y (gains)
- H(Y|X) is the conditional entropy of Y given X (feature)

**Key property**: MI captures ANY kind of relationship, not just linear. A feature that perfectly predicts gains in a non-linear way will have high MI but possibly low correlation.

### Why Bootstrap Validation Works

Bootstrap resampling approximates the sampling distribution of a statistic:

1. Original sample represents population
2. Resample with replacement many times
3. Calculate statistic on each resample
4. Distribution of resampled statistics approximates true sampling distribution

**For our use case**: If a classification changes frequently across bootstrap samples, we can't be confident it would hold with new data.

### Composite Scoring Rationale

The viability score balances EV advantage with sample size:

```
Score = (EV - baseline_EV) × √n × multiplier
```

Why √n? This mirrors the standard error formula where uncertainty decreases with √n. A range with 2x better EV but 1/4 the trades should score similarly to a range with average EV improvement but standard trades.

---

## Summary

This solution provides a robust, interpretable approach to feature analysis that:

1. **Avoids overfitting** by framing as statistical analysis, not prediction
2. **Considers practical viability** by incorporating trade count into all scores
3. **Provides actionable ranges** with clear favorable/unfavorable classifications
4. **Quantifies confidence** through bootstrap validation and statistical tests
5. **Integrates seamlessly** with existing Lumen architecture

The approach uses proven statistical methods while keeping implementation simple and dependencies light. Results are interpretable by non-technical users while providing detailed metrics for advanced analysis.

---

## Implementation Status

**Status: COMPLETE**

All stories from the implementation roadmap have been completed:

- **Story 8.1: Core Feature Analyzer Engine** - Complete
  - `src/core/feature_analyzer.py` implemented with all analysis functions
  - Unit tests in `tests/unit/test_feature_analyzer.py`

- **Story 8.2: Validation and Confidence Metrics** - Complete
  - Bootstrap stability and time consistency validation implemented
  - Statistical significance testing included
  - Warning generation for low-confidence scenarios

- **Story 8.3: Feature Insights Tab UI** - Complete
  - `src/tabs/feature_insights.py` with full configuration panel
  - `src/ui/components/feature_impact_chart.py` for impact visualization
  - `src/ui/components/range_analysis_table.py` for range display
  - Integration tests in `tests/integration/test_feature_insights.py`

- **Story 8.4: Integration with Filters** - Complete
  - "Apply Favorable Ranges as Filter" functionality implemented
  - Bidirectional sync with existing filter system

- **Final Polish** - Complete
  - Tooltips added to all key UI elements
  - User-friendly help text for lookahead bias prevention
  - Settings persistence for column exclusions
