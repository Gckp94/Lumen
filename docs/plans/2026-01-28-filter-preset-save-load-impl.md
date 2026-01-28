# Filter Preset Save/Load Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add save/load filter presets to Feature Explorer, storing complete filter state in JSON files.

**Architecture:** New `FilterPresetManager` handles persistence to `filters/` directory. `FilterPreset` dataclass in models.py holds all filter state. `SavePresetDialog` provides naming UI. `FilterPanel` gains Save button + Load dropdown.

**Tech Stack:** PyQt6, JSON, dataclasses

---

## Task 1: Add FilterPreset Dataclass

**Files:**
- Modify: `src/core/models.py`
- Test: `tests/unit/test_filter_preset.py`

**Step 1: Write the failing test**

Create `tests/unit/test_filter_preset.py`:

```python
"""Tests for FilterPreset dataclass."""

import pytest

from src.core.models import FilterCriteria, FilterPreset


class TestFilterPreset:
    """Tests for FilterPreset dataclass."""

    def test_create_filter_preset(self):
        """Test creating a FilterPreset with all fields."""
        criteria = FilterCriteria(
            column="gap_pct",
            operator="between",
            min_val=5.0,
            max_val=15.0,
        )
        preset = FilterPreset(
            name="Test Preset",
            column_filters=[criteria],
            date_range=("2024-01-01", "2024-12-31", False),
            time_range=("09:30:00", "10:30:00", False),
            first_trigger_only=True,
        )

        assert preset.name == "Test Preset"
        assert len(preset.column_filters) == 1
        assert preset.column_filters[0].column == "gap_pct"
        assert preset.date_range == ("2024-01-01", "2024-12-31", False)
        assert preset.time_range == ("09:30:00", "10:30:00", False)
        assert preset.first_trigger_only is True
        assert preset.created is None

    def test_filter_preset_with_created_timestamp(self):
        """Test FilterPreset with created timestamp."""
        preset = FilterPreset(
            name="Timestamped",
            column_filters=[],
            date_range=(None, None, True),
            time_range=(None, None, True),
            first_trigger_only=False,
            created="2026-01-28T10:30:00",
        )

        assert preset.created == "2026-01-28T10:30:00"

    def test_filter_preset_empty_filters(self):
        """Test FilterPreset with no column filters."""
        preset = FilterPreset(
            name="Empty",
            column_filters=[],
            date_range=(None, None, True),
            time_range=(None, None, True),
            first_trigger_only=True,
        )

        assert preset.column_filters == []
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_filter_preset.py -v`
Expected: FAIL with `ImportError: cannot import name 'FilterPreset'`

**Step 3: Write minimal implementation**

Add to `src/core/models.py` after the `FilterCriteria` class (around line 392):

```python
@dataclass
class FilterPreset:
    """Complete filter state for save/load functionality.

    Attributes:
        name: Display name for the preset.
        column_filters: List of column filter criteria.
        date_range: Tuple of (start_iso, end_iso, all_dates).
        time_range: Tuple of (start_time, end_time, all_times).
        first_trigger_only: State of first trigger toggle.
        created: ISO timestamp when preset was created.
    """

    name: str
    column_filters: list[FilterCriteria]
    date_range: tuple[str | None, str | None, bool]
    time_range: tuple[str | None, str | None, bool]
    first_trigger_only: bool
    created: str | None = None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_filter_preset.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/core/models.py tests/unit/test_filter_preset.py
git commit -m "feat: add FilterPreset dataclass for filter save/load"
```

---

## Task 2: Create FilterPresetManager

**Files:**
- Create: `src/core/filter_preset_manager.py`
- Test: `tests/unit/test_filter_preset_manager.py`

**Step 1: Write the failing tests**

Create `tests/unit/test_filter_preset_manager.py`:

