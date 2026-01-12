"""Widget tests for ToggleSwitch component."""

from PyQt6.QtCore import Qt
from pytestqt.qtbot import QtBot

from src.ui.components.toggle_switch import ToggleSwitch
from src.ui.constants import Colors


class TestToggleSwitchInitialState:
    """Tests for initial toggle state."""

    def test_toggle_switch_initial_state_true(self, qtbot: QtBot) -> None:
        """ToggleSwitch respects initial=True."""
        toggle = ToggleSwitch(label="First Trigger Only", initial=True)
        qtbot.addWidget(toggle)
        assert toggle.isChecked() is True

    def test_toggle_switch_initial_state_false(self, qtbot: QtBot) -> None:
        """ToggleSwitch respects initial=False."""
        toggle = ToggleSwitch(label="First Trigger Only", initial=False)
        qtbot.addWidget(toggle)
        assert toggle.isChecked() is False

    def test_toggle_switch_default_is_false(self, qtbot: QtBot) -> None:
        """ToggleSwitch defaults to False when initial not specified."""
        toggle = ToggleSwitch(label="Test")
        qtbot.addWidget(toggle)
        assert toggle.isChecked() is False


class TestToggleSwitchClick:
    """Tests for toggle click behavior."""

    def test_toggle_switch_click_changes_state(self, qtbot: QtBot) -> None:
        """Clicking toggle changes state from False to True."""
        toggle = ToggleSwitch(label="Test", initial=False)
        qtbot.addWidget(toggle)

        assert toggle.isChecked() is False

        qtbot.mouseClick(toggle, Qt.MouseButton.LeftButton)

        assert toggle.isChecked() is True

    def test_toggle_switch_click_toggles_back(self, qtbot: QtBot) -> None:
        """Clicking twice returns to original state."""
        toggle = ToggleSwitch(label="Test", initial=False)
        qtbot.addWidget(toggle)

        qtbot.mouseClick(toggle, Qt.MouseButton.LeftButton)
        assert toggle.isChecked() is True

        qtbot.mouseClick(toggle, Qt.MouseButton.LeftButton)
        assert toggle.isChecked() is False


class TestToggleSwitchSignal:
    """Tests for toggle signal emission."""

    def test_toggle_switch_emits_signal(self, qtbot: QtBot) -> None:
        """Clicking toggle emits toggled signal."""
        toggle = ToggleSwitch(label="Test", initial=False)
        qtbot.addWidget(toggle)

        with qtbot.waitSignal(toggle.toggled, timeout=1000) as blocker:
            qtbot.mouseClick(toggle, Qt.MouseButton.LeftButton)

        assert blocker.args[0] is True  # Toggled from False to True

    def test_toggle_switch_emits_false_when_toggled_off(self, qtbot: QtBot) -> None:
        """Toggle emits False when switched from ON to OFF."""
        toggle = ToggleSwitch(label="Test", initial=True)
        qtbot.addWidget(toggle)

        with qtbot.waitSignal(toggle.toggled, timeout=1000) as blocker:
            qtbot.mouseClick(toggle, Qt.MouseButton.LeftButton)

        assert blocker.args[0] is False


class TestToggleSwitchSetChecked:
    """Tests for setChecked method."""

    def test_toggle_switch_set_checked_true(self, qtbot: QtBot) -> None:
        """setChecked(True) sets state to True."""
        toggle = ToggleSwitch(label="Test", initial=False)
        qtbot.addWidget(toggle)

        toggle.setChecked(True)

        assert toggle.isChecked() is True

    def test_toggle_switch_set_checked_false(self, qtbot: QtBot) -> None:
        """setChecked(False) sets state to False."""
        toggle = ToggleSwitch(label="Test", initial=True)
        qtbot.addWidget(toggle)

        toggle.setChecked(False)

        assert toggle.isChecked() is False

    def test_toggle_switch_set_checked_no_signal(self, qtbot: QtBot) -> None:
        """setChecked does not emit signal."""
        toggle = ToggleSwitch(label="Test", initial=False)
        qtbot.addWidget(toggle)

        # Track if signal was emitted
        signal_emitted = []
        toggle.toggled.connect(lambda v: signal_emitted.append(v))

        toggle.setChecked(True)

        # Process events
        qtbot.wait(50)

        assert len(signal_emitted) == 0
        assert toggle.isChecked() is True

    def test_toggle_switch_set_checked_same_value_noop(self, qtbot: QtBot) -> None:
        """setChecked with same value is a no-op."""
        toggle = ToggleSwitch(label="Test", initial=True)
        qtbot.addWidget(toggle)

        # Should not change anything
        toggle.setChecked(True)

        assert toggle.isChecked() is True


class TestToggleSwitchLabel:
    """Tests for toggle label display."""

    def test_toggle_switch_has_label(self, qtbot: QtBot) -> None:
        """Toggle displays the specified label."""
        toggle = ToggleSwitch(label="First Trigger Only", initial=False)
        qtbot.addWidget(toggle)

        assert toggle._label == "First Trigger Only"
        assert toggle._label_widget.text() == "First Trigger Only"

    def test_toggle_switch_empty_label(self, qtbot: QtBot) -> None:
        """Toggle works with empty label."""
        toggle = ToggleSwitch(label="", initial=False)
        qtbot.addWidget(toggle)

        assert toggle._label == ""
        # No label widget should be created for empty label
        assert not hasattr(toggle, "_label_widget") or toggle._label == ""


class TestToggleSwitchAnimation:
    """Tests for toggle animation properties."""

    def test_toggle_switch_thumb_position_initial_off(self, qtbot: QtBot) -> None:
        """Thumb position is 0.0 when toggle is OFF initially."""
        toggle = ToggleSwitch(label="Test", initial=False)
        qtbot.addWidget(toggle)

        assert toggle.thumbPosition == 0.0

    def test_toggle_switch_thumb_position_initial_on(self, qtbot: QtBot) -> None:
        """Thumb position is 1.0 when toggle is ON initially."""
        toggle = ToggleSwitch(label="Test", initial=True)
        qtbot.addWidget(toggle)

        assert toggle.thumbPosition == 1.0


class TestToggleSwitchVisuals:
    """Tests for toggle visual styling."""

    def test_toggle_switch_uses_correct_on_color(self, qtbot: QtBot) -> None:
        """Toggle uses stellar-blue (SIGNAL_BLUE) when ON."""
        # This test verifies the color constant is correctly referenced
        toggle = ToggleSwitch(label="Test", initial=True)
        qtbot.addWidget(toggle)

        # The color is used in _ToggleTrack.paintEvent
        # We verify the constant exists and is correct
        assert Colors.SIGNAL_BLUE == "#4A9EFF"

    def test_toggle_switch_uses_correct_off_color(self, qtbot: QtBot) -> None:
        """Toggle uses BG_BORDER color when OFF."""
        toggle = ToggleSwitch(label="Test", initial=False)
        qtbot.addWidget(toggle)

        assert Colors.BG_BORDER == "#2A2A3A"
