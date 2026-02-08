# tests/unit/test_background_calculation_mixin.py
"""Tests for BackgroundCalculationMixin."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from pytestqt.qtbot import QtBot
from PyQt6.QtCore import QThreadPool
from PyQt6.QtWidgets import QWidget

from src.ui.mixins.background_calculation import BackgroundCalculationMixin


class MixinTestWidget(BackgroundCalculationMixin, QWidget):
    """Widget using the mixin for testing purposes."""

    def __init__(self, app_state: MagicMock) -> None:
        QWidget.__init__(self)
        BackgroundCalculationMixin.__init__(self, app_state, "Test Tab")


class TestBackgroundCalculationMixin:
    """Tests for BackgroundCalculationMixin."""

    def test_start_calculation_shows_overlay(self, qtbot: QtBot) -> None:
        """start_background_calculation should show loading overlay."""
        app_state = MagicMock()
        widget = MixinTestWidget(app_state)
        qtbot.addWidget(widget)
        widget.show()  # Show parent widget first

        widget._setup_background_calculation()

        # Mock the calculation function
        def calc_fn(df):
            return {"result": 42}

        widget._start_background_calculation(
            calc_fn, pd.DataFrame({"a": [1]}), lambda r: None
        )

        assert widget._loading_overlay.isVisible()

    def test_calculation_complete_hides_overlay(self, qtbot: QtBot) -> None:
        """Completing calculation should hide loading overlay."""
        app_state = MagicMock()
        widget = MixinTestWidget(app_state)
        qtbot.addWidget(widget)

        widget._setup_background_calculation()
        widget._loading_overlay.show()

        # Simulate completion callback
        widget._on_background_calculation_complete({"result": 42})

        assert not widget._loading_overlay.isVisible()

    def test_skips_calculation_when_not_visible(self, qtbot: QtBot) -> None:
        """Should mark stale and skip when tab not visible."""
        app_state = MagicMock()
        dock_widget = MagicMock()
        dock_widget.isVisible.return_value = False

        app_state.visibility_tracker.is_visible.return_value = False

        widget = MixinTestWidget(app_state)
        widget._dock_widget = dock_widget
        qtbot.addWidget(widget)

        widget._setup_background_calculation()

        calculation_ran = []

        def calc_fn(df):
            calculation_ran.append(True)
            return {"result": 42}

        result = widget._maybe_start_background_calculation(
            calc_fn, pd.DataFrame({"a": [1]}), lambda r: None
        )

        assert result is False
        assert len(calculation_ran) == 0
        app_state.visibility_tracker.mark_stale.assert_called_once_with("Test Tab")
