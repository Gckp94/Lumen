"""Parameter Sensitivity tab for testing filter robustness."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

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
    ParameterSensitivityConfig,
    ParameterSensitivityWorker,
)
from src.ui.components.no_scroll_widgets import NoScrollComboBox, NoScrollDoubleSpinBox

if TYPE_CHECKING:
    from src.core.app_state import AppState

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

        self._setup_ui()
        self._connect_signals()

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

        # Placeholder for results
        self._results_label = QLabel("Run an analysis to see results")
        self._results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._results_label)

        return main

    def _connect_signals(self) -> None:
        """Connect widget signals."""
        self._mode_group.buttonClicked.connect(self._on_mode_changed)
        self._run_btn.clicked.connect(self._on_run_clicked)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)

    def _on_mode_changed(self) -> None:
        """Handle mode selection change."""
        is_sweep = self._sweep_radio.isChecked()
        self._resolution_group.setVisible(is_sweep)

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

        config = ParameterSensitivityConfig(
            mode="sweep" if is_sweep else "neighborhood",
            primary_metric=primary_metric,
            grid_resolution=self._resolution_spin.value() if is_sweep else 10,
        )

        # Get baseline data and filters
        baseline_df = self._app_state.baseline_df
        column_mapping = self._app_state.column_mapping
        active_filters = self._app_state.filters or []

        if column_mapping is None:
            logger.warning("No column mapping available")
            self._results_label.setText("Load data first")
            return

        if not active_filters and not is_sweep:
            logger.warning("No active filters for neighborhood scan")
            self._results_label.setText("Apply filters in Feature Explorer first")
            return

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

    def _on_completed(self, results) -> None:
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

    def _on_error(self, message: str) -> None:
        """Handle analysis error."""
        self._run_btn.setVisible(True)
        self._cancel_btn.setVisible(False)
        self._progress_bar.setVisible(False)
        self._results_label.setText(f"Error: {message}")
        logger.error("Sensitivity analysis error: %s", message)

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

    def _display_sweep_results(self, result) -> None:
        """Display sweep results."""
        self._results_label.setText(
            f"<h3>Parameter Sweep Complete</h3>"
            f"<p>Filter: {result.filter_1_name}</p>"
            f"<p>Grid: {len(result.filter_1_values)} points</p>"
        )

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(5000)
