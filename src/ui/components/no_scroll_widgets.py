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

    def addItem(self, text: str, userData: object = None) -> None:
        """Add item with dark theme colors."""
        super().addItem(text, userData)
        self._style_item(self.count() - 1)

    def addItems(self, texts: list[str]) -> None:
        """Add items with dark theme colors."""
        start_index = self.count()
        super().addItems(texts)
        for i in range(start_index, self.count()):
            self._style_item(i)

    def _style_item(self, index: int) -> None:
        """Apply dark theme colors to a specific item."""
        self.setItemData(index, QColor(Colors.TEXT_PRIMARY), Qt.ItemDataRole.ForegroundRole)
        self.setItemData(index, QColor(Colors.BG_ELEVATED), Qt.ItemDataRole.BackgroundRole)

    def showPopup(self) -> None:
        """Show popup with forced dark styling."""
        # Force palette on popup right before showing
        popup = self.view()
        if popup:
            popup.setAutoFillBackground(True)
            palette = popup.palette()
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Base, QColor(Colors.BG_ELEVATED))
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Text, QColor(Colors.TEXT_PRIMARY))
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Window, QColor(Colors.BG_ELEVATED))
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.WindowText, QColor(Colors.TEXT_PRIMARY))
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.AlternateBase, QColor(Colors.BG_ELEVATED))
            popup.setPalette(palette)

            # Force re-style items
            for i in range(self.count()):
                self._style_item(i)

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
