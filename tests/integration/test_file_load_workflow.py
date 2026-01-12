"""Integration tests for file load workflow with caching."""

from time import sleep

import pandas as pd
import pytest
from PyQt6.QtCore import QCoreApplication

from src.core.cache_manager import CacheManager
from src.core.file_load_worker import FileLoadWorker


@pytest.fixture
def qapp():
    """Create QCoreApplication for Qt signal testing."""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    yield app


class TestFileCacheWorkflow:
    """Integration tests for file loading with cache."""

    def test_first_load_creates_cache(self, tmp_path, qapp):
        """First load creates cache file, second load uses cache."""
        # Create test CSV
        csv_file = tmp_path / "test.csv"
        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL"],
            "date": ["2024-01-01", "2024-01-02"],
            "gain_pct": [1.5, -0.8],
        })
        df.to_csv(csv_file, index=False)

        # Setup cache in tmp_path
        cache_dir = tmp_path / ".lumen_cache"
        cm = CacheManager(cache_dir=cache_dir)

        # First load - should miss cache
        cache_path = cm._get_cache_path(csv_file)
        assert not cache_path.exists()

        # Load and cache
        loaded_df = pd.read_csv(csv_file)
        sleep(0.1)
        cm.save_to_cache(loaded_df, csv_file)

        # Verify cache created
        assert cache_path.exists()

        # Second load - should hit cache
        cached_df = cm.get_cached(csv_file)
        assert cached_df is not None
        assert len(cached_df) == 2
        assert list(cached_df.columns) == ["ticker", "date", "gain_pct"]

    def test_modified_source_invalidates_cache(self, tmp_path, qapp):
        """Modifying source file invalidates cache."""
        # Create test CSV
        csv_file = tmp_path / "test.csv"
        df = pd.DataFrame({
            "ticker": ["AAPL"],
            "gain_pct": [1.5],
        })
        df.to_csv(csv_file, index=False)

        # Setup cache
        cache_dir = tmp_path / ".lumen_cache"
        cm = CacheManager(cache_dir=cache_dir)

        # Create cache
        sleep(0.1)
        cm.save_to_cache(df, csv_file)
        assert cm.is_cache_valid(csv_file) is True

        # Modify source file
        sleep(0.1)
        df_modified = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL"],
            "gain_pct": [1.5, 2.0],
        })
        df_modified.to_csv(csv_file, index=False)

        # Cache should now be invalid
        assert cm.is_cache_valid(csv_file) is False

        # get_cached should return None
        result = cm.get_cached(csv_file)
        assert result is None

    def test_file_load_worker_cache_hit_signal(self, tmp_path, qapp):
        """FileLoadWorker emits cache_hit signal correctly."""
        # Create test CSV
        csv_file = tmp_path / "test.csv"
        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL"],
            "date": ["2024-01-01", "2024-01-02"],
            "time": ["09:30:00", "10:00:00"],
            "gain_pct": [1.5, -0.8],
        })
        df.to_csv(csv_file, index=False)

        # Track signals
        cache_hit_values = []
        finished_dfs = []

        def on_cache_hit(value):
            cache_hit_values.append(value)

        def on_finished(result_df):
            finished_dfs.append(result_df)

        # First load - cache miss
        worker1 = FileLoadWorker(csv_file)
        worker1.cache_hit.connect(on_cache_hit)
        worker1.finished.connect(on_finished)
        worker1.run()  # Run synchronously for testing

        assert len(cache_hit_values) == 1
        assert cache_hit_values[0] is False  # Cache miss
        assert len(finished_dfs) == 1
        assert len(finished_dfs[0]) == 2

        # Second load - cache hit
        cache_hit_values.clear()
        finished_dfs.clear()

        worker2 = FileLoadWorker(csv_file)
        worker2.cache_hit.connect(on_cache_hit)
        worker2.finished.connect(on_finished)
        worker2.run()

        assert len(cache_hit_values) == 1
        assert cache_hit_values[0] is True  # Cache hit
        assert len(finished_dfs) == 1
        assert len(finished_dfs[0]) == 2

    def test_excel_sheet_caching(self, tmp_path, qapp):
        """Different Excel sheets have separate cache entries."""
        # Create test Excel with multiple sheets
        excel_file = tmp_path / "test.xlsx"
        df1 = pd.DataFrame({"ticker": ["AAPL"], "gain_pct": [1.5]})
        df2 = pd.DataFrame({"ticker": ["GOOGL", "MSFT"], "gain_pct": [2.0, -1.0]})

        with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
            df1.to_excel(writer, sheet_name="Sheet1", index=False)
            df2.to_excel(writer, sheet_name="Sheet2", index=False)

        # Setup cache
        cache_dir = tmp_path / ".lumen_cache"
        cm = CacheManager(cache_dir=cache_dir)

        # Cache both sheets
        sleep(0.1)
        cm.save_to_cache(df1, excel_file, "Sheet1")
        cm.save_to_cache(df2, excel_file, "Sheet2")

        # Verify separate cache files
        cache_path1 = cm._get_cache_path(excel_file, "Sheet1")
        cache_path2 = cm._get_cache_path(excel_file, "Sheet2")
        assert cache_path1 != cache_path2
        assert cache_path1.exists()
        assert cache_path2.exists()

        # Verify correct data retrieved
        cached1 = cm.get_cached(excel_file, "Sheet1")
        cached2 = cm.get_cached(excel_file, "Sheet2")

        assert len(cached1) == 1
        assert len(cached2) == 2
        assert cached1["ticker"].iloc[0] == "AAPL"
        assert cached2["ticker"].iloc[0] == "GOOGL"
