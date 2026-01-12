"""Background worker thread for file loading operations."""

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from src.core.cache_manager import CacheManager
from src.core.exceptions import FileLoadError
from src.core.file_loader import FileLoader


class FileLoadWorker(QThread):
    """Worker thread for loading files in the background.

    Signals:
        progress: Emitted with progress percentage (0-100).
        finished: Emitted with the loaded DataFrame on success.
        error: Emitted with error message string on failure.
        cache_hit: Emitted with True if loaded from cache, False otherwise.
    """

    progress = pyqtSignal(int)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    cache_hit = pyqtSignal(bool)

    def __init__(self, path: Path, sheet: str | None = None) -> None:
        """Initialize the worker.

        Args:
            path: Path to the file to load.
            sheet: Sheet name for Excel files (optional).
        """
        super().__init__()
        self.path = path
        self.sheet = sheet
        self._loader = FileLoader()
        self._cache_manager = CacheManager()

    def run(self) -> None:
        """Execute the file loading operation."""
        try:
            # Check cache first
            cached_df = self._cache_manager.get_cached(self.path, self.sheet)
            if cached_df is not None:
                self.progress.emit(100)
                self.cache_hit.emit(True)
                self.finished.emit(cached_df)
                return

            # Cache miss - load from source
            self.cache_hit.emit(False)
            self.progress.emit(10)
            df = self._loader.load(self.path, self.sheet)
            self.progress.emit(100)

            # Save to cache after successful load
            self._cache_manager.save_to_cache(df, self.path, self.sheet)

            self.finished.emit(df)
        except FileLoadError as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(f"Unexpected error: {e}")
