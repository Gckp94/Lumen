"""Tests for FilterPanel get_full_state and set_full_state methods."""

import pytest
from pytestqt.qtbot import QtBot

from src.core.models import FilterCriteria, FilterPreset
from src.ui.components.filter_panel import FilterPanel


class TestFilterPanelState:
    """Tests for FilterPanel state methods."""

    def test_get_full_state_returns_preset(self, qtbot: QtBot):
        """Test get_full_state returns a FilterPreset."""
        panel = FilterPanel(columns=["gap_pct", "volume"])
        qtbot.addWidget(panel)

        state = panel.get_full_state("Test")

        assert isinstance(state, FilterPreset)
        assert state.name == "Test"

    def test_set_full_state_applies_filters(self, qtbot: QtBot):
        """Test set_full_state applies all filter values."""
        panel = FilterPanel(columns=["gap_pct", "volume"])
        qtbot.addWidget(panel)

        preset = FilterPreset(
            name="Test",
            column_filters=[
                FilterCriteria(column="gap_pct", operator="between", min_val=5.0, max_val=15.0),
            ],
            date_range=("2024-01-01", "2024-06-30", False),
            time_range=("09:30:00", "10:30:00", False),
            first_trigger_only=False,
        )

        skipped = panel.set_full_state(preset)

        assert skipped == []
        # Verify state was applied
        state = panel.get_full_state("Check")
        assert len(state.column_filters) == 1
        assert state.first_trigger_only is False

    def test_set_full_state_returns_skipped_columns(self, qtbot: QtBot):
        """Test set_full_state returns list of skipped columns."""
        panel = FilterPanel(columns=["gap_pct"])
        qtbot.addWidget(panel)

        preset = FilterPreset(
            name="Test",
            column_filters=[
                FilterCriteria(column="gap_pct", operator="between", min_val=5.0, max_val=15.0),
                FilterCriteria(column="nonexistent", operator="between", min_val=1.0, max_val=10.0),
            ],
            date_range=(None, None, True),
            time_range=(None, None, True),
            first_trigger_only=True,
        )

        skipped = panel.set_full_state(preset)

        assert "nonexistent" in skipped
