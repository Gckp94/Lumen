"""Monte Carlo charts section for distribution visualization.

Provides a container with all Monte Carlo charts including confidence bands,
equity distribution, drawdown distribution, and risk metric histograms.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.export_manager import ExportManager
from src.ui.components.equity_confidence_chart import EquityConfidenceBandChart
from src.ui.components.mc_histogram import MonteCarloHistogram
from src.ui.components.toast import Toast
from src.ui.constants import Colors, Fonts, FontSizes, Spacing
from src.ui.dialogs.chart_expand_dialog import ChartExpandDialog

if TYPE_CHECKING:
    from src.core.monte_carlo import MonteCarloResults

logger = logging.getLogger(__name__)


class ChartPanel(QWidget):
    """Container widget for a chart with header, expand and export buttons.

    Wraps any chart widget with a consistent header bar containing
    the chart title and action buttons.
    """

    expand_requested = pyqtSignal()
    export_requested = pyqtSignal()

    def __init__(
        self,
        title: str,
        chart_widget: QWidget,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the ChartPanel.

        Args:
            title: Chart title to display.
            chart_widget: The chart widget to wrap.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._title = title
        self._chart_widget = chart_widget
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.XS)

        # Header row with title and buttons
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(Spacing.SM)

        # Title label
        title_label = QLabel(self._title)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
                font-weight: bold;
            }}
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # Button style
        btn_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: none;
                padding: 4px 8px;
                font-family: {Fonts.UI};
                font-size: 11px;
            }}
            QPushButton:hover {{
                color: {Colors.TEXT_PRIMARY};
                background-color: {Colors.BG_BORDER};
                border-radius: 4px;
            }}
        """

        # Expand button
        expand_btn = QPushButton("⤢")
        expand_btn.setToolTip("Expand to full screen")
        expand_btn.setFixedSize(28, 24)
        expand_btn.setStyleSheet(btn_style)
        expand_btn.clicked.connect(self.expand_requested.emit)
        header_layout.addWidget(expand_btn)

        # Export button
        export_btn = QPushButton("↓")
        export_btn.setToolTip("Export as PNG")
        export_btn.setFixedSize(28, 24)
        export_btn.setStyleSheet(btn_style)
        export_btn.clicked.connect(self.export_requested.emit)
        header_layout.addWidget(export_btn)

        layout.addWidget(header)

        # Chart widget
        layout.addWidget(self._chart_widget, stretch=1)

    @property
    def chart(self) -> QWidget:
        """Get the wrapped chart widget."""
        return self._chart_widget