```python
"""Tests for FilterPresetManager."""

import json
from pathlib import Path

import pytest

from src.core.filter_preset_manager import FilterPresetManager
from src.core.models import FilterCriteria, FilterPreset


class TestFilterPresetManager:
    """Tests for FilterPresetManager."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create a temporary directory for presets."""
        preset_dir = tmp_path / "filters"
        preset_dir.mkdir()
        return preset_dir

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a FilterPresetManager with temp directory."""
        return FilterPresetManager(preset_dir=temp_dir)

    @pytest.fixture
    def sample_preset(self):
        """Create a sample FilterPreset."""
        return FilterPreset(
            name="Test Preset",
            column_filters=[
                FilterCriteria(
                    column="gap_pct",
                    operator="between",
                    min_val=5.0,
                    max_val=15.0,
                )
            ],
            date_range=("2024-01-01", "2024-12-31", False),
            time_range=("09:30:00", "10:30:00", False),
            first_trigger_only=True,
        )

    def test_save_creates_json_file(self, manager, sample_preset, temp_dir):
        """Test that save creates a JSON file."""
        path = manager.save(sample_preset)

        assert path.exists()
        assert path.suffix == ".json"
        assert path.parent == temp_dir

    def test_save_sanitizes_filename(self, manager, temp_dir):
        """Test that save sanitizes preset name for filename."""
        preset = FilterPreset(
            name="High Gap Morning",
            column_filters=[],
            date_range=(None, None, True),
            time_range=(None, None, True),
            first_trigger_only=True,
        )
        path = manager.save(preset)

        assert path.name == "high_gap_morning.json"

    def test_load_returns_preset(self, manager, sample_preset):
        """Test that load returns the saved preset."""
        manager.save(sample_preset)
        loaded = manager.load("Test Preset")

        assert loaded.name == sample_preset.name
        assert len(loaded.column_filters) == 1
        assert loaded.column_filters[0].column == "gap_pct"
        assert loaded.date_range == sample_preset.date_range
        assert loaded.time_range == sample_preset.time_range
        assert loaded.first_trigger_only == sample_preset.first_trigger_only

    def test_load_nonexistent_raises(self, manager):
        """Test that loading nonexistent preset raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            manager.load("Nonexistent")

    def test_list_presets_returns_names(self, manager, sample_preset):
        """Test that list_presets returns preset names."""
        manager.save(sample_preset)
        preset2 = FilterPreset(
            name="Another Preset",
            column_filters=[],
            date_range=(None, None, True),
            time_range=(None, None, True),
            first_trigger_only=False,
        )
        manager.save(preset2)

        names = manager.list_presets()

        assert "Test Preset" in names
        assert "Another Preset" in names
        assert len(names) == 2

    def test_list_presets_empty_directory(self, manager):
        """Test list_presets with no presets."""
        names = manager.list_presets()
        assert names == []

    def test_list_presets_sorted_alphabetically(self, manager):
        """Test that list_presets returns names sorted alphabetically."""
        for name in ["Zebra", "Alpha", "Middle"]:
            preset = FilterPreset(
                name=name,
                column_filters=[],
                date_range=(None, None, True),
                time_range=(None, None, True),
                first_trigger_only=True,
            )
            manager.save(preset)

        names = manager.list_presets()
        assert names == ["Alpha", "Middle", "Zebra"]

    def test_delete_removes_file(self, manager, sample_preset, temp_dir):
        """Test that delete removes the preset file."""
        path = manager.save(sample_preset)
        assert path.exists()

        result = manager.delete("Test Preset")

        assert result is True
        assert not path.exists()

    def test_delete_nonexistent_returns_false(self, manager):
        """Test that deleting nonexistent preset returns False."""
        result = manager.delete("Nonexistent")
        assert result is False

    def test_exists_returns_true_for_existing(self, manager, sample_preset):
        """Test exists returns True for saved preset."""
        manager.save(sample_preset)
        assert manager.exists("Test Preset") is True

    def test_exists_returns_false_for_nonexistent(self, manager):
        """Test exists returns False for nonexistent preset."""
        assert manager.exists("Nonexistent") is False

    def test_save_creates_directory_if_missing(self, tmp_path):
        """Test that save creates preset directory if it doesn't exist."""
        preset_dir = tmp_path / "new_filters"
        manager = FilterPresetManager(preset_dir=preset_dir)
        preset = FilterPreset(
            name="Test",
            column_filters=[],
            date_range=(None, None, True),
            time_range=(None, None, True),
            first_trigger_only=True,
        )

        path = manager.save(preset)

        assert preset_dir.exists()
        assert path.exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_filter_preset_manager.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.core.filter_preset_manager'`

**Step 3: Write minimal implementation**

Create `src/core/filter_preset_manager.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_filter_preset_manager.py -v`
Expected: PASS (13 tests)

**Step 5: Commit**

```bash
git add src/core/filter_preset_manager.py tests/unit/test_filter_preset_manager.py
git commit -m "feat: add FilterPresetManager for preset persistence"
```

---

## Task 3: Create SavePresetDialog

**Files:**
- Create: `src/ui/dialogs/save_preset_dialog.py`
- Modify: `src/ui/dialogs/__init__.py`
- Test: `tests/unit/test_save_preset_dialog.py`

**Step 1: Write the failing test**

Create `tests/unit/test_save_preset_dialog.py`:

