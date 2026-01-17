"""Widget tests for TabbedChartContainer component."""

import pytest
from PyQt6.QtWidgets import QLabel
from src.ui.components.tabbed_chart_container import TabbedChartContainer


def test_tabbed_chart_container_shows_first_tab_by_default(qtbot):
    """Container should show the first tab by default."""
    container = TabbedChartContainer()
    container.add_tab("Tab 1", QLabel("Content 1"))
    container.add_tab("Tab 2", QLabel("Content 2"))
    qtbot.addWidget(container)

    assert container.current_index() == 0
    assert container.current_tab_name() == "Tab 1"


def test_tabbed_chart_container_switches_tabs(qtbot):
    """Clicking a tab should switch to that tab."""
    container = TabbedChartContainer()
    container.add_tab("Tab 1", QLabel("Content 1"))
    container.add_tab("Tab 2", QLabel("Content 2"))
    qtbot.addWidget(container)

    container.set_current_index(1)

    assert container.current_index() == 1
    assert container.current_tab_name() == "Tab 2"


def test_tabbed_chart_container_emits_signal_on_tab_change(qtbot):
    """Should emit tab_changed signal when tab changes."""
    container = TabbedChartContainer()
    container.add_tab("Tab 1", QLabel("Content 1"))
    container.add_tab("Tab 2", QLabel("Content 2"))
    qtbot.addWidget(container)

    with qtbot.waitSignal(container.tab_changed, timeout=1000) as blocker:
        container.set_current_index(1)

    assert blocker.args == [1]
