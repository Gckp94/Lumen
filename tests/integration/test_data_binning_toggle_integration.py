"""Integration tests for Data Binning baseline/filtered toggle."""

import pytest
import pandas as pd
from PyQt6.QtWidgets import QApplication

from src.core.app_state import AppState
from src.tabs.data_binning import DataBinningTab


@pytest.fixture
def app_state_with_data():
    """Create real AppState with test data."""
    state = AppState()
    state.baseline_df = pd.DataFrame({
        "ticker": ["AAPL", "GOOG", "MSFT", "TSLA", "AMZN"],
        "gain_pct": [0.05, -0.02, 0.03, 0.01, -0.01],
        "adjusted_gain_pct": [0.04, -0.025, 0.025, 0.008, -0.012],
        "trigger_number": [1, 1, 1, 1, 1],
        "gap_pct": [2.5, 1.8, 3.2, 0.9, 2.1],
    })
    state.filtered_df = pd.DataFrame({
        "ticker": ["AAPL", "MSFT"],
        "gain_pct": [0.05, 0.03],
        "adjusted_gain_pct": [0.04, 0.025],
        "trigger_number": [1, 1],
        "gap_pct": [2.5, 3.2],
    })
    return state


@pytest.fixture
def data_binning_tab(qtbot, app_state_with_data):
    """Create DataBinningTab with real AppState."""
    tab = DataBinningTab(app_state_with_data)
    qtbot.addWidget(tab)
    return tab


def test_full_toggle_workflow(data_binning_tab, app_state_with_data, qtbot):
    """Test complete workflow: load data, configure bins, toggle data source."""
    tab = data_binning_tab
    chart_panel = tab._chart_panel
    
    # Trigger label update (normally happens via signal)
    chart_panel._update_toggle_labels()
    
    # Verify initial state
    assert chart_panel._use_filtered is False
    assert "5" in chart_panel._baseline_btn.text()  # 5 baseline rows
    
    # Toggle to filtered
    chart_panel._filtered_btn.click()
    assert chart_panel._use_filtered is True
    
    # Toggle back to baseline
    chart_panel._baseline_btn.click()
    assert chart_panel._use_filtered is False


def test_signal_connection_works(data_binning_tab, app_state_with_data, qtbot):
    """Test that filtered_data_updated signal updates charts."""
    tab = data_binning_tab
    chart_panel = tab._chart_panel
    
    # Switch to filtered mode
    chart_panel._use_filtered = True
    chart_panel._filtered_btn.setChecked(True)
    
    # Emit the signal with new data
    new_filtered = pd.DataFrame({
        "ticker": ["GOOG"],
        "gain_pct": [-0.02],
        "adjusted_gain_pct": [-0.025],
        "trigger_number": [1],
        "gap_pct": [1.8],
    })
    app_state_with_data.filtered_df = new_filtered
    app_state_with_data.filtered_data_updated.emit(new_filtered)
    
    # Verify label updated
    assert "1" in chart_panel._filtered_btn.text()


def test_auto_switch_via_signal(data_binning_tab, app_state_with_data, qtbot):
    """Test auto-switch when filters cleared via signal."""
    tab = data_binning_tab
    chart_panel = tab._chart_panel
    
    # Start in filtered mode
    chart_panel._use_filtered = True
    chart_panel._filtered_btn.setChecked(True)
    
    # Clear filters (emit empty DataFrame)
    app_state_with_data.filtered_df = pd.DataFrame()
    app_state_with_data.filtered_data_updated.emit(pd.DataFrame())
    
    # Should auto-switch to baseline
    assert chart_panel._use_filtered is False
    assert chart_panel._baseline_btn.isChecked() is True
