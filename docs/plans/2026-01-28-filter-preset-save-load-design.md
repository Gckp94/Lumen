# Filter Preset Save/Load Design

## Overview

Add save and load functionality for filter presets in the Feature Explorer tab, allowing users to quickly restore a complete filter configuration rather than manually recreating filters one by one.

## Requirements

- Save all filter state (column filters, date range, time range, first trigger toggle)
- Store presets as JSON files in a `filters/` directory
- Load dropdown shows available presets for quick selection
- Integrate seamlessly with existing FilterPanel UI

## UI Design

### Button Row Layout

Extends the existing button row:

```
[Apply Filters] [Clear All]    [Save] [▼ Load]
```

**Save Button** - Secondary ghost style:
- Background: `BG_ELEVATED` (#1E1E2C)
- Text: `TEXT_PRIMARY` (#F4F4F8)
- Border: 1px solid `BG_BORDER` (#2A2A3A)
- Hover: Border and text become `SIGNAL_AMBER` (#FFAA00)

**Load Dropdown** - Compact combo-style:
- Same secondary styling as Save button
- Dropdown arrow indicator on right
- Hover: Border becomes `SIGNAL_CYAN` (#00FFD4)
- Shows preset names alphabetically
- Empty state: "No saved presets" (disabled)

### Save Dialog

Minimal modal dialog:

```
┌─────────────────────────────────────┐
│  Save Filter Preset                 │
├─────────────────────────────────────┤
│  Name: [________________________]   │
│                                     │
│           [Cancel]  [Save]          │
└─────────────────────────────────────┘
```

- Dialog background: `BG_SURFACE` (#141420)
- Input field: `BG_ELEVATED` with `BG_BORDER` border
- Focus state: Border becomes `SIGNAL_CYAN`
- Save button: Primary style (`SIGNAL_CYAN` background)
- Cancel button: Secondary ghost style

## Data Model

### FilterPreset

```python
@dataclass
class FilterPreset:
    name: str
    column_filters: list[FilterCriteria]
    date_range: tuple[str | None, str | None, bool]  # start, end, all_dates
    time_range: tuple[str | None, str | None, bool]  # start, end, all_times
    first_trigger_only: bool
    created: str | None = None  # ISO timestamp
```

### JSON File Format

```json
{
  "name": "High Gap Morning",
  "created": "2026-01-28T10:30:00",
  "filters": {
    "column_filters": [
      {
        "column": "gap_pct",
        "operator": "between",
        "min_val": 5.0,
        "max_val": 15.0
      }
    ],
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-12-31",
      "all_dates": false
    },
    "time_range": {
      "start": "09:30:00",
      "end": "10:30:00",
      "all_times": false
    },
    "first_trigger_only": true
  }
}
```

### Storage

- Location: `filters/` directory in project root
- File naming: `{preset_name}.json` (spaces to underscores, lowercase)
- Example: "High Gap Morning" → `filters/high_gap_morning.json`

## Architecture

### New Components

#### 1. FilterPresetManager
`src/core/filter_preset_manager.py`

```python
class FilterPresetManager:
    def __init__(self, preset_dir: Path = Path("filters"))
    def save(self, name: str, preset: FilterPreset) -> Path
    def load(self, name: str) -> FilterPreset
    def list_presets(self) -> list[str]
    def delete(self, name: str) -> bool
```

#### 2. SavePresetDialog
`src/ui/dialogs/save_preset_dialog.py`

Simple modal with name input field, Cancel/Save buttons.

### Modified Components

#### FilterPanel
`src/ui/components/filter_panel.py`

Additions:
- `_save_btn` (QPushButton)
- `_load_combo` (QComboBox)
- Signals: `preset_save_requested(str)`, `preset_load_requested(str)`
- Methods: `get_full_state() -> FilterPreset`, `set_full_state(FilterPreset)`

## Interaction Flow

### Save Flow

1. User clicks **Save** button
2. `SavePresetDialog` opens with empty name field (focused)
3. User types preset name, clicks **Save** (or presses Enter)
4. `FilterPresetManager.save()` writes JSON to `filters/{name}.json`
5. Load dropdown refreshes to include new preset
6. Dialog closes

**Validation**:
- Empty name: Disable Save button
- Name exists: Prompt "Overwrite existing preset?"

### Load Flow

1. User clicks **Load** dropdown
2. Dropdown shows available presets (alphabetically sorted)
3. User selects a preset
4. `FilterPresetManager.load()` reads JSON
5. `FilterPanel.set_full_state()` populates all filter controls
6. Filters are NOT auto-applied (user reviews and clicks Apply)

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Preset file missing/corrupted | Toast: "Could not load preset" |
| Column doesn't exist in data | Skip filter, warn: "Some filters skipped (columns not found)" |
| No data loaded yet | Save/Load still work; filters apply when data loads |
| Preset directory missing | Created automatically on first save |
| Special characters in name | Sanitized to filesystem-safe characters |

## Implementation Tasks

1. Add `FilterPreset` dataclass to `src/core/models.py`
2. Create `FilterPresetManager` in `src/core/filter_preset_manager.py`
3. Create `SavePresetDialog` in `src/ui/dialogs/save_preset_dialog.py`
4. Update `FilterPanel` with Save button, Load dropdown, and state methods
5. Wire up signals in `FeatureExplorerTab`
