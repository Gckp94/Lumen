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
            "MFE%": [2.0, 1.0, 1.5, 1.2],
            "WinLoss": ["W", "L", "W", "W"],
        }
    )
    state.column_mapping = ColumnMapping(
        ticker="Ticker",
        date="Date",
        time="Time",
        gain_pct="Gain%",
        mae_pct="MAE%",
        mfe_pct="MFE%",
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


def test_breakdown_tab_displays_baseline_on_initial_load(qtbot):
    """Test that breakdown tab displays baseline data when no filters applied."""
    from src.core.models import TradingMetrics

    # Create sample trades DataFrame
    sample_trades = pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT", "GOOGL", "AMZN"],
            "date": pd.to_datetime(
                [
                    "2023-01-15",
                    "2023-06-20",
                    "2024-02-10",
                    "2024-08-15",
                ]
            ),
            "time": ["09:30", "10:00", "09:45", "14:30"],
            "gain_pct": [5.0, -2.0, 3.5, 1.0],
            "mae_pct": [1.0, 3.0, 0.5, 0.8],
            "mfe_pct": [6.0, 1.0, 4.0, 2.0],
        }
    )

    state = AppState()
    state.column_mapping = ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
        win_loss=None,
        win_loss_derived=True,
        breakeven_is_win=False,
    )
    state.baseline_df = sample_trades
    # filtered_df intentionally left as None

    tab = BreakdownTab(state)
    qtbot.addWidget(tab)

    # Emit baseline_calculated signal (simulates data load completion)
    metrics = TradingMetrics(
        num_trades=len(sample_trades),
        win_rate=50.0,
        avg_winner=5.0,
        avg_loser=-3.0,
        rr_ratio=1.67,
        ev=1.0,
        kelly=5.0,
    )
    state.baseline_calculated.emit(metrics)

    # Verify yearly charts have data
    assert tab._yearly_charts["total_gain_pct"]._data, "Yearly gain chart should have data"
    assert tab._yearly_charts["count"]._data, "Yearly count chart should have data"


def test_breakdown_tab_update_charts_with_data(qtbot, sample_trades):
    """Test the shared chart update method works correctly."""
    from src.core.app_state import AppState
    from src.core.models import ColumnMapping
    from src.tabs.breakdown import BreakdownTab

    state = AppState()
    state.column_mapping = ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
        win_loss=None,
        win_loss_derived=True,
        breakeven_is_win=False,
    )
    state.baseline_df = sample_trades

    tab = BreakdownTab(state)
    qtbot.addWidget(tab)

    # Directly call the update method
    tab._update_charts_with_data(sample_trades)

    # Charts should now have data
    assert len(tab._yearly_charts["total_gain_pct"]._data) > 0


def test_breakdown_tab_displays_filtered_data_when_filters_applied(qtbot, sample_trades):
    """Test that filtered data overrides baseline when filters applied."""
    from src.core.app_state import AppState
    from src.core.models import ColumnMapping
    from src.tabs.breakdown import BreakdownTab

    state = AppState()
    state.column_mapping = ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
        win_loss=None,
        win_loss_derived=True,
        breakeven_is_win=False,
    )
    state.baseline_df = sample_trades
    # Apply filter - take only half the trades
    filtered = sample_trades.head(len(sample_trades) // 2).copy()
    state.filtered_df = filtered

    tab = BreakdownTab(state)
    qtbot.addWidget(tab)

    # Emit filtered_data_updated signal
    state.filtered_data_updated.emit(filtered)

    # Verify charts have data from filtered set
    assert tab._yearly_charts["count"]._data, "Count chart should have data"


def test_breakdown_tab_initializes_from_baseline_when_no_filtered(qtbot, sample_trades):
    """Test that initialization uses baseline_df when filtered_df is None."""
    from src.core.app_state import AppState
    from src.core.models import ColumnMapping
    from src.tabs.breakdown import BreakdownTab

    state = AppState()
    state.column_mapping = ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
        win_loss=None,
        win_loss_derived=True,
        breakeven_is_win=False,
    )
    state.baseline_df = sample_trades
    state.filtered_df = None  # Explicitly None

    tab = BreakdownTab(state)
    qtbot.addWidget(tab)

    # Should have initialized from baseline
    assert tab._yearly_charts["total_gain_pct"]._data, "Should initialize from baseline"


def test_breakdown_tab_year_change_uses_baseline_fallback(qtbot, sample_trades):
    """Test that year change works with baseline data when no filters applied."""
    from src.core.app_state import AppState
    from src.core.models import ColumnMapping
    from src.tabs.breakdown import BreakdownTab

    state = AppState()
    state.column_mapping = ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
        win_loss=None,
        win_loss_derived=True,
        breakeven_is_win=False,
    )
    state.baseline_df = sample_trades
    state.filtered_df = None

    tab = BreakdownTab(state)
    qtbot.addWidget(tab)

    # Initialize charts first
    tab._update_charts_with_data(sample_trades)

    # Get a year from the data
    years = pd.to_datetime(sample_trades["date"]).dt.year.unique()
    if len(years) > 0:
        # Trigger year change
        tab._on_year_changed(years[0])
        # Monthly charts should have data
        assert tab._monthly_charts["count"]._data is not None


def test_breakdown_tab_refresh_uses_baseline_fallback(qtbot, sample_trades):
    """Test that refresh uses baseline when no filtered data."""
    from src.core.app_state import AppState
    from src.core.models import ColumnMapping
    from src.tabs.breakdown import BreakdownTab

    state = AppState()
    state.column_mapping = ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
        win_loss=None,
        win_loss_derived=True,
        breakeven_is_win=False,
    )
    state.baseline_df = sample_trades
    state.filtered_df = None

    tab = BreakdownTab(state)
    qtbot.addWidget(tab)

    # Call refresh
    tab._refresh_charts()

    # Charts should have data from baseline
    assert tab._yearly_charts["total_gain_pct"]._data, "Refresh should use baseline"


def test_yearly_ev_chart_displays_data(qtbot, sample_trades):
    """Test that EV % chart displays correct data."""
    from src.core.app_state import AppState
    from src.core.models import ColumnMapping
    from src.tabs.breakdown import BreakdownTab

    state = AppState()
    state.column_mapping = ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
        win_loss=None,
        win_loss_derived=True,
        breakeven_is_win=False,
    )
    state.baseline_df = sample_trades
    state.filtered_df = None

    tab = BreakdownTab(state)
    qtbot.addWidget(tab)

    # Trigger chart update with data
    tab._update_charts_with_data(sample_trades)

    # Verify EV chart exists and has data
    assert "ev_pct" in tab._yearly_charts, "EV % chart should exist in yearly charts"
    ev_chart = tab._yearly_charts["ev_pct"]
    assert ev_chart._data is not None, "EV % chart should have data"
    assert len(ev_chart._data) > 0, "EV % chart should have at least one data point"
