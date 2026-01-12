"""Unit tests for FilterEngine."""

import pandas as pd

from src.core.filter_engine import FilterEngine
from src.core.models import FilterCriteria


class TestFilterEngineSingleFilter:
    """Tests for single filter application."""

    def test_single_filter_application(self, sample_trades: pd.DataFrame) -> None:
        """Single filter correctly filters data."""
        engine = FilterEngine()
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10)
        ]
        result = engine.apply_filters(sample_trades, filters)

        # Should include gain_pct values: 0, 5, 10 (not -5, 15)
        assert len(result) == 3
        assert result["gain_pct"].tolist() == [0.0, 5.0, 10.0]

    def test_not_between_single_filter(self, sample_trades: pd.DataFrame) -> None:
        """NOT BETWEEN filter correctly excludes range."""
        engine = FilterEngine()
        filters = [
            FilterCriteria(
                column="gain_pct", operator="not_between", min_val=0, max_val=10
            )
        ]
        result = engine.apply_filters(sample_trades, filters)

        # Should include gain_pct values: -5, 15 (not 0, 5, 10)
        assert len(result) == 2
        assert result["gain_pct"].tolist() == [-5.0, 15.0]


class TestFilterEngineMultipleFilters:
    """Tests for multiple filter application with AND logic."""

    def test_multiple_filters_and_logic(self, sample_trades: pd.DataFrame) -> None:
        """Multiple filters combine with AND logic."""
        engine = FilterEngine()
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10),
            FilterCriteria(column="gain_pct", operator="between", min_val=5, max_val=15),
        ]
        result = engine.apply_filters(sample_trades, filters)

        # Intersection: values between 5 and 10 (inclusive)
        assert len(result) == 2
        assert (result["gain_pct"] >= 5).all()
        assert (result["gain_pct"] <= 10).all()

    def test_multiple_filters_different_columns(
        self, sample_trades: pd.DataFrame
    ) -> None:
        """Multiple filters on different columns."""
        engine = FilterEngine()
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10),
            FilterCriteria(column="volume", operator="between", min_val=1000, max_val=2000),
        ]
        result = engine.apply_filters(sample_trades, filters)

        # gain_pct 0-10 AND volume 1000-2000
        # gain_pct: 0, 5, 10 (indices 1, 2, 3)
        # volume 1000-2000: 1000, 2000, 1500 (indices 0, 1, 2)
        # Intersection: indices 1, 2 (gain_pct=0, gain_pct=5)
        assert len(result) == 2


class TestFilterEngineEmptyFilters:
    """Tests for empty filter list behavior."""

    def test_empty_filter_list_returns_original(
        self, sample_trades: pd.DataFrame
    ) -> None:
        """Empty filter list returns copy of original DataFrame."""
        engine = FilterEngine()
        result = engine.apply_filters(sample_trades, [])

        assert len(result) == len(sample_trades)
        pd.testing.assert_frame_equal(result, sample_trades)


class TestFilterEngineReturnsCopy:
    """Tests that returned DataFrame is a copy, not a view."""

    def test_returns_copy_not_view(self, sample_trades: pd.DataFrame) -> None:
        """Filtered DataFrame is a copy, not a view."""
        engine = FilterEngine()
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=5)
        ]
        result = engine.apply_filters(sample_trades, filters)

        # Modify the result
        original_value = sample_trades.loc[1, "gain_pct"]  # Index 1 has gain_pct=0
        result.loc[result.index[0], "gain_pct"] = 999

        # Original should be unchanged
        assert sample_trades.loc[1, "gain_pct"] == original_value

    def test_empty_filters_returns_copy(self, sample_trades: pd.DataFrame) -> None:
        """Empty filter list also returns a copy."""
        engine = FilterEngine()
        result = engine.apply_filters(sample_trades, [])

        # Modify the result
        original_value = sample_trades.loc[0, "gain_pct"]
        result.loc[0, "gain_pct"] = 999

        # Original should be unchanged
        assert sample_trades.loc[0, "gain_pct"] == original_value


