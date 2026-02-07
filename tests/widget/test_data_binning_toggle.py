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
