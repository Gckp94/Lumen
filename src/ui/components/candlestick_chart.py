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
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QFont, QPainter, QPicture
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from src.ui.constants import Colors, Fonts

if TYPE_CHECKING:
    import pandas as pd
    from numpy.typing import NDArray

    from src.core.exit_simulator import ExitEvent

logger = logging.getLogger(__name__)


class TimeAxisItem(pg.AxisItem):
    """Custom axis that displays time strings instead of bar indices."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._datetimes: list[datetime] = []

    def set_datetimes(self, datetimes: list[datetime]) -> None:
        """Set the datetime values for the axis."""
        self._datetimes = datetimes

    def tickStrings(self, values, scale, spacing):
        """Convert bar indices to time strings."""
        strings = []
        for v in values:
            idx = int(round(v))
            if 0 <= idx < len(self._datetimes):
                dt = self._datetimes[idx]
                # Format as HH:MM (ET time)
                strings.append(dt.strftime("%H:%M"))
            else:
                strings.append("")
        return strings


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
        self._paint_logged: bool = False
        
        # Candle colors matching volume bars (green up, red down)
        self._bullish_color = (76, 175, 80)  # Green
        self._bearish_color = (244, 67, 54)  # Red

    def set_data(self, data: NDArray[np.float64] | None) -> None:
        """Set the candlestick data.

        Args:
            data: Numpy array with shape (n, 5) where columns are
                  [time_idx, open, high, low, close], or None to clear.
        """
        # Reset paint logging flag for fresh debug on new data
        self._paint_logged = False
        
        if data is None or len(data) == 0:
            self._data = np.array([]).reshape(0, 5) if data is None else data
            self._picture = None
            self.prepareGeometryChange()
            self.update()
            return

        self._data = np.asarray(data, dtype=np.float64)

        n_bars = len(self._data)
        
        # Dynamically adjust candle width based on number of bars
        if n_bars <= 30:
            self._candle_width = 0.8
        elif n_bars <= 100:
            self._candle_width = 0.6
        elif n_bars <= 200:
            self._candle_width = 0.4
        else:
            self._candle_width = 0.25

        logger.info("CandlestickItem: %d bars, candle_width=%.2f", n_bars, self._candle_width)
        
        # Log FIRST 5 bars to compare with chart_viewer logs
        if n_bars >= 5:
            logger.info("CandlestickItem FIRST 5 bars (should match chart_viewer):")
            for i in range(5):
                idx, o, h, l, c = self._data[i]
                bar_range = h - l
                logger.info("  [%d] idx=%.0f O=%.4f H=%.4f L=%.4f C=%.4f range=%.4f",
                           i, idx, o, h, l, c, bar_range)

        self._picture = None
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

        for i, row in enumerate(self._data):
            time_idx, open_price, high, low, close = row

            if i < 3:
                logger.info(
                    "_generate_picture bar[%d]: idx=%.0f O=%.4f H=%.4f L=%.4f C=%.4f",
                    i, time_idx, open_price, high, low, close
                )

            # Skip bars with NaN or infinite values
            if not np.isfinite(open_price) or not np.isfinite(close):
                continue
            if not np.isfinite(high) or not np.isfinite(low):
                continue

            # Determine color based on close vs open
            if close >= open_price:
                painter.setPen(bullish_pen)
                painter.setBrush(bullish_brush)
            else:
                painter.setPen(bearish_pen)
                painter.setBrush(bearish_brush)

            # Draw wick (high-low line) using QPointF instead of pg.Point
            painter.drawLine(
                QPointF(time_idx, low),
                QPointF(time_idx, high),
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
        if self._data is None or len(self._data) == 0:
            return

        # Log data on first paint call for debugging
        if not hasattr(self, '_paint_logged') or not self._paint_logged:
            self._paint_logged = True
            n_bars = len(self._data)
            logger.info("paint() called with %d bars", n_bars)
            if n_bars >= 3:
                logger.info("paint() FIRST 3 bars data:")
                for i in range(min(3, n_bars)):
                    idx, o, h, l, c = self._data[i]
                    logger.info("  paint[%d] idx=%.0f O=%.4f H=%.4f L=%.4f C=%.4f", i, idx, o, h, l, c)
            # Log transform
            transform = painter.transform()
            logger.info("paint() transform: m11=%.4f m22=%.4f dx=%.1f dy=%.1f",
                       transform.m11(), transform.m22(), transform.dx(), transform.dy())

        # Colors matching volume bars (green up, red down)
        bullish_color = pg.mkColor(*self._bullish_color)
        bearish_color = pg.mkColor(*self._bearish_color)

        bullish_pen = pg.mkPen(color=bullish_color, width=1)
        bearish_pen = pg.mkPen(color=bearish_color, width=1)
        bullish_brush = pg.mkBrush(color=bullish_color)
        bearish_brush = pg.mkBrush(color=bearish_color)

        w = self._candle_width / 2

        for row in self._data:
            time_idx, open_price, high, low, close = row

            # Skip bars with NaN or infinite values
            if not np.isfinite(open_price) or not np.isfinite(close):
                continue
            if not np.isfinite(high) or not np.isfinite(low):
                continue

            # Determine color based on close vs open
            if close >= open_price:
                painter.setPen(bullish_pen)
                painter.setBrush(bullish_brush)
            else:
                painter.setPen(bearish_pen)
                painter.setBrush(bearish_brush)

            # Draw wick (high-low line)
            painter.drawLine(QPointF(time_idx, low), QPointF(time_idx, high))

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

        rect = QRectF(
            x_min,
            y_min - y_padding,
            x_max - x_min,
            (y_max - y_min) + 2 * y_padding,
        )
        
        # Log bounding rect for debugging
        logger.debug("boundingRect: x=[%.2f, %.2f] y=[%.4f, %.4f] price_range=[%.4f, %.4f]",
                    x_min, x_max, y_min - y_padding, y_min - y_padding + rect.height(),
                    y_min, y_max)
        
        return rect


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
    
    # Session background colors (TradingView style)
    # Pre-market: light green tint
    PRE_MARKET_COLOR = (144, 238, 144, 40)  # Light green with low alpha
    # Post-market: light blue/lavender tint  
    POST_MARKET_COLOR = (173, 216, 230, 40)  # Light blue with low alpha

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the CandlestickChart.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._marker_items: list[pg.GraphicsObject] = []
        self._session_regions: list[pg.LinearRegionItem] = []
        self._datetime_to_idx: dict[datetime, int] = {}
        self._datetimes: list[datetime] = []  # Ordered list for axis and lookup
        self._vwap_item: pg.PlotDataItem | None = None
        self._time_axis: TimeAxisItem | None = None
        self._volume_bars: pg.BarGraphItem | None = None
        self._volume_plot: pg.PlotItem | None = None
        self._ohlcv_df: pd.DataFrame | None = None

        # Ruler measurement state
        self._ruler_active: bool = False
        self._ruler_start: tuple[float, float] | None = None  # (x, y) in plot coords

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
        # Create a GraphicsLayoutWidget to hold multiple plots
        self._graphics_layout = pg.GraphicsLayoutWidget()
        self._graphics_layout.setBackground(Colors.BG_SURFACE)

        # Create custom time axis for bottom of volume plot (shared X axis display)
        self._time_axis = TimeAxisItem(orientation="bottom")

        # Create main candlestick plot (top, 75% of height)
        self._plot_widget = self._graphics_layout.addPlot(row=0, col=0)
        self._plot_widget.showGrid(x=True, y=True, alpha=0.15)

        # Create volume plot (bottom, 25% of height)
        self._volume_plot = self._graphics_layout.addPlot(row=1, col=0, axisItems={"bottom": self._time_axis})
        self._volume_plot.showGrid(x=True, y=True, alpha=0.15)

        # Set relative heights (3:1 ratio for price:volume)
        self._graphics_layout.ci.layout.setRowStretchFactor(0, 3)
        self._graphics_layout.ci.layout.setRowStretchFactor(1, 1)

        # Link X axes so they scroll together
        self._volume_plot.setXLink(self._plot_widget)

        # Hide X axis on main plot (time axis only on volume plot)
        self._plot_widget.hideAxis("bottom")

        # Configure axes with theme colors
        axis_pen = pg.mkPen(color=Colors.BG_BORDER)

        # Main plot axes
        for axis_name in ("left",):
            axis = self._plot_widget.getAxis(axis_name)
            axis.setPen(axis_pen)
            axis.setTextPen(pg.mkPen(color=Colors.TEXT_SECONDARY))

        self._plot_widget.setLabel("left", "Price", **{
            "font-family": Fonts.DATA,
            "color": Colors.TEXT_SECONDARY,
        })

        # Volume plot axes
        for axis_name in ("left", "bottom"):
            axis = self._volume_plot.getAxis(axis_name)
            axis.setPen(axis_pen)
            axis.setTextPen(pg.mkPen(color=Colors.TEXT_SECONDARY))

        self._volume_plot.setLabel("left", "Vol", **{
            "font-family": Fonts.DATA,
            "color": Colors.TEXT_SECONDARY,
        })
        self._volume_plot.setLabel("bottom", "Time (ET)", **{
            "font-family": Fonts.DATA,
            "color": Colors.TEXT_SECONDARY,
        })

        # Disable right-click context menu on both plots
        self._plot_widget.getViewBox().setMenuEnabled(False)
        self._volume_plot.getViewBox().setMenuEnabled(False)

        # Enable mouse interactions on main plot
        viewbox = self._plot_widget.getViewBox()
        viewbox.setMouseEnabled(x=True, y=True)
        viewbox.setMouseMode(pg.ViewBox.PanMode)

        # Enable mouse interactions on volume plot (X linked, Y independent)
        vol_viewbox = self._volume_plot.getViewBox()
        vol_viewbox.setMouseEnabled(x=True, y=True)
        vol_viewbox.setMouseMode(pg.ViewBox.PanMode)

        # OHLCV info box overlay (top-left of price plot)
        self._info_text = pg.TextItem(
            text="",
            color=Colors.TEXT_PRIMARY,
            anchor=(0, 0),
        )
        self._info_text.setFont(QFont(Fonts.DATA, 9))
        self._info_text.setZValue(1000)  # Always on top
        self._plot_widget.addItem(self._info_text, ignoreBounds=True)

        # Crosshair lines (vertical + horizontal)
        self._crosshair_v = pg.InfiniteLine(
            angle=90,
            pen=pg.mkPen(
                Colors.TEXT_DISABLED, width=1, style=Qt.PenStyle.DashLine
            ),
        )
        self._crosshair_h = pg.InfiniteLine(
            angle=0,
            pen=pg.mkPen(
                Colors.TEXT_DISABLED, width=1, style=Qt.PenStyle.DashLine
            ),
        )
        self._crosshair_v.setVisible(False)
        self._crosshair_h.setVisible(False)
        self._plot_widget.addItem(self._crosshair_v, ignoreBounds=True)
        self._plot_widget.addItem(self._crosshair_h, ignoreBounds=True)

        # Floating price label on Y-axis (follows horizontal crosshair)
        self._price_label = pg.TextItem(
            text="",
            color=Colors.TEXT_PRIMARY,
            anchor=(1, 0.5),  # Right-center anchor (positions on right edge of plot)
            fill=pg.mkBrush(Colors.BG_ELEVATED + "EE"),
            border=pg.mkPen(Colors.BG_BORDER),
        )
        self._price_label.setFont(QFont(Fonts.DATA, 9))
        self._price_label.setZValue(1002)  # Above other overlays
        self._price_label.setVisible(False)
        self._plot_widget.addItem(self._price_label, ignoreBounds=True)

        # Floating time label on X-axis (follows vertical crosshair)
        self._time_label = pg.TextItem(
            text="",
            color=Colors.TEXT_PRIMARY,
            anchor=(0.5, 0),  # Top-center anchor (positions at bottom of plot)
            fill=pg.mkBrush(Colors.BG_ELEVATED + "EE"),
            border=pg.mkPen(Colors.BG_BORDER),
        )
        self._time_label.setFont(QFont(Fonts.DATA, 9))
        self._time_label.setZValue(1002)
        self._time_label.setVisible(False)
        self._plot_widget.addItem(self._time_label, ignoreBounds=True)

        # Connect mouse move signal
        self._mouse_proxy = pg.SignalProxy(
            self._plot_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._on_mouse_moved,
        )

        # Connect mouse click for ruler tool
        self._plot_widget.scene().sigMouseClicked.connect(
            self._on_mouse_clicked
        )

        # Ruler measurement tool (Shift+click to measure)
        self._ruler_line = pg.PlotDataItem(
            pen=pg.mkPen(
                Colors.SIGNAL_AMBER,
                width=2,
                style=Qt.PenStyle.DashDotLine,
            ),
        )
        self._ruler_line.setVisible(False)
        self._plot_widget.addItem(self._ruler_line, ignoreBounds=True)

        self._ruler_label = pg.TextItem(
            text="",
            color=Colors.SIGNAL_AMBER,
            anchor=(0.5, 1),
            fill=pg.mkBrush(Colors.BG_ELEVATED + "CC"),
        )
        self._ruler_label.setFont(QFont(Fonts.DATA, 10))
        self._ruler_label.setZValue(1001)
        self._ruler_label.setVisible(False)
        self._plot_widget.addItem(self._ruler_label, ignoreBounds=True)

        self._layout.addWidget(self._graphics_layout)

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
                Optional session column for pre/post market highlighting.
        """
        # Remove existing VWAP line if present
        if self._vwap_item is not None:
            self._plot_widget.removeItem(self._vwap_item)
            self._vwap_item = None
        
        # Remove existing volume bars if present
        if self._volume_bars is not None and self._volume_plot is not None:
            self._volume_plot.removeItem(self._volume_bars)
            self._volume_bars = None
        
        # Remove existing session regions
        self._clear_session_regions()

        if df is None or df.empty:
            self._candle_item.set_data(None)
            self._datetime_to_idx.clear()
            self._datetimes.clear()
            self._ohlcv_df = None
            if self._time_axis is not None:
                self._time_axis.set_datetimes([])
            logger.debug("CandlestickChart cleared")
            return

        try:
            # Check for duplicate timestamps
            if "datetime" in df.columns:
                dup_count = df["datetime"].duplicated().sum()
                if dup_count > 0:
                    logger.warning("Found %d duplicate timestamps - removing", dup_count)
                    df = df.drop_duplicates(subset=["datetime"], keep="first").reset_index(drop=True)

            # Build datetime to index mapping and ordered list
            self._datetime_to_idx.clear()
            self._datetimes = []
            for idx, dt in enumerate(df["datetime"].tolist()):
                if hasattr(dt, "to_pydatetime"):
                    dt = dt.to_pydatetime()
                self._datetime_to_idx[dt] = idx
                self._datetimes.append(dt)

            # Update time axis with datetimes
            if self._time_axis is not None:
                self._time_axis.set_datetimes(self._datetimes)

            # Extract OHLC data as numpy array
            # Format: [time_idx, open, high, low, close]
            n = len(df)
            data = np.zeros((n, 5), dtype=np.float64)
            data[:, 0] = np.arange(n)  # time index
            data[:, 1] = df["open"].to_numpy()
            data[:, 2] = df["high"].to_numpy()
            data[:, 3] = df["low"].to_numpy()
            data[:, 4] = df["close"].to_numpy()

            logger.info("CandlestickChart: %d bars", n)
            
            # Debug: Log first 3 bars of the numpy array before passing to CandlestickItem
            if n >= 3:
                logger.info("CandlestickChart numpy array FIRST 3 bars:")
                for i in range(3):
                    logger.info("  numpy[%d] idx=%.0f O=%.4f H=%.4f L=%.4f C=%.4f",
                               i, data[i, 0], data[i, 1], data[i, 2], data[i, 3], data[i, 4])

            self._candle_item.set_data(data)
            self._ohlcv_df = df

            # Draw session background regions if session column exists
            if "session" in df.columns:
                self._draw_session_regions(df)

            # Plot volume bars if volume data is available
            if "volume" in df.columns and self._volume_plot is not None:
                volumes = df["volume"].to_numpy()
                opens = df["open"].to_numpy()
                closes = df["close"].to_numpy()
                
                # Color bars based on price direction (green for up, red for down)
                colors = []
                for i in range(n):
                    if closes[i] >= opens[i]:
                        colors.append((76, 175, 80, 180))  # Green with alpha
                    else:
                        colors.append((244, 67, 54, 180))  # Red with alpha
                
                self._volume_bars = pg.BarGraphItem(
                    x=np.arange(n),
                    height=volumes,
                    width=0.8,
                    brushes=[pg.mkBrush(c) for c in colors],
                    pens=[pg.mkPen(None) for _ in range(n)],
                )
                self._volume_plot.addItem(self._volume_bars)

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
                # Log VWAP values for debugging
                if n >= 3:
                    logger.info("VWAP first 3 values: %.4f, %.4f, %.4f", vwap[0], vwap[1], vwap[2])

            self._plot_widget.autoRange()
            if self._volume_plot is not None:
                self._volume_plot.autoRange()

        except Exception as e:
            logger.error("Failed to set candlestick data: %s", e)
            self._candle_item.set_data(None)

    def _clear_session_regions(self) -> None:
        """Remove all session background region items from the plot."""
        for region in self._session_regions:
            self._plot_widget.removeItem(region)
        self._session_regions.clear()

    def _draw_session_regions(self, df: pd.DataFrame) -> None:
        """Draw background regions for pre-market and post-market sessions.

        Args:
            df: DataFrame with 'session' column containing 'pre', 'regular', or 'post'.
        """
        if "session" not in df.columns:
            return

        n = len(df)
        sessions = df["session"].tolist()
        
        # Find contiguous regions for pre and post market
        i = 0
        while i < n:
            session_type = sessions[i]
            if session_type in ("pre", "post"):
                # Find end of this session region
                start_idx = i
                while i < n and sessions[i] == session_type:
                    i += 1
                end_idx = i - 1
                
                # Determine color based on session type
                if session_type == "pre":
                    color = self.PRE_MARKET_COLOR
                else:
                    color = self.POST_MARKET_COLOR
                
                # Create LinearRegionItem for candlestick plot
                # Extend slightly beyond bar edges for visual coverage
                region = pg.LinearRegionItem(
                    values=[start_idx - 0.5, end_idx + 0.5],
                    orientation="vertical",
                    brush=pg.mkBrush(color),
                    pen=pg.mkPen(None),  # No border
                    movable=False,
                )
                # Set Z-value to be behind candles
                region.setZValue(-100)
                
                self._plot_widget.addItem(region)
                self._session_regions.append(region)
                
                # Also add region to volume plot if available
                if self._volume_plot is not None:
                    vol_region = pg.LinearRegionItem(
                        values=[start_idx - 0.5, end_idx + 0.5],
                        orientation="vertical",
                        brush=pg.mkBrush(color),
                        pen=pg.mkPen(None),
                        movable=False,
                    )
                    vol_region.setZValue(-100)
                    self._volume_plot.addItem(vol_region)
                    self._session_regions.append(vol_region)
                
                logger.debug("Drew %s-market region: indices %d-%d", session_type, start_idx, end_idx)
            else:
                i += 1

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

        # Get bar index for entry - prefer bar BEFORE entry time
        # (entry happens during/after that bar opens)
        entry_pos = self._find_closest_bar_idx(entry_time, prefer_before=True)
        
        logger.info("set_markers: entry_time=%s, entry_price=%.4f, entry_pos=%.2f", 
                   entry_time, entry_price, entry_pos)
        logger.info("set_markers: total bars=%d, total datetimes=%d", 
                   len(self._candle_item._data) if self._candle_item._data is not None else 0,
                   len(self._datetimes))

        # Entry marker (blue)
        entry_marker = pg.ScatterPlotItem(
            pos=[(entry_pos, entry_price)],
            size=12,
            pen=pg.mkPen(color=Colors.SIGNAL_BLUE, width=2),
            brush=pg.mkBrush(color=Colors.SIGNAL_BLUE),
            symbol="o",
        )
        self._plot_widget.addItem(entry_marker)
        self._marker_items.append(entry_marker)

        # Exit markers (cyan) - prefer bar AT or AFTER exit time
        for i, exit_event in enumerate(exits):
            exit_pos = self._find_closest_bar_idx(exit_event.time, prefer_before=False)
            logger.info("set_markers: exit[%d] time=%s, price=%.4f, pos=%.2f, reason=%s",
                       i, exit_event.time, exit_event.price, exit_pos, exit_event.reason)
            exit_marker = pg.ScatterPlotItem(
                pos=[(exit_pos, exit_event.price)],
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

    def _find_closest_bar_idx(self, target_time: datetime, prefer_before: bool = True) -> float:
        """Find the bar index for the target time.

        Args:
            target_time: The datetime to find the position for.
            prefer_before: If True, prefer the bar before target_time when no exact match.
                          If False, prefer the bar at or after target_time.

        Returns:
            Float index representing the X position for this time.
        """
        # Convert target_time to Python datetime if needed
        if hasattr(target_time, "to_pydatetime"):
            target_time = target_time.to_pydatetime()
        
        # Try exact match first
        if target_time in self._datetime_to_idx:
            idx = self._datetime_to_idx[target_time]
            logger.info("Exact match for %s -> index %d", target_time, idx)
            return float(idx)

        # No datetimes available
        if not self._datetimes:
            logger.warning("No datetimes available for finding closest bar")
            return 0.0

        # Find bars before and after target time
        bar_before_idx = None
        bar_before_time = None
        bar_after_idx = None
        bar_after_time = None
        
        for idx, bar_time in enumerate(self._datetimes):
            # Convert bar_time to Python datetime if needed
            if hasattr(bar_time, "to_pydatetime"):
                bar_time_py = bar_time.to_pydatetime()
            else:
                bar_time_py = bar_time
                
            if bar_time_py <= target_time:
                bar_before_idx = idx
                bar_before_time = bar_time_py
            elif bar_after_idx is None:
                bar_after_idx = idx
                bar_after_time = bar_time_py
                break  # Found first bar after, no need to continue

        # Choose based on preference
        if prefer_before and bar_before_idx is not None:
            logger.info(
                "Entry bar for %s: index %d at %s (bar before/at entry)",
                target_time, bar_before_idx, bar_before_time
            )
            return float(bar_before_idx)
        elif not prefer_before and bar_after_idx is not None:
            logger.info(
                "Exit bar for %s: index %d at %s (bar at/after exit)",
                target_time, bar_after_idx, bar_after_time
            )
            return float(bar_after_idx)
        elif bar_before_idx is not None:
            logger.info(
                "Fallback to bar before for %s: index %d at %s",
                target_time, bar_before_idx, bar_before_time
            )
            return float(bar_before_idx)
        elif bar_after_idx is not None:
            logger.info(
                "Fallback to bar after for %s: index %d at %s",
                target_time, bar_after_idx, bar_after_time
            )
            return float(bar_after_idx)
        
        return 0.0

    def _on_mouse_clicked(self, evt) -> None:
        """Handle mouse clicks for ruler measurement (Shift+click).

        Args:
            evt: pyqtgraph MouseClickEvent.
        """
        if evt.button() != Qt.MouseButton.LeftButton:
            return
        if not (evt.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            return

        pos = evt.scenePos()
        if not self._plot_widget.sceneBoundingRect().contains(pos):
            return

        mouse_point = self._plot_widget.getViewBox().mapSceneToView(pos)

        if not self._ruler_active:
            # Start ruler
            self._ruler_active = True
            self._ruler_start = (mouse_point.x(), mouse_point.y())
            self._ruler_line.setData(
                [mouse_point.x(), mouse_point.x()],
                [mouse_point.y(), mouse_point.y()],
            )
            self._ruler_line.setVisible(True)
            self._ruler_label.setVisible(True)
            evt.accept()
        else:
            # End ruler -- clear it
            self._ruler_active = False
            self._ruler_start = None
            self._ruler_line.setVisible(False)
            self._ruler_label.setVisible(False)
            self._ruler_label.setText("")
            evt.accept()

    def _on_mouse_moved(self, evt: tuple) -> None:
        """Handle mouse movement over the price plot to update info box and crosshair.

        Args:
            evt: Tuple containing the mouse position (QPointF).
        """
        pos = evt[0]
        if not self._plot_widget.sceneBoundingRect().contains(pos):
            self._crosshair_v.setVisible(False)
            self._crosshair_h.setVisible(False)
            return

        mouse_point = self._plot_widget.getViewBox().mapSceneToView(pos)
        bar_idx = int(round(mouse_point.x()))

        # Update crosshair position
        self._crosshair_v.setPos(mouse_point.x())
        self._crosshair_h.setPos(mouse_point.y())
        self._crosshair_v.setVisible(True)
        self._crosshair_h.setVisible(True)

        self._update_info_box(bar_idx)

        # Update floating crosshair labels
        self._update_crosshair_labels(bar_idx, mouse_point.y())

        # Update ruler if active
        if self._ruler_active and self._ruler_start is not None:
            sx, sy = self._ruler_start
            ex, ey = mouse_point.x(), mouse_point.y()
            self._ruler_line.setData([sx, ex], [sy, ey])
            label_text = self._format_ruler_label(
                sy, ey, int(round(sx)), int(round(ex))
            )
            self._ruler_label.setText(label_text)
            self._ruler_label.setPos((sx + ex) / 2, (sy + ey) / 2)

    def _update_info_box(self, bar_idx: int) -> None:
        """Update the OHLCV info text for the given bar index.

        Args:
            bar_idx: Integer index of the bar to display info for.
        """
        if (
            self._candle_item._data is None
            or len(self._candle_item._data) == 0
            or bar_idx < 0
            or bar_idx >= len(self._candle_item._data)
        ):
            self._info_text.setText("")
            return

        row = self._candle_item._data[bar_idx]
        _, o, h, l, c = row

        # Get time string
        time_str = ""
        if 0 <= bar_idx < len(self._datetimes):
            time_str = self._datetimes[bar_idx].strftime("%Y-%m-%d %H:%M")

        # Get volume if available
        vol_str = ""
        if self._ohlcv_df is not None and "volume" in self._ohlcv_df.columns:
            if 0 <= bar_idx < len(self._ohlcv_df):
                vol = self._ohlcv_df.iloc[bar_idx]["volume"]
                vol_str = f"  V {vol:,.0f}"

        self._info_text.setText(
            f"{time_str}  O {o:.2f}  H {h:.2f}  L {l:.2f}  C {c:.2f}{vol_str}"
        )

        # Anchor text to top-left of visible area
        view_range = self._plot_widget.viewRange()
        self._info_text.setPos(view_range[0][0], view_range[1][1])

    def _update_crosshair_labels(self, bar_idx: int, price: float) -> None:
        """Update the floating crosshair price and time labels.

        Args:
            bar_idx: Integer index of the bar at cursor X position.
            price: Y coordinate (price level) at cursor position.
        """
        view_range = self._plot_widget.viewRange()
        x_min, x_max = view_range[0]
        y_min, y_max = view_range[1]

        # Update price label - position on right edge at crosshair Y
        self._price_label.setText(f" {price:.2f} ")
        self._price_label.setPos(x_max, price)
        self._price_label.setVisible(True)

        # Update time label - position at bottom at crosshair X
        if 0 <= bar_idx < len(self._datetimes):
            time_str = self._datetimes[bar_idx].strftime("%H:%M")
            self._time_label.setText(f" {time_str} ")
            self._time_label.setPos(float(bar_idx), y_min)
            self._time_label.setVisible(True)
        else:
            self._time_label.setVisible(False)

    def _format_ruler_label(
        self,
        start_price: float,
        end_price: float,
        start_idx: int,
        end_idx: int,
    ) -> str:
        """Format the ruler measurement label text.

        Args:
            start_price: Price at ruler start.
            end_price: Price at ruler end.
            start_idx: Bar index at ruler start.
            end_idx: Bar index at ruler end.

        Returns:
            Formatted string with price delta, percentage, and bar count.
        """
        delta = end_price - start_price
        sign = "+" if delta >= 0 else ""
        bars = abs(end_idx - start_idx)

        if abs(start_price) > 1e-9:
            pct = (delta / start_price) * 100
            pct_str = f"{sign}{pct:.2f}%"
        else:
            pct_str = "N/A"

        return f"{sign}{delta:.2f} ({pct_str})  {bars} bars"

    def clear(self) -> None:
        """Clear all data and markers from the chart."""
        self._candle_item.set_data(None)
        self._clear_markers()
        self._clear_session_regions()
        self._datetime_to_idx.clear()

        # Clear info box and crosshair
        self._info_text.setText("")
        self._ohlcv_df = None
        self._crosshair_v.setVisible(False)
        self._crosshair_h.setVisible(False)

        # Clear ruler
        self._ruler_active = False
        self._ruler_start = None
        self._ruler_line.setVisible(False)
        self._ruler_label.setVisible(False)
        self._ruler_label.setText("")

        # Remove VWAP line
        if self._vwap_item is not None:
            self._plot_widget.removeItem(self._vwap_item)
            self._vwap_item = None

        # Remove volume bars
        if self._volume_bars is not None and self._volume_plot is not None:
            self._volume_plot.removeItem(self._volume_bars)
            self._volume_bars = None

        logger.debug("CandlestickChart cleared")

    def auto_range(self) -> None:
        """Reset view to auto-fit all data."""
        self._plot_widget.autoRange()
        if self._volume_plot is not None:
            self._volume_plot.autoRange()
