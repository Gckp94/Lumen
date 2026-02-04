"""Unit tests for CandlestickChart component."""

from datetime import datetime

import numpy as np
import pandas as pd
import pyqtgraph as pg  # type: ignore[import-untyped]
import pytest
from PyQt6.QtCore import Qt

from src.core.exit_simulator import ExitEvent
from src.ui.components.candlestick_chart import CandlestickChart, CandlestickItem


class TestCandlestickItemInitialization:
    """Tests for CandlestickItem initialization."""

    def test_creates_empty_item(self, qtbot):
        """CandlestickItem can be created without data."""
        item = CandlestickItem()
        assert item is not None

    def test_bounding_rect_empty(self, qtbot):
        """boundingRect returns empty rect when no data."""
        item = CandlestickItem()
        rect = item.boundingRect()
        assert rect is not None


class TestCandlestickItemSetData:
    """Tests for CandlestickItem.set_data() method."""

    def test_set_data_accepts_array(self, qtbot):
        """set_data() accepts numpy array with OHLC data."""
        item = CandlestickItem()

        # Array format: [time_idx, open, high, low, close]
        data = np.array([
            [0, 100.0, 105.0, 98.0, 103.0],
            [1, 103.0, 108.0, 101.0, 106.0],
            [2, 106.0, 107.0, 100.0, 101.0],
        ])
        item.set_data(data)

        assert item._data is not None
        assert len(item._data) == 3

    def test_set_data_empty_array(self, qtbot):
        """set_data() handles empty array."""
        item = CandlestickItem()
        data = np.array([]).reshape(0, 5)
        item.set_data(data)

        assert item._data is not None
        assert len(item._data) == 0

    def test_set_data_none_clears(self, qtbot):
        """set_data(None) clears data."""
        item = CandlestickItem()

        # First set some data
        data = np.array([[0, 100.0, 105.0, 98.0, 103.0]])
        item.set_data(data)
        assert len(item._data) == 1

        # Then clear
        item.set_data(None)
        assert item._data is None or len(item._data) == 0

    def test_bounding_rect_with_data(self, qtbot):
        """boundingRect returns proper rect when data present."""
        item = CandlestickItem()

        data = np.array([
            [0, 100.0, 110.0, 95.0, 105.0],
            [1, 105.0, 115.0, 100.0, 110.0],
        ])
        item.set_data(data)

        rect = item.boundingRect()
        # Rect should encompass the data
        assert rect.width() > 0
        assert rect.height() > 0


class TestCandlestickChartInitialization:
    """Tests for CandlestickChart initialization."""

    def test_creates_widget(self, qtbot):
        """CandlestickChart widget can be created."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)
        assert chart is not None

    def test_has_candle_item(self, qtbot):
        """CandlestickChart has _candle_item attribute."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)
        assert hasattr(chart, "_candle_item")
        assert chart._candle_item is not None

    def test_has_marker_items_list(self, qtbot):
        """CandlestickChart has _marker_items list."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)
        assert hasattr(chart, "_marker_items")
        assert isinstance(chart._marker_items, list)

    def test_has_plot_widget(self, qtbot):
        """CandlestickChart has underlying PlotWidget."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)
        assert hasattr(chart, "_plot_widget")
        assert chart._plot_widget is not None


