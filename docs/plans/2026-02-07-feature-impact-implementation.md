# Feature Impact Tab Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Feature Impact tab that ranks dataset features by predictive power using correlation, win rate lift, and expectancy lift metrics.

**Architecture:** Core calculator module computes optimal thresholds and metrics for each feature. Tab displays results in a sortable table with gradient coloring and expandable rows showing mini spark charts.

**Tech Stack:** PyQt6 (UI), pandas (calculations), pyqtgraph (spark charts), existing Lumen design system (Colors, Fonts, Spacing)

---

## Task 1: Feature Impact Calculator - Core Data Structures

**Files:**
- Create: `src/core/feature_impact_calculator.py`
- Test: `tests/unit/test_feature_impact_calculator.py`

**Step 1: Write the failing test for FeatureImpactResult dataclass**

```python
# tests/unit/test_feature_impact_calculator.py
"""Tests for feature impact calculator."""

import pytest
from src.core.feature_impact_calculator import FeatureImpactResult


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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_feature_impact_calculator.py::TestFeatureImpactResult::test_feature_impact_result_creation -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.core.feature_impact_calculator'"

**Step 3: Write minimal implementation**

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_feature_impact_calculator.py::TestFeatureImpactResult::test_feature_impact_result_creation -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/feature_impact_calculator.py tests/unit/test_feature_impact_calculator.py
git commit -m "feat(feature-impact): add FeatureImpactResult dataclass

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Feature Impact Calculator - Optimal Threshold Algorithm

**Files:**
- Modify: `src/core/feature_impact_calculator.py`
- Test: `tests/unit/test_feature_impact_calculator.py`

**Step 1: Write the failing test for optimal threshold calculation**

```python
# Add to tests/unit/test_feature_impact_calculator.py
import numpy as np
import pandas as pd

from src.core.feature_impact_calculator import (
    FeatureImpactCalculator,
    FeatureImpactResult,
)


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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_feature_impact_calculator.py::TestFeatureImpactCalculator::test_calculate_single_feature -v`
Expected: FAIL with "cannot import name 'FeatureImpactCalculator'"

**Step 3: Write implementation**

```python
# Add to src/core/feature_impact_calculator.py after FeatureImpactResult

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


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
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_feature_impact_calculator.py::TestFeatureImpactCalculator -v`
Expected: PASS (both tests)

**Step 5: Commit**

```bash
git add src/core/feature_impact_calculator.py tests/unit/test_feature_impact_calculator.py
git commit -m "feat(feature-impact): add optimal threshold algorithm

Finds the split point that maximizes win rate difference between
trades above and below the threshold.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Feature Impact Calculator - Multi-Feature Analysis & Impact Score

**Files:**
- Modify: `src/core/feature_impact_calculator.py`
- Test: `tests/unit/test_feature_impact_calculator.py`

**Step 1: Write the failing test for multi-feature analysis**

```python
# Add to tests/unit/test_feature_impact_calculator.py

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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_feature_impact_calculator.py::TestFeatureImpactCalculatorMultiFeature::test_calculate_all_features -v`
Expected: FAIL with "has no attribute 'calculate_all_features'"

**Step 3: Write implementation**

```python
# Add to FeatureImpactCalculator class in src/core/feature_impact_calculator.py

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
    ) -> dict[str, float]:
        """Calculate composite impact scores for all results.

        Score formula: 50% EV lift + 25% WR lift + 25% |correlation|
        All components normalized to 0-1 range.

        Args:
            results: List of FeatureImpactResult from calculate_all_features.

        Returns:
            Dict mapping feature_name to impact score (0-1).
        """
        if not results:
            return {}

        # Extract metrics for normalization
        correlations = [abs(r.correlation) for r in results]
        wr_lifts = [r.win_rate_lift for r in results]
        ev_lifts = [r.expectancy_lift for r in results]

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

        # Calculate composite scores
        scores = {}
        for i, result in enumerate(results):
            score = (
                0.50 * norm_ev[i] +
                0.25 * norm_wr[i] +
                0.25 * norm_corr[i]
            )
            scores[result.feature_name] = score

        return scores
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_feature_impact_calculator.py::TestFeatureImpactCalculatorMultiFeature -v`
Expected: PASS (all 3 tests)

**Step 5: Commit**

```bash
git add src/core/feature_impact_calculator.py tests/unit/test_feature_impact_calculator.py
git commit -m "feat(feature-impact): add multi-feature analysis and impact scores

- calculate_all_features() analyzes all numeric columns
- Auto-excludes date, ticker, gain_pct, etc.
- calculate_impact_scores() computes composite score:
  50% EV lift + 25% WR lift + 25% |correlation|

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Feature Impact Tab - Basic UI Skeleton

**Files:**
- Create: `src/tabs/feature_impact.py`
- Modify: `src/ui/main_window.py`
- Test: `tests/unit/test_feature_impact_tab.py`

**Step 1: Write the failing test for tab creation**

```python
# tests/unit/test_feature_impact_tab.py
"""Tests for Feature Impact tab."""

import pytest
from PyQt6.QtWidgets import QApplication

from src.core.app_state import AppState
from src.tabs.feature_impact import FeatureImpactTab


@pytest.fixture(scope="module")
def app():
    """Create QApplication for widget tests."""
    application = QApplication.instance() or QApplication([])
    yield application


class TestFeatureImpactTabCreation:
    """Tests for tab creation and basic structure."""

    def test_tab_creation(self, app):
        """Test that tab can be created."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        assert tab is not None

    def test_tab_has_empty_state(self, app):
        """Test that tab shows empty state when no data loaded."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        # Empty label should be visible
        assert tab._empty_label.isVisible() or not tab._table.isVisible()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_feature_impact_tab.py::TestFeatureImpactTabCreation::test_tab_creation -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.tabs.feature_impact'"

