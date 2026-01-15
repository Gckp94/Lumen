"""Tests for ColumnMapper cache path normalization."""

from pathlib import Path

from src.core.column_mapper import ColumnMapper
from src.core.models import ColumnMapping


class TestCachePathNormalization:
    """Tests for case-insensitive cache path handling on Windows."""

    def test_same_file_different_case_uses_same_cache(self, tmp_path: Path) -> None:
        """Loading same file with different path casing should use same cache."""
        # Create a test mapping
        mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
        )

        mapper = ColumnMapper(cache_dir=tmp_path)

        # Save with uppercase drive letter
        uppercase_path = Path("C:/Users/Test/file.xlsx")
        mapper.save_mapping(uppercase_path, mapping, "Sheet1")

        # Load with lowercase drive letter - should find the same cache
        lowercase_path = Path("c:/Users/Test/file.xlsx")
        loaded = mapper.load_mapping(lowercase_path, "Sheet1")

        assert loaded is not None, "Cache miss due to path case sensitivity"
        assert loaded.gain_pct == "gain_pct"

    def test_hash_is_case_insensitive(self) -> None:
        """Cache hash should be identical regardless of path casing."""
        mapper = ColumnMapper()

        hash1 = mapper._get_file_hash(Path("C:/Users/Test/file.xlsx"), "Sheet1")
        hash2 = mapper._get_file_hash(Path("c:/Users/Test/file.xlsx"), "Sheet1")

        assert hash1 == hash2, f"Hashes differ: {hash1} vs {hash2}"

    def test_hash_normalizes_backslashes(self) -> None:
        """Cache hash should normalize path separators."""
        mapper = ColumnMapper()

        hash1 = mapper._get_file_hash(Path("C:/Users/Test/file.xlsx"), "Sheet1")
        hash2 = mapper._get_file_hash(Path("C:\\Users\\Test\\file.xlsx"), "Sheet1")

        assert hash1 == hash2, f"Hashes differ: {hash1} vs {hash2}"
