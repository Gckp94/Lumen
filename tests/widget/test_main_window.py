"""Widget tests for the MainWindow."""

import pytest
from PyQt6.QtGui import QKeySequence
from pytestqt.qtbot import QtBot

from src.tabs.monte_carlo import MonteCarloTab
from src.ui.main_window import MainWindow


@pytest.fixture
def main_window(qtbot: QtBot) -> MainWindow:
    """Create a MainWindow instance for testing."""
    window = MainWindow()
    qtbot.addWidget(window)
    return window


@pytest.mark.widget
class TestViewMenu:
    """Tests for View menu functionality."""

    def test_view_menu_exists(self, main_window):
        """MainWindow should have a View menu."""
        menu_bar = main_window.menuBar()
        view_menu = None
        for action in menu_bar.actions():
            if action.text() == "&View":
                view_menu = action.menu()
                break

        assert view_menu is not None

    def test_view_menu_has_show_all_action(self, main_window):
        """View menu should have 'Show All Tabs' action."""
        menu_bar = main_window.menuBar()
        view_menu = None
        for action in menu_bar.actions():
            if action.text() == "&View":
                view_menu = action.menu()
                break

        action_texts = [a.text() for a in view_menu.actions()]
        assert "Show All Tabs" in action_texts

    def test_view_menu_has_tab_entries(self, main_window: MainWindow) -> None:
        """View menu should have category shortcuts."""
        view_menu = main_window._view_menu
        actions = view_menu.actions()
        action_texts = [a.text() for a in actions]

        # Should have category navigation entries
        assert "Go to ANALYZE" in action_texts
        assert "Go to MONTE CARLO" in action_texts
        assert "Go to FEATURES" in action_texts
        assert "Go to PORTFOLIO" in action_texts
        assert "Go to CHARTS" in action_texts

    def test_show_all_tabs_restores_hidden(self, main_window, qtbot):
        """'Show All Tabs' should restore hidden tabs."""
        # Hide a tab
        main_window.dock_manager.toggle_dock_visibility("Data Input")
        assert not main_window.dock_manager.is_dock_visible("Data Input")

        # Find and trigger Show All Tabs
        menu_bar = main_window.menuBar()
        for action in menu_bar.actions():
            if action.text() == "&View":
                view_menu = action.menu()
                for sub_action in view_menu.actions():
                    if sub_action.text() == "Show All Tabs":
                        sub_action.trigger()
                        break

        assert main_window.dock_manager.is_dock_visible("Data Input")


@pytest.mark.widget
class TestMainWindow:
    """Tests for the MainWindow class."""

    def test_main_window_has_fourteen_docks(self, qtbot: QtBot) -> None:
        """MainWindow contains exactly 14 docks."""
        window = MainWindow()
        qtbot.addWidget(window)
        assert window.dock_manager.dock_count() == 14

    def test_dock_titles_match_workflow(self, qtbot: QtBot) -> None:
        """Dock titles match expected workflow order."""
        window = MainWindow()
        qtbot.addWidget(window)
        expected = [
            "Data Input",
            "Feature Explorer",
            "Breakdown",
            "Data Binning",
            "P&L Stats",
            "Monte Carlo",
            "Parameter Sensitivity",
            "Feature Insights",
            "Portfolio Overview",
            "Portfolio Breakdown",
            "Portfolio Metrics",
            "Statistics",
        ]
        for title in expected:
            assert window.dock_manager.get_dock(title) is not None

    def test_docks_not_closable(self, qtbot: QtBot) -> None:
        """Docks tabs are not closable by default (config flag set)."""
        window = MainWindow()
        qtbot.addWidget(window)
        # DockManager configured with AllTabsHaveCloseButton = False
        import PyQt6Ads as ads
        # Use testConfigFlag method to check if AllTabsHaveCloseButton is disabled
        # The flag should NOT be set (i.e., tabs don't have close buttons)
        assert not window.dock_manager.testConfigFlag(
            ads.CDockManager.eConfigFlag.AllTabsHaveCloseButton
        )

    def test_docks_exist(self, qtbot: QtBot) -> None:
        """All docks are created successfully."""
        window = MainWindow()
        qtbot.addWidget(window)
        assert window.dock_manager.get_dock("Data Input") is not None
        assert window.dock_manager.get_dock("Feature Explorer") is not None
        assert window.dock_manager.get_dock("Breakdown") is not None
        assert window.dock_manager.get_dock("Data Binning") is not None
        assert window.dock_manager.get_dock("P&L Stats") is not None
        assert window.dock_manager.get_dock("Monte Carlo") is not None
        assert window.dock_manager.get_dock("Parameter Sensitivity") is not None
        assert window.dock_manager.get_dock("Feature Insights") is not None
        assert window.dock_manager.get_dock("Portfolio Overview") is not None
        assert window.dock_manager.get_dock("Portfolio Breakdown") is not None
        assert window.dock_manager.get_dock("Portfolio Metrics") is not None
        assert window.dock_manager.get_dock("Statistics") is not None

    def test_window_minimum_size(self, qtbot: QtBot) -> None:
        """Window has correct minimum size."""
        window = MainWindow()
        qtbot.addWidget(window)
        assert window.minimumWidth() == 1280
        assert window.minimumHeight() == 720

    def test_window_title(self, qtbot: QtBot) -> None:
        """Window has correct title."""
        window = MainWindow()
        qtbot.addWidget(window)
        assert window.windowTitle() == "Lumen"


@pytest.mark.widget
class TestMonteCarloTab:
    """Tests for the MonteCarloTab integration with MainWindow."""

    def test_monte_carlo_tab_requires_app_state(self, qtbot: QtBot) -> None:
        """Monte Carlo tab requires app_state parameter."""
        from src.core.app_state import AppState
        app_state = AppState()
        tab = MonteCarloTab(app_state)
        qtbot.addWidget(tab)
        assert tab is not None

    def test_monte_carlo_tab_has_config_panel(self, qtbot: QtBot) -> None:
        """Monte Carlo tab has configuration panel."""
        from src.core.app_state import AppState
        from src.ui.components.monte_carlo_config import MonteCarloConfigPanel
        app_state = AppState()
        tab = MonteCarloTab(app_state)
        qtbot.addWidget(tab)
        config_panel = tab.findChild(MonteCarloConfigPanel)
        assert config_panel is not None


@pytest.mark.widget
class TestKeyboardShortcuts:
    """Tests for keyboard shortcuts."""

    def test_show_all_tabs_shortcut(self, main_window):
        """Show All Tabs should have Ctrl+Shift+T shortcut."""
        menu_bar = main_window.menuBar()
        for action in menu_bar.actions():
            if action.text() == "&View":
                view_menu = action.menu()
                for sub_action in view_menu.actions():
                    if sub_action.text() == "Show All Tabs":
                        assert sub_action.shortcut() == QKeySequence("Ctrl+Shift+T")
                        return
        pytest.fail("Show All Tabs action not found")


@pytest.mark.widget
class TestDefaultTab:
    """Tests for default tab behavior."""

    def test_data_input_is_default_active_tab(self, main_window):
        """Data Input should be the active tab on startup."""
        dock = main_window.dock_manager.get_dock("Data Input")
        assert dock is not None
        assert dock.isCurrentTab()
