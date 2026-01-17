"""Equity confidence band chart for Monte Carlo simulation visualization.

Displays percentile bands (5th, 25th, 50th, 75th, 95th) of simulated equity curves
using semi-transparent fill regions and a median line.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import pyqtgraph as pg  # type: ignore[import-untyped]
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QToolTip, QVBoxLayout, QWidget

from src.ui.constants import Colors, Fonts

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from PyQt6.QtCore import QPointF

logger = logging.getLogger(__name__)

# Configure PyQtGraph for performance
pg.setConfigOptions(useOpenGL=True, antialias=True)


class EquityConfidenceBandChart(QWidget):
    """Chart displaying Monte Carlo equity curve confidence bands.

    Shows percentile bands at 5th-95th and 25th-75th ranges with a
    solid median (50th percentile) line. Uses semi-transparent fill
    between curves for visualization.

    Attributes:
        _plot_widget: The underlying PyQtGraph PlotWidget.
        _percentiles: Stored percentile data array.
    """

    render_failed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the EquityConfidenceBandChart.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._percentiles: NDArray[np.float64] | None = None
        self._setup_ui()
        self._setup_pyqtgraph()
        self._setup_bands()
        self._setup_crosshair()

    def _setup_ui(self) -> None:
        """Set up the widget layout."""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    def _setup_pyqtgraph(self) -> None:
        """Initialize PyQtGraph components with Observatory theme."""
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setBackground(Colors.BG_SURFACE)

        # Show subtle grid (BG_BORDER at 20% opacity)
        self._plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self._plot_widget.getPlotItem().getAxis("left").setGrid(51)
        self._plot_widget.getPlotItem().getAxis("bottom").setGrid(51)

        # Configure axes with theme colors
        axis_pen = pg.mkPen(color=Colors.BG_BORDER)
        plot_item = self._plot_widget.getPlotItem()

        for axis_name in ("left", "bottom"):
            axis = plot_item.getAxis(axis_name)
            axis.setPen(axis_pen)
            axis.setTextPen(pg.mkPen(color=Colors.TEXT_SECONDARY))

        # Set axis labels
        plot_item.setLabel("left", "Equity ($)", **{
            "font-family": Fonts.DATA,
            "color": Colors.TEXT_SECONDARY,
        })
        plot_item.setLabel("bottom", "Trade #", **{
            "font-family": Fonts.DATA,
            "color": Colors.TEXT_SECONDARY,
        })

        # Disable right-click context menu
        self._plot_widget.getViewBox().setMenuEnabled(False)

        self._layout.addWidget(self._plot_widget)

    def _setup_bands(self) -> None:
        """Set up confidence band curves and fills."""
        # Create invisible curves for percentile boundaries
        # These are used to create fill regions between them

        # p5 curve (5th percentile) - bottom of outer band
        self._p5_curve = pg.PlotDataItem(pen=pg.mkPen(None))
        self._plot_widget.addItem(self._p5_curve)

        # p95 curve (95th percentile) - top of outer band
        self._p95_curve = pg.PlotDataItem(pen=pg.mkPen(None))
        self._plot_widget.addItem(self._p95_curve)

        # p25 curve (25th percentile) - bottom of inner band
        self._p25_curve = pg.PlotDataItem(pen=pg.mkPen(None))
        self._plot_widget.addItem(self._p25_curve)

        # p75 curve (75th percentile) - top of inner band
        self._p75_curve = pg.PlotDataItem(pen=pg.mkPen(None))
        self._plot_widget.addItem(self._p75_curve)

        # Outer band fill: 5th-95th percentile (Cyan at 8% opacity)
        # SIGNAL_CYAN = #00FFD4 = (0, 255, 212)
        self._outer_fill = pg.FillBetweenItem(
            curve1=self._p5_curve,
            curve2=self._p95_curve,
            brush=pg.mkBrush(color=(0, 255, 212, 20)),  # 8% of 255 ≈ 20
        )
        self._plot_widget.addItem(self._outer_fill)

        # Inner band fill: 25th-75th percentile (Cyan at 15% opacity)
        self._inner_fill = pg.FillBetweenItem(
            curve1=self._p25_curve,
            curve2=self._p75_curve,
            brush=pg.mkBrush(color=(0, 255, 212, 38)),  # 15% of 255 ≈ 38
        )
        self._plot_widget.addItem(self._inner_fill)

        # Median line (p50): Solid cyan, 2px width
        self._median_curve = pg.PlotDataItem(
            pen=pg.mkPen(color=Colors.SIGNAL_CYAN, width=2),
            antialias=True,
        )
        self._plot_widget.addItem(self._median_curve)

    def _setup_crosshair(self) -> None:
        """Set up crosshair line for hover interaction."""
        # Vertical crosshair line
        self._crosshair_v = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen(color=Colors.TEXT_SECONDARY, style=Qt.PenStyle.DashLine, width=1),
        )
        self._crosshair_v.setVisible(False)
        self._plot_widget.addItem(self._crosshair_v, ignoreBounds=True)

        # Connect mouse move signal
        self._plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)

    def _on_mouse_moved(self, pos: QPointF) -> None:
        """Update crosshair and tooltip on mouse move.

        Args:
            pos: Mouse position in scene coordinates.
        """
        if self._percentiles is None or len(self._percentiles) == 0:
            self._crosshair_v.setVisible(False)
            return

        if self._plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self._plot_widget.plotItem.vb.mapSceneToView(pos)
            x_val = int(mouse_point.x())

            # Clamp to valid range
            if 0 <= x_val < len(self._percentiles):
                self._crosshair_v.setPos(x_val)
                self._crosshair_v.setVisible(True)

                # Show tooltip with percentile values
                p5, p25, p50, p75, p95 = self._percentiles[x_val]
                tooltip_text = (
                    f"Trade {x_val}\n"
                    f"---------\n"
                    f"95th: ${p95:,.0f}\n"
                    f"75th: ${p75:,.0f}\n"
                    f"50th: ${p50:,.0f}\n"
                    f"25th: ${p25:,.0f}\n"
                    f"5th:  ${p5:,.0f}"
                )

                global_pos = self._plot_widget.mapToGlobal(
                    self._plot_widget.mapFromScene(pos).toPoint()
                )
                QToolTip.showText(global_pos, tooltip_text)
            else:
                self._crosshair_v.setVisible(False)
                QToolTip.hideText()
        else:
            self._crosshair_v.setVisible(False)
            QToolTip.hideText()

    def set_data(self, percentiles: NDArray[np.float64]) -> None:
        """Set the percentile data for rendering.

        Args:
            percentiles: Array of shape (num_trades, 5) containing
                         p5, p25, p50, p75, p95 values at each trade index.
        """
        try:
            if percentiles is None or len(percentiles) == 0:
                self.clear()
                return

            # Validate shape
            if percentiles.ndim != 2 or percentiles.shape[1] != 5:
                raise ValueError(
                    f"Expected shape (n, 5), got {percentiles.shape}"
                )

            self._percentiles = percentiles
            num_trades = len(percentiles)
            x_data = np.arange(num_trades)

            # Extract percentile columns
            p5 = percentiles[:, 0]
            p25 = percentiles[:, 1]
            p50 = percentiles[:, 2]
            p75 = percentiles[:, 3]
            p95 = percentiles[:, 4]

            # Update curves
            self._p5_curve.setData(x=x_data, y=p5)
            self._p95_curve.setData(x=x_data, y=p95)
            self._p25_curve.setData(x=x_data, y=p25)
            self._p75_curve.setData(x=x_data, y=p75)
            self._median_curve.setData(x=x_data, y=p50)

            # Refresh fill items
            self._outer_fill.setCurves(self._p5_curve, self._p95_curve)
            self._inner_fill.setCurves(self._p25_curve, self._p75_curve)

            # Auto-range to fit data
            self._plot_widget.autoRange()

            logger.debug(
                "EquityConfidenceBandChart updated: %d trades",
                num_trades,
            )

        except Exception as e:
            error_msg = f"ChartRenderError: Failed to render confidence bands - {e}"
            logger.error(error_msg)
            self.render_failed.emit(error_msg)

    def clear(self) -> None:
        """Clear all data from the chart."""
        self._percentiles = None
        self._p5_curve.setData([], [])
        self._p25_curve.setData([], [])
        self._median_curve.setData([], [])
        self._p75_curve.setData([], [])
        self._p95_curve.setData([], [])
        self._crosshair_v.setVisible(False)
        logger.debug("EquityConfidenceBandChart cleared")

    def auto_range(self) -> None:
        """Reset view to auto-fit all data."""
        self._plot_widget.autoRange()