```python
"""Tests for SavePresetDialog."""

import pytest
from pytestqt.qtbot import QtBot

from src.ui.dialogs.save_preset_dialog import SavePresetDialog


class TestSavePresetDialog:
    """Tests for SavePresetDialog."""

    def test_dialog_creation(self, qtbot: QtBot):
        """Test dialog can be created."""
        dialog = SavePresetDialog()
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Save Filter Preset"

    def test_get_preset_name_returns_input(self, qtbot: QtBot):
        """Test get_preset_name returns the entered name."""
        dialog = SavePresetDialog()
        qtbot.addWidget(dialog)

        dialog._name_input.setText("My Preset")

        assert dialog.get_preset_name() == "My Preset"

    def test_save_button_disabled_when_empty(self, qtbot: QtBot):
        """Test save button is disabled when name is empty."""
        dialog = SavePresetDialog()
        qtbot.addWidget(dialog)

        dialog._name_input.setText("")

        assert not dialog._save_btn.isEnabled()

    def test_save_button_enabled_when_name_entered(self, qtbot: QtBot):
        """Test save button is enabled when name is entered."""
        dialog = SavePresetDialog()
        qtbot.addWidget(dialog)

        dialog._name_input.setText("Test")

        assert dialog._save_btn.isEnabled()

    def test_set_existing_names_for_validation(self, qtbot: QtBot):
        """Test setting existing names for duplicate checking."""
        dialog = SavePresetDialog(existing_names=["Existing"])
        qtbot.addWidget(dialog)

        dialog._name_input.setText("Existing")

        # Should show warning but still allow save (for overwrite)
        assert dialog._save_btn.isEnabled()
        assert dialog._warning_label.isVisible()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_save_preset_dialog.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `src/ui/dialogs/save_preset_dialog.py`:

```python
"""Save filter preset dialog."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.constants import Colors, Spacing


class SavePresetDialog(QDialog):
    """Dialog for entering a preset name when saving filters.

    Attributes:
        existing_names: List of existing preset names for duplicate detection.
    """

    def __init__(
        self,
        existing_names: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize SavePresetDialog.

        Args:
            existing_names: Existing preset names for duplicate warning.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._existing_names = [n.lower() for n in (existing_names or [])]
        self._setup_ui()
        self._apply_style()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up dialog UI."""
        self.setWindowTitle("Save Filter Preset")
        self.setMinimumWidth(350)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.MD)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)

        # Name input row
        name_layout = QHBoxLayout()
        name_label = QLabel("Name:")
        name_layout.addWidget(name_label)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Enter preset name")
        name_layout.addWidget(self._name_input, stretch=1)
        layout.addLayout(name_layout)

        # Warning label (hidden by default)
        self._warning_label = QLabel("A preset with this name already exists")
        self._warning_label.setVisible(False)
        layout.addWidget(self._warning_label)

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)

        self._save_btn = QPushButton("Save")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self.accept)
        self._save_btn.setDefault(True)
        btn_layout.addWidget(self._save_btn)

        layout.addLayout(btn_layout)

    def _apply_style(self) -> None:
        """Apply Observatory theme styling."""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_SURFACE};
            }}
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-size: 13px;
            }}
            QLineEdit {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
        """)

        # Primary button (Save)
        self._save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SIGNAL_CYAN};
                color: {Colors.BG_BASE};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {Colors.SIGNAL_BLUE};
            }}
            QPushButton:disabled {{
                background-color: {Colors.BG_BORDER};
                color: {Colors.TEXT_DISABLED};
            }}
        """)

        # Secondary button (Cancel)
        self._cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                border-color: {Colors.SIGNAL_CYAN};
                color: {Colors.SIGNAL_CYAN};
            }}
        """)

        # Warning label
        self._warning_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.SIGNAL_AMBER};
                font-size: 12px;
            }}
        """)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self._name_input.textChanged.connect(self._on_name_changed)

    def _on_name_changed(self, text: str) -> None:
        """Handle name input changes.

        Args:
            text: Current input text.
        """
        name = text.strip()
        has_name = bool(name)
        is_duplicate = name.lower() in self._existing_names

        self._save_btn.setEnabled(has_name)
        self._warning_label.setVisible(has_name and is_duplicate)

    def get_preset_name(self) -> str:
        """Get the entered preset name.

        Returns:
            Trimmed preset name.
        """
        return self._name_input.text().strip()
```

Update `src/ui/dialogs/__init__.py` to export the new dialog:

```python
"""UI dialogs module."""

from src.ui.dialogs.chart_expand_dialog import ChartExpandDialog
from src.ui.dialogs.import_strategy_dialog import ImportStrategyDialog
from src.ui.dialogs.save_preset_dialog import SavePresetDialog
from src.ui.dialogs.update_dialog import UpdateDialog

__all__ = [
    "ChartExpandDialog",
    "ImportStrategyDialog",
    "SavePresetDialog",
    "UpdateDialog",
]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_save_preset_dialog.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add src/ui/dialogs/save_preset_dialog.py src/ui/dialogs/__init__.py tests/unit/test_save_preset_dialog.py
git commit -m "feat: add SavePresetDialog for naming presets"
```

---

## Task 4: Add set_range Methods to Date/Time Filters

**Files:**
- Modify: `src/ui/components/date_range_filter.py`
- Modify: `src/ui/components/time_range_filter.py`
- Test: `tests/unit/test_date_time_filter_setters.py`

**Step 1: Write the failing tests**

Create `tests/unit/test_date_time_filter_setters.py`:

```python
"""Tests for DateRangeFilter and TimeRangeFilter set_range methods."""

