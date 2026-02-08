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


class TestStreamCsvToCache:
    """Tests for stream_csv_to_cache method."""

    def _write_csv(self, path, df):
        """Helper to write a DataFrame as CSV."""
        df.to_csv(path, index=False)

    def test_stream_creates_parquet_cache(self, tmp_path):
        """stream_csv_to_cache creates a valid Parquet cache file."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        csv_path = tmp_path / "data.csv"
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        self._write_csv(csv_path, df)

        result_path = cm.stream_csv_to_cache(csv_path)

        assert result_path.exists()
        assert result_path.suffix == ".parquet"
        cached = pd.read_parquet(result_path)
        assert len(cached) == 3
        assert list(cached.columns) == ["a", "b"]

    def test_stream_data_matches_source(self, tmp_path):
        """Streamed Parquet content matches the original CSV data."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        csv_path = tmp_path / "data.csv"
        df = pd.DataFrame({
            "int_col": [10, 20, 30],
            "float_col": [1.5, 2.5, 3.5],
            "str_col": ["alpha", "beta", "gamma"],
        })
        self._write_csv(csv_path, df)

        cm.stream_csv_to_cache(csv_path)
        cached = cm.get_cached(csv_path)

        assert cached is not None
        pd.testing.assert_frame_equal(cached, df)

    def test_stream_progress_callback_called(self, tmp_path):
        """Progress callback is invoked with increasing values."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        csv_path = tmp_path / "data.csv"
        df = pd.DataFrame({"a": list(range(100))})
        self._write_csv(csv_path, df)

        progress_values = []
        cm.stream_csv_to_cache(
            csv_path,
            progress_callback=progress_values.append,
        )

        assert len(progress_values) >= 1
        # All values should be in [0, 100]
        assert all(0 <= v <= 100 for v in progress_values)

    def test_stream_no_partial_file_on_success(self, tmp_path):
        """No .parquet.partial file remains after successful stream."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        csv_path = tmp_path / "data.csv"
        df = pd.DataFrame({"a": [1, 2, 3]})
        self._write_csv(csv_path, df)

        cm.stream_csv_to_cache(csv_path)

        partials = list((tmp_path / "cache").glob("*.partial"))
        assert partials == []

    def test_stream_cleans_up_partial_on_error(self, tmp_path):
        """Partial file is removed if streaming fails."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        csv_path = tmp_path / "bad.csv"
        # Write invalid CSV content that will fail to parse
        csv_path.write_text("a,b\n1,2\n\x00\x00\x00")

        # The streaming may or may not raise depending on pyarrow's
        # tolerance, but if it does, partial should be cleaned up
        try:
            cm.stream_csv_to_cache(csv_path)
        except Exception:
            pass

        partials = list((tmp_path / "cache").glob("*.partial"))
        assert partials == []

    def test_stream_nonexistent_csv_raises(self, tmp_path):
        """Raises when CSV file does not exist."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        csv_path = tmp_path / "missing.csv"

        with pytest.raises(Exception):
            cm.stream_csv_to_cache(csv_path)

    def test_stream_overwrites_existing_cache(self, tmp_path):
        """Streaming overwrites a previously cached version."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        csv_path = tmp_path / "data.csv"

        # First version
        df1 = pd.DataFrame({"a": [1, 2, 3]})
        self._write_csv(csv_path, df1)
        cm.stream_csv_to_cache(csv_path)

        # Second version
        sleep(0.1)
        df2 = pd.DataFrame({"a": [4, 5, 6, 7]})
        self._write_csv(csv_path, df2)
        cm.stream_csv_to_cache(csv_path)

        cached = cm.get_cached(csv_path)
        assert cached is not None
        assert len(cached) == 4

    def test_stream_with_custom_block_size(self, tmp_path):
        """Works with a small block size to force multiple batches."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        csv_path = tmp_path / "data.csv"
        # Create enough rows that a tiny block_size yields multiple batches
        df = pd.DataFrame({"a": list(range(500)), "b": list(range(500))})
        self._write_csv(csv_path, df)

        progress_values = []
        cm.stream_csv_to_cache(
            csv_path,
            progress_callback=progress_values.append,
            block_size=256,
        )

        # Multiple batches should mean multiple progress callbacks
        assert len(progress_values) > 1
        cached = cm.get_cached(csv_path)
        assert cached is not None
        assert len(cached) == 500


class TestStreamCsvNullColumnProbe:
    """Tests for null-typed column detection in streaming CSV."""

    def test_stream_handles_null_column_in_first_block(self, tmp_path):
        """Column that is all-null in block 1 but has values later loads OK.

        This reproduces the 'ArrowInvalid: CSV conversion error to null'
        bug by using a tiny block_size so that the first block contains
        only empty values for a column while a later block has real data.
        """
        cm = CacheManager(cache_dir=tmp_path / "cache")
        csv_path = tmp_path / "sparse.csv"

        # Build CSV: column 'sparse' is empty for the first 200 rows,
        # then contains '1' for the remaining rows.  With block_size=256
        # the first block will only see empty values → pa.null() type.
        lines = ["id,sparse"]
        for i in range(200):
            lines.append(f"{i},")
        for i in range(200, 300):
            lines.append(f"{i},1")
        csv_path.write_text("\n".join(lines))

        # Without the probe fix this would raise ArrowInvalid
        cm.stream_csv_to_cache(csv_path, block_size=256)

        cached = cm.get_cached(csv_path)
        assert cached is not None
        assert len(cached) == 300
        # The 'sparse' column should exist and contain the value '1'
        non_null = cached["sparse"].dropna()
        assert len(non_null) > 0

    def test_probe_returns_none_when_no_null_columns(self, tmp_path):
        """_probe_null_columns returns None for a well-typed CSV."""
        import pyarrow.csv as pa_csv

        csv_path = tmp_path / "good.csv"
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        df.to_csv(csv_path, index=False)

        read_opts = pa_csv.ReadOptions(block_size=32 * 1024 * 1024)
        result = CacheManager._probe_null_columns(csv_path, read_opts)
        assert result is None

    def test_probe_detects_null_column(self, tmp_path):
        """_probe_null_columns detects a column typed as null."""
        import pyarrow.csv as pa_csv

        csv_path = tmp_path / "nullcol.csv"
        # Column 'empty' will be all-null in the only block
        lines = ["a,empty", "1,", "2,", "3,"]
        csv_path.write_text("\n".join(lines))

        read_opts = pa_csv.ReadOptions(block_size=32 * 1024 * 1024)
        result = CacheManager._probe_null_columns(csv_path, read_opts)
        assert result is not None

    def test_probe_empty_csv_returns_none(self, tmp_path):
        """_probe_null_columns returns None for a header-only CSV."""
        import pyarrow.csv as pa_csv

        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("a,b\n")

        read_opts = pa_csv.ReadOptions(block_size=32 * 1024 * 1024)
        result = CacheManager._probe_null_columns(csv_path, read_opts)
        assert result is None


class TestCleanupPartial:
    """Tests for _cleanup_partial helper."""

    def test_cleanup_removes_existing_file(self, tmp_path):
        """_cleanup_partial removes a file that exists."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        partial = tmp_path / "cache" / "test.parquet.partial"
        partial.write_text("dummy")

        cm._cleanup_partial(partial)
        assert not partial.exists()

    def test_cleanup_ignores_missing_file(self, tmp_path):
        """_cleanup_partial does not raise for missing file."""
        cm = CacheManager(cache_dir=tmp_path / "cache")
        partial = tmp_path / "cache" / "nonexistent.parquet.partial"

        # Should not raise
        cm._cleanup_partial(partial)
