"""Portfolio charts component with side-by-side equity and drawdown charts.

Provides visualization for multi-strategy portfolio performance with a shared
legend bar for toggling series visibility.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
import pyqtgraph as pg  # type: ignore[import-untyped]
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from pyqtgraph import DateAxisItem

from src.ui.components.abbreviated_axis import AbbreviatedAxisItem
from src.ui.components.axis_mode_toggle import AxisMode, AxisModeToggle
from src.ui.constants import Colors, Fonts, FontSizes, Spacing

logger = logging.getLogger(__name__)

# Configure PyQtGraph for performance
pg.setConfigOptions(useOpenGL=True, antialias=True)

# Color constants for portfolio visualization
STRATEGY_COLORS = ["#00D9FF", "#FFB800", "#FF00FF", "#00FF88", "#FF6B6B", "#A855F7"]
BASELINE_COLOR = "#AAAAAA"
COMBINED_COLOR = "#00FF00"


class PortfolioChartsWidget(QWidget):
    """Widget with side-by-side equity and drawdown charts.

    Displays portfolio equity curves and drawdown percentages for multiple
    strategies with a shared legend bar.

    Signals:
        axis_mode_changed: Emitted when X-axis mode changes (AxisMode).

    Attributes:
        _data: Dictionary mapping series names to DataFrames.
        _series_visibility: Dictionary tracking visibility state of each series.
        _equity_curves: Dictionary mapping names to equity PlotDataItems.
        _drawdown_curves: Dictionary mapping names to drawdown PlotDataItems.
        _legend_checkboxes: Dictionary mapping names to legend checkboxes.
    """

    axis_mode_changed = pyqtSignal(object)  # AxisMode

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the PortfolioChartsWidget.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._data: dict[str, pd.DataFrame] = {}
        self._series_visibility: dict[str, bool] = {}
        self._equity_curves: dict[str, pg.PlotDataItem] = {}
        self._drawdown_curves: dict[str, pg.PlotDataItem] = {}
        self._legend_checkboxes: dict[str, QCheckBox] = {}
        self._color_map: dict[str, str] = {}
        self._axis_mode = AxisMode.TRADES
        self._strategy_color_index = 0

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the widget layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        # Legend bar at top
        self._legend_widget = QWidget()
        self._legend_layout = QHBoxLayout(self._legend_widget)
        self._legend_layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        self._legend_layout.setSpacing(Spacing.MD)
        self._legend_layout.addStretch()  # Right-align items
        layout.addWidget(self._legend_widget)

        # Charts container (side-by-side)
        charts_container = QWidget()
        charts_layout = QHBoxLayout(charts_container)
        charts_layout.setContentsMargins(0, 0, 0, 0)
        charts_layout.setSpacing(Spacing.MD)

        # Equity chart
        equity_container = QWidget()
        equity_layout = QVBoxLayout(equity_container)
        equity_layout.setContentsMargins(0, 0, 0, 0)
        equity_layout.setSpacing(Spacing.XS)

        equity_title = QLabel("Equity Curve")
        equity_title.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.UI};
                font-size: {FontSizes.H2}px;
                font-weight: bold;
            }}
        """)
        equity_layout.addWidget(equity_title)

        self._equity_plot = pg.PlotWidget()
        self._setup_plot_widget(self._equity_plot, "Equity ($)")
        self._equity_plot.setMinimumHeight(200)
        equity_layout.addWidget(self._equity_plot, stretch=1)

        charts_layout.addWidget(equity_container, stretch=1)

        # Drawdown chart
        drawdown_container = QWidget()
        drawdown_layout = QVBoxLayout(drawdown_container)
        drawdown_layout.setContentsMargins(0, 0, 0, 0)
        drawdown_layout.setSpacing(Spacing.XS)

        drawdown_title = QLabel("Drawdown (%)")
        drawdown_title.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.UI};
                font-size: {FontSizes.H2}px;
                font-weight: bold;
            }}
        """)
        drawdown_layout.addWidget(drawdown_title)

        self._drawdown_plot = pg.PlotWidget()
        self._setup_plot_widget(self._drawdown_plot, "Drawdown (%)")
        self._drawdown_plot.setMinimumHeight(200)
        drawdown_layout.addWidget(self._drawdown_plot, stretch=1)

        charts_layout.addWidget(drawdown_container, stretch=1)

        layout.addWidget(charts_container, stretch=1)

        # Controls row
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(Spacing.MD)

        # Axis mode toggle
        self._axis_toggle = AxisModeToggle()
        self._axis_toggle.mode_changed.connect(self._on_axis_mode_changed)
        controls_layout.addWidget(self._axis_toggle)

        controls_layout.addStretch()

        layout.addLayout(controls_layout)

    def _setup_plot_widget(self, plot_widget: pg.PlotWidget, y_label: str) -> None:
        """Configure a plot widget with theme styling.

        Args:
            plot_widget: The PlotWidget to configure.
            y_label: Label for the Y-axis.
        """
        plot_widget.setBackground(Colors.BG_SURFACE)
        plot_widget.showGrid(x=False, y=False)

        # Configure axes
        axis_pen = pg.mkPen(color=Colors.BG_BORDER)
        plot_item = plot_widget.getPlotItem()

        # Use AbbreviatedAxisItem for Y-axis to show K/M/B instead of scientific notation
        abbreviated_y_axis = AbbreviatedAxisItem(orientation="left")
        abbreviated_y_axis.setPen(axis_pen)
        abbreviated_y_axis.setTextPen(pg.mkPen(color=Colors.TEXT_SECONDARY))
        plot_item.setAxisItems({"left": abbreviated_y_axis})

        # Configure bottom axis
        bottom_axis = plot_item.getAxis("bottom")
        bottom_axis.setPen(axis_pen)
        bottom_axis.setTextPen(pg.mkPen(color=Colors.TEXT_SECONDARY))

        # Set labels
        plot_item.setLabel("left", y_label, **{
            "font-family": Fonts.DATA,
            "color": Colors.TEXT_SECONDARY,
        })
        plot_item.setLabel("bottom", "Trade #", **{
            "font-family": Fonts.DATA,
            "color": Colors.TEXT_SECONDARY,
        })

        # Enable interactions
        viewbox = plot_widget.getViewBox()
        viewbox.setMouseEnabled(x=True, y=True)
        viewbox.setMouseMode(pg.ViewBox.PanMode)
        viewbox.setMenuEnabled(False)

    def _get_color_for_series(self, name: str) -> str:
        """Get or assign a color for a series.

        Args:
            name: Series name.

        Returns:
            Hex color string.
        """
        if name in self._color_map:
            return self._color_map[name]

        if name == "baseline":
            color = BASELINE_COLOR
        elif name == "combined":
            color = COMBINED_COLOR
        else:
            # Rotate through strategy colors
            color = STRATEGY_COLORS[self._strategy_color_index % len(STRATEGY_COLORS)]
            self._strategy_color_index += 1

        self._color_map[name] = color
        return color

    def _get_pen_for_series(self, name: str) -> Any:
        """Get the pen style for a series.

        Args:
            name: Series name.

        Returns:
            PyQtGraph pen object.
        """
        color = self._get_color_for_series(name)

        if name == "baseline":
            # Dashed gray line for baseline
            return pg.mkPen(color=color, width=2, style=Qt.PenStyle.DashLine)
        else:
            # Solid line for other series
            return pg.mkPen(color=color, width=2)

    def set_data(self, data: dict[str, pd.DataFrame]) -> None:
        """Set chart data for all series.

        Args:
            data: Dictionary mapping series names to DataFrames.
                  Each DataFrame should have: trade_num, equity, drawdown, peak, date columns.
        """
        self._data = data

        # Clear existing curves
        for curve in self._equity_curves.values():
            self._equity_plot.removeItem(curve)
        for curve in self._drawdown_curves.values():
            self._drawdown_plot.removeItem(curve)

        self._equity_curves.clear()
        self._drawdown_curves.clear()

        # Clear legend checkboxes (except the stretch)
        while self._legend_layout.count() > 1:
            item = self._legend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._legend_checkboxes.clear()

        # Reset color index for new data
        # But keep color map to preserve colors for same series names
        self._strategy_color_index = 0

        # Create curves and legend entries for each series
        for name, df in data.items():
            self._add_series(name, df)

        # Auto-range both plots
        self._equity_plot.autoRange()
        self._drawdown_plot.autoRange()

    def _add_series(self, name: str, df: pd.DataFrame) -> None:
        """Add a series to both charts.

        Args:
            name: Series name.
            df: DataFrame with trade_num, equity, drawdown, peak, date columns.
        """
        if df.empty:
            return

        pen = self._get_pen_for_series(name)
        color = self._get_color_for_series(name)

        # Get X data based on axis mode
        x_data = self._get_x_data(df)
        if x_data is None:
            return

        # Create equity curve
        equity_curve = pg.PlotDataItem(
            x=x_data,
            y=df["equity"].to_numpy(),
            pen=pen,
            antialias=True,
        )
        self._equity_curves[name] = equity_curve
        self._equity_plot.addItem(equity_curve)

        # Create drawdown curve (as percentage)
        drawdown_pct = self._calculate_drawdown_pct(df)
        drawdown_curve = pg.PlotDataItem(
            x=x_data,
            y=drawdown_pct,
            pen=pen,
            antialias=True,
        )
        self._drawdown_curves[name] = drawdown_curve
        self._drawdown_plot.addItem(drawdown_curve)

        # Apply visibility state
        is_visible = self._series_visibility.get(name, True)
        equity_curve.setVisible(is_visible)
        drawdown_curve.setVisible(is_visible)

        # Create legend checkbox
        checkbox = self._create_legend_checkbox(name, color, is_visible)
        self._legend_checkboxes[name] = checkbox

        # Insert before the stretch
        self._legend_layout.insertWidget(self._legend_layout.count() - 1, checkbox)

    def _get_x_data(self, df: pd.DataFrame) -> np.ndarray | None:
        """Get X-axis data based on current axis mode.

        Args:
            df: DataFrame with trade data.

        Returns:
            Array of X values, or None if data is invalid.
        """
        if "trade_num" not in df.columns:
            return None

        if self._axis_mode == AxisMode.DATE and "date" in df.columns:
            try:
                # Convert dates to timestamps
                dates = pd.to_datetime(df["date"], errors="coerce")
                if dates.notna().all():
                    return (dates.astype(np.int64) // 10**9).to_numpy()
            except Exception as e:
                logger.warning("Failed to convert dates: %s", e)

        return df["trade_num"].to_numpy()

    def _calculate_drawdown_pct(self, df: pd.DataFrame) -> np.ndarray:
        """Calculate drawdown as percentage.

        Args:
            df: DataFrame with drawdown and peak columns.

        Returns:
            Array of drawdown percentages.
        """
        if "drawdown" not in df.columns or "peak" not in df.columns:
            return np.zeros(len(df))

        drawdown = df["drawdown"].to_numpy()
        peak = df["peak"].to_numpy()

        # Avoid division by zero
        with np.errstate(divide="ignore", invalid="ignore"):
            pct = np.where(peak > 0, (drawdown / peak) * 100, 0)

        return pct

    def _create_legend_checkbox(self, name: str, color: str, checked: bool) -> QCheckBox:
        """Create a colored checkbox for the legend.

        Args:
            name: Series name.
            color: Hex color for the checkbox.
            checked: Initial checked state.

        Returns:
            Configured QCheckBox.
        """
        checkbox = QCheckBox(name)
        checkbox.setChecked(checked)
        checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {color};
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
                font-weight: 500;
                spacing: {Spacing.XS}px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border-radius: 3px;
                border: 2px solid {color};
            }}
            QCheckBox::indicator:checked {{
                background-color: {color};
            }}
            QCheckBox::indicator:unchecked {{
                background-color: transparent;
            }}
        """)
        checkbox.toggled.connect(lambda checked, n=name: self._on_checkbox_toggled(n, checked))
        checkbox.setCursor(Qt.CursorShape.PointingHandCursor)

        return checkbox

    def _on_checkbox_toggled(self, name: str, checked: bool) -> None:
        """Handle legend checkbox toggle.

        Args:
            name: Series name.
            checked: New checked state.
        """
        self.set_series_visible(name, checked)

    def set_series_visible(self, name: str, visible: bool) -> None:
        """Set visibility of a series.

        Args:
            name: Series name.
            visible: Whether the series should be visible.
        """
        self._series_visibility[name] = visible

        # Update curve visibility
        if name in self._equity_curves:
            self._equity_curves[name].setVisible(visible)
        if name in self._drawdown_curves:
            self._drawdown_curves[name].setVisible(visible)

        # Update checkbox state
        if name in self._legend_checkboxes:
            checkbox = self._legend_checkboxes[name]
            # Block signals to avoid recursion
            checkbox.blockSignals(True)
            checkbox.setChecked(visible)
            checkbox.blockSignals(False)

    def is_series_visible(self, name: str) -> bool:
        """Check if a series is visible.

        Args:
            name: Series name.

        Returns:
            True if the series is visible, False otherwise.
        """
        return self._series_visibility.get(name, True)

    def _on_axis_mode_changed(self, mode: AxisMode) -> None:
        """Handle axis mode change.

        Args:
            mode: New axis mode.
        """
        self._axis_mode = mode
        self._update_axis_display()
        self.axis_mode_changed.emit(mode)

    def _update_axis_display(self) -> None:
        """Update chart X-axes based on current mode."""
        axis_pen = pg.mkPen(color=Colors.BG_BORDER)

        for plot_widget in (self._equity_plot, self._drawdown_plot):
            plot_item = plot_widget.getPlotItem()

            if self._axis_mode == AxisMode.DATE:
                # Switch to date axis with proper date format
                date_axis = DateAxisItem(orientation="bottom")
                date_axis.setPen(axis_pen)
                date_axis.setTextPen(pg.mkPen(color=Colors.TEXT_SECONDARY))
                # Set date format to show dates not times
                date_axis.setLabel(text="Date", **{
                    "font-family": Fonts.DATA,
                    "color": Colors.TEXT_SECONDARY,
                })
                plot_item.setAxisItems({"bottom": date_axis})
            else:
                # Switch to numeric axis
                numeric_axis = pg.AxisItem(orientation="bottom")
                numeric_axis.setPen(axis_pen)
                numeric_axis.setTextPen(pg.mkPen(color=Colors.TEXT_SECONDARY))
                plot_item.setAxisItems({"bottom": numeric_axis})
                plot_item.setLabel("bottom", "Trade #", **{
                    "font-family": Fonts.DATA,
                    "color": Colors.TEXT_SECONDARY,
                })

        # Replot curves with new X data
        self._replot_curves()

        # Auto-range to fit new data
        self._equity_plot.autoRange()
        self._drawdown_plot.autoRange()

    def _replot_curves(self) -> None:
        """Replot all curves with current axis mode's X values."""
        for name, df in self._data.items():
            x_data = self._get_x_data(df)
            if x_data is None:
                continue

            if name in self._equity_curves:
                self._equity_curves[name].setData(x=x_data, y=df["equity"].to_numpy())

            if name in self._drawdown_curves:
                drawdown_pct = self._calculate_drawdown_pct(df)
                self._drawdown_curves[name].setData(x=x_data, y=drawdown_pct)
