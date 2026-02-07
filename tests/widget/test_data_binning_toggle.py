"""Tests for Data Binning baseline/filtered toggle."""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication

from src.tabs.data_binning import BinChartPanel


@pytest.fixture
def app_state():
    """Create mock app state with baseline and filtered data."""
    state = MagicMock()
    state.baseline_df = pd.DataFrame({
        "ticker": ["AAPL", "GOOG", "MSFT", "TSLA"],
        "gain_pct": [0.05, -0.02, 0.03, 0.01],
        "adjusted_gain_pct": [0.04, -0.025, 0.025, 0.008],
        "trigger_number": [1, 1, 1, 1],
    })
    state.filtered_df = pd.DataFrame({
        "ticker": ["AAPL", "MSFT"],
        "gain_pct": [0.05, 0.03],
        "adjusted_gain_pct": [0.04, 0.025],
        "trigger_number": [1, 1],
    })
    state.filtered_data_updated = MagicMock()
    state.first_trigger_toggled = MagicMock()
    return state


@pytest.fixture
def chart_panel(qtbot, app_state):
    """Create BinChartPanel instance."""
    panel = BinChartPanel(app_state)
    qtbot.addWidget(panel)
    return panel


def test_data_source_toggle_exists(chart_panel):
    """Toggle buttons for Baseline/Filtered should exist."""
    assert hasattr(chart_panel, "_baseline_btn")
    assert hasattr(chart_panel, "_filtered_btn")


def test_baseline_selected_by_default(chart_panel):
    """Baseline should be selected by default."""
    assert chart_panel._use_filtered is False
    assert chart_panel._baseline_btn.isChecked() is True
    assert chart_panel._filtered_btn.isChecked() is False


def test_toggle_to_filtered(chart_panel, qtbot):
    """Clicking Filtered button should switch data source."""
    chart_panel._filtered_btn.click()
    assert chart_panel._use_filtered is True
    assert chart_panel._baseline_btn.isChecked() is False
    assert chart_panel._filtered_btn.isChecked() is True


def test_toggle_back_to_baseline(chart_panel, qtbot):
    """Clicking Baseline button should switch back."""
    chart_panel._filtered_btn.click()
    chart_panel._baseline_btn.click()
    assert chart_panel._use_filtered is False


def test_get_binning_df_returns_baseline_when_baseline_selected(chart_panel, app_state):
    """_get_binning_df should return baseline_df when baseline is selected."""
    chart_panel._use_filtered = False
    df = chart_panel._get_binning_df()
    assert len(df) == 4  # All rows from baseline


def test_get_binning_df_returns_filtered_when_filtered_selected(chart_panel, app_state):
    """_get_binning_df should return filtered_df when filtered is selected."""
    chart_panel._use_filtered = True
    df = chart_panel._get_binning_df()
    assert len(df) == 2  # Only filtered rows


def test_get_binning_df_falls_back_to_baseline_when_filtered_empty(chart_panel, app_state):
    """Should fall back to baseline when filtered_df is empty."""
    app_state.filtered_df = pd.DataFrame()
    chart_panel._use_filtered = True
    df = chart_panel._get_binning_df()
    assert len(df) == 4  # Falls back to baseline


def test_get_binning_df_falls_back_to_baseline_when_filtered_none(chart_panel, app_state):
    """Should fall back to baseline when filtered_df is None."""
    app_state.filtered_df = None
    chart_panel._use_filtered = True
    df = chart_panel._get_binning_df()
    assert len(df) == 4  # Falls back to baseline


def test_recalculate_uses_filtered_when_selected(chart_panel, app_state):
    """_recalculate_charts should use filtered data when toggle is set."""
    from src.core.models import BinDefinition

    chart_panel._selected_column = "gain_pct"
    chart_panel._bin_definitions = [
        BinDefinition(operator=">", value1=0, value2=None, label="Positive"),
        BinDefinition(operator="<", value1=0, value2=None, label="Negative"),
    ]

    # Switch to filtered
    chart_panel._use_filtered = True

    # Mock _get_binning_df to verify it's called
    with patch.object(chart_panel, '_get_binning_df', return_value=app_state.filtered_df) as mock:
        chart_panel._recalculate_charts()
        mock.assert_called_once()