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
        pnl_above: Total PnL (sum of gains) for trades above threshold.
        pnl_below: Total PnL (sum of gains) for trades at or below threshold.
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
    pnl_above: float
    pnl_below: float
    percentile_win_rates: list[float]


class FeatureImpactCalculator:
    """Calculates feature impact metrics using optimal threshold analysis.

    For each feature, finds the threshold that maximizes win rate difference
    between trades above and below that threshold.
    """

    NUM_PERCENTILE_BINS = 20

    # Default columns to exclude from analysis
    DEFAULT_EXCLUDED_COLS = {
        "date", "time", "ticker", "symbol", "gain_pct", "gain", "return",
        "trigger_number", "trade_id", "id", "index",
    }

    def calculate_all_features(
        self,
        df: pd.DataFrame,
        gain_col: str = "gain_pct",
        excluded_cols: list[str] | None = None,
    ) -> list[FeatureImpactResult]:
        """Calculate impact metrics for all numeric features.

        Args:
            df: DataFrame with trade data.
            gain_col: Name of the gain/return column.
            excluded_cols: Additional columns to exclude from analysis.

        Returns:
            List of FeatureImpactResult for each analyzed feature.
        """
        # Build exclusion set
        exclude_set = set(self.DEFAULT_EXCLUDED_COLS)
        if excluded_cols:
            exclude_set.update(col.lower() for col in excluded_cols)
        exclude_set.add(gain_col.lower())

        # Find numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        # Filter to analyzable features
        feature_cols = [
            col for col in numeric_cols
            if col.lower() not in exclude_set and col != gain_col
        ]

        logger.info(f"Analyzing {len(feature_cols)} features for impact")

        results = []
        for col in feature_cols:
            try:
                result = self.calculate_single_feature(df, col, gain_col)
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to analyze feature '{col}': {e}")

        return results

    def calculate_impact_scores(
        self,
        results: list[FeatureImpactResult],
        min_trades_threshold: int = 30,
    ) -> dict[str, float]:
        """Calculate composite impact scores for all results.

        Score formula:
            Base = 40% EV_lift + 20% WR_lift + 20% |correlation| + 20% sample_factor
            Final = Base × sample_penalty

        Sample penalty reduces score for small samples:
            penalty = min(1.0, trades_in_direction / min_trades_threshold)

        This prevents overfitting by penalizing features that only work
        on tiny subsets of the data.

        Args:
            results: List of FeatureImpactResult from calculate_all_features.
            min_trades_threshold: Minimum trades for full score (default 30).

        Returns:
            Dict mapping feature_name to impact score (0-1).
        """
        if not results:
            return {}

        # Extract metrics for normalization
        correlations = [abs(r.correlation) for r in results]
        wr_lifts = [r.win_rate_lift for r in results]
        ev_lifts = [r.expectancy_lift for r in results]

        # Get trades in the "good" direction for sample size factor
        def trades_in_direction(r: FeatureImpactResult) -> int:
            return r.trades_above if r.threshold_direction == "above" else r.trades_below

        trade_counts = [trades_in_direction(r) for r in results]

        # Normalize each metric to 0-1 range
        def normalize(values: list[float]) -> list[float]:
            if not values:
                return []
            min_val, max_val = min(values), max(values)
            if max_val == min_val:
                return [0.5] * len(values)
            return [(v - min_val) / (max_val - min_val) for v in values]

        norm_corr = normalize(correlations)
        norm_wr = normalize(wr_lifts)
        norm_ev = normalize(ev_lifts)
        norm_trades = normalize([float(t) for t in trade_counts])

        # Calculate composite scores with sample size penalty
        scores = {}
        for i, result in enumerate(results):
            # Base score includes sample size as positive factor
            base_score = (
                0.40 * norm_ev[i] +
                0.20 * norm_wr[i] +
                0.20 * norm_corr[i] +
                0.20 * norm_trades[i]
            )

            # Apply penalty for samples below threshold
            trades = trades_in_direction(result)
            sample_penalty = min(1.0, trades / min_trades_threshold)

            scores[result.feature_name] = base_score * sample_penalty

        return scores

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

        # Compute PnL for above/below threshold
        above_mask = feature_vals > threshold
        pnl_above = float(np.sum(gain_vals[above_mask]))
        pnl_below = float(np.sum(gain_vals[~above_mask]))

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
            pnl_above=pnl_above,
            pnl_below=pnl_below,
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
            pnl_above=0.0,
            pnl_below=0.0,
            percentile_win_rates=[50.0] * self.NUM_PERCENTILE_BINS,
        )
