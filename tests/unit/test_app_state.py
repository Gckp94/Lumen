"""Unit tests for AppState."""

import pandas as pd
from pytestqt.qtbot import QtBot

from src.core.app_state import AppState
from src.core.models import ColumnMapping


class TestAppStateInitialization:
    """Tests for AppState initialization."""

    def test_initial_state_has_none_values(self) -> None:
        """AppState initializes with None/empty values."""
        state = AppState()

        assert state.raw_df is None
        assert state.baseline_df is None
        assert state.filtered_df is None
        assert state.column_mapping is None
        assert state.filters == []
        assert state.baseline_metrics is None
        assert state.filtered_metrics is None

    def test_initial_first_trigger_enabled(self) -> None:
        """First trigger is enabled by default."""
        state = AppState()

        assert state.first_trigger_enabled is True


class TestAppStateHasData:
    """Tests for AppState.has_data property."""

    def test_has_data_false_when_no_data(self) -> None:
        """has_data returns False when no data loaded."""
        state = AppState()

        assert state.has_data is False

    def test_has_data_false_when_only_baseline_df(self) -> None:
        """has_data returns False when only baseline_df is set."""
        state = AppState()
        state.baseline_df = pd.DataFrame({"a": [1, 2, 3]})

        assert state.has_data is False

    def test_has_data_false_when_only_column_mapping(self) -> None:
        """has_data returns False when only column_mapping is set."""
        state = AppState()
        state.column_mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
        )

        assert state.has_data is False

    def test_has_data_true_when_both_set(self) -> None:
        """has_data returns True when baseline_df and column_mapping set."""
        state = AppState()
        state.baseline_df = pd.DataFrame({"a": [1, 2, 3]})
        state.column_mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
        )

        assert state.has_data is True


class TestAppStateSignals:
    """Tests for AppState signal emissions."""

    def test_data_loaded_signal_emits(self, qtbot: QtBot) -> None:
        """data_loaded signal emits correctly."""
        state = AppState()
        test_df = pd.DataFrame({"a": [1, 2]})

        with qtbot.waitSignal(state.data_loaded, timeout=100):
            state.data_loaded.emit(test_df)

    def test_column_mapping_changed_signal_emits(self, qtbot: QtBot) -> None:
        """column_mapping_changed signal emits correctly."""
        state = AppState()
        mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
        )

        with qtbot.waitSignal(state.column_mapping_changed, timeout=100):
            state.column_mapping_changed.emit(mapping)

    def test_baseline_calculated_signal_emits(self, qtbot: QtBot) -> None:
        """baseline_calculated signal emits correctly."""
        state = AppState()

        with qtbot.waitSignal(state.baseline_calculated, timeout=100):
            state.baseline_calculated.emit(None)

    def test_first_trigger_toggled_signal_emits(self, qtbot: QtBot) -> None:
        """first_trigger_toggled signal emits correctly."""
        state = AppState()

        with qtbot.waitSignal(state.first_trigger_toggled, timeout=100):
            state.first_trigger_toggled.emit(False)

    def test_request_tab_change_signal_emits(self, qtbot: QtBot) -> None:
        """request_tab_change signal emits correctly."""
        state = AppState()

        with qtbot.waitSignal(state.request_tab_change, timeout=100):
            state.request_tab_change.emit(2)

    def test_state_corrupted_signal_emits(self, qtbot: QtBot) -> None:
        """state_corrupted signal emits correctly."""
        state = AppState()

        with qtbot.waitSignal(state.state_corrupted, timeout=100):
            state.state_corrupted.emit("Error message")

    def test_state_recovered_signal_emits(self, qtbot: QtBot) -> None:
        """state_recovered signal emits correctly."""
        state = AppState()

        with qtbot.waitSignal(state.state_recovered, timeout=100):
            state.state_recovered.emit()

    def test_all_metrics_ready_signal_emits(self, qtbot: QtBot) -> None:
        """all_metrics_ready signal emits correctly."""
        state = AppState()

        with qtbot.waitSignal(state.all_metrics_ready, timeout=100):
            state.all_metrics_ready.emit(None)


class TestAppStateScenarioStorage:
    """Tests for AppState scenario storage fields."""

    def test_app_state_has_scenario_storage(self) -> None:
        """Test AppState has stop_scenarios and offset_scenarios attributes."""
        state = AppState()

        assert hasattr(state, 'stop_scenarios')
        assert hasattr(state, 'offset_scenarios')
        assert state.stop_scenarios is None
        assert state.offset_scenarios is None

    def test_app_state_has_all_metrics_ready_signal(self) -> None:
        """Test AppState has all_metrics_ready signal."""
        state = AppState()

        assert hasattr(state, 'all_metrics_ready')
        # Verify it's a signal by checking it has emit method
        assert hasattr(state.all_metrics_ready, 'emit')