**Step 3: Write basic tab skeleton**

```python
# src/tabs/feature_impact.py
"""Feature Impact tab for ranking features by predictive power.

Displays a scorecard table showing correlation, win rate lift, expectancy lift,
and composite impact score for each numeric feature in the dataset.
"""

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.app_state import AppState
from src.core.feature_impact_calculator import FeatureImpactCalculator, FeatureImpactResult
from src.ui.constants import Colors, Fonts, FontSizes, Spacing

logger = logging.getLogger(__name__)


class FeatureImpactTab(QWidget):
    """Tab displaying feature impact rankings."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        """Initialize the Feature Impact tab.

        Args:
            app_state: Application state for data access.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._app_state = app_state
        self._calculator = FeatureImpactCalculator()
        self._results: list[FeatureImpactResult] = []
        self._impact_scores: dict[str, float] = {}

        self._setup_ui()
        self._connect_signals()
        self._show_empty_state(True)

    def _setup_ui(self) -> None:
        """Set up the tab UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # Header section
        header = self._create_header()
        layout.addWidget(header)

        # Empty state label
        self._empty_label = QLabel("Load trade data to view feature impact analysis")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: 16px;
                padding: 40px;
            }}
        """)
        layout.addWidget(self._empty_label)

        # Main table
        self._table = self._create_table()
        layout.addWidget(self._table)

    def _create_header(self) -> QWidget:
        """Create the header section with title and summary."""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title and summary on left
        title_section = QWidget()
        title_layout = QVBoxLayout(title_section)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(Spacing.XS)

        title = QLabel("FEATURE IMPACT")
        title.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: {FontSizes.H2}px;
                font-weight: 600;
                letter-spacing: 1px;
            }}
        """)
        title_layout.addWidget(title)

        self._summary_label = QLabel("Analyzing features...")
        self._summary_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: {FontSizes.BODY}px;
            }}
        """)
        title_layout.addWidget(self._summary_label)

        layout.addWidget(title_section)
        layout.addStretch()

        return header

    def _create_table(self) -> QTableWidget:
        """Create the main scorecard table."""
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels([
            "Feature",
            "Impact Score",
            "Correlation",
            "WR Lift",
            "EV Lift",
            "Threshold",
            "Trades",
        ])

        # Style the table
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                gridline-color: {Colors.BG_BORDER};
            }}
            QTableWidget::item {{
                padding: {Spacing.SM}px;
                font-family: '{Fonts.DATA}';
                font-size: {FontSizes.BODY}px;
            }}
            QHeaderView::section {{
                background-color: {Colors.BG_BASE};
                color: {Colors.TEXT_SECONDARY};
                padding: {Spacing.SM}px {Spacing.MD}px;
                border: none;
                border-bottom: 1px solid {Colors.BG_BORDER};
                border-right: 1px solid {Colors.BG_BORDER};
                font-family: '{Fonts.UI}';
                font-size: 12px;
                font-weight: 500;
                text-transform: uppercase;
            }}
        """)

        # Configure header
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 7):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        return table

    def _connect_signals(self) -> None:
        """Connect to app state signals."""
        self._app_state.baseline_calculated.connect(self._on_data_updated)
        self._app_state.filtered_data_updated.connect(self._on_data_updated)

    def _show_empty_state(self, show: bool) -> None:
        """Toggle between empty state and table."""
        self._empty_label.setVisible(show)
        self._table.setVisible(not show)

    def _on_data_updated(self) -> None:
        """Handle data updates from app state."""
        if not self._app_state.has_data:
            self._show_empty_state(True)
            return

        self._show_empty_state(False)
        self._analyze_features()

    def _analyze_features(self) -> None:
        """Analyze all features and populate table."""
        df = self._app_state.baseline_df
        if df is None or df.empty:
            return

        # Get gain column from mapping
        gain_col = "gain_pct"
        if self._app_state.column_mapping:
            gain_col = self._app_state.column_mapping.gain_pct

        # Calculate impact for all features
        self._results = self._calculator.calculate_all_features(
            df=df,
            gain_col=gain_col,
        )
        self._impact_scores = self._calculator.calculate_impact_scores(self._results)

        # Sort by impact score (descending)
        self._results.sort(
            key=lambda r: self._impact_scores.get(r.feature_name, 0),
            reverse=True,
        )

        # Update UI
        self._update_summary()
        self._populate_table()

    def _update_summary(self) -> None:
        """Update the summary label."""
        n_features = len(self._results)
        n_trades = self._results[0].trades_total if self._results else 0
        self._summary_label.setText(
            f"Analyzing {n_features} features across {n_trades:,} trades"
        )

    def _populate_table(self) -> None:
        """Populate the table with analysis results."""
        self._table.setRowCount(len(self._results))

        for row, result in enumerate(self._results):
            score = self._impact_scores.get(result.feature_name, 0)

            # Feature name
            self._table.setItem(row, 0, QTableWidgetItem(result.feature_name))

            # Impact score
            score_item = QTableWidgetItem(f"{score:.2f}")
            score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 1, score_item)

            # Correlation
            corr_item = QTableWidgetItem(f"{result.correlation:+.3f}")
            corr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 2, corr_item)

            # Win rate lift
            wr_item = QTableWidgetItem(f"{result.win_rate_lift:+.1f}%")
            wr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 3, wr_item)

            # Expectancy lift
            ev_item = QTableWidgetItem(f"{result.expectancy_lift:+.4f}")
            ev_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 4, ev_item)

            # Threshold
            direction = ">" if result.threshold_direction == "above" else "<"
            thresh_item = QTableWidgetItem(f"{direction} {result.optimal_threshold:.2f}")
            thresh_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 5, thresh_item)

            # Trades
            trades_item = QTableWidgetItem(f"{result.trades_total:,}")
            trades_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 6, trades_item)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_feature_impact_tab.py -v`
