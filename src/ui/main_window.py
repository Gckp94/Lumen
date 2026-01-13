"""Main application window for Lumen.

Contains the MainWindow class with tab container for the application workflow.
"""

import logging

from PyQt6.QtWidgets import QMainWindow, QTabWidget

from src.core.app_state import AppState
from src.tabs.data_binning import DataBinningTab
from src.tabs.data_input import DataInputTab
from src.tabs.feature_explorer import FeatureExplorerTab
from src.tabs.monte_carlo import MonteCarloTab
from src.tabs.pnl_stats import PnLStatsTab

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window with tab-based workflow."""

    def __init__(self) -> None:
        """Initialize the main window with tab container."""
        super().__init__()
        self.setWindowTitle("Lumen")
        self.setMinimumSize(1280, 720)

        # Create centralized app state
        self._app_state = AppState()

        self._setup_tabs()
        logger.debug("MainWindow initialized")

    def _setup_tabs(self) -> None:
        """Set up the tab widget with all workflow tabs."""
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(False)
        self.tab_widget.setMovable(False)

        # Add tabs in workflow order, passing AppState where needed
        self.tab_widget.addTab(DataInputTab(self._app_state), "Data Input")
        self.tab_widget.addTab(FeatureExplorerTab(self._app_state), "Feature Explorer")
        self.tab_widget.addTab(DataBinningTab(self._app_state), "Data Binning")
        self.tab_widget.addTab(PnLStatsTab(self._app_state), "PnL & Trading Stats")
        self.tab_widget.addTab(MonteCarloTab(), "Monte Carlo")

        self.setCentralWidget(self.tab_widget)
        logger.debug("Tab widget configured with %d tabs", self.tab_widget.count())

    @property
    def app_state(self) -> AppState:
        """Get the centralized application state."""
        return self._app_state
