"""Unit tests for FirstTriggerEngine."""

from time import perf_counter

import numpy as np
import pandas as pd
import pytest

from src.core.first_trigger import FirstTriggerEngine


@pytest.fixture
def engine() -> FirstTriggerEngine:
    """Create FirstTriggerEngine instance."""
    return FirstTriggerEngine()


@pytest.fixture
def sample_first_trigger_data() -> pd.DataFrame:
    """Sample DataFrame for first trigger testing."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "AAPL", "AAPL", "GOOGL", "GOOGL"],
            "date": ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-01", "2024-01-01"],
            "time": ["09:30", "10:00", "09:30", "09:30", "10:00"],
            "gain_pct": [1.0, 2.0, 3.0, 4.0, 5.0],
        }
    )


class TestFirstTriggerBasic:
    """Basic functionality tests for FirstTriggerEngine."""

    def test_apply_returns_one_row_per_ticker_date(
        self, engine: FirstTriggerEngine, sample_first_trigger_data: pd.DataFrame
    ) -> None:
        """First trigger returns one row per ticker-date combination."""
        result = engine.apply(sample_first_trigger_data, "ticker", "date", "time")

        # Should have 3 rows: AAPL 01-01, AAPL 01-02, GOOGL 01-01
        assert len(result) == 3

        # Verify uniqueness
        groups = result.groupby(["ticker", "date"]).size()
        assert (groups == 1).all()

    def test_apply_keeps_earliest_time(
        self, engine: FirstTriggerEngine, sample_first_trigger_data: pd.DataFrame
    ) -> None:
        """First trigger keeps row with earliest time per group."""
        result = engine.apply(sample_first_trigger_data, "ticker", "date", "time")

        # AAPL 2024-01-01 should have 09:30 (first), gain_pct=1.0
        aapl_jan01 = result[(result["ticker"] == "AAPL") & (result["date"] == "2024-01-01")]
        assert len(aapl_jan01) == 1
        assert aapl_jan01.iloc[0]["gain_pct"] == 1.0

        # GOOGL 2024-01-01 should have 09:30 (first), gain_pct=4.0
        googl_jan01 = result[(result["ticker"] == "GOOGL") & (result["date"] == "2024-01-01")]
        assert len(googl_jan01) == 1
        assert googl_jan01.iloc[0]["gain_pct"] == 4.0


class TestFirstTriggerEdgeCases:
    """Edge case tests for FirstTriggerEngine."""

    def test_apply_empty_dataframe(self, engine: FirstTriggerEngine) -> None:
        """Empty DataFrame returns empty DataFrame with same columns."""
        empty = pd.DataFrame(columns=["ticker", "date", "time", "gain_pct"])
        result = engine.apply(empty, "ticker", "date", "time")

        assert len(result) == 0
        assert list(result.columns) == ["ticker", "date", "time", "gain_pct"]

    def test_apply_single_row(self, engine: FirstTriggerEngine) -> None:
        """Single row DataFrame returns that row."""
        df = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "date": ["2024-01-01"],
                "time": ["09:30"],
                "gain_pct": [1.0],
            }
        )
        result = engine.apply(df, "ticker", "date", "time")

        assert len(result) == 1
        assert result.iloc[0]["ticker"] == "AAPL"
        assert result.iloc[0]["gain_pct"] == 1.0

    def test_apply_null_times_sorted_first(self, engine: FirstTriggerEngine) -> None:
        """Null times are sorted first within groups."""
        df = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL"],
                "date": ["2024-01-01", "2024-01-01"],
                "time": ["09:30", None],
                "gain_pct": [1.0, 2.0],
            }
        )
        result = engine.apply(df, "ticker", "date", "time")

        assert len(result) == 1
        # Null time should be selected as first (na_position="first")
        assert result.iloc[0]["gain_pct"] == 2.0

    def test_apply_duplicate_times_keeps_first_occurrence(self, engine: FirstTriggerEngine) -> None:
        """Duplicate times keeps first occurrence in original order."""
        df = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL"],
                "date": ["2024-01-01", "2024-01-01"],
                "time": ["09:30", "09:30"],
                "gain_pct": [1.0, 2.0],
            }
        )
        result = engine.apply(df, "ticker", "date", "time")

        assert len(result) == 1
        # First occurrence (gain_pct=1.0) should be kept
        assert result.iloc[0]["gain_pct"] == 1.0

    def test_apply_all_same_ticker_date(self, engine: FirstTriggerEngine) -> None:
        """All rows with same ticker-date returns only first row."""
        df = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL", "AAPL"],
                "date": ["2024-01-01", "2024-01-01", "2024-01-01"],
                "time": ["09:30", "09:35", "09:40"],
                "gain_pct": [1.0, 2.0, 3.0],
            }
        )
        result = engine.apply(df, "ticker", "date", "time")

        assert len(result) == 1
        assert result.iloc[0]["time"] == "09:30"
        assert result.iloc[0]["gain_pct"] == 1.0


class TestFirstTriggerApplyFiltered:
    """Tests for apply_filtered method."""

    def test_apply_filtered_returns_one_per_ticker_date(
        self, engine: FirstTriggerEngine, sample_first_trigger_data: pd.DataFrame
    ) -> None:
        """apply_filtered returns one row per ticker-date."""
        result = engine.apply_filtered(sample_first_trigger_data, "ticker", "date", "time")

        # Verify uniqueness
        groups = result.groupby(["ticker", "date"]).size()
        assert (groups == 1).all()

    def test_apply_filtered_on_already_filtered_data(
        self, engine: FirstTriggerEngine
    ) -> None:
        """apply_filtered works on pre-filtered data."""
        # Simulate filtered data (subset of original)
        filtered_df = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL", "GOOGL"],
                "date": ["2024-01-01", "2024-01-01", "2024-01-01"],
                "time": ["10:00", "11:00", "09:30"],
                "gain_pct": [5.0, 6.0, 7.0],  # Assume filtered by gain > 4
            }
        )
        result = engine.apply_filtered(filtered_df, "ticker", "date", "time")

        # Should have 2 rows: AAPL 01-01, GOOGL 01-01
        assert len(result) == 2

        # AAPL should keep 10:00 (earliest in filtered set)
        aapl = result[result["ticker"] == "AAPL"]
        assert aapl.iloc[0]["time"] == "10:00"
        assert aapl.iloc[0]["gain_pct"] == 5.0

    def test_apply_filtered_empty_input(self, engine: FirstTriggerEngine) -> None:
        """Empty DataFrame returns empty DataFrame."""
        empty = pd.DataFrame(columns=["ticker", "date", "time", "gain_pct"])
        result = engine.apply_filtered(empty, "ticker", "date", "time")

        assert len(result) == 0
        assert list(result.columns) == ["ticker", "date", "time", "gain_pct"]

    def test_apply_filtered_returns_copy(
        self, engine: FirstTriggerEngine, sample_first_trigger_data: pd.DataFrame
    ) -> None:
        """apply_filtered returns DataFrame copy, not view."""
        result = engine.apply_filtered(sample_first_trigger_data, "ticker", "date", "time")

        # Modify result
        result["gain_pct"] = 999

        # Original should be unchanged
        assert (sample_first_trigger_data["gain_pct"] != 999).any()

    def test_apply_filtered_preserves_all_columns(
        self, engine: FirstTriggerEngine
    ) -> None:
        """apply_filtered preserves all columns from input."""
        df = pd.DataFrame(
            {
                "ticker": ["AAPL", "AAPL"],
                "date": ["2024-01-01", "2024-01-01"],
                "time": ["09:30", "10:00"],
                "gain_pct": [1.0, 2.0],
                "volume": [1000, 2000],
                "custom_col": ["a", "b"],
            }
        )
        result = engine.apply_filtered(df, "ticker", "date", "time")

        assert list(result.columns) == list(df.columns)
        assert "volume" in result.columns
        assert "custom_col" in result.columns


class TestFirstTriggerPerformance:
    """Performance tests for FirstTriggerEngine."""

    @pytest.mark.slow
    def test_apply_performance_100k_rows(self, engine: FirstTriggerEngine) -> None:
        """Performance: < 500ms for 100k rows."""
        np.random.seed(42)
        n_rows = 100_000

        # Generate 100k rows with ~50 tickers, ~250 dates
        df = pd.DataFrame(
            {
                "ticker": np.random.choice([f"TICK{i}" for i in range(50)], n_rows),
                "date": np.random.choice(
                    pd.date_range("2024-01-01", periods=250).strftime("%Y-%m-%d"),
                    n_rows,
                ),
                "time": pd.to_datetime(np.random.randint(0, 86400, n_rows), unit="s").strftime(
                    "%H:%M:%S"
                ),
                "gain_pct": np.random.normal(0.5, 3, n_rows),
            }
        )

        start = perf_counter()
        result = engine.apply(df, "ticker", "date", "time")
        elapsed = perf_counter() - start

        assert elapsed < 0.5, f"First trigger took {elapsed:.3f}s, exceeds 500ms limit"
        assert len(result) <= n_rows
        assert len(result) > 0

        # Verify result has unique ticker-date combinations
        groups = result.groupby(["ticker", "date"]).size()
        assert (groups == 1).all()
