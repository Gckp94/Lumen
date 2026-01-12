# Sprint Change Proposal: Efficiency & Stop Loss Adjustment Logic

**Date:** 2026-01-11
**Triggered By:** Missing requirement discovery during Epic/Story review
**Status:** APPROVED
**Approved:** 2026-01-11

---

## 1. Analysis Summary

### Issue Statement

The efficiency and stop loss calculation logic is not documented in any PRD, architecture, or story files. This is critical trade-level adjustment logic that affects all 25 metrics.

### Requirements Discovered

**Efficiency Adjustment:**
- Default: 5% (user-configurable)
- Always subtracted from gain (simulates transaction costs/slippage)
- Applied at trade level

**Stop Loss Adjustment:**
- Based on user input (stop_loss %)
- Uses `mae_pct` column (Maximum Adverse Excursion) from source data
- If `mae_pct > stop_loss`, the stop is considered "hit"
- When hit, gain is overridden to `-stop_loss`

**Calculation Order:**
```
Step 1: stop_adjusted_gain_pct = -stop_loss if mae_pct > stop_loss else gain_pct
Step 2: efficiency_adjusted_gain_pct = stop_adjusted_gain_pct - efficiency
```

**Data Format:**
- All percentage columns stored as whole numbers (e.g., 20 = 20%, not 0.20)

### Impact Assessment

| Epic | Impact Level | Details |
|------|--------------|---------|
| Epic 1 | High | Stories 1.4, 1.6 need retrofit |
| Epic 2 | Low | No changes needed |
| Epic 3 | Medium | Story 3.1 needs Efficiency input |
| Epic 4 | Low | Inherits from Epic 3 |

### Recommended Path

**Direct Integration** - Retrofit completed stories and update documentation. Estimated effort: 4-7 hours total.

---

## 2. Proposed Edits

### 2.1 PRD Requirements (docs/prd/2-requirements.md)

**ADD after FR4:**

```markdown
**FR4a:** The system shall require a `mae_pct` (Maximum Adverse Excursion %) column for stop loss calculations, with auto-detection support.
```

**CHANGE FR15 from:**
```markdown
**FR15:** The system shall accept user inputs for: Stop Loss %, Flat Stake $, Compounded Start Capital $, and Fractional Kelly %.
```

**TO:**
```markdown
**FR15:** The system shall accept user inputs for: Stop Loss %, Efficiency % (default 5%), Flat Stake $, Compounded Start Capital $, and Fractional Kelly %.
```

**ADD after FR15:**

```markdown
**FR15a:** The system shall calculate `stop_adjusted_gain_pct` where: if `mae_pct > stop_loss`, then `stop_adjusted_gain_pct = -stop_loss`, otherwise `stop_adjusted_gain_pct = gain_pct`.

**FR15b:** The system shall calculate `efficiency_adjusted_gain_pct = stop_adjusted_gain_pct - efficiency` for all trades.

**FR15c:** All 25 trading metrics shall use `efficiency_adjusted_gain_pct` as the basis for calculations.
```

---

### 2.2 Brief Appendix D (docs/brief.md)

**ADD to User Inputs table (after line 549):**

| Input | Default | Used By |
|-------|---------|---------|
| Efficiency % | 5% | All metrics (applied to every trade) |

**ADD new section before "Core Statistics" (after line 551):**

```markdown
#### Trade-Level Adjustments

Before any metric calculation, each trade's gain is adjusted:

**Step 1: Stop Loss Adjustment**
```
IF mae_pct > stop_loss:
    stop_adjusted_gain_pct = -stop_loss
ELSE:
    stop_adjusted_gain_pct = gain_pct
```

**Step 2: Efficiency Adjustment**
```
efficiency_adjusted_gain_pct = stop_adjusted_gain_pct - efficiency
```

**Example (stop_loss = 8, efficiency = 5):**

| gain_pct | mae_pct | Stop Hit? | stop_adjusted | efficiency_adjusted |
|----------|---------|-----------|---------------|---------------------|
| 20 | 3 | No | 20 | 15 |
| 10 | 10 | Yes | -8 | -13 |
| -2 | 5 | No | -2 | -7 |
| 5 | 12 | Yes | -8 | -13 |

**Note:** All percentage values are stored as whole numbers (20 = 20%).

---
```

**ADD to Data Requirements section (after line 538):**

```markdown
- **mae_pct column:** Required column containing Maximum Adverse Excursion percentage for each trade
```

---

### 2.3 Architecture Data Models (docs/architecture/4-data-models.md)

