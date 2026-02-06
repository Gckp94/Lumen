# src/core/feature_impact_calculator.py
"""Feature impact analysis calculator.

Computes correlation, optimal thresholds, and lift metrics for each feature
to help identify which features have the most predictive power.
"""

from dataclasses import dataclass


@dataclass
class FeatureImpactResult:
    """Results of feature impact analysis for a single feature.

    Attributes:
        feature_name: Name of the analyzed feature column.
        correlation: Pearson correlation with gain_pct.
        optimal_threshold: Value that maximizes win rate difference.
        threshold_direction: "above" or "below" - which side is better.
        win_rate_baseline: Overall win rate (%).
        win_rate_above: Win rate when feature > threshold (%).
        win_rate_below: Win rate when feature <= threshold (%).
        win_rate_lift: Improvement in win rate at optimal threshold (%).
        expectancy_baseline: Overall expected value.
        expectancy_above: EV when feature > threshold.
        expectancy_below: EV when feature <= threshold.
        expectancy_lift: Improvement in EV at optimal threshold.
        trades_above: Count of trades above threshold.
        trades_below: Count of trades at or below threshold.
        trades_total: Total trade count.
        percentile_win_rates: Win rates by percentile bins (for spark chart).
    """

    feature_name: str
    correlation: float
    optimal_threshold: float
    threshold_direction: str  # "above" or "below"
    win_rate_baseline: float
    win_rate_above: float
    win_rate_below: float
    win_rate_lift: float
    expectancy_baseline: float
    expectancy_above: float
    expectancy_below: float
    expectancy_lift: float
    trades_above: int
    trades_below: int
    trades_total: int
    percentile_win_rates: list[float]
