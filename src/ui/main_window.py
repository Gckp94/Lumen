"""Main application window for Lumen.

Contains the MainWindow class with dockable tab container for the application workflow.
Uses lazy loading for heavy tabs to improve startup performance.
"""

import logging
from typing import TYPE_CHECKING

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMainWindow

from src.core.app_state import AppState
from src.ui.dock_manager import DockManager
from src.ui.lazy_tab import LazyTabContainer

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

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
        self._apply_menu_styling()

        # Set Data Input as the default active tab
        self.dock_manager.set_active_dock("Data Input")

        logger.debug("MainWindow initialized with dockable tabs")

    def _setup_docks(self) -> None:
        """Set up dockable widgets for all workflow tabs.

        Uses lazy loading for heavy tabs to improve startup performance.
        The Data Input tab is loaded immediately as it's the default tab.
        Other tabs are loaded on first access.
        """
        # Import tab modules here to avoid circular imports and enable lazy loading
        from src.tabs.data_input import DataInputTab

        # Data Input is always loaded immediately (it's the default tab)
        data_input_tab = DataInputTab(self._app_state)
        self.dock_manager.add_dock("Data Input", data_input_tab)

        # Define lazy factories for heavy tabs
        # These are only instantiated when the tab is first accessed
        lazy_tabs: list[tuple[str, "type[QWidget]"]] = [
            ("Feature Explorer", self._create_feature_explorer),
            ("Breakdown", self._create_breakdown),
            ("Data Binning", self._create_data_binning),
            ("PnL & Trading Stats", self._create_pnl_stats),
            ("Monte Carlo", self._create_monte_carlo),
            ("Parameter Sensitivity", self._create_parameter_sensitivity),
            ("Feature Insights", self._create_feature_insights),
            ("Portfolio Overview", self._create_portfolio_overview),
            ("Portfolio Breakdown", self._create_portfolio_breakdown),
            ("Portfolio Metrics", self._create_portfolio_metrics),
            ("Statistics", self._create_statistics),
        ]

        # Store lazy containers for signal connections after loading
        self._lazy_containers: dict[str, LazyTabContainer] = {}

        for title, factory in lazy_tabs:
            container = LazyTabContainer(factory, f"Loading {title}...")
            self._lazy_containers[title] = container
            self.dock_manager.add_dock(title, container)

        # Connect portfolio signals after portfolio tabs are loaded
        # This is deferred until both tabs are accessed
        self._portfolio_signals_connected = False

        logger.debug("Dock manager configured with %d docks (lazy loading enabled)",
                     self.dock_manager.dock_count())

    def _create_feature_explorer(self) -> "QWidget":
        """Factory for Feature Explorer tab."""
        from src.tabs.feature_explorer import FeatureExplorerTab
        return FeatureExplorerTab(self._app_state)

    def _create_breakdown(self) -> "QWidget":
        """Factory for Breakdown tab."""
        from src.tabs.breakdown import BreakdownTab
        return BreakdownTab(self._app_state)

    def _create_data_binning(self) -> "QWidget":
        """Factory for Data Binning tab."""
        from src.tabs.data_binning import DataBinningTab
        return DataBinningTab(self._app_state)

    def _create_pnl_stats(self) -> "QWidget":
        """Factory for PnL & Trading Stats tab."""
        from src.tabs.pnl_stats import PnLStatsTab
        return PnLStatsTab(self._app_state)

    def _create_monte_carlo(self) -> "QWidget":
        """Factory for Monte Carlo tab."""
        from src.tabs.monte_carlo import MonteCarloTab
        return MonteCarloTab(self._app_state)

    def _create_parameter_sensitivity(self) -> "QWidget":
        """Factory for Parameter Sensitivity tab."""
        from src.tabs.parameter_sensitivity import ParameterSensitivityTab
        return ParameterSensitivityTab(self._app_state)

    def _create_feature_insights(self) -> "QWidget":
        """Factory for Feature Insights tab."""
        from src.tabs.feature_insights import FeatureInsightsTab
        return FeatureInsightsTab(self._app_state)

    def _create_portfolio_overview(self) -> "QWidget":
        """Factory for Portfolio Overview tab."""
        from src.tabs.portfolio_overview import PortfolioOverviewTab
        tab = PortfolioOverviewTab(self._app_state)
        # Connect signals when both portfolio tabs are loaded
        self._connect_portfolio_signals_if_ready()
        return tab

    def _create_portfolio_breakdown(self) -> "QWidget":
        """Factory for Portfolio Breakdown tab."""
        from src.tabs.portfolio_breakdown import PortfolioBreakdownTab
        tab = PortfolioBreakdownTab()
        # Connect signals when both portfolio tabs are loaded
        self._connect_portfolio_signals_if_ready()
        return tab

    def _create_portfolio_metrics(self) -> "QWidget":
        """Factory for Portfolio Metrics tab."""
        from src.tabs.portfolio_metrics import PortfolioMetricsTab
        tab = PortfolioMetricsTab()
        # Connect signals when both portfolio tabs are loaded
        self._connect_portfolio_signals_if_ready()
        return tab

    def _create_statistics(self) -> "QWidget":
        """Factory for Statistics tab."""
        from src.tabs.statistics_tab import StatisticsTab
        return StatisticsTab(self._app_state)

    def _connect_portfolio_signals_if_ready(self) -> None:
        """Connect portfolio signals when all portfolio tabs are loaded."""
        if self._portfolio_signals_connected:
            return

        overview_container = self._lazy_containers.get("Portfolio Overview")
        breakdown_container = self._lazy_containers.get("Portfolio Breakdown")
        metrics_container = self._lazy_containers.get("Portfolio Metrics")

        if not all([overview_container, breakdown_container, metrics_container]):
            return

        # Check if all are loaded
        if not (overview_container.is_loaded and
                breakdown_container.is_loaded and
                metrics_container.is_loaded):
            return

        # Connect signals
        overview = overview_container.widget
        breakdown = breakdown_container.widget
        metrics = metrics_container.widget

        if overview and breakdown:
            overview.portfolio_data_changed.connect(breakdown.on_portfolio_data_changed)
        if overview and metrics:
            overview.portfolio_data_changed.connect(metrics.on_portfolio_data_changed)

        self._portfolio_signals_connected = True
        logger.debug("Portfolio signals connected")

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
        show_all_action.setShortcut("Ctrl+Shift+T")
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

    def _apply_menu_styling(self) -> None:
        """Apply custom styling to the menu bar."""
        from src.ui.constants import Colors, Fonts

        menu_stylesheet = f"""
            QMenuBar {{
                background-color: {Colors.BG_BASE};
                color: {Colors.TEXT_PRIMARY};
                font-family: "{Fonts.UI}";
                font-size: 13px;
                padding: 4px 0px;
                border-bottom: 1px solid {Colors.BG_BORDER};
            }}

            QMenuBar::item {{
                background-color: transparent;
                padding: 6px 12px;
                margin: 0px 2px;
                border-radius: 4px;
            }}

            QMenuBar::item:selected {{
                background-color: {Colors.BG_ELEVATED};
            }}

            QMenuBar::item:pressed {{
                background-color: {Colors.BG_SURFACE};
            }}

            QMenu {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                font-family: "{Fonts.UI}";
                font-size: 13px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 6px;
                padding: 6px 0px;
            }}

            QMenu::item {{
                padding: 8px 32px 8px 16px;
                margin: 2px 6px;
                border-radius: 4px;
            }}

            QMenu::item:selected {{
                background-color: {Colors.BG_ELEVATED};
            }}

            QMenu::separator {{
                height: 1px;
                background-color: {Colors.BG_BORDER};
                margin: 6px 12px;
            }}

            QMenu::indicator {{
                width: 16px;
                height: 16px;
                margin-left: 8px;
            }}

            QMenu::indicator:checked {{
                background-color: {Colors.SIGNAL_CYAN};
                border-radius: 3px;
            }}

            QMenu::indicator:unchecked {{
                background-color: transparent;
                border: 1px solid {Colors.TEXT_SECONDARY};
                border-radius: 3px;
            }}
        """
        self.menuBar().setStyleSheet(menu_stylesheet)
