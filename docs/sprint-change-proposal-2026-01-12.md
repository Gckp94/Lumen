# Sprint Change Proposal

**Date:** 2026-01-12
**Prepared By:** Sarah (Product Owner)
**Interaction Mode:** Incremental
**Status:** APPROVED

---

## 1. Analysis Summary

### Original Issues

| # | Issue | Severity | Category |
|---|-------|----------|----------|
| 1 | Column Mappings combo box text hard to read/compressed | P2 | UI Polish |
| 2 | Average Winner showing -13.80 (negative value) in baseline | P1 | Logic Bug |

### Root Cause Analysis

**Issue 1:** The QComboBox styling in `ColumnConfigPanel` lacks explicit height constraints and proper drop-down arrow styling, causing the selected text to appear compressed.

**Issue 2:** When an explicit Win/Loss column exists in the data, the metrics calculator classifies wins/losses based on that column, but uses **adjusted gains** for the values. When stop-loss adjustments turn a "Win" into a negative gain, the "Avg Winner" displays a negative value, which is counterintuitive and misleading.

### Impact Assessment

| Area | Impact |
|------|--------|
| **Epic 1** | Minor - Stories 1.4 (UI) and 1.6 (metrics) need refinement |
| **Epic 2-4** | None - downstream consumers unaffected |
| **MVP Scope** | Unchanged |
| **PRD** | Clarification needed for FR5 |
| **Architecture** | Comment clarification for data models |

### Recommended Path Forward

**Option 1: Direct Adjustment** - Both issues can be fixed with isolated code changes without rollback or re-scoping.

---

## 2. Specific Proposed Edits

### Edit 1: Fix Combo Box Styling

**File:** `src/tabs/data_input.py`
**Location:** Lines 251-276 (`_add_field_row` method)

**FROM:**
```python
        combo.setStyleSheet(
            f"""
            QComboBox {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
                min-width: 150px;
            }}
            QComboBox:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                selection-background-color: {Colors.BG_BORDER};
            }}
        """
        )
```

**TO:**
```python
        combo.setStyleSheet(
            f"""
            QComboBox {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 8px 32px 8px 12px;
                font-size: 13px;
                min-width: 150px;
                min-height: 20px;
            }}
            QComboBox:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 24px;
                border: none;
            }}
            QComboBox::down-arrow {{
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {Colors.TEXT_SECONDARY};
            }}
            QComboBox::down-arrow:hover {{
                border-top-color: {Colors.TEXT_PRIMARY};
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                selection-background-color: {Colors.BG_BORDER};
                padding: 4px;
            }}
        """
        )
```

**Changes:**
- Added `min-height: 20px` to prevent compression
- Changed padding to `8px 32px 8px 12px` (right padding for arrow)
- Added proper `::drop-down` positioning
- Added CSS triangle `::down-arrow` indicator
- Added hover state for arrow
- Added padding to dropdown list items

---

### Edit 2: Fix Win/Loss Classification Logic

**File:** `src/core/metrics.py`
**Location:** Lines 110-122 (`calculate` method)

**FROM:**
```python
        # Classify wins/losses
        if win_loss_col and not derived:
            # Use explicit column
            winners_mask = df[win_loss_col].isin(["W", "Win", "WIN", 1, True])
            losers_mask = ~winners_mask
        else:
            # Derive from gain percentage
            if breakeven_is_win:
                winners_mask = gains >= 0
                losers_mask = gains < 0
            else:
                winners_mask = gains > 0
                losers_mask = gains <= 0
```

**TO:**
```python
        # Classify wins/losses based on adjusted gain sign
        # Note: Always use adjusted gains for classification per FR15c
        # This ensures avg_winner is always positive and avg_loser is always negative
        if breakeven_is_win:
            winners_mask = gains >= 0
            losers_mask = gains < 0
        else:
            winners_mask = gains > 0
            losers_mask = gains <= 0
```

**Changes:**
- Removed conditional branch that used explicit Win/Loss column for classification
- Win/loss classification now always based on adjusted gain sign
- Added clarifying comments explaining the rationale

