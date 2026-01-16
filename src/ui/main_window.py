"""Main application window for Lumen.

Contains the MainWindow class with dockable tab container for the application workflow.
"""

import logging

from PyQt6.QtWidgets import QMainWindow

from src.core.app_state import AppState
from src.tabs.breakdown import BreakdownTab
from src.tabs.data_binning import DataBinningTab
from src.tabs.data_input import DataInputTab
from src.tabs.feature_explorer import FeatureExplorerTab
from src.tabs.monte_carlo import MonteCarloTab
from src.tabs.pnl_stats import PnLStatsTab
from src.ui.dock_manager import DockManager

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window with dockable tab-based workflow."""

    def __init__(self) -> None:
        """Initialize the main window with dock manager."""
        super().__init__()
        self.setWindowTitle("Lumen")
        self.setMinimumSize(1280, 720)

        # Create centralized app state
        self._app_state = AppState()

        # Create dock manager
        self.dock_manager = DockManager(self)
        self.setCentralWidget(self.dock_manager)

        self._setup_docks()
        logger.debug("MainWindow initialized with dockable tabs")

    def _setup_docks(self) -> None:
        """Set up dockable widgets for all workflow tabs."""
        # Add tabs in workflow order, passing AppState where needed
        tabs = [
            ("Data Input", DataInputTab(self._app_state)),
            ("Feature Explorer", FeatureExplorerTab(self._app_state)),
            ("Breakdown", BreakdownTab(self._app_state)),
            ("Data Binning", DataBinningTab(self._app_state)),
            ("PnL & Trading Stats", PnLStatsTab(self._app_state)),
            ("Monte Carlo", MonteCarloTab()),
        ]

        for title, widget in tabs:
            self.dock_manager.add_dock(title, widget)

        logger.debug("Dock manager configured with %d docks", self.dock_manager.dock_count())

    @property
    def app_state(self) -> AppState:
        """Get the centralized application state."""
        return self._app_state
