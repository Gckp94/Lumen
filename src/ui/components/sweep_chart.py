"""Parameter sweep visualization chart component."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from src.ui.constants import Colors, Fonts
from src.ui.components.abbreviated_axis import AbbreviatedAxisItem


class SweepChart(QWidget):
    """Chart for displaying parameter sweep results.

    Supports both 1D line charts and 2D heatmaps.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._is_2d = False
        self._x_values: np.ndarray | None = None
        self._y_values: np.ndarray | None = None
        self._z_values: np.ndarray | None = None
        self._current_marker: pg.ScatterPlotItem | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the chart widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create plot widget with abbreviated axes
        self._plot_widget = pg.PlotWidget(
            axisItems={
                "left": AbbreviatedAxisItem(orientation="left"),
                "bottom": AbbreviatedAxisItem(orientation="bottom"),
            }
        )
        self._plot_widget.setBackground(Colors.BG_SURFACE)

        # Configure grid
        self._plot_widget.showGrid(x=True, y=True, alpha=0.2)

        # Create line curve for 1D
        self._line_curve = pg.PlotDataItem(
            pen=pg.mkPen(color=Colors.SIGNAL_CYAN, width=2),
            antialias=True,
        )
        self._plot_widget.addItem(self._line_curve)

        # Create scatter for current position marker
        self._current_marker = pg.ScatterPlotItem(
            size=12,
            pen=pg.mkPen(color=Colors.SIGNAL_AMBER, width=2),
            brush=pg.mkBrush(Colors.SIGNAL_AMBER),
            symbol="o",
        )
        self._plot_widget.addItem(self._current_marker)

        layout.addWidget(self._plot_widget)

    def set_1d_data(
        self,
        x_values: np.ndarray,
        y_values: np.ndarray,
        x_label: str,
        y_label: str,
    ) -> None:
        """Set data for 1D sweep visualization.

        Args:
            x_values: Filter values (X-axis).
            y_values: Metric values (Y-axis).
            x_label: Label for X-axis (filter name).
            y_label: Label for Y-axis (metric name).
        """
        self._is_2d = False
        self._x_values = x_values
        self._y_values = y_values

        # Update line curve
        self._line_curve.setData(x=x_values, y=y_values)

        # Update axis labels
        self._plot_widget.setLabel(
            "bottom",
            x_label,
            **{"font-family": Fonts.DATA, "color": Colors.TEXT_SECONDARY},
        )
        self._plot_widget.setLabel(
            "left",
            y_label,
            **{"font-family": Fonts.DATA, "color": Colors.TEXT_SECONDARY},
        )

        # Clear current marker
        self._current_marker.setData(x=[], y=[])

        # Auto-range
        self._plot_widget.autoRange()

    def set_current_position(
        self, x_index: int, y_index: int | None = None
    ) -> None:
        """Mark the current filter position on the chart.

        Args:
            x_index: Index in x_values array.
            y_index: Index in y_values array (for 2D only).
        """
        if self._x_values is None:
            return

        if self._is_2d:
            # 2D heatmap marker - will be implemented in Task 2
            pass
        else:
            # 1D line chart marker
            if 0 <= x_index < len(self._x_values) and self._y_values is not None:
                x = self._x_values[x_index]
                y = self._y_values[x_index]
                self._current_marker.setData(x=[x], y=[y])

    def clear(self) -> None:
        """Clear all chart data."""
        self._x_values = None
        self._y_values = None
        self._z_values = None
        self._line_curve.setData(x=[], y=[])
        self._current_marker.setData(x=[], y=[])
