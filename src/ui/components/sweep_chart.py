"""Parameter sweep visualization chart component."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg  # type: ignore[import-untyped]
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

        # Create ImageItem for 2D heatmap
        self._heatmap = pg.ImageItem()
        self._plot_widget.addItem(self._heatmap)
        self._heatmap.setVisible(False)

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

        Raises:
            ValueError: If x_values and y_values have different lengths.
        """
        if len(x_values) != len(y_values):
            raise ValueError("x_values and y_values must have the same length")

        self._is_2d = False
        self._x_values = x_values
        self._y_values = y_values

        # Show line curve, hide heatmap
        self._line_curve.setVisible(True)
        self._heatmap.setVisible(False)

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

    def set_2d_data(
        self,
        x_values: np.ndarray,
        y_values: np.ndarray,
        z_values: np.ndarray,
        x_label: str,
        y_label: str,
        z_label: str,
    ) -> None:
        """Set data for 2D sweep heatmap visualization.

        Args:
            x_values: Filter 1 values (X-axis).
            y_values: Filter 2 values (Y-axis).
            z_values: Metric values as 2D array, shape (len(y), len(x)).
            x_label: Label for X-axis (filter 1 name).
            y_label: Label for Y-axis (filter 2 name).
            z_label: Label for colorbar (metric name).

        Raises:
            ValueError: If z_values shape does not match (len(y_values), len(x_values)).
        """
        # Validate z_values shape
        expected_shape = (len(y_values), len(x_values))
        if z_values.shape != expected_shape:
            raise ValueError(
                f"z_values shape {z_values.shape} does not match expected {expected_shape}"
            )

        # Note: z_label is reserved for future colorbar support
        _ = z_label  # Unused for now

        self._is_2d = True
        self._x_values = x_values
        self._y_values = y_values
        self._z_values = z_values

        # Hide line curve, show heatmap
        self._line_curve.setVisible(False)
        self._heatmap.setVisible(True)

        # Calculate cell dimensions
        x_step = (x_values[-1] - x_values[0]) / (len(x_values) - 1) if len(x_values) > 1 else 1
        y_step = (y_values[-1] - y_values[0]) / (len(y_values) - 1) if len(y_values) > 1 else 1

        # Set heatmap data and position
        self._heatmap.setImage(z_values.T)  # Transpose for correct orientation
        self._heatmap.setRect(
            x_values[0] - x_step / 2,
            y_values[0] - y_step / 2,
            x_values[-1] - x_values[0] + x_step,
            y_values[-1] - y_values[0] + y_step,
        )

        # Create colormap (coral to cyan gradient)
        cmap = pg.ColorMap(
            pos=[0, 0.5, 1],
            color=[
                pg.mkColor(Colors.SIGNAL_CORAL),
                pg.mkColor(Colors.TEXT_SECONDARY),
                pg.mkColor(Colors.SIGNAL_CYAN),
            ],
        )
        self._heatmap.setColorMap(cmap)

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
            # 2D heatmap marker
            if (
                self._y_values is not None
                and y_index is not None
                and 0 <= x_index < len(self._x_values)
                and 0 <= y_index < len(self._y_values)
            ):
                x = self._x_values[x_index]
                y = self._y_values[y_index]
                self._current_marker.setData(x=[x], y=[y])
        else:
            # 1D line chart marker
            if 0 <= x_index < len(self._x_values) and self._y_values is not None:
                x = self._x_values[x_index]
                y = self._y_values[x_index]
                self._current_marker.setData(x=[x], y=[y])

    def clear(self) -> None:
        """Clear all chart data."""
        self._is_2d = False
        self._x_values = None
        self._y_values = None
        self._z_values = None
        self._line_curve.setData(x=[], y=[])
        self._current_marker.setData(x=[], y=[])
        self._heatmap.setImage(None)
        self._heatmap.setVisible(False)
        self._line_curve.setVisible(True)
