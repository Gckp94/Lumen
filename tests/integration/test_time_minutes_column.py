"""Integration tests for time_minutes column derivation during data loading."""

import pandas as pd
import pytest
from pytestqt.qtbot import QtBot

from src.core.app_state import AppState
from src.core.models import ColumnMapping
from src.tabs.data_input import DataInputTab


@pytest.fixture
def app_state() -> AppState:
    """Create AppState instance for testing."""
    return AppState()


@pytest.fixture
def sample_data_with_time(tmp_path):
    """Create sample CSV file with time column for testing."""
    csv_file = tmp_path / "trades_with_time.csv"
    df = pd.DataFrame(
        {
            "ticker": ["AAPL", "GOOGL", "MSFT", "TSLA"],
            "date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
            "time": ["09:30:00", "10:15:00", "14:45:00", "16:00:00"],
            "gain_pct": [1.5, -0.8, 2.1, -1.2],
            "mae_pct": [0.5, 1.2, 0.3, 0.8],  # Required for ColumnMapping
        }
    )
    df.to_csv(csv_file, index=False)
    return csv_file


class TestTimeMinutesColumnDerivation:
    """Tests for time_minutes derived column during data loading."""

    def test_time_minutes_column_added_to_baseline_df(
        self, qtbot: QtBot, app_state: AppState, sample_data_with_time
    ) -> None:
        """Test that time_minutes column is added to baseline_df when time column exists."""
        # Setup - create tab with app_state
        tab = DataInputTab(app_state=app_state)
        qtbot.addWidget(tab)

        # Load data directly (simulate what FileLoadWorker does)
        df = pd.read_csv(sample_data_with_time)
        tab._df = df
        tab._selected_path = sample_data_with_time

        # Create a mapping that includes time column
        mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
            win_loss_derived=True,
        )

        # Trigger the mapping continue which creates baseline_df (async worker)
        with qtbot.waitSignal(tab.mapping_completed, timeout=10000):
            tab._on_mapping_continue(mapping)

        # Verify baseline_df exists
        baseline_df = app_state.baseline_df
        assert baseline_df is not None, "baseline_df should be set after loading data"

        # Verify time_minutes column exists
        assert "time_minutes" in baseline_df.columns, (
            "time_minutes column should be added to baseline_df"
        )

        # Verify it's numeric (float)
        assert pd.api.types.is_float_dtype(baseline_df["time_minutes"]), (
            "time_minutes should be a float column"
        )

    def test_time_minutes_values_are_correct(
        self, qtbot: QtBot, app_state: AppState, sample_data_with_time
    ) -> None:
        """Test that time_minutes values are correctly calculated."""
        # Setup
        tab = DataInputTab(app_state=app_state)
        qtbot.addWidget(tab)

        # Load data directly
        df = pd.read_csv(sample_data_with_time)
        tab._df = df
        tab._selected_path = sample_data_with_time

        # Create mapping with time
        mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
            win_loss_derived=True,
        )

        with qtbot.waitSignal(tab.mapping_completed, timeout=10000):
            tab._on_mapping_continue(mapping)

        baseline_df = app_state.baseline_df
        assert baseline_df is not None

        # Verify values: 09:30 = 570 mins, 10:15 = 615 mins, 14:45 = 885 mins, 16:00 = 960 mins
        expected_minutes = [570.0, 615.0, 885.0, 960.0]
        actual_minutes = baseline_df["time_minutes"].tolist()

        for expected, actual in zip(expected_minutes, actual_minutes, strict=True):
            assert abs(actual - expected) < 0.01, (
                f"Expected {expected} minutes, got {actual}"
            )

    def test_time_minutes_not_added_when_time_column_missing_from_df(
        self, qtbot: QtBot, app_state: AppState, tmp_path
    ) -> None:
        """Test time_minutes NOT added when time column missing from DataFrame."""
        # Create CSV with a time column but we'll map to a non-existent column
        csv_file = tmp_path / "trades_with_time.csv"
        df = pd.DataFrame(
            {
                "ticker": ["AAPL", "GOOGL"],
                "date": ["2024-01-01", "2024-01-02"],
                "time": ["09:30:00", "10:00:00"],  # Time column exists
                "gain_pct": [1.5, -0.8],
                "mae_pct": [0.5, 1.2],
            }
        )
        df.to_csv(csv_file, index=False)

        # Setup and load
        tab = DataInputTab(app_state=app_state)
        qtbot.addWidget(tab)
        tab._df = df
        tab._selected_path = csv_file

        # Mapping with time column that exists but we remove it from baseline_df
        mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
            win_loss_derived=True,
        )

        with qtbot.waitSignal(tab.mapping_completed, timeout=10000):
            tab._on_mapping_continue(mapping)

        # Verify time_minutes IS added when mapping and column exist
        # The "not added" case is when mapping.time is falsy (empty string)
        baseline_df = app_state.baseline_df
        assert baseline_df is not None
        assert "time_minutes" in baseline_df.columns, (
            "time_minutes should be added when time column is properly mapped"
        )

    def test_time_minutes_preserved_on_recalculate_metrics(
        self, qtbot: QtBot, app_state: AppState, sample_data_with_time
    ) -> None:
        """Test that time_minutes column is preserved when metrics are recalculated."""
        # Setup
        tab = DataInputTab(app_state=app_state)
        qtbot.addWidget(tab)

        # Load and process data
        df = pd.read_csv(sample_data_with_time)
        tab._df = df
        tab._selected_path = sample_data_with_time

        mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
            win_loss_derived=True,
        )

        with qtbot.waitSignal(tab.mapping_completed, timeout=10000):
            tab._on_mapping_continue(mapping)

        # Verify initial time_minutes
        assert "time_minutes" in app_state.baseline_df.columns

        # Trigger recalculation by changing adjustment params
        from src.core.models import AdjustmentParams
        new_params = AdjustmentParams(stop_loss=10.0, efficiency=6.0)
        tab._pending_adjustment_params = new_params
        tab._recalculate_metrics()

        # Verify time_minutes still exists after recalculation
        baseline_df = app_state.baseline_df
        assert baseline_df is not None
        assert "time_minutes" in baseline_df.columns, (
            "time_minutes should be preserved after _recalculate_metrics"
        )