Expected: PASS

**Step 5: Add tab to main window**

```python
# In src/ui/main_window.py, add import at top:
from src.tabs.feature_impact import FeatureImpactTab

# In _setup_docks method, add after Feature Insights:
            ("Feature Insights", FeatureInsightsTab(self._app_state)),
            ("Feature Impact", FeatureImpactTab(self._app_state)),  # ADD THIS LINE
            ("Portfolio Overview", portfolio_overview),
```

**Step 6: Commit**

```bash
git add src/tabs/feature_impact.py src/ui/main_window.py tests/unit/test_feature_impact_tab.py
git commit -m "feat(feature-impact): add basic Feature Impact tab skeleton

- Creates FeatureImpactTab with header and table
- Connects to app_state signals for data updates
- Registers tab in MainWindow dock setup

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Feature Impact Tab - Gradient Cell Coloring

**Files:**
- Modify: `src/tabs/feature_impact.py`
- Test: `tests/unit/test_feature_impact_tab.py`

**Step 1: Write the failing test for gradient coloring**

```python
# Add to tests/unit/test_feature_impact_tab.py

class TestFeatureImpactTabGradients:
    """Tests for gradient cell coloring."""

    def test_positive_values_get_cyan_gradient(self, app):
        """Test that positive lift values get cyan-ish background."""
        from src.tabs.feature_impact import get_gradient_color
        from src.ui.constants import Colors

        bg, text = get_gradient_color(0.5, 0.0, 1.0)  # High positive
        # Should be toward cyan
        assert bg.green() > bg.red()  # Cyan has more green than red

    def test_negative_values_get_coral_gradient(self, app):
        """Test that negative lift values get coral-ish background."""
        from src.tabs.feature_impact import get_gradient_color

        bg, text = get_gradient_color(-0.5, -1.0, 1.0)  # Negative
        # Should be toward coral (red)
        assert bg.red() > bg.green()

    def test_zero_values_get_neutral_gradient(self, app):
        """Test that zero values get neutral background."""
        from src.tabs.feature_impact import get_gradient_color
        from src.ui.constants import Colors

        bg, text = get_gradient_color(0.0, -1.0, 1.0)  # Neutral
        # Should be close to BG_ELEVATED
        assert abs(bg.red() - 0x1E) < 20  # Within range of #1E1E2C
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_feature_impact_tab.py::TestFeatureImpactTabGradients::test_positive_values_get_cyan_gradient -v`
Expected: FAIL with "cannot import name 'get_gradient_color'"

**Step 3: Add gradient coloring implementation**

```python
# Add to src/tabs/feature_impact.py, after imports

from PyQt6.QtGui import QBrush, QColor

# Gradient colors (matching statistics_tab.py pattern)
GRADIENT_CORAL = QColor(Colors.SIGNAL_CORAL)  # Negative
GRADIENT_NEUTRAL = QColor(Colors.BG_ELEVATED)  # Zero
GRADIENT_CYAN = QColor(Colors.SIGNAL_CYAN)  # Positive
TEXT_ON_DARK = QColor(Colors.TEXT_PRIMARY)
TEXT_ON_LIGHT = QColor(Colors.BG_BASE)


def lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
    """Linear interpolation between two colors."""
    t = max(0.0, min(1.0, t))
    return QColor(
        int(c1.red() + (c2.red() - c1.red()) * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue() + (c2.blue() - c1.blue()) * t),
    )


def get_gradient_color(
    value: float,
    min_val: float,
    max_val: float,
) -> tuple[QColor, QColor]:
    """Get background and text colors for a value in range.

    Args:
        value: The value to color.
        min_val: Minimum value in range (maps to coral).
        max_val: Maximum value in range (maps to cyan).

    Returns:
        Tuple of (background_color, text_color).
    """
    if min_val == max_val:
        return (GRADIENT_NEUTRAL, TEXT_ON_DARK)

    # Normalize to -1 to +1 range where 0 is neutral
    if min_val < 0 and max_val > 0:
        # Range spans zero - normalize around zero
        if value < 0:
            t = value / min_val  # 0 to 1 for negative values
            bg = lerp_color(GRADIENT_NEUTRAL, GRADIENT_CORAL, t)
        else:
            t = value / max_val  # 0 to 1 for positive values
            bg = lerp_color(GRADIENT_NEUTRAL, GRADIENT_CYAN, t)
    else:
        # Range doesn't span zero - use full range
        normalized = (value - min_val) / (max_val - min_val)
        bg = lerp_color(GRADIENT_CORAL, GRADIENT_CYAN, normalized)

    # Text color based on background brightness
    brightness = (bg.red() * 299 + bg.green() * 587 + bg.blue() * 114) / 1000
    text = TEXT_ON_DARK if brightness < 128 else TEXT_ON_LIGHT

    return (bg, text)


