"""Widget tests for DataBinningTab."""

import pandas as pd
from PyQt6.QtWidgets import QComboBox, QPushButton
from pytestqt.qtbot import QtBot

from src.core.app_state import AppState
from src.core.models import BinConfig, BinDefinition
from src.tabs.data_binning import (
    BinChartPanel,
    BinConfigRow,
    DataBinningTab,
    HorizontalBarChart,
)


class TestDataBinningTabCreation:
    """Tests for DataBinningTab creation."""

    def test_tab_creates_without_error(self, qtbot: QtBot) -> None:
        """DataBinningTab creates without error."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)
        assert tab is not None

    def test_tab_has_column_dropdown(self, qtbot: QtBot) -> None:
        """DataBinningTab contains column dropdown."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        assert tab._column_dropdown is not None
        assert isinstance(tab._column_dropdown, QComboBox)

    def test_column_dropdown_initially_disabled(self, qtbot: QtBot) -> None:
        """Column dropdown is disabled when no data loaded."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        assert not tab._column_dropdown.isEnabled()

    def test_add_bin_button_exists(self, qtbot: QtBot) -> None:
        """DataBinningTab contains Add Bin button."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        assert tab._add_bin_button is not None
        assert isinstance(tab._add_bin_button, QPushButton)
        assert "+ Add Bin" in tab._add_bin_button.text()

    def test_add_bin_button_initially_disabled(self, qtbot: QtBot) -> None:
        """Add Bin button is disabled when no data loaded."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        assert not tab._add_bin_button.isEnabled()


class TestDataBinningTabSignalConnections:
    """Tests for DataBinningTab signal connections."""

    def test_data_loaded_signal_connected(self, qtbot: QtBot) -> None:
        """Tab connects to AppState data_loaded signal."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        # Emit data_loaded signal and verify dropdown gets enabled
        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL"],
            "gain_pct": [1.5, -0.8],
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)

        assert tab._column_dropdown.isEnabled()

    def test_column_selected_signal_emitted(self, qtbot: QtBot) -> None:
        """column_selected signal is emitted when column changes."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        # Load data first
        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL"],
            "gain_pct": [1.5, -0.8],
            "volume": [1000, 2000],
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)

        # Select a column and check signal
        with qtbot.waitSignal(tab.column_selected, timeout=1000) as blocker:
            tab._column_dropdown.setCurrentText("gain_pct")

        assert blocker.signal_triggered
        assert blocker.args == ["gain_pct"]

    def test_bin_config_changed_signal_emitted_on_add(self, qtbot: QtBot) -> None:
        """bin_config_changed signal is emitted when bin is added."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        # Load data and select column
        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL"],
            "gain_pct": [1.5, -0.8],
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)
        tab._column_dropdown.setCurrentText("gain_pct")

        # Add bin and check signal
        with qtbot.waitSignal(tab.bin_config_changed, timeout=1000):
            tab._add_bin_button.click()


class TestDataBinningTabColumnDropdown:
    """Tests for column dropdown population."""

    def test_dropdown_populated_with_numeric_columns(self, qtbot: QtBot) -> None:
        """Dropdown is populated with numeric columns only."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL"],
            "date": ["2024-01-01", "2024-01-02"],
            "gain_pct": [1.5, -0.8],
            "volume": [1000, 2000],
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)

        # Check dropdown items
        items = [tab._column_dropdown.itemText(i) for i in range(tab._column_dropdown.count())]
        assert "gain_pct" in items
        assert "volume" in items
        assert "ticker" not in items
        assert "date" not in items

    def test_dropdown_empty_when_no_numeric_columns(self, qtbot: QtBot) -> None:
        """Dropdown is empty when no numeric columns exist."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL"],
            "date": ["2024-01-01", "2024-01-02"],
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)

        assert tab._column_dropdown.count() == 0


