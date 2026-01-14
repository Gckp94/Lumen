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

    def test_percentile_clip_signals_forwarded(self, app, qtbot) -> None:
        """AxisControlPanel forwards percentile clip signals."""
        widget = AxisControlPanel()

        clip_received = []
        widget.percentile_clip_requested.connect(lambda p: clip_received.append(p))

        smart_received = []
        widget.smart_auto_fit_requested.connect(lambda: smart_received.append(True))

        # Trigger clip
        widget._percentile_control._clip_btn.click()
        assert len(clip_received) == 1

        # Trigger smart auto-fit
        widget._percentile_control._smart_btn.click()
        assert len(smart_received) == 1

    def test_set_clipped_state(self, app) -> None:
        """set_clipped_state updates indicator."""
        widget = AxisControlPanel()

        widget.set_clipped_state(True, 99.0)
        assert "99" in widget._percentile_control._indicator.text()

        widget.set_clipped_state(False)
        assert widget._percentile_control._indicator.text() == ""
