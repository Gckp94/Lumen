# tests/unit/test_portfolio_overview_tab.py
"""Unit tests for PortfolioOverviewTab widget."""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
from src.tabs.portfolio_overview import PortfolioOverviewTab
from src.core.app_state import AppState


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def mock_app_state():
    state = MagicMock(spec=AppState)
    return state


class TestPortfolioOverviewTab:
    def test_tab_creates_successfully(self, app, qtbot, mock_app_state):
        tab = PortfolioOverviewTab(mock_app_state)
        qtbot.addWidget(tab)
        assert tab is not None

    def test_tab_has_add_strategy_button(self, app, qtbot, mock_app_state):
        tab = PortfolioOverviewTab(mock_app_state)
        qtbot.addWidget(tab)
        assert tab._add_strategy_btn is not None

    def test_tab_has_account_start_input(self, app, qtbot, mock_app_state):
        tab = PortfolioOverviewTab(mock_app_state)
        qtbot.addWidget(tab)
        assert tab._account_start_spin is not None
        assert tab._account_start_spin.value() == 100_000

    def test_tab_has_strategy_table(self, app, qtbot, mock_app_state):
        tab = PortfolioOverviewTab(mock_app_state)
        qtbot.addWidget(tab)
        assert tab._strategy_table is not None

    def test_tab_has_charts(self, app, qtbot, mock_app_state):
        tab = PortfolioOverviewTab(mock_app_state)
        qtbot.addWidget(tab)
        assert tab._charts is not None
