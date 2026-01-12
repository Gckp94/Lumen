"""Widget tests for CalculationStatusIndicator (Story 4.1)."""

import pytest
from pytestqt.qtbot import QtBot

from src.core.app_state import AppState
from src.ui.components.calculation_status import CalculationStatusIndicator


class TestCalculationStatusIndicator:
    """Tests for CalculationStatusIndicator widget."""

    @pytest.fixture
    def app_state(self) -> AppState:
        """Create AppState for testing."""
        return AppState()

    @pytest.fixture
    def indicator(
        self, qtbot: QtBot, app_state: AppState
    ) -> CalculationStatusIndicator:
        """Create CalculationStatusIndicator for testing."""
        indicator = CalculationStatusIndicator(app_state)
        qtbot.addWidget(indicator)
        return indicator

    def test_indicator_initially_hidden(
        self, indicator: CalculationStatusIndicator
    ) -> None:
        """Indicator is hidden on initialization."""
        assert not indicator.isVisible()

    def test_indicator_shows_calculating_on_started_signal(
        self, qtbot: QtBot, app_state: AppState, indicator: CalculationStatusIndicator
    ) -> None:
        """Indicator shows 'Calculating...' when calculation started signal emitted."""
        app_state.filtered_calculation_started.emit()

        assert indicator.isVisible()
        assert indicator._status_label.text() == "Calculating..."

    def test_indicator_shows_ready_on_completed_signal(
        self, qtbot: QtBot, app_state: AppState, indicator: CalculationStatusIndicator
    ) -> None:
        """Indicator shows 'Ready' when calculation completed signal emitted."""
        # First start, then complete
        app_state.filtered_calculation_started.emit()
        app_state.filtered_calculation_completed.emit()

        assert indicator.isVisible()
        assert indicator._status_label.text() == "Ready"

    def test_indicator_calculating_styled_with_amber(
        self, qtbot: QtBot, app_state: AppState, indicator: CalculationStatusIndicator
    ) -> None:
        """Indicator uses SIGNAL_AMBER color during calculation."""
        app_state.filtered_calculation_started.emit()

        # Verify amber color is in the stylesheet (SIGNAL_AMBER = #FFAA00)
        stylesheet = indicator._status_label.styleSheet()
        assert "#FFAA00" in stylesheet or "255, 170, 0" in stylesheet

    def test_indicator_ready_styled_with_cyan(
        self, qtbot: QtBot, app_state: AppState, indicator: CalculationStatusIndicator
    ) -> None:
        """Indicator uses SIGNAL_CYAN color when ready."""
        app_state.filtered_calculation_started.emit()
        app_state.filtered_calculation_completed.emit()

        # Verify cyan color is in the stylesheet (SIGNAL_CYAN = #00FFD4)
        stylesheet = indicator._status_label.styleSheet()
        assert "#00FFD4" in stylesheet or "0, 255, 212" in stylesheet

    def test_indicator_pulse_timer_active_during_calculation(
        self, qtbot: QtBot, app_state: AppState, indicator: CalculationStatusIndicator
    ) -> None:
        """Pulse animation timer is active during calculation."""
        assert not indicator._pulse_timer.isActive()

        app_state.filtered_calculation_started.emit()
        assert indicator._pulse_timer.isActive()

        app_state.filtered_calculation_completed.emit()
        assert not indicator._pulse_timer.isActive()

    def test_indicator_fade_timer_starts_after_ready(
        self, qtbot: QtBot, app_state: AppState, indicator: CalculationStatusIndicator
    ) -> None:
        """Fade timer starts after showing Ready status."""
        app_state.filtered_calculation_started.emit()
        app_state.filtered_calculation_completed.emit()

        # Fade timer should be active (waiting to fade out)
        assert indicator._fade_timer.isActive()

    def test_indicator_cleanup_stops_timers(
        self, indicator: CalculationStatusIndicator, app_state: AppState
    ) -> None:
        """Cleanup method stops all timers."""
        app_state.filtered_calculation_started.emit()

        indicator.cleanup()

        assert not indicator._pulse_timer.isActive()
        assert not indicator._fade_timer.isActive()
        assert not indicator._fade_out_timer.isActive()

    def test_indicator_new_calculation_cancels_fade(
        self, qtbot: QtBot, app_state: AppState, indicator: CalculationStatusIndicator
    ) -> None:
        """Starting new calculation cancels any ongoing fade animation."""
        # Complete first calculation
        app_state.filtered_calculation_started.emit()
        app_state.filtered_calculation_completed.emit()
        assert indicator._fade_timer.isActive()

        # Start new calculation
        app_state.filtered_calculation_started.emit()

        # Fade should be cancelled
        assert not indicator._fade_timer.isActive()
        assert indicator._status_label.text() == "Calculating..."
