"""Exclude Column Panel component for Feature Insights.

Provides a vertical, searchable list of columns to exclude from analysis.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.ui.constants import Colors, Fonts, Spacing


class ExcludeColumnPanel(QWidget):
    """Vertical panel with searchable checkbox list for column exclusion.

    Signals:
        exclusion_changed: Emitted when any checkbox state changes.
    """

    exclusion_changed = pyqtSignal()

    def __init__(
        self,
        columns: list[str],
        excluded: set[str] | None = None,
        parent: QWidget | None = None,
    ):
        """Initialize the exclude column panel.

        Args:
            columns: List of column names to display.
            excluded: Set of column names to pre-check as excluded.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._columns = columns
        self._excluded = excluded or set()

        self._setup_ui()
        self._populate_list()
        self._apply_style()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        # Header
        header = QLabel("Exclude Columns")
        header.setObjectName("panelHeader")
        layout.addWidget(header)

        # Subheader with tooltip info
        subheader = QLabel("Lookahead bias prevention")
        subheader.setObjectName("panelSubheader")
        layout.addWidget(subheader)

        # Search input
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search columns...")
        self._search_input.textChanged.connect(self._on_search_changed)
        self._search_input.setClearButtonEnabled(True)
        layout.addWidget(self._search_input)

        # List widget with checkable items
        self._list_widget = QListWidget()
        self._list_widget.setFrameShape(QFrame.Shape.NoFrame)
        self._list_widget.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._list_widget, 1)

    def _populate_list(self) -> None:
        """Populate list with column checkboxes."""
        self._list_widget.clear()

        for col in sorted(self._columns):
            item = QListWidgetItem(col)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if col in self._excluded:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
            self._list_widget.addItem(item)

    def _apply_style(self) -> None:
        """Apply styling to the panel."""
        self.setStyleSheet(f"""
            QLabel#panelHeader {{
                font-family: "{Fonts.UI}";
                font-size: 14px;
                font-weight: bold;
                color: {Colors.TEXT_PRIMARY};
                padding: {Spacing.XS}px;
            }}
            QLabel#panelSubheader {{
                font-family: "{Fonts.UI}";
                font-size: 11px;
                color: {Colors.TEXT_SECONDARY};
                padding-left: {Spacing.XS}px;
                padding-bottom: {Spacing.SM}px;
            }}
            QLineEdit {{
                font-family: "{Fonts.UI}";
                font-size: 12px;
                color: {Colors.TEXT_PRIMARY};
                background-color: {Colors.BG_ELEVATED};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: {Spacing.SM}px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.SIGNAL_BLUE};
            }}
            QListWidget {{
                font-family: "{Fonts.DATA}";
                font-size: 12px;
                color: {Colors.TEXT_PRIMARY};
                background-color: {Colors.BG_SURFACE};
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                padding: {Spacing.SM}px {Spacing.XS}px;
                border-bottom: 1px solid {Colors.BG_BORDER};
            }}
            QListWidget::item:hover {{
                background-color: {Colors.BG_ELEVATED};
            }}
            QListWidget::item:selected {{
                background-color: {Colors.BG_ELEVATED};
            }}
            QListWidget::indicator {{
                width: 16px;
                height: 16px;
            }}
            QListWidget::indicator:unchecked {{
                border: 2px solid {Colors.TEXT_SECONDARY};
                border-radius: 3px;
                background-color: transparent;
            }}
            QListWidget::indicator:checked {{
                border: 2px solid {Colors.SIGNAL_CORAL};
                border-radius: 3px;
                background-color: {Colors.SIGNAL_CORAL};
            }}
        """)

    def _on_search_changed(self, text: str) -> None:
        """Filter list items based on search text."""
        search_lower = text.lower()
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            matches = search_lower in item.text().lower()
            item.setHidden(not matches)

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        """Handle item check state change."""
        self.exclusion_changed.emit()

    def get_excluded(self) -> set[str]:
        """Get the set of excluded column names.

        Returns:
            Set of column names that are checked (excluded).
        """
        excluded = set()
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                excluded.add(item.text())
        return excluded

    def set_columns(self, columns: list[str], excluded: set[str] | None = None) -> None:
        """Update the columns displayed in the panel.

        Args:
            columns: New list of column names.
            excluded: Set of column names to pre-check.
        """
        self._columns = columns
        self._excluded = excluded or set()
        self._populate_list()
