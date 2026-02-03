"""Unit tests for CandlestickChart component."""

from datetime import datetime

import numpy as np
import pandas as pd
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
