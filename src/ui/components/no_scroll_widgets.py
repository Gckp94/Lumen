"""Custom widgets that ignore scroll wheel events when not focused.

This prevents accidental value changes when scrolling through forms.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QComboBox, QDoubleSpinBox, QSpinBox, QWidget


class NoScrollComboBox(QComboBox):
    """QComboBox that ignores wheel events when not focused."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize with StrongFocus policy.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event: QWheelEvent | None) -> None:
        """Ignore wheel events unless widget has focus.

        Args:
            event: Wheel event to handle.
        """
        if event is None:
            return
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class NoScrollDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox that ignores wheel events when not focused."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize with StrongFocus policy.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event: QWheelEvent | None) -> None:
        """Ignore wheel events unless widget has focus.

        Args:
            event: Wheel event to handle.
        """
        if event is None:
            return
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class NoScrollSpinBox(QSpinBox):
    """QSpinBox that ignores wheel events when not focused."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize with StrongFocus policy.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event: QWheelEvent | None) -> None:
        """Ignore wheel events unless widget has focus.

        Args:
            event: Wheel event to handle.
        """
        if event is None:
            return
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()