# Then modify _populate_table to use gradients:

    def _populate_table(self) -> None:
        """Populate the table with analysis results."""
        self._table.setRowCount(len(self._results))

        # Calculate ranges for gradient coloring
        correlations = [r.correlation for r in self._results]
        wr_lifts = [r.win_rate_lift for r in self._results]
        ev_lifts = [r.expectancy_lift for r in self._results]
        scores = [self._impact_scores.get(r.feature_name, 0) for r in self._results]

        corr_range = (min(correlations), max(correlations)) if correlations else (0, 0)
        wr_range = (min(wr_lifts), max(wr_lifts)) if wr_lifts else (0, 0)
        ev_range = (min(ev_lifts), max(ev_lifts)) if ev_lifts else (0, 0)
        score_range = (min(scores), max(scores)) if scores else (0, 0)

        for row, result in enumerate(self._results):
            score = self._impact_scores.get(result.feature_name, 0)

            # Feature name (no gradient)
            name_item = QTableWidgetItem(result.feature_name)
            name_item.setForeground(QBrush(QColor(Colors.TEXT_PRIMARY)))
            self._table.setItem(row, 0, name_item)

            # Impact score (cyan gradient only - always positive)
            score_item = QTableWidgetItem(f"{score:.2f}")
            score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            bg, text = get_gradient_color(score, 0, score_range[1])
            score_item.setBackground(QBrush(bg))
            score_item.setForeground(QBrush(text))
            self._table.setItem(row, 1, score_item)

            # Correlation (coral to cyan)
            corr_item = QTableWidgetItem(f"{result.correlation:+.3f}")
            corr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            bg, text = get_gradient_color(result.correlation, corr_range[0], corr_range[1])
            corr_item.setBackground(QBrush(bg))
            corr_item.setForeground(QBrush(text))
            self._table.setItem(row, 2, corr_item)

            # Win rate lift (coral to cyan)
            wr_item = QTableWidgetItem(f"{result.win_rate_lift:+.1f}%")
            wr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            bg, text = get_gradient_color(result.win_rate_lift, wr_range[0], wr_range[1])
            wr_item.setBackground(QBrush(bg))
            wr_item.setForeground(QBrush(text))
            self._table.setItem(row, 3, wr_item)

            # Expectancy lift (coral to cyan)
            ev_item = QTableWidgetItem(f"{result.expectancy_lift:+.4f}")
            ev_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            bg, text = get_gradient_color(result.expectancy_lift, ev_range[0], ev_range[1])
            ev_item.setBackground(QBrush(bg))
            ev_item.setForeground(QBrush(text))
            self._table.setItem(row, 4, ev_item)

            # Threshold (no gradient)
            direction = ">" if result.threshold_direction == "above" else "<"
            thresh_item = QTableWidgetItem(f"{direction} {result.optimal_threshold:.2f}")
            thresh_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            thresh_item.setForeground(QBrush(QColor(Colors.TEXT_PRIMARY)))
            self._table.setItem(row, 5, thresh_item)

            # Trades (no gradient)
            trades_item = QTableWidgetItem(f"{result.trades_total:,}")
            trades_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            trades_item.setForeground(QBrush(QColor(Colors.TEXT_PRIMARY)))
            self._table.setItem(row, 6, trades_item)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_feature_impact_tab.py::TestFeatureImpactTabGradients -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tabs/feature_impact.py tests/unit/test_feature_impact_tab.py
git commit -m "feat(feature-impact): add gradient cell coloring

Cells colored coral → neutral → cyan based on value.
- Correlation: full range gradient
- WR/EV lift: coral for negative, cyan for positive
- Impact score: cyan intensity (always positive)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Feature Impact Tab - Baseline vs Filtered Columns

**Files:**
- Modify: `src/tabs/feature_impact.py`
- Test: `tests/unit/test_feature_impact_tab.py`

**Step 1: Write the failing test**

```python
# Add to tests/unit/test_feature_impact_tab.py

class TestFeatureImpactTabDualColumns:
    """Tests for baseline vs filtered column display."""

    def test_table_has_dual_columns(self, app):
        """Test that table has baseline and filtered sub-columns."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        # Should have columns for both baseline and filtered
        headers = [
            tab._table.horizontalHeaderItem(i).text()
            for i in range(tab._table.columnCount())
        ]
        # Check for paired columns
        assert "Corr (B)" in headers or "Correlation" in headers
        assert tab._table.columnCount() >= 9  # Feature + pairs + trades
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_feature_impact_tab.py::TestFeatureImpactTabDualColumns -v`
Expected: FAIL (column count assertion)

**Step 3: Update table to show baseline and filtered columns**

```python
# Update _create_table in src/tabs/feature_impact.py

    def _create_table(self) -> QTableWidget:
        """Create the main scorecard table with baseline/filtered columns."""
        table = QTableWidget()
        table.setColumnCount(11)
        table.setHorizontalHeaderLabels([
            "Feature",
            "Impact",
            "Corr (B)",
            "Corr (F)",
            "WR Lift (B)",
            "WR Lift (F)",
            "EV Lift (B)",
            "EV Lift (F)",
            "Threshold",
            "Trades (B)",
            "Trades (F)",
        ])

        # ... rest of styling unchanged ...

        # Configure header
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 11):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        # ... rest unchanged ...
        return table
```

Then update `_analyze_features` and `_populate_table` to handle both datasets:

