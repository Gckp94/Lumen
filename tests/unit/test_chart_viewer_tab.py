"""Unit tests for ChartViewerTab."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from PyQt6.QtWidgets import QComboBox, QLabel, QSplitter

from src.core.app_state import AppState
from src.core.exit_simulator import ExitEvent, ScalingConfig
from src.core.models import AdjustmentParams, ColumnMapping
from src.tabs.chart_viewer import ChartViewerTab


class TestChartViewerTabInitialization:
    """Tests for ChartViewerTab initialization."""

    def test_creates_trade_browser(self, qtbot):
        """Tab creates a TradeBrowser component."""
        app_state = AppState()
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        assert tab._trade_browser is not None

    def test_creates_candlestick_chart(self, qtbot):
        """Tab creates a CandlestickChart component."""
        app_state = AppState()
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        assert tab._chart is not None

    def test_creates_resolution_selector(self, qtbot):
        """Tab creates resolution dropdown selector."""
        app_state = AppState()
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        assert tab._resolution_combo is not None
        assert isinstance(tab._resolution_combo, QComboBox)

    def test_creates_zoom_selector(self, qtbot):
        """Tab creates zoom preset dropdown selector."""
        app_state = AppState()
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        assert tab._zoom_combo is not None
        assert isinstance(tab._zoom_combo, QComboBox)

    def test_creates_trade_info_box(self, qtbot):
        """Tab creates trade info display box."""
        app_state = AppState()
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        assert tab._trade_info_label is not None
        assert isinstance(tab._trade_info_label, QLabel)

    def test_creates_scaling_config_panel(self, qtbot):
        """Tab creates scaling configuration panel."""
        app_state = AppState()
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        # Check spin boxes for scaling config
        assert tab._scale_pct_spin is not None
        assert tab._profit_target_spin is not None

    def test_uses_splitter_layout(self, qtbot):
        """Tab uses splitter for left panel and chart."""
        app_state = AppState()
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        assert tab._splitter is not None
        assert isinstance(tab._splitter, QSplitter)


class TestChartViewerTabResolutionOptions:
    """Tests for resolution dropdown options."""

    def test_has_all_resolution_options(self, qtbot):
        """Resolution dropdown has all expected options."""
        app_state = AppState()
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        expected_resolutions = [
            "1s", "5s", "15s", "30s",
            "1m", "2m", "5m", "15m", "30m", "60m",
            "Daily",
        ]

        items = [tab._resolution_combo.itemText(i) for i in range(tab._resolution_combo.count())]
        for res in expected_resolutions:
            assert res in items, f"Resolution '{res}' not found in dropdown"

    def test_default_resolution_is_1min(self, qtbot):
        """Default resolution is 1-minute."""
        app_state = AppState()
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        assert tab._resolution_combo.currentText() == "1m"


class TestChartViewerTabZoomOptions:
    """Tests for zoom preset dropdown options."""

    def test_has_all_zoom_options(self, qtbot):
        """Zoom dropdown has all expected presets."""
        app_state = AppState()
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        expected_zooms = [
            "Trade only",
            "Trade +/- 15min",
            "Trade +/- 30min",
            "Trade +/- 60min",
            "Full session",
        ]

        items = [tab._zoom_combo.itemText(i) for i in range(tab._zoom_combo.count())]
        for zoom in expected_zooms:
            assert zoom in items, f"Zoom preset '{zoom}' not found in dropdown"

    def test_default_zoom_is_30min(self, qtbot):
        """Default zoom is Trade +/- 30min."""
        app_state = AppState()
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        assert tab._zoom_combo.currentText() == "Trade +/- 30min"


class TestChartViewerTabSignalConnections:
    """Tests for signal connections."""

    def test_connects_to_filtered_data_updated(self, qtbot):
        """Tab connects to app_state.filtered_data_updated signal."""
        app_state = AppState()
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        # Check that signal is connected (by verifying handler exists)
        assert hasattr(tab, "_on_filtered_data_updated")

    def test_filtered_data_updated_updates_trade_browser(self, qtbot):
        """filtered_data_updated signal updates trade browser."""
        app_state = AppState()
        app_state.column_mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
            win_loss_derived=True,
        )

        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        # Create sample filtered data
        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL"],
            "date": ["2024-01-15", "2024-01-15"],
            "time": ["09:32:00", "10:15:00"],
            "gain_pct": [1.5, -0.8],
            "mae_pct": [0.5, 1.2],
            "mfe_pct": [2.0, 1.0],
            "entry_price": [150.0, 140.0],
        })

        # Emit signal
        app_state.filtered_data_updated.emit(df)

        # Trade browser should have data
        assert tab._trade_browser.trade_list.count() == 2


class TestChartViewerTabTradeSelection:
    """Tests for trade selection handling."""

    def test_trade_selected_updates_trade_info(self, qtbot):
        """Selecting a trade updates the trade info display."""
        app_state = AppState()
        app_state.column_mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
            win_loss_derived=True,
        )
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        # Set up trade data
        df = pd.DataFrame({
            "ticker": ["AAPL"],
            "date": ["2024-01-15"],
            "time": ["09:32:00"],
            "gain_pct": [1.5],
            "mae_pct": [0.5],
            "mfe_pct": [2.0],
            "entry_price": [150.0],
        })
        app_state.filtered_data_updated.emit(df)

        # Select the trade
        tab._trade_browser.trade_list.setCurrentRow(0)

        # Trade info should show ticker
        info_text = tab._trade_info_label.text()
        assert "AAPL" in info_text


class TestChartViewerTabScalingConfig:
    """Tests for scaling configuration panel."""

    def test_scale_pct_default_is_50(self, qtbot):
        """Scale percentage default is 50%."""
        app_state = AppState()
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        assert tab._scale_pct_spin.value() == 50

    def test_profit_target_default_is_35(self, qtbot):
        """Profit target default is 35%."""
        app_state = AppState()
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        assert tab._profit_target_spin.value() == 35

    def test_get_scaling_config_returns_correct_values(self, qtbot):
        """_get_scaling_config returns ScalingConfig with current values."""
        app_state = AppState()
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        tab._scale_pct_spin.setValue(60)
        tab._profit_target_spin.setValue(25)

        config = tab._get_scaling_config()

        assert isinstance(config, ScalingConfig)
        assert config.scale_pct == 60
        assert config.profit_target_pct == 25


class TestChartViewerTabStopLevel:
    """Tests for stop level calculation."""

    def test_stop_level_calculated_from_adjustment_params(self, qtbot):
        """Stop level is calculated from adjustment_params.stop_loss."""
        app_state = AppState()
        # Explicitly set is_short=False for long trade test
        app_state.adjustment_params = AdjustmentParams(
            stop_loss=10.0, efficiency=5.0, is_short=False
        )

        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        entry_price = 100.0
        # For long trade: stop_level = entry_price * (1 - stop_loss_percent/100)
        expected_stop = 100.0 * (1 - 10.0 / 100)  # = 90.0

        stop_level = tab._calculate_stop_level(entry_price)

        assert stop_level == expected_stop

    def test_stop_level_with_different_entry_price(self, qtbot):
        """Stop level scales correctly with entry price."""
        app_state = AppState()
        # Explicitly set is_short=False for long trade test
        app_state.adjustment_params = AdjustmentParams(
            stop_loss=8.0, efficiency=5.0, is_short=False
        )

        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        entry_price = 150.0
        expected_stop = 150.0 * (1 - 8.0 / 100)  # = 138.0

        stop_level = tab._calculate_stop_level(entry_price)

        assert stop_level == expected_stop


class TestChartViewerTabPriceDataLoading:
    """Tests for price data loading."""

    def test_load_chart_for_trade_calls_price_loader(self, qtbot):
        """_load_chart_for_trade uses PriceDataLoader to load data."""
        app_state = AppState()
        app_state.column_mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
            win_loss_derived=True,
        )
        app_state.adjustment_params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)

        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        # Mock the price data loader
        mock_loader = MagicMock()
        mock_loader.load.return_value = pd.DataFrame({
            "datetime": pd.date_range("2024-01-15 09:30", periods=10, freq="1min"),
            "open": [150.0] * 10,
            "high": [151.0] * 10,
            "low": [149.0] * 10,
            "close": [150.5] * 10,
            "volume": [1000] * 10,
        })
        tab._price_loader = mock_loader

        trade_data = {
            "ticker": "AAPL",
            "date": "2024-01-15",
            "entry_time": datetime(2024, 1, 15, 9, 32),
            "entry_price": 150.0,
            "gain_pct": 1.5,
        }

        tab._load_chart_for_trade(trade_data)

        # Price loader should have been called
        mock_loader.load.assert_called_once()


class TestChartViewerTabExitSimulation:
    """Tests for exit simulation integration."""

    def test_load_chart_simulates_exits(self, qtbot):
        """_load_chart_for_trade runs ExitSimulator on price data."""
        app_state = AppState()
        app_state.column_mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
            win_loss_derived=True,
        )
        # Explicitly set is_short=False for long trade test
        app_state.adjustment_params = AdjustmentParams(
            stop_loss=8.0, efficiency=5.0, is_short=False
        )

        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        # Mock price data loader
        mock_loader = MagicMock()
        price_df = pd.DataFrame({
            "datetime": pd.date_range("2024-01-15 09:30", periods=60, freq="1min"),
            "open": [150.0] * 60,
            "high": [160.0] * 60,  # Will trigger profit target
            "low": [149.0] * 60,
            "close": [155.0] * 60,
            "volume": [1000] * 60,
        })
        mock_loader.load.return_value = price_df
        tab._price_loader = mock_loader

        # Mock chart to capture calls
        tab._chart = MagicMock()

        trade_data = {
            "ticker": "AAPL",
            "date": "2024-01-15",
            "entry_time": datetime(2024, 1, 15, 9, 32),
            "entry_price": 150.0,
            "gain_pct": 1.5,
        }

        tab._load_chart_for_trade(trade_data)

        # Chart should have set_markers called
        tab._chart.set_markers.assert_called_once()


class TestChartViewerTabEmptyState:
    """Tests for empty state handling."""

    def test_shows_empty_state_initially(self, qtbot):
        """Tab shows empty state when no data is loaded."""
        app_state = AppState()
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        # Trade browser should be empty
        assert tab._trade_browser.trade_list.count() == 0

    def test_trade_info_empty_initially(self, qtbot):
        """Trade info shows placeholder when no trade selected."""
        app_state = AppState()
        tab = ChartViewerTab(app_state)
        qtbot.addWidget(tab)

        # Trade info should have placeholder text
        info_text = tab._trade_info_label.text()
        assert "Select a trade" in info_text or info_text == ""
