"""Computation cache for memoizing expensive calculations.

This module provides a caching layer that stores results of expensive computations
like metrics calculations, breakdowns, and feature analysis. Results are keyed by
a hash of the input parameters, enabling instant retrieval when the same computation
is requested again.

This dramatically improves UI responsiveness when:
- Switching between tabs (same metrics displayed in multiple places)
- Toggling filters back and forth
- Re-running analysis with same parameters
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class CacheEntry:
    """Single cache entry with metadata."""

    value: Any
    created_at: float
    access_count: int = 0
    last_accessed: float = 0.0

    def __post_init__(self) -> None:
        self.last_accessed = self.created_at


class ComputationCache:
    """Thread-safe LRU cache for computation results.

    Features:
    - LRU eviction policy to manage memory
    - Thread-safe access for background computations
    - Automatic cache key generation from function arguments
    - TTL support for time-sensitive data
    - Hit/miss statistics for debugging
    """

    def __init__(
        self,
        max_size: int = 100,
        ttl_seconds: float | None = None,
    ) -> None:
        """Initialize the computation cache.

        Args:
            max_size: Maximum number of entries to store.
            ttl_seconds: Time-to-live in seconds. None means no expiration.
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def _generate_key(self, *args: Any, **kwargs: Any) -> str:
        """Generate a unique cache key from arguments.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            MD5 hash string of the arguments.
        """
        key_parts = []

        for arg in args:
            key_parts.append(self._hash_value(arg))

        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={self._hash_value(v)}")

        combined = "|".join(key_parts)
        return hashlib.md5(combined.encode()).hexdigest()

    def _hash_value(self, value: Any) -> str:
        """Hash a single value for cache key generation.

        Args:
            value: Value to hash.

        Returns:
            String representation suitable for hashing.
        """
        if isinstance(value, pd.DataFrame):
            # Use shape and a sample of data for fast hashing
            if len(value) == 0:
                return f"df:empty:{tuple(value.columns)}"
            # Hash shape + first/last rows + column names for uniqueness
            sample_hash = hashlib.md5(
                pd.util.hash_pandas_object(value.head(5)).values.tobytes()
                + pd.util.hash_pandas_object(value.tail(5)).values.tobytes()
            ).hexdigest()[:16]
            return f"df:{value.shape}:{sample_hash}"

        elif isinstance(value, pd.Series):
            if len(value) == 0:
                return f"series:empty:{value.name}"
            sample_hash = hashlib.md5(
                pd.util.hash_pandas_object(value.head(10)).values.tobytes()
            ).hexdigest()[:16]
            return f"series:{len(value)}:{sample_hash}"

        elif isinstance(value, np.ndarray):
            return f"array:{value.shape}:{hashlib.md5(value.tobytes()).hexdigest()[:16]}"

        elif isinstance(value, (list, tuple)):
            # Hash first few elements for lists/tuples
            if len(value) == 0:
                return f"{type(value).__name__}:empty"
            sample = value[:10] if len(value) > 10 else value
            return f"{type(value).__name__}:{len(value)}:{hash(tuple(sample)) % 10**8}"

        elif isinstance(value, dict):
            # Hash sorted items
            sorted_items = sorted(value.items(), key=lambda x: str(x[0]))
            return f"dict:{len(value)}:{hash(tuple(sorted_items)) % 10**8}"

        elif hasattr(value, "__dict__"):
            # For objects, use their __dict__
            return f"{type(value).__name__}:{hash(tuple(sorted(value.__dict__.items()))) % 10**8}"

        else:
            return str(hash(value))

    def get(self, key: str) -> tuple[bool, Any]:
        """Get a value from cache.

        Args:
            key: Cache key.

        Returns:
            Tuple of (hit, value). If hit is False, value is None.
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return (False, None)

            entry = self._cache[key]

            # Check TTL
            if self._ttl_seconds is not None:
                age = time.time() - entry.created_at
                if age > self._ttl_seconds:
                    del self._cache[key]
                    self._misses += 1
                    return (False, None)

            # Update access stats and move to end (LRU)
            entry.access_count += 1
            entry.last_accessed = time.time()
            self._cache.move_to_end(key)
            self._hits += 1

            return (True, entry.value)

    def set(self, key: str, value: Any) -> None:
        """Store a value in cache.

        Args:
            key: Cache key.
            value: Value to store.
        """
        with self._lock:
            # Remove oldest entries if at capacity
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)

            self._cache[key] = CacheEntry(
                value=value,
                created_at=time.time(),
            )

    def cached(
        self,
        func: Callable[..., T],
        *args: Any,
        cache_key: str | None = None,
        **kwargs: Any,
    ) -> T:
        """Execute function with caching.

        Args:
            func: Function to execute.
            *args: Positional arguments for function.
            cache_key: Optional explicit cache key. Auto-generated if None.
            **kwargs: Keyword arguments for function.

        Returns:
            Function result (from cache or fresh execution).
        """
        key = cache_key or self._generate_key(func.__name__, *args, **kwargs)

        hit, value = self.get(key)
        if hit:
            logger.debug("Cache hit for %s", func.__name__)
            return value

        logger.debug("Cache miss for %s, computing...", func.__name__)
        result = func(*args, **kwargs)
        self.set(key, result)
        return result

    def invalidate(self, key: str | None = None) -> None:
        """Invalidate cache entries.

        Args:
            key: Specific key to invalidate. If None, clears entire cache.
        """
        with self._lock:
            if key is None:
                self._cache.clear()
                logger.debug("Cleared entire computation cache")
            elif key in self._cache:
                del self._cache[key]
                logger.debug("Invalidated cache key: %s", key[:16])

    def invalidate_prefix(self, prefix: str) -> int:
        """Invalidate all entries with keys starting with prefix.

        Args:
            prefix: Key prefix to match.

        Returns:
            Number of entries invalidated.
        """
        with self._lock:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(prefix)]
            for key in keys_to_remove:
                del self._cache[key]
            logger.debug("Invalidated %d entries with prefix %s", len(keys_to_remove), prefix)
            return len(keys_to_remove)

    @property
    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with hits, misses, size, and hit rate.
        """
        with self._lock:
            total = self._hits + self._misses
            return {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._cache),
                "max_size": self._max_size,
                "hit_rate": self._hits / total if total > 0 else 0.0,
            }


