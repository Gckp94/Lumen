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
        """Set up the central widget with category bar above native dock tabs."""
        from PyQt6.QtWidgets import QVBoxLayout, QWidget

        from src.ui.components.category_bar import CategoryBar

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Category bar at top
        self._category_bar = CategoryBar()
        self._category_bar.category_changed.connect(self._on_category_changed)
        layout.addWidget(self._category_bar)

        # Dock manager below with native tabs visible
        layout.addWidget(self.dock_manager, 1)

        # Sync dock activation back to category bar
        self.dock_manager.dock_activated.connect(self._on_dock_activated)

        self.setCentralWidget(central)

        # Show only ANALYZE category tabs initially
        self._on_category_changed("ANALYZE")

    def _on_category_changed(self, category: str) -> None:
        """Handle category change - show only tabs in that category."""
        from src.ui.tab_categories import get_tabs_in_category

        tabs_to_show = get_tabs_in_category(category)
        self.dock_manager.show_only_tabs(tabs_to_show)

    def _on_dock_activated(self, tab_name: str) -> None:
        """Handle dock activation - update category bar if needed."""
        from src.ui.tab_categories import get_category_for_tab

        category = get_category_for_tab(tab_name)
        if category and category != self._category_bar.active_category:
            self._category_bar.set_active_category(category)

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

        # Category shortcuts
        from src.ui.tab_categories import get_all_categories

        for i, category in enumerate(get_all_categories(), 1):
            action = QAction(f"Go to {category}", self)
            action.setShortcut(f"Ctrl+{i}")
            action.triggered.connect(lambda checked, c=category: self._goto_category(c))
            view_menu.addAction(action)

        view_menu.addSeparator()

        # Show All Tabs action
        show_all_action = QAction("Show All Tabs", self)
        show_all_action.setShortcut("Ctrl+Shift+T")
        show_all_action.triggered.connect(self._on_show_all_tabs)
        view_menu.addAction(show_all_action)

        logger.debug("Menu bar configured with View menu")

    def _goto_category(self, category: str) -> None:
        """Switch to a category."""
        self._category_bar.set_active_category(category)
        self._on_category_changed(category)

    def _on_show_all_tabs(self) -> None:
        """Handle Show All Tabs action."""
        self.dock_manager.show_all_docks()
        logger.debug("Restored all tabs")

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
