"""Tests for FilterPanel component."""

import pytest
from pytestqt.qtbot import QtBot

from src.ui.components.filter_panel import FilterPanel
from src.core.models import FilterCriteria


def test_single_filter_apply_creates_chip(qtbot: QtBot) -> None:
    """Test that applying a single filter creates a visible chip and emits signal."""
    panel = FilterPanel(columns=["price", "volume"])
    qtbot.addWidget(panel)

    # Simulate single filter applied with signal verification
    criteria = FilterCriteria(column="price", operator="between", min_val=10.0, max_val=20.0)
    with qtbot.waitSignal(panel.single_filter_applied, timeout=1000):
        panel._on_single_filter_applied(criteria)

    # Chip should be created
    assert len(panel._filter_chips) == 1
    assert panel._filter_chips[0]._criteria == criteria


def test_single_filter_replaces_existing_for_same_column(qtbot: QtBot) -> None:
    """Test that applying a filter for same column replaces existing (not duplicate)."""
    panel = FilterPanel(columns=["price", "volume"])
    qtbot.addWidget(panel)

    # Apply first filter for "price"
    criteria1 = FilterCriteria(column="price", operator="between", min_val=10.0, max_val=20.0)
    with qtbot.waitSignal(panel.single_filter_applied, timeout=1000):
        panel._on_single_filter_applied(criteria1)

    assert len(panel._filter_chips) == 1
    assert panel._filter_chips[0]._criteria.min_val == 10.0
    assert panel._filter_chips[0]._criteria.max_val == 20.0

    # Apply different filter for same "price" column
    criteria2 = FilterCriteria(column="price", operator="between", min_val=50.0, max_val=100.0)
    with qtbot.waitSignal(panel.single_filter_applied, timeout=1000):
        panel._on_single_filter_applied(criteria2)

    # Should still be only 1 chip (replaced, not duplicated)
    assert len(panel._filter_chips) == 1
    # Should have the new values
    assert panel._filter_chips[0]._criteria.min_val == 50.0
    assert panel._filter_chips[0]._criteria.max_val == 100.0
    assert panel._filter_chips[0]._criteria == criteria2


def test_single_filter_chip_can_be_removed(qtbot: QtBot) -> None:
    """Test that single filter chip can be removed."""
    panel = FilterPanel(columns=["price"])
    qtbot.addWidget(panel)

    criteria = FilterCriteria(column="price", operator="between", min_val=10.0, max_val=20.0)
    panel._on_single_filter_applied(criteria)

    assert len(panel._filter_chips) == 1

    # Simulate chip removal
    panel._on_chip_removed(criteria)

    assert len(panel._filter_chips) == 0
