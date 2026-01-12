"""Parquet cache management for faster file loads."""

import contextlib
import hashlib
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class CacheManager:
    """Manage Parquet cache for faster file loads.

    Caches loaded DataFrames as Parquet files in `.lumen_cache/` for
    10-20x faster subsequent loads compared to Excel/CSV sources.
    """

    def __init__(self, cache_dir: Path = Path(".lumen_cache")) -> None:
        """Initialize CacheManager.

        Args:
            cache_dir: Directory for cache files. Created if doesn't exist.
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_key(self, file_path: Path, sheet: str | None = None) -> str:
        """Generate MD5 hash key for cache file.

        Args:
            file_path: Path to the source file.
            sheet: Sheet name for Excel files (None for CSV/Parquet).

        Returns:
            MD5 hash string of file path + sheet name.
        """
        key_string = str(file_path.absolute()) + (sheet or "default")
        return hashlib.md5(key_string.encode()).hexdigest()

    def _get_cache_path(self, file_path: Path, sheet: str | None = None) -> Path:
        """Get the cache file path for a source file.

        Args:
            file_path: Path to the source file.
            sheet: Sheet name for Excel files.

        Returns:
            Path to the cache Parquet file.
        """
        cache_key = self._get_cache_key(file_path, sheet)
        return self.cache_dir / f"{cache_key}.parquet"

    def is_cache_valid(self, file_path: Path, sheet: str | None = None) -> bool:
        """Check if valid cache exists for file.

        Cache is valid if:
        - Cache file exists
        - Cache file modification time is newer than source file

        Args:
            file_path: Path to the source file.
            sheet: Sheet name for Excel files.

        Returns:
            True if valid cache exists, False otherwise.
        """
        cache_path = self._get_cache_path(file_path, sheet)

        if not cache_path.exists():
            return False

        # Compare modification times
        source_mtime = file_path.stat().st_mtime
        cache_mtime = cache_path.stat().st_mtime

        return cache_mtime > source_mtime

    def get_cached(
        self,
        file_path: Path,
        sheet: str | None = None,
    ) -> pd.DataFrame | None:
        """Load DataFrame from cache if valid.

        Args:
            file_path: Path to the source file.
            sheet: Sheet name for Excel files.

        Returns:
            Cached DataFrame if valid cache exists, None otherwise.
            Returns None and deletes cache if cache file is corrupt.
        """
        if not self.is_cache_valid(file_path, sheet):
            return None

        cache_path = self._get_cache_path(file_path, sheet)

        try:
            df = pd.read_parquet(cache_path)
            logger.info("Loaded %d rows from cache for %s", len(df), file_path.name)
            return df
        except Exception as e:
            # Corrupt cache - delete and return None
            logger.warning("Corrupt cache for %s, deleting: %s", file_path.name, e)
            with contextlib.suppress(OSError):
                cache_path.unlink()
            return None

    def save_to_cache(
        self,
        df: pd.DataFrame,
        file_path: Path,
        sheet: str | None = None,
    ) -> None:
        """Save DataFrame to cache.

        Args:
            df: DataFrame to cache.
            file_path: Path to the source file.
            sheet: Sheet name for Excel files.
        """
        cache_path = self._get_cache_path(file_path, sheet)

        try:
            df.to_parquet(cache_path, index=False)
            logger.info("Cached %d rows for %s", len(df), file_path.name)
        except Exception as e:
            logger.error("Failed to save cache for %s: %s", file_path.name, e)
            # Don't raise - caching failure shouldn't break the app

    def invalidate(self, file_path: Path, sheet: str | None = None) -> None:
        """Remove cache for a specific file/sheet combination.

        Args:
            file_path: Path to the source file.
            sheet: Sheet name to invalidate. If None, only invalidates the default cache.
        """
        cache_path = self._get_cache_path(file_path, sheet)
        if cache_path.exists():
            try:
                cache_path.unlink()
                logger.debug("Removed cache file: %s", cache_path.name)
            except OSError as e:
                logger.warning("Failed to remove cache file %s: %s", cache_path.name, e)
