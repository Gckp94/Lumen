"""Tests for DateRangeFilter and TimeRangeFilter set_range methods."""

import pytest
from pytestqt.qtbot import QtBot

from src.ui.components.date_range_filter import DateRangeFilter
from src.ui.components.time_range_filter import TimeRangeFilter


class TestDateRangeFilterSetRange:
    """Tests for DateRangeFilter.set_range method."""

    def test_set_range_with_dates(self, qtbot: QtBot):
        """Test setting a specific date range."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        widget.set_range("2024-01-15", "2024-06-30", False)

        start, end, all_dates = widget.get_range()
        assert start == "2024-01-15"
        assert end == "2024-06-30"
        assert all_dates is False

    def test_set_range_all_dates(self, qtbot: QtBot):
        """Test setting all dates mode."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        # First set specific dates
        widget.set_range("2024-01-01", "2024-12-31", False)
        # Then set all dates
        widget.set_range(None, None, True)

        start, end, all_dates = widget.get_range()
        assert all_dates is True


class TestTimeRangeFilterSetRange:
    """Tests for TimeRangeFilter.set_range method."""

    def test_set_range_with_times(self, qtbot: QtBot):
        """Test setting a specific time range."""
        widget = TimeRangeFilter()
        qtbot.addWidget(widget)

        widget.set_range("09:30:00", "10:30:00", False)

        start, end, all_times = widget.get_range()
        assert start == "09:30:00"
        assert end == "10:30:00"
        assert all_times is False

    def test_set_range_all_times(self, qtbot: QtBot):
        """Test setting all times mode."""
        widget = TimeRangeFilter()
        qtbot.addWidget(widget)

        # First set specific times
        widget.set_range("09:00:00", "16:00:00", False)
        # Then set all times
        widget.set_range(None, None, True)

        start, end, all_times = widget.get_range()
        assert all_times is True
