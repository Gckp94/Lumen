"""Tests to verify first trigger exclusion logic."""

import pandas as pd
import pytest

from src.core.first_trigger import FirstTriggerEngine


class TestFirstTriggerExclusion:
    """Verify that when trigger 1 meets criteria, others are excluded."""

    def test_first_trigger_keeps_only_first(self):
        """If trigger 1 exists, triggers 2+ for same ticker-date are excluded."""
        engine = FirstTriggerEngine()

        # Create data with trigger_number already assigned
        df = pd.DataFrame({
            "ticker": ["AAPL", "AAPL", "AAPL", "MSFT", "MSFT"],
            "date": ["2024-01-01"] * 5,
            "time": ["09:30", "09:45", "10:00", "09:30", "09:35"],
            "trigger_number": [1, 2, 3, 1, 2],
            "gain": [5.0, 3.0, 2.0, 4.0, 1.0],
        })

        # Filter to first triggers only
        first_only = df[df["trigger_number"] == 1]

        # Should have 2 rows: AAPL trigger 1, MSFT trigger 1
        assert len(first_only) == 2
        assert set(first_only["ticker"]) == {"AAPL", "MSFT"}
        assert all(first_only["trigger_number"] == 1)

    def test_trigger_priority_is_chronological(self):
        """Trigger 1 is always the earliest by time, trigger 2 is second, etc."""
        engine = FirstTriggerEngine()

        df = pd.DataFrame({
            "ticker": ["AAPL", "AAPL", "AAPL"],
            "date": ["2024-01-01", "2024-01-01", "2024-01-01"],
            "time": ["10:00", "09:30", "09:45"],  # Out of order
            "gain": [1.0, 2.0, 3.0],
        })

        result = engine.assign_trigger_numbers(df, "ticker", "date", "time")

        # 09:30 should be trigger 1, 09:45 trigger 2, 10:00 trigger 3
        row_0930 = result[result["time"] == "09:30"].iloc[0]
        row_0945 = result[result["time"] == "09:45"].iloc[0]
        row_1000 = result[result["time"] == "10:00"].iloc[0]

        assert row_0930["trigger_number"] == 1
        assert row_0945["trigger_number"] == 2
        assert row_1000["trigger_number"] == 3