class MonteCarloChartsSection(QWidget):
    """Container for all Monte Carlo distribution charts.

    Displays equity confidence bands, final equity histogram,
    max drawdown histogram, and risk metric histograms in a
    responsive grid layout.

    Implements lazy rendering - charts only render when visible.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the MonteCarloChartsSection.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._results: MonteCarloResults | None = None
        self._rendered = False
        self._export_manager = ExportManager()
        self._setup_ui()
        self._setup_charts()

    def _setup_ui(self) -> None:
        """Set up the section layout."""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(Spacing.MD)

    def _setup_charts(self) -> None:
        """Create and configure all chart widgets with tabbed layout."""
        from src.ui.components.tabbed_chart_container import TabbedChartContainer

        # Create tabbed container
        self._chart_tabs = TabbedChartContainer()
        self._layout.addWidget(self._chart_tabs, stretch=1)

        # 1. Equity Confidence Band Chart
        self._equity_confidence_chart = EquityConfidenceBandChart()
        self._equity_confidence_chart.setMinimumHeight(350)
        self._equity_confidence_panel = ChartPanel(
            "",  # No title needed, tab has the name
            self._equity_confidence_chart,
        )
        self._equity_confidence_panel.expand_requested.connect(
            lambda: self._expand_chart(
                self._equity_confidence_chart, "Equity Curve Confidence Bands"
            )
        )
        self._equity_confidence_panel.export_requested.connect(
            lambda: self._export_chart(self._equity_confidence_chart, "equity_confidence")
        )
        self._chart_tabs.add_tab("Equity Curve", self._equity_confidence_panel)

        # 2. Final Equity Distribution
        self._final_equity_hist = MonteCarloHistogram(
            title="",
            color_gradient=False,
            x_format="dollar",
        )
        self._final_equity_hist.setMinimumHeight(350)
        self._final_equity_panel = ChartPanel("", self._final_equity_hist)
        self._final_equity_panel.expand_requested.connect(
            lambda: self._expand_chart(self._final_equity_hist, "Final Equity Distribution")
        )
        self._final_equity_panel.export_requested.connect(
            lambda: self._export_chart(self._final_equity_hist, "final_equity_dist")
        )
        self._chart_tabs.add_tab("Final Equity", self._final_equity_panel)

        # 3. Max Drawdown Distribution
        self._max_dd_hist = MonteCarloHistogram(
            title="",
            color_gradient=True,
            x_format="percent",
        )
        self._max_dd_hist.setMinimumHeight(350)
        self._max_dd_panel = ChartPanel("", self._max_dd_hist)
        self._max_dd_panel.expand_requested.connect(
            lambda: self._expand_chart(self._max_dd_hist, "Max Drawdown Distribution")
        )
        self._max_dd_panel.export_requested.connect(
            lambda: self._export_chart(self._max_dd_hist, "max_dd_dist")
        )
        self._chart_tabs.add_tab("Max Drawdown", self._max_dd_panel)

        # 4. Sharpe Ratio Distribution
        self._sharpe_hist = MonteCarloHistogram(
            title="",
            color_gradient=False,
            x_format="ratio",
        )
        self._sharpe_hist.setMinimumHeight(350)
        self._sharpe_panel = ChartPanel("", self._sharpe_hist)
        self._sharpe_panel.expand_requested.connect(
            lambda: self._expand_chart(self._sharpe_hist, "Sharpe Ratio Distribution")
        )
        self._sharpe_panel.export_requested.connect(
            lambda: self._export_chart(self._sharpe_hist, "sharpe_dist")
        )
        self._chart_tabs.add_tab("Sharpe Ratio", self._sharpe_panel)

        # 5. Profit Factor Distribution
        self._profit_factor_hist = MonteCarloHistogram(
            title="",
            color_gradient=False,
            x_format="ratio",
        )
        self._profit_factor_hist.setMinimumHeight(350)
        self._profit_factor_panel = ChartPanel("", self._profit_factor_hist)
        self._profit_factor_panel.expand_requested.connect(
            lambda: self._expand_chart(self._profit_factor_hist, "Profit Factor Distribution")
        )
        self._profit_factor_panel.export_requested.connect(
            lambda: self._export_chart(self._profit_factor_hist, "profit_factor_dist")
        )
        self._chart_tabs.add_tab("Profit Factor", self._profit_factor_panel)

        # 6. Recovery Factor Distribution
        self._recovery_factor_hist = MonteCarloHistogram(
            title="",
            color_gradient=False,
            x_format="ratio",
        )
        self._recovery_factor_hist.setMinimumHeight(350)
        self._recovery_factor_panel = ChartPanel("", self._recovery_factor_hist)
        self._recovery_factor_panel.expand_requested.connect(
            lambda: self._expand_chart(self._recovery_factor_hist, "Recovery Factor Distribution")
        )
        self._recovery_factor_panel.export_requested.connect(
            lambda: self._export_chart(self._recovery_factor_hist, "recovery_factor_dist")
        )
        self._chart_tabs.add_tab("Recovery Factor", self._recovery_factor_panel)

    def _expand_chart(self, chart: QWidget, title: str) -> None:
        """Open chart in expanded fullscreen dialog.

        Args:
            chart: The chart widget to expand.
            title: Title for the dialog.
        """
        # Create a copy/reference of the chart data to display in modal
        # For now, we'll show the original (note: moves widget temporarily)
        dialog = ChartExpandDialog(chart, title, self)
        dialog.exec()

        # After dialog closes, restore chart to original layout
        # This happens automatically via ChartExpandDialog.closeEvent

    def _export_chart(self, chart: QWidget, chart_name: str) -> None:
        """Export chart to PNG file.

        Args:
            chart: The chart widget to export.
            chart_name: Name for the exported file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"lumen_mc_{chart_name}_{timestamp}.png"

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Chart",
            default_name,
            "PNG Files (*.png)",
        )

        if path:
            try:
                self._export_manager.chart_to_png(
                    chart,
                    Path(path),
                    (1920, 1080),
                )
                Toast.display(self, "Chart exported successfully", "success")
                logger.info("Exported chart to %s", path)
            except Exception as e:
                Toast.display(self, f"Export failed: {e}", "error")
                logger.error("Chart export failed: %s", e)

    def update_from_results(self, results: MonteCarloResults) -> None:
        """Update all charts from Monte Carlo results.

        Args:
            results: Results from Monte Carlo simulation.
        """
        self._results = results
        self._rendered = False

        # Use deferred rendering for performance
        QTimer.singleShot(0, self._render_charts)

    def _render_charts(self) -> None:
        """Render all charts with current results data."""
        if self._results is None:
            return

        results = self._results

        # 1. Equity Confidence Band Chart
        if results.equity_percentiles is not None and len(results.equity_percentiles) > 0:
            self._equity_confidence_chart.set_data(results.equity_percentiles)

        # 2. Final Equity Distribution
        if results.final_equity_distribution is not None:
            mean_val = results.mean_final_equity
            median_val = np.median(results.final_equity_distribution)
            self._final_equity_hist.set_data(
                results.final_equity_distribution,
                mean=mean_val,
                median=median_val,
            )
            # Add confidence interval shading (5th-95th)
            self._final_equity_hist.add_confidence_shading(
                results.p5_final_equity,
                results.p95_final_equity,
            )

        # 3. Max Drawdown Distribution (with gradient coloring)
        if results.max_dd_distribution is not None:
            # Convert to percentages for display
            dd_pct = results.max_dd_distribution * 100
            median_dd = results.median_max_dd * 100
            p95_dd = results.p95_max_dd * 100
            p99_dd = results.p99_max_dd * 100

            self._max_dd_hist.set_data(
                dd_pct,
                median=median_dd,
                percentiles={"50th": median_dd, "95th": p95_dd, "99th": p99_dd},
            )

        # 4. Sharpe Ratio Distribution
        if results.sharpe_distribution is not None:
            mean_sharpe = results.mean_sharpe
            median_sharpe = np.median(results.sharpe_distribution)
            self._sharpe_hist.set_data(
                results.sharpe_distribution,
                mean=mean_sharpe,
                median=median_sharpe,
            )
            # Add reference line at 1.0
            self._sharpe_hist.set_reference_line(1.0, "good_threshold")
            # Color by reference
            self._sharpe_hist.set_color_by_reference(1.0)

        # 5. Profit Factor Distribution
        if results.profit_factor_distribution is not None:
            mean_pf = results.mean_profit_factor
            median_pf = np.median(results.profit_factor_distribution)
            self._profit_factor_hist.set_data(
                results.profit_factor_distribution,
                mean=mean_pf,
                median=median_pf,
            )
            # Add reference line at 1.0 (breakeven)
            self._profit_factor_hist.set_reference_line(1.0, "breakeven")
            # Color by reference
            self._profit_factor_hist.set_color_by_reference(1.0)

        # 6. Recovery Factor Distribution
        if results.recovery_factor_distribution is not None:
            mean_rf = results.mean_recovery_factor
            median_rf = np.median(results.recovery_factor_distribution)
            self._recovery_factor_hist.set_data(
                results.recovery_factor_distribution,
                mean=mean_rf,
                median=median_rf,
            )

        self._rendered = True
        logger.debug("MonteCarloChartsSection rendered")

    def clear(self) -> None:
        """Clear all chart data."""
        self._results = None
        self._rendered = False
        self._equity_confidence_chart.clear()
        self._final_equity_hist.clear()
        self._max_dd_hist.clear()
        self._sharpe_hist.clear()
        self._profit_factor_hist.clear()
        self._recovery_factor_hist.clear()

    def showEvent(self, event) -> None:
        """Handle widget becoming visible.

        Args:
            event: The show event.
        """
        super().showEvent(event)
        # Lazy render if we have data but haven't rendered yet
        if self._results is not None and not self._rendered:
            QTimer.singleShot(0, self._render_charts)
