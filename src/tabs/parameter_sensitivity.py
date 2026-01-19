"""Parameter Sensitivity tab for testing filter robustness."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
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
        """Handle run button click."""
        logger.info("Run analysis clicked")
        # TODO: Implement analysis execution

    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        if self._worker:
            self._worker.cancel()

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(5000)
