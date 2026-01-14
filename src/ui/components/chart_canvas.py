"""PyQtGraph chart wrapper with interactive controls.

Provides a reusable chart component for scatter plots with Observatory theme
styling and GPU acceleration for handling large datasets (83k+ points).
Includes pan, zoom, crosshair, and grid controls.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import pyqtgraph as pg  # type: ignore[import-untyped]
from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from src.ui.constants import Colors, Fonts

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)

# Configure PyQtGraph for performance
pg.setConfigOptions(useOpenGL=True, antialias=False)


class ChartCanvas(QWidget):
    """PyQtGraph chart wrapper with interactive controls.

    A reusable scatter plot component optimized for large datasets. Uses OpenGL
    acceleration and Observatory theme styling. Supports pan, zoom, crosshair,
    and grid toggle.

    Signals:
        point_clicked: Emitted when a point is clicked (index, x, y).
        render_failed: Emitted when rendering fails with error message.
        range_changed: Emitted when view range changes (x_min, x_max, y_min, y_max).
        view_reset: Emitted when view is reset via double-click.

    Attributes:
        _plot_widget: The underlying PyQtGraph PlotWidget.
        _scatter: The ScatterPlotItem for displaying data points.
        _show_grid: Whether grid lines are visible.
    """

    point_clicked = pyqtSignal(int, float, float)  # index, x, y
    render_failed = pyqtSignal(str)
    range_changed = pyqtSignal(float, float, float, float)  # x_min, x_max, y_min, y_max
    view_reset = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the ChartCanvas.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._show_grid: bool = False
        self._zoom_rect: pg.RectROI | None = None
        self._zoom_start: QPointF | None = None
        self._setup_ui()
        self._setup_pyqtgraph()
        self._setup_crosshair()
        self._setup_interactions()

    def _setup_ui(self) -> None:
        """Set up the widget layout."""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    def _setup_pyqtgraph(self) -> None:
        """Initialize PyQtGraph components with Observatory theme."""
        # Create plot widget
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setBackground(Colors.BG_SURFACE)

        # Disable grid by default for clean look
        self._plot_widget.showGrid(x=False, y=False)

        # Configure axes with theme colors
        axis_pen = pg.mkPen(color=Colors.BG_BORDER)
        for axis_name in ("left", "bottom"):
            axis = self._plot_widget.getPlotItem().getAxis(axis_name)
            axis.setPen(axis_pen)
            axis.setTextPen(pg.mkPen(color=Colors.TEXT_SECONDARY))

        # Add X-axis label
        plot_item = self._plot_widget.getPlotItem()
        plot_item.setLabel("bottom", "Trade #", **{
            "font-family": Fonts.DATA,
            "color": Colors.TEXT_SECONDARY,
        })

        # Create scatter plot item optimized for performance
        # Performance optimizations: small size (3px), no pen outline, OpenGL enabled
        self._scatter = pg.ScatterPlotItem(
            size=3,
            pen=None,  # No outline for better performance
            brush=pg.mkBrush(color=Colors.SIGNAL_CYAN),
        )
        self._plot_widget.addItem(self._scatter)

        # Connect click signal
        self._scatter.sigClicked.connect(self._on_point_clicked)

        # Add to layout
        self._layout.addWidget(self._plot_widget)

    def _setup_crosshair(self) -> None:
        """Set up crosshair lines and coordinate label."""
        # Create crosshair lines (moon-gray dashed)
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
            anchor=(0, 1),  # Bottom-left anchor
        )
        self._coord_label.setVisible(False)
        self._plot_widget.addItem(self._coord_label, ignoreBounds=True)

        # Connect mouse move
        self._plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)

    def _setup_interactions(self) -> None:
        """Configure ViewBox for mouse interactions."""
        viewbox = self._plot_widget.getViewBox()

        # Enable mouse interactions (wheel zoom enabled by default)
        viewbox.setMouseEnabled(x=True, y=True)

        # Left-button: Pan mode (default behavior)
        viewbox.setMouseMode(pg.ViewBox.PanMode)

        # Disable right-click context menu to allow custom zoom rectangle
        viewbox.setMenuEnabled(False)

        # Connect range changed signal for bidirectional sync
        viewbox.sigRangeChanged.connect(self._on_viewbox_range_changed)

    def _on_viewbox_range_changed(self, _viewbox: pg.ViewBox) -> None:
        """Handle ViewBox range change for bidirectional sync.

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
            self._coord_label.setText(f"X: {int(x)}, Y: {y:.2f}")

            # Boundary check: adjust anchor to prevent label clipping at edges
            view_range = self._plot_widget.viewRange()
            x_range, y_range = view_range[0], view_range[1]
            x_mid = (x_range[0] + x_range[1]) / 2
            y_mid = (y_range[0] + y_range[1]) / 2

            # Adjust anchor based on cursor position relative to center
            anchor_x = 0 if x < x_mid else 1  # Left side: anchor left, Right: anchor right
            anchor_y = 1 if y < y_mid else 0  # Bottom half: anchor bottom, Top: anchor top
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
            # Map widget position to scene position
            scene_pos = self._plot_widget.plotItem.vb.mapToScene(
                self._plot_widget.plotItem.vb.mapFromParent(event.position())
            )
            # Start zoom rectangle
            self._zoom_start = self._plot_widget.plotItem.vb.mapSceneToView(scene_pos)

            # Create visual rectangle (cyan border, no fill)
            self._zoom_rect = pg.RectROI(
                [self._zoom_start.x(), self._zoom_start.y()],
                [0, 0],
                pen=pg.mkPen(color=Colors.SIGNAL_CYAN, width=1),
                movable=False,
                resizable=False,
            )
            # Hide handles
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
            # Map widget position to scene position
            scene_pos = self._plot_widget.plotItem.vb.mapToScene(
                self._plot_widget.plotItem.vb.mapFromParent(event.position())
            )
            current = self._plot_widget.plotItem.vb.mapSceneToView(scene_pos)
            # Update rectangle size
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
            # Map widget position to scene position
            scene_pos = self._plot_widget.plotItem.vb.mapToScene(
                self._plot_widget.plotItem.vb.mapFromParent(event.position())
            )
            end = self._plot_widget.plotItem.vb.mapSceneToView(scene_pos)
            x_range = sorted([self._zoom_start.x(), end.x()])
            y_range = sorted([self._zoom_start.y(), end.y()])

            # Remove visual rectangle
            self._plot_widget.removeItem(self._zoom_rect)
            self._zoom_rect = None
            self._zoom_start = None

            # Apply zoom if rectangle has meaningful size
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

    def _on_point_clicked(
        self, _scatter: pg.ScatterPlotItem, points: list[pg.SpotItem]
    ) -> None:
        """Handle scatter plot point click.

        Args:
            _scatter: The scatter plot item (unused).
            points: List of clicked points.
        """
        if points:
            point = points[0]
            pos = point.pos()
            index = point.index()
            self.point_clicked.emit(index, pos.x(), pos.y())

    def update_data(
        self,
        df: pd.DataFrame,
        y_column: str,
        x_column: str | None = None,
        color: str = Colors.SIGNAL_CYAN,
        contrast_colors: bool = False,
        color_positive: str = Colors.SIGNAL_CYAN,
        color_negative: str = Colors.SIGNAL_CORAL,
    ) -> None:
        """Update scatter plot with column data.

        Renders the specified columns as a scatter plot. If x_column is None,
        uses row index as x-axis (backward compatible behavior).

        Args:
            df: DataFrame containing the data.
            y_column: Column name to plot on y-axis.
            x_column: Column name to plot on x-axis. If None, uses row index.
            color: Hex color string for points (default: plasma-cyan).
            contrast_colors: If True, color points based on y value sign.
            color_positive: Color for values >= 0 (default: cyan).
            color_negative: Color for values < 0 (default: coral).
        """
        try:
            plot_item = self._plot_widget.getPlotItem()

            # Set Y-axis label
            plot_item.setLabel("left", y_column, **{
                "font-family": Fonts.DATA,
                "color": Colors.TEXT_SECONDARY,
            })

            # Set X-axis label
            x_label = x_column if x_column else "Index"
            plot_item.setLabel("bottom", x_label, **{
                "font-family": Fonts.DATA,
                "color": Colors.TEXT_SECONDARY,
            })

            if df is None or df.empty or y_column not in df.columns:
                self._scatter.setData([], [])
                logger.debug("Cleared chart: empty data or missing column")
                return

            if x_column and x_column not in df.columns:
                self._scatter.setData([], [])
                logger.warning(f"X column '{x_column}' not found in DataFrame")
                return

            # Extract data
            y_data = df[y_column].values
            if x_column:
                x_data = df[x_column].values
            else:
                x_data = np.arange(len(y_data))

            # Update scatter plot with color(s)
            if contrast_colors:
                brush_pos = pg.mkBrush(color=color_positive)
                brush_neg = pg.mkBrush(color=color_negative)
                brushes = [brush_pos if val >= 0 else brush_neg for val in y_data]
                self._scatter.setData(x=x_data, y=y_data, brush=brushes)
            else:
                self._scatter.setBrush(pg.mkBrush(color=color))
                self._scatter.setData(x=x_data, y=y_data)

            self._plot_widget.autoRange()
            logger.debug(f"Chart updated with {len(y_data)} points: x={x_label}, y={y_column}")

        except Exception as e:
            error_msg = f"Failed to render chart: {e}"
            logger.error(error_msg)
            self.render_failed.emit(error_msg)

    def clear(self) -> None:
        """Clear all data from the chart."""
        self._scatter.setData([], [])

    def set_grid_visible(self, visible: bool) -> None:
        """Show or hide grid lines.

        Args:
            visible: Whether to show grid lines.
        """
        self._show_grid = visible
        if visible:
            # Use alpha value (0-255) for grid visibility
            self._plot_widget.getPlotItem().getAxis("left").setGrid(77)  # ~0.3 alpha
            self._plot_widget.getPlotItem().getAxis("bottom").setGrid(77)
        else:
            self._plot_widget.getPlotItem().getAxis("left").setGrid(0)
            self._plot_widget.getPlotItem().getAxis("bottom").setGrid(0)

    def set_range(
        self, x_min: float, x_max: float, y_min: float, y_max: float
    ) -> None:
        """Set the view range programmatically.

        Args:
            x_min: Minimum X value.
            x_max: Maximum X value.
            y_min: Minimum Y value.
            y_max: Maximum Y value.
        """
        self._plot_widget.setRange(xRange=(x_min, x_max), yRange=(y_min, y_max))

    def auto_range(self) -> None:
        """Reset view to auto-fit all data."""
        self._plot_widget.autoRange()
        self.view_reset.emit()

    def get_view_range(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Get current view range.

        Returns:
            Tuple of ((x_min, x_max), (y_min, y_max)).
        """
        view_range = self._plot_widget.viewRange()
        return (tuple(view_range[0]), tuple(view_range[1]))
