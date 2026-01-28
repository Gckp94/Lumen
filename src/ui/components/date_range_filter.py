"""DateRangeFilter component for filtering by date range."""

from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QCheckBox, QDateEdit, QHBoxLayout, QLabel, QWidget

from src.ui.constants import Colors, Spacing


class DateRangeFilter(QWidget):
    """Date range filter with start/end pickers and 'All Dates' toggle.

    Emits date_range_changed signal when range changes with ISO format strings.
    When 'All Dates' is checked, emits None values for start/end.

    Attributes:
        date_range_changed: Signal emitted when date range changes.
            Args: (start: str | None, end: str | None, all_dates: bool)
            Start/end are ISO format strings (YYYY-MM-DD) or None if all_dates=True.
    """

    date_range_changed = pyqtSignal(object, object, bool)  # start, end, all_dates

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize DateRangeFilter.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._all_dates = True
        self._setup_ui()
        self._apply_style()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the filter UI layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        # Label
        self._label = QLabel("Date Range:")
        layout.addWidget(self._label)

        # Start date picker
        self._start_date = QDateEdit()
        self._start_date.setCalendarPopup(True)
        self._start_date.setDate(QDate.currentDate().addMonths(-12))
        self._start_date.setEnabled(False)  # Disabled when All Dates checked
        self._start_date.setDisplayFormat("yyyy-MM-dd")
        layout.addWidget(self._start_date)

        # "to" label
        self._to_label = QLabel("to")
        layout.addWidget(self._to_label)

        # End date picker
        self._end_date = QDateEdit()
        self._end_date.setCalendarPopup(True)
        self._end_date.setDate(QDate.currentDate())
        self._end_date.setEnabled(False)
        self._end_date.setDisplayFormat("yyyy-MM-dd")
        layout.addWidget(self._end_date)

        # All Dates checkbox
        self._all_dates_checkbox = QCheckBox("All Dates")
        self._all_dates_checkbox.setChecked(True)
        layout.addWidget(self._all_dates_checkbox)

        layout.addStretch()

    def _apply_style(self) -> None:
        """Apply Observatory theme styling."""
        label_style = f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
            }}
        """
        self._label.setStyleSheet(label_style)
        self._to_label.setStyleSheet(label_style)

        date_edit_style = f"""
            QDateEdit {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 100px;
            }}
            QDateEdit:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QDateEdit:focus {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QDateEdit:disabled {{
                color: {Colors.TEXT_DISABLED};
                background-color: {Colors.BG_SURFACE};
            }}
            QDateEdit::drop-down {{
                border: none;
                width: 20px;
            }}
        """
        self._start_date.setStyleSheet(date_edit_style)
        self._end_date.setStyleSheet(date_edit_style)

        checkbox_style = f"""
            QCheckBox {{
                color: {Colors.TEXT_PRIMARY};
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid {Colors.BG_BORDER};
                background-color: {Colors.BG_ELEVATED};
            }}
            QCheckBox::indicator:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QCheckBox::indicator:checked {{
                background-color: {Colors.SIGNAL_CYAN};
                border-color: {Colors.SIGNAL_CYAN};
            }}
        """
        self._all_dates_checkbox.setStyleSheet(checkbox_style)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self._all_dates_checkbox.toggled.connect(self._on_all_dates_toggled)
        self._start_date.dateChanged.connect(self._on_date_changed)
        self._end_date.dateChanged.connect(self._on_date_changed)

    def _on_all_dates_toggled(self, checked: bool) -> None:
        """Handle 'All Dates' checkbox toggle.

        Args:
            checked: Whether checkbox is checked.
        """
        self._all_dates = checked
        self._start_date.setEnabled(not checked)
        self._end_date.setEnabled(not checked)
        self._emit_change()

    def _on_date_changed(self) -> None:
        """Handle date picker value change."""
        if not self._all_dates:
            self._validate_date_range()
            self._emit_change()

    def _validate_date_range(self) -> None:
        """Auto-correct if end date is before start date."""
        if self._end_date.date() < self._start_date.date():
            # Set end date to match start date
            self._end_date.blockSignals(True)
            self._end_date.setDate(self._start_date.date())
            self._end_date.blockSignals(False)

    def _emit_change(self) -> None:
        """Emit date_range_changed signal with current values."""
        if self._all_dates:
            self.date_range_changed.emit(None, None, True)
        else:
            start = self._start_date.date().toString(Qt.DateFormat.ISODate)
            end = self._end_date.date().toString(Qt.DateFormat.ISODate)
            self.date_range_changed.emit(start, end, False)

    def get_range(self) -> tuple[str | None, str | None, bool]:
        """Get current date range as ISO strings.

        Returns:
            Tuple of (start_iso, end_iso, all_dates).
            Strings are None if all_dates=True.
        """
        if self._all_dates:
            return (None, None, True)
        return (
            self._start_date.date().toString(Qt.DateFormat.ISODate),
            self._end_date.date().toString(Qt.DateFormat.ISODate),
            False,
        )

    def get_display_range(self) -> str:
        """Get formatted date range for display.

        Returns:
            Formatted string like 'Jan 15, 2024 - Jan 20, 2024' or empty string.
        """
        if self._all_dates:
            return ""
        start = self._start_date.date().toString("MMM d, yyyy")
        end = self._end_date.date().toString("MMM d, yyyy")
        return f"{start} - {end}"

    def reset(self) -> None:
        """Reset to default state (All Dates checked)."""
        self._all_dates_checkbox.blockSignals(True)
        self._all_dates_checkbox.setChecked(True)
        self._all_dates_checkbox.blockSignals(False)
        self._all_dates = True
        self._start_date.setEnabled(False)
        self._end_date.setEnabled(False)
        self._emit_change()

    def set_range(
        self, start: str | None, end: str | None, all_dates: bool
    ) -> None:
        """Set the date range programmatically.

        Args:
            start: Start date ISO string (YYYY-MM-DD) or None.
            end: End date ISO string (YYYY-MM-DD) or None.
            all_dates: Whether to enable 'All Dates' mode.
        """
        # Block signals during update
        self._all_dates_checkbox.blockSignals(True)
        self._start_date.blockSignals(True)
        self._end_date.blockSignals(True)

        self._all_dates = all_dates
        self._all_dates_checkbox.setChecked(all_dates)
        self._start_date.setEnabled(not all_dates)
        self._end_date.setEnabled(not all_dates)

        if start:
            date = QDate.fromString(start, Qt.DateFormat.ISODate)
            if date.isValid():
                self._start_date.setDate(date)

        if end:
            date = QDate.fromString(end, Qt.DateFormat.ISODate)
            if date.isValid():
                self._end_date.setDate(date)

        # Restore signals
        self._all_dates_checkbox.blockSignals(False)
        self._start_date.blockSignals(False)
        self._end_date.blockSignals(False)

        self._emit_change()

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        """Handle key press for keyboard navigation.

        Tab navigates between pickers, Enter confirms selection.
        """
        if event is None:
            return
        if event.key() == Qt.Key.Key_Tab:
            # Let Qt handle tab navigation
            super().keyPressEvent(event)
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # Emit change on Enter
            self._emit_change()
        else:
            super().keyPressEvent(event)