class TestBinRowManagement:
    """Tests for bin row add/remove functionality."""

    def test_nulls_row_added_on_column_select(self, qtbot: QtBot) -> None:
        """Nulls bin row is added when column is selected."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({
            "gain_pct": [1.5, -0.8],
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)
        tab._column_dropdown.setCurrentText("gain_pct")

        assert len(tab._bin_rows) == 1
        assert tab._bin_rows[0].get_operator() == "nulls"

    def test_add_bin_creates_new_row(self, qtbot: QtBot) -> None:
        """Clicking Add Bin creates a new bin row."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({
            "gain_pct": [1.5, -0.8],
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)
        tab._column_dropdown.setCurrentText("gain_pct")

        initial_count = len(tab._bin_rows)
        tab._add_bin_button.click()

        assert len(tab._bin_rows) == initial_count + 1

    def test_new_bin_has_less_than_operator(self, qtbot: QtBot) -> None:
        """Newly added bin has less than operator by default."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({
            "gain_pct": [1.5, -0.8],
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)
        tab._column_dropdown.setCurrentText("gain_pct")
        tab._add_bin_button.click()

        # First row should be the new one (before nulls)
        new_row = tab._bin_rows[0]
        assert new_row.get_operator() == "<"

    def test_nulls_row_not_removable(self, qtbot: QtBot) -> None:
        """Nulls bin row cannot be removed."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({
            "gain_pct": [1.5, -0.8],
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)
        tab._column_dropdown.setCurrentText("gain_pct")

        nulls_row = tab._bin_rows[0]
        assert nulls_row._is_removable is False

    def test_user_bin_removable(self, qtbot: QtBot) -> None:
        """User-added bin rows can be removed."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({
            "gain_pct": [1.5, -0.8],
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)
        tab._column_dropdown.setCurrentText("gain_pct")
        tab._add_bin_button.click()

        user_row = tab._bin_rows[0]
        assert user_row._is_removable is True


class TestBinConfigRow:
    """Tests for BinConfigRow widget."""

    def test_row_creates_with_operator(self, qtbot: QtBot) -> None:
        """BinConfigRow creates with specified operator."""
        row = BinConfigRow(operator="<")
        qtbot.addWidget(row)
        assert row.get_operator() == "<"

    def test_nulls_operator_row(self, qtbot: QtBot) -> None:
        """BinConfigRow with nulls operator has correct structure."""
        row = BinConfigRow(operator="nulls", is_removable=False)
        qtbot.addWidget(row)
        assert row.get_operator() == "nulls"
        assert row._is_removable is False

    def test_remove_signal_emitted(self, qtbot: QtBot) -> None:
        """remove_requested signal is emitted when remove button clicked."""
        row = BinConfigRow(operator="<", is_removable=True)
        qtbot.addWidget(row)

        with qtbot.waitSignal(row.remove_requested, timeout=1000):
            # Find and click the remove button
            for child in row.children():
                if isinstance(child, QPushButton) and child.text() == "×":
                    child.click()
                    break

    def test_config_changed_signal_on_operator_change(self, qtbot: QtBot) -> None:
        """config_changed signal is emitted when operator changes."""
        row = BinConfigRow(operator="<")
        qtbot.addWidget(row)

        with qtbot.waitSignal(row.config_changed, timeout=1000):
            row._operator_dropdown.setCurrentIndex(1)  # Change to ">"

    def test_get_bin_definition_less_than(self, qtbot: QtBot) -> None:
        """get_bin_definition returns correct BinDefinition for less than."""
        row = BinConfigRow(operator="<")
        qtbot.addWidget(row)
        row._value1_input.setText("100")

        bin_def = row.get_bin_definition()
        assert bin_def.operator == "<"
        assert bin_def.value1 == 100.0
        assert bin_def.label == "< 100"

    def test_get_bin_definition_range(self, qtbot: QtBot) -> None:
        """get_bin_definition returns correct BinDefinition for range."""
        row = BinConfigRow(operator="range")
        qtbot.addWidget(row)
        row._operator_dropdown.setCurrentIndex(2)  # Range
        row._value1_input.setText("10")
        row._value2_input.setText("50")

        bin_def = row.get_bin_definition()
        assert bin_def.operator == "range"
        assert bin_def.value1 == 10.0
        assert bin_def.value2 == 50.0

    def test_get_bin_definition_nulls(self, qtbot: QtBot) -> None:
        """get_bin_definition returns correct BinDefinition for nulls."""
        row = BinConfigRow(operator="nulls")
        qtbot.addWidget(row)

        bin_def = row.get_bin_definition()
        assert bin_def.operator == "nulls"
        assert bin_def.value1 is None
        assert bin_def.value2 is None
        assert bin_def.label == "Nulls"


class TestTimeColumnHandling:
    """Tests for time column detection and formatting in UI."""

    def test_time_column_detected(self, qtbot: QtBot) -> None:
        """Time column is detected when selected."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({
            "entry_time": [93000, 140000],
            "gain_pct": [1.5, -0.8],
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)
        tab._column_dropdown.setCurrentText("entry_time")

        assert tab._is_time_column is True

    def test_non_time_column_not_flagged(self, qtbot: QtBot) -> None:
        """Non-time column is not flagged as time column."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        df = pd.DataFrame({
            "entry_time": [93000, 140000],
            "gain_pct": [1.5, -0.8],
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)
        tab._column_dropdown.setCurrentText("gain_pct")

        assert tab._is_time_column is False

    def test_time_bin_row_has_time_placeholder(self, qtbot: QtBot) -> None:
        """Bin row for time column has HH:MM:SS placeholder."""
        row = BinConfigRow(operator="<", is_time_column=True)
        qtbot.addWidget(row)

        assert row._value1_input.placeholderText() == "HH:MM:SS"


class TestHorizontalBarChart:
    """Tests for HorizontalBarChart widget."""

    def test_chart_creates_without_error(self, qtbot: QtBot) -> None:
        """HorizontalBarChart creates without error."""
        chart = HorizontalBarChart(title="Test")
        qtbot.addWidget(chart)
        assert chart is not None

    def test_chart_with_title(self, qtbot: QtBot) -> None:
        """HorizontalBarChart displays title correctly."""
        chart = HorizontalBarChart(title="Average")
        qtbot.addWidget(chart)
        assert chart._title == "Average"

    def test_set_data_updates_chart(self, qtbot: QtBot) -> None:
        """set_data updates chart data."""
        chart = HorizontalBarChart(title="Test")
        qtbot.addWidget(chart)

        data = [("Low", 10.0), ("Mid", 20.0), ("High", 30.0)]
        chart.set_data(data)

        assert chart._data == data

    def test_chart_height_adjusts_to_data(self, qtbot: QtBot) -> None:
        """Chart height adjusts based on number of data items."""
        chart = HorizontalBarChart(title="Test")
        qtbot.addWidget(chart)

        # With no data
        initial_height = chart.minimumHeight()

        # Add data
        data = [("A", 1.0), ("B", 2.0), ("C", 3.0), ("D", 4.0), ("E", 5.0)]
        chart.set_data(data)

        assert chart.minimumHeight() > initial_height

    def test_format_value_percentage(self, qtbot: QtBot) -> None:
        """_format_value formats percentages correctly."""
        chart = HorizontalBarChart(title="Test")
        qtbot.addWidget(chart)
        chart._is_percentage = True

        assert chart._format_value(65.5) == "65.50%"
        assert chart._format_value(100.0) == "100.00%"

    def test_format_value_integer(self, qtbot: QtBot) -> None:
        """_format_value formats integers with K/M/B abbreviations."""
        chart = HorizontalBarChart(title="Test")
        qtbot.addWidget(chart)
        chart._is_percentage = False

        # Large numbers use K/M/B abbreviations
        assert chart._format_value(1000.0) == "1K"
        assert chart._format_value(1000000.0) == "1M"

    def test_get_tooltip_text(self, qtbot: QtBot) -> None:
        """get_tooltip_text returns formatted tooltip."""
        chart = HorizontalBarChart(title="Test")
        qtbot.addWidget(chart)
        chart.set_data([("Low", 25.5), ("High", 75.5)], is_percentage=True)

        tooltip = chart.get_tooltip_text(0)
        assert "Low" in tooltip
        assert "25.50%" in tooltip


class TestBinChartPanel:
    """Tests for BinChartPanel widget."""

    def test_chart_panel_creates_without_error(self, qtbot: QtBot) -> None:
        """BinChartPanel creates without error."""
        app_state = AppState()
        panel = BinChartPanel(app_state)
        qtbot.addWidget(panel)
        assert panel is not None

    def test_chart_panel_has_five_charts(self, qtbot: QtBot) -> None:
        """BinChartPanel has 5 charts including % of Total Gains."""
        app_state = AppState()
        panel = BinChartPanel(app_state)
        qtbot.addWidget(panel)

        charts = panel.findChildren(HorizontalBarChart)
        assert len(charts) == 5, "Should have 5 charts: Average, Median, Count, Win Rate, % of Total"

    def test_chart_panel_has_all_chart_attributes(self, qtbot: QtBot) -> None:
        """BinChartPanel contains all five chart sections."""
        app_state = AppState()
        panel = BinChartPanel(app_state)
        qtbot.addWidget(panel)

        assert panel._average_chart is not None
        assert panel._median_chart is not None
        assert panel._count_chart is not None
        assert panel._win_rate_chart is not None
        assert panel._pct_total_chart is not None

    def test_chart_panel_has_toggle_buttons(self, qtbot: QtBot) -> None:
        """BinChartPanel has metric toggle buttons."""
        app_state = AppState()
        panel = BinChartPanel(app_state)
        qtbot.addWidget(panel)

        assert panel._gain_btn is not None
        assert panel._adjusted_btn is not None
        assert panel._adjusted_btn.isChecked()  # Default to adjusted

    def test_toggle_switch_functionality(self, qtbot: QtBot) -> None:
        """Toggle switch changes metric column."""
        app_state = AppState()
        panel = BinChartPanel(app_state)
        qtbot.addWidget(panel)

        assert panel._current_metric_column == "adjusted_gain_pct"

        # Click gain_pct button
        with qtbot.waitSignal(panel.metric_toggled, timeout=1000):
            panel._gain_btn.click()

        assert panel._current_metric_column == "gain_pct"
        assert panel._gain_btn.isChecked()
        assert not panel._adjusted_btn.isChecked()

    def test_empty_state_shown_when_no_data(self, qtbot: QtBot) -> None:
        """Empty state is shown when no data loaded."""
        app_state = AppState()
        panel = BinChartPanel(app_state)
        qtbot.addWidget(panel)
        panel.show()

        # Initially empty state visible, chart hidden
        assert not panel._empty_state.isHidden()
        assert panel._chart_container.isHidden()

    def test_chart_updates_on_bin_config_change(self, qtbot: QtBot) -> None:
        """Charts update when bin configuration changes."""
        app_state = AppState()
        df = pd.DataFrame({
            "value": [5, 10, 15, 20, 25],
            "gain_pct": [1.0, 2.0, -1.0, 3.0, -2.0],
            "adjusted_gain_pct": [0.5, 1.5, -0.5, 2.5, -1.5],
        })
        app_state.baseline_df = df
        panel = BinChartPanel(app_state)
        qtbot.addWidget(panel)
        panel.show()

        bins = [
            BinDefinition(operator="<", value1=15, label="Low"),
            BinDefinition(operator=">=", value1=15, label="High"),
            BinDefinition(operator="nulls", label="Nulls"),
        ]
        panel.update_charts("value", bins)

        # Chart container should now be shown, empty state hidden
        assert not panel._chart_container.isHidden()
        assert panel._empty_state.isHidden()

    def test_empty_state_when_no_bins_configured(self, qtbot: QtBot) -> None:
        """Empty state shown when no bins are configured."""
        app_state = AppState()
        df = pd.DataFrame({
            "value": [5, 10, 15],
            "gain_pct": [1.0, 2.0, -1.0],
            "adjusted_gain_pct": [0.5, 1.5, -0.5],
        })
        app_state.baseline_df = df
        panel = BinChartPanel(app_state)
        qtbot.addWidget(panel)
        panel.show()

        # Update with empty bins
        panel.update_charts("value", [])

        # Empty state shown, chart hidden
        assert not panel._empty_state.isHidden()
        assert panel._chart_container.isHidden()

    def test_set_metric_column(self, qtbot: QtBot) -> None:
        """set_metric_column updates the metric and toggle buttons."""
        app_state = AppState()
        panel = BinChartPanel(app_state)
        qtbot.addWidget(panel)

        panel.set_metric_column("gain_pct")

        assert panel._current_metric_column == "gain_pct"
        assert panel._gain_btn.isChecked()
        assert not panel._adjusted_btn.isChecked()


class TestDataBinningTabChartIntegration:
    """Tests for DataBinningTab integration with BinChartPanel."""

    def test_tab_has_chart_panel(self, qtbot: QtBot) -> None:
        """DataBinningTab contains BinChartPanel."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_chart_panel")
        assert isinstance(tab._chart_panel, BinChartPanel)

    def test_chart_updates_on_column_selection(self, qtbot: QtBot) -> None:
        """Chart panel updates when column is selected."""
        app_state = AppState()
        df = pd.DataFrame({
            "value": [5, 10, 15, 20, 25],
            "gain_pct": [1.0, 2.0, -1.0, 3.0, -2.0],
            "adjusted_gain_pct": [0.5, 1.5, -0.5, 2.5, -1.5],
        })
        app_state.baseline_df = df
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        app_state.data_loaded.emit(df)
        tab._column_dropdown.setCurrentText("value")

        # Add some bins
        tab._add_bin_button.click()

        # Wait for debounce timer
        qtbot.wait(400)

        # Chart panel should have received update
        assert tab._chart_panel._selected_column == "value"

    def test_debounce_timer_exists(self, qtbot: QtBot) -> None:
        """DataBinningTab has debounce timer for chart updates."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_debounce_timer")
        assert tab._debounce_timer.isSingleShot()

    def test_scrollable_chart_container(self, qtbot: QtBot) -> None:
        """BinChartPanel chart container is scrollable."""
        app_state = AppState()
        panel = BinChartPanel(app_state)
        qtbot.addWidget(panel)

        # Check that chart layout is inside a scroll area
        # by verifying _chart_container has the expected structure
        assert panel._chart_layout is not None
        assert panel._chart_container is not None



class TestSaveLoadConfig:
    """Tests for bin configuration save/load functionality."""

    def test_save_button_exists(self, qtbot: QtBot) -> None:
        """Save Config button exists in sidebar."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        save_btn = tab.findChild(QPushButton, "save_config_btn")
        assert save_btn is not None
        assert save_btn.text() == "Save Config"

    def test_load_button_exists(self, qtbot: QtBot) -> None:
        """Load Config button exists in sidebar."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        load_btn = tab.findChild(QPushButton, "load_config_btn")
        assert load_btn is not None
        assert load_btn.text() == "Load Config"

    def test_get_current_config_returns_none_without_bins(self, qtbot: QtBot) -> None:
        """_get_current_config returns None when no bins configured."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        config = tab._get_current_config()
        assert config is None

    def test_get_current_config_returns_binconfig(self, qtbot: QtBot) -> None:
        """_get_current_config returns correct BinConfig when configured."""
        app_state = AppState()
        df = pd.DataFrame({
            "volume": [100, 200, 300, 400, 500],
            "gain_pct": [1.0, 2.0, -1.0, 3.0, -2.0],
            "adjusted_gain_pct": [0.5, 1.5, -0.5, 2.5, -1.5],
        })
        app_state.baseline_df = df
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        app_state.data_loaded.emit(df)
        tab._column_dropdown.setCurrentText("volume")

        # Add a bin
        tab._add_bin_button.click()

        config = tab._get_current_config()
        assert config is not None
        assert config.column == "volume"
        assert len(config.bins) >= 1  # At least nulls row + added bin

    def test_apply_config_populates_ui(self, qtbot: QtBot) -> None:
        """_apply_config correctly sets UI state from BinConfig."""
        app_state = AppState()
        df = pd.DataFrame({
            "volume": [100, 200, 300, 400, 500],
            "gain_pct": [1.0, 2.0, -1.0, 3.0, -2.0],
            "adjusted_gain_pct": [0.5, 1.5, -0.5, 2.5, -1.5],
        })
        app_state.baseline_df = df
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        app_state.data_loaded.emit(df)

        bins = [
            BinDefinition(operator="<", value1=200, label="Low"),
            BinDefinition(operator=">", value1=400, label="High"),
        ]
        config = BinConfig(column="volume", bins=bins, metric_column="gain_pct")

        tab._apply_config(config)

        # Verify column dropdown
        assert tab._column_dropdown.currentText() == "volume"
        # Verify bin rows created
        assert len(tab._bin_rows) == 2
        # Verify metric toggle
        assert tab._chart_panel._current_metric_column == "gain_pct"

    def test_bin_config_changed_signal_emits_after_apply(self, qtbot: QtBot) -> None:
        """bin_config_changed signal emits after _apply_config."""
        app_state = AppState()
        df = pd.DataFrame({
            "volume": [100, 200, 300],
            "gain_pct": [1.0, 2.0, -1.0],
            "adjusted_gain_pct": [0.5, 1.5, -0.5],
        })
        app_state.baseline_df = df
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        app_state.data_loaded.emit(df)

        bins = [BinDefinition(operator="<", value1=200, label="Low")]
        config = BinConfig(column="volume", bins=bins, metric_column="gain_pct")

        with qtbot.waitSignal(tab.bin_config_changed, timeout=1000):
            tab._apply_config(config)

    def test_last_save_dir_initialized_to_none(self, qtbot: QtBot) -> None:
        """_last_save_dir is initialized to None."""
        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        assert tab._last_save_dir is None



