"""Unit tests for Statistics tab."""
import pytest
from PyQt6.QtWidgets import QApplication, QTableWidget, QTabWidget
from src.tabs.statistics_tab import StatisticsTab
from src.core.app_state import AppState


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance() or QApplication([])
    yield app


class TestStatisticsTab:
    def test_creates_successfully(self, app):
        """Test that StatisticsTab can be instantiated."""
        app_state = AppState()
        tab = StatisticsTab(app_state)
        assert tab is not None

    def test_has_5_subtabs(self, app):
        """Test that StatisticsTab has 5 sub-tabs."""
        app_state = AppState()
        tab = StatisticsTab(app_state)
        assert tab._tab_widget.count() == 5

    def test_subtab_names(self, app):
        """Test correct sub-tab names."""
        app_state = AppState()
        tab = StatisticsTab(app_state)
        names = [tab._tab_widget.tabText(i) for i in range(5)]
        assert names == ["MAE Before Win", "MFE Before Loss", "Stop Loss", "Offset", "Scaling"]

    def test_tables_are_tablewidgets(self, app):
        """Test that first 4 sub-tabs contain QTableWidgets."""
        app_state = AppState()
        tab = StatisticsTab(app_state)
        for i in range(4):
            widget = tab._tab_widget.widget(i)
            assert isinstance(widget, QTableWidget)
