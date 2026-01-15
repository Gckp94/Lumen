# Expected Growth Position Sizing Metrics

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add three separate Expected Growth metrics based on different position sizing strategies: Full Kelly, Fractional Kelly, and Flat Stake.

**Architecture:** The expected growth formula `EG = f × μ - f² × σ² / 2` can use any bet fraction `f`. Currently it uses full Kelly. We'll add two additional metrics using fractional Kelly and flat stake fractions, allowing traders to see expected growth for their actual position sizing strategy.

**Tech Stack:** Python, PyQt6

---

## Design Summary

### New Metrics

| Metric | Display Name | Bet Fraction (f) |
|--------|--------------|------------------|
| `eg_full_kelly` | EG Full Kelly | `kelly / 100` |
| `eg_frac_kelly` | EG Frac Kelly | `fractional_kelly / 100` |
| `eg_flat_stake` | EG Flat Stake | `flat_stake / start_capital` |

### Default Value Changes

| Setting | Old Default | New Default |
|---------|-------------|-------------|
| `start_capital` | 10,000 | 100,000 |
| `flat_stake` | 1,000 | 10,000 |

### Display

- All three metrics always show (using defaults)
- Format: `.2f` with "pp" suffix (percentage points)
- Grouped in Position Sizing section of metrics grid
- Included in comparison grid with "higher is better" coloring
- Metrics recalculate when user changes flat_stake or start_capital inputs

### Migration

- Remove: `expected_growth` field from `TradingMetrics`
- Add: `eg_full_kelly`, `eg_frac_kelly`, `eg_flat_stake` fields
- Update all 21 files referencing `expected_growth`

---

## Files to Modify

| File | Change |
|------|--------|
| `src/core/models.py` | Replace `expected_growth` with three new fields in `TradingMetrics` |
| `src/core/metrics.py` | Calculate all three EG values; update parameter defaults |
| `src/ui/components/user_inputs_panel.py` | Update defaults: 100k capital, 10k flat stake |
| `src/ui/components/metrics_grid.py` | Display three EG metrics |
| `src/ui/components/comparison_grid.py` | Add three EG metrics to comparison |
| `src/core/export_manager.py` | Update any export references |
| `tests/unit/test_metrics.py` | Update/add tests for new metrics |
| `tests/unit/test_models.py` | Update model tests |
| `tests/conftest.py` | Update fixtures |
| `tests/widget/test_metrics_grid.py` | Update widget tests |
| `tests/widget/test_comparison_grid.py` | Update widget tests |

---

## Calculation Details

All three metrics use the same formula with different `f`:

```python
def calculate_expected_growth(f: float, ev: float, variance: float) -> float | None:
    """Calculate expected growth rate for a given bet fraction.

    Args:
        f: Bet fraction (decimal, e.g., 0.10 for 10%)
        ev: Expected value (percentage points)
        variance: Variance of returns (decimal)

    Returns:
        Expected growth in percentage points, or None if invalid
    """
    if f <= 0:
        return None
    return (f * ev) - ((f ** 2) * variance / 2)
```

Guard conditions:
- `eg_full_kelly`: Returns None when `kelly <= 0`
- `eg_frac_kelly`: Returns None when `fractional_kelly <= 0` (i.e., when kelly <= 0)
- `eg_flat_stake`: Returns None when `flat_stake <= 0` or `start_capital <= 0`

---

## Implementation Tasks

### Task 1: Update TradingMetrics Model

**Files:**
- Modify: `src/core/models.py`
- Test: `tests/unit/test_models.py`

**Step 1: Write failing test**

Add to `tests/unit/test_models.py`:

```python
def test_trading_metrics_has_eg_fields() -> None:
    """TradingMetrics has three expected growth fields."""
    metrics = TradingMetrics(
        num_trades=100,
        eg_full_kelly=0.15,
        eg_frac_kelly=0.04,
        eg_flat_stake=0.10,
    )
    assert metrics.eg_full_kelly == 0.15
    assert metrics.eg_frac_kelly == 0.04
    assert metrics.eg_flat_stake == 0.10
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_models.py::test_trading_metrics_has_eg_fields -v`

