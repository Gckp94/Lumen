"""Feature Explorer tab for filtering and charting.

This is the second tab in the workflow where users explore and filter
their data features.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.ui.components.no_scroll_widgets import NoScrollComboBox

from src.core.app_state import AppState
from src.core.exceptions import ExportError
from src.core.export_manager import ExportManager
from src.core.filter_engine import FilterEngine
from src.core.first_trigger import FirstTriggerEngine
from src.core.models import FilterCriteria, TradingMetrics
from src.ui.components.axis_control_panel import AxisControlPanel
from src.ui.components.chart_canvas import ChartCanvas
from src.ui.components.filter_panel import FilterPanel
from src.ui.components.toast import Toast
from src.ui.constants import Animation, Colors, Spacing

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class FeatureExplorerTab(QWidget):
    """Tab for feature exploration and filtering.

    Provides a 3-panel layout with column selector sidebar, scatter plot chart,
    and data point count bottom bar.

    Attributes:
        _app_state: Reference to the centralized application state.
        _sidebar: Left sidebar containing column selector.
        _chart_canvas: Main chart area for scatter plots.
        _bottom_bar: Bottom bar showing data point count.
        _column_selector: Dropdown for selecting numeric columns.
        _filter_panel: Panel for managing filters.
        _axis_control_panel: Panel for axis range and grid controls.
        _data_count_label: Label displaying current data point count.
        _empty_label: Label shown when no data is loaded.
    """

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        """Initialize the Feature Explorer tab.

        Args:
            app_state: Reference to the centralized application state.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._app_state = app_state
        self._debounce_timer: QTimer | None = None
        # Date range filter state
        self._date_start: str | None = None
        self._date_end: str | None = None
        self._all_dates: bool = True
        self._setup_ui()
        self._connect_signals()
        self._show_empty_state()

    def _setup_ui(self) -> None:
        """Set up the 3-panel layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create splitter for sidebar and chart area
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left sidebar (25% width)
        self._sidebar = QFrame()
        self._sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_ELEVATED};
                border-right: 1px solid {Colors.BG_BORDER};
            }}
        """)
        self._setup_sidebar()

        # Main chart area (75% width)
        self._chart_canvas = ChartCanvas()

        # Empty state label (overlay on chart)
        self._empty_label = QLabel("Load a data file to explore features")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 14px;
                background-color: {Colors.BG_SURFACE};
            }}
        """)

        # Stack widget to switch between empty state and chart
        self._chart_stack = QStackedWidget()
        self._chart_stack.addWidget(self._empty_label)
        self._chart_stack.addWidget(self._chart_canvas)

        # Add to splitter
        self._splitter.addWidget(self._sidebar)
        self._splitter.addWidget(self._chart_stack)
        self._splitter.setSizes([250, 750])  # 25% / 75% initial split
        self._splitter.setStretchFactor(0, 0)  # Sidebar fixed
        self._splitter.setStretchFactor(1, 1)  # Chart stretches

        # Bottom bar
        self._bottom_bar = QFrame()
        self._bottom_bar.setFixedHeight(32)
        self._bottom_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_ELEVATED};
                border-top: 1px solid {Colors.BG_BORDER};
            }}
        """)
        self._setup_bottom_bar()

        # Add to main layout
        main_layout.addWidget(self._splitter, stretch=1)
        main_layout.addWidget(self._bottom_bar)

    def _setup_sidebar(self) -> None:
        """Set up the sidebar with column selector and filter panel."""
        layout = QVBoxLayout(self._sidebar)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.SM)

        # Column selector label
        label = QLabel("Select Column")
        label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-size: 12px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(label)

        # Column selector dropdown
        self._column_selector = NoScrollComboBox()
        self._column_selector.setStyleSheet(f"""
            QComboBox {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 13px;
            }}
            QComboBox:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                selection-background-color: {Colors.BG_BORDER};
                border: 1px solid {Colors.BG_BORDER};
            }}
        """)
        self._column_selector.setEnabled(False)  # Disabled until data loads
        layout.addWidget(self._column_selector)

        # Filter panel below column selector
        self._filter_panel = FilterPanel()
        layout.addWidget(self._filter_panel)

        # Axis control panel below filter panel
        self._axis_control_panel = AxisControlPanel()
        layout.addWidget(self._axis_control_panel)

        # Spacer
        layout.addStretch()

    def _setup_bottom_bar(self) -> None:
        """Set up the bottom bar with data point count, filter summary, and export button."""
        layout = QHBoxLayout(self._bottom_bar)
        layout.setContentsMargins(Spacing.MD, 0, Spacing.MD, 0)

        self._data_count_label = QLabel("No data loaded")
        self._data_count_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 12px;
            }}
        """)
        layout.addWidget(self._data_count_label)

        # Filter summary label (between data count and export button)
        self._filter_summary_label = QLabel("Filters: None")
        self._filter_summary_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 12px;
                margin-left: {Spacing.LG}px;
            }}
        """)
        layout.addWidget(self._filter_summary_label)

        layout.addStretch()

        # Export button (right side)
        self._export_button = QPushButton("Export Filtered Data")
        self._export_button.setEnabled(False)  # Disabled until data available
        self._export_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: {Spacing.SM}px {Spacing.MD}px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_BORDER};
            }}
            QPushButton:disabled {{
                color: {Colors.TEXT_DISABLED};
            }}
        """)
        layout.addWidget(self._export_button)

    def _connect_signals(self) -> None:
        """Connect to AppState signals and local events."""
        # AppState signals
        self._app_state.data_loaded.connect(self._on_data_loaded)
        self._app_state.baseline_calculated.connect(self._on_baseline_calculated)
        self._app_state.filtered_data_updated.connect(self._on_filtered_data_updated)
        self._app_state.column_mapping_changed.connect(self._on_column_mapping_changed)

        # Local events
        self._column_selector.currentTextChanged.connect(self._on_column_changed_debounced)

        # Filter panel signals
        self._filter_panel.filters_applied.connect(self._on_filters_applied)
        self._filter_panel.filters_cleared.connect(self._on_filters_cleared)
        self._filter_panel.first_trigger_toggled.connect(self._on_first_trigger_toggled)
        self._filter_panel.date_range_changed.connect(self._on_date_range_changed)

        # Export button
        self._export_button.clicked.connect(self._on_export_clicked)

        # Axis control panel signals
        self._axis_control_panel.range_changed.connect(self._on_axis_range_changed)
        self._axis_control_panel.auto_fit_clicked.connect(self._chart_canvas.auto_range)
        self._axis_control_panel.grid_toggled.connect(self._chart_canvas.set_grid_visible)

        # Chart canvas range change for bidirectional sync
        self._chart_canvas.range_changed.connect(self._on_chart_range_changed)

    def _on_data_loaded(self, df: pd.DataFrame) -> None:
        """Handle data loaded signal.

        Populates the column selector and filter panel with numeric columns.
        Handles edge case of empty DataFrame by disabling toggle.

        Args:
            df: The loaded DataFrame.
        """
        numeric_columns = self._get_numeric_columns(df)

        self._column_selector.blockSignals(True)
        self._column_selector.clear()

        # Edge case: empty DataFrame - disable toggle
        if df is None or df.empty:
            self._column_selector.setEnabled(False)
            self._filter_panel.set_columns([])
            self._filter_panel._first_trigger_toggle.setEnabled(False)
            self._empty_label.setText("No data loaded")
            self._chart_stack.setCurrentIndex(0)
            self._data_count_label.setText("No data loaded")
            logger.warning("Empty DataFrame loaded")
            self._column_selector.blockSignals(False)
            return

        if not numeric_columns:
            self._column_selector.setEnabled(False)
            self._filter_panel.set_columns([])
            self._filter_panel._first_trigger_toggle.setEnabled(False)
            self._empty_label.setText("No numeric columns available for visualization")
            self._chart_stack.setCurrentIndex(0)  # Show empty state
            self._data_count_label.setText("No numeric columns")
            logger.warning("No numeric columns found in loaded data")
        else:
            self._column_selector.addItems(numeric_columns)
            self._column_selector.setEnabled(True)
            self._filter_panel.set_columns(numeric_columns)
            # Enable toggle only when column mapping is available
            self._filter_panel._first_trigger_toggle.setEnabled(
                self._app_state.column_mapping is not None
            )

            # Default to gain_pct if available, otherwise first column
            if "gain_pct" in numeric_columns:
                self._column_selector.setCurrentText("gain_pct")
            else:
                self._column_selector.setCurrentIndex(0)

            logger.info(f"Column selector populated with {len(numeric_columns)} columns")

        self._column_selector.blockSignals(False)

    def _on_column_mapping_changed(self, mapping: object) -> None:
        """Handle column mapping changed signal.

        Enables/disables first trigger toggle based on mapping availability.

        Args:
            mapping: The new ColumnMapping or None.
        """
        has_mapping = mapping is not None
        self._filter_panel._first_trigger_toggle.setEnabled(has_mapping)
        if has_mapping:
            logger.debug("Column mapping set, first trigger toggle enabled")
        else:
            logger.debug("Column mapping cleared, first trigger toggle disabled")

    def _on_baseline_calculated(self, _metrics: TradingMetrics) -> None:
        """Handle baseline calculated signal.

        Refreshes the chart with baseline data.

        Args:
            _metrics: The calculated metrics (unused, we use baseline_df directly).
        """
        self._update_chart()

        # Enable export button when baseline data is available
        has_data = (
            self._app_state.baseline_df is not None
            and not self._app_state.baseline_df.empty
        )
        self._export_button.setEnabled(has_data)

    def _on_column_changed_debounced(self, _column: str) -> None:
        """Handle column selector change with debounce.

        Args:
            _column: The selected column name (unused, we read from widget).
        """
        # Cancel any pending timer
        if self._debounce_timer is not None:
            self._debounce_timer.stop()

        # Create new timer for debounced update
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._update_chart)
        self._debounce_timer.start(Animation.DEBOUNCE_INPUT)

    def _update_chart(self) -> None:
        """Update the chart with current data and selected column.

        Uses filtered_df if filters are applied, otherwise baseline_df.
        """
        # Use filtered data if available, otherwise baseline
        df = self._app_state.filtered_df
        if df is None:
            df = self._app_state.baseline_df

        column = self._column_selector.currentText()

        if df is None or df.empty:
            # Edge case: zero matches after filter or zero first triggers
            first_trigger_on = self._app_state.first_trigger_enabled
            has_filters = bool(self._app_state.filters)

            if has_filters and first_trigger_on:
                self._empty_label.setText("No first triggers match current filters")
            elif has_filters:
                self._empty_label.setText("No data matches current filters")
            else:
                self._empty_label.setText("Load a data file to explore features")

            self._chart_stack.setCurrentIndex(0)
            self._data_count_label.setText("No matching data")
            return

        if not column or column not in df.columns:
            logger.warning(f"Column '{column}' not found in DataFrame")
            return

        # Show chart and update data
        self._chart_stack.setCurrentIndex(1)
        self._chart_canvas.update_data(df, column)

        # Update bottom bar with accurate counts
        count = len(df)
        baseline_count = (
            len(self._app_state.baseline_df)
            if self._app_state.baseline_df is not None
            else count
        )

        # Compute filtered-only count (before first trigger)
        filtered_count = count
        if (
            self._app_state.first_trigger_enabled
            and self._app_state.filters
            and self._app_state.baseline_df is not None
        ):
            # Need to compute how many rows matched filters before first trigger
            engine = FilterEngine()
            filtered_only = engine.apply_filters(
                self._app_state.baseline_df, self._app_state.filters
            )
            filtered_count = len(filtered_only)

        # Format message based on state
        first_trigger_on = self._app_state.first_trigger_enabled
        has_filters = bool(self._app_state.filters)

        if first_trigger_on and has_filters:
            # "Showing {n:,} first triggers of {filtered:,} filtered ({total:,} total)"
            self._data_count_label.setText(
                f"Showing {count:,} first triggers of {filtered_count:,} filtered "
                f"({baseline_count:,} total)"
            )
        elif first_trigger_on and not has_filters:
            # "Showing {n:,} first triggers ({total:,} total)"
            self._data_count_label.setText(
                f"Showing {count:,} first triggers ({baseline_count:,} total)"
            )
        elif not first_trigger_on and has_filters:
            # "Showing {n:,} of {total:,} data points (filtered)"
            self._data_count_label.setText(
                f"Showing {count:,} of {baseline_count:,} data points (filtered)"
            )
        else:
            # "Showing {n:,} data points"
            self._data_count_label.setText(f"Showing {count:,} data points")

        logger.debug(f"Chart updated: column='{column}', points={count}")

    def _show_empty_state(self) -> None:
        """Show the empty state message."""
        self._empty_label.setText("Load a data file to explore features")
        self._chart_stack.setCurrentIndex(0)
        self._data_count_label.setText("No data loaded")
        self._column_selector.setEnabled(False)
        self._export_button.setEnabled(False)

    def _on_filters_applied(self, filters: list[FilterCriteria]) -> None:
        """Handle filter application.

        Args:
            filters: List of FilterCriteria to apply.
        """
        if self._app_state.baseline_df is None:
            logger.warning("Cannot apply filters: no baseline data loaded")
            return

        self._app_state.filters = filters
        self._apply_current_filters()
        self._update_filter_summary()

        filtered_count = (
            len(self._app_state.filtered_df) if self._app_state.filtered_df is not None else 0
        )
        logger.info(f"Filters applied: {len(filters)} filters, {filtered_count} rows match")

    def _on_filters_cleared(self) -> None:
        """Handle filter clear."""
        self._app_state.filters = []
        self._apply_current_filters()
        self._update_filter_summary()
        logger.info("Filters cleared")

    def _on_first_trigger_toggled(self, enabled: bool) -> None:
        """Handle first trigger toggle state change.

        Args:
            enabled: Whether first trigger filtering is enabled.
        """
        self._app_state.first_trigger_enabled = enabled
        self._app_state.first_trigger_toggled.emit(enabled)
        self._apply_current_filters()
        logger.info(f"First trigger toggle: {'ON' if enabled else 'OFF'}")

    def _on_date_range_changed(
        self, start: str | None, end: str | None, all_dates: bool
    ) -> None:
        """Handle date range filter change.

        Args:
            start: Start date ISO string or None.
            end: End date ISO string or None.
            all_dates: Whether 'All Dates' is checked.
        """
        self._date_start = start
        self._date_end = end
        self._all_dates = all_dates
        self._apply_current_filters()
        self._update_filter_summary()
        if all_dates:
            logger.info("Date range filter: All Dates")
        else:
            logger.info(f"Date range filter: {start} to {end}")

    def _update_filter_summary(self) -> None:
        """Update filter summary display in bottom bar with date details."""
        filter_count = len(self._app_state.filters)
        has_date_filter = not self._all_dates
        date_display = self._filter_panel._date_range_filter.get_display_range()

        if filter_count == 0 and not has_date_filter:
            text = "Filters: None"
        elif has_date_filter and filter_count > 0:
            text = f"Filters: {filter_count} active, {date_display}"
        elif has_date_filter:
            text = f"Filters: {date_display}"
        else:
            text = f"Filters: {filter_count} active"

        self._filter_summary_label.setText(text)

    def _apply_current_filters(self) -> None:
        """Apply current filters with first-trigger state.

        Recomputes filtered_df based on current filters and first_trigger_enabled.
        Chain: baseline_df → date_range_filter → column_filters → first_trigger
        """
        if self._app_state.baseline_df is None:
            return

        engine = FilterEngine()

        # Start with baseline data
        df = self._app_state.baseline_df.copy()

        # Apply date range filter first (if column mapping available)
        if self._app_state.column_mapping and not self._all_dates:
            df = engine.apply_date_range(
                df,
                date_col=self._app_state.column_mapping.date,
                start=self._date_start,
                end=self._date_end,
                all_dates=self._all_dates,
            )

        # Apply feature filters if any
        if self._app_state.filters:
            df = engine.apply_filters(df, self._app_state.filters)

        # Apply first trigger if enabled and column mapping available
        if self._app_state.first_trigger_enabled and self._app_state.column_mapping:
            ft_engine = FirstTriggerEngine()
            mapping = self._app_state.column_mapping
            df = ft_engine.apply_filtered(
                df,
                mapping.ticker,
                mapping.date,
                mapping.time,
            )

        self._app_state.filtered_df = df
        self._app_state.filtered_data_updated.emit(df)

    def _on_filtered_data_updated(self, _df: pd.DataFrame) -> None:
        """Handle filtered data updated signal.

        Args:
            _df: The filtered DataFrame (unused, we read from AppState).
        """
        self._update_chart()

        # Enable/disable export button based on data availability
        has_data = (
            self._app_state.filtered_df is not None
            and not self._app_state.filtered_df.empty
        )
        self._export_button.setEnabled(has_data)

    @staticmethod
    def _get_numeric_columns(df: pd.DataFrame) -> list[str]:
        """Get list of numeric columns from DataFrame.

        Args:
            df: The DataFrame to analyze.

        Returns:
            List of column names that contain numeric data.
        """
        if df is None or df.empty:
            return []
        return df.select_dtypes(include=["number"]).columns.tolist()

    def _on_axis_range_changed(
        self, x_min: float, x_max: float, y_min: float, y_max: float
    ) -> None:
        """Handle axis control panel range change.

        Args:
            x_min: Minimum X value.
            x_max: Maximum X value.
            y_min: Minimum Y value.
            y_max: Maximum Y value.
        """
        self._chart_canvas.set_range(x_min, x_max, y_min, y_max)

    def _on_chart_range_changed(
        self, x_min: float, x_max: float, y_min: float, y_max: float
    ) -> None:
        """Handle chart range change for bidirectional sync.

        Args:
            x_min: Minimum X value.
            x_max: Maximum X value.
            y_min: Minimum Y value.
            y_max: Maximum Y value.
        """
        self._axis_control_panel.set_range(x_min, x_max, y_min, y_max)

    def _on_export_clicked(self) -> None:
        """Handle export button click.

        Shows save dialog, exports filtered data with metadata,
        and displays success/error toast notification.
        """
        if self._app_state.filtered_df is None:
            return

        # Generate suggested filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suggested_name = f"lumen_export_{timestamp}.csv"

        # Show save dialog
        path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Export Filtered Data",
            suggested_name,
            "CSV Files (*.csv);;All Files (*)",
        )

        if not path_str:
            return  # User cancelled

        # Ensure .csv extension
        path = Path(path_str)
        if path.suffix.lower() != ".csv":
            path = path.with_suffix(".csv")

        try:
            exporter = ExportManager()
            exporter.to_csv(
                df=self._app_state.filtered_df,
                path=path,
                filters=self._app_state.filters,
                first_trigger_enabled=self._app_state.first_trigger_enabled,
                total_rows=(
                    len(self._app_state.raw_df)
                    if self._app_state.raw_df is not None
                    else None
                ),
            )
            Toast.display(
                self,
                f"Exported {len(self._app_state.filtered_df):,} rows to {path.name}",
                "success",
            )
            logger.info("Export completed: %s", path)
        except ExportError as e:
            Toast.display(self, str(e), "error")
            logger.error("Export failed: %s", e)
