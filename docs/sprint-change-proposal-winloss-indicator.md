# Sprint Change Proposal: Win/Loss Column Status Indicator Fix

**Date:** 2026-01-12
**Triggered By:** User report - status indicator shows ✗ for valid manual selection
**Severity:** Low (UX bug, functionality unaffected)
**Recommended Path:** Direct Adjustment
**Status:** Implemented

---

## 1. Identified Issue Summary

**Problem:** When a user manually selects a column for Win/Loss mapping, the status 
indicator continues to show "✗" (missing) even though the selection contains valid 
binary (1/0) values. The indicator only reflects the auto-detection result based on 
column names, not the user's actual selection.

**Root Cause:** `_on_selection_changed()` in `ColumnConfigPanel` does not update 
status indicators - they are only set once during `_update_status_indicators()` 
based on auto-detection results.

**User Impact:** Confusing UX - users see "invalid" indicator for valid selections.

---

## 2. Epic Impact Summary

| Epic | Impact |
|------|--------|
| Epic 1: Foundation & Data Pipeline | Minor - Story 1.4 defect fix |
| Epic 2-4 | None |

No epic restructuring required. This is a localized bug fix.

---

## 3. Artifact Adjustment Needs

| Artifact | Change Required |
|----------|-----------------|
| `src/tabs/data_input.py` | Code fix (primary) |
| `docs/stories/1.4.story.md` | Add clarifying note (optional) |
| PRD / Architecture / FE Spec | No changes needed |

---

## 4. Recommended Path Forward

**Direct Adjustment** - Fix the status indicator to update on user selection.

**Rationale:**
- Aligns with existing UX principle: "Immediate feedback"
- Minimal scope and risk
- No architectural changes
- Preserves all existing work

---

## 5. PRD MVP Impact

None. This is a bug fix within existing MVP scope.

---

## 6. Specific Proposed Edits

### Edit 1: Update `_on_selection_changed()` method

**File:** `src/tabs/data_input.py`
**Location:** Lines 414-422

**Current:**
```python
def _on_selection_changed(self, _text: str) -> None:
    """Handle combo box selection change."""
    # Find which combo changed
    sender = self.sender()
    for field_name, combo in self._combos.items():
        if combo is sender:
            self._update_preview(field_name)
            break
    self._validate()
```

**Proposed:**
```python
def _on_selection_changed(self, _text: str) -> None:
    """Handle combo box selection change."""
    # Find which combo changed
    sender = self.sender()
    for field_name, combo in self._combos.items():
        if combo is sender:
            self._update_preview(field_name)
            self._update_single_status_indicator(field_name)
            break
    self._validate()
```

### Edit 2: Add new method `_update_single_status_indicator()`

**File:** `src/tabs/data_input.py`
**Location:** After `_update_status_indicators()` method (after line 386)

**Proposed new method:**
```python
def _update_single_status_indicator(self, field_name: str) -> None:
    """Update status indicator for a single field based on current selection.
    
    Args:
        field_name: The field name (e.g., 'ticker', 'win_loss')
    """
    if field_name not in self._status_labels:
        return
    
    label = self._status_labels[field_name]
    combo = self._combos.get(field_name)
    
    if combo and combo.currentText():
        # User has selected a column - show as valid
        label.setText("✓")
        label.setStyleSheet(f"color: {Colors.SIGNAL_CYAN}; font-size: 14px;")
    else:
        # No selection - show as missing
        label.setText("✗")
        label.setStyleSheet(f"color: {Colors.SIGNAL_CORAL}; font-size: 14px;")
```

### Edit 3: Update tests

**File:** `tests/widget/test_column_config_panel.py`

**Add test case:**
```python
def test_status_indicator_updates_on_manual_selection(qtbot: QtBot):
    """Status indicator updates to checkmark when user manually selects a column."""
    panel = ColumnConfigPanel()
    qtbot.addWidget(panel)
    
    # Set columns
    panel.set_columns(["col_a", "col_b", "my_wl_column"])
    
    # Initially win_loss should show X (not auto-detected)
    wl_label = panel._status_labels.get("win_loss")
    assert wl_label.text() == "✗"
    
    # Manually select a column
    panel._combos["win_loss"].setCurrentText("my_wl_column")
    
    # Status should now show checkmark
    assert wl_label.text() == "✓"
```

---

## 7. High-Level Action Plan

| Step | Action | Owner |
|------|--------|-------|
| 1 | Implement code changes (Edits 1-2) | Dev |
| 2 | Add/update test case (Edit 3) | Dev |
| 3 | Run `make test` to verify | Dev |
| 4 | Run `make lint && make typecheck` | Dev |
| 5 | Update Story 1.4 with clarifying note (optional) | PO |

---

## 8. Agent Handoff Plan

| Role | Responsibility |
|------|----------------|
| **PO** | Approved this proposal |
| **Dev** | Implement the fix |
| **QA** | Verify fix works as expected |

No PM or Architect involvement needed - this is a contained bug fix.

---

## 9. Success Criteria

- [x] Status indicator shows ✓ when user manually selects any column
- [x] Status indicator shows ✗ only when dropdown is empty
- [x] Auto-detection still works and shows appropriate initial states
- [x] All existing tests pass (957 tests)
- [x] New test validates the fix

---

## 10. Implementation Record

**Implemented By:** James (Dev Agent)
**Date:** 2026-01-12

### Files Modified

| File | Change |
|------|--------|
| `src/tabs/data_input.py` | Added `_update_single_status_indicator()` method, updated `_on_selection_changed()` |
| `tests/widget/test_column_config_panel.py` | Added `test_status_indicator_updates_on_manual_selection` test |

### Verification

- [x] All 957 tests pass
- [x] Lint (ruff) passes
- [x] New test validates fix behavior

---

## 11. Approval Record

| Date | Approver | Decision |
|------|----------|----------|
| 2026-01-12 | User | Approved |

---

## 12. Change Log

| Date | Version | Description |
|------|---------|-------------|
| 2026-01-12 | 1.0 | Initial proposal created and approved |
| 2026-01-12 | 1.1 | Implemented - all edits applied, tests passing |
