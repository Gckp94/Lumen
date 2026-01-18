"""Tests for ExcludeColumnPanel component."""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.ui.components.exclude_column_panel import ExcludeColumnPanel


@pytest.fixture
def panel(qtbot):
    """Create panel with sample columns."""
    columns = ["gain_pct", "volume", "close", "open", "high", "low"]
    widget = ExcludeColumnPanel(columns)
    qtbot.addWidget(widget)
    return widget


def test_panel_displays_all_columns(panel):
    """Panel shows all provided columns."""
    assert panel._list_widget.count() == 6


def test_panel_checks_excluded_columns(qtbot):
    """Panel checks columns in excluded set."""
    columns = ["gain_pct", "volume", "close"]
    excluded = {"gain_pct", "close"}
    widget = ExcludeColumnPanel(columns, excluded)
    qtbot.addWidget(widget)

    # Check items by text
    for i in range(widget._list_widget.count()):
        item = widget._list_widget.item(i)
        if item.text() in excluded:
            assert item.checkState() == Qt.CheckState.Checked
        else:
            assert item.checkState() == Qt.CheckState.Unchecked


def test_panel_emits_exclusion_changed(panel, qtbot):
    """Panel emits signal when exclusion changes."""
    with qtbot.waitSignal(panel.exclusion_changed, timeout=1000):
        item = panel._list_widget.item(0)
        # Change from Unchecked (default) to Checked to trigger signal
        item.setCheckState(Qt.CheckState.Checked)


def test_get_excluded_returns_checked_columns(qtbot):
    """get_excluded() returns set of checked column names."""
    columns = ["a", "b", "c"]
    excluded = {"a", "c"}
    widget = ExcludeColumnPanel(columns, excluded)
    qtbot.addWidget(widget)

    result = widget.get_excluded()
    assert result == {"a", "c"}


def test_search_filters_list(panel, qtbot):
    """Search box filters visible items."""
    panel._search_input.setText("vol")
    # Only "volume" should be visible
    visible_count = sum(
        1 for i in range(panel._list_widget.count())
        if not panel._list_widget.item(i).isHidden()
    )
    assert visible_count == 1