Expected: FAIL - fields don't exist

**Step 3: Update TradingMetrics dataclass**

In `src/core/models.py`, find `TradingMetrics` class and:
- Remove: `expected_growth: float | None = None`
- Add: `eg_full_kelly: float | None = None`
- Add: `eg_frac_kelly: float | None = None`
- Add: `eg_flat_stake: float | None = None`

**Step 4: Update empty() factory method**

In the `empty()` class method, replace `expected_growth=None` with the three new fields set to `None`.

**Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_models.py::test_trading_metrics_has_eg_fields -v`

Expected: PASS

**Step 6: Fix any other model tests**

Run: `pytest tests/unit/test_models.py -v`

Fix any tests that reference `expected_growth`.

**Step 7: Commit**

```bash
git add src/core/models.py tests/unit/test_models.py
git commit -m "refactor: replace expected_growth with three EG fields in TradingMetrics

- eg_full_kelly: Expected growth at full Kelly fraction
- eg_frac_kelly: Expected growth at fractional Kelly
- eg_flat_stake: Expected growth at flat stake fraction

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 2: Update Metrics Calculation

**Files:**
- Modify: `src/core/metrics.py`
- Test: `tests/unit/test_metrics.py`

**Step 1: Write failing tests for new EG calculations**

Add to `tests/unit/test_metrics.py` in `TestMetricsCalculatorExtended` class:

```python
def test_eg_full_kelly_calculation(self) -> None:
    """EG Full Kelly calculated with full Kelly fraction."""
    calc = MetricsCalculator()
    df = pd.DataFrame({
        "gain_pct": [0.05, 0.03, -0.02, 0.04, -0.01],  # Positive edge
    })
    metrics, _, _ = calc.calculate(df, "gain_pct", derived=True)

    assert metrics.kelly is not None
    assert metrics.kelly > 0
    assert metrics.eg_full_kelly is not None
    # EG = f*μ - f²σ²/2, should be positive with positive Kelly

def test_eg_frac_kelly_calculation(self) -> None:
    """EG Frac Kelly calculated with fractional Kelly."""
    calc = MetricsCalculator()
    df = pd.DataFrame({
        "gain_pct": [0.05, 0.03, -0.02, 0.04, -0.01],
    })
    metrics, _, _ = calc.calculate(
        df, "gain_pct", derived=True, fractional_kelly_pct=25.0
    )

    assert metrics.eg_frac_kelly is not None
    assert metrics.eg_full_kelly is not None
    # Fractional should be less than full Kelly EG
    assert metrics.eg_frac_kelly < metrics.eg_full_kelly

def test_eg_flat_stake_calculation(self) -> None:
    """EG Flat Stake calculated with flat stake / capital fraction."""
    calc = MetricsCalculator()
    df = pd.DataFrame({
        "gain_pct": [0.05, 0.03, -0.02, 0.04, -0.01],
    })
    metrics, _, _ = calc.calculate(
        df, "gain_pct", derived=True,
        flat_stake=10000.0, start_capital=100000.0
    )

    assert metrics.eg_flat_stake is not None
    # 10k/100k = 10% bet fraction

def test_all_eg_none_when_kelly_negative(self) -> None:
    """All EG metrics are None when Kelly is negative."""
    calc = MetricsCalculator()
    df = pd.DataFrame({
        "gain_pct": [0.02, -0.05, -0.04, -0.03, -0.06],  # Negative edge
    })
    metrics, _, _ = calc.calculate(
        df, "gain_pct", derived=True,
        flat_stake=10000.0, start_capital=100000.0
    )

    assert metrics.kelly is not None
    assert metrics.kelly < 0
    assert metrics.eg_full_kelly is None
    assert metrics.eg_frac_kelly is None
    # eg_flat_stake can still be calculated even with negative Kelly
    # because flat stake doesn't depend on Kelly
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_metrics.py -k "eg_" -v`

