"""Parameter Sensitivity tab for testing filter robustness."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.core.parameter_sensitivity import (
    NeighborhoodResult,
    ParameterSensitivityConfig,
    ParameterSensitivityWorker,
    SweepResult,
)
from src.ui.components.sweep_chart import SweepChart
from src.ui.components.no_scroll_widgets import NoScrollComboBox, NoScrollDoubleSpinBox
from src.ui.constants import Colors

if TYPE_CHECKING:
    from src.core.app_state import AppState
    from src.core.models import FilterCriteria

logger = logging.getLogger(__name__)


class ParameterSensitivityTab(QWidget):
    """Tab for parameter sensitivity analysis.

    Provides two analysis modes:
    - Neighborhood Scan: Quick robustness check of current filters
    - Parameter Sweep: Deep exploration across parameter ranges
    """

    def __init__(self, app_state: AppState) -> None:
        """Initialize the tab.

        Args:
            app_state: Application state for accessing data and filters.
        """
        super().__init__()
        self._app_state = app_state
        self._worker = None
        self._sweep_result: SweepResult | None = None

        self._setup_ui()
        self._connect_signals()

        # Connect to app state data changes
        self._app_state.data_loaded.connect(self._populate_sweep_columns)

        # Populate if data already loaded
        self._populate_sweep_columns()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create splitter for sidebar and main area
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Sidebar
        sidebar = self._create_sidebar()
        splitter.addWidget(sidebar)

        # Main visualization area
        main_area = self._create_main_area()
        splitter.addWidget(main_area)

        # Set initial splitter sizes (sidebar: 280px, main: stretch)
        splitter.setSizes([280, 800])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

    def _create_sidebar(self) -> QWidget:
        """Create the sidebar with configuration controls."""
        sidebar = QFrame()
        sidebar.setObjectName("sensitivity_sidebar")
        sidebar.setMaximumWidth(320)
        sidebar.setMinimumWidth(250)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Mode selection
        mode_group = QGroupBox("Analysis Mode")
        mode_layout = QVBoxLayout(mode_group)

        self._neighborhood_radio = QRadioButton("Neighborhood Scan")
        self._neighborhood_radio.setToolTip("Quick robustness check of current filter boundaries")
        self._neighborhood_radio.setChecked(True)

        self._sweep_radio = QRadioButton("Parameter Sweep")
        self._sweep_radio.setToolTip("Deep exploration across parameter ranges")

        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._neighborhood_radio, 0)
        self._mode_group.addButton(self._sweep_radio, 1)

        mode_layout.addWidget(self._neighborhood_radio)
        mode_layout.addWidget(self._sweep_radio)
        layout.addWidget(mode_group)

        # Configuration area (changes based on mode)
        self._config_stack = QWidget()
        self._config_layout = QVBoxLayout(self._config_stack)
        self._config_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._config_stack)

        # Metric selection
        metric_group = QGroupBox("Primary Metric")
        metric_layout = QVBoxLayout(metric_group)
        self._metric_combo = QComboBox()
        self._metric_combo.addItems(["Expected Value", "Win Rate", "Profit Factor"])
        metric_layout.addWidget(self._metric_combo)
        layout.addWidget(metric_group)

        # Grid resolution (for sweep mode)
        self._resolution_group = QGroupBox("Grid Resolution")
        resolution_layout = QVBoxLayout(self._resolution_group)
        self._resolution_spin = QSpinBox()
        self._resolution_spin.setRange(5, 25)
        self._resolution_spin.setValue(10)
        resolution_layout.addWidget(self._resolution_spin)
        self._resolution_group.setVisible(False)
        layout.addWidget(self._resolution_group)

        # Sweep filter configuration (for sweep mode)
        self._sweep_config_group = QGroupBox("Sweep Filters")
        sweep_config_layout = QVBoxLayout(self._sweep_config_group)
        sweep_config_layout.setSpacing(8)

        # Filter 1 (X-axis) - required
        filter1_label = QLabel("Filter 1 (X-axis):")
        sweep_config_layout.addWidget(filter1_label)

        self._sweep_filter1_combo = NoScrollComboBox()
        self._sweep_filter1_combo.setPlaceholderText("Select column...")
        sweep_config_layout.addWidget(self._sweep_filter1_combo)

        # Range 1
        range1_layout = QHBoxLayout()
        range1_layout.addWidget(QLabel("Min:"))
        self._sweep_min1_spin = NoScrollDoubleSpinBox()
        self._sweep_min1_spin.setDecimals(4)
        self._sweep_min1_spin.setRange(-1e9, 1e9)
        range1_layout.addWidget(self._sweep_min1_spin)
        range1_layout.addWidget(QLabel("Max:"))
        self._sweep_max1_spin = NoScrollDoubleSpinBox()
        self._sweep_max1_spin.setDecimals(4)
        self._sweep_max1_spin.setRange(-1e9, 1e9)
        range1_layout.addWidget(self._sweep_max1_spin)
        sweep_config_layout.addLayout(range1_layout)

        # Enable 2D sweep checkbox
        self._enable_2d_checkbox = QCheckBox("Enable 2D Sweep")
        sweep_config_layout.addWidget(self._enable_2d_checkbox)

        # Filter 2 (Y-axis) - optional
        self._filter2_container = QWidget()
        filter2_layout = QVBoxLayout(self._filter2_container)
        filter2_layout.setContentsMargins(0, 0, 0, 0)
        filter2_layout.setSpacing(8)

        filter2_label = QLabel("Filter 2 (Y-axis):")
        filter2_layout.addWidget(filter2_label)

        self._sweep_filter2_combo = NoScrollComboBox()
        self._sweep_filter2_combo.setPlaceholderText("Select column...")
        filter2_layout.addWidget(self._sweep_filter2_combo)

        # Range 2
        range2_layout = QHBoxLayout()
        range2_layout.addWidget(QLabel("Min:"))
        self._sweep_min2_spin = NoScrollDoubleSpinBox()
        self._sweep_min2_spin.setDecimals(4)
        self._sweep_min2_spin.setRange(-1e9, 1e9)
        range2_layout.addWidget(self._sweep_min2_spin)
        range2_layout.addWidget(QLabel("Max:"))
        self._sweep_max2_spin = NoScrollDoubleSpinBox()
        self._sweep_max2_spin.setDecimals(4)
        self._sweep_max2_spin.setRange(-1e9, 1e9)
        range2_layout.addWidget(self._sweep_max2_spin)
        filter2_layout.addLayout(range2_layout)

        self._filter2_container.setVisible(False)
        sweep_config_layout.addWidget(self._filter2_container)

        self._sweep_config_group.setVisible(False)
        layout.addWidget(self._sweep_config_group)

        layout.addStretch()

        # Run button and progress
        self._run_btn = QPushButton("Run Analysis")
        self._run_btn.setObjectName("primary_button")
        layout.addWidget(self._run_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setVisible(False)
        layout.addWidget(self._cancel_btn)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        return sidebar

    def _create_main_area(self) -> QWidget:
        """Create the main visualization area."""
        main = QFrame()
        main.setObjectName("sensitivity_main")

        layout = QVBoxLayout(main)
        layout.setContentsMargins(12, 12, 12, 12)

        # Placeholder label (shown when no results)
        self._results_label = QLabel("Run an analysis to see results")
        self._results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._results_label)

        # Results container (hidden initially)
        self._results_container = QWidget()
        results_layout = QVBoxLayout(self._results_container)
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.setSpacing(8)

        # Metric selector row
        metric_row = QHBoxLayout()
        metric_row.addWidget(QLabel("Metric:"))
        self._results_metric_combo = QComboBox()
        self._results_metric_combo.addItems(["win_rate", "profit_factor", "expected_value"])
        self._results_metric_combo.setCurrentText("expected_value")
        self._results_metric_combo.currentTextChanged.connect(self._on_metric_changed)
        metric_row.addWidget(self._results_metric_combo)
        metric_row.addStretch()
        results_layout.addLayout(metric_row)

        # Sweep chart
        self._sweep_chart = SweepChart()
        self._sweep_chart.setMinimumHeight(400)
        results_layout.addWidget(self._sweep_chart, stretch=1)

        # Summary statistics panel
        self._stats_frame = QFrame()
        self._stats_frame.setObjectName("sensitivity_stats")
        stats_layout = QHBoxLayout(self._stats_frame)
        stats_layout.setContentsMargins(8, 8, 8, 8)

        # Min value
        min_layout = QVBoxLayout()
        min_layout.addWidget(QLabel("Min"))
        self._min_label = QLabel("--")
        self._min_label.setStyleSheet(f"color: {Colors.SIGNAL_CORAL}; font-weight: bold;")
        min_layout.addWidget(self._min_label)
        stats_layout.addLayout(min_layout)

        stats_layout.addStretch()

        # Max value
        max_layout = QVBoxLayout()
        max_layout.addWidget(QLabel("Max"))
        self._max_label = QLabel("--")
        self._max_label.setStyleSheet(f"color: {Colors.SIGNAL_CYAN}; font-weight: bold;")
        max_layout.addWidget(self._max_label)
        stats_layout.addLayout(max_layout)

        stats_layout.addStretch()

        # Current position value
        current_layout = QVBoxLayout()
        current_layout.addWidget(QLabel("Current"))
        self._current_label = QLabel("--")
        self._current_label.setStyleSheet(f"color: {Colors.SIGNAL_AMBER}; font-weight: bold;")
        current_layout.addWidget(self._current_label)
        stats_layout.addLayout(current_layout)

        stats_layout.addStretch()

        # Range (max - min)
        range_layout = QVBoxLayout()
        range_layout.addWidget(QLabel("Range"))
        self._range_label = QLabel("--")
        range_layout.addWidget(self._range_label)
        stats_layout.addLayout(range_layout)

        results_layout.addWidget(self._stats_frame)

        self._results_container.setVisible(False)
        layout.addWidget(self._results_container)

        return main

    def _connect_signals(self) -> None:
        """Connect widget signals."""
        self._mode_group.buttonClicked.connect(self._on_mode_changed)
        self._enable_2d_checkbox.toggled.connect(self._on_2d_toggle_changed)
        self._run_btn.clicked.connect(self._on_run_clicked)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        self._sweep_filter1_combo.currentTextChanged.connect(self._on_filter1_selected)
        self._sweep_filter2_combo.currentTextChanged.connect(self._on_filter2_selected)

    def _on_mode_changed(self) -> None:
        """Handle mode selection change."""
        is_sweep = self._sweep_radio.isChecked()
        self._resolution_group.setVisible(is_sweep)
        self._sweep_config_group.setVisible(is_sweep)

    def _get_analyzable_filters(
        self, filters: list[FilterCriteria]
    ) -> tuple[list[FilterCriteria], list[FilterCriteria]]:
        """Separate filters into analyzable and partial (skipped).

        Neighborhood scan requires both min_val and max_val to perturb ranges.

        Args:
            filters: List of all active filters.

        Returns:
            Tuple of (analyzable_filters, partial_filters).
        """
        analyzable = []
        partial = []
        for f in filters:
            if f.min_val is not None and f.max_val is not None:
                analyzable.append(f)
            else:
                partial.append(f)
        return analyzable, partial

    def _on_2d_toggle_changed(self, enabled: bool) -> None:
        """Handle 2D sweep toggle change."""
        self._filter2_container.setVisible(enabled)

    def _on_filter1_selected(self, column_name: str) -> None:
        """Handle filter 1 column selection - auto-fill range from data."""
        if not column_name or not self._app_state.has_data:
            return

        baseline_df = self._app_state.baseline_df
        if baseline_df is None or column_name not in baseline_df.columns:
            return

        col_data = baseline_df[column_name].dropna()
        if len(col_data) == 0:
            return

        min_val = float(col_data.min())
        max_val = float(col_data.max())

        self._sweep_min1_spin.setValue(min_val)
        self._sweep_max1_spin.setValue(max_val)

        logger.debug("Filter 1 '%s' range: %.4f to %.4f", column_name, min_val, max_val)

    def _on_filter2_selected(self, column_name: str) -> None:
        """Handle filter 2 column selection - auto-fill range from data."""
        if not column_name or not self._app_state.has_data:
            return

        baseline_df = self._app_state.baseline_df
        if baseline_df is None or column_name not in baseline_df.columns:
            return

        col_data = baseline_df[column_name].dropna()
        if len(col_data) == 0:
            return

        min_val = float(col_data.min())
        max_val = float(col_data.max())

        self._sweep_min2_spin.setValue(min_val)
        self._sweep_max2_spin.setValue(max_val)

        logger.debug("Filter 2 '%s' range: %.4f to %.4f", column_name, min_val, max_val)

    def _populate_sweep_columns(self) -> None:
        """Populate sweep filter combo boxes with numeric columns from data."""
        import pandas as pd

        # Clear existing items
        self._sweep_filter1_combo.clear()
        self._sweep_filter2_combo.clear()

        if not self._app_state.has_data:
            return

        baseline_df = self._app_state.baseline_df
        if baseline_df is None or not isinstance(baseline_df, pd.DataFrame):
            return

        # Get numeric columns
        numeric_cols = baseline_df.select_dtypes(
            include=["int64", "float64", "int32", "float32"]
        ).columns.tolist()

        if not numeric_cols:
            return

        # Add to combo boxes
        self._sweep_filter1_combo.addItems(numeric_cols)
        self._sweep_filter2_combo.addItems(numeric_cols)

        logger.debug("Populated sweep combos with %d numeric columns", len(numeric_cols))

    def _on_run_clicked(self) -> None:
        """Handle run button click - start analysis."""
        if not self._app_state.has_data:
            logger.warning("No data loaded")
            return

        # Build config from UI state
        is_sweep = self._sweep_radio.isChecked()
        metric_map = {
            "Expected Value": "expected_value",
            "Win Rate": "win_rate",
            "Profit Factor": "profit_factor",
        }
        primary_metric = metric_map.get(self._metric_combo.currentText(), "expected_value")

        # Build sweep filter parameters if in sweep mode
        sweep_filter_1 = None
        sweep_range_1 = None
        sweep_filter_2 = None
        sweep_range_2 = None

        if is_sweep:
            sweep_filter_1 = self._sweep_filter1_combo.currentText()
            if not sweep_filter_1:
                logger.warning("No filter 1 column selected for sweep")
                self._results_label.setText("Select a column for Filter 1")
                return

            sweep_range_1 = (
                self._sweep_min1_spin.value(),
                self._sweep_max1_spin.value(),
            )

            if self._enable_2d_checkbox.isChecked():
                sweep_filter_2 = self._sweep_filter2_combo.currentText()
                if not sweep_filter_2:
                    logger.warning("No filter 2 column selected for 2D sweep")
                    self._results_label.setText("Select a column for Filter 2")
                    return
                sweep_range_2 = (
                    self._sweep_min2_spin.value(),
                    self._sweep_max2_spin.value(),
                )

        config = ParameterSensitivityConfig(
            mode="sweep" if is_sweep else "neighborhood",
            primary_metric=primary_metric,
            grid_resolution=self._resolution_spin.value() if is_sweep else 10,
            sweep_filter_1=sweep_filter_1,
            sweep_range_1=sweep_range_1,
            sweep_filter_2=sweep_filter_2,
            sweep_range_2=sweep_range_2,
        )

        # Get baseline data and filters
        baseline_df = self._app_state.baseline_df
        column_mapping = self._app_state.column_mapping
        active_filters = self._app_state.filters or []

        if column_mapping is None:
            logger.warning("No column mapping available")
            self._results_label.setText("Load data first")
            return

        if not is_sweep:
            if not active_filters:
                logger.warning("No active filters for neighborhood scan")
                self._results_label.setText("Apply filters in Feature Explorer first")
                return

            analyzable, partial = self._get_analyzable_filters(active_filters)
            if not analyzable:
                logger.warning(
                    f"No analyzable filters: {len(partial)} filters have partial bounds"
                )
                self._results_label.setText(
                    f"All {len(partial)} filter(s) have partial bounds (missing min or max).\n"
                    "Neighborhood scan requires filters with both min and max values."
                )
                return

        # Clear previous results
        self._sweep_result = None
        self._results_label.setText("Running analysis...")
        self._results_label.setVisible(True)
        self._results_container.setVisible(False)

        # Start worker
        self._worker = ParameterSensitivityWorker(
            config=config,
            baseline_df=baseline_df,
            column_mapping=column_mapping,
            active_filters=active_filters,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.completed.connect(self._on_completed)
        self._worker.error.connect(self._on_error)
        self._worker.start()

        # Update UI state
        self._run_btn.setVisible(False)
        self._cancel_btn.setVisible(True)
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)

    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        if self._worker:
            self._worker.cancel()

    def _on_progress(self, current: int, total: int) -> None:
        """Handle progress update."""
        if total > 0:
            self._progress_bar.setValue(int(current / total * 100))

    def _on_completed(self, results: list[NeighborhoodResult] | SweepResult) -> None:
        """Handle analysis completion."""
        self._run_btn.setVisible(True)
        self._cancel_btn.setVisible(False)
        self._progress_bar.setVisible(False)

        if isinstance(results, list):
            # Neighborhood scan results
            self._display_neighborhood_results(results)
        else:
            # Sweep result
            self._display_sweep_results(results)

    def _on_error(self, error_msg: str) -> None:
        """Handle worker error."""
        self._run_btn.setVisible(True)
        self._cancel_btn.setVisible(False)
        self._progress_bar.setVisible(False)
        self._results_label.setText(f"Error: {error_msg}")
        self._results_label.setVisible(True)
        self._results_container.setVisible(False)
        logging.error("Parameter sensitivity error: %s", error_msg)

    def _display_neighborhood_results(self, results: list) -> None:
        """Display neighborhood scan results."""
        if not results:
            self._results_label.setText("No filters to analyze")
            return

        # Build summary text
        lines = ["<h3>Neighborhood Scan Results</h3>"]
        for r in results:
            status_color = {"robust": "#22C55E", "caution": "#F59E0B", "fragile": "#EF4444"}
            color = status_color.get(r.status, "#64748B")
            lines.append(
                f"<p><b>{r.filter_name}</b>: "
                f"<span style='color:{color}'>{r.status.upper()}</span> "
                f"(worst: -{r.worst_degradation:.1f}% at ±{r.worst_level*100:.0f}%)</p>"
            )

        self._results_label.setText("".join(lines))

    def _display_sweep_results(self, result: SweepResult) -> None:
        """Display sweep results in the chart.

        Args:
            result: SweepResult from the sensitivity engine.
        """
        if result is None or not result.metric_grids:
            self._results_label.setText("No results to display")
            self._results_label.setVisible(True)
            self._results_container.setVisible(False)
            return

        self._sweep_result = result

        # Hide placeholder, show results container
        self._results_label.setVisible(False)
        self._results_container.setVisible(True)

        # Get current metric
        metric_name = self._results_metric_combo.currentText()

        # Validate metric exists
        if metric_name not in result.metric_grids:
            # Fall back to first available metric
            metric_name = next(iter(result.metric_grids.keys()))
            self._results_metric_combo.setCurrentText(metric_name)

        # Display based on dimensionality
        if result.filter_2_name is None:
            # 1D sweep - line chart
            self._sweep_chart.set_1d_data(
                x_values=result.filter_1_values,
                y_values=result.metric_grids[metric_name],
                x_label=result.filter_1_name,
                y_label=metric_name,
            )

            # Mark current position if available
            if result.current_position is not None:
                self._sweep_chart.set_current_position(x_index=result.current_position[0])
        else:
            # 2D sweep - heatmap
            self._sweep_chart.set_2d_data(
                x_values=result.filter_1_values,
                y_values=result.filter_2_values,
                z_values=result.metric_grids[metric_name],
                x_label=result.filter_1_name,
                y_label=result.filter_2_name,
                z_label=metric_name,
            )

            # Mark current position if available
            if result.current_position is not None:
                self._sweep_chart.set_current_position(
                    x_index=result.current_position[0],
                    y_index=result.current_position[1],
                )

        # Update summary statistics
        self._update_summary_stats(metric_name)

    def _on_metric_changed(self, metric_name: str) -> None:
        """Handle metric selection change.

        Args:
            metric_name: Selected metric name.
        """
        if self._sweep_result is None:
            return

        # Re-display with new metric
        self._display_sweep_results(self._sweep_result)

    def _update_summary_stats(self, metric_name: str) -> None:
        """Update summary statistics display.

        Args:
            metric_name: Current metric name.
        """
        if self._sweep_result is None:
            return

        values = self._sweep_result.metric_grids[metric_name]
        min_val = float(np.min(values))
        max_val = float(np.max(values))
        range_val = max_val - min_val

        # Format based on metric type
        if metric_name == "win_rate":
            fmt = lambda v: f"{v:.1%}"
        elif metric_name == "profit_factor":
            fmt = lambda v: f"{v:.2f}"
        else:
            fmt = lambda v: f"${v:.2f}"

        self._min_label.setText(fmt(min_val))
        self._max_label.setText(fmt(max_val))
        self._range_label.setText(fmt(range_val))

        # Current position value
        if self._sweep_result.current_position is not None:
            pos = self._sweep_result.current_position
            if self._sweep_result.filter_2_name is None:
                current_val = float(values[pos[0]])
            else:
                current_val = float(values[pos[1], pos[0]])
            self._current_label.setText(fmt(current_val))
        else:
            self._current_label.setText("--")

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(5000)
