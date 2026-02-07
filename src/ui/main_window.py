"""Main application window for Lumen.

Contains the MainWindow class with dockable tab container for the application workflow.
"""

import logging

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMainWindow

from src.core.app_state import AppState
from src.core.state_exporter import StateExporter
from src.tabs.breakdown import BreakdownTab
from src.tabs.chart_viewer import ChartViewerTab
from src.tabs.data_binning import DataBinningTab
from src.tabs.data_input import DataInputTab
from src.tabs.feature_explorer import FeatureExplorerTab
from src.tabs.feature_impact import FeatureImpactTab
from src.tabs.feature_insights import FeatureInsightsTab
from src.tabs.monte_carlo import MonteCarloTab
from src.tabs.parameter_sensitivity import ParameterSensitivityTab
from src.tabs.pnl_stats import PnLStatsTab
from src.tabs.portfolio_breakdown import PortfolioBreakdownTab
from src.tabs.portfolio_metrics import PortfolioMetricsTab
from src.tabs.portfolio_overview import PortfolioOverviewTab
from src.tabs.statistics_tab import StatisticsTab
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

        self._setup_docks()
        self._setup_central_widget()
        self._setup_menu_bar()
        self._apply_menu_styling()

        # Set Data Input as the default active tab
        self.dock_manager.set_active_dock("Data Input")

        # State exporter for MCP bridge
        self._state_exporter = StateExporter(self._app_state, self)

        logger.debug("MainWindow initialized with dockable tabs")

    def _setup_docks(self) -> None:
        """Set up dockable widgets for all workflow tabs."""
        # Create Portfolio tabs with signal connection
        portfolio_overview = PortfolioOverviewTab(self._app_state)
        portfolio_breakdown = PortfolioBreakdownTab()

        # Connect Portfolio Overview signal to Breakdown handler
        portfolio_overview.portfolio_data_changed.connect(
            portfolio_breakdown.on_portfolio_data_changed
        )

        portfolio_metrics = PortfolioMetricsTab()

        # Connect Portfolio Overview signal to Portfolio Metrics handler
        portfolio_overview.portfolio_data_changed.connect(
            portfolio_metrics.on_portfolio_data_changed
        )

        # Add tabs in workflow order, passing AppState where needed
        tabs = [
            ("Data Input", DataInputTab(self._app_state)),
            ("Feature Explorer", FeatureExplorerTab(self._app_state)),
            ("Breakdown", BreakdownTab(self._app_state)),
            ("Data Binning", DataBinningTab(self._app_state)),
            ("PnL & Trading Stats", PnLStatsTab(self._app_state)),
            ("Monte Carlo", MonteCarloTab(self._app_state)),
            ("Parameter Sensitivity", ParameterSensitivityTab(self._app_state)),
            ("Feature Insights", FeatureInsightsTab(self._app_state)),
            ("Feature Impact", FeatureImpactTab(self._app_state)),
            ("Portfolio Overview", portfolio_overview),
            ("Portfolio Breakdown", portfolio_breakdown),
            ("Portfolio Metrics", portfolio_metrics),
            ("Chart Viewer", ChartViewerTab(self._app_state)),
            ("Statistics", StatisticsTab(self._app_state)),
        ]

        for title, widget in tabs:
            self.dock_manager.add_dock(title, widget)

        logger.debug("Dock manager configured with %d docks", self.dock_manager.dock_count())

    def _setup_central_widget(self) -> None:
        """Set up the central widget with two-tier navigation."""
        from PyQt6.QtWidgets import QVBoxLayout, QWidget

        from src.ui.components.two_tier_tab_bar import TwoTierTabBar

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Two-tier tab bar at top
        self._tab_bar = TwoTierTabBar()
        self._tab_bar.tab_activated.connect(self._on_tab_bar_activated)
        layout.addWidget(self._tab_bar)

        # Dock manager below
        layout.addWidget(self.dock_manager, 1)

        self.setCentralWidget(central)

        # Hide native tabs since we have our custom navigation
        self.dock_manager.hide_native_tab_bar()

    def _on_tab_bar_activated(self, tab_name: str) -> None:
        """Handle tab activation from two-tier bar."""
        self.dock_manager.set_active_dock(tab_name)

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

    def closeEvent(self, event: object) -> None:
        """Clean up state exporter on close."""
        self._state_exporter.cleanup()
        super().closeEvent(event)  # type: ignore[arg-type]
