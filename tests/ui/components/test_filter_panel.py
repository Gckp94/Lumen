"""Tests for FilterPanel component."""

from pytestqt.qtbot import QtBot

from src.core.models import FilterCriteria
from src.ui.components.filter_panel import FilterPanel


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


def test_column_filter_panel_height_shows_6_rows(qtbot: QtBot) -> None:
    """Test that column filter panel height is sufficient for 6 rows."""
    panel = FilterPanel(columns=["col" + str(i) for i in range(15)])
    qtbot.addWidget(panel)

    # Minimum height should accommodate ~6 rows (220px)
    min_height = panel._column_filter_panel.minimumHeight()
    max_height = panel._column_filter_panel.maximumHeight()

    assert min_height == 220, f"Min height {min_height} should be 220"
    assert max_height == 240, f"Max height {max_height} should be 240"


def test_chips_use_flow_layout(qtbot: QtBot) -> None:
    """Chips area uses FlowLayout for wrapping."""
    from src.ui.utils.flow_layout import FlowLayout

    panel = FilterPanel(columns=["col1", "col2"])
    qtbot.addWidget(panel)

    # The chips layout should be a FlowLayout
    assert isinstance(panel._chips_layout, FlowLayout)


def test_chips_frame_scrollable(qtbot: QtBot) -> None:
    """Chips frame should be scrollable when many chips present."""
    from PyQt6.QtWidgets import QScrollArea

    panel = FilterPanel(columns=["col1"])
    qtbot.addWidget(panel)

    # chips_frame should be inside a scroll area
    parent = panel._chips_frame.parent()
    assert isinstance(parent, QScrollArea) or hasattr(panel, '_chips_scroll')