**CHANGE ColumnMapping class to add mae_pct:**

```python
@dataclass
class ColumnMapping:
    """Mapping of required columns to DataFrame column names."""

    ticker: str
    date: str
    time: str
    gain_pct: str
    mae_pct: str  # ADD THIS LINE - Required for stop loss calculation
    win_loss: str | None = None
    win_loss_derived: bool = False
    breakeven_is_win: bool = False

    def validate(self, df_columns: list[str]) -> list[str]:
        """Validate mapping against DataFrame columns. Returns list of errors."""
        errors = []
        required = [self.ticker, self.date, self.time, self.gain_pct, self.mae_pct]  # ADD mae_pct
        for col in required:
            if col not in df_columns:
                errors.append(f"Column '{col}' not found in data")
        if self.win_loss and self.win_loss not in df_columns:
            errors.append(f"Win/Loss column '{self.win_loss}' not found")
        return errors
```

**ADD new dataclass after ColumnMapping:**

```python
@dataclass
class AdjustmentParams:
    """User-configurable parameters for trade adjustment calculations."""

    stop_loss: float = 8.0      # Stop loss percentage (e.g., 8 = 8%)
    efficiency: float = 5.0      # Efficiency/slippage percentage (e.g., 5 = 5%)

    def calculate_adjusted_gain(self, gain_pct: float, mae_pct: float) -> float:
        """Calculate efficiency-adjusted gain for a single trade.

        Args:
            gain_pct: Original gain percentage (whole number, e.g., 20 = 20%)
            mae_pct: Maximum adverse excursion percentage

        Returns:
            Efficiency-adjusted gain percentage
        """
        # Step 1: Stop loss adjustment
        if mae_pct > self.stop_loss:
            stop_adjusted = -self.stop_loss
        else:
            stop_adjusted = gain_pct

        # Step 2: Efficiency adjustment
        return stop_adjusted - self.efficiency
```

**ADD to AppState class:**

```python
class AppState(QObject):
    # ... existing signals ...
    adjustment_params_changed = Signal(object)  # AdjustmentParams

    def __init__(self) -> None:
        # ... existing init ...
        self.adjustment_params: AdjustmentParams = AdjustmentParams()
```

---

### 2.4 PRD Epic 1 (docs/prd/6-epic-1-foundation-data-pipeline.md)

**CHANGE Story 1.4 Acceptance Criteria 1 from:**
```markdown
1. Auto-detection for required columns (Ticker, Date, Time, Gain %) with case-insensitive pattern matching
```

**TO:**
```markdown
1. Auto-detection for required columns (Ticker, Date, Time, Gain %, MAE %) with case-insensitive pattern matching
```

**ADD to Story 1.6 Acceptance Criteria (after existing AC 7):**

```markdown
8. User inputs panel with Stop Loss % (default 8%) and Efficiency % (default 5%)
9. Calculate stop_adjusted_gain_pct: if mae_pct > stop_loss then -stop_loss, else gain_pct
10. Calculate efficiency_adjusted_gain_pct = stop_adjusted_gain_pct - efficiency
11. All metrics calculated using efficiency_adjusted_gain_pct
12. User input changes trigger metric recalculation
```

---

### 2.5 PRD Epic 3 (docs/prd/8-epic-3-metrics-engine.md)

**CHANGE Story 3.1 Acceptance Criteria 2 from:**
```markdown
2. User inputs: Flat Stake ($), Starting Capital ($), Fractional Kelly (%), Stop Loss (%)
```

**TO:**
```markdown
2. User inputs: Flat Stake ($), Starting Capital ($), Fractional Kelly (%), Stop Loss (%), Efficiency (%)
3. Stop Loss and Efficiency inputs sync with Data Input tab values (shared state)
```

**ADD note to Story 3.1:**
```markdown
**Note:** Stop Loss and Efficiency are already available from Epic 1 Story 1.6. This story exposes them in the PnL Stats tab for convenience, with bidirectional sync via AppState.
```

---

### 2.6 Story 1.4 File (docs/stories/1.4.story.md)

**ADD to Acceptance Criteria (after AC 2):**
```markdown
2a. Auto-detection for required MAE % column (mae_pct)
```

**ADD to Task 1 subtasks:**
```markdown
- [x] Required fields: `ticker`, `date`, `time`, `gain_pct`, `mae_pct` (all `str`)
```

**ADD to Task 2 PATTERNS dict:**
```markdown
- `mae_pct`: ["mae", "max_adverse", "adverse", "drawdown", "mae_pct"]
```

