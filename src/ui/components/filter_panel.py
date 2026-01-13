"""FilterPanel container for managing filters."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.models import FilterCriteria
from src.ui.components.date_range_filter import DateRangeFilter
from src.ui.components.filter_chip import FilterChip
from src.ui.components.time_range_filter import TimeRangeFilter
from src.ui.components.column_filter_panel import ColumnFilterPanel
from src.ui.components.filter_row import FilterRow
from src.ui.components.toggle_switch import ToggleSwitch
from src.ui.constants import Colors, Limits, Spacing


class FilterPanel(QWidget):
    """Panel for managing filter rows and displaying active filters.

    Attributes:
        filters_applied: Signal emitted with list of FilterCriteria when applied.
        filters_cleared: Signal emitted when all filters are cleared.
        date_range_changed: Signal emitted when date range changes.
            Args: (start: str | None, end: str | None, all_dates: bool)
        time_range_changed: Signal emitted when time range changes.
            Args: (start: str | None, end: str | None, all_times: bool)
    """

    filters_applied = pyqtSignal(list)  # list[FilterCriteria]
    filters_cleared = pyqtSignal()
    first_trigger_toggled = pyqtSignal(bool)
    date_range_changed = pyqtSignal(object, object, bool)  # start, end, all_dates
    time_range_changed = pyqtSignal(object, object, bool)  # start, end, all_times

    def __init__(
        self,
        columns: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize FilterPanel.

        Args:
            columns: Initial list of numeric column names.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._columns = columns or []
        self._filter_rows: list[FilterRow] = []
        self._filter_chips: list[FilterChip] = []
        self._active_filters: list[FilterCriteria] = []
        # Date range state
        self._date_start: str | None = None
        self._date_end: str | None = None
        self._all_dates: bool = True
        # Time range state
        self._time_start: str | None = None
        self._time_end: str | None = None
        self._all_times_time: bool = True
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        """Set up the panel UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, Spacing.MD, 0, Spacing.MD)
        layout.setSpacing(Spacing.SM)

        # Section header
        header = QLabel("Filters")
        header.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-weight: bold;
                font-size: 13px;
            }}
        """)
        layout.addWidget(header)

        # Date range filter (above filter rows)
        self._date_range_filter = DateRangeFilter()
        self._date_range_filter.date_range_changed.connect(self._on_date_range_changed)
        layout.addWidget(self._date_range_filter)

        # Time range filter
        self._time_range_filter = TimeRangeFilter()
        self._time_range_filter.time_range_changed.connect(self._on_time_range_changed)
        layout.addWidget(self._time_range_filter)

        # Chips area for active filters
        self._chips_frame = QFrame()
        self._chips_layout = QHBoxLayout(self._chips_frame)
        self._chips_layout.setContentsMargins(0, 0, 0, 0)
        self._chips_layout.setSpacing(Spacing.XS)
        self._chips_layout.addStretch()
        layout.addWidget(self._chips_frame)

        # Column filter panel (new scrollable inline filter system)
        self._column_filter_panel = ColumnFilterPanel(columns=self._columns)
        self._column_filter_panel.setMinimumHeight(200)
        self._column_filter_panel.setMaximumHeight(300)
        layout.addWidget(self._column_filter_panel)

        # Filter rows container (legacy - to be removed in Task 4)
        self._rows_container = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(Spacing.XS)
        layout.addWidget(self._rows_container)

        # First trigger toggle (above buttons)
        self._first_trigger_toggle = ToggleSwitch(
            label="First Trigger Only",
            initial=True,  # ON by default, matching AppState default
        )
        self._first_trigger_toggle.toggled.connect(self.first_trigger_toggled.emit)
        layout.addWidget(self._first_trigger_toggle)

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(Spacing.SM)

        self._add_btn = QPushButton("+ Add Filter")
        self._add_btn.clicked.connect(self._on_add_filter)
        btn_layout.addWidget(self._add_btn)

        self._apply_btn = QPushButton("Apply Filters")
        self._apply_btn.clicked.connect(self._on_apply_filters)
        btn_layout.addWidget(self._apply_btn)

        self._clear_btn = QPushButton("Clear All")
        self._clear_btn.clicked.connect(self._on_clear_filters)
        btn_layout.addWidget(self._clear_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()

    def _apply_style(self) -> None:
        """Apply Observatory theme styling."""
        primary_btn_style = f"""
            QPushButton {{
                background-color: {Colors.SIGNAL_CYAN};
                color: {Colors.BG_BASE};
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.SIGNAL_BLUE};
            }}
            QPushButton:disabled {{
                background-color: {Colors.BG_BORDER};
                color: {Colors.TEXT_DISABLED};
            }}
        """
        self._apply_btn.setStyleSheet(primary_btn_style)

        secondary_btn_style = f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                border-color: {Colors.SIGNAL_CYAN};
                color: {Colors.SIGNAL_CYAN};
            }}
            QPushButton:disabled {{
                color: {Colors.TEXT_DISABLED};
            }}
        """
        self._add_btn.setStyleSheet(secondary_btn_style)
        self._clear_btn.setStyleSheet(secondary_btn_style)

    def _get_used_columns(self) -> set[str]:
        """Get columns already used in filter rows.

        Returns:
            Set of column names currently in use.
        """
        used = set()
        for row in self._filter_rows:
            col = row.get_column()
            if col:
                used.add(col)
        return used

    def _get_available_columns(self) -> list[str]:
        """Get columns not yet used in filter rows.

        Returns:
            List of available column names.
        """
        used = self._get_used_columns()
        return [c for c in self._columns if c not in used]

    def _on_add_filter(self) -> None:
        """Handle add filter button click."""
        if len(self._filter_rows) >= Limits.MAX_FILTERS:
            return

        available = self._get_available_columns()
        if not available:
            return  # No columns left to filter

        row = FilterRow(available)
        row.remove_requested.connect(lambda: self._on_remove_row(row))
        row.column_changed.connect(self._on_filter_column_changed)
        self._filter_rows.append(row)
        self._rows_layout.addWidget(row)

        # Disable add button if at max or no more columns available
        if (
            len(self._filter_rows) >= Limits.MAX_FILTERS
            or len(self._get_available_columns()) == 0
        ):
            self._add_btn.setEnabled(False)

    def _on_filter_column_changed(self, old_column: str, new_column: str) -> None:
        """Handle column selection change in a filter row.

        Args:
            old_column: Previously selected column.
            new_column: Newly selected column.
        """
        # Update availability: old_column is now available, new_column is used
        # No need to actively update other rows' dropdowns since they're only
        # updated when adding new filters. This keeps the UI simple.
        # Re-check add button state
        if len(self._get_available_columns()) == 0:
            self._add_btn.setEnabled(False)
        elif len(self._filter_rows) < Limits.MAX_FILTERS:
            self._add_btn.setEnabled(True)

    def _on_date_range_changed(
        self, start: str | None, end: str | None, all_dates: bool
    ) -> None:
        """Handle date range filter change.

        Args:
            start: Start date ISO string or None.
            end: End date ISO string or None.
            all_dates: Whether 'All Dates' is checked.
        """
        self._date_start = start
        self._date_end = end
        self._all_dates = all_dates
        self.date_range_changed.emit(start, end, all_dates)

    def _on_time_range_changed(
        self, start: str | None, end: str | None, all_times: bool
    ) -> None:
        """Handle time range filter change.

        Args:
            start: Start time string (HH:MM:SS) or None.
            end: End time string (HH:MM:SS) or None.
            all_times: Whether 'All Times' is checked.
        """
        self._time_start = start
        self._time_end = end
        self._all_times_time = all_times
        self.time_range_changed.emit(start, end, all_times)

    def _on_remove_row(self, row: FilterRow) -> None:
        """Handle remove row request.

        Args:
            row: The FilterRow to remove.
        """
        if row in self._filter_rows:
            self._filter_rows.remove(row)
            row.deleteLater()

        # Re-enable add button if under limits and columns available
        if len(self._filter_rows) < Limits.MAX_FILTERS and self._get_available_columns():
            self._add_btn.setEnabled(True)

    def _on_apply_filters(self) -> None:
        """Handle apply filters button click."""
        # Get criteria from new ColumnFilterPanel
        criteria_list = self._column_filter_panel.get_active_criteria()

        # Also collect from legacy FilterRow system (for backward compatibility)
        for row in self._filter_rows:
            criteria = row.get_criteria()
            if criteria is not None:
                criteria_list.append(criteria)

        self._active_filters = criteria_list
        self._update_chips()
        self.filters_applied.emit(criteria_list)

    def _on_clear_filters(self) -> None:
        """Handle clear all filters button click."""
        # Clear column filter panel
        self._column_filter_panel.clear_all()

        # Clear filter rows (legacy)
        for row in self._filter_rows[:]:
            row.deleteLater()
        self._filter_rows.clear()

        # Clear chips
        for chip in self._filter_chips[:]:
            chip.deleteLater()
        self._filter_chips.clear()

        # Reset date range filter
        self._date_range_filter.reset()
        self._date_start = None
        self._date_end = None
        self._all_dates = True

        # Reset time range filter
        self._time_range_filter.reset()
        self._time_start = None
        self._time_end = None
        self._all_times_time = True

        self._active_filters.clear()
        self._add_btn.setEnabled(True)
        self.filters_cleared.emit()

    def _update_chips(self) -> None:
        """Update chip display based on active filters."""
        # Clear existing chips
        for chip in self._filter_chips[:]:
            chip.deleteLater()
        self._filter_chips.clear()

        # Add new chips (insert before stretch)
        for criteria in self._active_filters:
            chip = FilterChip(criteria)
            chip.removed.connect(self._on_chip_removed)
            self._filter_chips.append(chip)
            # Insert before stretch (at count - 1 position)
            self._chips_layout.insertWidget(
                self._chips_layout.count() - 1, chip
            )

    def _on_chip_removed(self, criteria: FilterCriteria) -> None:
        """Handle chip removal.

        Args:
            criteria: The FilterCriteria to remove.
        """
        if criteria in self._active_filters:
            self._active_filters.remove(criteria)

        self._update_chips()

        # Re-emit with updated list
        if self._active_filters:
            self.filters_applied.emit(self._active_filters)
        else:
            self.filters_cleared.emit()

    def set_columns(self, columns: list[str]) -> None:
        """Update available columns for filtering.

        Args:
            columns: List of numeric column names.
        """
        self._columns = columns
        self._column_filter_panel.set_columns(columns)
        # Legacy: update existing FilterRow instances
        for row in self._filter_rows:
            row.set_columns(columns)

    def get_date_range(self) -> tuple[str | None, str | None, bool]:
        """Get current date range.

        Returns:
            Tuple of (start_iso, end_iso, all_dates).
        """
        return (self._date_start, self._date_end, self._all_dates)

    def get_time_range(self) -> tuple[str | None, str | None, bool]:
        """Get current time range filter values.

        Returns:
            Tuple of (start_time, end_time, all_times).
            Times are HH:MM:SS strings or None if all_times=True.
        """
        return self._time_range_filter.get_range()