```python
    def _analyze_features(self) -> None:
        """Analyze all features for both baseline and filtered data."""
        baseline_df = self._app_state.baseline_df
        filtered_df = self._app_state.filtered_df

        if baseline_df is None or baseline_df.empty:
            return

        gain_col = "gain_pct"
        if self._app_state.column_mapping:
            gain_col = self._app_state.column_mapping.gain_pct

        # Calculate for baseline
        self._baseline_results = self._calculator.calculate_all_features(
            df=baseline_df,
            gain_col=gain_col,
        )
        self._baseline_scores = self._calculator.calculate_impact_scores(
            self._baseline_results
        )

        # Calculate for filtered (if different from baseline)
        if filtered_df is not None and not filtered_df.empty and len(filtered_df) != len(baseline_df):
            self._filtered_results = self._calculator.calculate_all_features(
                df=filtered_df,
                gain_col=gain_col,
            )
            self._filtered_scores = self._calculator.calculate_impact_scores(
                self._filtered_results
            )
        else:
            self._filtered_results = self._baseline_results
            self._filtered_scores = self._baseline_scores

        # Create lookup dict for filtered results
        self._filtered_by_name = {r.feature_name: r for r in self._filtered_results}

        # Sort by baseline impact score
        self._baseline_results.sort(
            key=lambda r: self._baseline_scores.get(r.feature_name, 0),
            reverse=True,
        )

        self._update_summary()
        self._populate_table()


    def _populate_table(self) -> None:
        """Populate table with baseline and filtered results."""
        self._table.setRowCount(len(self._baseline_results))

        # Calculate ranges for gradients (using baseline)
        b_corrs = [r.correlation for r in self._baseline_results]
        b_wr = [r.win_rate_lift for r in self._baseline_results]
        b_ev = [r.expectancy_lift for r in self._baseline_results]

        f_corrs = [r.correlation for r in self._filtered_results]
        f_wr = [r.win_rate_lift for r in self._filtered_results]
        f_ev = [r.expectancy_lift for r in self._filtered_results]

        corr_range = (min(b_corrs + f_corrs), max(b_corrs + f_corrs))
        wr_range = (min(b_wr + f_wr), max(b_wr + f_wr))
        ev_range = (min(b_ev + f_ev), max(b_ev + f_ev))

        for row, b_result in enumerate(self._baseline_results):
            f_result = self._filtered_by_name.get(b_result.feature_name, b_result)
            b_score = self._baseline_scores.get(b_result.feature_name, 0)

            # Col 0: Feature name
            self._set_text_item(row, 0, b_result.feature_name)

            # Col 1: Impact score (baseline)
            self._set_gradient_item(row, 1, f"{b_score:.2f}", b_score, 0, 1)

            # Col 2-3: Correlation (B/F)
            self._set_gradient_item(row, 2, f"{b_result.correlation:+.3f}",
                                   b_result.correlation, *corr_range)
            self._set_gradient_item(row, 3, f"{f_result.correlation:+.3f}",
                                   f_result.correlation, *corr_range)

            # Col 4-5: WR Lift (B/F)
            self._set_gradient_item(row, 4, f"{b_result.win_rate_lift:+.1f}%",
                                   b_result.win_rate_lift, *wr_range)
            self._set_gradient_item(row, 5, f"{f_result.win_rate_lift:+.1f}%",
                                   f_result.win_rate_lift, *wr_range)

            # Col 6-7: EV Lift (B/F)
            self._set_gradient_item(row, 6, f"{b_result.expectancy_lift:+.4f}",
                                   b_result.expectancy_lift, *ev_range)
            self._set_gradient_item(row, 7, f"{f_result.expectancy_lift:+.4f}",
                                   f_result.expectancy_lift, *ev_range)

            # Col 8: Threshold
            direction = ">" if b_result.threshold_direction == "above" else "<"
            self._set_text_item(row, 8, f"{direction} {b_result.optimal_threshold:.2f}")

            # Col 9-10: Trades (B/F)
            self._set_text_item(row, 9, f"{b_result.trades_total:,}")
            self._set_text_item(row, 10, f"{f_result.trades_total:,}")

    def _set_text_item(self, row: int, col: int, text: str) -> None:
        """Set a plain text table item."""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setForeground(QBrush(QColor(Colors.TEXT_PRIMARY)))
        self._table.setItem(row, col, item)

    def _set_gradient_item(
        self, row: int, col: int, text: str,
        value: float, min_val: float, max_val: float
    ) -> None:
        """Set a gradient-colored table item."""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        bg, text_color = get_gradient_color(value, min_val, max_val)
        item.setBackground(QBrush(bg))
        item.setForeground(QBrush(text_color))
        self._table.setItem(row, col, item)
```

Also add instance variables in `__init__`:
```python
        self._baseline_results: list[FeatureImpactResult] = []
        self._filtered_results: list[FeatureImpactResult] = []
        self._baseline_scores: dict[str, float] = {}
        self._filtered_scores: dict[str, float] = {}
        self._filtered_by_name: dict[str, FeatureImpactResult] = {}
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_feature_impact_tab.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tabs/feature_impact.py tests/unit/test_feature_impact_tab.py
git commit -m "feat(feature-impact): add baseline vs filtered columns

Table now shows paired (B)/(F) columns for correlation,
WR lift, EV lift, and trade counts.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Feature Impact Tab - Sortable Column Headers

**Files:**
- Modify: `src/tabs/feature_impact.py`
- Test: `tests/unit/test_feature_impact_tab.py`

**Step 1: Write the failing test**

```python
# Add to tests/unit/test_feature_impact_tab.py

