"""Widget tests for DataInputTab."""

import pandas as pd
from PyQt6.QtWidgets import QComboBox, QLineEdit, QPushButton
from pytestqt.qtbot import QtBot

from src.core.app_state import AppState
from src.core.models import ColumnMapping
from src.tabs.data_input import AdjustmentInputsPanel, DataInputTab


class TestDataInputTabWidgets:
    """Tests for DataInputTab widget structure."""

    def test_tab_has_select_file_button(self, qtbot: QtBot) -> None:
        """DataInputTab contains Select File button."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        button = tab.findChild(QPushButton, "select_file_button")
        assert button is not None
        assert "Select File" in button.text()

    def test_file_path_display_exists(self, qtbot: QtBot) -> None:
        """DataInputTab contains file path display."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        line_edit = tab.findChild(QLineEdit, "file_path_display")
        assert line_edit is not None

    def test_file_path_display_is_readonly(self, qtbot: QtBot) -> None:
        """File path display is read-only."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        line_edit = tab.findChild(QLineEdit, "file_path_display")
        assert line_edit is not None
        assert line_edit.isReadOnly()

    def test_load_button_exists(self, qtbot: QtBot) -> None:
        """DataInputTab contains Load Data button."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        button = tab.findChild(QPushButton, "load_data_button")
        assert button is not None
        assert "Load Data" in button.text()

    def test_load_button_initially_disabled(self, qtbot: QtBot) -> None:
        """Load Data button is disabled until file selected."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        button = tab.findChild(QPushButton, "load_data_button")
        assert button is not None
        assert not button.isEnabled()

    def test_sheet_selector_exists(self, qtbot: QtBot) -> None:
        """DataInputTab contains sheet selector."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        combo = tab.findChild(QComboBox, "sheet_selector")
        assert combo is not None

    def test_sheet_selector_initially_hidden(self, qtbot: QtBot) -> None:
        """Sheet selector is hidden until Excel file selected."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        combo = tab.findChild(QComboBox, "sheet_selector")
        assert combo is not None
        assert not combo.isVisible()

    def test_dataframe_property_initially_none(self, qtbot: QtBot) -> None:
        """DataFrame property is None before loading."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        assert tab.dataframe is None


class TestDataInputTabAdjustmentPanel:
    """Tests for AdjustmentInputsPanel integration in DataInputTab."""

    def test_tab_has_adjustment_panel(self, qtbot: QtBot) -> None:
        """DataInputTab contains AdjustmentInputsPanel."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        panel = tab.findChild(AdjustmentInputsPanel, "adjustment_inputs_panel")
        assert panel is not None

    def test_adjustment_panel_initially_hidden(self, qtbot: QtBot) -> None:
        """AdjustmentInputsPanel is hidden before mapping complete."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        panel = tab.findChild(AdjustmentInputsPanel, "adjustment_inputs_panel")
        assert panel is not None
        assert not panel.isVisible()

    def test_adjustment_debounce_timer_exists(self, qtbot: QtBot) -> None:
        """DataInputTab has debounce timer for adjustments."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        assert hasattr(tab, "_adjustment_debounce_timer")
        assert tab._adjustment_debounce_timer.interval() == 300
        assert tab._adjustment_debounce_timer.isSingleShot()

    def test_pending_adjustment_params_initially_none(self, qtbot: QtBot) -> None:
        """Pending adjustment params is None before mapping."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        assert tab._pending_adjustment_params is None


