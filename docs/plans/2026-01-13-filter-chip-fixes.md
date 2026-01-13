# Filter Chip Styling and Icon Fixes

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix FilterChip text readability and replace X icon with trash bin icon.

**Architecture:** The FilterChip component (`src/ui/components/filter_chip.py`) displays active filters with an amber background. Two fixes needed: (1) text color is too dark for amber background - keep using BG_BASE which is correct for dark-on-amber contrast, but the actual issue is different styling may be overriding it; (2) replace the ✕ character with a trash bin icon (🗑) for clearer delete affordance.

**Tech Stack:** PyQt6, Python

---

### Task 1: Add Test for Text Color Readability

**Files:**
- Modify: `tests/widget/test_filter_chip.py`

**Step 1: Write the failing test**

Add a test to verify the label text color is set to BG_BASE (dark) for contrast on amber:

```python
def test_chip_label_has_dark_text_color(self, qtbot: QtBot) -> None:
    """FilterChip label text is dark for readability on amber background."""
    criteria = FilterCriteria(
        column="gain_pct", operator="between", min_val=0, max_val=10
    )
    chip = FilterChip(criteria)
    qtbot.addWidget(chip)

    stylesheet = chip.styleSheet()
    # Text should be dark (BG_BASE) for contrast on amber
    assert f"color: {Colors.BG_BASE}" in stylesheet
```

**Step 2: Run test to verify it passes (baseline)**

Run: `pytest tests/widget/test_filter_chip.py::TestFilterChipStyle::test_chip_label_has_dark_text_color -v`
Expected: PASS (the code already sets BG_BASE)

**Step 3: Commit**

```bash
git add tests/widget/test_filter_chip.py
git commit -m "test: add test for filter chip text color readability"
```

---

### Task 2: Add Test for Trash Bin Icon

**Files:**
- Modify: `tests/widget/test_filter_chip.py`

**Step 1: Write the failing test**

```python
def test_remove_button_has_trash_icon(self, qtbot: QtBot) -> None:
    """FilterChip remove button displays trash bin icon."""
    criteria = FilterCriteria(
        column="gain_pct", operator="between", min_val=0, max_val=10
    )
    chip = FilterChip(criteria)
    qtbot.addWidget(chip)

    # Should have trash bin icon, not X
    assert chip._remove_btn.text() == "\U0001F5D1"  # 🗑
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/widget/test_filter_chip.py::TestFilterChipStyle::test_remove_button_has_trash_icon -v`
Expected: FAIL - currently uses "✕" not "🗑"

**Step 3: Commit test**

```bash
git add tests/widget/test_filter_chip.py
git commit -m "test: add failing test for trash bin icon on filter chip"
```

---

### Task 3: Replace X with Trash Bin Icon

**Files:**
- Modify: `src/ui/components/filter_chip.py:51`

**Step 1: Update the remove button icon**

Change line 51 from:
```python
self._remove_btn = QPushButton("\u2715")  # ✕
```

To:
```python
self._remove_btn = QPushButton("\U0001F5D1")  # 🗑
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/widget/test_filter_chip.py::TestFilterChipStyle::test_remove_button_has_trash_icon -v`
Expected: PASS

**Step 3: Run all filter chip tests**

Run: `pytest tests/widget/test_filter_chip.py -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add src/ui/components/filter_chip.py
git commit -m "fix: use trash bin icon for filter chip remove button"
```

---

### Task 4: Investigate and Fix Text Color Issue

**Context:** The stylesheet already sets `color: {Colors.BG_BASE}` for QLabel, but the image shows black text. This could be a Qt stylesheet specificity issue or the color might be getting overridden.

**Files:**
- Modify: `src/ui/components/filter_chip.py:56-78`

**Step 1: Inspect and fix the stylesheet**

The issue may be that QLabel is inheriting styles from a parent. Add explicit `!important`-style fix by setting the color directly on the label widget AND in stylesheet. Update `_apply_style` method:

```python
def _apply_style(self) -> None:
    """Apply Observatory theme styling."""
    self.setStyleSheet(f"""
        FilterChip {{
            background-color: {Colors.SIGNAL_AMBER};
            border-radius: 4px;
        }}
        FilterChip QLabel {{
            color: {Colors.BG_BASE};
            font-weight: bold;
            font-size: 11px;
            background: transparent;
        }}
        FilterChip QPushButton {{
            background: transparent;
            border: none;
            color: {Colors.BG_BASE};
            padding: 0;
            font-size: 12px;
        }}
        FilterChip QPushButton:hover {{
            color: {Colors.SIGNAL_CORAL};
        }}
    """)
```

Key changes:
1. Scoped `QLabel` and `QPushButton` selectors to `FilterChip` for specificity
2. Added `background: transparent` to QLabel to prevent any background override
3. Increased font-size for trash icon to 12px for better visibility

**Step 2: Run all tests**

Run: `pytest tests/widget/test_filter_chip.py -v`
Expected: All PASS

**Step 3: Manual verification**

Run the application and verify:
1. Filter chip text is readable (dark on amber)
2. Trash bin icon is visible on the right

**Step 4: Commit**

```bash
git add src/ui/components/filter_chip.py
git commit -m "fix: improve filter chip stylesheet specificity for text color"
```

---

### Task 5: Final Verification

**Step 1: Run full test suite**

Run: `pytest tests/widget/test_filter_chip.py tests/widget/test_filter_panel.py -v`
Expected: All PASS

**Step 2: Visual verification**

Launch the app, apply a filter, and verify:
- [ ] Text is clearly readable (dark text on amber background)
- [ ] Trash bin icon (🗑) appears on the right side of the chip
- [ ] Hover state on trash icon changes color to coral

**Step 3: Final commit (if any cleanup needed)**

```bash
git add -A
git commit -m "fix: filter chip text readability and trash icon"
```
