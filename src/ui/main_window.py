"""Main application window for Lumen.

Contains the MainWindow class with dockable tab container for the application workflow.
"""

import logging

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMainWindow

from src.core.app_state import AppState
from src.tabs.breakdown import BreakdownTab
from src.tabs.data_binning import DataBinningTab
from src.tabs.data_input import DataInputTab
from src.tabs.feature_explorer import FeatureExplorerTab
from src.tabs.feature_insights import FeatureInsightsTab
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
        self._setup_menu_bar()

        # Set Data Input as the default active tab
        self.dock_manager.set_active_dock("Data Input")

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
            ("Monte Carlo", MonteCarloTab(self._app_state)),
            ("Feature Insights", FeatureInsightsTab(self._app_state)),
        ]

        for title, widget in tabs:
            self.dock_manager.add_dock(title, widget)

        logger.debug("Dock manager configured with %d docks", self.dock_manager.dock_count())

    @property
    def app_state(self) -> AppState:
        """Get the centralized application state."""
        return self._app_state

    def _setup_menu_bar(self) -> None:
        """Set up the application menu bar with View menu."""
        menu_bar = self.menuBar()

        # View menu
        view_menu = menu_bar.addMenu("&View")
        self._view_menu = view_menu

        # Show All Tabs action
        show_all_action = QAction("Show All Tabs", self)
        show_all_action.triggered.connect(self._on_show_all_tabs)
        view_menu.addAction(show_all_action)

        view_menu.addSeparator()

        # Add checkable action for each tab
        self._tab_actions: dict[str, QAction] = {}
        for title in self.dock_manager.get_all_dock_titles():
            action = QAction(title, self)
            action.setCheckable(True)
            action.setChecked(True)
            action.triggered.connect(lambda checked, t=title: self._on_toggle_tab(t))
            view_menu.addAction(action)
            self._tab_actions[title] = action

        # Update check states when menu is about to show
        view_menu.aboutToShow.connect(self._update_tab_action_states)

        logger.debug("Menu bar configured with View menu")

    def _on_show_all_tabs(self) -> None:
        """Handle Show All Tabs action."""
        self.dock_manager.show_all_docks()
        logger.debug("Restored all tabs")

    def _on_toggle_tab(self, title: str) -> None:
        """Handle tab visibility toggle.

        Args:
            title: Title of the tab to toggle.
        """
        self.dock_manager.toggle_dock_visibility(title)

    def _update_tab_action_states(self) -> None:
        """Update checkable action states to reflect current visibility."""
        for title, action in self._tab_actions.items():
            action.setChecked(self.dock_manager.is_dock_visible(title))