class TestCandlestickChartSetData:
    """Tests for CandlestickChart.set_data() method."""

    def test_set_data_with_dataframe(self, qtbot):
        """set_data() accepts DataFrame with OHLCV columns."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        df = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",
                "2024-01-15 09:34",
            ]),
            "open": [100.0, 103.0, 106.0],
            "high": [105.0, 108.0, 107.0],
            "low": [98.0, 101.0, 100.0],
            "close": [103.0, 106.0, 101.0],
            "volume": [1000, 1200, 800],
        })
        chart.set_data(df)

        assert chart._candle_item._data is not None
        assert len(chart._candle_item._data) == 3

    def test_set_data_empty_dataframe(self, qtbot):
        """set_data() handles empty DataFrame."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        df = pd.DataFrame(columns=["datetime", "open", "high", "low", "close"])
        chart.set_data(df)

        assert chart._candle_item._data is None or len(chart._candle_item._data) == 0

    def test_set_data_none_clears(self, qtbot):
        """set_data(None) clears the chart."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        # First add some data
        df = pd.DataFrame({
            "datetime": pd.to_datetime(["2024-01-15 09:32"]),
            "open": [100.0],
            "high": [105.0],
            "low": [98.0],
            "close": [103.0],
        })
        chart.set_data(df)
        assert len(chart._candle_item._data) == 1

        # Then clear
        chart.set_data(None)
        assert chart._candle_item._data is None or len(chart._candle_item._data) == 0


class TestCandlestickChartSetMarkers:
    """Tests for CandlestickChart.set_markers() method."""

    def test_set_markers_entry_point(self, qtbot):
        """set_markers() creates entry point marker."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        # Set data first
        df = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",
                "2024-01-15 09:34",
            ]),
            "open": [100.0, 103.0, 106.0],
            "high": [105.0, 108.0, 107.0],
            "low": [98.0, 101.0, 100.0],
            "close": [103.0, 106.0, 101.0],
        })
        chart.set_data(df)

        entry_time = datetime(2024, 1, 15, 9, 32)
        entry_price = 100.0

        chart.set_markers(
            entry_time=entry_time,
            entry_price=entry_price,
            exits=[],
            stop_level=None,
            profit_target=None,
        )

        # Should have at least one marker (entry point)
        assert len(chart._marker_items) >= 1

    def test_set_markers_exit_points(self, qtbot):
        """set_markers() creates exit point markers."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        # Set data first
        df = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",
                "2024-01-15 09:34",
            ]),
            "open": [100.0, 103.0, 106.0],
            "high": [105.0, 108.0, 107.0],
            "low": [98.0, 101.0, 100.0],
            "close": [103.0, 106.0, 101.0],
        })
        chart.set_data(df)

        entry_time = datetime(2024, 1, 15, 9, 32)
        entry_price = 100.0

        exits = [
            ExitEvent(
                time=datetime(2024, 1, 15, 9, 33),
                price=106.0,
                pct=50.0,
                reason="profit_target",
            ),
            ExitEvent(
                time=datetime(2024, 1, 15, 9, 34),
                price=101.0,
                pct=50.0,
                reason="session_close",
            ),
        ]

        chart.set_markers(
            entry_time=entry_time,
            entry_price=entry_price,
            exits=exits,
            stop_level=None,
            profit_target=None,
        )

        # Should have entry marker + 2 exit markers = at least 3
        assert len(chart._marker_items) >= 3

    def test_set_markers_stop_level(self, qtbot):
        """set_markers() creates stop level line."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        # Set data first
        df = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",
            ]),
            "open": [100.0, 103.0],
            "high": [105.0, 108.0],
            "low": [98.0, 101.0],
            "close": [103.0, 106.0],
        })
        chart.set_data(df)

        chart.set_markers(
            entry_time=datetime(2024, 1, 15, 9, 32),
            entry_price=100.0,
            exits=[],
            stop_level=95.0,
            profit_target=None,
        )

        # Should have entry marker + stop line
        assert len(chart._marker_items) >= 2

    def test_set_markers_profit_target(self, qtbot):
        """set_markers() creates profit target line."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        # Set data first
        df = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",
            ]),
            "open": [100.0, 103.0],
            "high": [105.0, 108.0],
            "low": [98.0, 101.0],
            "close": [103.0, 106.0],
        })
        chart.set_data(df)

        chart.set_markers(
            entry_time=datetime(2024, 1, 15, 9, 32),
            entry_price=100.0,
            exits=[],
            stop_level=None,
            profit_target=135.0,
        )

        # Should have entry marker + profit target line
        assert len(chart._marker_items) >= 2

    def test_set_markers_all_overlays(self, qtbot):
        """set_markers() with all overlay types."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        # Set data first
        df = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",
                "2024-01-15 09:34",
            ]),
            "open": [100.0, 103.0, 106.0],
            "high": [105.0, 108.0, 140.0],
            "low": [98.0, 101.0, 100.0],
            "close": [103.0, 106.0, 135.0],
        })
        chart.set_data(df)

        exits = [
            ExitEvent(
                time=datetime(2024, 1, 15, 9, 34),
                price=135.0,
                pct=50.0,
                reason="profit_target",
            ),
        ]

        chart.set_markers(
            entry_time=datetime(2024, 1, 15, 9, 32),
            entry_price=100.0,
            exits=exits,
            stop_level=95.0,
            profit_target=135.0,
        )

        # Should have: entry marker + exit marker + stop line + profit target line = 4+
        assert len(chart._marker_items) >= 4



