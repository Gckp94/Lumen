# Comparison Ribbon Sizing Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the compressed metrics display in the PnL Trading Stats tab by removing fixed height constraints that prevent the 48px hero font from displaying properly.

**Architecture:** Remove `setFixedHeight()` calls from `_RibbonCard` and `ComparisonRibbon` classes, replacing them with `setMinimumHeight()` to ensure adequate space while allowing the layout to expand naturally. The tab is already scrollable, so compression is unnecessary.

**Tech Stack:** PyQt6, Python

---

### Task 1: Update _RibbonCard to use minimum height instead of fixed height

**Files:**
- Modify: `src/ui/components/comparison_ribbon.py:122-124`

**Step 1: Write the failing test**

```python
# In tests/widget/test_comparison_ribbon.py, add to TestComparisonRibbonDisplay class:
def test_ribbon_card_has_minimum_height(self, qtbot: QtBot):
    """Test that ribbon card allows natural height expansion."""
    from src.ui.components.comparison_ribbon import _RibbonCard
    
    card = _RibbonCard("trades")
    qtbot.addWidget(card)
    
    # Card should have minimum height, not fixed height
    # minimumHeight should be set, but maximumHeight should not constrain
    assert card.minimumHeight() >= 120
    assert card.maximumHeight() >= 16777215  # Qt's QWIDGETSIZE_MAX default
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/widget/test_comparison_ribbon.py::TestComparisonRibbonDisplay::test_ribbon_card_has_minimum_height -v`
Expected: FAIL with assertion error (current fixed height is 100)

**Step 3: Update _RibbonCard._setup_ui to use minimum height**

In `src/ui/components/comparison_ribbon.py`, change `_RibbonCard._setup_ui` (lines 121-148):

Replace:
```python
    def _setup_ui(self) -> None:
        """Set up the widget UI layout."""
        self.setFixedWidth(200)
        self.setFixedHeight(100)
```

With:
```python
    def _setup_ui(self) -> None:
        """Set up the widget UI layout."""
        self.setFixedWidth(200)
        self.setMinimumHeight(120)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/widget/test_comparison_ribbon.py::TestComparisonRibbonDisplay::test_ribbon_card_has_minimum_height -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/widget/test_comparison_ribbon.py src/ui/components/comparison_ribbon.py
git commit -m "fix: use minimum height for ribbon card to prevent text clipping"
```

---

### Task 2: Update ComparisonRibbon to use minimum height instead of fixed height

**Files:**
- Modify: `src/ui/components/comparison_ribbon.py:273`

**Step 1: Write the failing test**

```python
# In tests/widget/test_comparison_ribbon.py, add to TestComparisonRibbonDisplay class:
def test_comparison_ribbon_has_minimum_height(self, qtbot: QtBot):
    """Test that comparison ribbon allows natural height expansion."""
    from src.ui.components.comparison_ribbon import ComparisonRibbon
    
    ribbon = ComparisonRibbon()
    qtbot.addWidget(ribbon)
    
    # Ribbon should have minimum height, not fixed height
    assert ribbon.minimumHeight() >= 140
    assert ribbon.maximumHeight() >= 16777215  # Qt's QWIDGETSIZE_MAX default
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/widget/test_comparison_ribbon.py::TestComparisonRibbonDisplay::test_comparison_ribbon_has_minimum_height -v`
Expected: FAIL with assertion error (current fixed height is 120)

**Step 3: Update ComparisonRibbon._setup_ui to use minimum height**

In `src/ui/components/comparison_ribbon.py`, change `ComparisonRibbon._setup_ui` (line 273):

Replace:
```python
        self.setFixedHeight(120)
```

With:
```python
        self.setMinimumHeight(140)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/widget/test_comparison_ribbon.py::TestComparisonRibbonDisplay::test_comparison_ribbon_has_minimum_height -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/widget/test_comparison_ribbon.py src/ui/components/comparison_ribbon.py
git commit -m "fix: use minimum height for comparison ribbon container"
```

---

### Task 3: Run all comparison ribbon tests to ensure no regressions

**Files:**
- Test: `tests/widget/test_comparison_ribbon.py`

**Step 1: Run full test suite for comparison ribbon**

Run: `pytest tests/widget/test_comparison_ribbon.py -v`
Expected: All tests PASS

**Step 2: Run integration tests that use comparison ribbon**

Run: `pytest tests/integration/test_filter_workflow.py::TestComparisonRibbonIntegration -v`
Expected: All tests PASS

**Step 3: Commit (if any additional fixes were needed)**

If tests revealed issues, fix them and commit. Otherwise, skip this step.

---

### Task 4: Manual visual verification

**Step 1: Run the application**

Run: `python -m src.main` (or the appropriate entry point)

**Step 2: Verify the fix**

1. Navigate to the PnL Trading Stats tab
2. Verify that the Comparison section metrics (Trades, Win Rate, EV, Kelly) display without clipping
3. Verify that the large numbers are fully visible
4. Verify that the delta indicators and baseline values are visible below the main numbers
5. Scroll the page to confirm scrolling still works correctly

**Step 3: Document verification**

Confirm visually that:
- [ ] Numbers like "231", "69.7%", "7.61%", "26.2%" display completely
- [ ] Delta indicators (▲/▼ with values) are visible
- [ ] Baseline values are visible
- [ ] No text overlap or clipping occurs