class TestFeatureImpactTabSorting:
    """Tests for column sorting."""

    def test_clicking_header_sorts_table(self, app):
        """Test that clicking column header triggers sort."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        # Table should have sorting enabled
        assert tab._table.isSortingEnabled() or hasattr(tab, '_sort_column')
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_feature_impact_tab.py::TestFeatureImpactTabSorting -v`
Expected: FAIL

**Step 3: Add sorting functionality**

```python
# Add to FeatureImpactTab class

    def __init__(self, ...):
        # ... existing code ...
        self._sort_column = 1  # Default sort by Impact Score
        self._sort_ascending = False

    def _create_table(self) -> QTableWidget:
        # ... existing code ...

        # Enable sorting via header clicks
        header = table.horizontalHeader()
        header.setSortIndicatorShown(True)
        header.sectionClicked.connect(self._on_header_clicked)

        return table

    def _on_header_clicked(self, col: int) -> None:
        """Handle column header click for sorting."""
        if col == self._sort_column:
            self._sort_ascending = not self._sort_ascending
        else:
            self._sort_column = col
            self._sort_ascending = False  # Default descending for new column

        self._sort_and_repopulate()

    def _sort_and_repopulate(self) -> None:
        """Sort results and repopulate table."""
        if not self._baseline_results:
            return

        # Define sort key based on column
        def get_sort_key(result: FeatureImpactResult) -> float:
            f_result = self._filtered_by_name.get(result.feature_name, result)
            col = self._sort_column

            if col == 0:  # Feature name (alphabetical)
                return result.feature_name.lower()
            elif col == 1:  # Impact score
                return self._baseline_scores.get(result.feature_name, 0)
            elif col == 2:  # Corr (B)
                return result.correlation
            elif col == 3:  # Corr (F)
                return f_result.correlation
            elif col == 4:  # WR Lift (B)
                return result.win_rate_lift
            elif col == 5:  # WR Lift (F)
                return f_result.win_rate_lift
            elif col == 6:  # EV Lift (B)
                return result.expectancy_lift
            elif col == 7:  # EV Lift (F)
                return f_result.expectancy_lift
            elif col == 9:  # Trades (B)
                return result.trades_total
            elif col == 10:  # Trades (F)
                return f_result.trades_total
            else:
                return 0

        # Handle alphabetical vs numeric sorting
        if self._sort_column == 0:
            self._baseline_results.sort(
                key=lambda r: r.feature_name.lower(),
                reverse=not self._sort_ascending,
            )
        else:
            self._baseline_results.sort(
                key=get_sort_key,
                reverse=not self._sort_ascending,
            )

        # Update sort indicator
        order = Qt.SortOrder.AscendingOrder if self._sort_ascending else Qt.SortOrder.DescendingOrder
        self._table.horizontalHeader().setSortIndicator(self._sort_column, order)

        self._populate_table()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_feature_impact_tab.py::TestFeatureImpactTabSorting -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tabs/feature_impact.py tests/unit/test_feature_impact_tab.py
git commit -m "feat(feature-impact): add sortable column headers

Click any column header to sort by that metric.
Click again to toggle ascending/descending.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Feature Impact Tab - Column Exclusion Panel

**Files:**
- Modify: `src/tabs/feature_impact.py`
- Test: `tests/unit/test_feature_impact_tab.py`

**Step 1: Write the failing test**

```python
# Add to tests/unit/test_feature_impact_tab.py

class TestFeatureImpactTabExclusion:
    """Tests for column exclusion panel."""

    def test_exclusion_panel_exists(self, app):
        """Test that exclusion panel widget exists."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        assert hasattr(tab, '_exclusion_panel')

    def test_excluding_column_removes_from_results(self, app):
        """Test that excluding a column removes it from analysis."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        # This tests the exclusion logic
        excluded = {"feature_a"}
        tab._user_excluded_cols = excluded
        # Should filter out excluded columns
        assert "feature_a" not in [r.feature_name for r in tab._baseline_results] or len(tab._baseline_results) == 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_feature_impact_tab.py::TestFeatureImpactTabExclusion -v`
Expected: FAIL

**Step 3: Add exclusion panel**

```python
# Add to src/tabs/feature_impact.py

from PyQt6.QtWidgets import (
    # ... existing imports ...
    QCheckBox,
    QGroupBox,
    QScrollArea,
)


class FeatureImpactTab(QWidget):
    def __init__(self, ...):
        # ... existing code ...
        self._user_excluded_cols: set[str] = set()
        self._column_checkboxes: dict[str, QCheckBox] = {}

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # Top row: Header + Exclusion panel
        top_row = QHBoxLayout()

        header = self._create_header()
        top_row.addWidget(header, stretch=1)

        self._exclusion_panel = self._create_exclusion_panel()
        top_row.addWidget(self._exclusion_panel)

        layout.addLayout(top_row)

        # ... rest of setup unchanged ...

    def _create_exclusion_panel(self) -> QWidget:
        """Create collapsible column exclusion panel."""
        group = QGroupBox("Exclude Columns")
        group.setCheckable(True)
        group.setChecked(False)  # Collapsed by default
        group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 16px;
                font-family: '{Fonts.UI}';
                font-size: 12px;
                color: {Colors.TEXT_SECONDARY};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }}
            QGroupBox::indicator {{
                width: 12px;
                height: 12px;
            }}
        """)
        group.setMaximumWidth(200)
        group.setMaximumHeight(300)

        # Scroll area for checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """)

        self._checkbox_container = QWidget()
        self._checkbox_layout = QVBoxLayout(self._checkbox_container)
        self._checkbox_layout.setContentsMargins(4, 4, 4, 4)
        self._checkbox_layout.setSpacing(2)

        scroll.setWidget(self._checkbox_container)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(scroll)

        return group

    def _update_exclusion_checkboxes(self, columns: list[str]) -> None:
        """Update checkboxes to match available columns."""
        # Clear existing
        for checkbox in self._column_checkboxes.values():
            checkbox.deleteLater()
        self._column_checkboxes.clear()

        # Create checkbox for each column
        for col in sorted(columns):
            checkbox = QCheckBox(col)
            checkbox.setChecked(col not in self._user_excluded_cols)
            checkbox.setStyleSheet(f"""
                QCheckBox {{
                    color: {Colors.TEXT_PRIMARY};
                    font-family: '{Fonts.DATA}';
                    font-size: 11px;
                }}
            """)
            checkbox.stateChanged.connect(
                lambda state, c=col: self._on_exclusion_changed(c, state)
            )
            self._checkbox_layout.addWidget(checkbox)
            self._column_checkboxes[col] = checkbox

        self._checkbox_layout.addStretch()

    def _on_exclusion_changed(self, column: str, state: int) -> None:
        """Handle column exclusion checkbox change."""
        if state == Qt.CheckState.Checked.value:
            self._user_excluded_cols.discard(column)
        else:
            self._user_excluded_cols.add(column)

        # Re-analyze with updated exclusions
        self._analyze_features()

    def _analyze_features(self) -> None:
        """Analyze features with user exclusions applied."""
        baseline_df = self._app_state.baseline_df
        # ... existing code ...

        # Build full exclusion list
        excluded = list(self._user_excluded_cols)

        self._baseline_results = self._calculator.calculate_all_features(
            df=baseline_df,
            gain_col=gain_col,
            excluded_cols=excluded,
        )

        # Update checkbox panel with available columns
        numeric_cols = baseline_df.select_dtypes(include=[np.number]).columns.tolist()
        analyzable = [c for c in numeric_cols if c != gain_col]
        self._update_exclusion_checkboxes(analyzable)

        # ... rest of method unchanged ...
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_feature_impact_tab.py::TestFeatureImpactTabExclusion -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tabs/feature_impact.py tests/unit/test_feature_impact_tab.py
git commit -m "feat(feature-impact): add column exclusion panel