class TestCandlestickChartGrid:
    """Tests for dynamic grid lines."""

    def test_price_plot_has_grid_enabled(self, qtbot):
        """Price plot should have both X and Y grid lines enabled."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        plot_item = chart._plot_widget
        # pyqtgraph stores grid state on the PlotItem's ctrl
        assert plot_item.ctrl.xGridCheck.isChecked()
        assert plot_item.ctrl.yGridCheck.isChecked()

    def test_volume_plot_has_grid_enabled(self, qtbot):
        """Volume plot should have both X and Y grid lines enabled."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        plot_item = chart._volume_plot
        assert plot_item.ctrl.xGridCheck.isChecked()
        assert plot_item.ctrl.yGridCheck.isChecked()


class TestCandlestickChartFindClosestBar:
    """Tests for CandlestickChart._find_closest_bar_idx() method."""

    def test_exact_match_returns_index(self, qtbot):
        """_find_closest_bar_idx returns exact match index."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        # Set data first
        df = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:30",
                "2024-01-15 09:31",
                "2024-01-15 09:32",
            ]),
            "open": [100.0, 101.0, 102.0],
            "high": [105.0, 106.0, 107.0],
            "low": [98.0, 99.0, 100.0],
            "close": [101.0, 102.0, 103.0],
        })
        chart.set_data(df)

        # Exact match at index 1
        target_time = datetime(2024, 1, 15, 9, 31)
        idx = chart._find_closest_bar_idx(target_time)
        assert idx == 1

    def test_closest_match_returns_nearest_index(self, qtbot):
        """_find_closest_bar_idx returns appropriate bar based on prefer_before."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        # Set data first
        df = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:30",
                "2024-01-15 09:31",
                "2024-01-15 09:32",
            ]),
            "open": [100.0, 101.0, 102.0],
            "high": [105.0, 106.0, 107.0],
            "low": [98.0, 99.0, 100.0],
            "close": [101.0, 102.0, 103.0],
        })
        chart.set_data(df)

        # Time between bars 0 and 1
        target_time = datetime(2024, 1, 15, 9, 30, 45)
        
        # Default (prefer_before=True) returns bar at/before target time
        idx = chart._find_closest_bar_idx(target_time, prefer_before=True)
        assert idx == 0  # Bar 0 is at 9:30, before 9:30:45
        
        # prefer_before=False returns bar at/after target time
        idx = chart._find_closest_bar_idx(target_time, prefer_before=False)
        assert idx == 1  # Bar 1 is at 9:31, after 9:30:45

        # Time between bars 1 and 2
        target_time = datetime(2024, 1, 15, 9, 31, 15)
        idx = chart._find_closest_bar_idx(target_time, prefer_before=True)
        assert idx == 1  # Bar 1 is at 9:31, before 9:31:15

    def test_empty_datetimes_returns_zero(self, qtbot):
        """_find_closest_bar_idx returns 0 when no data."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        target_time = datetime(2024, 1, 15, 9, 30)
        idx = chart._find_closest_bar_idx(target_time)
        assert idx == 0

    def test_time_before_first_bar_returns_first(self, qtbot):
        """_find_closest_bar_idx returns first bar for earlier time."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        df = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:30",
                "2024-01-15 09:31",
            ]),
            "open": [100.0, 101.0],
            "high": [105.0, 106.0],
            "low": [98.0, 99.0],
            "close": [101.0, 102.0],
        })
        chart.set_data(df)

        target_time = datetime(2024, 1, 15, 9, 25)
        idx = chart._find_closest_bar_idx(target_time)
        assert idx == 0

    def test_time_after_last_bar_returns_last(self, qtbot):
        """_find_closest_bar_idx returns last bar for later time."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        df = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:30",
                "2024-01-15 09:31",
            ]),
            "open": [100.0, 101.0],
            "high": [105.0, 106.0],
            "low": [98.0, 99.0],
            "close": [101.0, 102.0],
        })
        chart.set_data(df)

        target_time = datetime(2024, 1, 15, 9, 45)
        idx = chart._find_closest_bar_idx(target_time)
        assert idx == 1


class TestCandlestickChartClear:
    """Tests for CandlestickChart.clear() method."""

    def test_clear_removes_data(self, qtbot):
        """clear() removes candle data."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        df = pd.DataFrame({
            "datetime": pd.to_datetime(["2024-01-15 09:32"]),
            "open": [100.0],
            "high": [105.0],
            "low": [98.0],
            "close": [103.0],
        })
        chart.set_data(df)
        assert len(chart._candle_item._data) == 1

        chart.clear()
        assert chart._candle_item._data is None or len(chart._candle_item._data) == 0

    def test_clear_removes_markers(self, qtbot):
        """clear() removes all markers."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        df = pd.DataFrame({
            "datetime": pd.to_datetime(["2024-01-15 09:32"]),
            "open": [100.0],
            "high": [105.0],
            "low": [98.0],
            "close": [103.0],
        })
        chart.set_data(df)
        chart.set_markers(
            entry_time=datetime(2024, 1, 15, 9, 32),
            entry_price=100.0,
            exits=[],
            stop_level=95.0,
            profit_target=135.0,
        )
        assert len(chart._marker_items) > 0

        chart.clear()
        assert len(chart._marker_items) == 0


class TestCandlestickChartColors:
    """Tests for candlestick coloring."""

    def test_green_candle_when_close_above_open(self, qtbot):
        """Candles where close > open should be green/positive."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        # Close > Open = bullish/green candle
        df = pd.DataFrame({
            "datetime": pd.to_datetime(["2024-01-15 09:32"]),
            "open": [100.0],
            "high": [110.0],
            "low": [98.0],
            "close": [108.0],  # close > open
        })
        chart.set_data(df)

        # Verify candle item has data and can render
        assert chart._candle_item._data is not None
        assert len(chart._candle_item._data) == 1

    def test_red_candle_when_close_below_open(self, qtbot):
        """Candles where close < open should be red/negative."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        # Close < Open = bearish/red candle
        df = pd.DataFrame({
            "datetime": pd.to_datetime(["2024-01-15 09:32"]),
            "open": [108.0],
            "high": [110.0],
            "low": [98.0],
            "close": [100.0],  # close < open
        })
        chart.set_data(df)

        # Verify candle item has data and can render
        assert chart._candle_item._data is not None
        assert len(chart._candle_item._data) == 1


class TestCandlestickChartVWAP:
    """Tests for VWAP indicator."""

    def test_set_data_creates_vwap_line(self, qtbot):
        """set_data() creates VWAP line when volume data is present."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        df = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",
                "2024-01-15 09:34",
            ]),
            "open": [100.0, 103.0, 106.0],
            "high": [105.0, 108.0, 107.0],
            "low": [98.0, 101.0, 100.0],
            "close": [103.0, 106.0, 101.0],
            "volume": [1000, 1200, 800],
        })
        chart.set_data(df)

        # VWAP item should be created
        assert chart._vwap_item is not None

    def test_vwap_calculation_correct(self, qtbot):
        """VWAP calculation is mathematically correct."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        # Simple test case for VWAP calculation
        df = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",
            ]),
            "open": [100.0, 105.0],
            "high": [110.0, 115.0],
            "low": [90.0, 95.0],
            "close": [105.0, 110.0],
            "volume": [100, 200],
        })

        # Calculate expected VWAP
        # Bar 1: typical_price = (110 + 90 + 105) / 3 = 101.666...
        # Bar 2: typical_price = (115 + 95 + 110) / 3 = 106.666...
        # VWAP[0] = (101.666... * 100) / 100 = 101.666...
        # VWAP[1] = (101.666... * 100 + 106.666... * 200) / (100 + 200)
        #         = (10166.666... + 21333.333...) / 300 = 105.0

        tp1 = (110.0 + 90.0 + 105.0) / 3  # 101.666...
        tp2 = (115.0 + 95.0 + 110.0) / 3  # 106.666...
        expected_vwap_0 = tp1  # 101.666...
        expected_vwap_1 = (tp1 * 100 + tp2 * 200) / 300  # 105.0

        vwap = chart._calculate_vwap(df)

        assert len(vwap) == 2
        np.testing.assert_almost_equal(vwap[0], expected_vwap_0, decimal=5)
        np.testing.assert_almost_equal(vwap[1], expected_vwap_1, decimal=5)

    def test_clear_removes_vwap(self, qtbot):
        """clear() removes VWAP line."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        df = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",
            ]),
            "open": [100.0, 103.0],
            "high": [105.0, 108.0],
            "low": [98.0, 101.0],
            "close": [103.0, 106.0],
            "volume": [1000, 1200],
        })
        chart.set_data(df)

        # VWAP should be present
        assert chart._vwap_item is not None

        # Clear chart
        chart.clear()

        # VWAP should be removed
        assert chart._vwap_item is None

    def test_no_vwap_without_volume(self, qtbot):
        """VWAP is not created when volume column is missing."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        df = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",
            ]),
            "open": [100.0, 103.0],
            "high": [105.0, 108.0],
            "low": [98.0, 101.0],
            "close": [103.0, 106.0],
            # No volume column
        })
        chart.set_data(df)

        # VWAP should not be created
        assert chart._vwap_item is None

    def test_no_vwap_with_zero_volume(self, qtbot):
        """VWAP is not created when all volume is zero."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        df = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",
            ]),
            "open": [100.0, 103.0],
            "high": [105.0, 108.0],
            "low": [98.0, 101.0],
            "close": [103.0, 106.0],
            "volume": [0, 0],  # Zero volume
        })
        chart.set_data(df)

        # VWAP should not be created
        assert chart._vwap_item is None

    def test_set_data_replaces_vwap(self, qtbot):
        """set_data() replaces existing VWAP line with new data."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        df1 = pd.DataFrame({
            "datetime": pd.to_datetime(["2024-01-15 09:32"]),
            "open": [100.0],
            "high": [105.0],
            "low": [98.0],
            "close": [103.0],
            "volume": [1000],
        })
        chart.set_data(df1)

        first_vwap_item = chart._vwap_item
        assert first_vwap_item is not None

        # Set new data
        df2 = pd.DataFrame({
            "datetime": pd.to_datetime(["2024-01-15 10:00"]),
            "open": [200.0],
            "high": [210.0],
            "low": [195.0],
            "close": [205.0],
            "volume": [2000],
        })
        chart.set_data(df2)

        # VWAP should be a new item
        assert chart._vwap_item is not None
        assert chart._vwap_item is not first_vwap_item


class TestCandlestickChartInfoBox:
    """Tests for OHLCV info box overlay."""

    def test_info_text_item_exists(self, qtbot):
        """Chart should have a TextItem for OHLCV info overlay."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        assert hasattr(chart, "_info_text")
        assert isinstance(chart._info_text, pg.TextItem)

    def test_info_text_initially_empty(self, qtbot):
        """Info text should be empty before any mouse movement."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        assert chart._info_text.toPlainText() == ""

    def test_update_info_box_shows_ohlcv(self, qtbot):
        """_update_info_box with a valid bar index should display OHLCV."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        df = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",
            ]),
            "open": [100.0, 103.0],
            "high": [105.0, 108.0],
            "low": [98.0, 101.0],
            "close": [103.0, 106.0],
            "volume": [1000, 1200],
        })
        chart.set_data(df)

        chart._update_info_box(0)

        text = chart._info_text.toPlainText()
        assert "O 100" in text
        assert "H 105" in text
        assert "L 98" in text
        assert "C 103" in text
        assert "V 1000" in text or "V 1,000" in text

    def test_update_info_box_out_of_range(self, qtbot):
        """_update_info_box with out-of-range index should clear text."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        df = pd.DataFrame({
            "datetime": pd.to_datetime(["2024-01-15 09:32"]),
            "open": [100.0],
            "high": [105.0],
            "low": [98.0],
            "close": [103.0],
            "volume": [1000],
        })
        chart.set_data(df)

        chart._update_info_box(5)  # out of range

        assert chart._info_text.toPlainText() == ""

    def test_update_info_box_no_data(self, qtbot):
        """_update_info_box with no data loaded should not crash."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        chart._update_info_box(0)

        assert chart._info_text.toPlainText() == ""