# Global cache instances for different computation types
_metrics_cache = ComputationCache(max_size=50, ttl_seconds=None)
_breakdown_cache = ComputationCache(max_size=30, ttl_seconds=None)
_feature_cache = ComputationCache(max_size=20, ttl_seconds=None)
_statistics_cache = ComputationCache(max_size=20, ttl_seconds=None)


def get_metrics_cache() -> ComputationCache:
    """Get the global metrics computation cache."""
    return _metrics_cache


def get_breakdown_cache() -> ComputationCache:
    """Get the global breakdown computation cache."""
    return _breakdown_cache


def get_feature_cache() -> ComputationCache:
    """Get the global feature analysis computation cache."""
    return _feature_cache


def get_statistics_cache() -> ComputationCache:
    """Get the global statistics computation cache."""
    return _statistics_cache


def invalidate_all_caches() -> None:
    """Invalidate all computation caches.

    Call this when source data changes (e.g., new file loaded).
    """
    _metrics_cache.invalidate()
    _breakdown_cache.invalidate()
    _feature_cache.invalidate()
    _statistics_cache.invalidate()
    logger.info("All computation caches invalidated")


def get_all_cache_stats() -> dict[str, dict[str, Any]]:
    """Get statistics for all caches.

    Returns:
        Dict mapping cache name to stats dict.
    """
    return {
        "metrics": _metrics_cache.stats,
        "breakdown": _breakdown_cache.stats,
        "feature": _feature_cache.stats,
        "statistics": _statistics_cache.stats,
    }
