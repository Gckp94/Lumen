"""Tests for FilterPanel component."""

import pytest
from pytestqt.qtbot import QtBot

from src.ui.components.filter_panel import FilterPanel
from src.core.models import FilterCriteria


def test_single_filter_apply_creates_chip(qtbot: QtBot) -> None:
    """Test that applying a single filter creates a visible chip."""
    panel = FilterPanel(columns=["price", "volume"])
    qtbot.addWidget(panel)

    # Simulate single filter applied
    criteria = FilterCriteria(column="price", operator="between", min_val=10.0, max_val=20.0)
    panel._on_single_filter_applied(criteria)

    # Chip should be created
    assert len(panel._filter_chips) == 1
    assert panel._filter_chips[0]._criteria == criteria


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
