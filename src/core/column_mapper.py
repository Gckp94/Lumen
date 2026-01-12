"""Column auto-detection and mapping management."""

import hashlib
import json
import logging
from dataclasses import asdict
from pathlib import Path

from src.core.models import ColumnMapping, DetectionResult

logger = logging.getLogger(__name__)


class ColumnMapper:
    """Auto-detect and manage column mappings.

    Attributes:
        PATTERNS: Dict mapping column types to list of patterns for matching.
    """

    PATTERNS: dict[str, list[str]] = {
        "ticker": ["ticker", "symbol", "stock", "security"],
        "date": ["date", "trade_date", "entry_date"],
        "time": ["time", "trade_time", "entry_time"],
        "gain_pct": ["gain", "return", "pnl", "profit", "%"],
        "mae_pct": ["mae", "max_adverse", "adverse", "drawdown", "mae_pct"],
        "win_loss": ["win", "loss", "result", "outcome"],
    }

    REQUIRED_COLUMNS = ["ticker", "date", "time", "gain_pct", "mae_pct"]

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize ColumnMapper.

        Args:
            cache_dir: Directory for caching mappings. Defaults to .lumen_cache/
        """
        self._cache_dir = cache_dir or Path(".lumen_cache")

    def auto_detect(self, columns: list[str]) -> DetectionResult:
        """Attempt auto-detection of column mapping.

        Args:
            columns: List of column names from DataFrame.

        Returns:
            DetectionResult with mapping (if complete) and status dict.
        """
        statuses: dict[str, str] = {}
        detected: dict[str, str | None] = {}

        for column_type, patterns in self.PATTERNS.items():
            matched_col, status = self._match_column(columns, patterns)
            detected[column_type] = matched_col
            statuses[column_type] = status

        logger.debug("Detection status: %s", statuses)

        # Check if all required columns detected
        all_required = all(statuses.get(col) == "detected" for col in self.REQUIRED_COLUMNS)

        mapping: ColumnMapping | None = None
        if all_required:
            mapping = ColumnMapping(
                ticker=detected["ticker"],  # type: ignore[arg-type]
                date=detected["date"],  # type: ignore[arg-type]
                time=detected["time"],  # type: ignore[arg-type]
                gain_pct=detected["gain_pct"],  # type: ignore[arg-type]
                mae_pct=detected["mae_pct"],  # type: ignore[arg-type]
                win_loss=detected.get("win_loss"),
            )
            logger.info(
                "Column mapping completed: ticker=%s, date=%s, time=%s, gain=%s, mae=%s",
                mapping.ticker,
                mapping.date,
                mapping.time,
                mapping.gain_pct,
                mapping.mae_pct,
            )
        else:
            missing = [col for col in self.REQUIRED_COLUMNS if statuses.get(col) != "detected"]
            for col in missing:
                logger.warning("Could not auto-detect column: %s", col)

        return DetectionResult(
            mapping=mapping,
            statuses=statuses,
            all_required_detected=all_required,
        )

    def _match_column(self, columns: list[str], patterns: list[str]) -> tuple[str | None, str]:
        """Match a column using case-insensitive substring matching.

        Args:
            columns: List of column names to search.
            patterns: List of patterns to match against.

        Returns:
            Tuple of (matched_column_name, status).
            Status is "detected" for exact/substring match, "guessed" for partial,
            "missing" if no match found.
        """
        columns_lower = {col.lower(): col for col in columns}

        # First pass: exact match (case-insensitive)
        for pattern in patterns:
            if pattern.lower() in columns_lower:
                return columns_lower[pattern.lower()], "detected"

        # Second pass: substring match (pattern appears in column name)
        for pattern in patterns:
            for col_lower, col_original in columns_lower.items():
                if pattern.lower() in col_lower:
                    return col_original, "detected"

        # Third pass: column name appears in pattern (guessed)
        for pattern in patterns:
            for col_lower, col_original in columns_lower.items():
                if col_lower in pattern.lower():
                    return col_original, "guessed"

        return None, "missing"

    def _get_file_hash(self, file_path: Path, sheet: str | None = None) -> str:
        """Generate hash for cache key.

        Args:
            file_path: Path to the data file.
            sheet: Optional sheet name for Excel files.

        Returns:
            MD5 hash string.
        """
        key = str(file_path) + (sheet or "")
        return hashlib.md5(key.encode()).hexdigest()

    def save_mapping(
        self, file_path: Path, mapping: ColumnMapping, sheet: str | None = None
    ) -> None:
        """Persist mapping to cache.

        Args:
            file_path: Path to the data file.
            mapping: ColumnMapping to save.
            sheet: Optional sheet name for Excel files.
        """
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        file_hash = self._get_file_hash(file_path, sheet)
        cache_path = self._cache_dir / f"{file_hash}_mappings.json"

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(asdict(mapping), f, indent=2)

        logger.debug("Saved mapping to %s", cache_path)

    def load_mapping(self, file_path: Path, sheet: str | None = None) -> ColumnMapping | None:
        """Load persisted mapping if exists.

        Args:
            file_path: Path to the data file.
            sheet: Optional sheet name for Excel files.

        Returns:
            ColumnMapping if found in cache, else None.
        """
        file_hash = self._get_file_hash(file_path, sheet)
        cache_path = self._cache_dir / f"{file_hash}_mappings.json"

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)
            logger.debug("Loaded mapping from %s", cache_path)
            return ColumnMapping(**data)
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning("Failed to load cached mapping: %s", e)
            return None