import pytest
from pytestqt.qtbot import QtBot

from src.ui.components.date_range_filter import DateRangeFilter
from src.ui.components.time_range_filter import TimeRangeFilter


class TestDateRangeFilterSetRange:
    """Tests for DateRangeFilter.set_range method."""

    def test_set_range_with_dates(self, qtbot: QtBot):
        """Test setting a specific date range."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        widget.set_range("2024-01-15", "2024-06-30", False)

        start, end, all_dates = widget.get_range()
        assert start == "2024-01-15"
        assert end == "2024-06-30"
        assert all_dates is False

    def test_set_range_all_dates(self, qtbot: QtBot):
        """Test setting all dates mode."""
        widget = DateRangeFilter()
        qtbot.addWidget(widget)

        # First set specific dates
        widget.set_range("2024-01-01", "2024-12-31", False)
        # Then set all dates
        widget.set_range(None, None, True)

        start, end, all_dates = widget.get_range()
        assert all_dates is True


class TestTimeRangeFilterSetRange:
    """Tests for TimeRangeFilter.set_range method."""

    def test_set_range_with_times(self, qtbot: QtBot):
        """Test setting a specific time range."""
        widget = TimeRangeFilter()
        qtbot.addWidget(widget)

        widget.set_range("09:30:00", "10:30:00", False)

        start, end, all_times = widget.get_range()
        assert start == "09:30:00"
        assert end == "10:30:00"
        assert all_times is False

    def test_set_range_all_times(self, qtbot: QtBot):
        """Test setting all times mode."""
        widget = TimeRangeFilter()
        qtbot.addWidget(widget)

        # First set specific times
        widget.set_range("09:00:00", "16:00:00", False)
        # Then set all times
        widget.set_range(None, None, True)

        start, end, all_times = widget.get_range()
        assert all_times is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_date_time_filter_setters.py -v`
Expected: FAIL with `AttributeError: 'DateRangeFilter' object has no attribute 'set_range'`

**Step 3: Write minimal implementation**

Add to `src/ui/components/date_range_filter.py` after the `reset` method:

```python
    def set_range(
        self, start: str | None, end: str | None, all_dates: bool
    ) -> None:
        """Set the date range programmatically.

        Args:
            start: Start date ISO string (YYYY-MM-DD) or None.
            end: End date ISO string (YYYY-MM-DD) or None.
            all_dates: Whether to enable 'All Dates' mode.
        """
        # Block signals during update
        self._all_dates_checkbox.blockSignals(True)
        self._start_date.blockSignals(True)
        self._end_date.blockSignals(True)

        self._all_dates = all_dates
        self._all_dates_checkbox.setChecked(all_dates)
        self._start_date.setEnabled(not all_dates)
        self._end_date.setEnabled(not all_dates)

        if start:
            date = QDate.fromString(start, Qt.DateFormat.ISODate)
            if date.isValid():
                self._start_date.setDate(date)

        if end:
            date = QDate.fromString(end, Qt.DateFormat.ISODate)
            if date.isValid():
                self._end_date.setDate(date)

        # Restore signals
        self._all_dates_checkbox.blockSignals(False)
        self._start_date.blockSignals(False)
        self._end_date.blockSignals(False)

        self._emit_change()
```

Add to `src/ui/components/time_range_filter.py` after the `reset` method:

```python
    def set_range(
        self, start: str | None, end: str | None, all_times: bool
    ) -> None:
        """Set the time range programmatically.

        Args:
            start: Start time string (HH:MM:SS) or None.
            end: End time string (HH:MM:SS) or None.
            all_times: Whether to enable 'All Times' mode.
        """
        # Block signals during update
        self._all_times_checkbox.blockSignals(True)
        self._start_time.blockSignals(True)
        self._end_time.blockSignals(True)

        self._all_times = all_times
        self._all_times_checkbox.setChecked(all_times)
        self._start_time.setEnabled(not all_times)
        self._end_time.setEnabled(not all_times)

        if start:
            time = QTime.fromString(start, "HH:mm:ss")
            if time.isValid():
                self._start_time.setTime(time)

        if end:
            time = QTime.fromString(end, "HH:mm:ss")
            if time.isValid():
                self._end_time.setTime(time)

        # Restore signals
        self._all_times_checkbox.blockSignals(False)
        self._start_time.blockSignals(False)
        self._end_time.blockSignals(False)

        self._emit_change()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_date_time_filter_setters.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add src/ui/components/date_range_filter.py src/ui/components/time_range_filter.py tests/unit/test_date_time_filter_setters.py
git commit -m "feat: add set_range methods to DateRangeFilter and TimeRangeFilter"
```

---

## Task 5: Add set_filter_values to ColumnFilterPanel

**Files:**
- Modify: `src/ui/components/column_filter_panel.py`
- Test: `tests/unit/test_column_filter_panel_set_values.py`

**Step 1: Write the failing test**

Create `tests/unit/test_column_filter_panel_set_values.py`:

```python
"""Tests for ColumnFilterPanel.set_filter_values method."""

import pytest
from pytestqt.qtbot import QtBot

from src.core.models import FilterCriteria
from src.ui.components.column_filter_panel import ColumnFilterPanel


class TestColumnFilterPanelSetValues:
    """Tests for ColumnFilterPanel.set_filter_values method."""

    def test_set_filter_values_populates_rows(self, qtbot: QtBot):
        """Test that set_filter_values populates matching rows."""
        panel = ColumnFilterPanel(columns=["gap_pct", "volume", "price"])
        qtbot.addWidget(panel)

        criteria = [
            FilterCriteria(column="gap_pct", operator="between", min_val=5.0, max_val=15.0),
            FilterCriteria(column="volume", operator="not_between", min_val=100.0, max_val=500.0),
        ]

        panel.set_filter_values(criteria)

        active = panel.get_active_criteria()
        assert len(active) == 2

        # Check gap_pct filter
        gap_filter = next(c for c in active if c.column == "gap_pct")
        assert gap_filter.min_val == 5.0
        assert gap_filter.max_val == 15.0
        assert gap_filter.operator == "between"

    def test_set_filter_values_skips_missing_columns(self, qtbot: QtBot):
        """Test that missing columns are skipped without error."""
        panel = ColumnFilterPanel(columns=["gap_pct", "volume"])
        qtbot.addWidget(panel)

        criteria = [
            FilterCriteria(column="gap_pct", operator="between", min_val=5.0, max_val=15.0),
            FilterCriteria(column="nonexistent", operator="between", min_val=1.0, max_val=10.0),
        ]

        # Should not raise
        skipped = panel.set_filter_values(criteria)

        assert "nonexistent" in skipped
        active = panel.get_active_criteria()
        assert len(active) == 1

    def test_set_filter_values_clears_existing(self, qtbot: QtBot):
        """Test that set_filter_values clears existing values first."""
        panel = ColumnFilterPanel(columns=["gap_pct", "volume"])
        qtbot.addWidget(panel)

        # Set initial filters
        panel.set_filter_values([
            FilterCriteria(column="gap_pct", operator="between", min_val=1.0, max_val=2.0),
            FilterCriteria(column="volume", operator="between", min_val=10.0, max_val=20.0),
        ])

        # Set new filters (only gap_pct)
        panel.set_filter_values([
            FilterCriteria(column="gap_pct", operator="between", min_val=5.0, max_val=15.0),
        ])

        active = panel.get_active_criteria()
        assert len(active) == 1
        assert active[0].column == "gap_pct"
        assert active[0].min_val == 5.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_column_filter_panel_set_values.py -v`
Expected: FAIL with `AttributeError: 'ColumnFilterPanel' object has no attribute 'set_filter_values'`

**Step 3: Write minimal implementation**

Add to `src/ui/components/column_filter_panel.py` after the `set_columns` method:

```python
    def set_filter_values(self, criteria: list[FilterCriteria]) -> list[str]:
        """Set filter values from a list of FilterCriteria.

        Populates rows matching the criteria columns. Skips criteria
        for columns that don't exist in the panel.

        Args:
            criteria: List of FilterCriteria to apply.

        Returns:
            List of column names that were skipped (not found).
        """
        # Clear all existing values first
        self.clear_all()

        skipped = []
        column_to_row = {row.get_column_name(): row for row in self._rows}

        for c in criteria:
            row = column_to_row.get(c.column)
            if row:
                row.set_values(c.operator, c.min_val, c.max_val)
            else:
                skipped.append(c.column)

        return skipped
```

Also need to update `ColumnFilterRow.set_values` to accept operator. Check current implementation:

```python
    def set_values(
        self,
        operator: str,
        min_val: float | None,
        max_val: float | None,
    ) -> None:
        """Set filter values programmatically.

        Args:
            operator: Filter operator ('between' or 'not_between').
            min_val: Minimum value or None.
            max_val: Maximum value or None.
        """
        # Set operator
        self._operator = operator
        self._operator_btn.setText(operator)

        # Set values
        self._min_input.blockSignals(True)
        self._max_input.blockSignals(True)

        self._min_input.setText(str(min_val) if min_val is not None else "")
        self._max_input.setText(str(max_val) if max_val is not None else "")

        self._min_input.blockSignals(False)
        self._max_input.blockSignals(False)

        self._update_indicator()
        self.values_changed.emit()
```

If `ColumnFilterRow.set_values` signature differs, update it to match. Check existing implementation first.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_column_filter_panel_set_values.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/ui/components/column_filter_panel.py src/ui/components/column_filter_row.py tests/unit/test_column_filter_panel_set_values.py
git commit -m "feat: add set_filter_values to ColumnFilterPanel"
```

---

## Task 6: Add Save/Load UI to FilterPanel

**Files:**
- Modify: `src/ui/components/filter_panel.py`
- Test: `tests/unit/test_filter_panel_preset_ui.py`

**Step 1: Write the failing test**

Create `tests/unit/test_filter_panel_preset_ui.py`:

```python
"""Tests for FilterPanel preset save/load UI."""

import pytest
from pytestqt.qtbot import QtBot

from src.ui.components.filter_panel import FilterPanel


class TestFilterPanelPresetUI:
    """Tests for FilterPanel preset save/load buttons."""

    def test_has_save_button(self, qtbot: QtBot):
        """Test FilterPanel has a Save button."""
        panel = FilterPanel()
        qtbot.addWidget(panel)

        assert hasattr(panel, "_save_btn")
        assert panel._save_btn.text() == "Save"

    def test_has_load_combo(self, qtbot: QtBot):
        """Test FilterPanel has a Load dropdown."""
        panel = FilterPanel()
        qtbot.addWidget(panel)

        assert hasattr(panel, "_load_combo")

    def test_save_button_emits_signal(self, qtbot: QtBot):
        """Test Save button click emits preset_save_requested signal."""
        panel = FilterPanel()
        qtbot.addWidget(panel)

        with qtbot.waitSignal(panel.preset_save_requested, timeout=1000):
            panel._save_btn.click()

    def test_load_combo_emits_signal_on_selection(self, qtbot: QtBot):
        """Test Load combo selection emits preset_load_requested signal."""
        panel = FilterPanel()
        qtbot.addWidget(panel)

        # Add a preset to the combo
        panel.update_preset_list(["Test Preset"])

        with qtbot.waitSignal(panel.preset_load_requested, timeout=1000) as blocker:
            panel._load_combo.setCurrentIndex(1)  # Select "Test Preset"

        assert blocker.args == ["Test Preset"]

    def test_update_preset_list(self, qtbot: QtBot):
        """Test update_preset_list populates the dropdown."""
        panel = FilterPanel()
        qtbot.addWidget(panel)

        panel.update_preset_list(["Alpha", "Beta", "Gamma"])

        # First item is placeholder, then presets
        assert panel._load_combo.count() == 4
        assert panel._load_combo.itemText(1) == "Alpha"
        assert panel._load_combo.itemText(2) == "Beta"
        assert panel._load_combo.itemText(3) == "Gamma"

    def test_empty_preset_list_shows_placeholder(self, qtbot: QtBot):
        """Test empty preset list shows 'No saved presets'."""
        panel = FilterPanel()
        qtbot.addWidget(panel)

        panel.update_preset_list([])

        assert panel._load_combo.count() == 1
        assert "No saved presets" in panel._load_combo.itemText(0)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_filter_panel_preset_ui.py -v`
Expected: FAIL with `AttributeError: 'FilterPanel' object has no attribute '_save_btn'`

**Step 3: Write minimal implementation**

Modify `src/ui/components/filter_panel.py`:

1. Add new signals at class level (after existing signals around line 40):

```python
    preset_save_requested = pyqtSignal()  # Emitted when Save clicked
    preset_load_requested = pyqtSignal(str)  # Emitted with preset name
```

2. Add imports at top:

```python
from PyQt6.QtWidgets import QComboBox
```

3. In `_setup_ui`, modify the button row section (around line 135-149) to add Save and Load:

```python
        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(Spacing.SM)

        self._apply_btn = QPushButton("Apply Filters")
        self._apply_btn.clicked.connect(self._on_apply_filters)
        btn_layout.addWidget(self._apply_btn)

        self._clear_btn = QPushButton("Clear All")
        self._clear_btn.clicked.connect(self._on_clear_filters)
        btn_layout.addWidget(self._clear_btn)

        btn_layout.addSpacing(Spacing.MD)

        self._save_btn = QPushButton("Save")
        self._save_btn.clicked.connect(self._on_save_clicked)
        btn_layout.addWidget(self._save_btn)

        self._load_combo = QComboBox()
        self._load_combo.addItem("Load preset...")
        self._load_combo.currentIndexChanged.connect(self._on_load_selected)
        btn_layout.addWidget(self._load_combo)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)
```

4. In `_apply_style`, add styles for the new widgets (after secondary_btn_style):

```python
        # Save button (amber accent)
        save_btn_style = f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                border-color: {Colors.SIGNAL_AMBER};
                color: {Colors.SIGNAL_AMBER};
            }}
        """
        self._save_btn.setStyleSheet(save_btn_style)

        # Load combo
        load_combo_style = f"""
            QComboBox {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 120px;
            }}
            QComboBox:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {Colors.TEXT_SECONDARY};
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                selection-background-color: {Colors.BG_SURFACE};
            }}
        """
        self._load_combo.setStyleSheet(load_combo_style)
