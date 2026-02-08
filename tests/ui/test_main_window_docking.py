"""Tests for MainWindow docking behavior."""

import pytest

from src.ui.main_window import MainWindow


@pytest.mark.widget
class TestMainWindowDocking:
    """Tests for MainWindow docking functionality."""

    def test_main_window_has_dock_manager(self, qtbot):
        """Test MainWindow uses DockManager."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert hasattr(window, "dock_manager")
        assert window.dock_manager is not None

    def test_all_tabs_are_dockable(self, qtbot):
        """Test all workflow tabs are added as docks."""
        window = MainWindow()
        qtbot.addWidget(window)

        expected_tabs = [
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
            "Chart Viewer",
            "Statistics",
            "Chart Viewer",
        ]

        assert window.dock_manager.dock_count() == len(expected_tabs)

        for tab_name in expected_tabs:
            dock = window.dock_manager.get_dock(tab_name)
            assert dock is not None, f"Missing dock: {tab_name}"
