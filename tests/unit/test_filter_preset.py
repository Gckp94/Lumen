"""Tests for FilterPreset dataclass."""

import pytest

from src.core.models import FilterCriteria, FilterPreset


class TestFilterPreset:
    """Tests for FilterPreset dataclass."""

    def test_create_filter_preset(self):
        """Test creating a FilterPreset with all fields."""
        criteria = FilterCriteria(
            column="gap_pct",
            operator="between",
            min_val=5.0,
            max_val=15.0,
        )
        preset = FilterPreset(
            name="Test Preset",
            column_filters=[criteria],
            date_range=("2024-01-01", "2024-12-31", False),
            time_range=("09:30:00", "10:30:00", False),
            first_trigger_only=True,
        )

        assert preset.name == "Test Preset"
        assert len(preset.column_filters) == 1
        assert preset.column_filters[0].column == "gap_pct"
        assert preset.date_range == ("2024-01-01", "2024-12-31", False)
        assert preset.time_range == ("09:30:00", "10:30:00", False)
        assert preset.first_trigger_only is True
        assert preset.created is None

    def test_filter_preset_with_created_timestamp(self):
        """Test FilterPreset with created timestamp."""
        preset = FilterPreset(
            name="Timestamped",
            column_filters=[],
            date_range=(None, None, True),
            time_range=(None, None, True),
            first_trigger_only=False,
            created="2026-01-28T10:30:00",
        )

        assert preset.created == "2026-01-28T10:30:00"

    def test_filter_preset_empty_filters(self):
        """Test FilterPreset with no column filters."""
        preset = FilterPreset(
            name="Empty",
            column_filters=[],
            date_range=(None, None, True),
            time_range=(None, None, True),
            first_trigger_only=True,
        )

        assert preset.column_filters == []
