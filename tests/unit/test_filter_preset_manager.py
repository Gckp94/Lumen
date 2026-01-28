"""Tests for FilterPresetManager."""

import json
from pathlib import Path

import pytest

from src.core.filter_preset_manager import FilterPresetManager
from src.core.models import FilterCriteria, FilterPreset


class TestFilterPresetManager:
    """Tests for FilterPresetManager."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create a temporary directory for presets."""
        preset_dir = tmp_path / "filters"
        preset_dir.mkdir()
        return preset_dir

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a FilterPresetManager with temp directory."""
        return FilterPresetManager(preset_dir=temp_dir)

    @pytest.fixture
    def sample_preset(self):
        """Create a sample FilterPreset."""
        return FilterPreset(
            name="Test Preset",
            column_filters=[
                FilterCriteria(
                    column="gap_pct",
                    operator="between",
                    min_val=5.0,
                    max_val=15.0,
                )
            ],
            date_range=("2024-01-01", "2024-12-31", False),
            time_range=("09:30:00", "10:30:00", False),
            first_trigger_only=True,
        )

    def test_save_creates_json_file(self, manager, sample_preset, temp_dir):
        """Test that save creates a JSON file."""
        path = manager.save(sample_preset)

        assert path.exists()
        assert path.suffix == ".json"
        assert path.parent == temp_dir

    def test_save_sanitizes_filename(self, manager, temp_dir):
        """Test that save sanitizes preset name for filename."""
        preset = FilterPreset(
            name="High Gap Morning",
            column_filters=[],
            date_range=(None, None, True),
            time_range=(None, None, True),
            first_trigger_only=True,
        )
        path = manager.save(preset)

        assert path.name == "high_gap_morning.json"

    def test_load_returns_preset(self, manager, sample_preset):
        """Test that load returns the saved preset."""
        manager.save(sample_preset)
        loaded = manager.load("Test Preset")

        assert loaded.name == sample_preset.name
        assert len(loaded.column_filters) == 1
        assert loaded.column_filters[0].column == "gap_pct"
        assert loaded.date_range == sample_preset.date_range
        assert loaded.time_range == sample_preset.time_range
        assert loaded.first_trigger_only == sample_preset.first_trigger_only

    def test_load_nonexistent_raises(self, manager):
        """Test that loading nonexistent preset raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            manager.load("Nonexistent")

    def test_list_presets_returns_names(self, manager, sample_preset):
        """Test that list_presets returns preset names."""
        manager.save(sample_preset)
        preset2 = FilterPreset(
            name="Another Preset",
            column_filters=[],
            date_range=(None, None, True),
            time_range=(None, None, True),
            first_trigger_only=False,
        )
        manager.save(preset2)

        names = manager.list_presets()

        assert "Test Preset" in names
        assert "Another Preset" in names
        assert len(names) == 2

    def test_list_presets_empty_directory(self, manager):
        """Test list_presets with no presets."""
        names = manager.list_presets()
        assert names == []

    def test_list_presets_sorted_alphabetically(self, manager):
        """Test that list_presets returns names sorted alphabetically."""
        for name in ["Zebra", "Alpha", "Middle"]:
            preset = FilterPreset(
                name=name,
                column_filters=[],
                date_range=(None, None, True),
                time_range=(None, None, True),
                first_trigger_only=True,
            )
            manager.save(preset)

        names = manager.list_presets()
        assert names == ["Alpha", "Middle", "Zebra"]

    def test_delete_removes_file(self, manager, sample_preset, temp_dir):
        """Test that delete removes the preset file."""
        path = manager.save(sample_preset)
        assert path.exists()

        result = manager.delete("Test Preset")

        assert result is True
        assert not path.exists()

    def test_delete_nonexistent_returns_false(self, manager):
        """Test that deleting nonexistent preset returns False."""
        result = manager.delete("Nonexistent")
        assert result is False

    def test_exists_returns_true_for_existing(self, manager, sample_preset):
        """Test exists returns True for saved preset."""
        manager.save(sample_preset)
        assert manager.exists("Test Preset") is True

    def test_exists_returns_false_for_nonexistent(self, manager):
        """Test exists returns False for nonexistent preset."""
        assert manager.exists("Nonexistent") is False

    def test_save_creates_directory_if_missing(self, tmp_path):
        """Test that save creates preset directory if it doesn't exist."""
        preset_dir = tmp_path / "new_filters"
        manager = FilterPresetManager(preset_dir=preset_dir)
        preset = FilterPreset(
            name="Test",
            column_filters=[],
            date_range=(None, None, True),
            time_range=(None, None, True),
            first_trigger_only=True,
        )

        path = manager.save(preset)

        assert preset_dir.exists()
        assert path.exists()