class TestBaselineMetricsFirstTriggersIntegration:
    """Integration tests verifying baseline metrics use first triggers only."""

    def test_baseline_metrics_uses_first_triggers_only(self, qtbot: QtBot, tmp_path) -> None:
        """Verify data_input calculates baseline metrics from first triggers only.

        This test verifies the full data loading flow by:
        1. Creating test CSV with multiple triggers per ticker-date
        2. Simulating the mapping completion workflow
        3. Asserting metrics are calculated from first triggers only

        Note: Default adjustment params (8% stop-loss, 5% efficiency) are applied.
        Gains are in decimal format (0.20 = 20%), MAE is in percentage format (5 = 5%).

        First triggers (before adjustment): AAPL +20%, MSFT +15%
        First triggers (after 5% efficiency): AAPL +15%, MSFT +10% -> 2 wins
        Later triggers (before adjustment): AAPL -10%, MSFT -8%
        Later triggers (after adjustment): AAPL -13%, MSFT -11% -> 2 losses

        If all triggers used: 2 wins, 2 losses -> 50% win rate
        With first triggers only: 2 wins -> 100% win rate
        """
        # Create test CSV with multiple triggers per ticker-date
        # Using decimal format for gains (0.20 = 20%), percentage format for MAE (5 = 5%)
        # Using gains > 5% so they remain positive after 5% efficiency deduction
        csv_content = """ticker,date,time,gain_pct,mae_pct
AAPL,2024-01-01,09:30,0.20,2
AAPL,2024-01-01,09:45,-0.10,15
MSFT,2024-01-01,09:30,0.15,3
MSFT,2024-01-01,09:35,-0.08,12
"""
        csv_file = tmp_path / "test_data.csv"
        csv_file.write_text(csv_content)

        # Create AppState and DataInputTab
        app_state = AppState()
        tab = DataInputTab(app_state=app_state)
        qtbot.addWidget(tab)

        # Load the DataFrame directly (simulating file load completion)
        df = pd.read_csv(csv_file)
        tab._df = df
        tab._selected_path = csv_file

        # Create column mapping matching our test CSV
        mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
            win_loss=None,
            win_loss_derived=True,
            breakeven_is_win=False,
        )

        # Trigger the mapping completion workflow (runs on background thread)
        with qtbot.waitSignal(tab.mapping_completed, timeout=10000):
            tab._on_mapping_continue(mapping)

        # Verify baseline_metrics in AppState
        metrics = app_state.baseline_metrics
        assert metrics is not None, "baseline_metrics should be set after mapping complete"

        # First triggers only: AAPL +20%, MSFT +15% -> both wins after 5% efficiency
        # (20% - 5% = 15%, 15% - 5% = 10%, both positive = wins)
        assert metrics.num_trades == 2, (
            f"Expected 2 trades (first triggers only), got {metrics.num_trades}"
        )
        assert metrics.win_rate == 100.0, (
            f"Expected 100% win rate (both first triggers are wins after adjustment), "
            f"got {metrics.win_rate}"
        )
        assert metrics.winner_count == 2, (
            f"Expected 2 winners, got {metrics.winner_count}"
        )
        assert metrics.loser_count == 0, (
            f"Expected 0 losers, got {metrics.loser_count}"
        )

    def test_baseline_df_contains_all_rows_with_trigger_numbers(
        self, qtbot: QtBot, tmp_path
    ) -> None:
        """Verify baseline_df retains all rows with trigger_number assigned.

        The baseline_df should contain ALL rows (not just first triggers),
        but each row should have a trigger_number assigned for filtering.
        """
        # Using decimal format for gains, percentage format for MAE
        csv_content = """ticker,date,time,gain_pct,mae_pct
AAPL,2024-01-01,09:30,0.10,2
AAPL,2024-01-01,09:45,-0.20,15
AAPL,2024-01-01,10:00,0.15,3
"""
        csv_file = tmp_path / "test_multi_trigger.csv"
        csv_file.write_text(csv_content)

        app_state = AppState()
        tab = DataInputTab(app_state=app_state)
        qtbot.addWidget(tab)

        df = pd.read_csv(csv_file)
        tab._df = df
        tab._selected_path = csv_file

        mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
            win_loss=None,
            win_loss_derived=True,
            breakeven_is_win=False,
        )

        with qtbot.waitSignal(tab.mapping_completed, timeout=10000):
            tab._on_mapping_continue(mapping)

        # baseline_df should have all 3 rows
        baseline_df = app_state.baseline_df
        assert baseline_df is not None
        assert len(baseline_df) == 3, (
            f"baseline_df should contain all 3 rows, got {len(baseline_df)}"
        )

        # trigger_number column should exist
        assert "trigger_number" in baseline_df.columns, (
            "baseline_df should have trigger_number column"
        )

        # Verify trigger numbers are assigned correctly
        # After sorting by time: 09:30 -> 1, 09:45 -> 2, 10:00 -> 3
        trigger_counts = baseline_df["trigger_number"].value_counts().to_dict()
        assert 1 in trigger_counts, "Should have at least one first trigger"
        assert trigger_counts.get(1, 0) == 1, "Should have exactly 1 first trigger"
        assert trigger_counts.get(2, 0) == 1, "Should have exactly 1 second trigger"
        assert trigger_counts.get(3, 0) == 1, "Should have exactly 1 third trigger"

    def test_metrics_differ_from_all_triggers_calculation(
        self, qtbot: QtBot, tmp_path
    ) -> None:
        """Verify baseline metrics differ from what all-triggers would produce.

        This test demonstrates that the first-trigger filtering actually changes
        the metrics - proving the filtering is working correctly.

        Note: Uses gains that remain meaningful after 5% efficiency adjustment.
        MAE in percentage format, gains in decimal format.

        First triggers (after adjustment):
        - AAPL: 15% - 5% = 10% (win)
        - MSFT: -8% - 5% = -13% (loss, stop-loss hit at 8%)
        -> 1 win, 1 loss = 50% win rate

        Later triggers would add more trades if included.
        """
        # Create data where first triggers have different stats than all triggers
        # Using decimal format for gains, percentage format for MAE
        csv_content = """ticker,date,time,gain_pct,mae_pct
AAPL,2024-01-01,09:30,0.15,2
AAPL,2024-01-01,09:45,0.30,3
MSFT,2024-01-01,09:30,-0.05,10
MSFT,2024-01-01,09:35,-0.25,20
"""
        csv_file = tmp_path / "test_diff_metrics.csv"
        csv_file.write_text(csv_content)

        app_state = AppState()
        tab = DataInputTab(app_state=app_state)
        qtbot.addWidget(tab)

        df = pd.read_csv(csv_file)
        tab._df = df
        tab._selected_path = csv_file

        mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
            win_loss=None,
            win_loss_derived=True,
            breakeven_is_win=False,
        )

        with qtbot.waitSignal(tab.mapping_completed, timeout=10000):
            tab._on_mapping_continue(mapping)

        metrics = app_state.baseline_metrics
        assert metrics is not None

        # First triggers only:
        # AAPL: 15% gain, 2% MAE (under 8% stop) -> 15% - 5% efficiency = 10% (win)
        # MSFT: -5% loss, 10% MAE (over 8% stop) -> -8% - 5% efficiency = -13% (loss)
        # -> 1 win, 1 loss = 50% win rate
        assert metrics.num_trades == 2
        assert metrics.winner_count == 1
        assert metrics.loser_count == 1
        assert metrics.win_rate == 50.0

        # If all triggers were used, we'd have 4 trades
        # This proves first-trigger filtering is active
        baseline_df = app_state.baseline_df
        assert len(baseline_df) == 4, "baseline_df should have all 4 rows"
        first_triggers_count = len(baseline_df[baseline_df["trigger_number"] == 1])
        assert first_triggers_count == 2, "Should have exactly 2 first triggers"