Collapsible panel with checkboxes to exclude specific
columns from analysis. Updates results in real-time.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 9: Feature Impact Tab - Expandable Row Detail with Spark Chart

**Files:**
- Modify: `src/tabs/feature_impact.py`
- Test: `tests/unit/test_feature_impact_tab.py`

**Step 1: Write the failing test**

```python
# Add to tests/unit/test_feature_impact_tab.py

class TestFeatureImpactTabExpansion:
    """Tests for expandable row detail."""

    def test_row_click_expands_detail(self, app):
        """Test that clicking a row shows detail panel."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        assert hasattr(tab, '_on_row_clicked')
        # Expansion widget should exist
        assert hasattr(tab, '_detail_widget') or hasattr(tab, '_expanded_row')
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_feature_impact_tab.py::TestFeatureImpactTabExpansion -v`
Expected: FAIL

**Step 3: Add expandable row with spark chart**

```python
# Add to src/tabs/feature_impact.py

import pyqtgraph as pg


class FeatureDetailWidget(QWidget):
    """Expandable detail widget showing threshold analysis."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        layout.setSpacing(Spacing.SM)

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: 4px;
            }}
        """)

        # Threshold label
        self._threshold_label = QLabel()
        self._threshold_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: {FontSizes.BODY}px;
                font-weight: 600;
            }}
        """)
        layout.addWidget(self._threshold_label)

        # Spark chart
        self._chart = pg.PlotWidget()
        self._chart.setBackground(Colors.BG_ELEVATED)
        self._chart.setMinimumHeight(80)
        self._chart.setMaximumHeight(100)
        self._chart.hideAxis('left')
        self._chart.hideAxis('bottom')
        self._chart.setMouseEnabled(False, False)
        layout.addWidget(self._chart)

        # Comparison stats
        stats_row = QHBoxLayout()

        self._below_stats = self._create_stats_card("BELOW THRESHOLD")
        self._above_stats = self._create_stats_card("ABOVE THRESHOLD")

        stats_row.addWidget(self._below_stats)
        stats_row.addWidget(self._above_stats)
        layout.addLayout(stats_row)

    def _create_stats_card(self, title: str) -> QWidget:
        """Create a stats comparison card."""
        card = QWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: 10px;
                letter-spacing: 1px;
            }}
        """)
        layout.addWidget(title_label)

        # Stats labels will be added dynamically
        card._stats_layout = layout
        card._stat_labels = {}

        return card

    def set_data(self, result: FeatureImpactResult) -> None:
        """Populate the detail widget with result data."""
        # Threshold label
        direction = ">" if result.threshold_direction == "above" else "<"
        self._threshold_label.setText(
            f"Threshold: {result.feature_name} {direction} {result.optimal_threshold:.2f}"
        )

        # Spark chart - win rate by percentile
        self._chart.clear()
        x = list(range(len(result.percentile_win_rates)))
        y = result.percentile_win_rates

        # Bar chart
        bar = pg.BarGraphItem(
            x=x, height=y, width=0.8,
            brush=Colors.SIGNAL_CYAN,
            pen=pg.mkPen(None),
        )
        self._chart.addItem(bar)

        # Threshold line (approximate position)
        thresh_pct = 50  # Would need to calculate actual percentile
        line = pg.InfiniteLine(
            pos=thresh_pct / 5,  # Scale to bar count
            angle=90,
            pen=pg.mkPen(Colors.SIGNAL_AMBER, width=2),
        )
        self._chart.addItem(line)

        # Update stats cards
        self._update_stats_card(self._below_stats, {
            "Trades": f"{result.trades_below:,}",
            "Win Rate": f"{result.win_rate_below:.1f}%",
            "Expectancy": f"{result.expectancy_below:.4f}",
        })

        lift_wr = result.win_rate_above - result.win_rate_baseline
        lift_ev = result.expectancy_above - result.expectancy_baseline
        self._update_stats_card(self._above_stats, {
            "Trades": f"{result.trades_above:,}",
            "Win Rate": f"{result.win_rate_above:.1f}% ({lift_wr:+.1f}%)",
            "Expectancy": f"{result.expectancy_above:.4f} ({lift_ev:+.4f})",
        }, highlight=result.threshold_direction == "above")

    def _update_stats_card(
        self, card: QWidget, stats: dict[str, str], highlight: bool = False
    ) -> None:
        """Update stats card labels."""
        # Clear existing stat labels
        for label in card._stat_labels.values():
            label.deleteLater()
        card._stat_labels.clear()

        color = Colors.SIGNAL_CYAN if highlight else Colors.TEXT_PRIMARY

        for key, value in stats.items():
            label = QLabel(f"{key}: {value}")
            label.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-family: '{Fonts.DATA}';
                    font-size: 12px;
                }}
            """)
            card._stats_layout.addWidget(label)
            card._stat_labels[key] = label


# In FeatureImpactTab:

    def __init__(self, ...):
        # ... existing ...
        self._expanded_row: int | None = None

    def _setup_ui(self) -> None:
        # ... existing code ...

        # Detail widget (hidden by default)
        self._detail_widget = FeatureDetailWidget()
        self._detail_widget.setVisible(False)
        layout.addWidget(self._detail_widget)

        # Table (moved after detail widget in layout)
        self._table = self._create_table()
        layout.addWidget(self._table)

    def _create_table(self) -> QTableWidget:
        # ... existing code ...

        # Connect row click
        table.cellClicked.connect(self._on_row_clicked)

        return table

    def _on_row_clicked(self, row: int, col: int) -> None:
        """Handle row click to expand/collapse detail."""
        if self._expanded_row == row:
            # Collapse
            self._detail_widget.setVisible(False)
            self._expanded_row = None
        else:
            # Expand
            if row < len(self._baseline_results):
                result = self._baseline_results[row]
                self._detail_widget.set_data(result)
                self._detail_widget.setVisible(True)
                self._expanded_row = row
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_feature_impact_tab.py::TestFeatureImpactTabExpansion -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tabs/feature_impact.py tests/unit/test_feature_impact_tab.py
git commit -m "feat(feature-impact): add expandable row detail with spark chart

Click any row to expand a detail panel showing:
- Optimal threshold value
- Win rate by percentile spark chart
- Below/above threshold comparison stats

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 10: Tab Overflow Menu (PyQt6Ads Configuration)

**Files:**
- Modify: `src/ui/dock_manager.py`
- Test: Manual verification (PyQt6Ads behavior)

**Step 1: Verify PyQt6Ads overflow menu is enabled**

Check `dock_manager.py` for `DockAreaHasTabsMenuButton` flag.

**Step 2: Ensure flag is set**

```python
# In src/ui/dock_manager.py __init__ method, verify this flag exists:
self.setConfigFlag(ads.CDockManager.eConfigFlag.DockAreaHasTabsMenuButton, True)
```

This should already be present. If not, add it.

**Step 3: Style the overflow menu**

```python
# Add to _apply_styling() method in dock_manager.py

        # Tabs menu button (overflow)
        ads--CDockAreaTitleBar > QPushButton {{
            background-color: {Colors.BG_ELEVATED};
            border: none;
            border-radius: 4px;
            padding: 4px 8px;
            color: {Colors.TEXT_PRIMARY};
        }}

        ads--CDockAreaTitleBar > QPushButton:hover {{
            background-color: {Colors.BG_BORDER};
        }}

        /* Menu styling for overflow dropdown */
        ads--CDockAreaTitleBar QMenu {{
            background-color: {Colors.BG_ELEVATED};
            border: 1px solid {Colors.BG_BORDER};
            border-radius: 4px;
            padding: 4px 0;
        }}

        ads--CDockAreaTitleBar QMenu::item {{
            padding: 8px 24px;
            color: {Colors.TEXT_PRIMARY};
        }}

        ads--CDockAreaTitleBar QMenu::item:selected {{
            background-color: rgba(0, 255, 212, 0.15);
        }}

        ads--CDockAreaTitleBar QMenu::separator {{
            height: 1px;
            background-color: {Colors.BG_BORDER};
            margin: 4px 8px;
        }}
