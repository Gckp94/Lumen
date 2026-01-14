"""Tests for FilterEngine time range filtering."""

from datetime import time

import numpy as np
import pandas as pd
import pytest

from src.core.filter_engine import FilterEngine, time_to_minutes


class TestTimeRangeFilter:
    """Tests for apply_time_range method."""

    def test_time_filter_string_format(self) -> None:
        """Filter with HH:MM:SS string format times."""
        df = pd.DataFrame({
            "time": ["04:30:00", "09:30:00", "12:00:00", "16:00:00"],
            "value": [1, 2, 3, 4],
        })

        result = FilterEngine.apply_time_range(df, "time", "04:30:00", "12:00:00")

        assert len(result) == 3
        assert list(result["value"]) == [1, 2, 3]

    def test_time_filter_datetime_time_objects(self) -> None:
        """Filter should work with datetime.time objects in column."""
        df = pd.DataFrame({
            "time": [time(4, 30), time(9, 30), time(12, 0), time(16, 0)],
            "value": [1, 2, 3, 4],
        })

        result = FilterEngine.apply_time_range(df, "time", "04:30:00", "12:00:00")

        assert len(result) == 3
        assert list(result["value"]) == [1, 2, 3]

    def test_time_filter_no_bounds(self) -> None:
        """No filter when both bounds are None."""
        df = pd.DataFrame({
            "time": ["04:30:00", "09:30:00", "12:00:00"],
            "value": [1, 2, 3],
        })

        result = FilterEngine.apply_time_range(df, "time", None, None)

        assert len(result) == 3

    def test_time_filter_start_only(self) -> None:
        """Filter with start time only."""
        df = pd.DataFrame({
            "time": ["04:30:00", "09:30:00", "12:00:00", "16:00:00"],
            "value": [1, 2, 3, 4],
        })

        result = FilterEngine.apply_time_range(df, "time", "10:00:00", None)

        assert len(result) == 2  # 12:00 and 16:00
        assert list(result["value"]) == [3, 4]

    def test_time_filter_end_only(self) -> None:
        """Filter with end time only."""
        df = pd.DataFrame({
            "time": ["04:30:00", "09:30:00", "12:00:00", "16:00:00"],
            "value": [1, 2, 3, 4],
        })

        result = FilterEngine.apply_time_range(df, "time", None, "10:00:00")

        assert len(result) == 2  # 04:30 and 09:30
        assert list(result["value"]) == [1, 2]

    def test_time_filter_missing_column(self) -> None:
        """Returns original DataFrame when time column doesn't exist."""
        df = pd.DataFrame({
            "other": ["04:30:00", "09:30:00"],
            "value": [1, 2],
        })

        result = FilterEngine.apply_time_range(df, "time", "04:30:00", "12:00:00")

        assert len(result) == 2  # No filtering applied

    def test_time_filter_empty_result(self) -> None:
        """Filter can return empty DataFrame."""
        df = pd.DataFrame({
            "time": ["04:30:00", "09:30:00"],
            "value": [1, 2],
        })

        result = FilterEngine.apply_time_range(df, "time", "20:00:00", "23:00:00")

        assert len(result) == 0

    def test_time_filter_boundary_inclusive(self) -> None:
        """Boundary times are inclusive."""
        df = pd.DataFrame({
            "time": ["09:30:00", "10:00:00", "10:30:00"],
            "value": [1, 2, 3],
        })

        result = FilterEngine.apply_time_range(df, "time", "09:30:00", "10:30:00")

        assert len(result) == 3  # All included (boundaries inclusive)

    def test_time_filter_excel_serial_format(self) -> None:
        """Filter should work with Excel serial time (float 0-1)."""
        # Excel serial time: fraction of 24 hours
        # 0.395833 ≈ 09:30:00, 0.5 = 12:00:00, 0.666667 ≈ 16:00:00
        df = pd.DataFrame({
            "time": [0.1875, 0.395833, 0.5, 0.666667],  # 04:30, 09:30, 12:00, 16:00
            "value": [1, 2, 3, 4],
        })

        result = FilterEngine.apply_time_range(df, "time", "04:30:00", "12:00:00")

        assert len(result) == 3
        assert list(result["value"]) == [1, 2, 3]

    def test_time_filter_excel_serial_afternoon(self) -> None:
        """Filter Excel serial time for afternoon range."""
        df = pd.DataFrame({
            "time": [0.395833, 0.5, 0.583333, 0.666667],  # 09:30, 12:00, 14:00, 16:00
            "value": [1, 2, 3, 4],
        })

        result = FilterEngine.apply_time_range(df, "time", "12:00:00", "16:00:00")

        assert len(result) == 3  # 12:00, 14:00, 16:00
        assert list(result["value"]) == [2, 3, 4]

    def test_time_filter_excel_serial_with_nan(self) -> None:
        """Filter Excel serial time with NaN values."""
        import numpy as np

        df = pd.DataFrame({
            "time": [0.1875, np.nan, 0.5, 0.666667],  # 04:30, NaN, 12:00, 16:00
            "value": [1, 2, 3, 4],
        })

        result = FilterEngine.apply_time_range(df, "time", "04:30:00", "12:00:00")

        assert len(result) == 2  # 04:30 and 12:00 (NaN excluded)
        assert list(result["value"]) == [1, 3]


