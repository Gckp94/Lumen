"""Equity curve chart component with baseline/filtered comparison.

Provides a line chart for visualizing equity curves with drawdown overlay,
crosshair, pan/zoom interactions, and keyboard accessibility.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import pyqtgraph as pg  # type: ignore[import-untyped]
from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import (
    QCheckBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.ui.constants import Colors, Fonts, FontSizes, Spacing

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)

# Configure PyQtGraph for performance
pg.setConfigOptions(useOpenGL=True, antialias=True)


class EquityChart(QWidget):
    """Line chart for equity curve visualization.

    Displays baseline and filtered equity curves with optional drawdown fill.
    Supports interactive pan, zoom, crosshair, and keyboard controls.

    Signals:
        render_failed: Emitted when rendering fails with error message.
        range_changed: Emitted when view range changes (x_min, x_max, y_min, y_max).
        view_reset: Emitted when view is reset via double-click or Home key.

    Attributes:
        _plot_widget: The underlying PyQtGraph PlotWidget.
        _baseline_curve: PlotDataItem for baseline equity.
        _filtered_curve: PlotDataItem for filtered equity.
        _drawdown_fill: FillBetweenItem for drawdown visualization.
        _show_drawdown: Whether drawdown fill is visible.
    """

    render_failed = pyqtSignal(str)
    range_changed = pyqtSignal(float, float, float, float)  # x_min, x_max, y_min, y_max
    view_reset = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the EquityChart.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._show_drawdown: bool = False
        self._zoom_rect: pg.RectROI | None = None
        self._zoom_start: QPointF | None = None
        self._baseline_data: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None
        self._setup_ui()
        self._setup_pyqtgraph()
        self._setup_curves()
        self._setup_crosshair()
        self._setup_interactions()

        # Enable keyboard focus for shortcuts
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

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
        plot_item.setLabel("left", "Equity ($)", **{
            "font-family": Fonts.DATA,
            "color": Colors.TEXT_SECONDARY,
        })
        plot_item.setLabel("bottom", "Trade #", **{
            "font-family": Fonts.DATA,
            "color": Colors.TEXT_SECONDARY,
        })

        self._layout.addWidget(self._plot_widget)

    def _setup_curves(self) -> None:
        """Set up baseline and filtered curve items."""
        # Baseline curve (stellar-blue)
        self._baseline_curve = pg.PlotDataItem(
            pen=pg.mkPen(color=Colors.SIGNAL_BLUE, width=2),
            antialias=True,
        )
        self._plot_widget.addItem(self._baseline_curve)

        # Filtered curve (plasma-cyan)
        self._filtered_curve = pg.PlotDataItem(
            pen=pg.mkPen(color=Colors.SIGNAL_CYAN, width=2),
            antialias=True,
        )
        self._plot_widget.addItem(self._filtered_curve)

        # Peak curve for drawdown calculation (invisible)
        self._peak_curve = pg.PlotDataItem(pen=None)
        self._plot_widget.addItem(self._peak_curve)

        # Drawdown fill (semi-transparent coral)
        self._drawdown_fill = pg.FillBetweenItem(
            curve1=self._baseline_curve,
            curve2=self._peak_curve,
            brush=pg.mkBrush(color=(255, 71, 87, 128)),  # SIGNAL_CORAL with 50% alpha
        )
        self._drawdown_fill.setVisible(False)
        self._plot_widget.addItem(self._drawdown_fill)

        # Add legend
        self._legend = self._plot_widget.addLegend(offset=(10, 10))
        self._legend.addItem(self._baseline_curve, "Baseline")
        self._legend.addItem(self._filtered_curve, "Filtered")

    def _setup_crosshair(self) -> None:
        """Set up crosshair lines and coordinate label."""
        pen = pg.mkPen(color=Colors.TEXT_SECONDARY, style=Qt.PenStyle.DashLine, width=1)

        self._crosshair_v = pg.InfiniteLine(angle=90, movable=False, pen=pen)
        self._crosshair_h = pg.InfiniteLine(angle=0, movable=False, pen=pen)
        self._crosshair_v.setVisible(False)
        self._crosshair_h.setVisible(False)
        self._plot_widget.addItem(self._crosshair_v, ignoreBounds=True)
        self._plot_widget.addItem(self._crosshair_h, ignoreBounds=True)

        # Coordinate label
        self._coord_label = pg.TextItem(
            text="",
            color=Colors.TEXT_PRIMARY,
            anchor=(0, 1),
        )
        self._coord_label.setVisible(False)
        self._plot_widget.addItem(self._coord_label, ignoreBounds=True)

        # Connect mouse move
        self._plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)

    def _setup_interactions(self) -> None:
        """Configure ViewBox for mouse interactions."""
        viewbox = self._plot_widget.getViewBox()

        # Enable mouse interactions
        viewbox.setMouseEnabled(x=True, y=True)

        # Left-button: Pan mode
        viewbox.setMouseMode(pg.ViewBox.PanMode)

        # Disable right-click context menu
        viewbox.setMenuEnabled(False)

        # Connect range changed signal
        viewbox.sigRangeChanged.connect(self._on_viewbox_range_changed)

    def _on_viewbox_range_changed(self, _viewbox: pg.ViewBox) -> None:
        """Handle ViewBox range change.

        Args:
            _viewbox: The ViewBox that changed (unused).
        """
        view_range = self._plot_widget.viewRange()
        x_range, y_range = view_range[0], view_range[1]
        self.range_changed.emit(x_range[0], x_range[1], y_range[0], y_range[1])

    def _on_mouse_moved(self, pos: QPointF) -> None:
        """Update crosshair position on mouse move.

        Args:
            pos: Mouse position in scene coordinates.
        """
        if self._plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self._plot_widget.plotItem.vb.mapSceneToView(pos)
            x, y = mouse_point.x(), mouse_point.y()

            self._crosshair_v.setPos(x)
            self._crosshair_h.setPos(y)
            self._coord_label.setText(f"Trade: {int(x)}, Equity: ${y:,.2f}")

            # Boundary check: adjust anchor to prevent label clipping
            view_range = self._plot_widget.viewRange()
            x_range, y_range = view_range[0], view_range[1]
            x_mid = (x_range[0] + x_range[1]) / 2
            y_mid = (y_range[0] + y_range[1]) / 2

            anchor_x = 0 if x < x_mid else 1
            anchor_y = 1 if y < y_mid else 0
            self._coord_label.setAnchor((anchor_x, anchor_y))
            self._coord_label.setPos(x, y)

            self._crosshair_v.setVisible(True)
            self._crosshair_h.setVisible(True)
            self._coord_label.setVisible(True)
        else:
            self._crosshair_v.setVisible(False)
            self._crosshair_h.setVisible(False)
            self._coord_label.setVisible(False)

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        """Handle mouse press for right-click zoom start.

        Args:
            event: The mouse press event.
        """
        if event is None:
            return
        if event.button() == Qt.MouseButton.RightButton:
            scene_pos = self._plot_widget.plotItem.vb.mapToScene(
                self._plot_widget.plotItem.vb.mapFromParent(event.position())
            )
            self._zoom_start = self._plot_widget.plotItem.vb.mapSceneToView(scene_pos)

            self._zoom_rect = pg.RectROI(
                [self._zoom_start.x(), self._zoom_start.y()],
                [0, 0],
                pen=pg.mkPen(color=Colors.SIGNAL_CYAN, width=1),
                movable=False,
                resizable=False,
            )
            for handle in self._zoom_rect.getHandles():
                handle.hide()
            self._plot_widget.addItem(self._zoom_rect)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:
        """Handle mouse move for zoom rectangle resize.

        Args:
            event: The mouse move event.
        """
        if event is None:
            return
        if self._zoom_rect is not None and self._zoom_start is not None:
            scene_pos = self._plot_widget.plotItem.vb.mapToScene(
                self._plot_widget.plotItem.vb.mapFromParent(event.position())
            )
            current = self._plot_widget.plotItem.vb.mapSceneToView(scene_pos)
            self._zoom_rect.setSize([
                current.x() - self._zoom_start.x(),
                current.y() - self._zoom_start.y(),
            ])
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        """Handle mouse release for zoom rectangle apply.

        Args:
            event: The mouse release event.
        """
        if event is None:
            return
        if (
            event.button() == Qt.MouseButton.RightButton
            and self._zoom_rect is not None
            and self._zoom_start is not None
        ):
            scene_pos = self._plot_widget.plotItem.vb.mapToScene(
                self._plot_widget.plotItem.vb.mapFromParent(event.position())
            )
            end = self._plot_widget.plotItem.vb.mapSceneToView(scene_pos)
            x_range = sorted([self._zoom_start.x(), end.x()])
            y_range = sorted([self._zoom_start.y(), end.y()])

            self._plot_widget.removeItem(self._zoom_rect)
            self._zoom_rect = None
            self._zoom_start = None

            if abs(x_range[1] - x_range[0]) > 1 and abs(y_range[1] - y_range[0]) > 0.01:
                self._plot_widget.setRange(xRange=x_range, yRange=y_range)
        else:
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent | None) -> None:
        """Handle double-click to reset view.

        Args:
            event: The mouse double-click event.
        """
        if event is None:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._plot_widget.autoRange()
            self.view_reset.emit()
        else:
            super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        """Handle keyboard shortcuts for accessibility.

        Args:
            event: The key press event.
        """
        if event is None:
            return

        key = event.key()

        # Home key: reset view
        if key == Qt.Key.Key_Home:
            self._plot_widget.autoRange()
            self.view_reset.emit()
        # Plus key: zoom in
        elif key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            viewbox = self._plot_widget.getViewBox()
            viewbox.scaleBy((0.8, 0.8))
        # Minus key: zoom out
        elif key == Qt.Key.Key_Minus:
            viewbox = self._plot_widget.getViewBox()
            viewbox.scaleBy((1.25, 1.25))
        else:
            super().keyPressEvent(event)

    @property
    def show_drawdown(self) -> bool:
        """Whether drawdown fill is visible."""
        return self._show_drawdown

    def set_drawdown_visible(self, visible: bool) -> None:
        """Show or hide the drawdown fill.

        Args:
            visible: Whether to show drawdown fill.
        """
        self._show_drawdown = visible
        self._drawdown_fill.setVisible(visible and self._baseline_data is not None)

    def set_baseline(self, equity_df: pd.DataFrame | None) -> None:
        """Set the baseline equity curve data.

        Args:
            equity_df: DataFrame with trade_num, equity, and peak columns, or None to clear.
        """
        try:
            if equity_df is None or equity_df.empty:
                self._baseline_curve.setData([], [])
                self._peak_curve.setData([], [])
                self._baseline_data = None
                self._drawdown_fill.setVisible(False)
                logger.debug("Cleared baseline equity curve")
                return

            x_data = equity_df["trade_num"].to_numpy()
            y_data = equity_df["equity"].to_numpy()
            peak_data = equity_df["peak"].to_numpy()

            self._baseline_curve.setData(x=x_data, y=y_data)
            self._peak_curve.setData(x=x_data, y=peak_data)
            self._baseline_data = (x_data, y_data, peak_data)

            # Update drawdown fill visibility
            if self._show_drawdown:
                self._drawdown_fill.setVisible(True)

            self._plot_widget.autoRange()
            logger.debug("EquityChart updated: %d baseline points", len(x_data))

        except Exception as e:
            error_msg = f"ChartRenderError: Failed to render baseline - {e}"
            logger.error(error_msg)
            self.render_failed.emit(error_msg)

    def set_filtered(self, equity_df: pd.DataFrame | None) -> None:
        """Set the filtered equity curve data.

        Args:
            equity_df: DataFrame with trade_num and equity columns, or None to hide.
        """
        try:
            if equity_df is None or equity_df.empty:
                self._filtered_curve.setData([], [])
                logger.debug("Cleared filtered equity curve")
                return

            x_data = equity_df["trade_num"].to_numpy()
            y_data = equity_df["equity"].to_numpy()

            self._filtered_curve.setData(x=x_data, y=y_data)
            self._plot_widget.autoRange()
            logger.debug("EquityChart updated: %d filtered points", len(x_data))

        except Exception as e:
            error_msg = f"ChartRenderError: Failed to render filtered - {e}"
            logger.error(error_msg)
            self.render_failed.emit(error_msg)

    def clear(self) -> None:
        """Clear all data from the chart."""
        self._baseline_curve.setData([], [])
        self._filtered_curve.setData([], [])
        self._peak_curve.setData([], [])
        self._baseline_data = None
        self._drawdown_fill.setVisible(False)

    def auto_range(self) -> None:
        """Reset view to auto-fit all data."""
        self._plot_widget.autoRange()
        self.view_reset.emit()


class _ChartPanel(QWidget):
    """Container widget for an equity chart with title and controls.

    Contains a title label, EquityChart, and drawdown toggle checkbox.

    Attributes:
        chart: The EquityChart widget.
        _drawdown_checkbox: Checkbox to toggle drawdown visibility.
    """

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        """Initialize the chart panel.

        Args:
            title: Title text to display above the chart.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._setup_ui(title)

    def _setup_ui(self, title: str) -> None:
        """Set up the panel layout.

        Args:
            title: Title text for the chart.
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        # Title label
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.UI};
                font-size: {FontSizes.H2}px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(title_label)

        # Equity chart
        self.chart = EquityChart()
        self.chart.setMinimumHeight(250)
        layout.addWidget(self.chart, stretch=1)

        # Drawdown checkbox
        self._drawdown_checkbox = QCheckBox("Show Drawdown")
        self._drawdown_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
            }}
        """)
        self._drawdown_checkbox.toggled.connect(self.chart.set_drawdown_visible)
        layout.addWidget(self._drawdown_checkbox)

    def set_baseline(self, equity_df: pd.DataFrame | None) -> None:
        """Pass-through to chart's set_baseline method.

        Args:
            equity_df: DataFrame with equity data.
        """
        self.chart.set_baseline(equity_df)

    def set_filtered(self, equity_df: pd.DataFrame | None) -> None:
        """Pass-through to chart's set_filtered method.

        Args:
            equity_df: DataFrame with equity data.
        """
        self.chart.set_filtered(equity_df)

    def clear(self) -> None:
        """Clear the chart."""
        self.chart.clear()
