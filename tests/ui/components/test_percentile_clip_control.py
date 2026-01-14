"""Tests for PercentileClipControl widget."""

import pytest
from PyQt6.QtWidgets import QApplication

from src.ui.components.percentile_clip_control import PercentileClipControl


@pytest.fixture(scope="module")
def app():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestPercentileClipControl:
    """Tests for PercentileClipControl widget."""

    def test_initial_state(self, app) -> None:
        """Widget initializes with 99% selected."""
        widget = PercentileClipControl()
        assert widget.selected_percentile == 99.0

    def test_preset_percentiles_available(self, app) -> None:
        """Preset percentile options are available."""
        widget = PercentileClipControl()
        # Should have 95%, 99%, 99.9% presets
        assert widget._combo.count() >= 3

    def test_clip_signal_emitted_on_button_click(self, app, qtbot) -> None:
        """clip_requested signal emits selected percentile."""
        widget = PercentileClipControl()

        received = []
        widget.clip_requested.connect(lambda p: received.append(p))

        widget._clip_btn.click()

        assert len(received) == 1
        assert received[0] == 99.0  # Default selection

    def test_selection_changes_percentile(self, app) -> None:
        """Changing combo selection updates selected_percentile."""
        widget = PercentileClipControl()

        # Select 95% (first item)
        widget._combo.setCurrentIndex(0)
        assert widget.selected_percentile == 95.0

    def test_smart_auto_fit_signal(self, app, qtbot) -> None:
        """smart_auto_fit_requested signal emits on button click."""
        widget = PercentileClipControl()

        received = []
        widget.smart_auto_fit_requested.connect(lambda: received.append(True))

        widget._smart_btn.click()

        assert len(received) == 1

    def test_set_clipped_indicator(self, app) -> None:
        """set_clipped_state updates visual indicator."""
        widget = PercentileClipControl()

        # Initially not clipped
        widget.set_clipped_state(False)
        assert "clipped" not in widget._indicator.text().lower()

        # Set to clipped
        widget.set_clipped_state(True, 99.0)
        assert "99" in widget._indicator.text()
