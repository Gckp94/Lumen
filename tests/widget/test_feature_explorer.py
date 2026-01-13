"""Widget tests for Feature Explorer tab."""

import pandas as pd

from src.core.app_state import AppState
from src.tabs.feature_explorer import FeatureExplorerTab


class TestFeatureExplorerLayout:
    """Tests for Feature Explorer layout structure."""

    def test_layout_has_sidebar_chart_and_bottom_bar(self, qtbot):
        """Feature Explorer has sidebar, chart, and bottom bar."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        # Verify layout components exist
        assert tab._sidebar is not None
        assert tab._chart_canvas is not None
        assert tab._bottom_bar is not None

    def test_layout_has_column_selector(self, qtbot):
        """Feature Explorer has column selector dropdown."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        assert tab._column_selector is not None

    def test_layout_has_data_count_label(self, qtbot):
        """Feature Explorer has data count label in bottom bar."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        assert tab._data_count_label is not None


class TestColumnSelector:
    """Tests for column selector functionality."""

    def test_column_selector_populates_with_numeric_columns(self, qtbot):
        """Column selector shows numeric columns only."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL"],
            "gain_pct": [1.5, 2.3],
            "volume": [100, 200],
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)

        # Should have gain_pct and volume (numeric), not ticker (string)
        items = [
            tab._column_selector.itemText(i)
            for i in range(tab._column_selector.count())
        ]
        assert "gain_pct" in items
        assert "volume" in items
        assert "ticker" not in items

    def test_column_selector_defaults_to_gain_pct(self, qtbot):
        """Column selector defaults to gain_pct if available."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({
            "volume": [100, 200],
            "gain_pct": [1.5, 2.3],
            "price": [150.0, 2800.0],
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)

        assert tab._column_selector.currentText() == "gain_pct"

    def test_column_selector_defaults_to_first_if_no_gain_pct(self, qtbot):
        """Column selector defaults to first column if gain_pct not available."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({
            "volume": [100, 200],
            "price": [150.0, 2800.0],
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)

        # Should default to first numeric column
        assert tab._column_selector.currentIndex() == 0

    def test_column_selector_disabled_when_no_data(self, qtbot):
        """Column selector is disabled when no data is loaded."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        assert not tab._column_selector.isEnabled()

    def test_column_selector_enabled_after_data_load(self, qtbot):
        """Column selector is enabled after data is loaded."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0]})
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)

        assert tab._column_selector.isEnabled()


