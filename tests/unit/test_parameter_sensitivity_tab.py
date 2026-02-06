"""Tests for Parameter Sensitivity tab UI logic."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import pandas as pd

from src.core.parameter_sensitivity import ParameterSensitivityConfig


class TestSweepConfigConstruction:
    """Test sweep config construction from UI values."""

    def test_sweep_config_with_filter_1_only(self):
        """Sweep config should accept filter_1 without filter_2."""
        config = ParameterSensitivityConfig(
            mode="sweep",
            primary_metric="expected_value",
            grid_resolution=10,
            sweep_filter_1="gap_percent",
            sweep_range_1=(0.5, 2.0),
        )

        assert config.sweep_filter_1 == "gap_percent"
        assert config.sweep_range_1 == (0.5, 2.0)
        assert config.sweep_filter_2 is None
        assert config.sweep_range_2 is None

    def test_sweep_config_with_2d_filters(self):
        """Sweep config should accept both filter_1 and filter_2."""
        config = ParameterSensitivityConfig(
            mode="sweep",
            primary_metric="win_rate",
            grid_resolution=15,
            sweep_filter_1="gap_percent",
            sweep_range_1=(0.5, 2.0),
            sweep_filter_2="volume",
            sweep_range_2=(1000, 5000),
        )

        assert config.sweep_filter_1 == "gap_percent"
        assert config.sweep_range_1 == (0.5, 2.0)
        assert config.sweep_filter_2 == "volume"
        assert config.sweep_range_2 == (1000, 5000)

    def test_neighborhood_config_ignores_sweep_params(self):
        """Neighborhood mode should work without sweep parameters."""
        config = ParameterSensitivityConfig(
            mode="neighborhood",
            primary_metric="profit_factor",
        )

        assert config.mode == "neighborhood"
        assert config.sweep_filter_1 is None


# Fixtures for tab-level tests
from PyQt6.QtWidgets import QApplication
from src.core.app_state import AppState


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for widget tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_app_state():
    """Create mock AppState for testing."""
    state = MagicMock(spec=AppState)
    return state


def test_run_clicked_uses_baseline_df_with_date_time_filters(
    qtbot, mock_app_state, qapp
):
    """Verify _on_run_clicked uses baseline_df + date/time filters for bidirectional analysis."""
    from unittest.mock import patch, MagicMock
    from src.tabs.parameter_sensitivity import ParameterSensitivityTab
    from src.core.models import ColumnMapping, FilterCriteria

    # Create sample data with multiple triggers per ticker-date
    df = pd.DataFrame({
        "ticker": ["AAPL", "AAPL", "AAPL", "GOOG", "GOOG"],
        "date": ["2024-01-01", "2024-01-01", "2024-01-01", "2024-01-01", "2024-01-01"],
        "time": ["09:30", "09:35", "09:40", "09:30", "09:35"],
        "trigger_number": [1, 2, 3, 1, 2],
        "gain_pct": [0.05, 0.03, 0.02, 0.04, 0.01],
        "gap_pct": [3.0, 3.0, 3.0, 4.0, 4.0],
    })
    
    mock_app_state.baseline_df = df
    mock_app_state.filtered_df = df[df["trigger_number"] == 1].copy()
    mock_app_state.first_trigger_enabled = True
    mock_app_state.column_mapping = ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
    )
    mock_app_state.filters = [
        FilterCriteria(column="gap_pct", operator="between", min_val=2.0, max_val=5.0)
    ]
    mock_app_state.adjustment_params = None  # Uses default AdjustmentParams
    # Date/time range fields - all_dates=True means no date/time filtering
    mock_app_state.all_dates = True
    mock_app_state.all_times = True
    mock_app_state.date_start = None
    mock_app_state.date_end = None
    mock_app_state.time_start = None
    mock_app_state.time_end = None

    tab = ParameterSensitivityTab(mock_app_state)
    qtbot.addWidget(tab)
    tab._current_filter_index = 0

    # Mock the worker to capture what data it receives
    with patch(
        "src.tabs.parameter_sensitivity.ThresholdAnalysisWorker"
    ) as MockWorker:
        mock_worker = MagicMock()
        mock_worker.isRunning.return_value = False
        MockWorker.return_value = mock_worker

        tab._on_run_clicked()

        # Verify worker is called with baseline_df (all 5 rows before feature filters)
        MockWorker.assert_called_once()
        call_kwargs = MockWorker.call_args.kwargs
        
        # Should use baseline_df (5 rows) - worker applies feature filters with varied thresholds
        passed_df = call_kwargs["baseline_df"]
        assert len(passed_df) == 5, f"Expected baseline_df with 5 rows, got {len(passed_df)}"
        
        # first_trigger_enabled should be True (worker applies it after feature filters)
        assert call_kwargs["first_trigger_enabled"] is True


def test_run_clicked_applies_date_time_filters(
    qtbot, mock_app_state, qapp
):
    """Verify _on_run_clicked applies date/time filters from AppState."""
    from unittest.mock import patch, MagicMock
    from src.tabs.parameter_sensitivity import ParameterSensitivityTab
    from src.core.models import ColumnMapping, FilterCriteria

    # Create sample data with multiple dates
    df = pd.DataFrame({
        "ticker": ["AAPL", "AAPL", "GOOG", "GOOG", "MSFT"],
        "date": ["2024-01-01", "2024-01-02", "2024-01-01", "2024-01-02", "2024-01-03"],
        "time": ["09:30", "09:35", "09:40", "09:30", "09:35"],
        "trigger_number": [1, 1, 1, 1, 1],
        "gain_pct": [0.05, 0.03, 0.02, 0.04, 0.01],
        "gap_pct": [3.0, 3.0, 4.0, 4.0, 2.5],
    })

    mock_app_state.baseline_df = df
    mock_app_state.filtered_df = df.copy()
    mock_app_state.first_trigger_enabled = False  # Disabled
    mock_app_state.column_mapping = ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
    )
    mock_app_state.filters = [
        FilterCriteria(column="gap_pct", operator="between", min_val=2.0, max_val=5.0)
    ]
    mock_app_state.adjustment_params = None  # Uses default AdjustmentParams
    # Set date range filter - should filter to 2024-01-01 and 2024-01-02 only
    mock_app_state.all_dates = False
    mock_app_state.date_start = "2024-01-01"
    mock_app_state.date_end = "2024-01-02"
    mock_app_state.all_times = True
    mock_app_state.time_start = None
    mock_app_state.time_end = None

    tab = ParameterSensitivityTab(mock_app_state)
    qtbot.addWidget(tab)
    tab._current_filter_index = 0

    with patch(
        "src.tabs.parameter_sensitivity.ThresholdAnalysisWorker"
    ) as MockWorker:
        mock_worker = MagicMock()
        mock_worker.isRunning.return_value = False
        MockWorker.return_value = mock_worker

        tab._on_run_clicked()

        MockWorker.assert_called_once()
        call_kwargs = MockWorker.call_args.kwargs
        passed_df = call_kwargs["baseline_df"]

        # Should have 4 rows (excludes 2024-01-03)
        assert len(passed_df) == 4, f"Expected 4 rows after date filter, got {len(passed_df)}"
        
        # first_trigger_enabled should be False (disabled in AppState)
        assert call_kwargs["first_trigger_enabled"] is False
