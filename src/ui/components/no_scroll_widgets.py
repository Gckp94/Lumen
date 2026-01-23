"""Custom widgets that ignore scroll wheel events when not focused.

This prevents accidental value changes when scrolling through forms.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette, QWheelEvent
from PyQt6.QtWidgets import QComboBox, QDoubleSpinBox, QSpinBox, QWidget

from src.ui.constants import Colors


class NoScrollComboBox(QComboBox):
    """QComboBox that ignores wheel events when not focused."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize with StrongFocus policy and dark theme styling.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # Apply dark theme stylesheet to combobox and its dropdown
        self.setStyleSheet(f"""
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                selection-background-color: rgba(0, 255, 212, 0.15);
                selection-color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                color: {Colors.TEXT_PRIMARY};
                background-color: {Colors.BG_ELEVATED};
                padding: 6px 12px;
                min-height: 24px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {Colors.BG_BORDER};
                color: {Colors.TEXT_PRIMARY};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: rgba(0, 255, 212, 0.15);
                color: {Colors.TEXT_PRIMARY};
            }}
        """)

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