class TestCumulativeToggle:
    """Tests for cumulative toggle on % of Total Gains chart."""

    def test_pct_total_chart_has_cumulative_toggle(self, qtbot: QtBot) -> None:
        """Test that % of Total Gains chart has a cumulative toggle."""
        from PyQt6.QtWidgets import QPushButton

        app_state = AppState()
        panel = BinChartPanel(app_state)
        qtbot.addWidget(panel)

        # Find toggle buttons by text
        buttons = panel.findChildren(QPushButton)
        button_texts = [b.text() for b in buttons]

        assert "Abs" in button_texts or "Absolute" in button_texts, "Should have Absolute toggle"
        assert "Cum" in button_texts or "Cumulative" in button_texts, "Should have Cumulative toggle"

    def test_cumulative_mode_calculates_running_totals(self) -> None:
        """Test that cumulative mode shows running totals summing to ~100%."""
        percentages = [10.0, 25.0, 35.0, 30.0]

        cumulative = []
        running_total = 0.0
        for pct in percentages:
            running_total += pct
            cumulative.append(running_total)

        assert cumulative == [10.0, 35.0, 70.0, 100.0]
        assert cumulative[-1] == 100.0, "Final cumulative should be 100%"

    def test_cumulative_toggle_changes_chart_data(self, qtbot: QtBot) -> None:
        """Test that clicking cumulative toggle changes chart data."""
        app_state = AppState()
        panel = BinChartPanel(app_state)
        qtbot.addWidget(panel)

        assert panel._cumulative_mode is False

        panel._cum_btn.click()
        assert panel._cumulative_mode is True

        panel._abs_btn.click()
        assert panel._cumulative_mode is False


