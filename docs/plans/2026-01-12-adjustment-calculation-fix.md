# Adjustment Calculation Unit Mismatch Fix

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the unit mismatch bug where `AdjustmentParams.calculate_adjusted_gains()` incorrectly mixes decimal-format gains with percentage-format stop_loss/efficiency values, causing all adjusted trades to become losers.

**Architecture:** Convert gains from decimal to percentage format before applying stop loss and efficiency adjustments, then convert back to decimal format for compatibility with `MetricsCalculator`.

**Tech Stack:** Python, pandas

---

## Background

**The Bug:**
- `gain_pct` values are in **decimal format** (0.20 = 20%)
- `mae_pct` values are in **percentage format** (27 = 27%)
- `stop_loss` and `efficiency` are in **percentage format** (8 = 8%, 5 = 5%)

**Current broken calculation:**
```python
# gains = 0.20 (decimal, meaning 20%)
# efficiency = 5.0 (percentage, meaning 5%)
adjusted = gains - efficiency  # = 0.20 - 5.0 = -4.80 (nonsense!)
```

**Correct calculation:**
```python
gains_pct = gains * 100  # = 20.0 (percentage)
adjusted_pct = gains_pct - efficiency  # = 20.0 - 5.0 = 15.0 (percentage)
adjusted = adjusted_pct / 100  # = 0.15 (decimal, meaning 15%)
```

---

## Task 1: Write Failing Test for Adjustment Calculation

**Files:**
- Create: `tests/unit/test_adjustment_params.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_adjustment_params.py
"""Tests for AdjustmentParams calculation."""

import pandas as pd
import pytest

from src.core.models import AdjustmentParams


class TestAdjustmentCalculation:
    """Tests for adjustment calculation with decimal-format gains."""

    def test_adjustment_preserves_decimal_format(self) -> None:
        """Adjusted gains should remain in decimal format."""
        # Input: gain_pct in decimal format (0.20 = 20%)
        df = pd.DataFrame({
            "gain_pct": [0.20, -0.05, 0.10],  # 20%, -5%, 10%
            "mae_pct": [5.0, 3.0, 2.0],  # All below 8% stop loss
        })

        adj = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
        result = adj.calculate_adjusted_gains(df, "gain_pct", "mae_pct")

        # Expected: gains converted to %, subtract 5% efficiency, convert back
        # 20% - 5% = 15% -> 0.15
        # -5% - 5% = -10% -> -0.10
        # 10% - 5% = 5% -> 0.05
        expected = [0.15, -0.10, 0.05]

        assert result.tolist() == pytest.approx(expected, rel=1e-6), (
            f"Expected {expected}, got {result.tolist()}. "
            "Adjustment should work with decimal-format gains."
        )

    def test_stop_loss_triggers_correctly(self) -> None:
        """Stop loss should trigger when MAE exceeds threshold."""
        df = pd.DataFrame({
            "gain_pct": [0.20, 0.30],  # 20%, 30%
            "mae_pct": [5.0, 15.0],  # First survives, second hits stop
        })

        adj = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
        result = adj.calculate_adjusted_gains(df, "gain_pct", "mae_pct")

        # First trade: 20% - 5% = 15% -> 0.15
        # Second trade: -8% (stop loss) - 5% = -13% -> -0.13
        expected = [0.15, -0.13]

        assert result.tolist() == pytest.approx(expected, rel=1e-6)

    def test_winner_becomes_loser_after_efficiency(self) -> None:
        """Small winner should become loser after efficiency adjustment."""
        df = pd.DataFrame({
            "gain_pct": [0.03],  # 3% gain
            "mae_pct": [2.0],  # Survives stop loss
        })

        adj = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
        result = adj.calculate_adjusted_gains(df, "gain_pct", "mae_pct")

        # 3% - 5% = -2% -> -0.02
        expected = [-0.02]

        assert result.tolist() == pytest.approx(expected, rel=1e-6)

    def test_single_trade_calculation(self) -> None:
        """Single trade calculation should match vectorized."""
        adj = AdjustmentParams(stop_loss=8.0, efficiency=5.0)

        # Test with decimal-format input
        # 20% gain, 5% MAE (survives stop loss)
        # Expected: 20% - 5% = 15%
        result = adj.calculate_adjusted_gain(gain_pct=20.0, mae_pct=5.0)
        assert result == pytest.approx(15.0, rel=1e-6)

        # 20% gain, 15% MAE (hits stop loss)
        # Expected: -8% - 5% = -13%
        result = adj.calculate_adjusted_gain(gain_pct=20.0, mae_pct=15.0)
        assert result == pytest.approx(-13.0, rel=1e-6)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_adjustment_params.py -v`
