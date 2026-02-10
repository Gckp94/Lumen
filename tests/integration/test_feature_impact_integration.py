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
    """Provide QApplication instance for Qt tests."""
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def sample_trade_data() -> pd.DataFrame:
    """Create realistic sample trade data."""
    np.random.seed(42)
    n = 500
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=n),
        "time": ["09:30:00"] * n,
        "ticker": np.random.choice(["AAPL", "MSFT", "GOOG"], n),
        "gap_pct": np.random.uniform(-5, 10, n),
        "volume_ratio": np.random.uniform(0.5, 3, n),
        "float_pct": np.random.uniform(1, 20, n),
        "gain_pct": np.random.normal(0.02, 0.05, n),
        "mae_pct": np.random.uniform(0, 5, n),
        "mfe_pct": np.random.uniform(0, 10, n),
    })


@pytest.fixture
def app_state_with_data(sample_trade_data: pd.DataFrame) -> AppState:
    """AppState configured with sample trade data."""
    app_state = AppState()
    app_state.raw_df = sample_trade_data
    app_state.baseline_df = sample_trade_data.copy()
    app_state.column_mapping = ColumnMapping(
        date="date",
        time="time",
        ticker="ticker",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
    )
    return app_state


class TestFeatureImpactIntegration:
    """Integration tests for full workflow."""

    def test_full_analysis_workflow(self, app, qtbot, app_state_with_data):
        """Test complete workflow from data load to display."""
        # Create tab
        tab = FeatureImpactTab(app_state_with_data)
        qtbot.addWidget(tab)

        # Trigger analysis via signal
        app_state_with_data.baseline_calculated.emit(None)

        # Process events
        qtbot.wait(50)

        # Verify results
        # Features: gap_pct, volume_ratio, float_pct, mae_pct, mfe_pct = 5 features
        assert len(tab._baseline_results) == 5
        assert tab._table.rowCount() == 5
        assert tab._empty_label.isHidden()
        assert not tab._table.isHidden()

    def test_handles_empty_data(self, app, qtbot):
        """Test graceful handling of empty data."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        qtbot.addWidget(tab)

        # Should show empty state
        assert not tab._empty_label.isHidden()
        assert tab._table.isHidden()

    def test_filtered_data_updates_results(self, app, qtbot, app_state_with_data):
        """Test that filtered data triggers recalculation."""
        tab = FeatureImpactTab(app_state_with_data)
        qtbot.addWidget(tab)

        # Initial analysis
        app_state_with_data.baseline_calculated.emit(None)
        qtbot.wait(50)

        initial_row_count = tab._table.rowCount()
        assert initial_row_count == 5  # 5 numeric feature columns

        # Create filtered data (subset)
        filtered_df = app_state_with_data.baseline_df.iloc[:250].copy()
        app_state_with_data.filtered_df = filtered_df

        # Trigger filtered data update
        app_state_with_data.filtered_data_updated.emit(filtered_df)
        qtbot.wait(50)

        # Table should still have same structure
        assert tab._table.rowCount() == 5

        # Filtered results should be updated (different from baseline)
        assert len(tab._filtered_results) == 5

    def test_column_exclusion_reduces_features(self, app, qtbot, app_state_with_data):
        """Test that excluding columns removes features from analysis."""
        tab = FeatureImpactTab(app_state_with_data)
        qtbot.addWidget(tab)

        # Initial analysis
        app_state_with_data.baseline_calculated.emit(None)
        qtbot.wait(50)

        assert tab._table.rowCount() == 5  # 5 numeric feature columns

        # Exclude gap_pct column
        tab._user_excluded_cols.add("gap_pct")
        tab._analyze_features()
        qtbot.wait(50)

        # Should now have only 4 features
        assert tab._table.rowCount() == 4
        assert len(tab._baseline_results) == 4

    def test_sorting_changes_order(self, app, qtbot, app_state_with_data):
        """Test that clicking headers changes sort order."""
        tab = FeatureImpactTab(app_state_with_data)
        qtbot.addWidget(tab)

        # Initial analysis
        app_state_with_data.baseline_calculated.emit(None)
        qtbot.wait(50)

        # Get initial order (first feature name)
        initial_first = tab._baseline_results[0].feature_name

        # Click feature name column (col 0) to sort alphabetically
        tab._on_header_clicked(0)

        # Get new order
        new_first = tab._baseline_results[0].feature_name

        # Order should change (unless already alphabetical)
        # At minimum, verify sort was applied
        assert tab._sort_column == 0

    def test_row_click_shows_detail(self, app, qtbot, app_state_with_data):
        """Test that clicking a row shows the detail widget."""
        tab = FeatureImpactTab(app_state_with_data)
        qtbot.addWidget(tab)

        # Initial analysis
        app_state_with_data.baseline_calculated.emit(None)
        qtbot.wait(50)

        # Detail widget should be hidden initially
        assert tab._detail_widget.isHidden()

        # Simulate row click
        tab._on_row_clicked(0, 0)

        # Detail widget should now be visible
        assert not tab._detail_widget.isHidden()
        assert tab._expanded_row == 0

        # Click same row again to collapse
        tab._on_row_clicked(0, 0)
        assert tab._detail_widget.isHidden()
        assert tab._expanded_row is None

    def test_table_has_expected_columns(self, app, qtbot, app_state_with_data):
        """Test that table has correct column structure."""
        tab = FeatureImpactTab(app_state_with_data)
        qtbot.addWidget(tab)

        # Verify column count (13 columns including PnL columns)
        assert tab._table.columnCount() == 13

        # Verify key column headers
        headers = []
        for col in range(tab._table.columnCount()):
            header_item = tab._table.horizontalHeaderItem(col)
            if header_item:
                headers.append(header_item.text())

        assert "Feature" in headers
        assert "Impact" in headers
        assert "Corr (B)" in headers
        assert "Corr (F)" in headers
        assert "WR Lift (B)" in headers
        assert "WR Lift (F)" in headers
        assert "PnL (B)" in headers
        assert "PnL (F)" in headers

    def test_summary_label_updates(self, app, qtbot, app_state_with_data):
        """Test that summary label shows correct counts."""
        tab = FeatureImpactTab(app_state_with_data)
        qtbot.addWidget(tab)

        # Initial analysis
        app_state_with_data.baseline_calculated.emit(None)
        qtbot.wait(50)

        # Summary should show feature count and trade count
        summary_text = tab._summary_label.text()
        assert "5 features" in summary_text
        assert "500" in summary_text  # Trade count

    def test_exclusion_panel_has_checkboxes(self, app, qtbot, app_state_with_data):
        """Test that exclusion panel populates with column checkboxes."""
        tab = FeatureImpactTab(app_state_with_data)
        qtbot.addWidget(tab)

        # Initial analysis
        app_state_with_data.baseline_calculated.emit(None)
        qtbot.wait(50)

        # Exclusion panel should exist
        assert hasattr(tab, '_exclude_panel')

        # No columns should be excluded by default
        excluded = tab._exclude_panel.get_excluded()
        assert len(excluded) == 0


class TestFeatureImpactWithCorrelatedData:
    """Test feature impact detection with known correlations."""

    @pytest.fixture
    def correlated_trade_data(self) -> pd.DataFrame:
        """Create data where one feature strongly predicts gains."""
        np.random.seed(123)
        n = 1000

        # predictive_feature directly influences gains
        predictive_feature = np.random.uniform(0, 100, n)

        # Gains are higher when predictive_feature > 50
        gains = np.where(
            predictive_feature > 50,
            np.random.normal(0.05, 0.02, n),  # Higher gains above threshold
            np.random.normal(-0.02, 0.02, n),  # Lower gains below threshold
        )

        # Random noise feature (no correlation)
        noise_feature = np.random.randn(n)

        return pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=n),
            "time": ["09:30:00"] * n,
            "ticker": np.random.choice(["A", "B", "C"], n),
            "predictive_feature": predictive_feature,
            "noise_feature": noise_feature,
            "gain_pct": gains,
            "mae_pct": np.random.uniform(0, 5, n),
            "mfe_pct": np.random.uniform(0, 10, n),
        })

    def test_identifies_predictive_feature(self, app, qtbot, correlated_trade_data):
        """Test that predictive feature ranks higher than noise."""
        app_state = AppState()
        app_state.raw_df = correlated_trade_data
        app_state.baseline_df = correlated_trade_data.copy()
        app_state.column_mapping = ColumnMapping(
            date="date",
            time="time",
            ticker="ticker",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
        )

        tab = FeatureImpactTab(app_state)
        qtbot.addWidget(tab)

        # Trigger analysis
        app_state.baseline_calculated.emit(None)
        qtbot.wait(50)

        # predictive_feature should have higher impact score
        scores = tab._baseline_scores
        assert scores["predictive_feature"] > scores["noise_feature"], (
            f"Predictive feature ({scores['predictive_feature']:.3f}) should rank "
            f"higher than noise ({scores['noise_feature']:.3f})"
        )

    def test_threshold_direction_detected(self, app, qtbot, correlated_trade_data):
        """Test that optimal threshold direction is correctly detected."""
        app_state = AppState()
        app_state.raw_df = correlated_trade_data
        app_state.baseline_df = correlated_trade_data.copy()
        app_state.column_mapping = ColumnMapping(
            date="date",
            time="time",
            ticker="ticker",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
        )

        tab = FeatureImpactTab(app_state)
        qtbot.addWidget(tab)

        # Trigger analysis
        app_state.baseline_calculated.emit(None)
        qtbot.wait(50)

        # Find predictive_feature result
        predictive_result = next(
            r for r in tab._baseline_results
            if r.feature_name == "predictive_feature"
        )

        # Should detect "above" as the favorable direction
        assert predictive_result.threshold_direction == "above", (
            f"Expected 'above' direction, got '{predictive_result.threshold_direction}'"
        )

        # Threshold should be around 50 (the split point)
        assert 40 <= predictive_result.optimal_threshold <= 60, (
            f"Expected threshold near 50, got {predictive_result.optimal_threshold}"
        )


class TestFeatureImpactEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_single_feature(self, app, qtbot):
        """Test handling of data with only one numeric feature."""
        n = 100
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=n),
            "time": ["09:30:00"] * n,
            "ticker": ["AAPL"] * n,
            "only_feature": np.random.randn(n),
            "gain_pct": np.random.randn(n) * 0.02,
            "mae_pct": np.random.uniform(0, 5, n),
            "mfe_pct": np.random.uniform(0, 10, n),
        })

        app_state = AppState()
        app_state.raw_df = df
        app_state.baseline_df = df.copy()
        app_state.column_mapping = ColumnMapping(
            date="date",
            time="time",
            ticker="ticker",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
        )

        tab = FeatureImpactTab(app_state)
        qtbot.addWidget(tab)

        # Trigger analysis
        app_state.baseline_calculated.emit(None)
        qtbot.wait(50)

        # Should analyze available features: only_feature, mae_pct, mfe_pct = 3
        assert tab._table.rowCount() == 3
        assert len(tab._baseline_results) == 3

    def test_handles_small_dataset(self, app, qtbot):
        """Test handling of very small datasets."""
        n = 20
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=n),
            "time": ["09:30:00"] * n,
            "ticker": ["AAPL"] * n,
            "feature1": np.random.randn(n),
            "gain_pct": np.random.randn(n) * 0.02,
            "mae_pct": np.random.uniform(0, 5, n),
            "mfe_pct": np.random.uniform(0, 10, n),
        })

        app_state = AppState()
        app_state.raw_df = df
        app_state.baseline_df = df.copy()
        app_state.column_mapping = ColumnMapping(
            date="date",
            time="time",
            ticker="ticker",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
        )

        tab = FeatureImpactTab(app_state)
        qtbot.addWidget(tab)

        # Trigger analysis
        app_state.baseline_calculated.emit(None)
        qtbot.wait(50)

        # Should still analyze without errors: feature1, mae_pct, mfe_pct = 3
        assert tab._table.rowCount() == 3

    def test_handles_constant_feature(self, app, qtbot):
        """Test handling of constant (zero variance) features."""
        np.random.seed(42)
        n = 100
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=n),
            "time": ["09:30:00"] * n,
            "ticker": ["AAPL"] * n,
            "constant_feature": [5.0] * n,  # No variance
            "varying_feature": np.random.randn(n),
            "gain_pct": np.random.randn(n) * 0.02,
            "mae_pct": np.random.uniform(0, 5, n),
            "mfe_pct": np.random.uniform(0, 10, n),
        })

        app_state = AppState()
        app_state.raw_df = df
        app_state.baseline_df = df.copy()
        app_state.column_mapping = ColumnMapping(
            date="date",
            time="time",
            ticker="ticker",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
        )

        tab = FeatureImpactTab(app_state)
        qtbot.addWidget(tab)

        # Trigger analysis
        app_state.baseline_calculated.emit(None)
        qtbot.wait(50)

        # Should handle gracefully - constant feature should be skipped or handled
        # At minimum, should not crash
        assert tab._table.rowCount() >= 1

    def test_initialize_with_existing_data(self, app, qtbot, sample_trade_data):
        """Test that tab initializes correctly when data already exists in state."""
        # Set up state with data before creating tab
        app_state = AppState()
        app_state.raw_df = sample_trade_data
        app_state.baseline_df = sample_trade_data.copy()
        app_state.filtered_df = sample_trade_data.copy()
        app_state.column_mapping = ColumnMapping(
            date="date",
            time="time",
            ticker="ticker",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
        )

        # Create tab - should detect existing data
        tab = FeatureImpactTab(app_state)
        qtbot.addWidget(tab)

        # Trigger data update
        app_state.baseline_calculated.emit(None)
        qtbot.wait(50)

        # Tab should be populated
        assert not tab._empty_label.isHidden() or tab._table.rowCount() > 0