**UPDATE ColumnMapping in Dev Notes to include mae_pct field.**

---

### 2.7 Story 1.6 File (docs/stories/1.6.story.md)

**ADD new Acceptance Criteria:**
```markdown
8. User inputs panel displays Stop Loss % (default 8%) and Efficiency % (default 5%)
9. Trade adjustments calculated: stop_adjusted_gain_pct and efficiency_adjusted_gain_pct
10. All 7 metrics use efficiency_adjusted_gain_pct as input
11. Metrics recalculate when user inputs change
```

**ADD new Tasks:**

```markdown
- [ ] Task 12: Create AdjustmentParams Dataclass
  - [ ] Add `AdjustmentParams` to `src/core/models.py`
  - [ ] Fields: `stop_loss: float = 8.0`, `efficiency: float = 5.0`
  - [ ] Method: `calculate_adjusted_gain(gain_pct, mae_pct) -> float`
  - [ ] Add unit tests

- [ ] Task 13: Create User Inputs Panel for Data Input Tab
  - [ ] Create `AdjustmentInputsPanel` widget
  - [ ] Stop Loss % input with spinner (0-100, default 8)
  - [ ] Efficiency % input with spinner (0-100, default 5)
  - [ ] Style consistent with existing panels
  - [ ] Emit signal on value change

- [ ] Task 14: Integrate Adjustments into Metrics Calculation
  - [ ] Update `MetricsCalculator.calculate()` to accept `AdjustmentParams`
  - [ ] Calculate adjusted gains before metric computation
  - [ ] Store adjusted DataFrame in AppState
  - [ ] Update tests for adjusted calculations

- [ ] Task 15: Wire User Input Changes to Recalculation
  - [ ] Connect input panel signals to recalculation
  - [ ] Debounce rapid changes (300ms)
  - [ ] Update metrics display after recalculation
```

---

## 3. Implementation Checklist

### Phase 1: Documentation (Do First) ✅ COMPLETE
- [x] Update docs/prd/2-requirements.md
- [x] Update docs/brief.md (Appendix D)
- [x] Update docs/architecture/4-data-models.md
- [x] Update docs/prd/6-epic-1-foundation-data-pipeline.md
- [x] Update docs/prd/8-epic-3-metrics-engine.md

### Phase 2: Story 1.4 Retrofit ✅ COMPLETE
- [x] Update docs/stories/1.4.story.md
- [x] Add mae_pct to ColumnMapping in src/core/models.py
- [x] Add mae_pct patterns to src/core/column_mapper.py
- [x] Update validation logic
- [x] Update unit tests
- [x] Update widget tests
- [x] Verify column detection works

### Phase 3: Story 1.6 Retrofit ✅ COMPLETE
- [x] Update docs/stories/1.6.story.md
- [x] Create AdjustmentParams dataclass
- [x] Create AdjustmentInputsPanel widget
- [x] Update MetricsCalculator to use adjusted gains
- [x] Wire user inputs to recalculation
- [x] Update unit tests
- [x] Update widget tests
- [x] Verify end-to-end flow

### Phase 4: Verification ✅ COMPLETE
- [x] Run full test suite (424 tests passing)
- [x] Lint and typecheck passing
- [x] Verify metrics match expected adjusted values

---

## 4. Agent Handoff Plan

| Role | Responsibility |
|------|----------------|
| **PM (Current)** | Approve this proposal, update PRD docs |
| **Architect** | Update architecture docs (data models) |
| **Dev** | Implement code changes for Stories 1.4, 1.6 |
| **QA** | Update test cases, verify implementation |

---

## 5. Approval

**APPROVED** - 2026-01-11

- [x] User approves change proposal
- [x] Documentation updates completed (2026-01-11)
- [x] Code changes implemented (2026-01-11)
- [x] Tests updated and passing (424 tests, lint, typecheck all pass)
- [x] QA verification complete (2026-01-11)

### QA Verification Summary

| Story | Gate | Reviewer | Tests |
|-------|------|----------|-------|
| 1.4 - Column Configuration Panel | **PASS** | Quinn | 57 tests |
| 1.6 - Core Metrics Calculation | **PASS** | Quinn | 59 tests |

Gate files updated:
- `docs/qa/gates/1.4-column-configuration-panel.yml`
- `docs/qa/gates/1.6-core-metrics-calculation-display.yml`

---

*Generated by PM Agent (John) - Correct Course Task*