Expected: FAIL - current code produces nonsense values like -4.80 instead of 0.15

**Step 3: Implement the fix**

Modify `src/core/models.py` `calculate_adjusted_gains` method:

```python
def calculate_adjusted_gains(
    self, df: pd.DataFrame, gain_col: str, mae_col: str
) -> pd.Series:
    """Calculate efficiency-adjusted gains for all trades (vectorized).

    Args:
        df: DataFrame with trade data.
        gain_col: Column name for gain percentage (decimal format, e.g., 0.20 = 20%).
        mae_col: Column name for MAE percentage (percentage format, e.g., 27 = 27%).

    Returns:
        Series of efficiency-adjusted gain percentages (decimal format).
    """
    gains = df[gain_col].astype(float)
    mae = df[mae_col].astype(float)

    # Convert gains from decimal to percentage format for adjustment
    gains_pct = gains * 100

    # Step 1: Stop loss adjustment (vectorized)
    # If MAE > stop_loss, gain becomes -stop_loss (in percentage)
    stop_adjusted = gains_pct.where(mae <= self.stop_loss, -self.stop_loss)

    # Step 2: Efficiency adjustment (in percentage)
    adjusted_pct = stop_adjusted - self.efficiency

    # Convert back to decimal format for MetricsCalculator compatibility
    return adjusted_pct / 100
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_adjustment_params.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_adjustment_params.py src/core/models.py
git commit -m "fix: adjustment calculation handles decimal-format gains

The calculate_adjusted_gains method now correctly converts gains from
decimal format (0.20 = 20%) to percentage format before applying
stop loss and efficiency adjustments, then converts back to decimal.

This fixes the bug where a 20% gain with 5% efficiency produced
-4.80 (nonsense) instead of 0.15 (15% after adjustment).

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Update Single-Trade Calculation Method

**Files:**
- Modify: `src/core/models.py`

**Step 1: Check current single-trade method**

The `calculate_adjusted_gain` method (singular) is used for single-trade calculations. It currently expects percentage-format input per its docstring. We need to decide: should it also accept decimal format, or keep it as percentage?

For consistency, let's keep it as percentage format (since stop_loss and efficiency are in percentage) but update the docstring to be clearer.

**Step 2: Update docstring for clarity**

```python
def calculate_adjusted_gain(self, gain_pct: float, mae_pct: float) -> float:
    """Calculate efficiency-adjusted gain for a single trade.

    Note: This method expects PERCENTAGE format inputs (20 = 20%, not 0.20).
    For decimal-format inputs, use calculate_adjusted_gains() instead.

    Args:
        gain_pct: Original gain in percentage format (e.g., 20 = 20%).
        mae_pct: Maximum adverse excursion in percentage format.

    Returns:
        Efficiency-adjusted gain in percentage format.
    """
    # Step 1: Stop loss adjustment
    stop_adjusted = -self.stop_loss if mae_pct > self.stop_loss else gain_pct
    # Step 2: Efficiency adjustment
    return stop_adjusted - self.efficiency
```

**Step 3: Run tests**

Run: `pytest tests/unit/test_adjustment_params.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add src/core/models.py
git commit -m "docs: clarify percentage format expected in calculate_adjusted_gain

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Integration Test with Real Data Pattern

**Files:**
- Modify: `tests/integration/test_column_detection_edge_cases.py`

**Step 1: Add integration test**

