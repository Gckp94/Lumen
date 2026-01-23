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
        """Initialize with StrongFocus policy.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def showPopup(self) -> None:
        """Show popup with dark theme colors applied."""
        # Apply palette right before showing to override native styling
        view = self.view()
        if view:
            palette = view.palette()
            palette.setColor(QPalette.ColorRole.Base, QColor(Colors.BG_ELEVATED))
            palette.setColor(QPalette.ColorRole.Text, QColor(Colors.TEXT_PRIMARY))
            palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 255, 212, 40))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor(Colors.TEXT_PRIMARY))
            palette.setColor(QPalette.ColorRole.Window, QColor(Colors.BG_ELEVATED))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(Colors.TEXT_PRIMARY))
            view.setPalette(palette)
            # Also set stylesheet directly on view
            view.setStyleSheet(f"""
                QListView {{
                    background-color: {Colors.BG_ELEVATED};
                    color: {Colors.TEXT_PRIMARY};
                }}
                QListView::item {{
                    color: {Colors.TEXT_PRIMARY};
                    padding: 4px 8px;
                }}
                QListView::item:selected {{
                    background-color: rgba(0, 255, 212, 0.15);
                }}
            """)
        super().showPopup()

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