```

5. Add handler methods at the end of the class:

```python
    def _on_save_clicked(self) -> None:
        """Handle Save button click."""
        self.preset_save_requested.emit()

    def _on_load_selected(self, index: int) -> None:
        """Handle Load combo selection.

        Args:
            index: Selected item index.
        """
        if index > 0:  # Skip placeholder
            preset_name = self._load_combo.itemText(index)
            self.preset_load_requested.emit(preset_name)
            # Reset to placeholder
            self._load_combo.blockSignals(True)
            self._load_combo.setCurrentIndex(0)
            self._load_combo.blockSignals(False)

    def update_preset_list(self, names: list[str]) -> None:
        """Update the Load dropdown with available presets.

        Args:
            names: List of preset names (already sorted).
        """
        self._load_combo.blockSignals(True)
        self._load_combo.clear()

        if names:
            self._load_combo.addItem("Load preset...")
            for name in names:
                self._load_combo.addItem(name)
        else:
            self._load_combo.addItem("No saved presets")

        self._load_combo.blockSignals(False)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_filter_panel_preset_ui.py -v`
Expected: PASS (6 tests)

**Step 5: Commit**

```bash
git add src/ui/components/filter_panel.py tests/unit/test_filter_panel_preset_ui.py
git commit -m "feat: add Save button and Load dropdown to FilterPanel"
```

---

## Task 7: Add get/set State Methods to FilterPanel

**Files:**
- Modify: `src/ui/components/filter_panel.py`
- Test: `tests/unit/test_filter_panel_state.py`

**Step 1: Write the failing test**

Create `tests/unit/test_filter_panel_state.py`:

```python
"""Tests for FilterPanel get_full_state and set_full_state methods."""

