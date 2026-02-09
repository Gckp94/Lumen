import pytest
import pandas as pd
from src.core.date_utils import detect_date_format, DateFormat


class TestDetectDateFormat:
    def test_detects_iso_format(self):
        dates = pd.Series(["2021-02-05", "2021-03-10", "2021-12-25"])
        assert detect_date_format(dates) == DateFormat.ISO

    def test_detects_day_first_format(self):
        dates = pd.Series(["05/02/2021", "10/03/2021", "25/12/2021"])
        assert detect_date_format(dates) == DateFormat.DAY_FIRST

    def test_detects_month_first_format(self):
        dates = pd.Series(["02/05/2021", "03/10/2021", "12/25/2021"])
        assert detect_date_format(dates) == DateFormat.MONTH_FIRST

    def test_returns_day_first_for_ambiguous(self):
        # All values could be either day-first or month-first
        dates = pd.Series(["01/02/2021", "02/03/2021", "03/04/2021"])
        assert detect_date_format(dates) == DateFormat.DAY_FIRST

    def test_handles_empty_series(self):
        dates = pd.Series([], dtype=str)
        assert detect_date_format(dates) == DateFormat.UNKNOWN

    def test_handles_null_values(self):
        dates = pd.Series([None, "2021-02-05", None])
        assert detect_date_format(dates) == DateFormat.ISO