class TestFilterEngineEdgeCases:
    """Tests for edge cases."""

    def test_filter_removes_all_rows(self) -> None:
        """Filter that matches no rows returns empty DataFrame."""
        df = pd.DataFrame({"gain_pct": [1, 2, 3]})
        engine = FilterEngine()
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=10, max_val=20)
        ]
        result = engine.apply_filters(df, filters)

        assert len(result) == 0
        assert list(result.columns) == ["gain_pct"]

    def test_filter_empty_dataframe(self) -> None:
        """Filtering empty DataFrame returns empty DataFrame."""
        df = pd.DataFrame({"gain_pct": []})
        engine = FilterEngine()
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10)
        ]
        result = engine.apply_filters(df, filters)

        assert len(result) == 0

    def test_filter_preserves_all_columns(self, sample_trades: pd.DataFrame) -> None:
        """Filtering preserves all columns from original DataFrame."""
        engine = FilterEngine()
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10)
        ]
        result = engine.apply_filters(sample_trades, filters)

        assert list(result.columns) == list(sample_trades.columns)


class TestFilterEngineDateRange:
    """Tests for date range filtering."""

    def test_date_range_filter_inclusive(self) -> None:
        """Date range includes boundary dates (inclusive)."""
        dates = ["2024-01-14", "2024-01-15", "2024-01-18", "2024-01-20", "2024-01-21"]
        df = pd.DataFrame({
            "date": pd.to_datetime(dates),
            "value": [1, 2, 3, 4, 5],
        })
        engine = FilterEngine()
        result = engine.apply_date_range(
            df,
            date_col="date",
            start="2024-01-15",
            end="2024-01-20",
        )

        # Should include: 2024-01-15, 2024-01-18, 2024-01-20
        assert len(result) == 3
        dates = pd.to_datetime(result["date"])
        assert all(dates >= pd.Timestamp("2024-01-15"))
        assert all(dates <= pd.Timestamp("2024-01-20"))

    def test_date_range_all_dates_returns_full_dataframe(self) -> None:
        """all_dates=True returns unfiltered DataFrame."""
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-15", "2024-01-20", "2024-01-25"]),
            "value": [1, 2, 3],
        })
        engine = FilterEngine()
        result = engine.apply_date_range(
            df,
            date_col="date",
            start="2024-01-20",
            end="2024-01-20",
            all_dates=True,
        )

        # Should return all rows since all_dates=True
        assert len(result) == 3

    def test_date_range_no_start_unbounded_lower(self) -> None:
        """None start means no lower bound."""
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-01-05", "2024-01-10", "2024-01-15"]),
            "value": [1, 2, 3, 4],
        })
        engine = FilterEngine()
        result = engine.apply_date_range(
            df,
            date_col="date",
            start=None,
            end="2024-01-05",
        )

        # Should include all dates <= 2024-01-05
        assert len(result) == 2
        dates = pd.to_datetime(result["date"])
        assert all(dates <= pd.Timestamp("2024-01-05"))

    def test_date_range_no_end_unbounded_upper(self) -> None:
        """None end means no upper bound."""
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-01-10", "2024-01-20", "2024-01-30"]),
            "value": [1, 2, 3, 4],
        })
        engine = FilterEngine()
        result = engine.apply_date_range(
            df,
            date_col="date",
            start="2024-01-20",
            end=None,
        )

        # Should include all dates >= 2024-01-20
        assert len(result) == 2
        dates = pd.to_datetime(result["date"])
        assert all(dates >= pd.Timestamp("2024-01-20"))

    def test_date_range_with_datetime64_column(self) -> None:
        """Works correctly with datetime64 column types."""
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-15", "2024-01-20"]),
            "value": [1, 2],
        })
        assert df["date"].dtype == "datetime64[ns]"

        engine = FilterEngine()
        result = engine.apply_date_range(
            df,
            date_col="date",
            start="2024-01-15",
            end="2024-01-15",
        )

        assert len(result) == 1
        assert result.iloc[0]["value"] == 1

    def test_date_range_with_string_dates_column(self) -> None:
        """Works with date column as string (consistent ISO format)."""
        df = pd.DataFrame({
            "date": ["2024-01-15", "2024-01-20", "2024-01-25"],
            "value": [1, 2, 3],
        })
        engine = FilterEngine()
        result = engine.apply_date_range(
            df,
            date_col="date",
            start="2024-01-16",
            end="2024-01-25",
        )

        # Should include 2024-01-20 and 2024-01-25
        assert len(result) == 2

    def test_date_range_returns_copy(self) -> None:
        """Filtered DataFrame is a copy, not a view."""
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-15", "2024-01-20"]),
            "value": [1, 2],
        })
        engine = FilterEngine()
        result = engine.apply_date_range(
            df,
            date_col="date",
            start="2024-01-15",
            end="2024-01-15",
        )

        # Modify the result
        original_value = df.iloc[0]["value"]
        result.iloc[0, result.columns.get_loc("value")] = 999

        # Original should be unchanged
        assert df.iloc[0]["value"] == original_value

    def test_date_range_missing_column_returns_original(self) -> None:
        """Missing date column returns original DataFrame (copy)."""
        df = pd.DataFrame({
            "other_col": [1, 2, 3],
        })
        engine = FilterEngine()
        result = engine.apply_date_range(
            df,
            date_col="date",
            start="2024-01-15",
            end="2024-01-20",
        )

        # Should return copy of original since column doesn't exist
        assert len(result) == 3

    def test_date_range_both_none_returns_original(self) -> None:
        """Both start and end as None returns original DataFrame (copy)."""
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-15", "2024-01-20"]),
            "value": [1, 2],
        })
        engine = FilterEngine()
        result = engine.apply_date_range(
            df,
            date_col="date",
            start=None,
            end=None,
        )

        assert len(result) == 2