Expected: FAIL

**Step 3: Implement calculations in metrics.py**

In `src/core/metrics.py`, replace the expected_growth calculation block with:

```python
        # Expected Growth calculations
        # EG = f * μ - (f² * σ²) / 2
        # where f = bet fraction, μ = EV, σ² = variance
        eg_full_kelly: float | None = None
        eg_frac_kelly: float | None = None
        eg_flat_stake: float | None = None

        all_gains = winner_gains + loser_gains
        combined_variance: float | None = None
        if len(all_gains) >= 2:
            var_result = pd.Series(all_gains).var()
            if pd.notna(var_result):
                combined_variance = cast(float, var_result)

        if combined_variance is not None and ev is not None:
            # EG Full Kelly - only when Kelly > 0
            if kelly is not None and kelly > 0:
                kelly_decimal = kelly / 100
                eg_full_kelly = (kelly_decimal * ev) - (
                    (kelly_decimal**2) * combined_variance / 2
                )

            # EG Fractional Kelly - only when fractional Kelly > 0
            if fractional_kelly is not None and fractional_kelly > 0:
                frac_kelly_decimal = fractional_kelly / 100
                eg_frac_kelly = (frac_kelly_decimal * ev) - (
                    (frac_kelly_decimal**2) * combined_variance / 2
                )

            # EG Flat Stake - when flat_stake and start_capital provided
            if flat_stake is not None and start_capital is not None:
                if flat_stake > 0 and start_capital > 0:
                    flat_fraction = flat_stake / start_capital
                    eg_flat_stake = (flat_fraction * ev) - (
                        (flat_fraction**2) * combined_variance / 2
                    )
```

**Step 4: Update TradingMetrics return**

Update the return statement to use the new fields instead of `expected_growth`.

**Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_metrics.py -k "eg_" -v`

Expected: PASS

**Step 6: Remove old expected_growth test, update others**

Remove or update `test_expected_growth_none_when_kelly_negative` (now covered by `test_all_eg_none_when_kelly_negative`).

**Step 7: Run all metrics tests**

Run: `pytest tests/unit/test_metrics.py -v`

Expected: PASS

**Step 8: Commit**

```bash
git add src/core/metrics.py tests/unit/test_metrics.py
git commit -m "feat: calculate three expected growth metrics for different position sizes

- eg_full_kelly: Uses full Kelly fraction
- eg_frac_kelly: Uses fractional Kelly (default 25%)
- eg_flat_stake: Uses flat_stake / start_capital fraction

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 3: Update Default Values

**Files:**
- Modify: `src/ui/components/user_inputs_panel.py`

**Step 1: Update flat_stake default**

In `src/ui/components/user_inputs_panel.py`, line 95, change:
- From: `default=1000.0`
- To: `default=10000.0`

**Step 2: Update start_capital default**

In `src/ui/components/user_inputs_panel.py`, line 106, change:
- From: `default=10000.0`
- To: `default=100000.0`

**Step 3: Commit**

```bash
git add src/ui/components/user_inputs_panel.py
git commit -m "fix: update position sizing defaults to 100k capital, 10k flat stake

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 4: Update Metrics Grid Display

**Files:**
- Modify: `src/ui/components/metrics_grid.py`
- Test: `tests/widget/test_metrics_grid.py`

**Step 1: Update METRICS_CONFIG**

In `src/ui/components/metrics_grid.py`, find the "Expected Growth" entry and replace with three entries:

From:
```python
    ("Expected Growth", "expected_growth", ".2f"),
