"""Tests for ColumnFilterPanel.set_filter_values method."""

import pytest
from pytestqt.qtbot import QtBot

from src.core.models import FilterCriteria
from src.ui.components.column_filter_panel import ColumnFilterPanel


class TestColumnFilterPanelSetValues:
    """Tests for ColumnFilterPanel.set_filter_values method."""

    def test_set_filter_values_populates_rows(self, qtbot: QtBot):
        """Test that set_filter_values populates matching rows."""
        panel = ColumnFilterPanel(columns=["gap_pct", "volume", "price"])
        qtbot.addWidget(panel)

        criteria = [
            FilterCriteria(column="gap_pct", operator="between", min_val=5.0, max_val=15.0),
            FilterCriteria(column="volume", operator="not_between", min_val=100.0, max_val=500.0),
        ]

        panel.set_filter_values(criteria)

        active = panel.get_active_criteria()
        assert len(active) == 2

        # Check gap_pct filter
        gap_filter = next(c for c in active if c.column == "gap_pct")
        assert gap_filter.min_val == 5.0
        assert gap_filter.max_val == 15.0
        assert gap_filter.operator == "between"

    def test_set_filter_values_skips_missing_columns(self, qtbot: QtBot):
        """Test that missing columns are skipped without error."""
        panel = ColumnFilterPanel(columns=["gap_pct", "volume"])
        qtbot.addWidget(panel)

        criteria = [
            FilterCriteria(column="gap_pct", operator="between", min_val=5.0, max_val=15.0),
            FilterCriteria(column="nonexistent", operator="between", min_val=1.0, max_val=10.0),
        ]

        # Should not raise
        skipped = panel.set_filter_values(criteria)

        assert "nonexistent" in skipped
        active = panel.get_active_criteria()
        assert len(active) == 1

    def test_set_filter_values_clears_existing(self, qtbot: QtBot):
        """Test that set_filter_values clears existing values first."""
        panel = ColumnFilterPanel(columns=["gap_pct", "volume"])
        qtbot.addWidget(panel)

        # Set initial filters
        panel.set_filter_values([
            FilterCriteria(column="gap_pct", operator="between", min_val=1.0, max_val=2.0),
            FilterCriteria(column="volume", operator="between", min_val=10.0, max_val=20.0),
        ])

        # Set new filters (only gap_pct)
        panel.set_filter_values([
            FilterCriteria(column="gap_pct", operator="between", min_val=5.0, max_val=15.0),
        ])

        active = panel.get_active_criteria()
        assert len(active) == 1
        assert active[0].column == "gap_pct"
        assert active[0].min_val == 5.0
