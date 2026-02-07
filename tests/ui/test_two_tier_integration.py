"""Tests for two-tier tab bar integration with dock manager."""

import pytest
from pytestqt.qtbot import QtBot

from src.ui.main_window import MainWindow


class TestTwoTierSync:
    """Test bidirectional sync between bar and docks."""

    def test_dock_activation_updates_bar(self, qtbot: QtBot) -> None:
        """Activating dock should update tab bar selection."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Activate dock directly
        window.dock_manager.set_active_dock("Monte Carlo")

        from src.ui.components.two_tier_tab_bar import TwoTierTabBar

        bar = window.findChild(TwoTierTabBar)

        assert bar.active_tab == "Monte Carlo"
        assert bar.active_category == "SIMULATE"


class TestTwoTierIntegration:
    """Test two-tier navigation integration."""

    def test_main_window_has_two_tier_bar(self, qtbot: QtBot) -> None:
        """Main window should have TwoTierTabBar."""
        window = MainWindow()
        qtbot.addWidget(window)

        from src.ui.components.two_tier_tab_bar import TwoTierTabBar

        bar = window.findChild(TwoTierTabBar)
        assert bar is not None

    def test_tab_click_activates_dock(self, qtbot: QtBot) -> None:
        """Clicking tab in bar should activate corresponding dock."""
        window = MainWindow()
        qtbot.addWidget(window)

        from src.ui.components.two_tier_tab_bar import TwoTierTabBar

        bar = window.findChild(TwoTierTabBar)
        bar.set_active_tab("Statistics")

        assert window.dock_manager.is_dock_visible("Statistics")
