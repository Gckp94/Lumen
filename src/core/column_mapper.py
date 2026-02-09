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
        "time": ["time", "trade_time", "entry_time", "trigger_time_et"],
        "gain_pct": ["gain", "return", "pnl", "profit", "%"],
        "mae_pct": ["mae", "max_adverse", "adverse", "drawdown", "mae_pct"],
        "mfe_pct": ["mfe", "max_favorable", "favorable", "runup", "mfe_pct"],
        "win_loss": ["win", "loss", "result", "outcome"],
        "mae_time": ["mae_time", "mae time", "time_mae", "adverse_time"],
        "mfe_time": ["mfe_time", "mfe time", "time_mfe", "favorable_time"],
        # Price interval columns
        "price_10_min_after": ["price_10_min_after", "10_min_after", "10min_after"],
        "price_20_min_after": ["price_20_min_after", "20_min_after", "20min_after"],
        "price_30_min_after": ["price_30_min_after", "30_min_after", "30min_after"],
        "price_60_min_after": ["price_60_min_after", "60_min_after", "60min_after"],
        "price_90_min_after": ["price_90_min_after", "90_min_after", "90min_after"],
        "price_120_min_after": ["price_120_min_after", "120_min_after", "120min_after"],
        "price_150_min_after": ["price_150_min_after", "150_min_after", "150min_after"],
        "price_180_min_after": ["price_180_min_after", "180_min_after", "180min_after"],
        "price_240_min_after": ["price_240_min_after", "240_min_after", "240min_after"],
    }

    REQUIRED_COLUMNS = ["ticker", "date", "time", "gain_pct", "mae_pct", "mfe_pct"]

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
                mfe_pct=detected["mfe_pct"],  # type: ignore[arg-type]
                win_loss=detected.get("win_loss"),
                mae_time=detected.get("mae_time"),
                mfe_time=detected.get("mfe_time"),
            )
            logger.info(
                "Column mapping completed: ticker=%s, date=%s, time=%s, gain=%s, mae=%s, mfe=%s",
                mapping.ticker,
                mapping.date,
                mapping.time,
                mapping.gain_pct,
                mapping.mae_pct,
                mapping.mfe_pct,
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
        """Match a column using case-insensitive matching with priority rules.

        Priority order:
        1. Exact match (case-insensitive)
        2. Substring match - prefer shorter column names
        3. Reverse substring match (guessed)

        Args:
            columns: List of column names to search.
            patterns: List of patterns to match against.

        Returns:
            Tuple of (matched_column_name, status).
            Status is "detected" for exact/substring match, "guessed" for partial,
            "missing" if no match found.
        """
        columns_lower = {col.lower(): col for col in columns}

        # First pass: exact match (case-insensitive) - highest priority
        for pattern in patterns:
            if pattern.lower() in columns_lower:
                return columns_lower[pattern.lower()], "detected"

        # Second pass: substring match (pattern appears in column name)
        # Collect all matches, then prefer shorter column names
        substring_matches: list[str] = []
        for pattern in patterns:
            for col_lower, col_original in columns_lower.items():
                if pattern.lower() in col_lower:
                    substring_matches.append(col_original)

        if substring_matches:
            # Sort by length (prefer shorter names) then alphabetically for consistency
            substring_matches.sort(key=lambda x: (len(x), x.lower()))
            return substring_matches[0], "detected"

        # Third pass: column name appears in pattern (guessed) - lowest priority
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
        # Normalize path: resolve to absolute, convert to lowercase for case-insensitive matching
        # Use as_posix() to normalize separators, then lowercase for Windows compatibility
        normalized_path = file_path.resolve().as_posix().lower()
        key = normalized_path + (sheet or "")
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
