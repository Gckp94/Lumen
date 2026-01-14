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
    QCheckBox,
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

from src.core.app_state import AppState
from src.core.exceptions import ExportError
from src.core.export_manager import ExportManager
from src.core.filter_engine import FilterEngine
from src.core.models import FilterCriteria, TradingMetrics
from src.ui.components.axis_column_selector import AxisColumnSelector
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
        _sidebar: Left sidebar containing axis column selector.
        _chart_canvas: Main chart area for scatter plots.
        _bottom_bar: Bottom bar showing data point count.
        _axis_selector: Selector for X and Y axis columns.
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
        # Time range filter state
        self._time_start: str | None = None
        self._time_end: str | None = None
        self._all_times: bool = True
        # Contrast colors state
        self._contrast_colors: bool = False
        # Axis bounds for data filtering (not just zoom)
        self._x_filter_min: float | None = None
        self._x_filter_max: float | None = None
        self._y_filter_min: float | None = None
        self._y_filter_max: float | None = None
        self._setup_ui()
        self._connect_signals()
        self._show_empty_state()

    def _setup_ui(self) -> None:
        """Set up the 3-panel layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Ensure minimum height so bottom bar is always visible
        self.setMinimumHeight(200)

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

        # Axis column selector (replaces single column selector)
        self._axis_selector = AxisColumnSelector()
        layout.addWidget(self._axis_selector)

        # Filter panel below column selector
        self._filter_panel = FilterPanel()
        layout.addWidget(self._filter_panel)

        # Axis control panel below filter panel
        self._axis_control_panel = AxisControlPanel()
        layout.addWidget(self._axis_control_panel)

        # Contrast colors toggle
        self._contrast_toggle = QCheckBox("Contrast colors (\u00b10)")
        self._contrast_toggle.setStyleSheet(f"""
            QCheckBox {{
                color: {Colors.TEXT_PRIMARY};
                font-size: 12px;
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 3px;
                background: {Colors.BG_SURFACE};
            }}
            QCheckBox::indicator:checked {{
                background: {Colors.SIGNAL_CYAN};
                border-color: {Colors.SIGNAL_CYAN};
            }}
        """)
        self._contrast_toggle.setToolTip("Color points cyan if \u22650, coral if <0")
        self._contrast_toggle.toggled.connect(self._on_contrast_toggled)
        layout.addWidget(self._contrast_toggle)

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
        self._axis_selector.selection_changed.connect(self._on_column_changed_debounced)

        # Filter panel signals
        self._filter_panel.filters_applied.connect(self._on_filters_applied)
        self._filter_panel.filters_cleared.connect(self._on_filters_cleared)
        self._filter_panel.first_trigger_toggled.connect(self._on_first_trigger_toggled)
        self._filter_panel.date_range_changed.connect(self._on_date_range_changed)
        self._filter_panel.time_range_changed.connect(self._on_time_range_changed)
        self._filter_panel.single_filter_applied.connect(self._on_single_filter_applied)

        # Export button
        self._export_button.clicked.connect(self._on_export_clicked)

        # Axis control panel signals
        self._axis_control_panel.range_changed.connect(self._on_axis_range_changed)
        self._axis_control_panel.auto_fit_clicked.connect(self._on_auto_fit)
        self._axis_control_panel.grid_toggled.connect(self._chart_canvas.set_grid_visible)

        # Chart canvas range change for bidirectional sync
        self._chart_canvas.range_changed.connect(self._on_chart_range_changed)

        # Axis bounds from column selector
        self._axis_selector.x_bounds_changed.connect(self._on_x_bounds_changed)
        self._axis_selector.y_bounds_changed.connect(self._on_y_bounds_changed)

    def _on_data_loaded(self, df: pd.DataFrame) -> None:
        """Handle data loaded signal.

        Populates the axis selector and filter panel with numeric columns.
        Handles edge case of empty DataFrame by disabling toggle.

        Args:
            df: The loaded DataFrame.
        """
        numeric_columns = self._get_numeric_columns(df)

        # Edge case: empty DataFrame - disable toggle
        if df is None or df.empty:
            self._axis_selector.set_columns([])
            self._filter_panel.set_columns([])
            self._filter_panel._first_trigger_toggle.setEnabled(False)
            self._empty_label.setText("No data loaded")
            self._chart_stack.setCurrentIndex(0)
            self._data_count_label.setText("No data loaded")
            logger.warning("Empty DataFrame loaded")
            return

        if not numeric_columns:
            self._axis_selector.set_columns([])
            self._filter_panel.set_columns([])
            self._filter_panel._first_trigger_toggle.setEnabled(False)
            self._empty_label.setText("No numeric columns available for visualization")
            self._chart_stack.setCurrentIndex(0)  # Show empty state
            self._data_count_label.setText("No numeric columns")
            logger.warning("No numeric columns found in loaded data")
        else:
            self._axis_selector.set_columns(numeric_columns)
            self._filter_panel.set_columns(numeric_columns)
            # Enable toggle only when column mapping is available
            self._filter_panel._first_trigger_toggle.setEnabled(
                self._app_state.column_mapping is not None
            )

            # Default Y to gain_pct if available
            if "gain_pct" in numeric_columns:
                self._axis_selector.set_y_column("gain_pct")

            logger.info(f"Axis selector populated with {len(numeric_columns)} columns")

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

    def _on_column_changed_debounced(self) -> None:
        """Handle axis column selector change with debounce."""
        # Cancel any pending timer
        if self._debounce_timer is not None:
            self._debounce_timer.stop()

        # Create new timer for debounced update
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._update_chart)
        self._debounce_timer.start(Animation.DEBOUNCE_INPUT)

    def _update_chart(self) -> None:
        """Update the chart with current data and selected columns.

        Uses filtered_df if filters are applied, otherwise baseline_df.
        """
        # Use filtered data if available, otherwise baseline
        df = self._app_state.filtered_df
        if df is None:
            df = self._app_state.baseline_df

        y_column = self._axis_selector.y_column
        x_column = self._axis_selector.x_column

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

        if not y_column or y_column not in df.columns:
            logger.warning(f"Y column '{y_column}' not found in DataFrame")
            return

        # Show chart and update data
        self._chart_stack.setCurrentIndex(1)
        self._chart_canvas.update_data(
            df,
            y_column=y_column,
            x_column=x_column,
            contrast_colors=self._contrast_colors,
        )

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

        logger.debug(f"Chart updated: y_column='{y_column}', x_column='{x_column}', points={count}")

    def _show_empty_state(self) -> None:
        """Show the empty state message."""
        self._empty_label.setText("Load a data file to explore features")
        self._chart_stack.setCurrentIndex(0)
        self._data_count_label.setText("No data loaded")
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

    def _on_single_filter_applied(self, criteria: FilterCriteria) -> None:
        """Apply a single filter criterion without clearing others.

        Args:
            criteria: The FilterCriteria to apply.
        """
        # Remove any existing filter for the same column
        current_filters = [f for f in self._app_state.filters if f.column != criteria.column]
        # Add the new filter
        current_filters.append(criteria)
        self._app_state.filters = current_filters
        self._apply_current_filters()
        self._update_filter_summary()
        logger.info(f"Single filter applied: {criteria.column}")

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

    def _on_time_range_changed(
        self, start: str | None, end: str | None, all_times: bool
    ) -> None:
        """Handle time range filter change.

        Args:
            start: Start time (HH:MM:SS) or None.
            end: End time (HH:MM:SS) or None.
            all_times: Whether "All Times" is checked.
        """
        self._time_start = start
        self._time_end = end
        self._all_times = all_times
        self._apply_current_filters()
        self._update_filter_summary()
        if all_times:
            logger.info("Time range filter: All Times")
        else:
            logger.info("Time range filter: %s to %s", start, end)

    def _update_filter_summary(self) -> None:
        """Update filter summary label with active filter count."""
        # Count column filters
        column_filter_count = len(self._app_state.filters)

        # Count date filter as active if not "all dates"
        date_filter_active = not self._all_dates

        # Count time filter as active if not "all times"
        time_filter_active = not self._all_times

        # Total active filters
        date_count = 1 if date_filter_active else 0
        time_count = 1 if time_filter_active else 0
        total_active = column_filter_count + date_count + time_count

        # Build display parts
        parts = []

        if date_filter_active:
            date_display = self._filter_panel._date_range_filter.get_display_range()
            if date_display:
                parts.append(date_display)

        if time_filter_active:
            time_display = self._filter_panel._time_range_filter.get_display_range()
            if time_display:
                parts.append(time_display)

        # Build final display string
        if total_active == 0:
            display = "Filters: None"
        else:
            if parts:
                range_info = ", ".join(parts)
                display = f"Filters: {total_active} active ({range_info})"
            else:
                display = f"Filters: {total_active} active"

        self._filter_summary_label.setText(display)

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

        # Apply time range filter
        if (
            not self._all_times
            and self._app_state.column_mapping is not None
            and self._app_state.column_mapping.time is not None
        ):
            df = FilterEngine.apply_time_range(
                df,
                self._app_state.column_mapping.time,
                self._time_start,
                self._time_end,
            )

        # Apply feature filters if any
        if self._app_state.filters:
            df = engine.apply_filters(df, self._app_state.filters)

        # Apply first trigger filter using pre-computed trigger_number column
        if self._app_state.first_trigger_enabled:
            if "trigger_number" in df.columns:
                df = df[df["trigger_number"] == 1].copy()
                logger.debug(
                    "First trigger filter applied: %d rows with trigger_number=1",
                    len(df),
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

    @staticmethod
    def _apply_bounds_filter(
        df: pd.DataFrame,
        x_column: str | None,
        y_column: str | None,
        x_min: float | None,
        x_max: float | None,
        y_min: float | None,
        y_max: float | None,
    ) -> pd.DataFrame:
        """Filter DataFrame to only include rows within axis bounds.

        Args:
            df: Input DataFrame.
            x_column: X axis column name.
            y_column: Y axis column name.
            x_min: Minimum X value (inclusive), or None for no limit.
            x_max: Maximum X value (inclusive), or None for no limit.
            y_min: Minimum Y value (inclusive), or None for no limit.
            y_max: Maximum Y value (inclusive), or None for no limit.

        Returns:
            DataFrame with out-of-bounds rows removed.
        """
        if df is None or df.empty:
            return df

        mask = pd.Series(True, index=df.index)

        # Apply X bounds
        if x_column and x_column in df.columns:
            if x_min is not None:
                mask &= df[x_column] >= x_min
            if x_max is not None:
                mask &= df[x_column] <= x_max

        # Apply Y bounds
        if y_column and y_column in df.columns:
            if y_min is not None:
                mask &= df[y_column] >= y_min
            if y_max is not None:
                mask &= df[y_column] <= y_max

        return df[mask].copy()

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

    def _on_auto_fit(self) -> None:
        """Handle auto-fit request."""
        self._chart_canvas.auto_range()

    def _on_x_bounds_changed(self, x_min: float, x_max: float) -> None:
        """Handle X axis bounds change from selector.

        Stores bounds as filter criteria and re-renders chart with filtered data.

        Args:
            x_min: New X minimum.
            x_max: New X maximum.
        """
        self._x_filter_min = x_min
        self._x_filter_max = x_max

        # Re-render chart with filtered data
        self._update_chart()

        # Sync axis control panel with new bounds
        if self._chart_canvas:
            view_box = self._chart_canvas._plot_widget.getViewBox()
            y_range = view_box.viewRange()[1]
            self._axis_control_panel.set_range(x_min, x_max, y_range[0], y_range[1])

    def _on_y_bounds_changed(self, y_min: float, y_max: float) -> None:
        """Handle Y axis bounds change from selector.

        Args:
            y_min: New Y minimum.
            y_max: New Y maximum.
        """
        if self._chart_canvas is None:
            return

        # Get current X range from chart
        view_box = self._chart_canvas._plot_widget.getViewBox()
        x_range = view_box.viewRange()[0]

        # Update chart with new Y bounds, keep X
        self._chart_canvas._plot_widget.setYRange(y_min, y_max, padding=0)

        # Sync axis control panel
        self._axis_control_panel.set_range(x_range[0], x_range[1], y_min, y_max)

    def _on_chart_range_changed(
        self, x_min: float, x_max: float, y_min: float, y_max: float
    ) -> None:
        """Handle chart range change from user interaction.

        Args:
            x_min: Minimum X value.
            x_max: Maximum X value.
            y_min: Minimum Y value.
            y_max: Maximum Y value.
        """
        # Update axis control panel
        self._axis_control_panel.set_range(x_min, x_max, y_min, y_max)

        # Update axis selector bounds
        self._axis_selector.set_x_bounds(x_min, x_max)
        self._axis_selector.set_y_bounds(y_min, y_max)

    def _on_contrast_toggled(self, checked: bool) -> None:
        """Toggle contrast coloring on scatter plot.

        Args:
            checked: Whether contrast colors are enabled.
        """
        self._contrast_colors = checked
        self._update_chart()

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
