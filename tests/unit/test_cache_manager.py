"""Unit tests for CacheManager."""

from time import sleep

import pandas as pd
import pytest

from src.core.cache_manager import CacheManager


class TestGetCacheKey:
    """Tests for _get_cache_key method."""

    def test_cache_key_consistent(self, tmp_path):
        """Same file+sheet produces same cache key."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        file_path = tmp_path / "test.xlsx"
        file_path.touch()

        key1 = cm._get_cache_key(file_path, "Sheet1")
        key2 = cm._get_cache_key(file_path, "Sheet1")

        assert key1 == key2
        assert len(key1) == 32  # MD5 hex length

    def test_cache_key_differs_for_sheets(self, tmp_path):
        """Different sheets produce different cache keys."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        file_path = tmp_path / "test.xlsx"
        file_path.touch()

        key1 = cm._get_cache_key(file_path, "Sheet1")
        key2 = cm._get_cache_key(file_path, "Sheet2")

        assert key1 != key2

    def test_cache_key_differs_for_files(self, tmp_path):
        """Different files produce different cache keys."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        file1 = tmp_path / "test1.csv"
        file2 = tmp_path / "test2.csv"
        file1.touch()
        file2.touch()

        key1 = cm._get_cache_key(file1)
        key2 = cm._get_cache_key(file2)

        assert key1 != key2

    def test_cache_key_none_sheet_uses_default(self, tmp_path):
        """None sheet uses 'default' string."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        file_path = tmp_path / "test.csv"
        file_path.touch()

        key1 = cm._get_cache_key(file_path, None)
        key2 = cm._get_cache_key(file_path)  # Default None

        assert key1 == key2


class TestIsCacheValid:
    """Tests for is_cache_valid method."""

    def test_is_cache_valid_no_cache(self, tmp_path):
        """Returns False when cache doesn't exist."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        file_path = tmp_path / "test.csv"
        file_path.touch()

        assert cm.is_cache_valid(file_path) is False

    def test_is_cache_valid_outdated(self, tmp_path):
        """Returns False when source is newer than cache."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        file_path = tmp_path / "test.csv"

        # Create cache first
        file_path.touch()
        df = pd.DataFrame({"a": [1, 2, 3]})
        cm.save_to_cache(df, file_path)

        # Wait and touch source to make it newer
        sleep(0.1)
        file_path.touch()

        assert cm.is_cache_valid(file_path) is False

    def test_is_cache_valid_fresh(self, tmp_path):
        """Returns True when cache is newer than source."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        file_path = tmp_path / "test.csv"
        file_path.touch()

        # Wait then save to cache (cache will be newer)
        sleep(0.1)
        df = pd.DataFrame({"a": [1, 2, 3]})
        cm.save_to_cache(df, file_path)

        assert cm.is_cache_valid(file_path) is True


class TestGetCached:
    """Tests for get_cached method."""

    def test_get_cached_returns_none_invalid(self, tmp_path):
        """Returns None when cache is invalid."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        file_path = tmp_path / "test.csv"
        file_path.touch()

        result = cm.get_cached(file_path)
        assert result is None

    def test_get_cached_returns_dataframe(self, tmp_path):
        """Returns DataFrame when cache is valid."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        file_path = tmp_path / "test.csv"
        file_path.touch()

        # Save then retrieve
        sleep(0.1)
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        cm.save_to_cache(df, file_path)

        result = cm.get_cached(file_path)
        assert result is not None
        assert len(result) == 3
        assert list(result.columns) == ["a", "b"]

    def test_get_cached_handles_corrupt(self, tmp_path):
        """Returns None and deletes corrupt cache."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        file_path = tmp_path / "test.csv"
        file_path.touch()

        # Create corrupt cache file
        sleep(0.1)
        cache_path = cm._get_cache_path(file_path)
        cache_path.write_text("not valid parquet data")

        result = cm.get_cached(file_path)

        assert result is None
        assert not cache_path.exists()  # Corrupt file deleted


