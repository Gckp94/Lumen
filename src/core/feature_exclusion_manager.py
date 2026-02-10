"""Manager for persisting feature exclusion settings per data file."""
import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FeatureExclusionManager:
    """Persists feature exclusion settings per source data file.

    Each source file gets its own exclusion set, stored as JSON.
    Files are identified by a hash of their absolute path.
    """

    def __init__(self, config_dir: Path | None = None):
        """Initialize the manager.

        Args:
            config_dir: Directory for storing exclusion configs.
                        Defaults to ~/.lumen/feature_exclusions/
        """
        if config_dir is None:
            config_dir = Path.home() / ".lumen" / "feature_exclusions"
        self._config_dir = Path(config_dir)

    def _get_config_path(self, source_file: str) -> Path:
        """Get config file path for a source file.

        Uses a hash of the source path for the filename to avoid
        filesystem issues with special characters.
        """
        # Normalize path and create hash
        normalized = str(Path(source_file).resolve())
        path_hash = hashlib.md5(normalized.encode()).hexdigest()[:12]
        return self._config_dir / f"{path_hash}.json"

    def save(self, source_file: str, exclusions: set[str]) -> None:
        """Save exclusions for a source file.

        Args:
            source_file: Path to the source data file.
            exclusions: Set of column names to exclude.
        """
        self._config_dir.mkdir(parents=True, exist_ok=True)
        config_path = self._get_config_path(source_file)

        data = {
            "source_file": source_file,
            "exclusions": sorted(exclusions),  # Sort for deterministic output
        }

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(exclusions)} exclusions for {source_file}")
        except Exception as e:
            logger.error(f"Failed to save exclusions: {e}")

    def load(self, source_file: str) -> set[str]:
        """Load exclusions for a source file.

        Args:
            source_file: Path to the source data file.

        Returns:
            Set of excluded column names, or empty set if not found.
        """
        config_path = self._get_config_path(source_file)

        if not config_path.exists():
            return set()

        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
            exclusions = set(data.get("exclusions", []))
            logger.debug(f"Loaded {len(exclusions)} exclusions for {source_file}")
            return exclusions
        except Exception as e:
            logger.error(f"Failed to load exclusions: {e}")
            return set()
