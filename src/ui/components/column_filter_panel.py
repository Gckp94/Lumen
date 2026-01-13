# src/ui/components/column_filter_panel.py
"""ColumnFilterPanel component for scrollable column filter list."""

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.core.models import FilterCriteria
from src.ui.components.column_filter_row import ColumnFilterRow
from src.ui.constants import Colors, Fonts, Spacing


class ColumnFilterPanel(QWidget):
    """Scrollable panel displaying all columns with inline filter inputs.

    Attributes:
        active_count_changed: Signal emitted when number of active filters changes.
        filters_changed: Signal emitted when any filter value changes.
        single_filter_applied: Signal emitted when a single filter is applied.
    """

    active_count_changed = pyqtSignal(int)
    filters_changed = pyqtSignal()
    single_filter_applied = pyqtSignal(object)  # Emits single FilterCriteria

    def __init__(
        self,
        columns: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize ColumnFilterPanel.

        Args:
            columns: List of column names to display.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._columns = columns or []
        self._rows: list[ColumnFilterRow] = []
        self._last_active_count = 0
        self._setup_ui()
        self._apply_style()
        self._build_rows()

    def _setup_ui(self) -> None:
        """Set up the panel UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.setSpacing(Spacing.SM)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search columns...")
        self._search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self._search_input)

        self._clear_search_btn = QPushButton("Clear")
        self._clear_search_btn.setFixedWidth(60)
        self._clear_search_btn.clicked.connect(self._on_clear_search)
        search_layout.addWidget(self._clear_search_btn)

        layout.addLayout(search_layout)

        # Header row
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(Spacing.SM, Spacing.XS, Spacing.SM, Spacing.XS)
        header_layout.setSpacing(Spacing.SM)

        col_header = QLabel("Column")
        col_header.setFixedWidth(140)
        header_layout.addWidget(col_header)

        mode_header = QLabel("Mode")
        mode_header.setFixedWidth(90)
        header_layout.addWidget(mode_header)

        min_header = QLabel("Min")
        min_header.setFixedWidth(70)
        header_layout.addWidget(min_header)

        max_header = QLabel("Max")
        max_header.setFixedWidth(70)
        header_layout.addWidget(max_header)

        header_layout.addStretch()
        layout.addWidget(header_frame)

        # Scrollable area for rows
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self._rows_container = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(0)
        self._rows_layout.addStretch()

        self._scroll_area.setWidget(self._rows_container)
        layout.addWidget(self._scroll_area)

    def _apply_style(self) -> None:
        """Apply Observatory theme styling."""
        self._search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 6px 10px;
                font-family: "{Fonts.UI}";
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
        """)

        self._clear_search_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 6px 10px;
                font-family: "{Fonts.UI}";
                font-size: 11px;
            }}
            QPushButton:hover {{
                border-color: {Colors.SIGNAL_CYAN};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)

        header_style = f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: "{Fonts.UI}";
                font-size: 11px;
                font-weight: bold;
            }}
        """
        for label in self.findChildren(QLabel):
            if label.parent() and isinstance(label.parent(), QFrame):
                label.setStyleSheet(header_style)

        self._scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
            }}
            QScrollBar:vertical {{
                background-color: {Colors.BG_ELEVATED};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {Colors.BG_BORDER};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {Colors.TEXT_SECONDARY};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        self._rows_container.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_SURFACE};
            }}
        """)

    def _build_rows(self) -> None:
        """Build rows for current columns."""
        # Clear existing rows
        for row in self._rows:
            row.deleteLater()
        self._rows.clear()

        # Create new rows with alternating backgrounds
        for i, column in enumerate(self._columns):
            row = ColumnFilterRow(column_name=column, alternate=(i % 2 == 1))
            row.values_changed.connect(self._on_row_values_changed)
            row.apply_clicked.connect(self._on_row_apply_clicked)
            self._rows.append(row)
            # Insert before stretch
            self._rows_layout.insertWidget(self._rows_layout.count() - 1, row)

    def _on_search_changed(self, text: str) -> None:
        """Handle search text changes.

        Args:
            text: Current search text.
        """
        search_lower = text.lower().strip()
        for row in self._rows:
            if search_lower:
                visible = search_lower in row.get_column_name().lower()
            else:
                visible = True
            row.setVisible(visible)

    def _on_clear_search(self) -> None:
        """Handle clear search button click."""
        self._search_input.clear()

    def _on_row_values_changed(self) -> None:
        """Handle value changes in any row."""
        active_count = sum(1 for row in self._rows if row.has_values())
        if active_count != self._last_active_count:
            self._last_active_count = active_count
            self.active_count_changed.emit(active_count)
        self.filters_changed.emit()

    def _on_row_apply_clicked(self, column: str) -> None:
        """Apply filter for a single column only.

        Args:
            column: The column name for which to apply the filter.
        """
        for row in self._rows:
            if row.get_column_name() == column:
                criteria = row.get_criteria()
                if criteria:
                    self.single_filter_applied.emit(criteria)
                break

    def get_active_criteria(self) -> list[FilterCriteria]:
        """Get FilterCriteria for all rows with valid values.

        Returns:
            List of FilterCriteria objects.
        """
        criteria_list = []
        for row in self._rows:
            criteria = row.get_criteria()
            if criteria is not None:
                criteria_list.append(criteria)
        return criteria_list

    def clear_all(self) -> None:
        """Clear all row values."""
        for row in self._rows:
            row.clear_values()

    def set_columns(self, columns: list[str]) -> None:
        """Update displayed columns.

        Args:
            columns: New list of column names.
        """
        self._columns = columns
        self._build_rows()
