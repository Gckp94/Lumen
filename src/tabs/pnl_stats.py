"""P&L Stats tab for metrics and comparison.

This is the third tab in the workflow where users view performance
metrics and charts.
"""

import logging
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.app_state import AppState
from src.core.export_manager import ExportManager
from src.core.metrics import MetricsCalculator, calculate_suggested_bins
from src.core.models import AdjustmentParams, MetricsUserInputs, TradingMetrics
from src.ui.components import (
    CalculationStatusIndicator,
    ComparisonGridHorizontal,
    ComparisonRibbon,
    EmptyState,
    UserInputsPanel,
)
from src.ui.components.distribution_card import DistributionCard
from src.ui.components.distribution_histogram import HistogramDialog
from src.ui.components.equity_chart import _ChartPanel
from src.ui.components.export_dialog import ExportCategory, ExportDialog, ExportFormat
from src.ui.constants import Animation, Colors, Fonts, FontSizes, Spacing
from src.ui.mixins.background_calculation import BackgroundCalculationMixin

logger = logging.getLogger(__name__)


class PnLStatsTab(BackgroundCalculationMixin, QWidget):
    """Tab for PnL metrics and trading statistics.

    Layout structure:
    - Top: UserInputsPanel (fixed ~120px)
    - Middle: MetricsGrid or EmptyState (stretches)
    - Bottom: Charts placeholder (fixed ~200px)

    Attributes:
        _app_state: Reference to centralized app state.
        _user_inputs_panel: Panel for user input configuration.
        _metrics_stack: Stacked widget for metrics (empty state / grid).
        _metrics_empty: Empty state shown when no data.
        _comparison_grid: Grid showing calculated metrics with baseline/filtered comparison.
        _charts_placeholder: Placeholder for charts.
        _recalc_timer: Timer for debouncing recalculations.
    """

    def __init__(
        self, app_state: AppState, parent: QWidget | None = None
    ) -> None:
        """Initialize the PnL Stats tab.

        Args:
            app_state: Centralized application state.
            parent: Optional parent widget.
        """
        QWidget.__init__(self, parent)
        BackgroundCalculationMixin.__init__(self, app_state, "PnL Stats")
        self._metrics_calculator = MetricsCalculator()
        self._filtered_df_hash: str | None = None  # Track filtered DataFrame state
        self._setup_ui()
        self._setup_background_calculation()
        self._setup_recalc_timer()
        self._setup_filtered_equity_timer()
        self._connect_signals()
        self._initialize_from_state()

    def _setup_ui(self) -> None:
        """Set up the three-section layout."""
        self.setObjectName("pnlStatsTab")
        self.setStyleSheet(f"""
            QWidget#pnlStatsTab {{
                background-color: {Colors.BG_SURFACE};
            }}
            QLabel.sectionHeader {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.UI};
                font-size: {FontSizes.H2}px;
                font-weight: bold;
            }}
        """)

        # Create outer layout for the tab
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {Colors.BG_SURFACE};
                border: none;
            }}
        """)

        # Create content widget
        content_widget = QWidget()
        content_widget.setObjectName("pnlStatsContent")

        # Move the main_layout to be on content_widget instead of self
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        main_layout.setSpacing(Spacing.LG)

        # Top row: Configuration header + Status indicator
        top_row_layout = QHBoxLayout()
        inputs_header = QLabel("Configuration")
        inputs_header.setProperty("class", "sectionHeader")
        top_row_layout.addWidget(inputs_header)
        top_row_layout.addStretch()

        # Export button with dropdown menu
        self._export_btn = self._create_export_button()
        top_row_layout.addWidget(self._export_btn)

        # Calculation status indicator (top-right)
        self._status_indicator = CalculationStatusIndicator(self._app_state)
        top_row_layout.addWidget(self._status_indicator)
        main_layout.addLayout(top_row_layout)

        self._user_inputs_panel = UserInputsPanel()
        self._user_inputs_panel.setFixedHeight(100)
        main_layout.addWidget(self._user_inputs_panel)

        # Middle section: Metrics Grid with QStackedWidget
        metrics_header = QLabel("Trading Metrics")
        metrics_header.setProperty("class", "sectionHeader")
        main_layout.addWidget(metrics_header)

        self._metrics_stack = QStackedWidget()

        # Index 0: EmptyState (shown when no data)
        self._metrics_empty = EmptyState()
        self._metrics_empty.set_message(
            icon="📊",
            title="No Metrics Yet",
            description="Metrics will appear here after data is loaded and configured",
        )
        self._metrics_stack.addWidget(self._metrics_empty)

        # Index 1: ComparisonGridHorizontal (shown when data is available)
        self._comparison_grid = ComparisonGridHorizontal()
        self._metrics_stack.addWidget(self._comparison_grid)

        main_layout.addWidget(self._metrics_stack, stretch=1)

        # Distribution Cards section (side by side)
        dist_header = QLabel("Distribution Statistics")
        dist_header.setProperty("class", "sectionHeader")
        main_layout.addWidget(dist_header)

        dist_layout = QHBoxLayout()
        dist_layout.setSpacing(Spacing.LG)

        self._winner_dist_card = DistributionCard(DistributionCard.WINNER)
        self._loser_dist_card = DistributionCard(DistributionCard.LOSER)

        dist_layout.addWidget(self._winner_dist_card)
        dist_layout.addWidget(self._loser_dist_card)
        main_layout.addLayout(dist_layout)

        # Bottom section: Equity Charts
        charts_header = QLabel("Charts")
        charts_header.setProperty("class", "sectionHeader")
        main_layout.addWidget(charts_header)

        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(Spacing.LG)

        self._flat_stake_chart_panel = _ChartPanel("Flat Stake PnL")
        self._kelly_chart_panel = _ChartPanel("Compounded Kelly PnL")

        charts_layout.addWidget(self._flat_stake_chart_panel)
        charts_layout.addWidget(self._kelly_chart_panel)
        main_layout.addLayout(charts_layout, stretch=1)

        # Comparison Ribbon at TOP (Story 4.2) - insert at indices 0-1
        comparison_header = QLabel("Comparison")
        comparison_header.setProperty("class", "sectionHeader")
        self._comparison_ribbon = ComparisonRibbon()
        main_layout.insertWidget(0, comparison_header)
        main_layout.insertWidget(1, self._comparison_ribbon)

        # Wire up the scroll area
        scroll_area.setWidget(content_widget)
        outer_layout.addWidget(scroll_area)

    def _create_export_button(self) -> QPushButton:
        """Create export dropdown button."""
        btn = QPushButton("Export")
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                font-family: "{Fonts.UI}";
                font-size: {FontSizes.BODY}px;
                padding: {Spacing.SM}px {Spacing.MD}px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border-color: {Colors.TEXT_SECONDARY};
            }}
            QPushButton::menu-indicator {{
                subcontrol-position: right center;
                subcontrol-origin: padding;
                right: {Spacing.SM}px;
            }}
        """)

        menu = QMenu(btn)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                font-family: "{Fonts.UI}";
                font-size: {FontSizes.BODY}px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: {Spacing.XS}px;
            }}
            QMenu::item {{
                padding: {Spacing.SM}px {Spacing.MD}px;
                border-radius: 2px;
            }}
            QMenu::item:selected {{
                background-color: {Colors.BG_SURFACE};
            }}
            QMenu::item:disabled {{
                color: {Colors.TEXT_DISABLED};
            }}
        """)

        data_action = menu.addAction("Export Data...")
        data_action.triggered.connect(self._on_export_data_clicked)

        charts_action = menu.addAction("Export Charts...")
        charts_action.triggered.connect(self._on_export_charts_clicked)

        report_action = menu.addAction("Export Report...")
        report_action.setEnabled(False)  # Deferred to future story

        btn.setMenu(menu)
        return btn

    def _on_export_data_clicked(self) -> None:
        """Handle Export Data menu action."""
        dialog = ExportDialog(self)
        dialog.set_category(ExportCategory.DATA)
        if dialog.exec():
            self._execute_data_export(dialog)

    def _on_export_charts_clicked(self) -> None:
        """Handle Export Charts menu action."""
        dialog = ExportDialog(self)
        dialog.set_category(ExportCategory.CHARTS)
        if dialog.exec():
            self._execute_chart_export(dialog)

    def _execute_data_export(self, dialog: ExportDialog) -> None:
        """Execute data export based on dialog selection.

        Args:
            dialog: The export dialog with user selections
        """
        export_format = dialog.selected_format
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if export_format == ExportFormat.CSV:
            self._export_data_csv(timestamp)
        elif export_format == ExportFormat.EXCEL:
            self._export_data_excel(timestamp)
        elif export_format == ExportFormat.PARQUET:
            self._export_data_parquet(timestamp)
        elif export_format == ExportFormat.METRICS_CSV:
            self._export_metrics_csv(timestamp)

    def _export_data_csv(self, timestamp: str) -> None:
        """Export filtered data to CSV.

        Args:
            timestamp: Timestamp for filename
        """
        default_name = f"lumen_export_{timestamp}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Data as CSV",
            default_name,
            "CSV Files (*.csv)",
        )

        if not path:
            return

        df = self._app_state.filtered_df
        if df is None:
            df = self._app_state.raw_df

        if df is None:
            return

        filters = self._app_state.filters
        first_trigger = self._app_state.first_trigger_enabled
        total_rows = len(self._app_state.raw_df) if self._app_state.raw_df is not None else None

        export_manager = ExportManager()
        try:
            export_manager.to_csv(
                df,
                Path(path),
                filters=filters,
                first_trigger_enabled=first_trigger,
                total_rows=total_rows,
            )
            from src.ui.components.toast import Toast

            Toast.display(self, "Export complete", "success")
        except Exception as e:
            from src.ui.components.toast import Toast

            Toast.display(self, f"Export failed: {e}", "error", duration=5000)
            logger.error("CSV export failed: %s", e)

    def _export_data_excel(self, timestamp: str) -> None:
        """Export filtered data to Excel.

        Args:
            timestamp: Timestamp for filename
        """
        default_name = f"lumen_export_{timestamp}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Data as Excel",
            default_name,
            "Excel Files (*.xlsx)",
        )

        if not path:
            return

        df = self._app_state.filtered_df
        if df is None:
            df = self._app_state.raw_df

        if df is None:
            return

        filters = self._app_state.filters
        first_trigger = self._app_state.first_trigger_enabled
        total_rows = len(self._app_state.raw_df) if self._app_state.raw_df is not None else None

        export_manager = ExportManager()
        try:
            export_manager.to_excel(
                df,
                Path(path),
                filters=filters,
                first_trigger_enabled=first_trigger,
                total_rows=total_rows,
            )
            from src.ui.components.toast import Toast

            Toast.display(self, "Export complete", "success")
        except Exception as e:
            from src.ui.components.toast import Toast

            Toast.display(self, f"Export failed: {e}", "error", duration=5000)
            logger.error("Excel export failed: %s", e)

    def _export_data_parquet(self, timestamp: str) -> None:
        """Export filtered data to Parquet.

        Args:
            timestamp: Timestamp for filename
        """
        default_name = f"lumen_export_{timestamp}.parquet"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Data as Parquet",
            default_name,
            "Parquet Files (*.parquet)",
        )

        if not path:
            return

        df = self._app_state.filtered_df
        if df is None:
            df = self._app_state.raw_df

        if df is None:
            return

        # Build metadata
        metadata = {
            "lumen_export": "true",
            "export_timestamp": datetime.now().isoformat(),
            "first_trigger": "ON" if self._app_state.first_trigger_enabled else "OFF",
            "row_count": str(len(df)),
        }

        if self._app_state.raw_df is not None:
            metadata["total_rows"] = str(len(self._app_state.raw_df))

        if self._app_state.filters:
            filter_strs = [
                f"{f.column} {f.operator} [{f.min_val}, {f.max_val}]"
                for f in self._app_state.filters
            ]
            metadata["filters"] = "; ".join(filter_strs)

        export_manager = ExportManager()
        try:
            export_manager.to_parquet(df, Path(path), metadata=metadata)
            from src.ui.components.toast import Toast

            Toast.display(self, "Export complete", "success")
        except Exception as e:
            from src.ui.components.toast import Toast

            Toast.display(self, f"Export failed: {e}", "error", duration=5000)
            logger.error("Parquet export failed: %s", e)

    def _export_metrics_csv(self, timestamp: str) -> None:
        """Export metrics comparison to CSV.

        Args:
            timestamp: Timestamp for filename
        """
        default_name = f"lumen_metrics_{timestamp}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Metrics as CSV",
            default_name,
            "CSV Files (*.csv)",
        )

        if not path:
            return

        baseline = self._app_state.baseline_metrics
        filtered = self._app_state.filtered_metrics

        if baseline is None:
            from src.ui.components.toast import Toast

            Toast.display(self, "No metrics to export", "error", duration=5000)
            return

        export_manager = ExportManager()
        try:
            export_manager.metrics_to_csv(baseline, filtered, Path(path))
            from src.ui.components.toast import Toast

            Toast.display(self, "Export complete", "success")
        except Exception as e:
            from src.ui.components.toast import Toast

            Toast.display(self, f"Export failed: {e}", "error", duration=5000)
            logger.error("Metrics export failed: %s", e)

    def _execute_chart_export(self, dialog: ExportDialog) -> None:
        """Execute chart export based on dialog selection.

        Args:
            dialog: The export dialog with user selections
        """
        export_format = dialog.selected_format
        resolution = dialog.selected_resolution
        timestamp = datetime.now().strftime("%Y%m%d")

        if export_format == ExportFormat.PNG:
            self._export_chart_png(resolution, timestamp)
        elif export_format == ExportFormat.ZIP:
            self._export_charts_zip(resolution, timestamp)

    def _get_exportable_charts(self) -> dict[str, object]:
        """Get dictionary of exportable chart widgets.

        Returns:
            Dict mapping chart names to chart widgets
        """
        charts = {}

        # Get chart from flat stake panel
        if hasattr(self._flat_stake_chart_panel, "chart"):
            chart = self._flat_stake_chart_panel.chart
            if chart is not None:
                charts["flat_stake_pnl"] = chart

        # Get chart from kelly panel
        if hasattr(self._kelly_chart_panel, "chart"):
            chart = self._kelly_chart_panel.chart
            if chart is not None:
                charts["kelly_pnl"] = chart

        return charts

    def _export_chart_png(self, resolution: tuple[int, int], timestamp: str) -> None:
        """Export individual chart to PNG.

        Args:
            resolution: Target resolution as (width, height)
            timestamp: Timestamp for filename
        """
        charts = self._get_exportable_charts()

        if not charts:
            from src.ui.components.toast import Toast

            Toast.display(self, "No charts available to export", "error", duration=5000)
            return

        # If only one chart, export it directly
        if len(charts) == 1:
            chart_name, chart = next(iter(charts.items()))
            default_name = f"lumen_chart_{chart_name}_{timestamp}.png"
        else:
            # Show selection dialog (for simplicity, export first chart)
            # In a full implementation, would show a selection dialog
            chart_name, chart = next(iter(charts.items()))
            default_name = f"lumen_chart_{chart_name}_{timestamp}.png"

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Chart as PNG",
            default_name,
            "PNG Files (*.png)",
        )

        if not path:
            return

        export_manager = ExportManager()
        try:
            export_manager.chart_to_png(chart, Path(path), resolution)
            from src.ui.components.toast import Toast

            Toast.display(self, "Export complete", "success")
        except Exception as e:
            from src.ui.components.toast import Toast

            Toast.display(self, f"Export failed: {e}", "error", duration=5000)
            logger.error("Chart PNG export failed: %s", e)

    def _export_charts_zip(self, resolution: tuple[int, int], timestamp: str) -> None:
        """Export all charts to ZIP.

        Args:
            resolution: Target resolution as (width, height)
            timestamp: Timestamp for filename
        """
        charts = self._get_exportable_charts()

        if not charts:
            from src.ui.components.toast import Toast

            Toast.display(self, "No charts available to export", "error", duration=5000)
            return

        default_name = f"lumen_charts_{timestamp}.zip"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export All Charts as ZIP",
            default_name,
            "ZIP Files (*.zip)",
        )

        if not path:
            return

        export_manager = ExportManager()
        try:
            export_manager.charts_to_zip(charts, Path(path), resolution)
            from src.ui.components.toast import Toast

            Toast.display(self, "Export complete", "success")
        except Exception as e:
            from src.ui.components.toast import Toast

            Toast.display(self, f"Export failed: {e}", "error", duration=5000)
            logger.error("Charts ZIP export failed: %s", e)

    def _setup_recalc_timer(self) -> None:
        """Set up debounce timer for metric recalculation."""
        self._recalc_timer = QTimer()
        self._recalc_timer.setSingleShot(True)
        self._recalc_timer.setInterval(Animation.DEBOUNCE_METRICS)
        self._recalc_timer.timeout.connect(self._recalculate_metrics)

    def _setup_filtered_equity_timer(self) -> None:
        """Set up debounce timer for filtered equity curve calculation."""
        self._filtered_equity_debounce_timer = QTimer()
        self._filtered_equity_debounce_timer.setSingleShot(True)
        self._filtered_equity_debounce_timer.timeout.connect(
            self._calculate_filtered_equity_curves
        )

    def _connect_signals(self) -> None:
        """Connect signals for bidirectional sync."""
        # AppState -> UserInputsPanel
        self._app_state.adjustment_params_changed.connect(
            self._on_app_state_adjustment_changed
        )

        # AppState -> MetricsGrid (baseline calculated)
        self._app_state.baseline_calculated.connect(self._on_baseline_calculated)

        # AppState -> Filtered metrics calculation (Story 4.1)
        self._app_state.filtered_data_updated.connect(self._on_filtered_data_updated)

        # UserInputsPanel -> AppState
        self._user_inputs_panel.metrics_inputs_changed.connect(
            self._on_panel_metrics_changed
        )
        self._user_inputs_panel.adjustment_params_changed.connect(
            self._on_panel_adjustment_changed
        )

        # Distribution card signals
        self._winner_dist_card.view_histogram_clicked.connect(
            self._on_view_winner_histogram
        )
        self._loser_dist_card.view_histogram_clicked.connect(
            self._on_view_loser_histogram
        )

        # Recalculation triggers (debounced)
        self._app_state.metrics_user_inputs_changed.connect(
            self._schedule_recalculation
        )
        self._app_state.adjustment_params_changed.connect(
            self._schedule_recalculation
        )

        # First trigger toggle - recalculate baseline metrics.
        # Note: Feature Explorer now emits this signal AFTER updating filtered_df,
        # so there's no race condition. We need this to update baseline metrics
        # which depend on first_trigger_enabled state.
        self._app_state.first_trigger_toggled.connect(self._on_first_trigger_toggled)

        # Comparison Ribbon update (Story 4.2)
        self._app_state.metrics_updated.connect(self._on_metrics_updated)

        # Equity chart signals (Story 4.4)
        self._app_state.equity_curve_updated.connect(self._on_equity_curve_updated)
        self._app_state.kelly_equity_curve_updated.connect(
            self._on_kelly_equity_curve_updated
        )
        self._app_state.filtered_equity_curve_updated.connect(
            self._on_filtered_equity_curve_updated
        )
        self._app_state.filtered_kelly_equity_curve_updated.connect(
            self._on_filtered_kelly_equity_curve_updated
        )

    def _initialize_from_state(self) -> None:
        """Initialize panel values from AppState."""
        if self._app_state.adjustment_params:
            self._user_inputs_panel.set_adjustment_params(
                self._app_state.adjustment_params
            )
        if self._app_state.metrics_user_inputs:
            self._user_inputs_panel.set_metrics_inputs(
                self._app_state.metrics_user_inputs
            )
        # Update metrics visibility based on current state
        self._update_metrics_visibility()

        # Initialize comparison ribbon (Story 4.2)
        if (
            self._app_state.filtered_metrics is not None
            and self._app_state.baseline_metrics is not None
        ):
            self._comparison_ribbon.set_values(
                self._app_state.baseline_metrics,
                self._app_state.filtered_metrics,
            )
        else:
            self._comparison_ribbon.clear()

        # Initialize equity charts (Story 4.4)
        if self._app_state.flat_stake_equity_curve is not None:
            self._flat_stake_chart_panel.set_baseline(
                self._app_state.flat_stake_equity_curve
            )
        if self._app_state.kelly_equity_curve is not None:
            self._kelly_chart_panel.set_baseline(self._app_state.kelly_equity_curve)
        else:
            self._kelly_chart_panel.set_baseline(None)
        if self._app_state.filtered_flat_stake_equity_curve is not None:
            self._flat_stake_chart_panel.set_filtered(
                self._app_state.filtered_flat_stake_equity_curve
            )
        if self._app_state.filtered_kelly_equity_curve is not None:
            self._kelly_chart_panel.set_filtered(
                self._app_state.filtered_kelly_equity_curve
            )
        else:
            self._kelly_chart_panel.set_filtered(None)

    def _update_metrics_visibility(self) -> None:
        """Switch between EmptyState and MetricsGrid based on data availability."""
        if self._app_state.has_data:
            self._metrics_stack.setCurrentIndex(1)  # MetricsGrid
        else:
            self._metrics_stack.setCurrentIndex(0)  # EmptyState

    def _update_distribution_cards(self, metrics: TradingMetrics) -> None:
        """Update distribution cards with metrics data.

        Args:
            metrics: Calculated trading metrics.
        """
        # Update winner distribution card
        if metrics.winner_count and metrics.winner_count > 0:
            winner_bins = calculate_suggested_bins(metrics.winner_gains)
            self._winner_dist_card.update_stats(
                count=metrics.winner_count,
                min_val=metrics.winner_min,
                max_val=metrics.winner_max,
                mean=metrics.avg_winner,
                median=metrics.median_winner,
                std=metrics.winner_std,
                suggested_bins=winner_bins,
            )
        else:
            self._winner_dist_card.clear()

        # Update loser distribution card
        if metrics.loser_count and metrics.loser_count > 0:
            loser_bins = calculate_suggested_bins(metrics.loser_gains)
            self._loser_dist_card.update_stats(
                count=metrics.loser_count,
                min_val=metrics.loser_min,
                max_val=metrics.loser_max,
                mean=metrics.avg_loser,
                median=metrics.median_loser,
                std=metrics.loser_std,
                suggested_bins=loser_bins,
            )
        else:
            self._loser_dist_card.clear()

    def _on_view_winner_histogram(self) -> None:
        """Handle View Histogram click for winners.

        Opens a HistogramDialog showing winner distribution with baseline
        and filtered data overlays.
        """
        baseline_metrics = self._app_state.baseline_metrics
        if baseline_metrics is None or not baseline_metrics.winner_gains:
            logger.debug("No winner data available for histogram")
            return

        filtered_metrics = self._app_state.filtered_metrics
        filtered_gains = None
        filtered_mean = None
        filtered_median = None

        if filtered_metrics is not None and filtered_metrics.winner_gains:
            filtered_gains = filtered_metrics.winner_gains
            filtered_mean = filtered_metrics.avg_winner
            filtered_median = filtered_metrics.median_winner

        dialog = HistogramDialog(
            card_type="winner",
            baseline_gains=baseline_metrics.winner_gains,
            filtered_gains=filtered_gains,
            baseline_mean=baseline_metrics.avg_winner,
            baseline_median=baseline_metrics.median_winner,
            filtered_mean=filtered_mean,
            filtered_median=filtered_median,
            parent=self,
        )
        dialog.exec()
        # TODO: Epic 4 will implement histogram display

    def _on_view_loser_histogram(self) -> None:
        """Handle View Histogram click for losers.

        Opens a HistogramDialog showing loser distribution with baseline
        and filtered data overlays.
        """
        baseline_metrics = self._app_state.baseline_metrics
        if baseline_metrics is None or not baseline_metrics.loser_gains:
            logger.debug("No loser data available for histogram")
            return

        filtered_metrics = self._app_state.filtered_metrics
        filtered_gains = None
        filtered_mean = None
        filtered_median = None

        if filtered_metrics is not None and filtered_metrics.loser_gains:
            filtered_gains = filtered_metrics.loser_gains
            filtered_mean = filtered_metrics.avg_loser
            filtered_median = filtered_metrics.median_loser

        dialog = HistogramDialog(
            card_type="loser",
            baseline_gains=baseline_metrics.loser_gains,
            filtered_gains=filtered_gains,
            baseline_mean=baseline_metrics.avg_loser,
            baseline_median=baseline_metrics.median_loser,
            filtered_mean=filtered_mean,
            filtered_median=filtered_median,
            parent=self,
        )
        dialog.exec()
        # TODO: Epic 4 will implement histogram display

    def _on_baseline_calculated(self, metrics: TradingMetrics) -> None:
        """Handle baseline metrics calculation from AppState.

        Args:
            metrics: Calculated baseline metrics.
        """
        # Recalculate to ensure baseline respects first_trigger_enabled state
        # The initial metrics from data_input always use first triggers only,
        # but we need to respect the current toggle state
        baseline_df = self._app_state.baseline_df
        if baseline_df is not None and "trigger_number" in baseline_df.columns:
            self._recalculate_metrics()
        else:
            # Fallback: use metrics as provided (no trigger_number column yet)
            self._comparison_grid.set_values(metrics, None)
            self._update_distribution_cards(metrics)
        self._update_metrics_visibility()

    def _on_metrics_updated(
        self,
        baseline: TradingMetrics | None,
        filtered: TradingMetrics | None,
    ) -> None:
        """Update comparison ribbon and grid with new metrics.

        Args:
            baseline: Baseline metrics (full dataset), or None if not available.
            filtered: Filtered metrics, or None if no filter applied.
        """
        # Guard clause for None baseline
        if baseline is None:
            return

        # Update comparison ribbon
        if filtered is not None:
            self._comparison_ribbon.set_values(baseline, filtered)
            self._comparison_grid.set_values(baseline, filtered)
            self._update_distribution_cards(filtered)
        else:
            self._comparison_ribbon.clear()
            self._comparison_grid.clear()
            self._comparison_grid.set_values(baseline, None)
            self._update_distribution_cards(baseline)
            # Clear filtered equity curves when filter is removed
            self._flat_stake_chart_panel.set_filtered(None)
            self._kelly_chart_panel.set_filtered(None)

    def _on_equity_curve_updated(self, equity_df: pd.DataFrame) -> None:
        """Handle baseline flat stake equity curve update.

        Args:
            equity_df: DataFrame with equity curve data.
        """
        logger.info(
            "Flat stake equity curve received: cols=%s, rows=%d",
            list(equity_df.columns) if equity_df is not None else None,
            len(equity_df) if equity_df is not None else 0,
        )
        self._flat_stake_chart_panel.set_baseline(equity_df)

    def _on_kelly_equity_curve_updated(self, equity_df: pd.DataFrame) -> None:
        """Handle baseline Kelly equity curve update.

        Args:
            equity_df: DataFrame with equity curve data.
        """
        logger.info(
            "Kelly equity curve received: cols=%s, rows=%d",
            list(equity_df.columns) if equity_df is not None else None,
            len(equity_df) if equity_df is not None else 0,
        )
        self._kelly_chart_panel.set_baseline(equity_df)

    def _on_filtered_equity_curve_updated(self, equity_df: pd.DataFrame) -> None:
        """Handle filtered flat stake equity curve update.

        Args:
            equity_df: DataFrame with equity curve data.
        """
        self._flat_stake_chart_panel.set_filtered(equity_df)

    def _on_filtered_kelly_equity_curve_updated(self, equity_df: pd.DataFrame) -> None:
        """Handle filtered Kelly equity curve update.

        Args:
            equity_df: DataFrame with equity curve data.
        """
        self._kelly_chart_panel.set_filtered(equity_df)

    def _on_app_state_adjustment_changed(self, params: AdjustmentParams) -> None:
        """Handle adjustment params change from AppState.

        Args:
            params: New adjustment parameters.
        """
        self._user_inputs_panel.set_adjustment_params(params)

    def _on_panel_metrics_changed(self, inputs: MetricsUserInputs) -> None:
        """Handle metrics inputs change from panel.

        Args:
            inputs: New metrics inputs.
        """
        self._app_state.metrics_user_inputs = inputs
        self._app_state.metrics_user_inputs_changed.emit(inputs)

    def _on_panel_adjustment_changed(self, params: AdjustmentParams) -> None:
        """Handle adjustment params change from panel.

        Args:
            params: New adjustment parameters.
        """
        self._app_state.adjustment_params = params
        self._app_state.adjustment_params_changed.emit(params)

    def _schedule_recalculation(self, _: object = None) -> None:
        """Schedule debounced metric recalculation.

        Args:
            _: Ignored signal payload (can be MetricsUserInputs or AdjustmentParams).
        """
        if self._app_state.has_data:
            self._recalc_timer.start()

    def _on_first_trigger_toggled(self, enabled: bool) -> None:
        """Handle first trigger toggle state change.

        Args:
            enabled: Whether first trigger filtering is enabled.
        """
        # Recalculate all metrics with new toggle state
        self._recalculate_metrics()
        logger.info("PnL metrics recalculated for first_trigger_enabled=%s", enabled)

    def _recalculate_metrics(self) -> None:
        """Recalculate metrics with current parameters."""
        if not self._app_state.has_data:
            return

        baseline_df = self._app_state.baseline_df
        column_mapping = self._app_state.column_mapping

        if baseline_df is None or column_mapping is None:
            logger.debug("Cannot recalculate: missing baseline_df or column_mapping")
            return

        # Get current parameters
        adjustment_params = self._app_state.adjustment_params
        metrics_inputs = self._app_state.metrics_user_inputs
        fractional_kelly_pct = (
            metrics_inputs.fractional_kelly if metrics_inputs else 25.0
        )
        flat_stake = metrics_inputs.flat_stake if metrics_inputs else 10000.0
        start_capital = metrics_inputs.starting_capital if metrics_inputs else 100000.0

        # Filter baseline data based on first_trigger_enabled setting
        if self._app_state.first_trigger_enabled:
            first_triggers_df = baseline_df[baseline_df["trigger_number"] == 1].copy()
        else:
            first_triggers_df = baseline_df.copy()
        logger.info(
            "pnl_stats._recalculate_metrics: Using %d rows (first_trigger_enabled=%s, from %d total)",
            len(first_triggers_df),
            self._app_state.first_trigger_enabled,
            len(baseline_df),
        )

        # Recalculate baseline metrics (returns 3-tuple: metrics, flat_equity, kelly_equity)
        metrics, flat_equity, kelly_equity = self._metrics_calculator.calculate(
            df=first_triggers_df,
            gain_col=column_mapping.gain_pct,
            derived=column_mapping.win_loss_derived,
            breakeven_is_win=column_mapping.breakeven_is_win,
            win_loss_col=column_mapping.win_loss,
            adjustment_params=adjustment_params,
            mae_col=column_mapping.mae_pct,
            fractional_kelly_pct=fractional_kelly_pct,
            date_col=column_mapping.date,
            time_col=column_mapping.time,
            flat_stake=flat_stake,
            start_capital=start_capital,
        )

        # Store baseline metrics in app state
        self._app_state.baseline_metrics = metrics

        # Store flat stake equity curve in app state and emit signal
        self._app_state.flat_stake_equity_curve = flat_equity
        if flat_equity is not None:
            self._app_state.equity_curve_updated.emit(flat_equity)

        # Store Kelly equity curve in app state and emit signal
        # Store Kelly equity curve in app state
        self._app_state.kelly_equity_curve = kelly_equity
        # Only emit Kelly equity curve if baseline Kelly is positive
        if kelly_equity is not None and metrics.kelly is not None and metrics.kelly > 0:
            self._app_state.kelly_equity_curve_updated.emit(kelly_equity)
        elif kelly_equity is not None:
            # Clear the Kelly chart when Kelly is negative
            self._app_state.kelly_equity_curve_updated.emit(pd.DataFrame())
            if metrics.kelly is not None:
                logger.info(
                    "Baseline Kelly is negative (%.2f%%), not plotting Kelly curve",
                    metrics.kelly,
                )
            else:
                logger.info("Baseline Kelly is None, not plotting Kelly equity curve")
            self._kelly_chart_panel.set_baseline(None)
        else:
            # kelly_equity is None
            logger.info("Kelly equity curve is None, clearing chart")
            self._kelly_chart_panel.set_baseline(None)

        # Update adjusted_gain_pct column in baseline_df and filtered_df
        # This ensures Monte Carlo gets the correct efficiency-adjusted gains
        if adjustment_params is not None and column_mapping.mae_pct is not None:
            # Update baseline_df
            adjusted_gains = adjustment_params.calculate_adjusted_gains(
                baseline_df, column_mapping.gain_pct, column_mapping.mae_pct
            )
            baseline_df["adjusted_gain_pct"] = adjusted_gains
            logger.debug(
                "Updated baseline_df adjusted_gain_pct: efficiency=%.2f%%, mean=%.4f",
                adjustment_params.efficiency,
                adjusted_gains.mean(),
            )
            
            # Also update filtered_df if it exists
            # NOTE: filtered_df has reset indices (0, 1, 2, ...) after first-trigger filtering,
            # so we must recalculate directly on filtered_df, not copy from baseline_df
            if self._app_state.filtered_df is not None and not self._app_state.filtered_df.empty:
                filtered_adjusted_gains = adjustment_params.calculate_adjusted_gains(
                    self._app_state.filtered_df, column_mapping.gain_pct, column_mapping.mae_pct
                )
                self._app_state.filtered_df["adjusted_gain_pct"] = filtered_adjusted_gains
                logger.debug(
                    "Updated filtered_df adjusted_gain_pct: efficiency=%.2f%%, %d rows, mean=%.4f",
                    adjustment_params.efficiency,
                    len(self._app_state.filtered_df),
                    filtered_adjusted_gains.mean(),
                )

        # Recalculate filtered metrics if there is filtered data
        filtered_metrics = None
        if self._app_state.filtered_df is not None and not self._app_state.filtered_df.empty:
            filtered_metrics, _, _ = self._metrics_calculator.calculate(
                df=self._app_state.filtered_df,
                gain_col=column_mapping.gain_pct,
                derived=column_mapping.win_loss_derived,
                breakeven_is_win=column_mapping.breakeven_is_win,
                win_loss_col=column_mapping.win_loss,
                adjustment_params=adjustment_params,
                mae_col=column_mapping.mae_pct,
                fractional_kelly_pct=fractional_kelly_pct,
                date_col=column_mapping.date,
                time_col=column_mapping.time,
                flat_stake=None,      # Skip equity calculation for filtered (done separately)
                start_capital=None,
            )
            self._app_state.filtered_metrics = filtered_metrics

        # Update comparison components with both baseline and filtered
        if filtered_metrics:
            self._comparison_ribbon.set_values(metrics, filtered_metrics)
        else:
            self._comparison_ribbon.clear()
        self._comparison_grid.set_values(metrics, filtered_metrics)
        # Update distribution cards: use filtered metrics if available, else baseline
        if filtered_metrics is not None:
            self._update_distribution_cards(filtered_metrics)
        else:
            self._update_distribution_cards(metrics)

        # Emit metrics_updated signal to notify other listeners
        self._app_state.metrics_updated.emit(metrics, filtered_metrics)

        # Schedule filtered equity curve calculation if there is filtered data
        # This ensures flat stake and kelly metrics are recalculated
        if self._app_state.filtered_df is not None and not self._app_state.filtered_df.empty:
            self._schedule_equity_curve_calculation()

        logger.debug(
            "Recalculated metrics: kelly=%.1f%%, stake=%.2f, capital=%.2f",
            fractional_kelly_pct,
            flat_stake,
            start_capital,
        )

    def showEvent(self, event: QShowEvent | None) -> None:
        """Handle tab becoming visible - refresh charts and check if metrics need recalculation.

        Args:
            event: The show event.
        """
        super().showEvent(event)

        # Refresh equity charts from AppState (Story 4.4)
        if self._app_state.flat_stake_equity_curve is not None:
            self._flat_stake_chart_panel.set_baseline(
                self._app_state.flat_stake_equity_curve
            )
        if self._app_state.kelly_equity_curve is not None:
            self._kelly_chart_panel.set_baseline(self._app_state.kelly_equity_curve)
        else:
            # Clear Kelly chart if no equity curve (e.g., negative Kelly)
            self._kelly_chart_panel.set_baseline(None)
        if self._app_state.filtered_flat_stake_equity_curve is not None:
            self._flat_stake_chart_panel.set_filtered(
                self._app_state.filtered_flat_stake_equity_curve
            )
        if self._app_state.filtered_kelly_equity_curve is not None:
            self._kelly_chart_panel.set_filtered(
                self._app_state.filtered_kelly_equity_curve
            )
        else:
            self._kelly_chart_panel.set_filtered(None)

        # Check if filtered metrics need recalculation
        if self._app_state.filtered_df is not None:
            current_hash = self._compute_df_hash(self._app_state.filtered_df)
            if current_hash != self._filtered_df_hash:
                self._on_filtered_data_updated(self._app_state.filtered_df)

    def _compute_df_hash(self, df: pd.DataFrame) -> str:
        """Compute hash of DataFrame for change detection.

        Args:
            df: DataFrame to hash.

        Returns:
            Hash string representing DataFrame state.
        """
        if df.empty:
            return "empty"
        return str(pd.util.hash_pandas_object(df).sum())

    def _on_filtered_data_updated(self, filtered_df: pd.DataFrame) -> None:
        """Handle filtered data update from AppState.

        Args:
            filtered_df: The filtered DataFrame.
        """
        # Check visibility first
        if self._dock_widget is not None:
            if not self._app_state.visibility_tracker.is_visible(self._dock_widget):
                self._app_state.visibility_tracker.mark_stale(self._tab_name)
                return

        # Emit calculation started signal
        self._app_state.is_calculating_filtered = True
        self._app_state.filtered_calculation_started.emit()

        # Calculate filtered metrics immediately (fast - no equity curves)
        self._calculate_filtered_metrics(filtered_df)

        # Schedule debounced equity curve calculation
        self._schedule_equity_curve_calculation()

    def _calculate_filtered_metrics(self, filtered_df: pd.DataFrame) -> None:
        """Calculate filtered metrics without equity curves (fast path).

        Args:
            filtered_df: The filtered DataFrame to calculate metrics for.
        """
        column_mapping = self._app_state.column_mapping
        if column_mapping is None:
            logger.debug("Cannot calculate filtered metrics: missing column_mapping")
            return

        # Update hash tracking
        self._filtered_df_hash = self._compute_df_hash(filtered_df)

        # Handle empty DataFrame edge case
        if filtered_df.empty:
            self._app_state.filtered_metrics = TradingMetrics.empty()
            self._app_state.metrics_updated.emit(
                self._app_state.baseline_metrics,
                self._app_state.filtered_metrics,
            )
            # Complete calculation immediately for empty data
            self._app_state.is_calculating_filtered = False
            self._app_state.filtered_calculation_completed.emit()
            return

        # Get current parameters
        adjustment_params = self._app_state.adjustment_params
        metrics_inputs = self._app_state.metrics_user_inputs
        fractional_kelly_pct = (
            metrics_inputs.fractional_kelly if metrics_inputs else 25.0
        )

        # Fast calculation without equity curves
        start = time.perf_counter()
        metrics, _, _ = self._metrics_calculator.calculate(
            df=filtered_df,
            gain_col=column_mapping.gain_pct,
            derived=column_mapping.win_loss_derived,
            breakeven_is_win=column_mapping.breakeven_is_win,
            win_loss_col=column_mapping.win_loss,
            adjustment_params=adjustment_params,
            mae_col=column_mapping.mae_pct,
            fractional_kelly_pct=fractional_kelly_pct,
            date_col=column_mapping.date,
            time_col=column_mapping.time,
            flat_stake=None,      # Skip flat stake equity calculation
            start_capital=None,   # Skip Kelly equity calculation
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Filtered core stats calculated in %.2fms (target: <100ms)", elapsed_ms
        )

        # Store filtered metrics and emit signal
        self._app_state.filtered_metrics = metrics
        self._app_state.metrics_updated.emit(
            self._app_state.baseline_metrics,
            self._app_state.filtered_metrics,
        )

        # Calculate and store scenario results (golden statistics)
        scenario_start = time.perf_counter()

        # Only calculate scenarios if we have the required columns
        if column_mapping.mae_pct and column_mapping.mae_pct in filtered_df.columns:
            self._app_state.stop_scenarios = self._metrics_calculator.calculate_stop_scenarios(
                df=filtered_df,
                mapping=column_mapping,
                adjustment_params=adjustment_params,
                start_capital=metrics_inputs.starting_capital if metrics_inputs else None,
                fractional_kelly_pct=fractional_kelly_pct,
            )
        else:
            self._app_state.stop_scenarios = []

        if (column_mapping.mae_pct and column_mapping.mfe_pct and
            column_mapping.mae_pct in filtered_df.columns and
            column_mapping.mfe_pct in filtered_df.columns):
            self._app_state.offset_scenarios = self._metrics_calculator.calculate_offset_scenarios(
                df=filtered_df,
                mapping=column_mapping,
                adjustment_params=adjustment_params,
                start_capital=metrics_inputs.starting_capital if metrics_inputs else None,
                fractional_kelly_pct=fractional_kelly_pct,
            )
        else:
            self._app_state.offset_scenarios = []

        scenario_elapsed = (time.perf_counter() - scenario_start) * 1000
        logger.info("Scenarios calculated in %.2fms", scenario_elapsed)

        # Emit unified metrics signal
        from src.core.models import ComputedMetrics
        computed = ComputedMetrics(
            trading_metrics=metrics,
            stop_scenarios=self._app_state.stop_scenarios,
            offset_scenarios=self._app_state.offset_scenarios,
            computation_time_ms=elapsed_ms + scenario_elapsed,
        )
        self._app_state.all_metrics_ready.emit(computed)

    def _schedule_equity_curve_calculation(self) -> None:
        """Schedule debounced equity curve calculation."""
        self._filtered_equity_debounce_timer.start(Animation.DEBOUNCE_METRICS)

    def _calculate_filtered_equity_curves(self) -> None:
        """Calculate filtered equity curves after debounce completes."""
        filtered_df = self._app_state.filtered_df
        column_mapping = self._app_state.column_mapping

        if filtered_df is None or column_mapping is None:
            logger.debug(
                "Cannot calculate filtered equity curves: missing data or mapping"
            )
            self._app_state.is_calculating_filtered = False
            self._app_state.filtered_calculation_completed.emit()
            return

        # Handle empty DataFrame edge case
        if filtered_df.empty:
            self._app_state.filtered_flat_stake_equity_curve = None
            self._app_state.filtered_kelly_equity_curve = None
            self._app_state.is_calculating_filtered = False
            self._app_state.filtered_calculation_completed.emit()
            return

        # Get current parameters
        adjustment_params = self._app_state.adjustment_params
        metrics_inputs = self._app_state.metrics_user_inputs
        fractional_kelly_pct = (
            metrics_inputs.fractional_kelly if metrics_inputs else 25.0
        )
        flat_stake = metrics_inputs.flat_stake if metrics_inputs else 10000.0
        start_capital = metrics_inputs.starting_capital if metrics_inputs else 100000.0

        # Full calculation with equity curves
        metrics, flat_equity, kelly_equity = self._metrics_calculator.calculate(
            df=filtered_df,
            gain_col=column_mapping.gain_pct,
            derived=column_mapping.win_loss_derived,
            breakeven_is_win=column_mapping.breakeven_is_win,
            win_loss_col=column_mapping.win_loss,
            adjustment_params=adjustment_params,
            mae_col=column_mapping.mae_pct,
            fractional_kelly_pct=fractional_kelly_pct,
            date_col=column_mapping.date,
            time_col=column_mapping.time,
            flat_stake=flat_stake,
            start_capital=start_capital,
        )

        # Update filtered metrics with flat stake and Kelly values
        if self._app_state.filtered_metrics is not None:
            from dataclasses import replace
            updated_metrics = replace(
                self._app_state.filtered_metrics,
                flat_stake_pnl=metrics.flat_stake_pnl,
                flat_stake_max_dd=metrics.flat_stake_max_dd,
                flat_stake_max_dd_pct=metrics.flat_stake_max_dd_pct,
                flat_stake_dd_duration=metrics.flat_stake_dd_duration,
                kelly_pnl=metrics.kelly_pnl,
                kelly_max_dd=metrics.kelly_max_dd,
                kelly_max_dd_pct=metrics.kelly_max_dd_pct,
                kelly_dd_duration=metrics.kelly_dd_duration,
                eg_full_kelly=metrics.eg_full_kelly,
                eg_frac_kelly=metrics.eg_frac_kelly,
                eg_flat_stake=metrics.eg_flat_stake,
            )
            self._app_state.filtered_metrics = updated_metrics
            # Re-emit metrics updated signal so UI refreshes
            self._app_state.metrics_updated.emit(
                self._app_state.baseline_metrics,
                self._app_state.filtered_metrics,
            )
            logger.debug("Updated filtered metrics with flat stake/Kelly values")

        # Store and emit filtered equity curves
        self._app_state.filtered_flat_stake_equity_curve = flat_equity
        if flat_equity is not None:
            self._app_state.filtered_equity_curve_updated.emit(flat_equity)

        self._app_state.filtered_kelly_equity_curve = kelly_equity
        # Only emit Kelly equity curve if filtered Kelly is positive
        if kelly_equity is not None and metrics.kelly is not None and metrics.kelly > 0:
            self._app_state.filtered_kelly_equity_curve_updated.emit(kelly_equity)
        elif kelly_equity is not None:
            # Clear the Kelly chart when Kelly is negative
            self._app_state.filtered_kelly_equity_curve_updated.emit(pd.DataFrame())
            if metrics.kelly is not None:
                logger.debug(
                    "Filtered Kelly is negative (%.2f%%), not plotting Kelly curve",
                    metrics.kelly,
                )
            else:
                logger.debug("Filtered Kelly is None, not plotting Kelly curve")
        else:
            # Clear filtered Kelly when no equity curve
            self._kelly_chart_panel.set_filtered(None)

        # Complete calculation
        self._app_state.is_calculating_filtered = False
        self._app_state.filtered_calculation_completed.emit()
        logger.debug("Filtered equity curves calculated")

    def cleanup(self) -> None:
        """Clean up resources."""
        self._recalc_timer.stop()
        self._filtered_equity_debounce_timer.stop()
        self._user_inputs_panel.cleanup()
        self._status_indicator.cleanup()
