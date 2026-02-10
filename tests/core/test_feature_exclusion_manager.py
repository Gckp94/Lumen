"""Tests for FeatureExclusionManager."""
import pytest
from pathlib import Path
from src.core.feature_exclusion_manager import FeatureExclusionManager


class TestFeatureExclusionManager:
    """Tests for exclusion persistence."""

    def test_save_and_load_exclusions(self, tmp_path):
        """Exclusions saved for a file can be loaded back."""
        config_dir = tmp_path / ".lumen" / "feature_exclusions"
        manager = FeatureExclusionManager(config_dir)

        source_file = "/path/to/trades.xlsx"
        exclusions = {"volume", "open_price", "close_price"}

        manager.save(source_file, exclusions)
        loaded = manager.load(source_file)

        assert loaded == exclusions

    def test_load_nonexistent_returns_empty_set(self, tmp_path):
        """Loading exclusions for unknown file returns empty set."""
        config_dir = tmp_path / ".lumen" / "feature_exclusions"
        manager = FeatureExclusionManager(config_dir)

        loaded = manager.load("/path/to/unknown.xlsx")

        assert loaded == set()

    def test_different_files_have_separate_exclusions(self, tmp_path):
        """Each source file has independent exclusion set."""
        config_dir = tmp_path / ".lumen" / "feature_exclusions"
        manager = FeatureExclusionManager(config_dir)

        manager.save("/path/to/file1.xlsx", {"col_a", "col_b"})
        manager.save("/path/to/file2.xlsx", {"col_x", "col_y"})

        assert manager.load("/path/to/file1.xlsx") == {"col_a", "col_b"}
        assert manager.load("/path/to/file2.xlsx") == {"col_x", "col_y"}
