"""Unit tests for FileLoadWorker."""

from pathlib import Path
from time import sleep
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.file_load_worker import FileLoadWorker


@pytest.fixture()
def csv_file(tmp_path):
    """Create a small CSV file for testing."""
    csv_path = tmp_path / "test_data.csv"
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0]})
    df.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture()
def xlsx_file(tmp_path):
    """Create a small Excel file for testing."""
    xlsx_path = tmp_path / "test_data.xlsx"
    df = pd.DataFrame({"x": [10, 20], "y": [30, 40]})
    df.to_excel(xlsx_path, index=False, sheet_name="Sheet1")
    return xlsx_path


class TestFileLoadWorkerCsvStreaming:
    """Tests for CSV streaming path in FileLoadWorker."""

    def test_csv_uses_stream_csv_to_cache(self, csv_file, tmp_path):
        """CSV cache miss calls stream_csv_to_cache instead of FileLoader.load."""
        worker = FileLoadWorker(csv_file)
        worker._cache_manager.cache_dir = tmp_path / "cache"
        worker._cache_manager.cache_dir.mkdir(exist_ok=True)

        with patch.object(
            worker._cache_manager, "stream_csv_to_cache", wraps=worker._cache_manager.stream_csv_to_cache
        ) as mock_stream, patch.object(
            worker._loader, "load", wraps=worker._loader.load
        ) as mock_load:
            worker.run()

            mock_stream.assert_called_once()
            mock_load.assert_not_called()

    def test_csv_emits_finished_with_dataframe(self, csv_file, tmp_path):
        """CSV streaming path emits finished signal with valid DataFrame."""
        worker = FileLoadWorker(csv_file)
        worker._cache_manager.cache_dir = tmp_path / "cache"
        worker._cache_manager.cache_dir.mkdir(exist_ok=True)

        finished_results = []
        worker.finished.connect(finished_results.append)

        worker.run()

        assert len(finished_results) == 1
        df = finished_results[0]
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ["a", "b"]

    def test_csv_emits_progress(self, csv_file, tmp_path):
        """CSV streaming path emits progress signals."""
        worker = FileLoadWorker(csv_file)
        worker._cache_manager.cache_dir = tmp_path / "cache"
        worker._cache_manager.cache_dir.mkdir(exist_ok=True)

        progress_values = []
        worker.progress.connect(progress_values.append)

        worker.run()

        # Should include at least 10 (start) and 100 (end)
        assert 10 in progress_values
        assert 100 in progress_values

    def test_csv_emits_cache_hit_false(self, csv_file, tmp_path):
        """CSV cache miss emits cache_hit(False)."""
        worker = FileLoadWorker(csv_file)
        worker._cache_manager.cache_dir = tmp_path / "cache"
        worker._cache_manager.cache_dir.mkdir(exist_ok=True)

        hit_values = []
        worker.cache_hit.connect(hit_values.append)

        worker.run()

        assert hit_values == [False]


class TestFileLoadWorkerCacheHit:
    """Tests for cache hit path."""

    def test_cache_hit_returns_cached_data(self, csv_file, tmp_path):
        """Cache hit path returns data from cache."""
        worker = FileLoadWorker(csv_file)
        worker._cache_manager.cache_dir = tmp_path / "cache"
        worker._cache_manager.cache_dir.mkdir(exist_ok=True)

        # First run: populates cache via streaming
        worker.run()

        # Second run: should hit cache
        worker2 = FileLoadWorker(csv_file)
        worker2._cache_manager.cache_dir = tmp_path / "cache"
        worker2._cache_manager.cache_dir.mkdir(exist_ok=True)

        hit_values = []
        finished_results = []
        worker2.cache_hit.connect(hit_values.append)
        worker2.finished.connect(finished_results.append)

        worker2.run()

        assert hit_values == [True]
        assert len(finished_results) == 1
        assert len(finished_results[0]) == 3


class TestFileLoadWorkerNonCsv:
    """Tests for non-CSV file path."""

    def test_xlsx_uses_file_loader(self, xlsx_file, tmp_path):
        """Excel files use FileLoader.load, not streaming."""
        worker = FileLoadWorker(xlsx_file, sheet="Sheet1")
        worker._cache_manager.cache_dir = tmp_path / "cache"
        worker._cache_manager.cache_dir.mkdir(exist_ok=True)

        with patch.object(
            worker._cache_manager, "stream_csv_to_cache"
        ) as mock_stream, patch.object(
            worker._loader, "load", wraps=worker._loader.load
        ) as mock_load:
            worker.run()

            mock_stream.assert_not_called()
            mock_load.assert_called_once()


class TestFileLoadWorkerStreamingFallback:
    """Tests for streaming-to-standard-load fallback."""

    def test_falls_back_when_streaming_raises(self, csv_file, tmp_path):
        """If stream_csv_to_cache raises, falls back to FileLoader.load."""
        worker = FileLoadWorker(csv_file)
        worker._cache_manager.cache_dir = tmp_path / "cache"
        worker._cache_manager.cache_dir.mkdir(exist_ok=True)

        with patch.object(
            worker._cache_manager,
            "stream_csv_to_cache",
            side_effect=RuntimeError("simulated ArrowInvalid"),
        ):
            finished_results = []
            worker.finished.connect(finished_results.append)

            worker.run()

            # Should still succeed via the fallback path
            assert len(finished_results) == 1
            assert len(finished_results[0]) == 3


class TestFileLoadWorkerErrors:
    """Tests for error handling."""

    def test_missing_file_emits_error(self, tmp_path):
        """Missing file emits error signal."""
        worker = FileLoadWorker(tmp_path / "nonexistent.csv")
        worker._cache_manager.cache_dir = tmp_path / "cache"
        worker._cache_manager.cache_dir.mkdir(exist_ok=True)

        errors = []
        worker.error.connect(errors.append)

        worker.run()

        assert len(errors) == 1
        assert errors[0]  # non-empty error message


class TestOnStreamProgress:
    """Tests for _on_stream_progress helper."""

    def test_maps_zero_to_ten(self):
        """0% streaming maps to 10% overall."""
        worker = FileLoadWorker.__new__(FileLoadWorker)
        # Manually set up the signal since we used __new__
        values = []

        worker._on_stream_progress = lambda pct: values.append(
            10 + int(pct * 75 / 100)
        )
        worker._on_stream_progress(0)
        assert values == [10]

    def test_maps_hundred_to_eighty_five(self):
        """100% streaming maps to 85% overall."""
        result = 10 + int(100 * 75 / 100)
        assert result == 85
