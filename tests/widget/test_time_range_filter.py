"""Widget tests for TimeRangeFilter component."""

from PyQt6.QtCore import QTime
from pytestqt.qtbot import QtBot

from src.ui.components.time_range_filter import TimeRangeFilter
from src.ui.constants import Colors


class TestTimeRangeFilterInitialState:
    """Tests for initial time range filter state."""

    def test_initial_state_all_times(self, qtbot: QtBot) -> None:
        """TimeRangeFilter starts with 'All Times' checked."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        assert filter_widget._all_times is True
        assert filter_widget._all_times_checkbox.isChecked() is True
        assert filter_widget._start_time.isEnabled() is False
        assert filter_widget._end_time.isEnabled() is False

    def test_initial_start_time_default(self, qtbot: QtBot) -> None:
        """TimeRangeFilter starts with default start time of 9:30 AM."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        expected = QTime(9, 30, 0)
        assert filter_widget._start_time.time() == expected

    def test_initial_end_time_default(self, qtbot: QtBot) -> None:
        """TimeRangeFilter starts with default end time of 4:00 PM."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        expected = QTime(16, 0, 0)
        assert filter_widget._end_time.time() == expected

    def test_initial_get_range_returns_none(self, qtbot: QtBot) -> None:
        """get_range returns None values when All Times is checked."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        start, end, all_times = filter_widget.get_range()
        assert start is None
        assert end is None
        assert all_times is True


class TestTimeRangeFilterSignals:
    """Tests for signal emission."""

    def test_emits_signal_on_checkbox_toggle(self, qtbot: QtBot) -> None:
        """Unchecking 'All Times' emits time_range_changed signal."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        with qtbot.waitSignal(filter_widget.time_range_changed, timeout=1000) as blocker:
            filter_widget._all_times_checkbox.setChecked(False)

        start, end, all_times = blocker.args
        assert start == "09:30:00"
        assert end == "16:00:00"
        assert all_times is False

    def test_emits_signal_on_start_time_change(self, qtbot: QtBot) -> None:
        """Changing start time emits time_range_changed signal."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        # First uncheck All Times to enable the time pickers
        filter_widget._all_times_checkbox.setChecked(False)

        with qtbot.waitSignal(filter_widget.time_range_changed, timeout=1000) as blocker:
            filter_widget._start_time.setTime(QTime(10, 0, 0))

        start, end, all_times = blocker.args
        assert start == "10:00:00"
        assert end == "16:00:00"
        assert all_times is False

    def test_emits_signal_on_end_time_change(self, qtbot: QtBot) -> None:
        """Changing end time emits time_range_changed signal."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        # First uncheck All Times to enable the time pickers
        filter_widget._all_times_checkbox.setChecked(False)

        with qtbot.waitSignal(filter_widget.time_range_changed, timeout=1000) as blocker:
            filter_widget._end_time.setTime(QTime(15, 30, 0))

        start, end, all_times = blocker.args
        assert start == "09:30:00"
        assert end == "15:30:00"
        assert all_times is False

    def test_emits_signal_on_recheck_all_times(self, qtbot: QtBot) -> None:
        """Re-checking 'All Times' emits signal with None values."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        # First uncheck, then re-check
        filter_widget._all_times_checkbox.setChecked(False)

        with qtbot.waitSignal(filter_widget.time_range_changed, timeout=1000) as blocker:
            filter_widget._all_times_checkbox.setChecked(True)

        start, end, all_times = blocker.args
        assert start is None
        assert end is None
        assert all_times is True


class TestTimeRangeFilterGetRange:
    """Tests for get_range method."""

    def test_get_range_returns_time_strings(self, qtbot: QtBot) -> None:
        """get_range returns HH:MM:SS formatted time strings."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        # Uncheck All Times to enable range
        filter_widget._all_times_checkbox.setChecked(False)

        start, end, all_times = filter_widget.get_range()
        assert start == "09:30:00"
        assert end == "16:00:00"
        assert all_times is False

    def test_get_range_after_time_change(self, qtbot: QtBot) -> None:
        """get_range reflects changed time values."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        filter_widget._all_times_checkbox.setChecked(False)
        filter_widget._start_time.setTime(QTime(8, 0, 0))
        filter_widget._end_time.setTime(QTime(12, 30, 45))

        start, end, all_times = filter_widget.get_range()
        assert start == "08:00:00"
        assert end == "12:30:45"
        assert all_times is False

    def test_get_range_with_all_times_checked(self, qtbot: QtBot) -> None:
        """get_range returns None when All Times is checked."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        start, end, all_times = filter_widget.get_range()
        assert start is None
        assert end is None
        assert all_times is True


class TestTimeRangeFilterReset:
    """Tests for reset method."""

    def test_reset_returns_to_all_times(self, qtbot: QtBot) -> None:
        """reset() returns filter to 'All Times' checked state."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        # Modify state
        filter_widget._all_times_checkbox.setChecked(False)
        filter_widget._start_time.setTime(QTime(10, 0, 0))
        filter_widget._end_time.setTime(QTime(14, 0, 0))

        # Reset
        filter_widget.reset()

        # Verify state
        assert filter_widget._all_times is True
        assert filter_widget._all_times_checkbox.isChecked() is True
        assert filter_widget._start_time.isEnabled() is False
        assert filter_widget._end_time.isEnabled() is False

    def test_reset_emits_signal(self, qtbot: QtBot) -> None:
        """reset() emits time_range_changed signal with None values."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        # Modify state
        filter_widget._all_times_checkbox.setChecked(False)

        with qtbot.waitSignal(filter_widget.time_range_changed, timeout=1000) as blocker:
            filter_widget.reset()

        start, end, all_times = blocker.args
        assert start is None
        assert end is None
        assert all_times is True

    def test_reset_get_range_returns_none(self, qtbot: QtBot) -> None:
        """After reset(), get_range returns None values."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        # Modify and reset
        filter_widget._all_times_checkbox.setChecked(False)
        filter_widget.reset()

        start, end, all_times = filter_widget.get_range()
        assert start is None
        assert end is None
        assert all_times is True