class TestSaveToCache:
    """Tests for save_to_cache method."""

    def test_save_to_cache_creates_file(self, tmp_path):
        """save_to_cache creates Parquet file."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        file_path = tmp_path / "test.csv"
        file_path.touch()

        df = pd.DataFrame({"a": [1, 2, 3]})
        cm.save_to_cache(df, file_path)

        cache_path = cm._get_cache_path(file_path)
        assert cache_path.exists()
        assert cache_path.suffix == ".parquet"

    def test_save_to_cache_overwrites(self, tmp_path):
        """save_to_cache overwrites existing cache."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        file_path = tmp_path / "test.csv"
        file_path.touch()

        # Save first version
        df1 = pd.DataFrame({"a": [1, 2, 3]})
        cm.save_to_cache(df1, file_path)

        # Save second version
        df2 = pd.DataFrame({"a": [4, 5, 6, 7]})
        cm.save_to_cache(df2, file_path)

        # Verify second version
        sleep(0.1)
        result = cm.get_cached(file_path)
        assert len(result) == 4

    def test_save_to_cache_preserves_data_types(self, tmp_path):
        """save_to_cache preserves DataFrame data types."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        file_path = tmp_path / "test.csv"
        file_path.touch()

        df = pd.DataFrame({
            "int_col": [1, 2, 3],
            "float_col": [1.1, 2.2, 3.3],
            "str_col": ["a", "b", "c"],
        })
        cm.save_to_cache(df, file_path)

        sleep(0.1)
        result = cm.get_cached(file_path)
        assert result["int_col"].dtype == df["int_col"].dtype
        assert result["float_col"].dtype == df["float_col"].dtype
        assert result["str_col"].dtype == df["str_col"].dtype


class TestInvalidate:
    """Tests for invalidate method."""

    def test_invalidate_removes_cache(self, tmp_path):
        """invalidate removes only the specific cache file."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        file_path1 = tmp_path / "test1.csv"
        file_path2 = tmp_path / "test2.csv"
        file_path1.touch()
        file_path2.touch()

        df = pd.DataFrame({"a": [1, 2, 3]})
        cm.save_to_cache(df, file_path1)
        cm.save_to_cache(df, file_path2)

        cache_path1 = cm._get_cache_path(file_path1)
        cache_path2 = cm._get_cache_path(file_path2)
        assert cache_path1.exists()
        assert cache_path2.exists()

        cm.invalidate(file_path1)

        # Only file1's cache should be removed
        assert not cache_path1.exists()
        assert cache_path2.exists()  # file2's cache preserved

    def test_invalidate_nonexistent_cache(self, tmp_path):
        """invalidate handles non-existent cache gracefully."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        file_path = tmp_path / "test.csv"
        file_path.touch()

        # Should not raise
        cm.invalidate(file_path)

    def test_invalidate_specific_sheet(self, tmp_path):
        """invalidate removes only specific sheet's cache."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        file_path = tmp_path / "test.xlsx"
        file_path.touch()

        df = pd.DataFrame({"a": [1, 2, 3]})
        cm.save_to_cache(df, file_path, "Sheet1")
        cm.save_to_cache(df, file_path, "Sheet2")

        cache_path1 = cm._get_cache_path(file_path, "Sheet1")
        cache_path2 = cm._get_cache_path(file_path, "Sheet2")
        assert cache_path1.exists()
        assert cache_path2.exists()

        cm.invalidate(file_path, "Sheet1")

        assert not cache_path1.exists()
        assert cache_path2.exists()  # Sheet2's cache preserved


class TestCacheManagerInit:
    """Tests for CacheManager initialization."""

    def test_cache_dir_created_on_init(self, tmp_path):
        """Cache directory created if doesn't exist."""
        cache_dir = tmp_path / "new_cache_dir"
        assert not cache_dir.exists()

        CacheManager(cache_dir=cache_dir)

        assert cache_dir.exists()

    def test_cache_dir_exists_on_init(self, tmp_path):
        """Handles existing cache directory."""
        cache_dir = tmp_path / "existing_cache"
        cache_dir.mkdir()

        # Should not raise
        cm = CacheManager(cache_dir=cache_dir)
        assert cm.cache_dir == cache_dir


class TestCachePerformance:
    """Performance tests for CacheManager."""

    @pytest.mark.slow
    def test_cache_load_performance(self, tmp_path):
        """Performance: cache load < 500ms for 100k rows."""
        from time import perf_counter

        import numpy as np

        cm = CacheManager(cache_dir=tmp_path / "cache")
        file_path = tmp_path / "test.csv"
        file_path.touch()

        # Create 100k row DataFrame
        np.random.seed(42)
        df = pd.DataFrame({
            "ticker": ["AAPL"] * 100_000,
            "date": pd.date_range("2024-01-01", periods=100_000, freq="h"),
            "gain_pct": np.random.normal(0.5, 3, 100_000),
        })

        # Save to cache
        sleep(0.1)
        cm.save_to_cache(df, file_path)

        # Measure load time
        start = perf_counter()
        result = cm.get_cached(file_path)
        elapsed = perf_counter() - start

        assert result is not None
        assert len(result) == 100_000
        assert elapsed < 0.5, f"Cache load took {elapsed:.3f}s, exceeds 500ms limit"

    @pytest.mark.slow
    def test_cache_save_performance(self, tmp_path):
        """Performance: cache save < 1s for 100k rows."""
        from time import perf_counter

        import numpy as np

        cm = CacheManager(cache_dir=tmp_path / "cache")
        file_path = tmp_path / "test.csv"
        file_path.touch()

        # Create 100k row DataFrame
        np.random.seed(42)
        df = pd.DataFrame({
            "ticker": ["AAPL"] * 100_000,
            "date": pd.date_range("2024-01-01", periods=100_000, freq="h"),
            "gain_pct": np.random.normal(0.5, 3, 100_000),
        })

        # Measure save time
        start = perf_counter()
        cm.save_to_cache(df, file_path)
        elapsed = perf_counter() - start

        assert elapsed < 1.0, f"Cache save took {elapsed:.3f}s, exceeds 1s limit"
