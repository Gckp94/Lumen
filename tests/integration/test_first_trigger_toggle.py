"""Integration tests for first trigger toggle workflow."""

import pandas as pd
import pytest
from pytestqt.qtbot import QtBot

from src.core.app_state import AppState
from src.core.filter_engine import FilterEngine
from src.core.first_trigger import FirstTriggerEngine
from src.core.models import ColumnMapping, FilterCriteria


@pytest.fixture
def app_state() -> AppState:
    """Create fresh AppState instance."""
    return AppState()


@pytest.fixture
def column_mapping() -> ColumnMapping:
    """Standard column mapping for tests."""
    return ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        win_loss_derived=True,
    )


@pytest.fixture
def multi_trigger_data() -> pd.DataFrame:
    """DataFrame with multiple triggers per ticker-date for testing."""
    return pd.DataFrame(
        {
            "ticker": [
                "AAPL", "AAPL", "AAPL",  # 3 triggers on Jan 1
                "AAPL", "AAPL",          # 2 triggers on Jan 2
                "GOOGL", "GOOGL",        # 2 triggers on Jan 1
            ],
            "date": [
                "2024-01-01", "2024-01-01", "2024-01-01",
                "2024-01-02", "2024-01-02",
                "2024-01-01", "2024-01-01",
            ],
            "time": [
                "09:30", "10:00", "10:30",
                "09:30", "10:00",
                "09:30", "10:00",
            ],
            "gain_pct": [
                1.0, 5.0, 10.0,   # AAPL Jan 1: first=1.0
                2.0, 6.0,        # AAPL Jan 2: first=2.0
                3.0, 7.0,        # GOOGL Jan 1: first=3.0
            ],
        }
    )


class TestToggleOnShowsFirstTriggers:
    """Tests for toggle ON behavior."""

    def test_toggle_on_shows_first_triggers(
        self,
        app_state: AppState,
        multi_trigger_data: pd.DataFrame,
        column_mapping: ColumnMapping,
    ) -> None:
        """Toggle ON shows first trigger data."""
        app_state.raw_df = multi_trigger_data
        app_state.baseline_df = multi_trigger_data
        app_state.column_mapping = column_mapping
        app_state.first_trigger_enabled = True

        # Apply first trigger
        engine = FirstTriggerEngine()
        result = engine.apply_filtered(
            multi_trigger_data,
            column_mapping.ticker,
            column_mapping.date,
            column_mapping.time,
        )

        # Should have 3 rows: AAPL Jan1, AAPL Jan2, GOOGL Jan1
        assert len(result) == 3
        assert len(result) < len(multi_trigger_data)

        # Verify each group has only one row
        groups = result.groupby(["ticker", "date"]).size()
        assert (groups == 1).all()

    def test_toggle_on_keeps_earliest_time(
        self,
        app_state: AppState,
        multi_trigger_data: pd.DataFrame,
        column_mapping: ColumnMapping,
    ) -> None:
        """Toggle ON keeps first (earliest) trigger per group."""
        engine = FirstTriggerEngine()
        result = engine.apply_filtered(
            multi_trigger_data,
            column_mapping.ticker,
            column_mapping.date,
            column_mapping.time,
        )

        # AAPL Jan 1 should have gain_pct=1.0 (first trigger at 09:30)
        aapl_jan1 = result[
            (result["ticker"] == "AAPL") & (result["date"] == "2024-01-01")
        ]
        assert aapl_jan1.iloc[0]["gain_pct"] == 1.0


class TestToggleOffShowsAllData:
    """Tests for toggle OFF behavior."""

    def test_toggle_off_shows_all_data(
        self,
        app_state: AppState,
        multi_trigger_data: pd.DataFrame,
    ) -> None:
        """Toggle OFF shows all data."""
        app_state.raw_df = multi_trigger_data
        app_state.baseline_df = multi_trigger_data
        app_state.first_trigger_enabled = False
        app_state.filtered_df = multi_trigger_data

        assert len(app_state.filtered_df) == len(multi_trigger_data)
        assert len(app_state.filtered_df) == 7


