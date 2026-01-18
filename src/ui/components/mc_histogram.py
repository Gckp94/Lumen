"""Monte Carlo histogram component for distribution visualization.

Provides histogram charts for displaying simulation result distributions
with statistical markers and optional gradient coloring.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import pyqtgraph as pg  # type: ignore[import-untyped]
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QToolTip, QVBoxLayout, QWidget

from src.core.metrics import calculate_suggested_bins
from src.ui.constants import Colors, Fonts

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from PyQt6.QtCore import QPointF

logger = logging.getLogger(__name__)


class MonteCarloHistogram(QWidget):
    """Histogram chart for Monte Carlo distribution visualization.

    Displays distribution data with auto-binning, statistical markers,
    and optional gradient coloring for value-based visualization.

    Attributes:
        _plot_widget: The underlying PyQtGraph PlotWidget.
        _data: Raw distribution data.
        _title: Chart title.
        _color_gradient: Whether to apply gradient coloring.
    """

    render_failed = pyqtSignal(str)

    def __init__(
        self,
        title: str = "",
        color_gradient: bool = False,
        x_format: str = "default",
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the MonteCarloHistogram.

        Args:
            title: Chart title to display.
            color_gradient: If True, apply value-based gradient coloring.
            x_format: X-axis format - "default", "dollar", "percent", or "ratio".
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._title = title
        self._color_gradient = color_gradient
        self._x_format = x_format
        self._data: NDArray[np.float64] | None = None
        self._bin_edges: NDArray[np.float64] | None = None
        self._bin_counts: NDArray[np.int64] | None = None
        self._mean_value: float | None = None
        self._median_value: float | None = None
        self._percentile_markers: dict[str, float] = {}

        self._setup_ui()
        self._setup_pyqtgraph()
        self._setup_bars()
        self._setup_markers()
        self._setup_interactions()

    def _setup_ui(self) -> None:
        """Set up the widget layout."""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    def _setup_pyqtgraph(self) -> None:
        """Initialize PyQtGraph components with Observatory theme."""
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setBackground(Colors.BG_SURFACE)

        # Disable grid
        self._plot_widget.showGrid(x=False, y=False)

        # Configure axes with theme colors
        axis_pen = pg.mkPen(color=Colors.BG_BORDER)
        plot_item = self._plot_widget.getPlotItem()

        for axis_name in ("left", "bottom"):
            axis = plot_item.getAxis(axis_name)
            axis.setPen(axis_pen)
            axis.setTextPen(pg.mkPen(color=Colors.TEXT_SECONDARY))

        # Set axis labels
        plot_item.setLabel("left", "Frequency", **{
            "font-family": Fonts.DATA,
            "color": Colors.TEXT_SECONDARY,
        })

        # Set title if provided
        if self._title:
            plot_item.setTitle(self._title, color=Colors.TEXT_PRIMARY)

        # Disable right-click context menu
        self._plot_widget.getViewBox().setMenuEnabled(False)

        self._layout.addWidget(self._plot_widget)

    def _setup_bars(self) -> None:
        """Set up bar graph item."""
        self._bar_item = pg.BarGraphItem(
            x=[],
            height=[],
            width=0.8,
            brush=pg.mkBrush(Colors.SIGNAL_CYAN),
        )
        self._plot_widget.addItem(self._bar_item)

    def _setup_markers(self) -> None:
        """Set up statistical marker lines."""
        # Mean line: Dashed SIGNAL_BLUE
        self._mean_line = pg.InfiniteLine(
            pos=0,
            angle=90,
            pen=pg.mkPen(color=Colors.SIGNAL_BLUE, style=Qt.PenStyle.DashLine, width=2),
        )
        self._mean_line.setVisible(False)
        self._plot_widget.addItem(self._mean_line)

        # Median line: Solid SIGNAL_CYAN
        self._median_line = pg.InfiniteLine(
            pos=0,
            angle=90,
            pen=pg.mkPen(color=Colors.SIGNAL_CYAN, style=Qt.PenStyle.SolidLine, width=2),
        )
        self._median_line.setVisible(False)
        self._plot_widget.addItem(self._median_line)

        # Percentile markers dictionary (created dynamically)
        self._percentile_lines: dict[str, pg.InfiniteLine] = {}

    def _setup_interactions(self) -> None:
        """Set up mouse interaction handlers."""
        self._plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)

    def _on_mouse_moved(self, pos: QPointF) -> None:
        """Handle mouse movement for tooltip display.

        Args:
            pos: Mouse position in scene coordinates.
        """
        if self._bin_edges is None or self._bin_counts is None:
            return

        try:
            view_box = self._plot_widget.getViewBox()
            mouse_point = view_box.mapSceneToView(pos)
            x, y = mouse_point.x(), mouse_point.y()

            # Find which bin the mouse is over
            tooltip_text = self._get_bar_tooltip(x, y)

            if tooltip_text:
                global_pos = self._plot_widget.mapToGlobal(
                    self._plot_widget.mapFromScene(pos)
                )
                QToolTip.showText(global_pos, tooltip_text)
            else:
                QToolTip.hideText()

        except Exception as e:
            logger.debug("Error in mouse move handler: %s", e)
            QToolTip.hideText()

    def _get_bar_tooltip(self, x: float, y: float) -> str | None:
        """Get tooltip text for bar at position.

        Args:
            x: X position in data coordinates.
            y: Y position in data coordinates.

        Returns:
            Tooltip text or None if not over a bar.
        """
        if self._bin_edges is None or self._bin_counts is None or self._data is None:
            return None

        total_count = len(self._data)

        for i in range(len(self._bin_counts)):
            bin_left = self._bin_edges[i]
            bin_right = self._bin_edges[i + 1]
            count = self._bin_counts[i]

            if bin_left <= x < bin_right and 0 <= y <= count:
                percentage = (count / total_count) * 100 if total_count > 0 else 0

                # Format range based on x_format
                range_str = self._format_range(bin_left, bin_right)

                return (
                    f"Range: {range_str}\n"
                    f"Count: {count:,} simulations\n"
                    f"Percentage: {percentage:.1f}%"
                )

        return None

    def _format_range(self, left: float, right: float) -> str:
        """Format bin range for display.

        Args:
            left: Left edge value.
            right: Right edge value.

        Returns:
            Formatted range string.
        """
        if self._x_format == "dollar":
            return f"${left:,.0f} - ${right:,.0f}"
        elif self._x_format == "percent":
            return f"{left:.1f}% - {right:.1f}%"
        elif self._x_format == "ratio":
            return f"{left:.2f} - {right:.2f}"
        else:
            return f"{left:.2f} - {right:.2f}"

    def _format_value(self, value: float) -> str:
        """Format a single value for display.

        Args:
            value: Value to format.

        Returns:
            Formatted string.
        """
        if self._x_format == "dollar":
            return f"${value:,.0f}"
        elif self._x_format == "percent":
            return f"{value:.1f}%"
        elif self._x_format == "ratio":
            return f"{value:.2f}"
        else:
            return f"{value:.2f}"

    def _calculate_bins(self, data: NDArray[np.float64]) -> tuple[NDArray, NDArray]:
        """Calculate histogram bins using Freedman-Diaconis rule.

        Args:
            data: Distribution data array.

        Returns:
            Tuple of (bin_edges, counts) arrays.
        """
        if len(data) == 0:
            return np.array([]), np.array([])

        # Use existing Freedman-Diaconis implementation
        num_bins = calculate_suggested_bins(list(data), "freedman_diaconis")

        counts, bin_edges = np.histogram(data, bins=num_bins)
        return bin_edges, counts

    def _create_gradient_colors(
        self,
        values: NDArray[np.float64],
        reverse: bool = False,
    ) -> list[tuple[int, int, int, int]]:
        """Create gradient colors based on values.

        For drawdown: cyan (low/good) -> coral (high/bad)
        For metrics with reference: below reference = coral, above = cyan

        Args:
            values: Bin center values for coloring.
            reverse: If True, reverse the gradient direction.

        Returns:
            List of RGBA tuples for each bar.
        """
        colors = []
        min_val, max_val = values.min(), values.max()

        for v in values:
            # Normalize to 0-1
            if max_val != min_val:
                normalized = (v - min_val) / (max_val - min_val)
            else:
                normalized = 0.5

            if reverse:
                normalized = 1 - normalized

            # Interpolate cyan (0, 255, 212) -> coral (255, 71, 87)
            r = int(0 + normalized * 255)
            g = int(255 - normalized * 184)  # 255 -> 71
            b = int(212 - normalized * 125)  # 212 -> 87

            colors.append((r, g, b, 200))

        return colors

    def _update_bars(self) -> None:
        """Update bar graph with current data."""
        if self._data is None or len(self._data) == 0:
            self._bar_item.setOpts(x=[], height=[], width=0.8)
            return

        self._bin_edges, self._bin_counts = self._calculate_bins(self._data)

        if len(self._bin_edges) < 2:
            self._bar_item.setOpts(x=[], height=[], width=0.8)
            return

        # Calculate bin centers and width
        bin_centers = (self._bin_edges[:-1] + self._bin_edges[1:]) / 2
        bin_width = self._bin_edges[1] - self._bin_edges[0]

        # Apply gradient coloring if enabled
        if self._color_gradient:
            colors = self._create_gradient_colors(bin_centers)
            brushes = [pg.mkBrush(*c) for c in colors]
            self._bar_item.setOpts(
                x=bin_centers,
                height=self._bin_counts,
                width=bin_width * 0.85,
                brushes=brushes,
            )
        else:
            self._bar_item.setOpts(
                x=bin_centers,
                height=self._bin_counts,
                width=bin_width * 0.85,
                brush=pg.mkBrush(Colors.SIGNAL_CYAN),
            )

        # Auto-range view
        self._plot_widget.autoRange()

    def _update_markers(self) -> None:
        """Update statistical marker line positions."""
        if self._mean_value is not None:
            self._mean_line.setPos(self._mean_value)
            self._mean_line.setVisible(True)
        else:
            self._mean_line.setVisible(False)

        if self._median_value is not None:
            self._median_line.setPos(self._median_value)
            self._median_line.setVisible(True)
        else:
            self._median_line.setVisible(False)

        # Update percentile markers
        for label, value in self._percentile_markers.items():
            if label not in self._percentile_lines:
                # Create new percentile line
                line = pg.InfiniteLine(
                    pos=value,
                    angle=90,
                    pen=pg.mkPen(
                        color=Colors.TEXT_SECONDARY,
                        style=Qt.PenStyle.DotLine,
                        width=1,
                    ),
                )
                self._percentile_lines[label] = line
                self._plot_widget.addItem(line)
            else:
                self._percentile_lines[label].setPos(value)
                self._percentile_lines[label].setVisible(True)

        # Hide unused percentile lines
        for label, line in self._percentile_lines.items():
            if label not in self._percentile_markers:
                line.setVisible(False)

    def set_data(
        self,
        data: NDArray[np.float64],
        mean: float | None = None,
        median: float | None = None,
        percentiles: dict[str, float] | None = None,
    ) -> None:
        """Set the distribution data for rendering.

        Args:
            data: Array of values to histogram.
            mean: Optional mean value for marker line.
            median: Optional median value for marker line.
            percentiles: Optional dict of {label: value} for percentile markers.
        """
        try:
            if data is None or len(data) == 0:
                self.clear()
                return

            self._data = np.asarray(data, dtype=np.float64)
            self._mean_value = mean
            self._median_value = median
            self._percentile_markers = percentiles or {}

            self._update_bars()
            self._update_markers()

            logger.debug(
                "MonteCarloHistogram '%s' updated: %d values",
                self._title,
                len(data),
            )

        except Exception as e:
            error_msg = f"HistogramRenderError: Failed to render histogram - {e}"
            logger.error(error_msg)
            self.render_failed.emit(error_msg)

    def set_reference_line(self, value: float, label: str = "reference") -> None:
        """Add a reference line (e.g., breakeven at 1.0 for profit factor).

        Args:
            value: X-axis value for reference line.
            label: Label for the reference line.
        """
        if label not in self._percentile_lines:
            line = pg.InfiniteLine(
                pos=value,
                angle=90,
                pen=pg.mkPen(
                    color=Colors.SIGNAL_AMBER,
                    style=Qt.PenStyle.DashDotLine,
                    width=1,
                ),
            )
            self._percentile_lines[label] = line
            self._plot_widget.addItem(line)
        else:
            self._percentile_lines[label].setPos(value)
            self._percentile_lines[label].setVisible(True)

    def set_color_by_reference(
        self,
        reference: float,
        below_color: tuple[int, int, int, int] | None = None,
        above_color: tuple[int, int, int, int] | None = None,
    ) -> None:
        """Color bars based on whether they're above or below a reference value.

        Args:
            reference: Reference value for comparison.
            below_color: RGBA color for values below reference (default: coral).
            above_color: RGBA color for values above reference (default: cyan).
        """
        if self._bin_edges is None or self._bin_counts is None:
            return

        below_color = below_color or (255, 71, 87, 200)  # SIGNAL_CORAL
        above_color = above_color or (0, 255, 212, 200)  # SIGNAL_CYAN

        bin_centers = (self._bin_edges[:-1] + self._bin_edges[1:]) / 2
        colors = []

        for center in bin_centers:
            if center < reference:
                colors.append(below_color)
            else:
                colors.append(above_color)

        brushes = [pg.mkBrush(*c) for c in colors]
        self._bar_item.setOpts(brushes=brushes)

    def add_confidence_shading(
        self,
        lower: float,
        upper: float,
        color: tuple[int, int, int, int] | None = None,
    ) -> None:
        """Add semi-transparent confidence interval shading.

        Args:
            lower: Lower bound of confidence interval.
            upper: Upper bound of confidence interval.
            color: RGBA color for shading (default: cyan at 15% opacity).
        """
        color = color or (0, 255, 212, 38)  # 15% opacity

        # Remove existing shading if present
        if hasattr(self, "_confidence_region"):
            self._plot_widget.removeItem(self._confidence_region)

        # Create linear region item for shading
        self._confidence_region = pg.LinearRegionItem(
            values=[lower, upper],
            orientation="vertical",
            brush=pg.mkBrush(*color),
            pen=pg.mkPen(None),
            movable=False,
        )
        self._plot_widget.addItem(self._confidence_region)

        # Move to back (behind bars)
        self._confidence_region.setZValue(-100)

    def clear(self) -> None:
        """Clear all data from the histogram."""
        self._data = None
        self._bin_edges = None
        self._bin_counts = None
        self._mean_value = None
        self._median_value = None
        self._percentile_markers = {}

        self._bar_item.setOpts(x=[], height=[], width=0.8)
        self._mean_line.setVisible(False)
        self._median_line.setVisible(False)

        for line in self._percentile_lines.values():
            line.setVisible(False)

        if hasattr(self, "_confidence_region"):
            self._plot_widget.removeItem(self._confidence_region)

        logger.debug("MonteCarloHistogram '%s' cleared", self._title)

    def auto_range(self) -> None:
        """Reset view to auto-fit all data."""
        self._plot_widget.autoRange()