class TestTimeToMinutes:
    """Tests for time_to_minutes utility function."""

    def test_time_string_hms_format(self):
        """Test parsing HH:MM:SS string format."""
        series = pd.Series(["09:30:00", "14:45:30", "00:00:00"])
        result = time_to_minutes(series)
        expected = pd.Series([570.0, 885.5, 0.0])
        pd.testing.assert_series_equal(result, expected)

    def test_time_string_hm_format(self):
        """Test parsing HH:MM string format (no seconds)."""
        series = pd.Series(["09:30", "14:45", "00:00"])
        result = time_to_minutes(series)
        expected = pd.Series([570.0, 885.0, 0.0])
        pd.testing.assert_series_equal(result, expected)

    def test_integer_hhmmss_format(self):
        """Test parsing integer HHMMSS format (e.g., 93000 for 09:30:00)."""
        series = pd.Series([93000, 144530, 0])
        result = time_to_minutes(series)
        expected = pd.Series([570.0, 885.5, 0.0])
        pd.testing.assert_series_equal(result, expected)

    def test_excel_serial_time(self):
        """Test parsing Excel serial time (0-1 fraction of day)."""
        series = pd.Series([0.5, 0.25, 0.0])
        result = time_to_minutes(series)
        expected = pd.Series([720.0, 360.0, 0.0])
        pd.testing.assert_series_equal(result, expected)

    def test_handles_nan_values(self):
        """Test that NaN values are preserved."""
        series = pd.Series(["09:30:00", None, "14:45:00"])
        result = time_to_minutes(series)
        assert result.iloc[0] == 570.0
        assert pd.isna(result.iloc[1])
        assert result.iloc[2] == 885.0

    def test_datetime_time_objects(self):
        """Test parsing datetime.time objects."""
        from datetime import time
        series = pd.Series([time(9, 30, 0), time(14, 45, 30), time(0, 0, 0)])
        result = time_to_minutes(series)
        expected = pd.Series([570.0, 885.5, 0.0])
        pd.testing.assert_series_equal(result, expected)

    def test_empty_series_returns_empty(self):
        """Test that empty series returns empty series."""
        series = pd.Series([], dtype=object)
        result = time_to_minutes(series)
        assert len(result) == 0

    def test_all_nan_series(self):
        """Test that all-NaN series returns all-NaN result."""
        series = pd.Series([None, np.nan, None])
        result = time_to_minutes(series)
        assert result.isna().all()
        assert len(result) == 3  # Verify length preserved
