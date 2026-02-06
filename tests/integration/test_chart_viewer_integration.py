"""Integration tests for Chart Viewer tab full workflow.

Tests the complete workflow:
1. Trade selection from TradeBrowser
2. Price data loading from parquet files
3. Exit simulation
4. Chart display with markers

Uses tmp_path fixture for mock parquet data files.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from PyQt6.QtCore import Qt

from src.core.app_state import AppState
from src.core.exit_simulator import ExitEvent, ScalingConfig
from src.core.models import AdjustmentParams, ColumnMapping
from src.core.price_data import PriceDataLoader, Resolution
from src.tabs.chart_viewer import ChartViewerTab


@pytest.fixture
def app_state() -> AppState:
    """Create a fresh AppState for each test."""
    return AppState()


@pytest.fixture
def column_mapping() -> ColumnMapping:
    """Create column mapping for tests."""
    return ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
        win_loss=None,
        breakeven_is_win=True,
        win_loss_derived=True,
    )


@pytest.fixture
def sample_trades_df() -> pd.DataFrame:
    """Create sample trading data for tests."""
    return pd.DataFrame({
        "ticker": ["AAPL", "GOOGL", "MSFT", "TSLA"],
        "date": ["2024-01-15", "2024-01-15", "2024-01-16", "2024-01-16"],
        "time": ["09:32:00", "10:15:00", "09:45:00", "11:00:00"],
        "gain_pct": [2.5, -1.2, 3.8, -0.5],
        "mae_pct": [0.5, 1.5, 0.3, 0.8],
        "mfe_pct": [3.0, 0.5, 4.2, 1.0],
        "entry_price": [150.0, 140.0, 380.0, 250.0],
    })


@pytest.fixture
def mock_price_data_path(tmp_path: Path) -> Path:
    """Create mock parquet files with sample price bars.

    Creates minute-level price data files for testing.
    """
    # Create directory structure for minute-level data
    minute_path = tmp_path / "Minute-Level"
    minute_path.mkdir(parents=True, exist_ok=True)

    # Generate price data for 2024-01-15
    base_time = pd.Timestamp("2024-01-15 09:30:00")
    times = [base_time + pd.Timedelta(minutes=i) for i in range(391)]  # Full trading day

    # Create AAPL data with price movement that will trigger profit target
    # Entry at 09:32 at $150, price rises to hit 35% profit target at $202.50
    aapl_data = pd.DataFrame({
        "ticker": ["AAPL"] * 391,
        "datetime": times,
        "open": np.linspace(148, 210, 391),
        "high": np.linspace(150, 215, 391),
        "low": np.linspace(147, 205, 391),
        "close": np.linspace(149, 212, 391),
        "volume": np.random.randint(1000, 10000, 391),
    })

    # Create GOOGL data with price movement that hits stop
    googl_data = pd.DataFrame({
        "ticker": ["GOOGL"] * 391,
        "datetime": times,
        "open": np.linspace(140, 125, 391),
        "high": np.linspace(142, 128, 391),
        "low": np.linspace(138, 120, 391),
        "close": np.linspace(139, 122, 391),
        "volume": np.random.randint(1000, 10000, 391),
    })

    # Combine and save
    day1_data = pd.concat([aapl_data, googl_data], ignore_index=True)
    day1_data.to_parquet(minute_path / "2024-01-15.parquet")

    # Generate price data for 2024-01-16
    base_time_2 = pd.Timestamp("2024-01-16 09:30:00")
    times_2 = [base_time_2 + pd.Timedelta(minutes=i) for i in range(391)]

    # Create MSFT data
    msft_data = pd.DataFrame({
        "ticker": ["MSFT"] * 391,
        "datetime": times_2,
        "open": np.linspace(378, 420, 391),
        "high": np.linspace(380, 425, 391),
        "low": np.linspace(376, 415, 391),
        "close": np.linspace(379, 422, 391),
        "volume": np.random.randint(1000, 10000, 391),
    })

    # Create TSLA data
    tsla_data = pd.DataFrame({
        "ticker": ["TSLA"] * 391,
        "datetime": times_2,
        "open": np.linspace(250, 245, 391),
        "high": np.linspace(252, 248, 391),
        "low": np.linspace(248, 240, 391),
        "close": np.linspace(249, 243, 391),
        "volume": np.random.randint(1000, 10000, 391),
    })

    day2_data = pd.concat([msft_data, tsla_data], ignore_index=True)
    day2_data.to_parquet(minute_path / "2024-01-16.parquet")

    return minute_path


@pytest.fixture
def configured_app_state(
    app_state: AppState,
    column_mapping: ColumnMapping,
    sample_trades_df: pd.DataFrame,
) -> AppState:
    """Create AppState with loaded data and column mapping."""
    app_state.raw_df = sample_trades_df.copy()
    app_state.baseline_df = sample_trades_df.copy()
    app_state.filtered_df = sample_trades_df.copy()
    app_state.column_mapping = column_mapping
    app_state.adjustment_params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
    return app_state


class TestChartViewerFullWorkflow:
    """Integration tests for complete chart viewer workflow."""

    def test_trade_selection_loads_chart(
        self,
        qtbot,
        configured_app_state: AppState,
        mock_price_data_path: Path,
    ):
        """Full workflow: trade selection -> price data load -> chart display.

        Steps:
        1. Create ChartViewerTab with configured app state
        2. Set price loader to use mock data path
        3. Emit filtered_data_updated to populate trade browser
        4. Select a trade from the browser
        5. Verify chart displays price data and markers
        """
        # Create tab
        tab = ChartViewerTab(configured_app_state)
        qtbot.addWidget(tab)

        # Configure price loader with mock data path
        tab._price_loader = PriceDataLoader(minute_path=mock_price_data_path)

        # Emit filtered data to populate trade browser
        configured_app_state.filtered_data_updated.emit(configured_app_state.filtered_df)

        # Verify trade browser has trades
        assert tab._trade_browser.trade_list.count() == 4

        # Select first trade (AAPL)
        tab._trade_browser.trade_list.setCurrentRow(0)

        # Verify trade info is updated
        info_text = tab._trade_info_label.text()
        assert "AAPL" in info_text
        assert "150.00" in info_text

        # Verify chart has data
        assert tab._chart._candle_item._data is not None
        assert len(tab._chart._candle_item._data) > 0

        # Verify markers are set (entry marker at minimum)
        assert len(tab._chart._marker_items) >= 1

    def test_exit_simulation_runs_on_trade_selection(
        self,
        qtbot,
        configured_app_state: AppState,
        mock_price_data_path: Path,
    ):
        """Exit simulation runs when trade is selected.

        Verifies that ExitSimulator generates exit events that are
        displayed as markers on the chart.
        """
        tab = ChartViewerTab(configured_app_state)
        qtbot.addWidget(tab)
        tab._price_loader = PriceDataLoader(minute_path=mock_price_data_path)

        # Populate trades
        configured_app_state.filtered_data_updated.emit(configured_app_state.filtered_df)

        # Select AAPL trade
        tab._trade_browser.trade_list.setCurrentRow(0)

        # With default scaling (50% at 35% profit), price movement should trigger exits
        # Check that markers include entry + at least one exit or level line
        assert len(tab._chart._marker_items) >= 2

    def test_full_workflow_from_view_chart_requested_signal(
        self,
        qtbot,
        configured_app_state: AppState,
        mock_price_data_path: Path,
    ):
        """Full workflow triggered by external view_chart_requested signal.

        This simulates the Statistics tab's "View Chart" context menu action.
        """
        tab = ChartViewerTab(configured_app_state)
        qtbot.addWidget(tab)
        tab._price_loader = PriceDataLoader(minute_path=mock_price_data_path)

        # Simulate external request to view chart
        trade_data = {
            "ticker": "AAPL",
            "date": "2024-01-15",
            "entry_time": datetime(2024, 1, 15, 9, 32),
            "entry_price": 150.0,
            "pnl_pct": 2.5,
        }

        # Emit the view_chart_requested signal
        configured_app_state.view_chart_requested.emit(trade_data)

        # Verify trade info is updated
        info_text = tab._trade_info_label.text()
        assert "AAPL" in info_text

        # Verify chart displays data
        assert tab._chart._candle_item._data is not None
        assert len(tab._chart._candle_item._data) > 0


class TestMissingPriceDataHandling:
    """Tests for handling missing price data gracefully."""

    def test_missing_parquet_file_shows_empty_chart(
        self,
        qtbot,
        configured_app_state: AppState,
        tmp_path: Path,
    ):
        """Chart clears when price data file is missing.

        When a trade is selected but no parquet file exists for that date,
        the chart should clear without error.
        """
        tab = ChartViewerTab(configured_app_state)
        qtbot.addWidget(tab)

        # Use empty directory as price path
        empty_path = tmp_path / "empty_minute_data"
        empty_path.mkdir(parents=True, exist_ok=True)
        tab._price_loader = PriceDataLoader(minute_path=empty_path)

        # Populate trades
        configured_app_state.filtered_data_updated.emit(configured_app_state.filtered_df)

        # Select a trade - should not crash
        tab._trade_browser.trade_list.setCurrentRow(0)

        # Chart should be cleared (no data)
        assert tab._chart._candle_item._data is None or len(tab._chart._candle_item._data) == 0

    def test_missing_ticker_in_file_shows_empty_chart(
        self,
        qtbot,
        configured_app_state: AppState,
        tmp_path: Path,
    ):
        """Chart clears when ticker is not found in parquet file.

        When the parquet file exists but doesn't contain the selected ticker,
        the chart should clear without error.
        """
        # Create price data with only MSFT (no AAPL)
        minute_path = tmp_path / "minute_data"
        minute_path.mkdir(parents=True, exist_ok=True)

        base_time = pd.Timestamp("2024-01-15 09:30:00")
        times = [base_time + pd.Timedelta(minutes=i) for i in range(60)]

        msft_only = pd.DataFrame({
            "ticker": ["MSFT"] * 60,
            "datetime": times,
            "open": [380.0] * 60,
            "high": [382.0] * 60,
            "low": [378.0] * 60,
            "close": [381.0] * 60,
            "volume": [1000] * 60,
        })
        msft_only.to_parquet(minute_path / "2024-01-15.parquet")

        tab = ChartViewerTab(configured_app_state)
        qtbot.addWidget(tab)
        tab._price_loader = PriceDataLoader(minute_path=minute_path)

        # Populate trades
        configured_app_state.filtered_data_updated.emit(configured_app_state.filtered_df)

        # Select AAPL trade (which isn't in the parquet file)
        tab._trade_browser.trade_list.setCurrentRow(0)

        # Chart should be cleared
        assert tab._chart._candle_item._data is None or len(tab._chart._candle_item._data) == 0


class TestResolutionChangeUpdatesChart:
    """Tests for resolution dropdown updates."""

    def test_resolution_change_reloads_chart(
        self,
        qtbot,
        configured_app_state: AppState,
        mock_price_data_path: Path,
    ):
        """Changing resolution reloads chart with new aggregation.

        When resolution dropdown changes, the chart should reload
        with data aggregated to the new resolution.
        """
        tab = ChartViewerTab(configured_app_state)
        qtbot.addWidget(tab)
        tab._price_loader = PriceDataLoader(minute_path=mock_price_data_path)

        # Populate and select trade
        configured_app_state.filtered_data_updated.emit(configured_app_state.filtered_df)
        tab._trade_browser.trade_list.setCurrentRow(0)

        # Record initial bar count at 1-minute resolution
        initial_bar_count = len(tab._chart._candle_item._data)
        assert initial_bar_count > 0

        # Change to 5-minute resolution
        tab._resolution_combo.setCurrentText("5m")

        # Chart should have fewer bars (aggregated)
        new_bar_count = len(tab._chart._candle_item._data)
        assert new_bar_count < initial_bar_count
        # 5-min bars should be roughly 1/5 of 1-min bars
        assert new_bar_count <= initial_bar_count // 4

    def test_resolution_change_without_trade_does_nothing(
        self,
        qtbot,
        configured_app_state: AppState,
    ):
        """Changing resolution without selected trade does nothing.

        When no trade is selected, changing resolution should not cause errors.
        """
        tab = ChartViewerTab(configured_app_state)
        qtbot.addWidget(tab)

        # Change resolution without selecting a trade
        tab._resolution_combo.setCurrentText("5m")
        tab._resolution_combo.setCurrentText("15m")
        tab._resolution_combo.setCurrentText("1m")

        # Should not crash, chart should remain empty
        assert tab._chart._candle_item._data is None or len(tab._chart._candle_item._data) == 0


class TestZoomFilterCorrectlyFiltersBars:
    """Tests for zoom preset filtering."""

    def test_zoom_trade_only_shows_narrow_window(
        self,
        qtbot,
        configured_app_state: AppState,
        mock_price_data_path: Path,
    ):
        """'Trade only' zoom shows narrow window around entry.

        The 'Trade only' zoom preset should show a minimal window
        (5 minutes by default) around the trade entry time.
        """
        tab = ChartViewerTab(configured_app_state)
        qtbot.addWidget(tab)
        tab._price_loader = PriceDataLoader(minute_path=mock_price_data_path)

        # Populate and select trade
        configured_app_state.filtered_data_updated.emit(configured_app_state.filtered_df)
        tab._trade_browser.trade_list.setCurrentRow(0)

        # Get bar count at default zoom (+/- 30min)
        default_bar_count = len(tab._chart._candle_item._data)

        # Change to "Trade only" zoom
        tab._zoom_combo.setCurrentText("Trade only")

        # Should have fewer bars
        trade_only_bar_count = len(tab._chart._candle_item._data)
        assert trade_only_bar_count < default_bar_count
        # Trade only shows +/- 5 minutes = about 11 bars
        assert trade_only_bar_count <= 15

    def test_zoom_full_session_shows_all_bars(
        self,
        qtbot,
        configured_app_state: AppState,
        mock_price_data_path: Path,
    ):
        """'Full session' zoom shows all bars for the day.

        The 'Full session' zoom preset should show all available bars
        without any time filtering.
        """
        tab = ChartViewerTab(configured_app_state)
        qtbot.addWidget(tab)
        tab._price_loader = PriceDataLoader(minute_path=mock_price_data_path)

        # Populate and select trade
        configured_app_state.filtered_data_updated.emit(configured_app_state.filtered_df)
        tab._trade_browser.trade_list.setCurrentRow(0)

        # Get bar count at default zoom
        default_bar_count = len(tab._chart._candle_item._data)

        # Change to "Full session" zoom
        tab._zoom_combo.setCurrentText("Full session")

        # Should have all bars (approximately 391 for full trading day)
        # Allow small margin for OHLC validation filtering
        full_session_bar_count = len(tab._chart._candle_item._data)
        assert full_session_bar_count > default_bar_count
        assert full_session_bar_count >= 385  # Allow margin for validation

    def test_zoom_15min_filter_correctly_applied(
        self,
        qtbot,
        configured_app_state: AppState,
        mock_price_data_path: Path,
    ):
        """'+/- 15min' zoom shows correct time window.

        The '+/- 15min' zoom preset should show bars in a 30-minute window
        centered on entry time. Since entry is at 09:32 and data starts at
        09:30, we get ~2 bars before + ~15 bars after = ~18 bars.
        """
        tab = ChartViewerTab(configured_app_state)
        qtbot.addWidget(tab)
        tab._price_loader = PriceDataLoader(minute_path=mock_price_data_path)

        # Populate and select trade
        configured_app_state.filtered_data_updated.emit(configured_app_state.filtered_df)
        tab._trade_browser.trade_list.setCurrentRow(0)

        # Change to "+/- 15min" zoom
        tab._zoom_combo.setCurrentText("Trade +/- 15min")

        # Entry at 09:32, filter is +/- 15min = 09:17 to 09:47
        # Data starts at 09:30, so we get 09:30-09:47 = ~18 bars
        bar_count = len(tab._chart._candle_item._data)
        assert 15 <= bar_count <= 25  # Allow some tolerance

    def test_zoom_60min_filter_correctly_applied(
        self,
        qtbot,
        configured_app_state: AppState,
        mock_price_data_path: Path,
    ):
        """'+/- 60min' zoom shows correct time window.

        The '+/- 60min' zoom preset should show bars in a 120-minute window
        centered on entry time. Since entry is at 09:32 and data starts at
        09:30, we get ~2 bars before + ~60 bars after = ~63 bars.
        """
        tab = ChartViewerTab(configured_app_state)
        qtbot.addWidget(tab)
        tab._price_loader = PriceDataLoader(minute_path=mock_price_data_path)

        # Populate and select trade
        configured_app_state.filtered_data_updated.emit(configured_app_state.filtered_df)
        tab._trade_browser.trade_list.setCurrentRow(0)

        # Change to "+/- 60min" zoom
        tab._zoom_combo.setCurrentText("Trade +/- 60min")

        # Entry at 09:32, filter is +/- 60min = 08:32 to 10:32
        # Data starts at 09:30, so we get 09:30-10:32 = ~63 bars
        bar_count = len(tab._chart._candle_item._data)
        assert 55 <= bar_count <= 75  # Allow some tolerance


class TestScalingConfigUpdatesChart:
    """Tests for scaling configuration panel."""

    def test_scale_pct_change_reloads_chart(
        self,
        qtbot,
        configured_app_state: AppState,
        mock_price_data_path: Path,
    ):
        """Changing scale percentage reloads chart with new exit simulation.

        When the scale percentage spinbox value changes, the exit simulation
        should re-run and chart markers should update.
        """
        tab = ChartViewerTab(configured_app_state)
        qtbot.addWidget(tab)
        tab._price_loader = PriceDataLoader(minute_path=mock_price_data_path)

        # Populate and select trade
        configured_app_state.filtered_data_updated.emit(configured_app_state.filtered_df)
        tab._trade_browser.trade_list.setCurrentRow(0)

        # Record initial marker count
        initial_marker_count = len(tab._chart._marker_items)
        assert initial_marker_count >= 1

        # Change scale percentage
        tab._scale_pct_spin.setValue(75)

        # Markers should still be present (may have same or different count)
        assert len(tab._chart._marker_items) >= 1

    def test_profit_target_change_reloads_chart(
        self,
        qtbot,
        configured_app_state: AppState,
        mock_price_data_path: Path,
    ):
        """Changing profit target reloads chart with new exit simulation.

        When the profit target spinbox value changes, the exit simulation
        should re-run with the new target level.
        """
        tab = ChartViewerTab(configured_app_state)
        qtbot.addWidget(tab)
        tab._price_loader = PriceDataLoader(minute_path=mock_price_data_path)

        # Populate and select trade
        configured_app_state.filtered_data_updated.emit(configured_app_state.filtered_df)
        tab._trade_browser.trade_list.setCurrentRow(0)

        # Change profit target to very high value (less likely to hit)
        tab._profit_target_spin.setValue(100)

        # Chart should still have markers
        assert len(tab._chart._marker_items) >= 1


class TestChartViewerTabLifecycle:
    """Tests for tab lifecycle and cleanup."""

    def test_tab_closes_without_error(
        self,
        qtbot,
        configured_app_state: AppState,
        mock_price_data_path: Path,
    ):
        """Tab closes cleanly after use.

        Verifies that signal disconnections happen properly during close.
        """
        tab = ChartViewerTab(configured_app_state)
        qtbot.addWidget(tab)
        tab._price_loader = PriceDataLoader(minute_path=mock_price_data_path)

        # Use the tab
        configured_app_state.filtered_data_updated.emit(configured_app_state.filtered_df)
        tab._trade_browser.trade_list.setCurrentRow(0)

        # Close should not raise
        tab.close()

    def test_multiple_trade_selections(
        self,
        qtbot,
        configured_app_state: AppState,
        mock_price_data_path: Path,
    ):
        """Multiple trade selections work correctly.

        Rapidly selecting different trades should not cause issues.
        """
        tab = ChartViewerTab(configured_app_state)
        qtbot.addWidget(tab)
        tab._price_loader = PriceDataLoader(minute_path=mock_price_data_path)

        # Populate trades
        configured_app_state.filtered_data_updated.emit(configured_app_state.filtered_df)

        # Select each trade in sequence
        for i in range(4):
            tab._trade_browser.trade_list.setCurrentRow(i)

            # Verify chart updates (may be empty if no data for that ticker/date)
            # Main thing is no crashes
            info_text = tab._trade_info_label.text()
            assert info_text != ""

        # Select back to first trade
        tab._trade_browser.trade_list.setCurrentRow(0)
        assert "AAPL" in tab._trade_info_label.text()


@pytest.mark.integration
class TestColumnMappingSignalHandling:
    """Tests for column mapping signal handling in Chart Viewer."""

    def test_trade_browser_populates_after_column_mapping_changed(
        self, qtbot, app_state, column_mapping
    ):
        """
        Trade browser should populate when column_mapping_changed signal fires.

        This tests the scenario where:
        1. Chart Viewer tab is created before CSV is loaded
        2. User loads CSV and configures column mapping
        3. column_mapping_changed signal fires
        4. Trade browser should then populate with the trades
        """
        # Create Chart Viewer tab BEFORE loading data
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        # Verify trade browser is empty initially
        assert tab._trade_browser.trade_list.count() == 0

        # Create baseline data (simulating CSV load)
        test_df = pd.DataFrame({
            "ticker": ["AAPL", "MSFT", "GOOG"],
            "date": ["2024-01-15", "2024-01-15", "2024-01-16"],
            "time": ["09:35:00", "10:15:00", "09:45:00"],
            "gain_pct": [2.5, -1.5, 3.0],
            "mae_pct": [-0.5, -2.0, -0.3],
            "mfe_pct": [3.0, 0.5, 3.5],
        })

        # Set baseline data and column mapping (simulating column mapping dialog)
        app_state.baseline_df = test_df
        app_state.column_mapping = column_mapping

        # Fire the column_mapping_changed signal
        app_state.column_mapping_changed.emit(column_mapping)

        # Trade browser should now be populated
        assert tab._trade_browser.trade_list.count() == 3

    def test_trade_browser_updates_when_column_mapping_changes_with_existing_data(
        self, qtbot, app_state, column_mapping
    ):
        """
        Trade browser should update when column mapping changes on existing data.
        """
        # Create tab and set baseline data without column mapping
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        test_df = pd.DataFrame({
            "ticker": ["AAPL", "MSFT"],
            "date": ["2024-01-15", "2024-01-15"],
            "time": ["09:35:00", "10:15:00"],
            "gain_pct": [2.5, -1.5],
            "mae_pct": [-0.5, -2.0],
            "mfe_pct": [3.0, 0.5],
        })

        app_state.baseline_df = test_df

        # Without column mapping, trade browser should be empty
        tab._initialize_from_state()
        assert tab._trade_browser.trade_list.count() == 0

        # Set column mapping and fire signal
        app_state.column_mapping = column_mapping
        app_state.column_mapping_changed.emit(column_mapping)

        # Now trade browser should be populated
        assert tab._trade_browser.trade_list.count() == 2

    def test_trade_browser_handles_excel_serial_time_format(
        self, qtbot, app_state, column_mapping
    ):
        """
        Trade browser should handle Excel serial time format (floats 0-1).

        Excel serial time represents time as fraction of day:
        - 0.0 = midnight (00:00)
        - 0.5 = noon (12:00)
        - 0.395833... = 09:30
        """
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        # Create data with Excel serial time format
        test_df = pd.DataFrame({
            "ticker": ["AAPL", "MSFT"],
            "date": ["2024-01-15", "2024-01-15"],
            "time": [0.395833, 0.427083],  # 09:30 and 10:15 in Excel serial format
            "gain_pct": [2.5, -1.5],
            "mae_pct": [-0.5, -2.0],
            "mfe_pct": [3.0, 0.5],
        })

        app_state.baseline_df = test_df
        app_state.column_mapping = column_mapping
        app_state.column_mapping_changed.emit(column_mapping)

        # Trade browser should be populated
        assert tab._trade_browser.trade_list.count() == 2

        # Verify the time was parsed correctly (first item should show around 09:30)
        first_item = tab._trade_browser.trade_list.item(0)
        assert "AAPL" in first_item.text()
        # 0.395833 ≈ 09:29:59, so accept 09:29 or 09:30
        assert "09:2" in first_item.text() or "09:3" in first_item.text()


class TestChartAutoFit:
    """Tests for chart auto-fit on load."""

    def test_chart_auto_ranges_after_markers_set(
        self,
        qtbot,
        configured_app_state: AppState,
        mock_price_data_path,
    ):
        """Chart should auto-range after markers are set to ensure proper fit.

        This tests that auto_range is called after set_markers so the chart
        fits all data including markers.
        """
        from datetime import date
        from unittest.mock import patch

        # Create tab
        tab = ChartViewerTab(configured_app_state)
        qtbot.addWidget(tab)

        # Configure price loader with mock data path
        tab._price_loader = PriceDataLoader(minute_path=mock_price_data_path)

        # Populate trades
        configured_app_state.filtered_data_updated.emit(configured_app_state.filtered_df)

        # Patch auto_range before selecting a trade
        with patch.object(tab._chart, 'auto_range') as mock_auto_range:
            # Select first trade (AAPL) which triggers _load_chart_for_trade
            tab._trade_browser.trade_list.setCurrentRow(0)

            # auto_range should have been called once after set_markers
            mock_auto_range.assert_called_once()
