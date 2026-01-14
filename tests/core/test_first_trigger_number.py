"""Tests for trigger_number column assignment."""

import pandas as pd
import pytest

from src.core.first_trigger import FirstTriggerEngine


class TestTriggerNumberAssignment:
    """Test trigger_number column is correctly assigned."""

    def test_assign_trigger_numbers_basic(self):
        """First trigger per ticker-date gets 1, second gets 2, etc."""
        engine = FirstTriggerEngine()
        df = pd.DataFrame({
            "ticker": ["AAPL", "AAPL", "AAPL", "MSFT", "MSFT"],
            "date": ["2024-01-01", "2024-01-01", "2024-01-01", "2024-01-01", "2024-01-01"],
            "time": ["09:30", "09:45", "10:00", "09:30", "09:35"],
            "gain": [1.0, 2.0, 3.0, 4.0, 5.0],
        })

        result = engine.assign_trigger_numbers(df, "ticker", "date", "time")

        # AAPL: 09:30 -> 1, 09:45 -> 2, 10:00 -> 3
        # MSFT: 09:30 -> 1, 09:35 -> 2
        assert "trigger_number" in result.columns
        aapl_rows = result[result["ticker"] == "AAPL"].sort_values("time")
        assert list(aapl_rows["trigger_number"]) == [1, 2, 3]

        msft_rows = result[result["ticker"] == "MSFT"].sort_values("time")
        assert list(msft_rows["trigger_number"]) == [1, 2]

    def test_assign_trigger_numbers_multiple_dates(self):
        """Each date starts fresh with trigger_number=1."""
        engine = FirstTriggerEngine()
        df = pd.DataFrame({
            "ticker": ["AAPL", "AAPL", "AAPL", "AAPL"],
            "date": ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02"],
            "time": ["09:30", "09:45", "09:30", "09:45"],
            "gain": [1.0, 2.0, 3.0, 4.0],
        })

        result = engine.assign_trigger_numbers(df, "ticker", "date", "time")

        # Day 1: 09:30 -> 1, 09:45 -> 2
        # Day 2: 09:30 -> 1, 09:45 -> 2 (resets)
        day1 = result[result["date"] == "2024-01-01"].sort_values("time")
        day2 = result[result["date"] == "2024-01-02"].sort_values("time")

        assert list(day1["trigger_number"]) == [1, 2]
        assert list(day2["trigger_number"]) == [1, 2]

    def test_assign_trigger_numbers_empty_df(self):
        """Empty DataFrame returns empty with trigger_number column."""
        engine = FirstTriggerEngine()
        df = pd.DataFrame(columns=["ticker", "date", "time", "gain"])

        result = engine.assign_trigger_numbers(df, "ticker", "date", "time")

        assert "trigger_number" in result.columns
        assert len(result) == 0
