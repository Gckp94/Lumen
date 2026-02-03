"""Candlestick chart component for trade visualization.

Provides a candlestick chart with OHLC data rendering and trade markers
for entry points, exit points, stop levels, and profit targets.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

import numpy as np
import pyqtgraph as pg  # type: ignore[import-untyped]
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QPainter, QPicture
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from src.ui.constants import Colors, Fonts

if TYPE_CHECKING:
    import pandas as pd
    from numpy.typing import NDArray

    from src.core.exit_simulator import ExitEvent

logger = logging.getLogger(__name__)


class CandlestickItem(pg.GraphicsObject):
    """Custom pyqtgraph item for rendering candlestick charts.

    Renders OHLC data as candlesticks with green (bullish) and red (bearish)
    colors based on close vs open price comparison.

    Attributes:
        _data: Numpy array with columns [time_idx, open, high, low, close].
        _picture: QPicture cache for efficient repainting.
    """

    def __init__(self) -> None:
        """Initialize the CandlestickItem."""
        super().__init__()
        self._data: NDArray[np.float64] | None = None
        self._picture: QPicture | None = None
        self._candle_width: float = 0.6

    def set_data(self, data: NDArray[np.float64] | None) -> None:
        """Set the candlestick data.

        Args:
            data: Numpy array with shape (n, 5) where columns are
                  [time_idx, open, high, low, close], or None to clear.
        """
        if data is None or len(data) == 0:
            self._data = np.array([]).reshape(0, 5) if data is None else data
            self._picture = None
            self.prepareGeometryChange()
            self.update()
            return

        self._data = np.asarray(data, dtype=np.float64)
        self._picture = None  # Invalidate cache
        self.prepareGeometryChange()
        self.update()

    def _generate_picture(self) -> None:
        """Generate the QPicture for rendering candlesticks."""
        self._picture = QPicture()
        painter = QPainter(self._picture)

        if self._data is None or len(self._data) == 0:
            painter.end()
            return

        # Colors from theme
        bullish_color = pg.mkColor(Colors.SIGNAL_CYAN)
        bearish_color = pg.mkColor(Colors.SIGNAL_CORAL)

        bullish_pen = pg.mkPen(color=bullish_color, width=1)
        bearish_pen = pg.mkPen(color=bearish_color, width=1)
        bullish_brush = pg.mkBrush(color=bullish_color)
        bearish_brush = pg.mkBrush(color=bearish_color)

        w = self._candle_width / 2

        for row in self._data:
            time_idx, open_price, high, low, close = row

            # Determine color based on close vs open
            if close >= open_price:
                painter.setPen(bullish_pen)
                painter.setBrush(bullish_brush)
            else:
                painter.setPen(bearish_pen)
                painter.setBrush(bearish_brush)

            # Draw wick (high-low line)
            painter.drawLine(
                pg.Point(time_idx, low),
                pg.Point(time_idx, high),
            )

            # Draw body (open-close rectangle)
            body_top = max(open_price, close)
            body_bottom = min(open_price, close)
            body_height = body_top - body_bottom

            # Minimum body height for visibility
            if body_height < 0.01:
                body_height = 0.01

            painter.drawRect(
                QRectF(
                    time_idx - w,
                    body_bottom,
                    self._candle_width,
                    body_height,
                )
            )

        painter.end()

    def paint(
        self,
        painter: QPainter,
        option: object,
        widget: QWidget | None = None,
    ) -> None:
        """Paint the candlesticks.

        Args:
            painter: The QPainter to use.
            option: Style options (unused).
            widget: The widget being painted on (unused).
        """
        if self._picture is None:
            self._generate_picture()

        if self._picture is not None:
            self._picture.play(painter)

    def boundingRect(self) -> QRectF:
        """Return the bounding rectangle for this item.

        Returns:
            QRectF containing all candlestick data.
        """
        if self._data is None or len(self._data) == 0:
            return QRectF()

        # Columns: time_idx, open, high, low, close
        time_idx = self._data[:, 0]
        high = self._data[:, 2]
        low = self._data[:, 3]

        x_min = time_idx.min() - self._candle_width
        x_max = time_idx.max() + self._candle_width
        y_min = low.min()
        y_max = high.max()

        # Add padding
        y_padding = (y_max - y_min) * 0.05 if y_max > y_min else 1.0

        return QRectF(
            x_min,
            y_min - y_padding,
            x_max - x_min,
            (y_max - y_min) + 2 * y_padding,
        )


class CandlestickChart(QWidget):
    """Candlestick chart widget for trade visualization.

    Displays OHLC price data as candlesticks with overlays for:
    - Entry point (blue marker)
    - Exit points (green markers)
    - Stop level (red dashed horizontal line)
    - Profit target (orange dashed horizontal line)
    - VWAP line (purple)

    Attributes:
        _plot_widget: The underlying PyQtGraph PlotWidget.
        _candle_item: The CandlestickItem for rendering candles.
        _marker_items: List of marker graphics items.
        _vwap_item: PlotDataItem for the VWAP line.
    """

    # VWAP line color (purple)
    VWAP_COLOR = "#BB86FC"

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the CandlestickChart.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._marker_items: list[pg.GraphicsObject] = []
        self._datetime_to_idx: dict[datetime, int] = {}
        self._vwap_item: pg.PlotDataItem | None = None

        self._setup_ui()
        self._setup_pyqtgraph()
        self._setup_candle_item()

    def _setup_ui(self) -> None:
        """Set up the widget layout."""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    def _setup_pyqtgraph(self) -> None:
        """Initialize PyQtGraph components with Observatory theme."""
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setBackground(Colors.BG_SURFACE)

        # Disable grid by default
        self._plot_widget.showGrid(x=False, y=False)

        # Configure axes with theme colors
        axis_pen = pg.mkPen(color=Colors.BG_BORDER)
        plot_item = self._plot_widget.getPlotItem()

        for axis_name in ("left", "bottom"):
            axis = plot_item.getAxis(axis_name)
            axis.setPen(axis_pen)
            axis.setTextPen(pg.mkPen(color=Colors.TEXT_SECONDARY))

        # Set axis labels
        plot_item.setLabel("left", "Price", **{
            "font-family": Fonts.DATA,
            "color": Colors.TEXT_SECONDARY,
        })
        plot_item.setLabel("bottom", "Bar #", **{
            "font-family": Fonts.DATA,
            "color": Colors.TEXT_SECONDARY,
        })

        # Disable right-click context menu
        self._plot_widget.getViewBox().setMenuEnabled(False)

        # Enable mouse interactions
        viewbox = self._plot_widget.getViewBox()
        viewbox.setMouseEnabled(x=True, y=True)
        viewbox.setMouseMode(pg.ViewBox.PanMode)

        self._layout.addWidget(self._plot_widget)

    def _setup_candle_item(self) -> None:
        """Set up the candlestick graphics item."""
        self._candle_item = CandlestickItem()
        self._plot_widget.addItem(self._candle_item)

    @staticmethod
    def _calculate_vwap(df: pd.DataFrame) -> NDArray[np.float64]:
        """Calculate Volume Weighted Average Price (VWAP).

        VWAP = cumsum(typical_price * volume) / cumsum(volume)
        where typical_price = (high + low + close) / 3

        Args:
            df: DataFrame with high, low, close, and volume columns.

        Returns:
            Numpy array of VWAP values for each bar.
        """
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        volume = df["volume"].to_numpy()

        typical_price = (high + low + close) / 3
        cumulative_tp_volume = np.cumsum(typical_price * volume)
        cumulative_volume = np.cumsum(volume)

        # Avoid division by zero
        with np.errstate(divide="ignore", invalid="ignore"):
            vwap = cumulative_tp_volume / cumulative_volume
            # Replace any inf/nan with 0
            vwap = np.nan_to_num(vwap, nan=0.0, posinf=0.0, neginf=0.0)

        return vwap

    def set_data(self, df: pd.DataFrame | None) -> None:
        """Set the OHLCV bar data for the chart.

        Args:
            df: DataFrame with columns datetime, open, high, low, close.
                Optional volume column for VWAP calculation.
        """
        # Remove existing VWAP line if present
        if self._vwap_item is not None:
            self._plot_widget.removeItem(self._vwap_item)
            self._vwap_item = None

        if df is None or df.empty:
            self._candle_item.set_data(None)
            self._datetime_to_idx.clear()
            logger.debug("CandlestickChart cleared")
            return

        try:
            # Build datetime to index mapping
            self._datetime_to_idx.clear()
            datetimes = df["datetime"].tolist()
            for idx, dt in enumerate(datetimes):
                if hasattr(dt, "to_pydatetime"):
                    dt = dt.to_pydatetime()
                self._datetime_to_idx[dt] = idx

            # Extract OHLC data as numpy array
            # Format: [time_idx, open, high, low, close]
            n = len(df)
            data = np.zeros((n, 5), dtype=np.float64)
            data[:, 0] = np.arange(n)  # time index
            data[:, 1] = df["open"].to_numpy()
            data[:, 2] = df["high"].to_numpy()
            data[:, 3] = df["low"].to_numpy()
            data[:, 4] = df["close"].to_numpy()

            self._candle_item.set_data(data)

            # Calculate and plot VWAP if volume data is available
            if "volume" in df.columns and df["volume"].sum() > 0:
                vwap = self._calculate_vwap(df)
                x_indices = np.arange(n)
                self._vwap_item = self._plot_widget.plot(
                    x_indices,
                    vwap,
                    pen=pg.mkPen(color=self.VWAP_COLOR, width=2),
                    name="VWAP",
                )

            self._plot_widget.autoRange()

            logger.debug("CandlestickChart updated: %d bars", n)

        except Exception as e:
            logger.error("Failed to set candlestick data: %s", e)
            self._candle_item.set_data(None)

    def set_markers(
        self,
        entry_time: datetime,
        entry_price: float,
        exits: list[ExitEvent],
        stop_level: float | None,
        profit_target: float | None,
    ) -> None:
        """Add trade markers to the chart.

        Args:
            entry_time: Entry timestamp.
            entry_price: Entry price level.
            exits: List of ExitEvent objects.
            stop_level: Stop loss price level (red dashed line).
            profit_target: Profit target price level (orange dashed line).
        """
        # Clear existing markers
        self._clear_markers()

        # Get time index for entry
        entry_idx = self._datetime_to_idx.get(entry_time, 0)

        # Entry marker (blue)
        entry_marker = pg.ScatterPlotItem(
            pos=[(entry_idx, entry_price)],
            size=12,
            pen=pg.mkPen(color=Colors.SIGNAL_BLUE, width=2),
            brush=pg.mkBrush(color=Colors.SIGNAL_BLUE),
            symbol="o",
        )
        self._plot_widget.addItem(entry_marker)
        self._marker_items.append(entry_marker)

        # Exit markers (green)
        for exit_event in exits:
            exit_idx = self._datetime_to_idx.get(exit_event.time, 0)
            exit_marker = pg.ScatterPlotItem(
                pos=[(exit_idx, exit_event.price)],
                size=12,
                pen=pg.mkPen(color=Colors.SIGNAL_CYAN, width=2),
                brush=pg.mkBrush(color=Colors.SIGNAL_CYAN),
                symbol="x",
            )
            self._plot_widget.addItem(exit_marker)
            self._marker_items.append(exit_marker)

        # Stop level (red dashed horizontal line)
        if stop_level is not None:
            stop_line = pg.InfiniteLine(
                pos=stop_level,
                angle=0,
                pen=pg.mkPen(
                    color=Colors.SIGNAL_CORAL,
                    style=Qt.PenStyle.DashLine,
                    width=1,
                ),
            )
            self._plot_widget.addItem(stop_line)
            self._marker_items.append(stop_line)

        # Profit target (orange dashed horizontal line)
        if profit_target is not None:
            target_line = pg.InfiniteLine(
                pos=profit_target,
                angle=0,
                pen=pg.mkPen(
                    color=Colors.SIGNAL_AMBER,
                    style=Qt.PenStyle.DashLine,
                    width=1,
                ),
            )
            self._plot_widget.addItem(target_line)
            self._marker_items.append(target_line)

        logger.debug(
            "CandlestickChart markers set: entry=%s, exits=%d, stop=%s, target=%s",
            entry_price,
            len(exits),
            stop_level,
            profit_target,
        )

    def _clear_markers(self) -> None:
        """Remove all marker items from the plot."""
        for item in self._marker_items:
            self._plot_widget.removeItem(item)
        self._marker_items.clear()

    def clear(self) -> None:
        """Clear all data and markers from the chart."""
        self._candle_item.set_data(None)
        self._clear_markers()
        self._datetime_to_idx.clear()

        # Remove VWAP line
        if self._vwap_item is not None:
            self._plot_widget.removeItem(self._vwap_item)
            self._vwap_item = None

        logger.debug("CandlestickChart cleared")

    def auto_range(self) -> None:
        """Reset view to auto-fit all data."""
        self._plot_widget.autoRange()
