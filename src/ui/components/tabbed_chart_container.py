"""Tabbed container for Monte Carlo charts."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QPushButton,
    QSizePolicy,
)

from src.ui.constants import Colors, Fonts, FontSizes, Spacing


class TabButton(QPushButton):
    """Pill-style tab button."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

    def _update_style(self) -> None:
        """Update button style based on checked state."""
        if self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.SIGNAL_CYAN};
                    color: {Colors.BG_BASE};
                    border: none;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-family: {Fonts.UI};
                    font-size: {FontSizes.BODY}px;
                    font-weight: 600;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {Colors.TEXT_SECONDARY};
                    border: 1px solid {Colors.BG_BORDER};
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-family: {Fonts.UI};
                    font-size: {FontSizes.BODY}px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {Colors.BG_ELEVATED};
                    color: {Colors.TEXT_PRIMARY};
                    border-color: {Colors.BG_BORDER};
                }}
            """)

    def setChecked(self, checked: bool) -> None:
        """Override to update style when checked state changes."""
        super().setChecked(checked)
        self._update_style()


class TabbedChartContainer(QWidget):
    """Container with horizontal tab bar and stacked chart content."""

    tab_changed = pyqtSignal(int)  # Emitted when tab changes

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tabs: list[tuple[str, TabButton, QWidget]] = []
        self._current_index = -1
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the container layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        # Tab bar
        self._tab_bar = QWidget()
        self._tab_bar_layout = QHBoxLayout(self._tab_bar)
        self._tab_bar_layout.setContentsMargins(0, 0, 0, 0)
        self._tab_bar_layout.setSpacing(Spacing.XS)
        self._tab_bar_layout.addStretch()
        layout.addWidget(self._tab_bar)

        # Content stack
        self._stack = QStackedWidget()
        self._stack.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self._stack, stretch=1)

    def add_tab(self, name: str, widget: QWidget) -> int:
        """Add a tab with the given name and content widget.

        Args:
            name: Tab display name.
            widget: Content widget to show when tab is active.

        Returns:
            Index of the new tab.
        """
        button = TabButton(name)
        index = len(self._tabs)

        # Insert button before the stretch
        self._tab_bar_layout.insertWidget(index, button)

        # Connect button click
        button.clicked.connect(lambda checked, i=index: self.set_current_index(i))

        # Add to stack
        self._stack.addWidget(widget)
        self._tabs.append((name, button, widget))

        # Select first tab by default
        if index == 0:
            self.set_current_index(0)

        return index

    def set_current_index(self, index: int) -> None:
        """Set the current active tab by index."""
        if index < 0 or index >= len(self._tabs):
            return

        if index == self._current_index:
            return

        # Update button states
        for i, (_, button, _) in enumerate(self._tabs):
            button.setChecked(i == index)

        # Update stack
        self._stack.setCurrentIndex(index)
        self._current_index = index
        self.tab_changed.emit(index)

    def current_index(self) -> int:
        """Return the current tab index."""
        return self._current_index

    def current_tab_name(self) -> str:
        """Return the current tab name."""
        if 0 <= self._current_index < len(self._tabs):
            return self._tabs[self._current_index][0]
        return ""

    def widget_at(self, index: int) -> QWidget | None:
        """Return the widget at the given index."""
        if 0 <= index < len(self._tabs):
            return self._tabs[index][2]
        return None
