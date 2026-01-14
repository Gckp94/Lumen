"""Flow layout that wraps widgets to new lines."""

from PyQt6.QtCore import QPoint, QRect, QSize, Qt
from PyQt6.QtWidgets import QLayout, QLayoutItem, QSizePolicy, QWidget


class FlowLayout(QLayout):
    """Layout that arranges widgets in a flow, wrapping to new lines.

    Based on Qt's FlowLayout example, adapted for PyQt6.
    Widgets are arranged left-to-right, wrapping to new lines as needed.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        margin: int = 0,
        spacing: int = -1,
    ) -> None:
        """Initialize FlowLayout.

        Args:
            parent: Parent widget.
            margin: Margin around the layout.
            spacing: Spacing between items. -1 uses widget spacing.
        """
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def __del__(self) -> None:
        """Clean up layout items."""
        while self._items:
            self.takeAt(0)

    def addItem(self, item: QLayoutItem) -> None:
        """Add item to layout."""
        self._items.append(item)

    def count(self) -> int:
        """Return number of items in layout."""
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:
        """Return item at index."""
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:
        """Remove and return item at index."""
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:
        """Return expanding directions (none for flow layout)."""
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        """Flow layout height depends on width."""
        return True

    def heightForWidth(self, width: int) -> int:
        """Calculate height needed for given width."""
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        """Set geometry of all items."""
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        """Return preferred size."""
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        """Return minimum size needed."""
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())

        margins = self.contentsMargins()
        size += QSize(
            margins.left() + margins.right(),
            margins.top() + margins.bottom(),
        )
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        """Perform layout of items.

        Args:
            rect: Rectangle to layout within.
            test_only: If True, just calculate height without moving items.

        Returns:
            Height needed for the layout.
        """
        margins = self.contentsMargins()
        effective_rect = rect.adjusted(
            margins.left(),
            margins.top(),
            -margins.right(),
            -margins.bottom(),
        )

        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self._items:
            widget = item.widget()
            if widget is None:
                continue
            # Skip hidden widgets only during actual layout, not during height calculation
            if not test_only and not widget.isVisible():
                continue

            space_x = spacing
            space_y = spacing
            if space_x == -1:
                space_x = widget.style().layoutSpacing(
                    QSizePolicy.ControlType.PushButton,
                    QSizePolicy.ControlType.PushButton,
                    Qt.Orientation.Horizontal,
                )
            if space_y == -1:
                space_y = widget.style().layoutSpacing(
                    QSizePolicy.ControlType.PushButton,
                    QSizePolicy.ControlType.PushButton,
                    Qt.Orientation.Vertical,
                )

            next_x = x + item.sizeHint().width() + space_x

            # Wrap to next line if needed
            if next_x - space_x > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y() + margins.bottom()
