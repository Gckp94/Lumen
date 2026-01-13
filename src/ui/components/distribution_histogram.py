"""Distribution histogram component for winner/loser distributions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import pyqtgraph as pg  # type: ignore[import-untyped]
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.components.no_scroll_widgets import NoScrollComboBox
from src.ui.constants import Colors, Fonts, FontSizes, Spacing

if TYPE_CHECKING:
    from PyQt6.QtCore import QPointF

logger = logging.getLogger(__name__)


class DistributionHistogram(QWidget):
    """Histogram chart for distribution visualization with baseline overlay."""

    render_failed = pyqtSignal(str)

    # Bin size options: None = auto, otherwise percentage values
    BIN_SIZE_OPTIONS: dict[str, float | None] = {
        "Auto": None,
        "0.5%": 0.5,
        "1%": 1.0,
        "2%": 2.0,
        "5%": 5.0,
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the DistributionHistogram.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._current_bin_size: float | None = None
        self._baseline_gains: list[float] | None = None
        self._filtered_gains: list[float] | None = None
        self._baseline_mean: float | None = None
        self._baseline_median: float | None = None
        self._filtered_mean: float | None = None
        self._filtered_median: float | None = None

        # Bin data for tooltip
        self._baseline_bin_edges: np.ndarray | None = None
        self._filtered_bin_edges: np.ndarray | None = None
        self._baseline_counts: np.ndarray | None = None
        self._filtered_counts: np.ndarray | None = None

        self._setup_ui()
        self._setup_pyqtgraph()
        self._setup_bars()
        self._setup_reference_lines()
        self._setup_tooltip()
        self._setup_interactions()

    def _setup_ui(self) -> None:
        """Set up the layout."""
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
        plot_item.setLabel("left", "Count", **{
            "font-family": Fonts.DATA,
            "color": Colors.TEXT_SECONDARY,
        })
        plot_item.setLabel("bottom", "Gain %", **{
            "font-family": Fonts.DATA,
            "color": Colors.TEXT_SECONDARY,
        })

        self._layout.addWidget(self._plot_widget)

    def _setup_bars(self) -> None:
        """Set up baseline and filtered bar graph items."""
        # Baseline bars: SIGNAL_BLUE at 50% opacity (74, 158, 255, 128)
        self._baseline_bars = pg.BarGraphItem(
            x=[],
            height=[],
            width=0.8,
            brush=pg.mkBrush(74, 158, 255, 128),
        )
        self._plot_widget.addItem(self._baseline_bars)

        # Filtered bars: SIGNAL_CYAN at full opacity
        self._filtered_bars = pg.BarGraphItem(
            x=[],
            height=[],
            width=0.6,
            brush=pg.mkBrush(Colors.SIGNAL_CYAN),
        )
        self._plot_widget.addItem(self._filtered_bars)

    def _setup_reference_lines(self) -> None:
        """Set up mean and median reference lines."""
        # Mean line: dashed, SIGNAL_AMBER
        self._mean_line = pg.InfiniteLine(
            pos=0,
            angle=90,
            pen=pg.mkPen(color=Colors.SIGNAL_AMBER, style=Qt.PenStyle.DashLine, width=2),
        )
        self._mean_line.setVisible(False)
        self._plot_widget.addItem(self._mean_line)

        # Median line: dotted, TEXT_PRIMARY
        self._median_line = pg.InfiniteLine(
            pos=0,
            angle=90,
            pen=pg.mkPen(color=Colors.TEXT_PRIMARY, style=Qt.PenStyle.DotLine, width=2),
        )
        self._median_line.setVisible(False)
        self._plot_widget.addItem(self._median_line)

        # Add legend
        self._legend = self._plot_widget.addLegend(offset=(10, 10))
        # Create dummy plots for legend entries
        self._mean_legend_item = self._plot_widget.plot(
            [], [],
            pen=pg.mkPen(color=Colors.SIGNAL_AMBER, style=Qt.PenStyle.DashLine, width=2),
            name="Mean",
        )
        self._median_legend_item = self._plot_widget.plot(
            [], [],
            pen=pg.mkPen(color=Colors.TEXT_PRIMARY, style=Qt.PenStyle.DotLine, width=2),
            name="Median",
        )

    def _setup_tooltip(self) -> None:
        """Set up tooltip for bar hover."""
        self._tooltip = pg.TextItem(
            text="",
            color=Colors.TEXT_SECONDARY,
            anchor=(0, 1),
        )
        self._tooltip.setVisible(False)
        self._plot_widget.addItem(self._tooltip)

    def _setup_interactions(self) -> None:
        """Set up mouse interaction handlers."""
        self._plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)

    def _calculate_bins(
        self, data: list[float], bin_size: float | None
    ) -> tuple[np.ndarray, np.ndarray]:
        """Calculate histogram bins.

        Args:
            data: List of gain percentages.
            bin_size: Fixed bin size or None for auto.

        Returns:
            Tuple of (bin_edges, counts) arrays.
        """
        if not data:
            return np.array([]), np.array([])

        try:
            data_array = np.array(data)

            # Auto bin using Freedman-Diaconis rule if bin_size is None
            bin_width = (
                self._calculate_auto_bin_width(data_array) if bin_size is None else bin_size
            )

            # Calculate bin edges
            data_min = np.min(data_array)
            data_max = np.max(data_array)

            # Extend range slightly to include edge values
            bin_start = np.floor(data_min / bin_width) * bin_width
            bin_end = np.ceil(data_max / bin_width) * bin_width + bin_width

            bins = np.arange(bin_start, bin_end, bin_width)

            # Ensure at least 2 bin edges
            if len(bins) < 2:
                bins = np.array([data_min - 0.5, data_max + 0.5])

            counts, bin_edges = np.histogram(data_array, bins=bins)

            return bin_edges, counts

        except Exception as e:
            logger.exception("Error calculating bins: %s", e)
            self.render_failed.emit(f"Binning error: {e}")
            return np.array([]), np.array([])

    def _calculate_auto_bin_width(self, data: np.ndarray) -> float:
        """Calculate optimal bin width using Freedman-Diaconis rule.

        Handles edge cases:
        - IQR=0 (all identical or near-identical values): use range-based fallback
        - Range=0 (single unique value): use 1.0 as minimum bin width

        Args:
            data: numpy array of data values.

        Returns:
            Calculated bin width.
        """
        if len(data) == 0:
            return 1.0

        iqr = np.percentile(data, 75) - np.percentile(data, 25)
        n = len(data)

        if iqr > 0:
            return float(2 * iqr / (n ** (1 / 3)))

        # IQR=0 fallback: use range-based calculation
        data_range = np.max(data) - np.min(data)
        if data_range > 0:
            return float(data_range / 10)  # 10 bins across the range

        return 1.0  # Absolute fallback for single-value data

    def _update_bars(self) -> None:
        """Update bar graph items with current data."""
        # Update baseline bars
        if self._baseline_gains:
            self._baseline_bin_edges, self._baseline_counts = self._calculate_bins(
                self._baseline_gains, self._current_bin_size
            )
            if len(self._baseline_bin_edges) > 1:
                bin_centers = (
                    self._baseline_bin_edges[:-1] + self._baseline_bin_edges[1:]
                ) / 2
                width = self._baseline_bin_edges[1] - self._baseline_bin_edges[0]
                self._baseline_bars.setOpts(
                    x=bin_centers,
                    height=self._baseline_counts,
                    width=width * 0.8,
                )
            else:
                self._baseline_bars.setOpts(x=[], height=[], width=0.8)
        else:
            self._baseline_bin_edges = None
            self._baseline_counts = None
            self._baseline_bars.setOpts(x=[], height=[], width=0.8)

        # Update filtered bars
        if self._filtered_gains:
            self._filtered_bin_edges, self._filtered_counts = self._calculate_bins(
                self._filtered_gains, self._current_bin_size
            )
            if len(self._filtered_bin_edges) > 1:
                bin_centers = (
                    self._filtered_bin_edges[:-1] + self._filtered_bin_edges[1:]
                ) / 2
                width = self._filtered_bin_edges[1] - self._filtered_bin_edges[0]
                self._filtered_bars.setOpts(
                    x=bin_centers,
                    height=self._filtered_counts,
                    width=width * 0.6,
                )
            else:
                self._filtered_bars.setOpts(x=[], height=[], width=0.6)
        else:
            self._filtered_bin_edges = None
            self._filtered_counts = None
            self._filtered_bars.setOpts(x=[], height=[], width=0.6)

        # Update reference lines
        self._update_reference_lines()

        # Auto-range view
        self._plot_widget.autoRange()

        baseline_count = len(self._baseline_counts) if self._baseline_counts is not None else 0
        filtered_count = len(self._filtered_counts) if self._filtered_counts is not None else 0
        logger.debug(
            "DistributionHistogram updated: %d baseline, %d filtered bars",
            baseline_count,
            filtered_count,
        )

    def _update_reference_lines(self) -> None:
        """Update mean and median line positions."""
        # Use filtered stats if available, otherwise baseline
        mean_val = self._filtered_mean if self._filtered_mean is not None else self._baseline_mean
        median_val = (
            self._filtered_median if self._filtered_median is not None else self._baseline_median
        )

        if mean_val is not None:
            self._mean_line.setPos(mean_val)
            self._mean_line.setVisible(True)
        else:
            self._mean_line.setVisible(False)

        if median_val is not None:
            self._median_line.setPos(median_val)
            self._median_line.setVisible(True)
        else:
            self._median_line.setVisible(False)

    def _on_mouse_moved(self, pos: QPointF) -> None:
        """Handle mouse movement for tooltip display.

        Args:
            pos: Mouse position in scene coordinates.
        """
        try:
            # Convert scene coordinates to view coordinates
            view_box = self._plot_widget.getViewBox()
            mouse_point = view_box.mapSceneToView(pos)
            x, y = mouse_point.x(), mouse_point.y()

            # Check which bar the mouse is over
            tooltip_text = self._get_bar_tooltip(x, y)

            if tooltip_text:
                self._tooltip.setText(tooltip_text)
                self._tooltip.setPos(x, y)

                # Adjust anchor based on position to prevent edge clipping
                view_range = view_box.viewRange()
                x_mid = (view_range[0][0] + view_range[0][1]) / 2
                if x > x_mid:
                    self._tooltip.setAnchor((1, 1))
                else:
                    self._tooltip.setAnchor((0, 1))

                self._tooltip.setVisible(True)
            else:
                self._tooltip.setVisible(False)

        except Exception as e:
            logger.debug("Error in mouse move handler: %s", e)
            self._tooltip.setVisible(False)

    def _get_bar_tooltip(self, x: float, y: float) -> str | None:
        """Get tooltip text for bar at position.

        Args:
            x: X position in data coordinates.
            y: Y position in data coordinates.

        Returns:
            Tooltip text or None if not over a bar.
        """
        # Check filtered bars first (they're on top)
        if self._filtered_bin_edges is not None and self._filtered_counts is not None:
            for i in range(len(self._filtered_counts)):
                bin_left = self._filtered_bin_edges[i]
                bin_right = self._filtered_bin_edges[i + 1]
                count = self._filtered_counts[i]
                if bin_left <= x < bin_right and 0 <= y <= count:
                    return f"Bin: {bin_left:.1f}% to {bin_right:.1f}%, Count: {count}"

        # Check baseline bars
        if self._baseline_bin_edges is not None and self._baseline_counts is not None:
            for i in range(len(self._baseline_counts)):
                bin_left = self._baseline_bin_edges[i]
                bin_right = self._baseline_bin_edges[i + 1]
                count = self._baseline_counts[i]
                if bin_left <= x < bin_right and 0 <= y <= count:
                    return f"Bin: {bin_left:.1f}% to {bin_right:.1f}%, Count: {count}"

        return None

    def set_bin_size(self, bin_size: float | None) -> None:
        """Set the bin size and re-bin data.

        Args:
            bin_size: Bin size in percentage points, or None for auto.
        """
        self._current_bin_size = bin_size
        self._update_bars()

    def set_baseline(
        self,
        gains: list[float] | None,
        mean: float | None,
        median: float | None,
    ) -> None:
        """Set baseline distribution data.

        Args:
            gains: List of gain percentages or None to clear.
            mean: Mean value for reference line.
            median: Median value for reference line.
        """
        self._baseline_gains = gains
        self._baseline_mean = mean
        self._baseline_median = median
        self._update_bars()

    def set_filtered(
        self,
        gains: list[float] | None,
        mean: float | None,
        median: float | None,
    ) -> None:
        """Set filtered distribution data.

        Args:
            gains: List of gain percentages or None to hide.
            mean: Mean value for reference line.
            median: Median value for reference line.
        """
        self._filtered_gains = gains
        self._filtered_mean = mean
        self._filtered_median = median
        self._update_bars()

    def set_baseline_visible(self, visible: bool) -> None:
        """Show or hide baseline bars.

        Args:
            visible: Whether baseline should be visible.
        """
        self._baseline_bars.setVisible(visible)

    def clear(self) -> None:
        """Clear all data from the histogram."""
        self._baseline_gains = None
        self._filtered_gains = None
        self._baseline_mean = None
        self._baseline_median = None
        self._filtered_mean = None
        self._filtered_median = None
        self._baseline_bin_edges = None
        self._filtered_bin_edges = None
        self._baseline_counts = None
        self._filtered_counts = None
        self._update_bars()


class _HistogramPanel(QWidget):
    """Container widget with title, controls, and histogram chart."""

    def __init__(
        self,
        card_type: str,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the histogram panel.

        Args:
            card_type: "winner" or "loser".
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._card_type = card_type.lower()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # Title
        title_text = "Winner Distribution" if self._card_type == "winner" else "Loser Distribution"
        title_color = Colors.SIGNAL_CYAN if self._card_type == "winner" else Colors.SIGNAL_CORAL
        self._title_label = QLabel(title_text)
        self._title_label.setStyleSheet(f"""
            QLabel {{
                font-family: {Fonts.UI};
                font-size: {FontSizes.H2}px;
                color: {title_color};
                font-weight: bold;
            }}
        """)
        layout.addWidget(self._title_label)

        # Controls row
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(Spacing.MD)

        # Binning dropdown
        self._bin_combo = NoScrollComboBox()
        for label in DistributionHistogram.BIN_SIZE_OPTIONS:
            self._bin_combo.addItem(label)
        self._bin_combo.setCurrentText("Auto")
        self._bin_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 80px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {Colors.TEXT_SECONDARY};
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                selection-background-color: {Colors.BG_BORDER};
                selection-color: {Colors.TEXT_PRIMARY};
            }}
        """)
        self._bin_combo.currentIndexChanged.connect(self._on_bin_size_changed)
        controls_layout.addWidget(QLabel("Bin Size:"))
        controls_layout.addWidget(self._bin_combo)

        # Show baseline checkbox
        self._baseline_checkbox = QCheckBox("Show Baseline")
        self._baseline_checkbox.setChecked(True)
        self._baseline_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {Colors.TEXT_PRIMARY};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 3px;
                background-color: {Colors.BG_ELEVATED};
            }}
            QCheckBox::indicator:checked {{
                background-color: {Colors.SIGNAL_BLUE};
                border-color: {Colors.SIGNAL_BLUE};
            }}
        """)
        self._baseline_checkbox.toggled.connect(self._on_show_baseline_toggled)
        controls_layout.addWidget(self._baseline_checkbox)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Histogram chart
        self._histogram = DistributionHistogram()
        layout.addWidget(self._histogram, stretch=1)

    def _on_bin_size_changed(self, index: int) -> None:
        """Handle bin size dropdown change.

        Args:
            index: Selected index.
        """
        label = self._bin_combo.currentText()
        bin_size = DistributionHistogram.BIN_SIZE_OPTIONS.get(label)
        self._histogram.set_bin_size(bin_size)

    def _on_show_baseline_toggled(self, checked: bool) -> None:
        """Handle show baseline checkbox toggle.

        Args:
            checked: Whether checkbox is checked.
        """
        self._histogram.set_baseline_visible(checked)

    def set_baseline(
        self,
        gains: list[float] | None,
        mean: float | None,
        median: float | None,
    ) -> None:
        """Set baseline data.

        Args:
            gains: Baseline gain values.
            mean: Baseline mean.
            median: Baseline median.
        """
        self._histogram.set_baseline(gains, mean, median)

    def set_filtered(
        self,
        gains: list[float] | None,
        mean: float | None,
        median: float | None,
    ) -> None:
        """Set filtered data.

        Args:
            gains: Filtered gain values.
            mean: Filtered mean.
            median: Filtered median.
        """
        self._histogram.set_filtered(gains, mean, median)


class HistogramDialog(QDialog):
    """Modal dialog displaying distribution histogram."""

    def __init__(
        self,
        card_type: str,
        baseline_gains: list[float],
        filtered_gains: list[float] | None,
        baseline_mean: float | None,
        baseline_median: float | None,
        filtered_mean: float | None = None,
        filtered_median: float | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the histogram dialog.

        Args:
            card_type: "winner" or "loser".
            baseline_gains: Baseline distribution data.
            filtered_gains: Filtered distribution data (optional).
            baseline_mean: Baseline mean value.
            baseline_median: Baseline median value.
            filtered_mean: Filtered mean value (optional).
            filtered_median: Filtered median value (optional).
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._card_type = card_type.lower()

        # Set dialog properties
        title = "Winner Distribution" if self._card_type == "winner" else "Loser Distribution"
        self.setWindowTitle(title)
        self.setMinimumSize(600, 400)

        # Apply Observatory styling
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_ELEVATED};
            }}
        """)

        self._setup_ui()

        # Set data
        self._panel.set_baseline(baseline_gains, baseline_mean, baseline_median)
        if filtered_gains:
            self._panel.set_filtered(filtered_gains, filtered_mean, filtered_median)

    def _setup_ui(self) -> None:
        """Set up the dialog layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, Spacing.LG)
        layout.setSpacing(0)

        # Add histogram panel
        self._panel = _HistogramPanel(self._card_type)
        layout.addWidget(self._panel, stretch=1)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_BORDER};
                color: {Colors.TEXT_PRIMARY};
                border: none;
                border-radius: 4px;
                padding: 8px 24px;
                font-family: {Fonts.UI};
            }}
            QPushButton:hover {{
                background-color: {Colors.SIGNAL_BLUE};
            }}
        """)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        button_layout.addSpacing(Spacing.LG)
        layout.addLayout(button_layout)
