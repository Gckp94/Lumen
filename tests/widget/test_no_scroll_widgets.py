"""Tests for NoScrollWidgets components."""

from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtGui import QWheelEvent
from pytestqt.qtbot import QtBot

from src.ui.components.no_scroll_widgets import NoScrollComboBox, NoScrollDoubleSpinBox


def create_wheel_event(scroll_up: bool = True) -> QWheelEvent:
    """Create a wheel event for testing.

    Args:
        scroll_up: If True, scroll up (positive delta). If False, scroll down (negative).

    Returns:
        QWheelEvent configured for the scroll direction.
    """
    delta = 120 if scroll_up else -120
    return QWheelEvent(
        QPointF(0, 0),  # position
        QPointF(0, 0),  # global position
        QPoint(0, delta),  # pixel delta
        QPoint(0, delta),  # angle delta
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,  # inverted
    )


class TestNoScrollComboBox:
    """Tests for NoScrollComboBox."""

    def test_ignores_wheel_when_not_focused(self, qtbot: QtBot) -> None:
        """Wheel event should be ignored when widget is not focused."""
        combo = NoScrollComboBox()
        combo.addItems(["Item 1", "Item 2", "Item 3"])
        combo.setCurrentIndex(1)  # Start at middle item
        qtbot.addWidget(combo)

        # Clear focus
        combo.clearFocus()
        assert not combo.hasFocus()

        # Simulate wheel event (scroll up)
        initial_index = combo.currentIndex()
        event = create_wheel_event(scroll_up=True)
        combo.wheelEvent(event)

        # Wheel should not change value when not focused
        assert combo.currentIndex() == initial_index

    def test_accepts_wheel_when_focused(self, qtbot: QtBot) -> None:
        """Wheel event should work when widget is focused."""
        combo = NoScrollComboBox()
        combo.addItems(["Item 1", "Item 2", "Item 3"])
        combo.setCurrentIndex(1)  # Start at middle item
        combo.show()
        qtbot.addWidget(combo)

        # Set focus
        combo.setFocus()
        qtbot.waitUntil(lambda: combo.hasFocus(), timeout=1000)

        # Simulate wheel event (scroll up should decrease index)
        initial_index = combo.currentIndex()
        event = create_wheel_event(scroll_up=True)
        combo.wheelEvent(event)

        # Wheel should change value when focused (scroll up decreases index)
        assert combo.currentIndex() != initial_index

    def test_has_strong_focus_policy(self, qtbot: QtBot) -> None:
        """NoScrollComboBox should have StrongFocus policy."""
        combo = NoScrollComboBox()
        qtbot.addWidget(combo)

        assert combo.focusPolicy() == Qt.FocusPolicy.StrongFocus

    def test_parent_argument_passed(self, qtbot: QtBot) -> None:
        """Parent argument should be passed to QComboBox."""
        from PyQt6.QtWidgets import QWidget

        parent = QWidget()
        qtbot.addWidget(parent)

        combo = NoScrollComboBox(parent)
        assert combo.parent() == parent


class TestNoScrollDoubleSpinBox:
    """Tests for NoScrollDoubleSpinBox."""

    def test_ignores_wheel_when_not_focused(self, qtbot: QtBot) -> None:
        """Wheel event should be ignored when widget is not focused."""
        spin = NoScrollDoubleSpinBox()
        spin.setRange(0, 100)
        spin.setValue(50)
        qtbot.addWidget(spin)

        # Clear focus
        spin.clearFocus()
        assert not spin.hasFocus()

        # Simulate wheel event
        initial_value = spin.value()
        event = create_wheel_event(scroll_up=True)
        spin.wheelEvent(event)

        # Wheel should not change value when not focused
        assert spin.value() == initial_value

    def test_accepts_wheel_when_focused(self, qtbot: QtBot) -> None:
        """Wheel event should work when widget is focused."""
        spin = NoScrollDoubleSpinBox()
        spin.setRange(0, 100)
        spin.setValue(50)
        spin.setSingleStep(1.0)  # Ensure step is set
        spin.show()
        qtbot.addWidget(spin)

        # Set focus
        spin.setFocus()
        qtbot.waitUntil(lambda: spin.hasFocus(), timeout=1000)

        # Simulate wheel event (scroll up should increase value)
        initial_value = spin.value()
        event = create_wheel_event(scroll_up=True)
        spin.wheelEvent(event)

        # Wheel should change value when focused (scroll up increases value)
        assert spin.value() != initial_value

    def test_has_strong_focus_policy(self, qtbot: QtBot) -> None:
        """NoScrollDoubleSpinBox should have StrongFocus policy."""
        spin = NoScrollDoubleSpinBox()
        qtbot.addWidget(spin)

        assert spin.focusPolicy() == Qt.FocusPolicy.StrongFocus

    def test_parent_argument_passed(self, qtbot: QtBot) -> None:
        """Parent argument should be passed to QDoubleSpinBox."""
        from PyQt6.QtWidgets import QWidget

        parent = QWidget()
        qtbot.addWidget(parent)

        spin = NoScrollDoubleSpinBox(parent)
        assert spin.parent() == parent


class TestNoScrollSpinBox:
    """Tests for NoScrollSpinBox (integer version)."""

    def test_ignores_wheel_when_not_focused(self, qtbot: QtBot) -> None:
        """Wheel event should be ignored when widget is not focused."""
        from src.ui.components.no_scroll_widgets import NoScrollSpinBox

        spin = NoScrollSpinBox()
        spin.setRange(0, 100)
        spin.setValue(50)
        qtbot.addWidget(spin)

        # Clear focus
        spin.clearFocus()
        assert not spin.hasFocus()

        # Simulate wheel event
        initial_value = spin.value()
        event = create_wheel_event(scroll_up=True)
        spin.wheelEvent(event)

        # Wheel should not change value when not focused
        assert spin.value() == initial_value

    def test_accepts_wheel_when_focused(self, qtbot: QtBot) -> None:
        """Wheel event should work when widget is focused."""
        from src.ui.components.no_scroll_widgets import NoScrollSpinBox

        spin = NoScrollSpinBox()
        spin.setRange(0, 100)
        spin.setValue(50)
        spin.setSingleStep(1)  # Ensure step is set
        spin.show()
        qtbot.addWidget(spin)

        # Set focus
        spin.setFocus()
        qtbot.waitUntil(lambda: spin.hasFocus(), timeout=1000)

        # Simulate wheel event (scroll up should increase value)
        initial_value = spin.value()
        event = create_wheel_event(scroll_up=True)
        spin.wheelEvent(event)

        # Wheel should change value when focused (scroll up increases value)
        assert spin.value() != initial_value

    def test_has_strong_focus_policy(self, qtbot: QtBot) -> None:
        """NoScrollSpinBox should have StrongFocus policy."""
        from src.ui.components.no_scroll_widgets import NoScrollSpinBox

        spin = NoScrollSpinBox()
        qtbot.addWidget(spin)

        assert spin.focusPolicy() == Qt.FocusPolicy.StrongFocus

    def test_parent_argument_passed(self, qtbot: QtBot) -> None:
        """Parent argument should be passed to QSpinBox."""
        from PyQt6.QtWidgets import QWidget

        from src.ui.components.no_scroll_widgets import NoScrollSpinBox

        parent = QWidget()
        qtbot.addWidget(parent)

        spin = NoScrollSpinBox(parent)
        assert spin.parent() == parent
