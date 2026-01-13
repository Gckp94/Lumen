"""Tests for AxisModeToggle component."""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.ui.components.axis_mode_toggle import AxisModeToggle, AxisMode


@pytest.fixture(scope="module")
def app():
    """Create QApplication for widget tests."""
    app = QApplication.instance() or QApplication([])
    yield app


def test_toggle_default_mode_is_trades(app) -> None:
    """Default mode should be TRADES."""
    toggle = AxisModeToggle()
    assert toggle.mode == AxisMode.TRADES


def test_toggle_emits_signal_on_mode_change(app, qtbot) -> None:
    """mode_changed signal should emit when mode changes."""
    toggle = AxisModeToggle()

    with qtbot.waitSignal(toggle.mode_changed, timeout=1000) as blocker:
        toggle.set_mode(AxisMode.DATE)

    assert blocker.args == [AxisMode.DATE]


def test_toggle_switches_mode_on_click(app, qtbot) -> None:
    """Clicking inactive option should switch mode."""
    toggle = AxisModeToggle()
    assert toggle.mode == AxisMode.TRADES

    # Click the DATE option
    with qtbot.waitSignal(toggle.mode_changed):
        toggle._date_btn.click()

    assert toggle.mode == AxisMode.DATE