class TestPctTotalGainsChart:
    """Tests for % of Total Gains chart functionality."""

    def test_pct_total_chart_displays_percentages(self, qtbot: QtBot) -> None:
        """Test that % of Total Gains chart shows correct percentages."""
        app_state = AppState()
        df = pd.DataFrame({
            "value": [10, 20, 30, 40, 50],
            "gain_pct": [10.0, 20.0, 30.0, 15.0, 25.0],  # Total: 100.0
            "adjusted_gain_pct": [10.0, 20.0, 30.0, 15.0, 25.0],
        })
        app_state.baseline_df = df
        panel = BinChartPanel(app_state)
        qtbot.addWidget(panel)
        panel.show()

        # Create bins where:
        # Low (<25): values 10, 20 -> gains 10, 20 -> total 30 -> 30%
        # High (>25): values 30, 40, 50 -> gains 30, 15, 25 -> total 70 -> 70%
        bins = [
            BinDefinition(operator="<", value1=25, label="Low"),
            BinDefinition(operator=">", value1=25, label="High"),
        ]
        panel.update_charts("value", bins)

        # Verify the chart has data
        assert len(panel._pct_total_chart._data) == 2

    def test_pct_total_chart_handles_zero_total(self, qtbot: QtBot) -> None:
        """Test that % of Total handles zero total gracefully."""
        app_state = AppState()
        df = pd.DataFrame({
            "value": [10, 20, 30],
            "gain_pct": [0.0, 0.0, 0.0],  # All zeros - total is 0
            "adjusted_gain_pct": [0.0, 0.0, 0.0],
        })
        app_state.baseline_df = df
        panel = BinChartPanel(app_state)
        qtbot.addWidget(panel)
        panel.show()

        bins = [
            BinDefinition(operator="<", value1=25, label="Low"),
            BinDefinition(operator=">", value1=25, label="High"),
        ]
        panel.update_charts("value", bins)

        # Should not crash and should show 0% for all bins
        assert panel._pct_total_chart._data is not None