```

To:
```python
    ("EG Full Kelly", "eg_full_kelly", ".2f"),
    ("EG Frac Kelly", "eg_frac_kelly", ".2f"),
    ("EG Flat Stake", "eg_flat_stake", ".2f"),
```

**Step 2: Run widget tests**

Run: `pytest tests/widget/test_metrics_grid.py -v`

Fix any failures related to expected_growth references.

**Step 3: Commit**

```bash
git add src/ui/components/metrics_grid.py tests/widget/test_metrics_grid.py
git commit -m "feat: display three EG metrics in metrics grid

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 5: Update Comparison Grid Display

**Files:**
- Modify: `src/ui/components/comparison_grid.py`
- Test: `tests/widget/test_comparison_grid.py`

**Step 1: Update METRIC_SPECS**

In `src/ui/components/comparison_grid.py`, find the "expected_growth" entry and replace:

From:
```python
    "expected_growth": ("Expected Growth", ".2f", "pp", "higher"),
```

To:
```python
    "eg_full_kelly": ("EG Full Kelly", ".2f", "pp", "higher"),
    "eg_frac_kelly": ("EG Frac Kelly", ".2f", "pp", "higher"),
    "eg_flat_stake": ("EG Flat Stake", ".2f", "pp", "higher"),
```

**Step 2: Update EXTENDED_METRICS list**

Find `"expected_growth"` in the EXTENDED_METRICS list and replace with the three new field names.

**Step 3: Run widget tests**

Run: `pytest tests/widget/test_comparison_grid.py -v`

Fix any failures.

**Step 4: Commit**

```bash
git add src/ui/components/comparison_grid.py tests/widget/test_comparison_grid.py
git commit -m "feat: display three EG metrics in comparison grid

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 6: Update Export Manager

**Files:**
- Modify: `src/core/export_manager.py`

**Step 1: Search for expected_growth references**

Check if export_manager.py references expected_growth and update to the three new fields.

**Step 2: Update any references**

Replace `expected_growth` with appropriate new field(s) in export logic.

**Step 3: Commit if changes made**

```bash
git add src/core/export_manager.py
git commit -m "refactor: update export manager for new EG fields

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 7: Update Test Fixtures

**Files:**
- Modify: `tests/conftest.py`

**Step 1: Update sample_metrics fixture**

Find any `TradingMetrics` instances in conftest.py and replace `expected_growth` with the three new fields.

**Step 2: Run affected tests**

Run: `pytest tests/ -v --ignore=tests/e2e -k "metrics"`

**Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: update fixtures for new EG fields

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 8: Final Verification

**Step 1: Run full test suite**

Run: `pytest tests/ -v --ignore=tests/e2e`

Expected: All tests pass (except pre-existing failures)

**Step 2: Manual verification**

Run: `python -m src.main`

Verify:
- Metrics grid shows "EG Full Kelly", "EG Frac Kelly", "EG Flat Stake"
- Comparison grid shows all three metrics
- Changing flat stake or start capital updates the EG Flat Stake value
- Default values show 100,000 capital and 10,000 flat stake

**Step 3: Final commit if any cleanup needed**

---

## Summary of Changes

| File | Change |
|------|--------|
| `src/core/models.py` | Replace `expected_growth` with `eg_full_kelly`, `eg_frac_kelly`, `eg_flat_stake` |
| `src/core/metrics.py` | Calculate all three EG values |
| `src/ui/components/user_inputs_panel.py` | Defaults: 100k capital, 10k flat stake |
| `src/ui/components/metrics_grid.py` | Display three EG metrics |
| `src/ui/components/comparison_grid.py` | Three EG metrics in comparison |
| `src/core/export_manager.py` | Update export references |
| `tests/unit/test_models.py` | Test new fields |
| `tests/unit/test_metrics.py` | Test new calculations |
| `tests/conftest.py` | Update fixtures |
| `tests/widget/test_metrics_grid.py` | Update widget tests |
| `tests/widget/test_comparison_grid.py` | Update widget tests |
