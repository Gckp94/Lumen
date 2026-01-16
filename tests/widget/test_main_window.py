"""Widget tests for the MainWindow."""

import pytest
from PyQt6.QtWidgets import QLabel
from pytestqt.qtbot import QtBot

from src.tabs.monte_carlo import MonteCarloTab
from src.ui.main_window import MainWindow


@pytest.mark.widget
class TestMainWindow:
    """Tests for the MainWindow class."""

    def test_main_window_has_six_docks(self, qtbot: QtBot) -> None:
        """MainWindow contains exactly 6 docks."""
        window = MainWindow()
        qtbot.addWidget(window)
        assert window.dock_manager.dock_count() == 6

    def test_dock_titles_match_workflow(self, qtbot: QtBot) -> None:
        """Dock titles match expected workflow order."""
        window = MainWindow()
        qtbot.addWidget(window)
        expected = [
            "Data Input",
            "Feature Explorer",
            "Data Binning",
            "PnL & Trading Stats",
            "Breakdown",
            "Monte Carlo",
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
        assert window.dock_manager.get_dock("Data Binning") is not None
        assert window.dock_manager.get_dock("PnL & Trading Stats") is not None
        assert window.dock_manager.get_dock("Breakdown") is not None
        assert window.dock_manager.get_dock("Monte Carlo") is not None

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
    """Tests for the MonteCarloTab placeholder."""

    def test_monte_carlo_shows_placeholder(self, qtbot: QtBot) -> None:
        """Monte Carlo tab shows Phase 3 message."""
        tab = MonteCarloTab()
        qtbot.addWidget(tab)
        labels = tab.findChildren(QLabel)
        assert any("Phase 3" in label.text() for label in labels)

    def test_monte_carlo_message_text(self, qtbot: QtBot) -> None:
        """Monte Carlo tab shows correct placeholder message."""
        tab = MonteCarloTab()
        qtbot.addWidget(tab)
        labels = tab.findChildren(QLabel)
        assert any("Monte Carlo simulations coming in Phase 3" in label.text() for label in labels)
