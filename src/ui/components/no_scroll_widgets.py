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
        self._apply_dark_theme()

    def _apply_dark_theme(self) -> None:
        """Apply dark theme to the combobox dropdown."""
        # Set palette on the view
        view = self.view()
        if view:
            palette = view.palette()
            palette.setColor(QPalette.ColorRole.Text, QColor(Colors.TEXT_PRIMARY))
            palette.setColor(QPalette.ColorRole.Base, QColor(Colors.BG_ELEVATED))
            palette.setColor(QPalette.ColorRole.Window, QColor(Colors.BG_ELEVATED))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(Colors.TEXT_PRIMARY))
            view.setPalette(palette)

    def addItem(self, text: str, userData: object = None) -> None:
        """Add item with dark theme foreground color."""
        super().addItem(text, userData)
        # Set foreground color on the newly added item
        index = self.count() - 1
        self.setItemData(index, QColor(Colors.TEXT_PRIMARY), Qt.ItemDataRole.ForegroundRole)

    def addItems(self, texts: list[str]) -> None:
        """Add items with dark theme foreground color."""
        start_index = self.count()
        super().addItems(texts)
        # Set foreground color on all newly added items
        for i in range(start_index, self.count()):
            self.setItemData(i, QColor(Colors.TEXT_PRIMARY), Qt.ItemDataRole.ForegroundRole)

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
