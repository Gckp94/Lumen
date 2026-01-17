"""Monte Carlo simulation tab for strategy analysis.

This tab provides Monte Carlo simulation controls, displays hero metrics,
and shows detailed metric sections organized by category.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.app_state import AppState
from src.core.monte_carlo import (
    MonteCarloEngine,
    MonteCarloResults,
    extract_gains_from_app_state,
)
from src.ui.components import EmptyState, Toast
from src.ui.components.hero_metric_card import HeroMetricsPanel
from src.ui.components.monte_carlo_charts import MonteCarloChartsSection
from src.ui.components.monte_carlo_config import MonteCarloConfigPanel
from src.ui.components.monte_carlo_section import MonteCarloSectionsContainer
from src.ui.constants import Colors, Fonts, FontSizes, Spacing

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class MonteCarloWorker(QObject):
    """Worker for running Monte Carlo simulations in a background thread.

    Signals:
        progress: Emitted with (completed, total) during simulation.
        finished: Emitted with MonteCarloResults when complete.
        error: Emitted with error message on failure.
    """

    progress = pyqtSignal(int, int)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, engine: MonteCarloEngine, gains: NDArray[np.float64]) -> None:
        """Initialize the worker.

        Args:
            engine: MonteCarloEngine instance to use.
            gains: Array of trade gains for simulation.
        """
        super().__init__()
        self._engine = engine
        self._gains = gains

    def run(self) -> None:
        """Execute the Monte Carlo simulation."""
        try:
            results = self._engine.run(
                self._gains,
                progress_callback=lambda c, t: self.progress.emit(c, t),
            )
            self.finished.emit(results)
        except Exception as e:
            logger.exception("Monte Carlo simulation failed")
            self.error.emit(str(e))


class MonteCarloTab(QWidget):
    """Tab for Monte Carlo simulation and metrics display.

    Layout structure:
    - Top: Configuration Panel (fixed ~80px)
    - Middle: ScrollArea with:
        - EmptyState (when no results)
        - ResultsContainer (when results exist)
            - HeroMetricsPanel (3 key metrics)
            - Metric Sections (6 categories)
    - Bottom: Status bar (simulation time, count)
    """

    def __init__(
        self, app_state: AppState, parent: QWidget | None = None
    ) -> None:
        """Initialize the Monte Carlo tab.

        Args:
            app_state: Centralized application state.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._app_state = app_state
        self._thread: QThread | None = None
        self._worker: MonteCarloWorker | None = None
        self._engine: MonteCarloEngine | None = None
        self._setup_ui()
        self._connect_signals()
        self._initialize_from_state()

    def _setup_ui(self) -> None:
        """Set up the tab layout with scroll area."""
        self.setObjectName("monteCarloTab")
        self.setStyleSheet(f"""
            QWidget#monteCarloTab {{
                background-color: {Colors.BG_SURFACE};
            }}
            QLabel.sectionHeader {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.UI};
                font-size: {FontSizes.H2}px;
                font-weight: bold;
            }}
            QLabel.diamondBullet {{
                color: {Colors.SIGNAL_CYAN};
                font-size: 10px;
            }}
        """)

        # Main layout
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Configuration panel
        self._config_panel = MonteCarloConfigPanel()
        outer_layout.addWidget(self._config_panel)

        # Scroll area for results
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {Colors.BG_SURFACE};
                border: none;
            }}
        """)

        # Content widget inside scroll area
        content_widget = QWidget()
        content_widget.setObjectName("monteCarloContent")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(
            Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG
        )
        content_layout.setSpacing(Spacing.LG)

        # Stacked widget for empty state / results
        self._content_stack = QStackedWidget()

        # Index 0: Empty state (pre-simulation)
        self._empty_state = EmptyState()
        self._empty_state.set_message(
            icon="◇",  # Diamond geometric pattern
            title="No Simulation Results",
            description=(
                "Configure parameters above and run a Monte Carlo simulation "
                "to see statistical analysis of your strategy."
            ),
        )
        self._content_stack.addWidget(self._empty_state)

        # Index 1: Results container
        self._results_container = QWidget()
        self._results_layout = QVBoxLayout(self._results_container)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.setSpacing(Spacing.LG)

        # Hero metrics panel
        self._hero_panel = HeroMetricsPanel()
        self._results_layout.addWidget(self._hero_panel)

        # Sections container
        self._sections_container = MonteCarloSectionsContainer()
        self._results_layout.addWidget(self._sections_container)

        # Charts section (distribution visualizations)
        self._charts_section = MonteCarloChartsSection()
        self._results_layout.addWidget(self._charts_section)

        self._results_layout.addStretch()
        self._content_stack.addWidget(self._results_container)

        content_layout.addWidget(self._content_stack)
        scroll_area.setWidget(content_widget)
        outer_layout.addWidget(scroll_area, stretch=1)

        # Status bar
        self._status_bar = self._create_status_bar()
        outer_layout.addWidget(self._status_bar)

    def _create_status_bar(self) -> QWidget:
        """Create the bottom status bar.

        Returns:
            Status bar widget.
        """
        status_bar = QWidget()
        status_bar.setFixedHeight(32)
        status_bar.setStyleSheet(f"""
            background-color: {Colors.BG_ELEVATED};
            border-top: 1px solid {Colors.BG_BORDER};
        """)

        layout = QHBoxLayout(status_bar)
        layout.setContentsMargins(Spacing.MD, 0, Spacing.MD, 0)
        layout.setSpacing(Spacing.MD)

        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-family: {Fonts.UI};
            font-size: 11px;
        """)

        self._sim_count_label = QLabel("")
        self._sim_count_label.setStyleSheet(f"""
            color: {Colors.TEXT_DISABLED};
            font-family: {Fonts.DATA};
            font-size: 11px;
        """)

        layout.addWidget(self._status_label)
        layout.addStretch()
        layout.addWidget(self._sim_count_label)

        return status_bar

    def _connect_signals(self) -> None:
        """Connect signals for state updates."""
        # Config panel signals
        self._config_panel.run_requested.connect(self._on_run_simulation)
        self._config_panel.cancel_requested.connect(self._on_cancel_simulation)

        # AppState signals
        self._app_state.filtered_data_updated.connect(
            self._on_filtered_data_changed
        )
        self._app_state.first_trigger_toggled.connect(
            self._on_first_trigger_toggled
        )

        # Monte Carlo AppState signals
        self._app_state.monte_carlo_completed.connect(
            self._on_simulation_complete
        )
        self._app_state.monte_carlo_progress.connect(
            self._on_progress
        )
        self._app_state.monte_carlo_error.connect(
            self._on_error
        )

    def _initialize_from_state(self) -> None:
        """Initialize display from AppState."""
        # Update run button enabled state
        self._update_run_button_state()

        # Check if there are existing Monte Carlo results
        results = self._app_state.monte_carlo_results
        if results is not None:
            self._display_results(results)
        else:
            self._show_empty_state()

    def _update_run_button_state(self) -> None:
        """Update whether run button is enabled based on data availability."""
        has_data = self._app_state.has_data
        self._config_panel.set_run_enabled(has_data)

    def _show_empty_state(self, message: str | None = None) -> None:
        """Show the empty state panel.

        Args:
            message: Optional custom message to display.
        """
        if message:
            self._empty_state.set_message(
                icon="◇",
                title="No Simulation Results",
                description=message,
            )
        else:
            self._empty_state.set_message(
                icon="◇",
                title="No Simulation Results",
                description=(
                    "Configure parameters above and run a Monte Carlo simulation "
                    "to see statistical analysis of your strategy."
                ),
            )
        self._content_stack.setCurrentIndex(0)
        self._status_label.setText("Ready")
        self._sim_count_label.setText("")

    def _show_results(self) -> None:
        """Show the results panel."""
        self._content_stack.setCurrentIndex(1)

    def _display_results(self, results: MonteCarloResults) -> None:
        """Display Monte Carlo simulation results.

        Args:
            results: Results from Monte Carlo simulation.
        """
        self._show_results()

        # Update hero metrics panel
        self._hero_panel.update_from_results(results)

        # Update all metric sections
        self._sections_container.update_from_results(results)

        # Update charts section
        self._charts_section.update_from_results(results)

        # Update status bar
        self._status_label.setText(
            f"Simulation complete ({results.num_trades} trades)"
        )
        self._sim_count_label.setText(
            f"{results.config.num_simulations:,} simulations"
        )

    def _on_run_simulation(self) -> None:
        """Handle run simulation request."""
        if self._app_state.monte_carlo_running:
            logger.warning("Simulation already running")
            return

        if not self._app_state.has_data:
            Toast.display(self, "No data loaded", "error")
            return

        try:
            # Extract gains from filtered data (respects user's Filter Panel filters)
            gains = extract_gains_from_app_state(
                self._app_state.baseline_df,
                self._app_state.filtered_df,
                self._app_state.column_mapping,
                self._app_state.first_trigger_enabled,
            )
        except ValueError as e:
            Toast.display(self, str(e), "error")
            return

        # Get configuration from panel (includes position sizing mode)
        config = self._config_panel.get_config()

        # Get user inputs for flat stake and initial capital from app state
        metrics_inputs = self._app_state.metrics_user_inputs
        if metrics_inputs:
            config.flat_stake = metrics_inputs.flat_stake
            config.initial_capital = metrics_inputs.starting_capital

        # Get the CALCULATED fractional kelly from trading metrics
        # Note: metrics_inputs.fractional_kelly is the Kelly FRACTION multiplier (e.g., 25%)
        # but we need the CALCULATED position size (e.g., 2.98% = stop_adjusted_kelly * 0.25)
        if (
            self._app_state.baseline_metrics
            and self._app_state.baseline_metrics.fractional_kelly is not None
        ):
            config.fractional_kelly_pct = self._app_state.baseline_metrics.fractional_kelly
        else:
            # Fallback: use a default fractional kelly
            config.fractional_kelly_pct = 10.0  # Conservative default
            logger.warning("No calculated fractional_kelly available, using default 10%")

        # Create engine
        self._engine = MonteCarloEngine(config)

        # Create worker and thread
        self._thread = QThread()
        self._worker = MonteCarloWorker(self._engine, gains)
        self._worker.moveToThread(self._thread)

        # Connect signals
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_simulation_complete)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._on_error)
        self._worker.error.connect(self._thread.quit)

        # Update UI state
        self._app_state.monte_carlo_running = True
        self._config_panel.set_running(True)
        self._status_label.setText("Running simulation...")
        self._app_state.monte_carlo_started.emit()

        # Start thread
        self._thread.start()
        logger.info(
            "Started Monte Carlo simulation: %d simulations, %d trades",
            config.num_simulations,
            len(gains),
        )

    def _on_cancel_simulation(self) -> None:
        """Handle cancel simulation request."""
        if self._engine is not None:
            self._engine.cancel()
            logger.info("Monte Carlo simulation cancelled")

        self._cleanup_worker()
        self._app_state.monte_carlo_running = False
        self._config_panel.set_running(False)
        self._status_label.setText("Simulation cancelled")

    def _on_progress(self, completed: int, total: int) -> None:
        """Handle progress update from worker.

        Args:
            completed: Number of completed simulations.
            total: Total number of simulations.
        """
        self._config_panel.update_progress(completed, total)
        self._app_state.monte_carlo_progress.emit(completed, total)

    def _on_simulation_complete(self, results: MonteCarloResults) -> None:
        """Handle simulation completion.

        Args:
            results: Simulation results.
        """
        self._cleanup_worker()

        # Store results in app state
        self._app_state.monte_carlo_results = results
        self._app_state.monte_carlo_running = False
        self._app_state.monte_carlo_completed.emit(results)

        # Update UI
        self._config_panel.set_running(False)
        self._display_results(results)

        logger.info(
            "Monte Carlo simulation complete: prob_profit=%.1f%%, risk_of_ruin=%.1f%%",
            results.probability_of_profit * 100,
            results.risk_of_ruin * 100,
        )

    def _on_error(self, error_message: str) -> None:
        """Handle simulation error.

        Args:
            error_message: Error message.
        """
        self._cleanup_worker()

        self._app_state.monte_carlo_running = False
        self._app_state.monte_carlo_error.emit(error_message)

        self._config_panel.set_running(False)
        self._status_label.setText("Simulation failed")

        Toast.display(self, f"Simulation failed: {error_message}", "error")
        logger.error("Monte Carlo simulation error: %s", error_message)

    def _cleanup_worker(self) -> None:
        """Clean up worker and thread."""
        if self._thread is not None:
            if self._thread.isRunning():
                self._thread.quit()
                self._thread.wait()
            self._thread = None
        self._worker = None
        self._engine = None

    def _on_filtered_data_changed(self, filtered_df: object) -> None:
        """Handle filtered data changes - invalidate results.

        Args:
            filtered_df: The new filtered DataFrame.
        """
        # Invalidate Monte Carlo results when data changes
        self._app_state.monte_carlo_results = None
        self._show_empty_state(
            "Data changed. Run simulation to see updated results."
        )
        self._update_run_button_state()

    def _on_first_trigger_toggled(self, enabled: bool) -> None:
        """Handle first trigger toggle change.

        Args:
            enabled: Whether first trigger is enabled.
        """
        # Invalidate results when toggle changes
        if self._app_state.monte_carlo_results is not None:
            self._app_state.monte_carlo_results = None
            self._show_empty_state(
                "Filter settings changed. Run simulation to see updated results."
            )

    def showEvent(self, event: QShowEvent | None) -> None:
        """Handle tab becoming visible.

        Args:
            event: The show event.
        """
        super().showEvent(event)
        # Refresh display from AppState
        self._update_run_button_state()

        results = self._app_state.monte_carlo_results
        if results is not None:
            self._display_results(results)
        else:
            # Restore empty state with appropriate message
            self._show_empty_state()

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._engine is not None:
            self._engine.cancel()
        self._cleanup_worker()
        self._charts_section.clear()