class TestDataCountLabel:
    """Tests for bottom bar data count label."""

    def test_data_count_label_shows_correct_count(self, qtbot):
        """Bottom bar shows correct data point count."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0]})
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)
        app_state.baseline_calculated.emit(None)

        assert "3" in tab._data_count_label.text()

    def test_data_count_label_formats_large_numbers(self, qtbot):
        """Bottom bar formats large numbers with commas."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({"gain_pct": list(range(12847))})
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)
        app_state.baseline_calculated.emit(None)

        assert "12,847" in tab._data_count_label.text()

    def test_data_count_label_shows_no_data_initially(self, qtbot):
        """Bottom bar shows 'No data loaded' initially."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        assert "No data" in tab._data_count_label.text()


class TestEmptyStates:
    """Tests for empty state handling."""

    def test_shows_empty_state_when_no_data(self, qtbot):
        """Shows empty state message when no data is loaded."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        # Empty state should be visible (index 0)
        assert tab._chart_stack.currentIndex() == 0
        assert "Load a data file" in tab._empty_label.text()

    def test_shows_no_numeric_columns_message(self, qtbot):
        """Shows message when no numeric columns available."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        # DataFrame with only non-numeric columns
        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL"],
            "name": ["Apple", "Google"],
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)

        assert "No numeric columns" in tab._empty_label.text()
        assert not tab._column_selector.isEnabled()


class TestChartUpdates:
    """Tests for chart update functionality."""

    def test_chart_updates_on_baseline_calculated(self, qtbot):
        """Chart updates when baseline_calculated signal is emitted."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0, 4.0, 5.0]})
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)
        app_state.baseline_calculated.emit(None)

        # Chart should now be visible (index 1)
        assert tab._chart_stack.currentIndex() == 1
        # Chart should have data
        assert len(tab._chart_canvas._scatter.data) == 5

    def test_chart_updates_on_column_change(self, qtbot):
        """Chart updates when column selector changes."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({
            "gain_pct": [1.0, 2.0, 3.0],
            "volume": [100.0, 200.0, 300.0],
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)
        app_state.baseline_calculated.emit(None)

        # Change column
        tab._column_selector.setCurrentText("volume")

        # Wait for debounce timer
        qtbot.wait(200)

        # Chart should still have 3 points
        assert len(tab._chart_canvas._scatter.data) == 3


class TestExportButton:
    """Tests for export button in bottom bar."""

    def test_export_button_exists_in_bottom_bar(self, qtbot):
        """Export button exists in the bottom bar."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_export_button")
        assert tab._export_button is not None
        assert tab._export_button.text() == "Export Filtered Data"

    def test_export_button_initially_disabled(self, qtbot):
        """Export button is disabled when no data is loaded."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        assert not tab._export_button.isEnabled()

    def test_export_button_enabled_when_baseline_data_available(self, qtbot):
        """Export button is enabled when baseline data is available."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0]})
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)
        app_state.baseline_calculated.emit(None)

        assert tab._export_button.isEnabled()

    def test_export_button_enabled_when_filtered_data_available(self, qtbot):
        """Export button is enabled when filtered data is available."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0]})
        app_state.baseline_df = df
        app_state.filtered_df = df
        app_state.filtered_data_updated.emit(df)

        assert tab._export_button.isEnabled()

    def test_export_button_disabled_when_filtered_df_empty(self, qtbot):
        """Export button is disabled when filtered DataFrame is empty."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0]})
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)

        # Set filtered_df to empty
        empty_df = pd.DataFrame(columns=["gain_pct"])
        app_state.filtered_df = empty_df
        app_state.filtered_data_updated.emit(empty_df)

        assert not tab._export_button.isEnabled()


class TestFilterSummary:
    """Tests for filter summary label in bottom bar (AC: 5)."""

    def test_filter_summary_label_exists(self, qtbot):
        """Filter summary label exists in bottom bar."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_filter_summary_label")
        assert tab._filter_summary_label is not None

    def test_filter_summary_shows_none_initially(self, qtbot):
        """Filter summary shows 'Filters: None' initially."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        assert tab._filter_summary_label.text() == "Filters: None"

    def test_filter_summary_updates_with_filter_count(self, qtbot):
        """Filter summary updates to show active filter count."""
        from src.core.models import FilterCriteria

        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0, 4.0, 5.0]})
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)

        # Apply 2 filters
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10),
            FilterCriteria(column="gain_pct", operator="between", min_val=1, max_val=5),
        ]
        tab._on_filters_applied(filters)

        assert "2 active" in tab._filter_summary_label.text()

    def test_filter_summary_shows_date_range(self, qtbot):
        """Filter summary shows date range when date filter active."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0]})
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)

        # Simulate date range change (not all dates)
        tab._on_date_range_changed("2024-01-15", "2024-01-20", False)

        # Should contain the date range display
        summary_text = tab._filter_summary_label.text()
        assert "Filters:" in summary_text
        # Should not say "None"
        assert "None" not in summary_text

    def test_filter_summary_shows_count_and_date_range(self, qtbot):
        """Filter summary shows both filter count and date range."""
        from src.core.models import FilterCriteria

        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0, 4.0, 5.0]})
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)

        # Set date range
        tab._on_date_range_changed("2024-01-15", "2024-01-20", False)

        # Apply column filter
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10),
        ]
        tab._on_filters_applied(filters)

        summary_text = tab._filter_summary_label.text()
        # 1 column filter + 1 date range filter = 2 active
        assert "2 active" in summary_text
        # Should also contain date indication

    def test_filter_summary_resets_on_clear(self, qtbot):
        """Filter summary resets to 'None' when filters cleared."""
        from src.core.models import FilterCriteria

        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0]})
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)

        # Apply filter
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10),
        ]
        tab._on_filters_applied(filters)
        assert "1 active" in tab._filter_summary_label.text()

        # Clear filters
        tab._on_filters_cleared()

        assert tab._filter_summary_label.text() == "Filters: None"