class TestCandlestickChartRuler:
    """Tests for the ruler measurement tool."""

    def test_ruler_items_exist(self, qtbot):
        """Chart should have ruler line and label items."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        assert hasattr(chart, "_ruler_line")
        assert hasattr(chart, "_ruler_label")
        assert isinstance(chart._ruler_label, pg.TextItem)

    def test_ruler_initially_hidden(self, qtbot):
        """Ruler should be hidden initially."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        assert not chart._ruler_line.isVisible()
        assert not chart._ruler_label.isVisible()

    def test_format_ruler_label_positive(self, qtbot):
        """_format_ruler_label returns correct text for upward movement."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        text = chart._format_ruler_label(
            start_price=100.0,
            end_price=110.0,
            start_idx=0,
            end_idx=10,
        )
        assert "+10.00" in text
        assert "+10.00%" in text
        assert "10 bars" in text

    def test_format_ruler_label_negative(self, qtbot):
        """_format_ruler_label returns correct text for downward movement."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        text = chart._format_ruler_label(
            start_price=100.0,
            end_price=90.0,
            start_idx=0,
            end_idx=5,
        )
        assert "-10.00" in text
        assert "-10.00%" in text
        assert "5 bars" in text

    def test_format_ruler_label_zero_start(self, qtbot):
        """_format_ruler_label handles zero start price without crash."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        text = chart._format_ruler_label(
            start_price=0.0,
            end_price=10.0,
            start_idx=0,
            end_idx=1,
        )
        # Should not crash, percentage might be N/A or inf
        assert "10.00" in text


class TestCandlestickChartInteractiveFeatures:
    """Integration tests for grid + info box + ruler coexistence."""

    def test_all_features_coexist_after_set_data(self, qtbot):
        """All interactive features should work after loading data."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        df = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",
                "2024-01-15 09:34",
            ]),
            "open": [100.0, 103.0, 106.0],
            "high": [105.0, 108.0, 107.0],
            "low": [98.0, 101.0, 100.0],
            "close": [103.0, 106.0, 101.0],
            "volume": [1000, 1200, 800],
        })
        chart.set_data(df)

        # Grid is on
        assert chart._plot_widget.ctrl.yGridCheck.isChecked()

        # Info box updates
        chart._update_info_box(1)
        assert "O 103" in chart._info_text.toPlainText()

        # Ruler label formats
        text = chart._format_ruler_label(100.0, 110.0, 0, 5)
        assert "+10.00" in text

    def test_clear_resets_all_features(self, qtbot):
        """clear() should reset info box, crosshair, and ruler."""
        chart = CandlestickChart()
        qtbot.addWidget(chart)

        df = pd.DataFrame({
            "datetime": pd.to_datetime(["2024-01-15 09:32"]),
            "open": [100.0],
            "high": [105.0],
            "low": [98.0],
            "close": [103.0],
            "volume": [1000],
        })
        chart.set_data(df)
        chart._update_info_box(0)
        assert chart._info_text.toPlainText() != ""

        chart.clear()

        assert chart._info_text.toPlainText() == ""
        assert not chart._ruler_line.isVisible()
        assert not chart._crosshair_v.isVisible()