class TestTimeRangeFilterValidation:
    """Tests for time range validation."""

    def test_end_time_auto_corrected_if_before_start(self, qtbot: QtBot) -> None:
        """End time is auto-corrected if set before start time."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        filter_widget._all_times_checkbox.setChecked(False)

        # Set start time after end time
        filter_widget._start_time.setTime(QTime(17, 0, 0))

        # End time should be auto-corrected to match start
        assert filter_widget._end_time.time() == QTime(17, 0, 0)


class TestTimeRangeFilterDisplayRange:
    """Tests for display range formatting."""

    def test_get_display_range_empty_when_all_times(self, qtbot: QtBot) -> None:
        """get_display_range returns empty string when All Times checked."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        assert filter_widget.get_display_range() == ""

    def test_get_display_range_formatted(self, qtbot: QtBot) -> None:
        """get_display_range returns formatted time range."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        filter_widget._all_times_checkbox.setChecked(False)

        display = filter_widget.get_display_range()
        # Format is "hh:mm AP - hh:mm AP"
        assert "09:30" in display
        assert "04:00" in display
        assert " - " in display


class TestTimeRangeFilterStyling:
    """Tests for Observatory theme styling."""

    def test_time_edit_has_themed_style(self, qtbot: QtBot) -> None:
        """Time edit widgets have Observatory theme styling."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        start_style = filter_widget._start_time.styleSheet()
        assert Colors.BG_ELEVATED in start_style
        assert Colors.TEXT_PRIMARY in start_style
        assert Colors.SIGNAL_CYAN in start_style

    def test_checkbox_has_themed_style(self, qtbot: QtBot) -> None:
        """Checkbox has Observatory theme styling."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        checkbox_style = filter_widget._all_times_checkbox.styleSheet()
        assert Colors.TEXT_PRIMARY in checkbox_style
        assert Colors.SIGNAL_CYAN in checkbox_style

    def test_labels_have_secondary_text_color(self, qtbot: QtBot) -> None:
        """Labels use secondary text color."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        label_style = filter_widget._label.styleSheet()
        assert Colors.TEXT_SECONDARY in label_style


class TestTimeRangeFilterUI:
    """Tests for UI layout and components."""

    def test_has_label(self, qtbot: QtBot) -> None:
        """Filter has 'Time Range:' label."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        assert filter_widget._label.text() == "Time Range:"

    def test_has_to_label(self, qtbot: QtBot) -> None:
        """Filter has 'to' label between time pickers."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        assert filter_widget._to_label.text() == "to"

    def test_checkbox_text(self, qtbot: QtBot) -> None:
        """Checkbox has 'All Times' text."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        assert filter_widget._all_times_checkbox.text() == "All Times"

    def test_time_edit_display_format(self, qtbot: QtBot) -> None:
        """Time edits use HH:mm:ss display format."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        assert filter_widget._start_time.displayFormat() == "HH:mm:ss"
        assert filter_widget._end_time.displayFormat() == "HH:mm:ss"

    def test_start_time_has_input_tooltip(self, qtbot: QtBot) -> None:
        """Start time widget has tooltip explaining digit input."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        tooltip = filter_widget._start_time.toolTip()
        assert "040000" in tooltip
        assert "04:00:00" in tooltip

    def test_end_time_has_input_tooltip(self, qtbot: QtBot) -> None:
        """End time widget has tooltip explaining digit input."""
        filter_widget = TimeRangeFilter()
        qtbot.addWidget(filter_widget)

        tooltip = filter_widget._end_time.toolTip()
        assert "160000" in tooltip
        assert "16:00:00" in tooltip
