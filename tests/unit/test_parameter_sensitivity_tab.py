"""Tests for Parameter Sensitivity tab UI logic."""

import pytest
from unittest.mock import MagicMock, patch
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


def test_run_clicked_applies_first_trigger_filter(
    qtbot, mock_app_state, qapp
):
    """Verify _on_run_clicked applies first trigger filtering when enabled."""
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

        # Verify worker was created with first-trigger-filtered data
        MockWorker.assert_called_once()
        call_kwargs = MockWorker.call_args.kwargs
        passed_df = call_kwargs["baseline_df"]

        # Should have 2 rows (first trigger per ticker-date), not 5
        assert len(passed_df) == 2, f"Expected 2 first triggers, got {len(passed_df)}"
        assert set(passed_df["trigger_number"].unique()) == {1}
