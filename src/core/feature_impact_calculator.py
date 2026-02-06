# src/core/feature_impact_calculator.py
"""Feature impact analysis calculator.

Computes correlation, optimal thresholds, and lift metrics for each feature
to help identify which features have the most predictive power.
"""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


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


class FeatureImpactCalculator:
    """Calculates feature impact metrics using optimal threshold analysis.

    For each feature, finds the threshold that maximizes win rate difference
    between trades above and below that threshold.
    """

    NUM_PERCENTILE_BINS = 20

    def calculate_single_feature(
        self,
        df: pd.DataFrame,
        feature_col: str,
        gain_col: str = "gain_pct",
    ) -> FeatureImpactResult:
        """Calculate impact metrics for a single feature.

        Args:
            df: DataFrame with trade data.
            feature_col: Name of the feature column to analyze.
            gain_col: Name of the gain/return column.

        Returns:
            FeatureImpactResult with all computed metrics.
        """
        # Drop rows with NaN in feature or gain columns
        valid_df = df[[feature_col, gain_col]].dropna()
        if len(valid_df) < 10:
            return self._empty_result(feature_col, len(valid_df))

        feature_vals = valid_df[feature_col].values
        gain_vals = valid_df[gain_col].values

        # Calculate correlation
        correlation = float(np.corrcoef(feature_vals, gain_vals)[0, 1])
        if np.isnan(correlation):
            correlation = 0.0

        # Calculate baseline metrics
        wins = gain_vals > 0
        win_rate_baseline = float(np.mean(wins) * 100)
        expectancy_baseline = float(np.mean(gain_vals))

        # Find optimal threshold
        threshold, direction, wr_above, wr_below, ev_above, ev_below, n_above, n_below = (
            self._find_optimal_threshold(feature_vals, gain_vals)
        )

        # Calculate lift (always positive - represents improvement)
        if direction == "above":
            win_rate_lift = wr_above - win_rate_baseline
            expectancy_lift = ev_above - expectancy_baseline
        else:
            win_rate_lift = wr_below - win_rate_baseline
            expectancy_lift = ev_below - expectancy_baseline

        # Calculate percentile win rates for spark chart
        percentile_win_rates = self._calculate_percentile_win_rates(
            feature_vals, gain_vals
        )

        return FeatureImpactResult(
            feature_name=feature_col,
            correlation=correlation,
            optimal_threshold=threshold,
            threshold_direction=direction,
            win_rate_baseline=win_rate_baseline,
            win_rate_above=wr_above,
            win_rate_below=wr_below,
            win_rate_lift=win_rate_lift,
            expectancy_baseline=expectancy_baseline,
            expectancy_above=ev_above,
            expectancy_below=ev_below,
            expectancy_lift=expectancy_lift,
            trades_above=n_above,
            trades_below=n_below,
            trades_total=len(valid_df),
            percentile_win_rates=percentile_win_rates,
        )

    def _find_optimal_threshold(
        self,
        feature_vals: np.ndarray,
        gain_vals: np.ndarray,
    ) -> tuple[float, str, float, float, float, float, int, int]:
        """Find threshold that maximizes win rate difference.

        Returns:
            Tuple of (threshold, direction, wr_above, wr_below,
                      ev_above, ev_below, n_above, n_below)
        """
        wins = gain_vals > 0

        # Get unique values sorted
        unique_vals = np.unique(feature_vals)
        if len(unique_vals) < 2:
            # No variation - return median
            med = float(np.median(feature_vals))
            wr = float(np.mean(wins) * 100)
            ev = float(np.mean(gain_vals))
            return (med, "above", wr, wr, ev, ev, len(gain_vals), 0)

        # Sample thresholds (use percentiles for efficiency on large datasets)
        if len(unique_vals) > 100:
            percentiles = np.percentile(feature_vals, np.linspace(5, 95, 50))
            thresholds = np.unique(percentiles)
        else:
            # Use midpoints between unique values
            thresholds = (unique_vals[:-1] + unique_vals[1:]) / 2

        best_threshold = thresholds[0]
        best_diff = 0.0
        best_direction = "above"
        best_stats = None

        for thresh in thresholds:
            above_mask = feature_vals > thresh
            below_mask = ~above_mask

            n_above = int(np.sum(above_mask))
            n_below = int(np.sum(below_mask))

            # Skip if either side has too few trades
            if n_above < 5 or n_below < 5:
                continue

            wr_above = float(np.mean(wins[above_mask]) * 100)
            wr_below = float(np.mean(wins[below_mask]) * 100)
            ev_above = float(np.mean(gain_vals[above_mask]))
            ev_below = float(np.mean(gain_vals[below_mask]))

            # Check both directions
            diff_above = wr_above - wr_below  # above is better
            diff_below = wr_below - wr_above  # below is better

            if diff_above > best_diff:
                best_diff = diff_above
                best_threshold = thresh
                best_direction = "above"
                best_stats = (wr_above, wr_below, ev_above, ev_below, n_above, n_below)

            if diff_below > best_diff:
                best_diff = diff_below
                best_threshold = thresh
                best_direction = "below"
                best_stats = (wr_above, wr_below, ev_above, ev_below, n_above, n_below)

        if best_stats is None:
            # Fallback to median
            med = float(np.median(feature_vals))
            above_mask = feature_vals > med
            wr_above = float(np.mean(wins[above_mask]) * 100) if np.any(above_mask) else 0
            wr_below = float(np.mean(wins[~above_mask]) * 100) if np.any(~above_mask) else 0
            ev_above = float(np.mean(gain_vals[above_mask])) if np.any(above_mask) else 0
            ev_below = float(np.mean(gain_vals[~above_mask])) if np.any(~above_mask) else 0
            return (
                med, "above", wr_above, wr_below, ev_above, ev_below,
                int(np.sum(above_mask)), int(np.sum(~above_mask))
            )

        return (best_threshold, best_direction, *best_stats)

    def _calculate_percentile_win_rates(
        self,
        feature_vals: np.ndarray,
        gain_vals: np.ndarray,
    ) -> list[float]:
        """Calculate win rates for each percentile bin.

        Returns:
            List of win rates for NUM_PERCENTILE_BINS bins.
        """
        wins = gain_vals > 0
        percentile_edges = np.percentile(
            feature_vals, np.linspace(0, 100, self.NUM_PERCENTILE_BINS + 1)
        )

        win_rates = []
        for i in range(self.NUM_PERCENTILE_BINS):
            low, high = percentile_edges[i], percentile_edges[i + 1]
            if i == self.NUM_PERCENTILE_BINS - 1:
                mask = (feature_vals >= low) & (feature_vals <= high)
            else:
                mask = (feature_vals >= low) & (feature_vals < high)

            if np.sum(mask) > 0:
                win_rates.append(float(np.mean(wins[mask]) * 100))
            else:
                win_rates.append(50.0)  # Default to 50% if no trades

        return win_rates

    def _empty_result(self, feature_name: str, n_trades: int) -> FeatureImpactResult:
        """Create an empty result for features with insufficient data."""
        return FeatureImpactResult(
            feature_name=feature_name,
            correlation=0.0,
            optimal_threshold=0.0,
            threshold_direction="above",
            win_rate_baseline=0.0,
            win_rate_above=0.0,
            win_rate_below=0.0,
            win_rate_lift=0.0,
            expectancy_baseline=0.0,
            expectancy_above=0.0,
            expectancy_below=0.0,
            expectancy_lift=0.0,
            trades_above=0,
            trades_below=0,
            trades_total=n_trades,
            percentile_win_rates=[50.0] * self.NUM_PERCENTILE_BINS,
        )