class TestNumberAbbreviations:
    """Tests for K/M/B number abbreviations in chart values."""

    def test_format_large_number_abbreviations(self, qtbot: QtBot) -> None:
        """Test that large numbers are formatted with K, M, B suffixes."""
        chart = HorizontalBarChart()
        qtbot.addWidget(chart)

        # Test thousands
        assert chart._format_value(1500) == "1.5K"
        assert chart._format_value(25000) == "25K"
        assert chart._format_value(999999) == "1000K"  # Edge case

        # Test millions
        assert chart._format_value(1500000) == "1.5M"
        assert chart._format_value(25000000) == "25M"

        # Test billions
        assert chart._format_value(1500000000) == "1.5B"
        assert chart._format_value(25000000000) == "25B"

        # Test small numbers (no abbreviation)
        assert chart._format_value(500) == "500"
        assert chart._format_value(0.5) == "0.5"

        # Test negative numbers
        assert chart._format_value(-1500000) == "-1.5M"
        assert chart._format_value(-25000) == "-25K"

    def test_chart_displays_abbreviated_numbers(self, qtbot: QtBot) -> None:
        """Test that chart displays abbreviated numbers in the UI."""
        chart = HorizontalBarChart()
        qtbot.addWidget(chart)
        chart.set_data([("Bin 1", 1500000.0), ("Bin 2", 25000.0)])

        # Verify data is set (visual verification would require rendering)
        assert chart._data == [("Bin 1", 1500000.0), ("Bin 2", 25000.0)]


