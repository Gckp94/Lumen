"""Widget tests for the MainWindow."""

import pytest
from PyQt6.QtWidgets import QLabel
from pytestqt.qtbot import QtBot

from src.tabs.monte_carlo import MonteCarloTab
from src.ui.main_window import MainWindow


@pytest.mark.widget
class TestMainWindow:
    """Tests for the MainWindow class."""

    def test_main_window_has_four_tabs(self, qtbot: QtBot) -> None:
        """MainWindow contains exactly 4 tabs."""
        window = MainWindow()
        qtbot.addWidget(window)
        assert window.tab_widget.count() == 4

    def test_tab_titles_match_workflow(self, qtbot: QtBot) -> None:
        """Tab titles match expected workflow order."""
        window = MainWindow()
        qtbot.addWidget(window)
        expected = ["Data Input", "Feature Explorer", "PnL & Trading Stats", "Monte Carlo"]
        for i, title in enumerate(expected):
            assert window.tab_widget.tabText(i) == title

    def test_tabs_not_closable(self, qtbot: QtBot) -> None:
        """Tabs cannot be closed."""
        window = MainWindow()
        qtbot.addWidget(window)
        assert not window.tab_widget.tabsClosable()

    def test_tabs_not_movable(self, qtbot: QtBot) -> None:
        """Tabs cannot be reordered."""
        window = MainWindow()
        qtbot.addWidget(window)
        assert not window.tab_widget.isMovable()

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
