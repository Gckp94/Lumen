# Filter Panel UX Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve filter panel UX with visible apply icons, active filter display after single-row apply, and expanded panel height.

**Architecture:** Three targeted fixes to existing PyQt6 components - improving apply button visibility with a styled plus icon, connecting single-filter-apply to chip display, and expanding panel height constraints.

**Tech Stack:** PyQt6, Python, existing Observatory theme (Colors, Fonts from constants.py)

---

## Task 1: Add Plus Icon to Apply Button

**Files:**
- Modify: `src/ui/components/column_filter_row.py:90-116`
- Test: `tests/ui/components/test_column_filter_row.py`

**Context:** The apply button currently uses `setText("\u25b6")` (▶) which renders blank. Replace with a styled plus icon that's visible and fits the Observatory theme.

**Frontend Design:** Refined minimalist approach - a bold "+" character with proper font weight and sizing, amber accent on hover to indicate "add this filter". The icon should be immediately recognizable and feel intentional.

**Step 1: Write the failing test**

In `tests/ui/components/test_column_filter_row.py`, add:

```python
def test_apply_button_has_visible_icon(qtbot: QtBot) -> None:
    """Test that apply button displays a visible plus icon."""
    row = ColumnFilterRow(column_name="test_col")
    qtbot.addWidget(row)

    # Button should have a plus icon text
    assert row._apply_btn.text() == "+"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/ui/components/test_column_filter_row.py::test_apply_button_has_visible_icon -v`
Expected: FAIL with AssertionError (current text is "▶")

**Step 3: Update apply button to use plus icon**

In `src/ui/components/column_filter_row.py`, replace the apply button setup (around line 90-116) with:

```python
        # Apply button (for applying this single filter)
        self._apply_btn = QPushButton("+")
        self._apply_btn.setFixedSize(22, 22)
        self._apply_btn.setToolTip("Apply this filter")
        self._apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
                font-family: "{Fonts.UI}";
                color: {Colors.TEXT_SECONDARY};
            }}
            QPushButton:hover {{
                background: {Colors.BG_BORDER};
                border-color: {Colors.SIGNAL_AMBER};
                color: {Colors.SIGNAL_AMBER};
            }}
            QPushButton:pressed {{
                background: {Colors.BG_ELEVATED};
            }}
            QPushButton:disabled {{
                color: {Colors.TEXT_DISABLED};
                border-color: transparent;
            }}
        """)
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._on_apply_clicked)
        layout.addWidget(self._apply_btn)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/ui/components/test_column_filter_row.py::test_apply_button_has_visible_icon -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/ui/components/test_column_filter_row.py src/ui/components/column_filter_row.py
git commit -m "feat: add visible plus icon to filter row apply button"
```

---

## Task 2: Display Active Filter Chips After Single-Row Apply

**Files:**
- Modify: `src/ui/components/filter_panel.py:205-211`
- Test: `tests/ui/components/test_filter_panel.py`

**Context:** When a user clicks the per-row apply button, the filter should appear as a chip in the chips area, showing what was added and allowing removal.

**Frontend Design:** The chip already exists with amber background and trash icon. We just need to wire up the single-apply to add the chip (currently only bulk "Apply Filters" shows chips).

**Step 1: Write the failing test**

In `tests/ui/components/test_filter_panel.py`, add:

```python
def test_single_filter_apply_creates_chip(qtbot: QtBot) -> None:
    """Test that applying a single filter creates a visible chip."""
    panel = FilterPanel(columns=["price", "volume"])
    qtbot.addWidget(panel)

    # Simulate single filter applied
    from src.core.models import FilterCriteria
    criteria = FilterCriteria(column="price", operator="between", min_val=10.0, max_val=20.0)
    panel._on_single_filter_applied(criteria)

    # Chip should be created
    assert len(panel._filter_chips) == 1
    assert panel._filter_chips[0]._criteria == criteria


def test_single_filter_chip_can_be_removed(qtbot: QtBot) -> None:
    """Test that single filter chip can be removed."""
    panel = FilterPanel(columns=["price"])
    qtbot.addWidget(panel)

    from src.core.models import FilterCriteria
    criteria = FilterCriteria(column="price", operator="between", min_val=10.0, max_val=20.0)
    panel._on_single_filter_applied(criteria)

    assert len(panel._filter_chips) == 1

    # Simulate chip removal
    panel._on_chip_removed(criteria)

    assert len(panel._filter_chips) == 0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/ui/components/test_filter_panel.py::test_single_filter_apply_creates_chip tests/ui/components/test_filter_panel.py::test_single_filter_chip_can_be_removed -v`