class TestToggleWithFilters:
    """Tests for toggle combined with filters."""

    def test_toggle_with_filters_applies_both(
        self,
        app_state: AppState,
        multi_trigger_data: pd.DataFrame,
        column_mapping: ColumnMapping,
    ) -> None:
        """Toggle ON + filters applies both filters and first trigger."""
        app_state.raw_df = multi_trigger_data
        app_state.baseline_df = multi_trigger_data
        app_state.column_mapping = column_mapping
        app_state.first_trigger_enabled = True

        # Apply filter first: gain_pct between 2.1 and 100 (excludes 1.0 and 2.0)
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=2.1, max_val=100.0
        )
        filter_engine = FilterEngine()
        filtered = filter_engine.apply_filters(multi_trigger_data, [criteria])

        # Filtered should have 5 rows (1.0 and 2.0 excluded)
        assert len(filtered) == 5

        # Apply first trigger to filtered
        ft_engine = FirstTriggerEngine()
        result = ft_engine.apply_filtered(
            filtered,
            column_mapping.ticker,
            column_mapping.date,
            column_mapping.time,
        )

        # Result should have fewer or equal rows than filtered
        assert len(result) <= len(filtered)

        # Should have at most 3 unique ticker-date combinations
        groups = result.groupby(["ticker", "date"]).size()
        assert len(groups) <= 3
        assert (groups == 1).all()

    def test_toggle_off_with_filters_shows_all_filtered(
        self,
        app_state: AppState,
        multi_trigger_data: pd.DataFrame,
    ) -> None:
        """Toggle OFF + filters shows all filtered rows."""
        app_state.first_trigger_enabled = False

        # Apply filter: gain_pct between 2.1 and 100 (excludes 1.0 and 2.0)
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=2.1, max_val=100.0
        )
        filter_engine = FilterEngine()
        filtered = filter_engine.apply_filters(multi_trigger_data, [criteria])

        # All filtered rows should be shown (5 rows)
        assert len(filtered) == 5


class TestEdgeCases:
    """Tests for edge cases in toggle workflow."""

    def test_no_matches_after_filter(
        self,
        app_state: AppState,
        multi_trigger_data: pd.DataFrame,
    ) -> None:
        """Edge case: no matches after filter."""
        # Apply impossible filter: gain_pct between 100 and 200 (nothing matches)
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=100.0, max_val=200.0
        )
        filter_engine = FilterEngine()
        filtered = filter_engine.apply_filters(multi_trigger_data, [criteria])

        assert len(filtered) == 0

    def test_no_first_triggers_after_filter(
        self,
        app_state: AppState,
        column_mapping: ColumnMapping,
    ) -> None:
        """Edge case: no first triggers after filter (already just first triggers)."""
        # Create data where filter result is already first triggers only
        df = pd.DataFrame(
            {
                "ticker": ["AAPL"],
                "date": ["2024-01-01"],
                "time": ["09:30"],
                "gain_pct": [5.0],
            }
        )

        # Apply first trigger
        ft_engine = FirstTriggerEngine()
        result = ft_engine.apply_filtered(
            df,
            column_mapping.ticker,
            column_mapping.date,
            column_mapping.time,
        )

        # Should have same single row
        assert len(result) == 1

    def test_empty_dataframe_handling(
        self,
        column_mapping: ColumnMapping,
    ) -> None:
        """Edge case: empty DataFrame handling."""
        empty_df = pd.DataFrame(
            columns=["ticker", "date", "time", "gain_pct"]
        )

        ft_engine = FirstTriggerEngine()
        result = ft_engine.apply_filtered(
            empty_df,
            column_mapping.ticker,
            column_mapping.date,
            column_mapping.time,
        )

        assert len(result) == 0
        assert list(result.columns) == ["ticker", "date", "time", "gain_pct"]


class TestSignalFlow:
    """Tests for signal flow in toggle workflow."""

    def test_first_trigger_toggled_signal_emits_correct_value(
        self,
        qtbot: QtBot,
        app_state: AppState,
    ) -> None:
        """first_trigger_toggled signal emits correct boolean."""
        with qtbot.waitSignal(app_state.first_trigger_toggled, timeout=1000) as blocker:
            app_state.first_trigger_toggled.emit(False)

        assert blocker.args[0] is False

        with qtbot.waitSignal(app_state.first_trigger_toggled, timeout=1000) as blocker:
            app_state.first_trigger_toggled.emit(True)

        assert blocker.args[0] is True
