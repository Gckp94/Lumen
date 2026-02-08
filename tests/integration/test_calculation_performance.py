# tests/integration/test_calculation_performance.py
"""Integration tests for calculation performance optimizations."""

from unittest.mock import MagicMock

import pandas as pd
import pytest
from pytestqt.qtbot import QtBot


class TestCalculationPerformance:
    """Integration tests for performance features."""

    def test_hidden_tabs_do_not_calculate(self, qtbot: QtBot) -> None:
        """Hidden tabs should not calculate on filter change."""
        from src.core.app_state import AppState

        app_state = AppState()

        # Create a mock dock widget that reports as not visible
        dock = MagicMock()
        dock.isVisible.return_value = True  # Widget is visible
        area = MagicMock()
        area.currentDockWidget.return_value = None  # But not the active tab
        dock.dockAreaWidget.return_value = area

        # The visibility tracker should return False
        assert app_state.visibility_tracker.is_visible(dock) is False

    def test_visible_tab_is_detected(self, qtbot: QtBot) -> None:
        """Visible and active tab should be detected correctly."""
        from src.core.app_state import AppState

        app_state = AppState()

        # Create a mock dock widget that is visible and active
        dock = MagicMock()
        dock.isVisible.return_value = True
        area = MagicMock()
        area.currentDockWidget.return_value = dock  # This dock is the active tab
        dock.dockAreaWidget.return_value = area
        container = MagicMock()
        container.isFloating.return_value = False
        dock.dockContainer.return_value = container

        # Should be visible
        assert app_state.visibility_tracker.is_visible(dock) is True

    def test_stale_tab_tracking(self, qtbot: QtBot) -> None:
        """Stale tabs should be tracked and cleared properly."""
        from src.core.app_state import AppState

        app_state = AppState()

        # Initially not stale
        assert app_state.visibility_tracker.is_stale("Statistics") is False

        # Mark as stale
        app_state.visibility_tracker.mark_stale("Statistics")
        assert app_state.visibility_tracker.is_stale("Statistics") is True

        # Clear stale
        app_state.visibility_tracker.clear_stale("Statistics")
        assert app_state.visibility_tracker.is_stale("Statistics") is False

    def test_notify_tab_visible_emits_signal(self, qtbot: QtBot) -> None:
        """notify_tab_visible should emit signal for stale tabs."""
        from src.core.app_state import AppState

        app_state = AppState()

        # Mark tab as stale
        app_state.visibility_tracker.mark_stale("Statistics")

        # Track signal emissions
        signals_received = []
        app_state.tab_became_visible.connect(lambda name: signals_received.append(name))

        # Notify that tab became visible
        app_state.notify_tab_visible("Statistics")

        # Signal should have been emitted and stale cleared
        assert "Statistics" in signals_received
        assert app_state.visibility_tracker.is_stale("Statistics") is False

    def test_loading_overlay_exists_on_tabs(self, qtbot: QtBot) -> None:
        """All integrated tabs should have loading overlay from mixin."""
        app_state = MagicMock()
        app_state.column_mapping = None
        app_state.visibility_tracker = MagicMock()
        app_state.filters = []
        app_state.first_trigger_enabled = True
        app_state.baseline_df = None
        app_state.filtered_df = None
        app_state.adjustment_params = MagicMock()
        app_state.metrics_user_inputs = MagicMock()
        app_state.baseline_metrics = None
        app_state.filtered_metrics = None

        # Test each integrated tab that uses BackgroundCalculationMixin
        from src.tabs.statistics_tab import StatisticsTab
        from src.tabs.breakdown import BreakdownTab

        for TabClass in [StatisticsTab, BreakdownTab]:
            tab = TabClass(app_state)
            qtbot.addWidget(tab)
            # The mixin provides _loading_overlay and set_dock_widget
            assert hasattr(tab, "_loading_overlay"), f"{TabClass.__name__} missing _loading_overlay"
            assert hasattr(tab, "set_dock_widget"), f"{TabClass.__name__} missing set_dock_widget"

    def test_background_calculation_worker(self, qtbot: QtBot) -> None:
        """CalculationWorker should run functions in background."""
        from src.core.calculation_worker import CalculationWorker

        # Test function that doubles input
        def calc_fn(data):
            return data * 2

        worker = CalculationWorker(calc_fn, 21)

        results = []
        worker.signals.finished.connect(lambda r: results.append(r))

        with qtbot.waitSignal(worker.signals.finished, timeout=5000):
            worker.run()

        assert results == [42]

    def test_calculation_worker_handles_errors(self, qtbot: QtBot) -> None:
        """CalculationWorker should emit error signal on exception."""
        from src.core.calculation_worker import CalculationWorker

        def failing_fn(data):
            raise ValueError("Test error")

        worker = CalculationWorker(failing_fn, None)

        errors = []
        worker.signals.error.connect(lambda e: errors.append(e))

        with qtbot.waitSignal(worker.signals.error, timeout=5000):
            worker.run()

        assert len(errors) == 1
        assert "Test error" in errors[0]

    def test_visibility_tracker_isolation(self, qtbot: QtBot) -> None:
        """Each AppState should have isolated visibility tracking."""
        from src.core.app_state import AppState

        state1 = AppState()
        state2 = AppState()

        state1.visibility_tracker.mark_stale("Tab1")

        # State2 should not see Tab1 as stale
        assert state1.visibility_tracker.is_stale("Tab1") is True
        assert state2.visibility_tracker.is_stale("Tab1") is False

    def test_floating_minimized_window_not_visible(self, qtbot: QtBot) -> None:
        """Dock in minimized floating window should not be visible."""
        from src.core.app_state import AppState

        app_state = AppState()

        dock = MagicMock()
        dock.isVisible.return_value = True
        area = MagicMock()
        area.currentDockWidget.return_value = dock
        dock.dockAreaWidget.return_value = area
        container = MagicMock()
        container.isFloating.return_value = True
        container.isMinimized.return_value = True  # Minimized!
        dock.dockContainer.return_value = container

        assert app_state.visibility_tracker.is_visible(dock) is False

    def test_not_stale_does_not_emit_signal(self, qtbot: QtBot) -> None:
        """notify_tab_visible should not emit signal for non-stale tabs."""
        from src.core.app_state import AppState

        app_state = AppState()

        # Tab is NOT stale
        assert app_state.visibility_tracker.is_stale("Statistics") is False

        signals_received = []
        app_state.tab_became_visible.connect(lambda name: signals_received.append(name))

        # Notify that tab became visible
        app_state.notify_tab_visible("Statistics")

        # No signal should have been emitted
        assert signals_received == []

    def test_multiple_stale_tabs(self, qtbot: QtBot) -> None:
        """Multiple tabs can be marked stale independently."""
        from src.core.app_state import AppState

        app_state = AppState()

        # Mark multiple tabs as stale
        app_state.visibility_tracker.mark_stale("Tab1")
        app_state.visibility_tracker.mark_stale("Tab2")
        app_state.visibility_tracker.mark_stale("Tab3")

        assert app_state.visibility_tracker.is_stale("Tab1") is True
        assert app_state.visibility_tracker.is_stale("Tab2") is True
        assert app_state.visibility_tracker.is_stale("Tab3") is True

        # Clear just one
        app_state.visibility_tracker.clear_stale("Tab2")

        assert app_state.visibility_tracker.is_stale("Tab1") is True
        assert app_state.visibility_tracker.is_stale("Tab2") is False
        assert app_state.visibility_tracker.is_stale("Tab3") is True

    def test_calculation_worker_started_signal(self, qtbot: QtBot) -> None:
        """CalculationWorker should emit started signal."""
        from src.core.calculation_worker import CalculationWorker

        def calc_fn(data):
            return data

        worker = CalculationWorker(calc_fn, "test")

        started_received = []
        worker.signals.started.connect(lambda: started_received.append(True))

        with qtbot.waitSignal(worker.signals.finished, timeout=5000):
            worker.run()

        assert started_received == [True]