---

### Edit 3: PRD Clarification (Documentation)

**File:** `docs/prd/2-requirements.md`
**Location:** FR5 (Line 15)

**FROM:**
```markdown
**FR5:** The system shall support an optional Win/Loss column with fallback to deriving win/loss from Gain % values.
```

**TO:**
```markdown
**FR5:** The system shall support an optional Win/Loss column for data reference. For metric calculations, win/loss classification shall always be determined by the sign of the efficiency_adjusted_gain (positive = win, zero or negative = loss per breakeven setting), ensuring Avg Winner is always positive and Avg Loser is always negative.
```

---

### Edit 4: Architecture Clarification (Documentation)

**File:** `docs/architecture/4-data-models.md`
**Location:** TradingMetrics section (around line 133-134)

**FROM:**
```python
    avg_winner: float | None        # Percentage
    avg_loser: float | None         # Percentage (negative)
```

**TO:**
```python
    avg_winner: float | None        # Percentage (always positive - classified by adjusted gain > 0)
    avg_loser: float | None         # Percentage (always negative - classified by adjusted gain <= 0)
```

---

### Edit 5: Add Unit Test for Classification

**File:** `tests/unit/test_metrics.py`
**Action:** Add new test case

**ADD:**
```python
def test_winner_classification_uses_adjusted_gains() -> None:
    """Winners should be classified by adjusted gain sign, not raw Win/Loss column.

    This ensures avg_winner is always positive even when stop-loss adjustments
    turn originally winning trades into losses.
    """
    # Trade that was a "Win" but MAE exceeded stop loss
    # Original: gain=+10%, mae=10%, stop_loss=8%, efficiency=5%
    # Adjusted: -8% - 5% = -13% (should be classified as LOSS)
    df = pd.DataFrame({
        "gain_pct": [10.0, 5.0, -3.0],
        "mae_pct": [10.0, 2.0, 2.0],  # First trade exceeds 8% stop
        "win_loss": ["W", "W", "L"],
    })

    params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
    calc = MetricsCalculator()
    metrics, _, _ = calc.calculate(
        df,
        gain_col="gain_pct",
        win_loss_col="win_loss",
        derived=False,  # Would have used explicit column before fix
        adjustment_params=params,
        mae_col="mae_pct",
    )

    # After adjustment: [-13.0, 0.0, -8.0]
    # Winners (>0): none
    # Losers (<=0): all 3
    assert metrics.winner_count == 0
    assert metrics.loser_count == 3
    assert metrics.avg_winner is None  # No winners
    assert metrics.avg_loser is not None
    assert metrics.avg_loser < 0  # Always negative
```

---

## 3. High-Level Action Plan

| # | Task | Owner | Priority |
|---|------|-------|----------|
| 1 | Implement combo box styling fix | Dev | P2 |
| 2 | Implement metrics classification fix | Dev | P1 |
| 3 | Update PRD FR5 clarification | PO | P2 |
| 4 | Update architecture doc comments | PO | P2 |
| 5 | Add unit test for classification | Dev | P1 |
| 6 | Run full test suite, fix any failures | Dev | P1 |
| 7 | Manual verification of both fixes | QA | P1 |

---

## 4. Agent Handoff Plan

| Role | Responsibility |
|------|----------------|
| **PO (Sarah)** | Update PRD and architecture docs after approval |
| **Dev Agent** | Implement code fixes (Edits 1, 2, 5) |
| **QA Agent** | Verify fixes, run regression tests |

---

## 5. Validation Criteria

| Validation | Criteria |
|------------|----------|
| **Issue 1 Fixed** | Combo box displays full text, has visible arrow, not compressed |
| **Issue 2 Fixed** | Avg Winner always shows positive value (or None if no winners) |
| **Tests Pass** | `make test` passes including new classification test |
| **No Regressions** | Existing metrics calculations unchanged for normal cases |

---

## 6. Approval

- **Approved By:** User
- **Approval Date:** 2026-01-12
- **Status:** Ready for Implementation

---