```python
class TestAdjustmentWithDecimalGains:
    """Test adjustment calculations with decimal-format gain data."""

    def test_adjustment_produces_valid_metrics(self) -> None:
        """Metrics should be valid after adjustment with decimal gains."""
        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL", "MSFT", "AMZN"],
            "date": ["2024-01-01"] * 4,
            "time": ["09:30:00"] * 4,
            "gain_pct": [0.20, -0.05, 0.03, 0.15],  # Decimal: 20%, -5%, 3%, 15%
            "mae_pct": [5.0, 3.0, 2.0, 12.0],  # Percentage format
        })

        from src.core.metrics import MetricsCalculator
        from src.core.models import AdjustmentParams

        calc = MetricsCalculator()
        adj = AdjustmentParams(stop_loss=8.0, efficiency=5.0)

        metrics, _, _ = calc.calculate(
            df=df,
            gain_col="gain_pct",
            mae_col="mae_pct",
            derived=True,
            breakeven_is_win=False,
            adjustment_params=adj,
        )

        # After adjustment:
        # Trade 1: 20% - 5% = 15% (winner)
        # Trade 2: -5% - 5% = -10% (loser)
        # Trade 3: 3% - 5% = -2% (loser, was winner)
        # Trade 4: -8% (stop) - 5% = -13% (loser, hit stop)

        assert metrics.winner_count == 1, "Should have 1 winner after adjustment"
        assert metrics.loser_count == 3, "Should have 3 losers after adjustment"
        assert metrics.win_rate == pytest.approx(25.0, rel=0.01)
        assert metrics.avg_winner is not None, "avg_winner should not be None"
        assert metrics.avg_winner == pytest.approx(15.0, rel=0.01)  # 15%
```

**Step 2: Run test**

Run: `pytest tests/integration/test_column_detection_edge_cases.py::TestAdjustmentWithDecimalGains -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/integration/test_column_detection_edge_cases.py
git commit -m "test: add integration test for adjustment with decimal gains

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Verify with User's Actual Data

**Step 1: Run verification script**

```python
import pandas as pd
from src.core.metrics import MetricsCalculator
from src.core.models import AdjustmentParams

df = pd.read_excel(r'c:\Users\Gerry Chan\OneDrive\Documents\Para40Min15Prev40.xlsx',
                   sheet_name='1st_Trigger')

calc = MetricsCalculator()
adj = AdjustmentParams(stop_loss=8.0, efficiency=5.0)

metrics, _, _ = calc.calculate(
    df=df,
    gain_col='gain_pct',
    mae_col='mae_pct',
    derived=True,
    breakeven_is_win=False,
    adjustment_params=adj,
)

print(f"With adjustment (stop_loss=8%, efficiency=5%):")
print(f"  win_rate: {metrics.win_rate:.2f}%")
print(f"  avg_winner: {metrics.avg_winner}")
print(f"  avg_loser: {metrics.avg_loser:.2f}%")
print(f"  winner_count: {metrics.winner_count}")
print(f"  loser_count: {metrics.loser_count}")
```

Expected: avg_winner should NOT be None, win_rate should be reasonable (not 0%)

**Step 2: Final commit**

```bash
git add -A
git commit -m "test: verify adjustment fix with real data

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Summary

| Task | Component | Description |
|------|-----------|-------------|
| 1 | test_adjustment_params.py, models.py | Fix decimal/percentage unit mismatch |
| 2 | models.py | Clarify docstrings for format expectations |
| 3 | test_column_detection_edge_cases.py | Integration test with adjustment |
| 4 | Manual verification | Test with user's actual data |

**Root Cause:**
- `gain_pct` is in decimal format (0.20 = 20%)
- `stop_loss` and `efficiency` are in percentage format (8 = 8%)
- Subtracting 5.0 from 0.20 produces -4.80 (nonsense)

**Fix:**
- Convert gains to percentage (×100) before adjustment
- Apply stop loss and efficiency in percentage format
- Convert back to decimal (÷100) for MetricsCalculator compatibility