class TestApplyTimeRange:
    """Tests for apply_time_range method."""

    def test_returns_original_if_no_bounds(self, sample_trades: pd.DataFrame) -> None:
        """Should return original df if no start or end time."""
        result = FilterEngine.apply_time_range(sample_trades, "time", None, None)
        assert len(result) == len(sample_trades)

    def test_filters_by_start_time(self, sample_trades: pd.DataFrame) -> None:
        """Should filter rows with time >= start_time."""
        result = FilterEngine.apply_time_range(sample_trades, "time", "10:00:00", None)
        # sample_trades has times: 09:30:00, 10:00:00, 09:35:00, 11:00:00, 14:30:00
        # Times >= 10:00:00: 10:00:00, 11:00:00, 14:30:00
        assert len(result) == 3
        # Verify all times are >= 10:00:00
        for t in result["time"]:
            assert t >= "10:00:00"

    def test_filters_by_end_time(self, sample_trades: pd.DataFrame) -> None:
        """Should filter rows with time <= end_time."""
        result = FilterEngine.apply_time_range(sample_trades, "time", None, "10:00:00")
        # sample_trades has times: 09:30:00, 10:00:00, 09:35:00, 11:00:00, 14:30:00
        # Times <= 10:00:00: 09:30:00, 10:00:00, 09:35:00
        assert len(result) == 3
        # Verify all times are <= 10:00:00
        for t in result["time"]:
            assert t <= "10:00:00"

    def test_filters_by_range(self, sample_trades: pd.DataFrame) -> None:
        """Should filter rows within time range."""
        result = FilterEngine.apply_time_range(sample_trades, "time", "09:30:00", "10:00:00")
        # sample_trades has times: 09:30:00, 10:00:00, 09:35:00, 11:00:00, 14:30:00
        # Times in [09:30:00, 10:00:00]: 09:30:00, 10:00:00, 09:35:00
        assert len(result) == 3
        # Verify all times are within range
        for t in result["time"]:
            assert t >= "09:30:00"
            assert t <= "10:00:00"

    def test_returns_original_if_column_missing(self, sample_trades: pd.DataFrame) -> None:
        """Should return original df if time column doesn't exist."""
        result = FilterEngine.apply_time_range(sample_trades, "nonexistent", "09:30:00", "10:00:00")
        assert len(result) == len(sample_trades)