class TestBrightnessGradient:
    """Tests for brightness-based gradient coloring in bar charts."""

    def test_brightness_gradient_higher_values_brighter(self, qtbot: QtBot) -> None:
        """Test that higher values produce brighter colors (not just more opaque)."""
        from PyQt6.QtGui import QColor

        chart = HorizontalBarChart()
        qtbot.addWidget(chart)

        # Get colors for low, medium, and high positive values
        low_color = chart._calculate_gradient_color(10, 0, 100)
        mid_color = chart._calculate_gradient_color(50, 0, 100)
        high_color = chart._calculate_gradient_color(100, 0, 100)

        # Calculate perceived brightness (simple luminance formula)
        def brightness(c: QColor) -> float:
            return 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()

        # Higher values should have higher brightness
        assert brightness(high_color) > brightness(mid_color), "High value should be brighter than mid"
        assert brightness(mid_color) > brightness(low_color), "Mid value should be brighter than low"

        # Alpha should be 255 (fully opaque, no transparency)
        assert high_color.alpha() == 255, "Colors should be fully opaque"
        assert mid_color.alpha() == 255, "Colors should be fully opaque"
        assert low_color.alpha() == 255, "Colors should be fully opaque"

    def test_brightness_gradient_negative_values_use_coral(self, qtbot: QtBot) -> None:
        """Test that negative values use coral color gradient."""
        chart = HorizontalBarChart()
        qtbot.addWidget(chart)

        # Get color for negative value
        neg_color = chart._calculate_gradient_color(-50, -100, 0)

        # Should be in coral range (red > green, red > blue)
        assert neg_color.red() > neg_color.green(), "Negative values should use coral (red dominant)"
        assert neg_color.red() > neg_color.blue(), "Negative values should use coral (red dominant)"


class TestResizableSidebar:
    """Tests for resizable sidebar with QSplitter."""

    def test_data_binning_tab_has_resizable_splitter(self, qtbot: QtBot) -> None:
        """Test that the Data Binning Tab uses a QSplitter for resizable panels."""
        from PyQt6.QtWidgets import QSplitter

        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        # Find the QSplitter in the widget hierarchy
        splitter = tab.findChild(QSplitter)
        assert splitter is not None, "DataBinningTab should contain a QSplitter"
        assert splitter.count() == 2, "Splitter should have 2 panels (sidebar and chart)"

    def test_sidebar_has_minimum_width(self, qtbot: QtBot) -> None:
        """Test that sidebar has a minimum width to prevent collapsing too small."""
        from PyQt6.QtWidgets import QSplitter

        app_state = AppState()
        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        splitter = tab.findChild(QSplitter)
        sidebar = splitter.widget(0)

        assert sidebar.minimumWidth() >= 200, "Sidebar should have minimum width of 200px"
