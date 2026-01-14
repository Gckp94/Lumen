"""Tests for AxisControlPanel widget."""

import pytest
from PyQt6.QtWidgets import QApplication

from src.ui.components.axis_control_panel import AxisControlPanel


@pytest.fixture(scope="module")
def app():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestAxisControlPanel:
    """Tests for AxisControlPanel widget."""

    def test_panel_initializes(self, app) -> None:
        """AxisControlPanel initializes without error."""
        widget = AxisControlPanel()
        assert widget is not None