import pytest
from pytestqt.qtbot import QtBot

from src.core.models import FilterCriteria, FilterPreset
from src.ui.components.filter_panel import FilterPanel


class TestFilterPanelState:
    """Tests for FilterPanel state methods."""

    def test_get_full_state_returns_preset(self, qtbot: QtBot):
        """Test get_full_state returns a FilterPreset."""
        panel = FilterPanel(columns=["gap_pct", "volume"])
        qtbot.addWidget(panel)

        state = panel.get_full_state("Test")

        assert isinstance(state, FilterPreset)
        assert state.name == "Test"

    def test_set_full_state_applies_filters(self, qtbot: QtBot):
        """Test set_full_state applies all filter values."""
        panel = FilterPanel(columns=["gap_pct", "volume"])
        qtbot.addWidget(panel)

        preset = FilterPreset(
            name="Test",
            column_filters=[
                FilterCriteria(column="gap_pct", operator="between", min_val=5.0, max_val=15.0),
            ],
            date_range=("2024-01-01", "2024-06-30", False),
            time_range=("09:30:00", "10:30:00", False),
            first_trigger_only=False,
        )

        skipped = panel.set_full_state(preset)

        assert skipped == []
        # Verify state was applied
        state = panel.get_full_state("Check")
        assert len(state.column_filters) == 1
        assert state.first_trigger_only is False

    def test_set_full_state_returns_skipped_columns(self, qtbot: QtBot):
        """Test set_full_state returns list of skipped columns."""
        panel = FilterPanel(columns=["gap_pct"])
        qtbot.addWidget(panel)

        preset = FilterPreset(
            name="Test",
            column_filters=[
                FilterCriteria(column="gap_pct", operator="between", min_val=5.0, max_val=15.0),
                FilterCriteria(column="nonexistent", operator="between", min_val=1.0, max_val=10.0),
            ],
            date_range=(None, None, True),
            time_range=(None, None, True),
            first_trigger_only=True,
        )

        skipped = panel.set_full_state(preset)

        assert "nonexistent" in skipped
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_filter_panel_state.py -v`
Expected: FAIL with `AttributeError: 'FilterPanel' object has no attribute 'get_full_state'`

**Step 3: Write minimal implementation**

Add imports at top of `src/ui/components/filter_panel.py`:

```python
from src.core.models import FilterCriteria, FilterPreset
```

Add methods at end of class:

```python
    def get_full_state(self, name: str) -> FilterPreset:
        """Get complete filter state as a FilterPreset.

        Args:
            name: Name for the preset.

        Returns:
            FilterPreset with all current filter state.
        """
        return FilterPreset(
            name=name,
            column_filters=self._column_filter_panel.get_active_criteria(),
            date_range=self.get_date_range(),
            time_range=self.get_time_range(),
            first_trigger_only=self._first_trigger_toggle.isChecked(),
        )

    def set_full_state(self, preset: FilterPreset) -> list[str]:
        """Apply a FilterPreset to all filter controls.

        Args:
            preset: FilterPreset to apply.

        Returns:
            List of column names that were skipped (not found).
        """
        # Set column filters
        skipped = self._column_filter_panel.set_filter_values(preset.column_filters)

        # Set date range
        self._date_range_filter.set_range(*preset.date_range)

        # Set time range
        self._time_range_filter.set_range(*preset.time_range)

        # Set first trigger toggle
        self._first_trigger_toggle.setChecked(preset.first_trigger_only)

        return skipped
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_filter_panel_state.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/ui/components/filter_panel.py tests/unit/test_filter_panel_state.py
git commit -m "feat: add get_full_state and set_full_state to FilterPanel"
```

---

## Task 8: Wire Up Save/Load in FeatureExplorerTab

**Files:**
- Modify: `src/tabs/feature_explorer.py`
- Test: Manual integration test

**Step 1: Add imports**

Add to imports at top of `src/tabs/feature_explorer.py`:

```python
from src.core.filter_preset_manager import FilterPresetManager
from src.ui.dialogs.save_preset_dialog import SavePresetDialog
```

**Step 2: Initialize FilterPresetManager**

In `__init__` method, add after other initializations:

```python
        self._preset_manager = FilterPresetManager()
