"""Unit tests for DateRangeFilter component."""

from PyQt6.QtCore import QDate
from pytestqt.qtbot import QtBot

from src.ui.components.date_range_filter import DateRangeFilter


class TestDateRangeFilterInitialization:
    """Tests for DateRangeFilter initialization."""

    def test_default_all_dates_checked(self, qtbot: QtBot) -> None:
        """All Dates checkbox is checked by default."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        assert widget._all_dates_checkbox.isChecked() is True
        assert widget._all_dates is True

    def test_date_pickers_disabled_by_default(self, qtbot: QtBot) -> None:
        """Date pickers are disabled when All Dates is checked."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        assert widget._start_date.isEnabled() is False
        assert widget._end_date.isEnabled() is False

    def test_start_date_default_one_year_ago(self, qtbot: QtBot) -> None:
        """Start date defaults to one year ago."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        expected = QDate.currentDate().addMonths(-12)
        assert widget._start_date.date() == expected

    def test_end_date_default_today(self, qtbot: QtBot) -> None:
        """End date defaults to today."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        assert widget._end_date.date() == QDate.currentDate()


class TestDateRangeFilterAllDatesToggle:
    """Tests for All Dates checkbox behavior."""

    def test_unchecking_enables_date_pickers(self, qtbot: QtBot) -> None:
        """Unchecking All Dates enables date pickers."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        widget._all_dates_checkbox.setChecked(False)

        assert widget._start_date.isEnabled() is True
        assert widget._end_date.isEnabled() is True
        assert widget._all_dates is False

    def test_rechecking_disables_date_pickers(self, qtbot: QtBot) -> None:
        """Re-checking All Dates disables date pickers."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        # Uncheck then re-check
        widget._all_dates_checkbox.setChecked(False)
        widget._all_dates_checkbox.setChecked(True)

        assert widget._start_date.isEnabled() is False
        assert widget._end_date.isEnabled() is False
        assert widget._all_dates is True


class TestDateRangeFilterSignals:
    """Tests for signal emissions."""

    def test_signal_emitted_on_checkbox_toggle(self, qtbot: QtBot) -> None:
        """date_range_changed signal emitted when checkbox toggled."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        with qtbot.waitSignal(widget.date_range_changed, timeout=1000) as blocker:
            widget._all_dates_checkbox.setChecked(False)

        start, end, all_dates = blocker.args
        assert all_dates is False
        assert start is not None  # ISO string
        assert end is not None

    def test_signal_emits_none_when_all_dates(self, qtbot: QtBot) -> None:
        """Signal emits None for start/end when All Dates is checked."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        # First uncheck, then check to trigger signal
        widget._all_dates_checkbox.setChecked(False)

        with qtbot.waitSignal(widget.date_range_changed, timeout=1000) as blocker:
            widget._all_dates_checkbox.setChecked(True)

        start, end, all_dates = blocker.args
        assert all_dates is True
        assert start is None
        assert end is None

    def test_signal_emitted_on_date_change(self, qtbot: QtBot) -> None:
        """Signal emitted when date picker value changes."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        # Enable date pickers
        widget._all_dates_checkbox.setChecked(False)

        with qtbot.waitSignal(widget.date_range_changed, timeout=1000) as blocker:
            widget._start_date.setDate(QDate(2024, 6, 15))

        start, end, all_dates = blocker.args
        assert all_dates is False
        assert start == "2024-06-15"

    def test_signal_emits_iso_format_dates(self, qtbot: QtBot) -> None:
        """Signal emits dates in ISO format (YYYY-MM-DD)."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        widget._all_dates_checkbox.setChecked(False)
        widget._start_date.setDate(QDate(2024, 1, 15))
        widget._end_date.setDate(QDate(2024, 1, 20))

        start, end, _ = widget.get_range()
        assert start == "2024-01-15"
        assert end == "2024-01-20"


class TestDateRangeFilterValidation:
    """Tests for date range validation."""

    def test_end_before_start_auto_corrects(self, qtbot: QtBot) -> None:
        """End date before start date auto-corrects to match start."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        # Enable date pickers
        widget._all_dates_checkbox.setChecked(False)

        # Set start to Jan 20
        widget._start_date.setDate(QDate(2024, 1, 20))

        # Try to set end to Jan 15 (before start)
        widget._end_date.setDate(QDate(2024, 1, 15))

        # End should be corrected to match start
        assert widget._end_date.date() == QDate(2024, 1, 20)


class TestDateRangeFilterGetRange:
    """Tests for get_range method."""

    def test_get_range_all_dates_returns_none(self, qtbot: QtBot) -> None:
        """get_range returns None values when All Dates is checked."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        start, end, all_dates = widget.get_range()
        assert start is None
        assert end is None
        assert all_dates is True

    def test_get_range_returns_iso_strings(self, qtbot: QtBot) -> None:
        """get_range returns ISO format strings when dates specified."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        widget._all_dates_checkbox.setChecked(False)
        widget._start_date.setDate(QDate(2024, 3, 10))
        widget._end_date.setDate(QDate(2024, 3, 25))

        start, end, all_dates = widget.get_range()
        assert start == "2024-03-10"
        assert end == "2024-03-25"
        assert all_dates is False


class TestDateRangeFilterDisplayRange:
    """Tests for get_display_range method."""

    def test_display_range_empty_when_all_dates(self, qtbot: QtBot) -> None:
        """get_display_range returns empty string when All Dates is checked."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        assert widget.get_display_range() == ""

    def test_display_range_formatted_string(self, qtbot: QtBot) -> None:
        """get_display_range returns formatted string like 'Jan 15, 2024 - Jan 20, 2024'."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        widget._all_dates_checkbox.setChecked(False)
        widget._start_date.setDate(QDate(2024, 1, 15))
        widget._end_date.setDate(QDate(2024, 1, 20))

        display = widget.get_display_range()
        assert "Jan 15, 2024" in display
        assert "Jan 20, 2024" in display
        assert " - " in display


class TestDateRangeFilterReset:
    """Tests for reset method."""

    def test_reset_checks_all_dates(self, qtbot: QtBot) -> None:
        """reset() checks All Dates checkbox."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        # Uncheck first
        widget._all_dates_checkbox.setChecked(False)
        assert widget._all_dates is False

        widget.reset()

        assert widget._all_dates_checkbox.isChecked() is True
        assert widget._all_dates is True

    def test_reset_disables_date_pickers(self, qtbot: QtBot) -> None:
        """reset() disables date pickers."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        widget._all_dates_checkbox.setChecked(False)
        assert widget._start_date.isEnabled() is True

        widget.reset()

        assert widget._start_date.isEnabled() is False
        assert widget._end_date.isEnabled() is False

    def test_reset_emits_signal(self, qtbot: QtBot) -> None:
        """reset() emits date_range_changed signal."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        widget._all_dates_checkbox.setChecked(False)

        with qtbot.waitSignal(widget.date_range_changed, timeout=1000) as blocker:
            widget.reset()

        _, _, all_dates = blocker.args
        assert all_dates is True
