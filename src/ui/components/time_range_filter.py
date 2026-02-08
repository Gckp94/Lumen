"""TimeRangeFilter widget for filtering by time of day."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTime, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QTimeEdit, QWidget

from src.ui.constants import Colors, Spacing


class TimeRangeFilter(QWidget):
    """Time range filter with start/end time pickers and 'All Times' toggle.

    Emits time_range_changed signal when range changes with HH:MM:SS strings.
    When 'All Times' is checked, emits None values for start/end.

    Attributes:
        time_range_changed: Signal emitted when time range changes.
            Args: (start: str | None, end: str | None, all_times: bool)
            Start/end are time strings (HH:MM:SS) or None if all_times=True.
    """

    time_range_changed = pyqtSignal(object, object, bool)  # start, end, all_times

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize TimeRangeFilter.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._all_times = True
        self._setup_ui()
        self._apply_style()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the filter UI layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        # Label
        self._label = QLabel("Time Range:")
        layout.addWidget(self._label)

        # Start time picker (default 9:30 AM)
        self._start_time = QTimeEdit()
        self._start_time.setDisplayFormat("HH:mm:ss")
        self._start_time.setTime(QTime(9, 30, 0))
        self._start_time.setEnabled(False)  # Disabled when All Times checked
        self._start_time.setToolTip("Type digits: 040000 for 04:00:00, or use arrows")
        layout.addWidget(self._start_time)

        # "to" label
        self._to_label = QLabel("to")
        layout.addWidget(self._to_label)

        # End time picker (default 4:00 PM)
        self._end_time = QTimeEdit()
        self._end_time.setDisplayFormat("HH:mm:ss")
        self._end_time.setTime(QTime(16, 0, 0))
        self._end_time.setEnabled(False)
        self._end_time.setToolTip("Type digits: 160000 for 16:00:00, or use arrows")
        layout.addWidget(self._end_time)

        # All Times checkbox
        self._all_times_checkbox = QCheckBox("All Times")
        self._all_times_checkbox.setChecked(True)
        layout.addWidget(self._all_times_checkbox)

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

        time_edit_style = f"""
            QTimeEdit {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 80px;
            }}
            QTimeEdit:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QTimeEdit:focus {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QTimeEdit:disabled {{
                color: {Colors.TEXT_DISABLED};
                background-color: {Colors.BG_SURFACE};
            }}
            QTimeEdit::up-button, QTimeEdit::down-button {{
                border: none;
                width: 16px;
            }}
        """
        self._start_time.setStyleSheet(time_edit_style)
        self._end_time.setStyleSheet(time_edit_style)

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
        self._all_times_checkbox.setStyleSheet(checkbox_style)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self._all_times_checkbox.toggled.connect(self._on_all_times_toggled)
        self._start_time.editingFinished.connect(self._on_time_changed)
        self._end_time.editingFinished.connect(self._on_time_changed)

    def _on_all_times_toggled(self, checked: bool) -> None:
        """Handle 'All Times' checkbox toggle.

        Args:
            checked: Whether checkbox is checked.
        """
        self._all_times = checked
        self._start_time.setEnabled(not checked)
        self._end_time.setEnabled(not checked)
        self._emit_change()

    def _on_time_changed(self) -> None:
        """Handle time picker value change."""
        if not self._all_times:
            self._validate_time_range()
            self._emit_change()

    def _validate_time_range(self) -> None:
        """Auto-correct if end time is before start time."""
        if self._end_time.time() < self._start_time.time():
            # Set end time to match start time
            self._end_time.blockSignals(True)
            self._end_time.setTime(self._start_time.time())
            self._end_time.blockSignals(False)

    def _emit_change(self) -> None:
        """Emit time_range_changed signal with current values."""
        if self._all_times:
            self.time_range_changed.emit(None, None, True)
        else:
            start = self._start_time.time().toString("HH:mm:ss")
            end = self._end_time.time().toString("HH:mm:ss")
            self.time_range_changed.emit(start, end, False)

    def get_range(self) -> tuple[str | None, str | None, bool]:
        """Get current time range as HH:MM:SS strings.

        Returns:
            Tuple of (start_time, end_time, all_times).
            Strings are None if all_times=True.
        """
        if self._all_times:
            return (None, None, True)
        return (
            self._start_time.time().toString("HH:mm:ss"),
            self._end_time.time().toString("HH:mm:ss"),
            False,
        )

    def get_display_range(self) -> str:
        """Get formatted time range for display.

        Returns:
            Formatted string like '09:30 AM - 04:00 PM' or empty string.
        """
        if self._all_times:
            return ""
        start = self._start_time.time().toString("hh:mm AP")
        end = self._end_time.time().toString("hh:mm AP")
        return f"{start} - {end}"

    def reset(self) -> None:
        """Reset to default state (All Times checked)."""
        self._all_times_checkbox.blockSignals(True)
        self._all_times_checkbox.setChecked(True)
        self._all_times_checkbox.blockSignals(False)
        self._all_times = True
        self._start_time.setEnabled(False)
        self._end_time.setEnabled(False)
        self._emit_change()

    def set_range(
        self, start: str | None, end: str | None, all_times: bool
    ) -> None:
        """Set the time range programmatically.

        Args:
            start: Start time string (HH:MM:SS) or None.
            end: End time string (HH:MM:SS) or None.
            all_times: Whether to enable 'All Times' mode.
        """
        # Block signals during update
        self._all_times_checkbox.blockSignals(True)
        self._start_time.blockSignals(True)
        self._end_time.blockSignals(True)

        self._all_times = all_times
        self._all_times_checkbox.setChecked(all_times)
        self._start_time.setEnabled(not all_times)
        self._end_time.setEnabled(not all_times)

        if start:
            time = QTime.fromString(start, "HH:mm:ss")
            if time.isValid():
                self._start_time.setTime(time)

        if end:
            time = QTime.fromString(end, "HH:mm:ss")
            if time.isValid():
                self._end_time.setTime(time)

        # Restore signals
        self._all_times_checkbox.blockSignals(False)
        self._start_time.blockSignals(False)
        self._end_time.blockSignals(False)

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