Expected: FAIL (chips are empty because `_on_single_filter_applied` doesn't update chips)

**Step 3: Update `_on_single_filter_applied` to add chip**

In `src/ui/components/filter_panel.py`, replace the `_on_single_filter_applied` method:

```python
    def _on_single_filter_applied(self, criteria: FilterCriteria) -> None:
        """Handle single filter applied from column row.

        Args:
            criteria: The FilterCriteria to apply.
        """
        # Check if filter for this column already exists, replace it
        self._active_filters = [
            f for f in self._active_filters if f.column != criteria.column
        ]
        self._active_filters.append(criteria)
        self._update_chips()
        self.single_filter_applied.emit(criteria)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/ui/components/test_filter_panel.py::test_single_filter_apply_creates_chip tests/ui/components/test_filter_panel.py::test_single_filter_chip_can_be_removed -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/ui/components/filter_panel.py tests/ui/components/test_filter_panel.py
git commit -m "feat: display filter chip when single row apply clicked"
```

---

## Task 3: Expand Filter Panel Height to Show 10 Rows

**Files:**
- Modify: `src/ui/components/filter_panel.py:102-103`
- Test: `tests/ui/components/test_filter_panel.py`

**Context:** The filter panel currently shows ~4 rows (200-300px height). Increase to show approximately 10 rows by adjusting height constraints.

**Frontend Design:** Each row is ~36px. For 10 rows: 360px + search bar (~40px) + header (~30px) = ~430px. Set minHeight=400, maxHeight=450 for comfortable viewing.

**Step 1: Write the failing test**

In `tests/ui/components/test_filter_panel.py`, add:

```python
def test_column_filter_panel_height_shows_10_rows(qtbot: QtBot) -> None:
    """Test that column filter panel height is sufficient for 10 rows."""
    panel = FilterPanel(columns=["col" + str(i) for i in range(15)])
    qtbot.addWidget(panel)

    # Minimum height should accommodate ~10 rows (400px)
    min_height = panel._column_filter_panel.minimumHeight()
    max_height = panel._column_filter_panel.maximumHeight()

    assert min_height >= 400, f"Min height {min_height} should be >= 400"
    assert max_height >= 450, f"Max height {max_height} should be >= 450"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/ui/components/test_filter_panel.py::test_column_filter_panel_height_shows_10_rows -v`
Expected: FAIL (current minHeight=200, maxHeight=300)

**Step 3: Update height constraints**

In `src/ui/components/filter_panel.py`, update lines 102-103:

```python
        self._column_filter_panel.setMinimumHeight(400)
        self._column_filter_panel.setMaximumHeight(450)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/ui/components/test_filter_panel.py::test_column_filter_panel_height_shows_10_rows -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/ui/components/filter_panel.py tests/ui/components/test_filter_panel.py
git commit -m "feat: expand filter panel height to show 10 rows"
```

---

## Final Verification

**Step 1: Run all related tests**

Run: `pytest tests/ui/components/test_column_filter_row.py tests/ui/components/test_filter_panel.py -v`
Expected: All tests PASS

**Step 2: Visual verification (manual)**

Launch the app and verify:
1. Apply button shows visible "+" icon with amber hover
2. Clicking per-row "+" adds amber chip showing filter values
3. Chip has trash icon to remove filter
4. Filter panel shows ~10 rows without scrolling

**Step 3: Final commit if any cleanup needed**

```bash
git status
# If clean, done. Otherwise:
git add -A && git commit -m "chore: cleanup filter panel improvements"
```