```

**Step 3: Connect signals**

In `_connect_signals` method, add:

```python
        self._filter_panel.preset_save_requested.connect(self._on_preset_save)
        self._filter_panel.preset_load_requested.connect(self._on_preset_load)
```

**Step 4: Add handler methods**

Add at end of class:

```python
    def _on_preset_save(self) -> None:
        """Handle preset save request."""
        existing = self._preset_manager.list_presets()
        dialog = SavePresetDialog(existing_names=existing, parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.get_preset_name()
            preset = self._filter_panel.get_full_state(name)
            self._preset_manager.save(preset)
            self._refresh_preset_list()

    def _on_preset_load(self, name: str) -> None:
        """Handle preset load request.

        Args:
            name: Preset name to load.
        """
        try:
            preset = self._preset_manager.load(name)
            skipped = self._filter_panel.set_full_state(preset)
            if skipped:
                # Log warning about skipped columns
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Skipped columns not in data: {skipped}")
        except FileNotFoundError:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Preset '{name}' not found")

    def _refresh_preset_list(self) -> None:
        """Refresh the preset dropdown with current presets."""
        names = self._preset_manager.list_presets()
        self._filter_panel.update_preset_list(names)
```

**Step 5: Initialize preset list on data load**

In `_on_data_loaded` method, add at the end:

```python
        self._refresh_preset_list()
```

**Step 6: Add QDialog import**

Add to imports:

```python
from PyQt6.QtWidgets import QDialog
```

**Step 7: Manual integration test**

1. Run the application: `python -m src.main`
2. Load data in Data Input tab
3. Go to Feature Explorer tab
4. Set some filters (column filters, date range, time range, first trigger)
5. Click Save button
6. Enter a name and click Save
7. Clear filters
8. Select the preset from Load dropdown
9. Verify all filters are restored

**Step 8: Commit**

```bash
git add src/tabs/feature_explorer.py
git commit -m "feat: wire up filter preset save/load in FeatureExplorerTab"
```

---

## Task 9: Add filters/ to .gitignore

**Files:**
- Modify: `.gitignore`

**Step 1: Add filters directory**

Add to `.gitignore`:

```
# Filter presets (user-specific)
filters/
```

**Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: add filters/ directory to .gitignore"
```

---

## Task 10: Run Full Test Suite

**Step 1: Run all tests**

```bash
pytest tests/unit/test_filter_preset.py tests/unit/test_filter_preset_manager.py tests/unit/test_save_preset_dialog.py tests/unit/test_date_time_filter_setters.py tests/unit/test_column_filter_panel_set_values.py tests/unit/test_filter_panel_preset_ui.py tests/unit/test_filter_panel_state.py -v
```

Expected: All tests pass

**Step 2: Run full test suite**

```bash
pytest tests/ --ignore=tests/ui --ignore=tests/widget -q
```

Expected: No new failures introduced

---

## Summary

**New files created:**
- `src/core/filter_preset_manager.py`
- `src/ui/dialogs/save_preset_dialog.py`
- `tests/unit/test_filter_preset.py`
- `tests/unit/test_filter_preset_manager.py`
- `tests/unit/test_save_preset_dialog.py`
- `tests/unit/test_date_time_filter_setters.py`
- `tests/unit/test_column_filter_panel_set_values.py`
- `tests/unit/test_filter_panel_preset_ui.py`
- `tests/unit/test_filter_panel_state.py`

**Modified files:**
- `src/core/models.py` - Added FilterPreset dataclass
- `src/ui/components/filter_panel.py` - Added Save/Load UI and state methods
- `src/ui/components/date_range_filter.py` - Added set_range method
- `src/ui/components/time_range_filter.py` - Added set_range method
- `src/ui/components/column_filter_panel.py` - Added set_filter_values method
- `src/ui/dialogs/__init__.py` - Export SavePresetDialog
- `src/tabs/feature_explorer.py` - Wire up preset save/load
- `.gitignore` - Add filters/ directory
