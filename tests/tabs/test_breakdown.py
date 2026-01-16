"""Tests for BreakdownTab."""

import pandas as pd
import pytest
from PyQt6.QtWidgets import QApplication

from src.core.app_state import AppState
from src.core.models import ColumnMapping
from src.tabs.breakdown import BreakdownTab


@pytest.fixture(scope="module")
def app():
    """Create QApplication for tests."""
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def app_state():
    """Create AppState with sample data."""
    state = AppState()
    state.filtered_df = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                [
                    "2023-01-15",
                    "2023-06-20",
                    "2024-02-10",
                    "2024-08-15",
                ]
            ),
            "Time": ["09:30", "10:00", "09:45", "14:30"],
            "Ticker": ["AAPL", "MSFT", "GOOGL", "AMZN"],
            "Gain%": [5.0, -2.0, 3.5, 1.0],
            "MAE%": [1.0, 3.0, 0.5, 0.8],
            "WinLoss": ["W", "L", "W", "W"],
        }
    )
    state.column_mapping = ColumnMapping(
        ticker="Ticker",
        date="Date",
        time="Time",
        gain_pct="Gain%",
        mae_pct="MAE%",
        win_loss="WinLoss",
    )
    return state


def test_breakdown_tab_init(app, app_state):
    """Test BreakdownTab initializes."""
    tab = BreakdownTab(app_state)
    assert tab._app_state is app_state


def test_breakdown_tab_updates_on_filtered_data(app, app_state):
    """Test charts update when filtered data changes."""
    tab = BreakdownTab(app_state)

    # Verify year selector has years
    assert tab._year_selector._years == [2023, 2024]

    # Verify yearly charts have data
    assert len(tab._yearly_charts["total_gain_pct"]._data) == 2  # 2 years


def test_breakdown_tab_year_selector_updates_monthly(app, app_state):
    """Test monthly charts update when year is selected."""
    tab = BreakdownTab(app_state)

    # Initially shows most recent year (2024)
    assert tab._year_selector.selected_year() == 2024

    # Monthly charts should have data for 2024
    monthly_data = tab._monthly_charts["total_gain_pct"]._data
    assert len(monthly_data) == 2  # Feb and Aug in 2024


def test_breakdown_tab_empty_state(app):
    """Test BreakdownTab shows empty state when no data."""
    state = AppState()
    tab = BreakdownTab(state)

    # Should not crash, charts should be empty
    assert tab._year_selector._years == []
    assert tab._yearly_charts["total_gain_pct"]._data == []