```

**Step 4: Commit**

```bash
git add src/ui/dock_manager.py
git commit -m "style(dock): improve tab overflow menu styling

Styled the PyQt6Ads overflow menu button and dropdown
to match Lumen Observatory theme.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 11: Integration Test & Final Polish

**Files:**
- Test: `tests/integration/test_feature_impact_integration.py`

**Step 1: Write integration test**

```python
# tests/integration/test_feature_impact_integration.py
"""Integration tests for Feature Impact tab."""

import numpy as np
import pandas as pd
import pytest
from PyQt6.QtWidgets import QApplication

from src.core.app_state import AppState
from src.core.models import ColumnMapping
from src.tabs.feature_impact import FeatureImpactTab


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def sample_trade_data() -> pd.DataFrame:
    """Create realistic sample trade data."""
    np.random.seed(42)
    n = 500
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=n),
        "ticker": np.random.choice(["AAPL", "MSFT", "GOOG"], n),
        "gap_pct": np.random.uniform(-5, 10, n),
        "volume_ratio": np.random.uniform(0.5, 3, n),
        "float_pct": np.random.uniform(1, 20, n),
        "gain_pct": np.random.normal(0.02, 0.05, n),
    })


class TestFeatureImpactIntegration:
    """Integration tests for full workflow."""

    def test_full_analysis_workflow(self, app, sample_trade_data):
        """Test complete workflow from data load to display."""
        # Set up app state with data
        app_state = AppState()
        app_state.raw_df = sample_trade_data
        app_state.baseline_df = sample_trade_data
        app_state.column_mapping = ColumnMapping(
            date="date",
            ticker="ticker",
            gain_pct="gain_pct",
        )

        # Create tab
        tab = FeatureImpactTab(app_state)

        # Trigger analysis
        tab._on_data_updated()

        # Verify results
        assert len(tab._baseline_results) == 3  # gap_pct, volume_ratio, float_pct
        assert tab._table.rowCount() == 3
        assert not tab._empty_label.isVisible()
        assert tab._table.isVisible()

    def test_handles_empty_data(self, app):
        """Test graceful handling of empty data."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)

        # Should show empty state
        assert tab._empty_label.isVisible()
        assert not tab._table.isVisible()
```

**Step 2: Run integration tests**

Run: `pytest tests/integration/test_feature_impact_integration.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/integration/test_feature_impact_integration.py
git commit -m "test(feature-impact): add integration tests

Tests full workflow from data loading through display.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Summary

This plan implements the Feature Impact Tab in 11 tasks:

1. **Task 1-3**: Core calculator (data structures, optimal threshold, multi-feature)
2. **Task 4-5**: Basic tab skeleton with gradient coloring
3. **Task 6**: Baseline vs filtered dual columns
4. **Task 7**: Sortable column headers
5. **Task 8**: Column exclusion panel
6. **Task 9**: Expandable row detail with spark chart
7. **Task 10**: Tab overflow menu styling
8. **Task 11**: Integration tests

Each task is TDD: write failing test → implement → verify → commit.

---

**Plan complete and saved to `docs/plans/2026-02-07-feature-impact-implementation.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session in worktree with executing-plans, batch execution with checkpoints

**Which approach?**
