"""Filter preset persistence manager."""

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from src.core.models import FilterCriteria, FilterPreset

logger = logging.getLogger(__name__)


class FilterPresetManager:
    """Manages saving and loading filter presets to JSON files.

    Presets are stored as JSON files in a configurable directory.
    Filenames are derived from preset names (lowercase, spaces to underscores).
    """

    def __init__(self, preset_dir: Path | None = None) -> None:
        """Initialize FilterPresetManager.

        Args:
            preset_dir: Directory to store presets. Defaults to 'filters/'.
        """
        if preset_dir is None:
            preset_dir = Path("filters")
        self._preset_dir = Path(preset_dir)

    def _name_to_filename(self, name: str) -> str:
        """Convert preset name to safe filename.

        Args:
            name: Preset display name.

        Returns:
            Safe filename (lowercase, spaces to underscores).
        """
        # Replace spaces with underscores, remove unsafe chars, lowercase
        safe = re.sub(r"[^\w\s-]", "", name)
        safe = re.sub(r"\s+", "_", safe)
        return safe.lower() + ".json"

    def _filename_to_name(self, filename: str) -> str:
        """Extract preset name from JSON file.

        Args:
            filename: JSON filename.

        Returns:
            Preset name from file contents.
        """
        path = self._preset_dir / filename
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("name", filename.replace(".json", ""))

    def save(self, preset: FilterPreset) -> Path:
        """Save preset to JSON file.

        Args:
            preset: FilterPreset to save.

        Returns:
            Path to saved file.
        """
        self._preset_dir.mkdir(parents=True, exist_ok=True)

        # Add created timestamp if not set
        if preset.created is None:
            preset = FilterPreset(
                name=preset.name,
                column_filters=preset.column_filters,
                date_range=preset.date_range,
                time_range=preset.time_range,
                first_trigger_only=preset.first_trigger_only,
                created=datetime.now().isoformat(timespec="seconds"),
            )

        data = {
            "name": preset.name,
            "created": preset.created,
            "filters": {
                "column_filters": [
                    {
                        "column": f.column,
                        "operator": f.operator,
                        "min_val": f.min_val,
                        "max_val": f.max_val,
                    }
                    for f in preset.column_filters
                ],
                "date_range": {
                    "start": preset.date_range[0],
                    "end": preset.date_range[1],
                    "all_dates": preset.date_range[2],
                },
                "time_range": {
                    "start": preset.time_range[0],
                    "end": preset.time_range[1],
                    "all_times": preset.time_range[2],
                },
                "first_trigger_only": preset.first_trigger_only,
            },
        }

        filename = self._name_to_filename(preset.name)
        path = self._preset_dir / filename

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved filter preset '{preset.name}' to {path}")
        return path

    def load(self, name: str) -> FilterPreset:
        """Load preset by name.

        Args:
            name: Preset display name.

        Returns:
            Loaded FilterPreset.

        Raises:
            FileNotFoundError: If preset doesn't exist.
        """
        filename = self._name_to_filename(name)
        path = self._preset_dir / filename

        if not path.exists():
            raise FileNotFoundError(f"Preset '{name}' not found at {path}")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        filters = data.get("filters", {})

        column_filters = [
            FilterCriteria(
                column=f["column"],
                operator=f["operator"],
                min_val=f["min_val"],
                max_val=f["max_val"],
            )
            for f in filters.get("column_filters", [])
        ]

        date_range = filters.get("date_range", {})
        time_range = filters.get("time_range", {})

        preset = FilterPreset(
            name=data.get("name", name),
            column_filters=column_filters,
            date_range=(
                date_range.get("start"),
                date_range.get("end"),
                date_range.get("all_dates", True),
            ),
            time_range=(
                time_range.get("start"),
                time_range.get("end"),
                time_range.get("all_times", True),
            ),
            first_trigger_only=filters.get("first_trigger_only", True),
            created=data.get("created"),
        )

        logger.info(f"Loaded filter preset '{name}' from {path}")
        return preset

    def list_presets(self) -> list[str]:
        """List all available preset names.

        Returns:
            Sorted list of preset names.
        """
        if not self._preset_dir.exists():
            return []

        names = []
        for path in self._preset_dir.glob("*.json"):
            try:
                name = self._filename_to_name(path.name)
                names.append(name)
            except Exception as e:
                logger.warning(f"Failed to read preset {path}: {e}")

        return sorted(names)

    def delete(self, name: str) -> bool:
        """Delete a preset by name.

        Args:
            name: Preset display name.

        Returns:
            True if deleted, False if not found.
        """
        filename = self._name_to_filename(name)
        path = self._preset_dir / filename

        if not path.exists():
            return False

        path.unlink()
        logger.info(f"Deleted filter preset '{name}'")
        return True

    def exists(self, name: str) -> bool:
        """Check if a preset exists.

        Args:
            name: Preset display name.

        Returns:
            True if preset exists.
        """
        filename = self._name_to_filename(name)
        path = self._preset_dir / filename
        return path.exists()
