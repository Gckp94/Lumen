# Four Issues Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix four UI/calculation issues: Show Drawdown button not working, Max Loss % showing wrong metric, Filtered Flat Stake metrics blank, and verify drawdown calculation logic.

**Architecture:** Fix PyQtGraph FillBetweenItem curve refresh, change max_loss_pct to count stop-hit trades, update filtered metrics after debounced equity calculation, and verify/document drawdown logic.

**Tech Stack:** Python, PyQtGraph, Qt, dataclasses

---

## Issue Analysis

| Issue | Root Cause | Fix |
|-------|------------|-----|
| 1. Show Drawdown button | FillBetweenItem doesn't auto-refresh when curves get new data | Call `setCurves()` after `setData()` in `_replot_curves` |
| 2. Max Loss % wrong metric | Currently shows worst single-trade loss, user wants % of trades hitting stop | Change calculation to `(trades where MAE > stop_loss) / total * 100` |
| 3. Filtered Flat Stake blank | Fast path skips equity calculation, debounced path discards metrics | Update filtered_metrics after debounced calculation |
| 4. Drawdown values suspicious | Need verification | Verify logic is correct, values may be valid for Kelly sizing |

---

### Task 1: Fix Show Drawdown Button (FillBetweenItem Refresh)

**Files:**
- Modify: `src/ui/components/equity_chart.py:623-652` (`_replot_curves` method)
- Test: `tests/unit/test_equity_chart.py`

**Step 1: Write the failing test**

Add to `tests/unit/test_equity_chart.py` in `TestEquityChartDrawdown` class:

```python
def test_drawdown_fill_updates_when_data_changes(self, qtbot):
    """Drawdown fill refreshes correctly when curve data is updated."""
    chart = EquityChart()
    qtbot.addWidget(chart)

    # Set initial data
    equity_df1 = pd.DataFrame({
        "trade_num": [1, 2, 3],
        "equity": [100.0, 90.0, 95.0],  # Has drawdown
        "peak": [100.0, 100.0, 100.0],
    })
    chart.set_baseline(equity_df1)
    chart.set_drawdown_visible(True)

    assert chart._drawdown_fill.isVisible()

    # Update with new data
    equity_df2 = pd.DataFrame({
        "trade_num": [1, 2, 3, 4],
        "equity": [100.0, 80.0, 70.0, 90.0],  # Larger drawdown
        "peak": [100.0, 100.0, 100.0, 100.0],
    })
    chart.set_baseline(equity_df2)

    # Drawdown fill should still be visible and have updated curves
    assert chart._drawdown_fill.isVisible()
    # Verify the fill's curves are the current curve objects
    assert chart._drawdown_fill.curves[0] is chart._baseline_curve
    assert chart._drawdown_fill.curves[1] is chart._peak_curve
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_equity_chart.py::TestEquityChartDrawdown::test_drawdown_fill_updates_when_data_changes -v`
Expected: FAIL (curves attribute may not exist or not match)

**Step 3: Write minimal implementation**

In `src/ui/components/equity_chart.py`, modify `_replot_curves` method. After setting data on both curves, add a call to refresh the FillBetweenItem:

```python
def _replot_curves(self) -> None:
    """Replot all curves using current axis mode's X values."""
    # Check if we should use timestamps (DATE mode with available timestamps)
    use_timestamps = (
        self._axis_mode == AxisMode.DATE
        and self._baseline_timestamps is not None
        and len(self._baseline_timestamps) > 0
    )

    # Replot baseline curve
    if self._baseline_equity is not None:
        if use_timestamps and self._baseline_timestamps is not None:
            x_data = self._baseline_timestamps
        else:
            x_data = self._baseline_trade_nums

        if x_data is not None:
            self._baseline_curve.setData(x=x_data, y=self._baseline_equity)
            if self._baseline_peak is not None:
                self._peak_curve.setData(x=x_data, y=self._baseline_peak)
                # Refresh FillBetweenItem after curves have new data
                self._drawdown_fill.setCurves(self._baseline_curve, self._peak_curve)

    # Replot filtered curve
    if self._filtered_equity is not None:
        if use_timestamps and self._filtered_timestamps is not None:
            x_data = self._filtered_timestamps
        else:
            x_data = self._filtered_trade_nums

        if x_data is not None:
            self._filtered_curve.setData(x=x_data, y=self._filtered_equity)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_equity_chart.py::TestEquityChartDrawdown -v`
Expected: PASS

**Step 5: Run all equity chart tests**

Run: `pytest tests/unit/test_equity_chart.py tests/widget/test_equity_chart.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add src/ui/components/equity_chart.py tests/unit/test_equity_chart.py
git commit -m "fix: refresh FillBetweenItem when curve data changes

The Show Drawdown button wasn't working because FillBetweenItem
doesn't automatically update when its underlying curves get new data.
Now we call setCurves() after setting curve data in _replot_curves.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
"
```

---

### Task 2: Change Max Loss % to Count Stop-Hit Trades

**Files:**
- Modify: `src/core/models.py:145` (TradingMetrics docstring)
- Modify: `src/core/metrics.py:259-267` (calculation)
- Modify: `src/ui/components/metrics_grid.py:25,55` (label/description)
- Test: `tests/unit/test_metrics.py`

**Step 1: Write the failing test**

Add to `tests/unit/test_metrics.py`:

```python
class TestMaxLossPctStopHit:
    """Tests for max_loss_pct as percentage of trades hitting stop."""

    def test_max_loss_pct_counts_stop_hits(self):
        """max_loss_pct should be (trades where MAE > stop) / total * 100."""
        df = pd.DataFrame({
            "gain_pct": [0.05, -0.02, 0.03, -0.04, 0.01, -0.03, 0.02, -0.01, 0.04, -0.02],
            "mae_pct": [5.0, 12.0, 3.0, 9.0, 2.0, 7.0, 4.0, 15.0, 6.0, 8.0],  # 3 trades > 8% stop
        })

        calc = MetricsCalculator()
        adjustment_params = AdjustmentParams(stop_loss=8.0, efficiency=0.0)

        metrics, _, _ = calc.calculate(
            df=df,
            gain_col="gain_pct",
            derived=True,
            adjustment_params=adjustment_params,
            mae_col="mae_pct",
        )

        # 3 out of 10 trades hit stop (mae_pct > 8.0): indices 1, 7, 8 have mae 12, 15, 9
        # Wait: mae 12 > 8, mae 15 > 8, mae 9 > 8 = 3 trades
        # 3/10 = 30%
        assert metrics.max_loss_pct == 30.0

    def test_max_loss_pct_zero_when_no_stops_hit(self):
        """max_loss_pct should be 0 when no trades hit stop."""
        df = pd.DataFrame({
            "gain_pct": [0.05, -0.02, 0.03],
            "mae_pct": [3.0, 5.0, 2.0],  # All below 8% stop
        })

        calc = MetricsCalculator()
        adjustment_params = AdjustmentParams(stop_loss=8.0, efficiency=0.0)

        metrics, _, _ = calc.calculate(
            df=df,
            gain_col="gain_pct",
            derived=True,
            adjustment_params=adjustment_params,
            mae_col="mae_pct",
        )

        assert metrics.max_loss_pct == 0.0

    def test_max_loss_pct_none_without_adjustment_params(self):
        """max_loss_pct should be None when no adjustment_params provided."""
        df = pd.DataFrame({
            "gain_pct": [0.05, -0.02, 0.03],
        })

        calc = MetricsCalculator()

        metrics, _, _ = calc.calculate(
            df=df,
            gain_col="gain_pct",
            derived=True,
        )

        assert metrics.max_loss_pct is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_metrics.py::TestMaxLossPctStopHit -v`
Expected: FAIL (current implementation returns loser_min, not stop hit percentage)

**Step 3: Update TradingMetrics docstring**

In `src/core/models.py`, update the `max_loss_pct` field docstring (around line 145):

```python
    # Streak & Loss Metrics (Story 3.3 - metrics 13-15)
    max_consecutive_wins: int | None = None
    max_consecutive_losses: int | None = None
    max_loss_pct: float | None = None  # Percentage of trades that hit stop loss level
```

And in the class docstring (around line 100):

```python
        max_loss_pct: Percentage of trades that hit the stop loss level (MAE > stop_loss).
```

**Step 4: Update calculation in MetricsCalculator**

In `src/core/metrics.py`, replace lines 259-267:

```python
        # Streak & Loss Metrics (Story 3.3 - metrics 13-15)
        max_consecutive_wins, max_consecutive_losses = self._calculate_streaks(winners_mask)

        # Calculate max_loss_pct as percentage of trades hitting stop level
        max_loss_pct: float | None = None
        if adjustment_params is not None and mae_col is not None and mae_col in df.columns:
            mae_values = df[mae_col].astype(float)
            stop_hit_count = (mae_values > adjustment_params.stop_loss).sum()
            max_loss_pct = (stop_hit_count / num_trades) * 100 if num_trades > 0 else 0.0

        logger.debug(
            "Calculated streaks: max_wins=%s, max_losses=%s, max_loss_pct=%s",
            max_consecutive_wins,
            max_consecutive_losses,
            max_loss_pct,
        )
```

**Step 5: Update UI label and description**

In `src/ui/components/metrics_grid.py`, update line 25:

```python
    "Max Loss %": "Percentage of trades that hit stop loss level",
```

**Step 6: Run test to verify it passes**

Run: `pytest tests/unit/test_metrics.py::TestMaxLossPctStopHit -v`
Expected: PASS

**Step 7: Run all metrics tests**

Run: `pytest tests/unit/test_metrics.py -v`
Expected: All PASS (may need to update other tests that assume old behavior)

**Step 8: Commit**

```bash
git add src/core/models.py src/core/metrics.py src/ui/components/metrics_grid.py tests/unit/test_metrics.py
git commit -m "fix: Max Loss % now shows percentage of trades hitting stop level

Changed max_loss_pct from worst single-trade loss to the percentage
of trades where MAE exceeded the stop loss setting. For example,
if 10 out of 1000 trades hit stop, max_loss_pct = 1%.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
"
```

---

### Task 3: Fix Filtered Flat Stake Metrics Being Blank

**Files:**
- Modify: `src/tabs/pnl_stats.py:1087-1145` (`_calculate_filtered_equity_curves` method)
- Test: `tests/unit/test_pnl_stats.py` or `tests/integration/test_pnl_stats.py`

**Step 1: Understand the issue**

The problem is in `_calculate_filtered_equity_curves` (lines 1117-1145):
- It calculates `metrics, flat_equity, kelly_equity = self._metrics_calculator.calculate(...)`
- The `metrics` object contains the flat stake metrics (pnl, max_dd, etc.)
- But it's discarded! Only `flat_equity` and `kelly_equity` are stored
- The filtered_metrics object (from fast path) has `flat_stake_pnl=None`, etc.

**Step 2: Write the failing test**

Add to appropriate test file (create if needed):

```python
def test_filtered_flat_stake_metrics_populated_after_debounce(qtbot, sample_df, sample_mapping):
    """Filtered flat stake metrics should be populated after debounced calculation."""
    app_state = AppState()
    app_state.baseline_df = sample_df
    app_state.column_mapping = sample_mapping

    tab = PnLStatsTab(app_state)
    qtbot.addWidget(tab)

    # Apply a filter to trigger filtered calculation
    app_state.filtered_df = sample_df.head(50)

    # Wait for debounced equity calculation
    qtbot.wait(500)  # Animation.DEBOUNCE_METRICS + buffer

    # Filtered metrics should have flat stake data
    filtered = app_state.filtered_metrics
    assert filtered is not None
    assert filtered.flat_stake_pnl is not None
    assert filtered.flat_stake_max_dd is not None
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/unit/test_pnl_stats.py::test_filtered_flat_stake_metrics_populated_after_debounce -v`
Expected: FAIL (flat_stake_pnl is None)

**Step 4: Write minimal implementation**

In `src/tabs/pnl_stats.py`, modify `_calculate_filtered_equity_curves` method. After line 1131, add code to update filtered_metrics:

```python
    def _calculate_filtered_equity_curves(self) -> None:
        """Calculate filtered equity curves after debounce completes."""
        filtered_df = self._app_state.filtered_df
        column_mapping = self._app_state.column_mapping

        if filtered_df is None or column_mapping is None:
            logger.debug(
                "Cannot calculate filtered equity curves: missing data or mapping"
            )
            self._app_state.is_calculating_filtered = False
            self._app_state.filtered_calculation_completed.emit()
            return

        # Handle empty DataFrame edge case
        if filtered_df.empty:
            self._app_state.filtered_flat_stake_equity_curve = None
            self._app_state.filtered_kelly_equity_curve = None
            self._app_state.is_calculating_filtered = False
            self._app_state.filtered_calculation_completed.emit()
            return

        # Get current parameters
        adjustment_params = self._app_state.adjustment_params
        metrics_inputs = self._app_state.metrics_user_inputs
        fractional_kelly_pct = (
            metrics_inputs.fractional_kelly if metrics_inputs else 25.0
        )
        flat_stake = metrics_inputs.flat_stake if metrics_inputs else 1000.0
        start_capital = metrics_inputs.starting_capital if metrics_inputs else 10000.0

        # Full calculation with equity curves
        metrics, flat_equity, kelly_equity = self._metrics_calculator.calculate(
            df=filtered_df,
            gain_col=column_mapping.gain_pct,
            derived=column_mapping.win_loss_derived,
            breakeven_is_win=column_mapping.breakeven_is_win,
            win_loss_col=column_mapping.win_loss,
            adjustment_params=adjustment_params,
            mae_col=column_mapping.mae_pct,
            fractional_kelly_pct=fractional_kelly_pct,
            date_col=column_mapping.date,
            time_col=column_mapping.time,
            flat_stake=flat_stake,
            start_capital=start_capital,
        )

        # Update filtered metrics with flat stake and Kelly values
        if self._app_state.filtered_metrics is not None:
            from dataclasses import replace
            updated_metrics = replace(
                self._app_state.filtered_metrics,
                flat_stake_pnl=metrics.flat_stake_pnl,
                flat_stake_max_dd=metrics.flat_stake_max_dd,
                flat_stake_max_dd_pct=metrics.flat_stake_max_dd_pct,
                flat_stake_dd_duration=metrics.flat_stake_dd_duration,
                kelly_pnl=metrics.kelly_pnl,
                kelly_max_dd=metrics.kelly_max_dd,
                kelly_max_dd_pct=metrics.kelly_max_dd_pct,
                kelly_dd_duration=metrics.kelly_dd_duration,
            )
            self._app_state.filtered_metrics = updated_metrics
            # Re-emit metrics updated signal so UI refreshes
            self._app_state.metrics_updated.emit(
                self._app_state.baseline_metrics,
                self._app_state.filtered_metrics,
            )
            logger.debug("Updated filtered metrics with flat stake/Kelly values")

        # Store and emit filtered equity curves
        self._app_state.filtered_flat_stake_equity_curve = flat_equity
        if flat_equity is not None:
            self._app_state.filtered_equity_curve_updated.emit(flat_equity)

        self._app_state.filtered_kelly_equity_curve = kelly_equity
        if kelly_equity is not None:
            self._app_state.filtered_kelly_equity_curve_updated.emit(kelly_equity)

        # Complete calculation
        self._app_state.is_calculating_filtered = False
        self._app_state.filtered_calculation_completed.emit()
        logger.debug("Filtered equity curves calculated")
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_pnl_stats.py::test_filtered_flat_stake_metrics_populated_after_debounce -v`
Expected: PASS

**Step 6: Run all pnl_stats tests**

Run: `pytest tests/unit/test_pnl_stats.py tests/widget/test_pnl_stats.py -v`
Expected: All PASS

**Step 7: Commit**

```bash
git add src/tabs/pnl_stats.py tests/unit/test_pnl_stats.py
git commit -m "fix: populate filtered flat stake metrics after debounced calculation

The filtered flat stake metrics were blank because the fast path
calculation skipped equity curves, and the debounced path discarded
the metrics object. Now we update filtered_metrics with the flat
stake and Kelly values after the debounced calculation completes.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
"
```

---

### Task 4: Verify Drawdown Calculation Logic

**Files:**
- Review: `src/core/equity.py:88-151` (`calculate_drawdown_metrics`)
- Test: `tests/unit/test_equity.py`

**Step 1: Analyze the current implementation**

The current logic at `src/core/equity.py:88-151`:

```python
# drawdown = equity - peak (always <= 0)
# drawdown_pct = (drawdown / peak) * -100.0 (positive percentage)
# max_dd_pct_idx = argmax(drawdown_pct) - finds max PERCENTAGE drawdown
# max_dd_dollars = abs(drawdown[max_dd_pct_idx]) - dollar amount at that point
```

**Potential Issue:** `max_dd_dollars` uses the dollar amount at the maximum *percentage* drawdown point, not the maximum *dollar* drawdown point. These can differ:
- Trade A: peak=$100, equity=$50 → drawdown=$50 (50%)
- Trade B: peak=$1000, equity=$700 → drawdown=$300 (30%)

Trade A has higher %, Trade B has higher $.

**Decision:** The current behavior finds Max DD (%) correctly, but Max DD ($) should be the maximum dollar drawdown, not the dollar value at max % point.

**Step 2: Write the failing test**

Add to `tests/unit/test_equity.py`:

```python
def test_max_dd_dollar_is_max_dollar_amount():
    """Max DD ($) should be the largest dollar drawdown, not at max % point."""
    calc = EquityCalculator()

    # Scenario: max % drawdown at different point than max $ drawdown
    equity_df = pd.DataFrame({
        "trade_num": [1, 2, 3, 4, 5],
        "equity": [100.0, 50.0, 200.0, 150.0, 180.0],  # Point 2: 50% DD, $50. Point 4: 25% DD, $50
        "peak": [100.0, 100.0, 200.0, 200.0, 200.0],
        "drawdown": [0.0, -50.0, 0.0, -50.0, -20.0],  # Max $ DD is $50 at both points 2 and 4
    })

    max_dd_dollars, max_dd_pct, _ = calc.calculate_drawdown_metrics(equity_df)

    # Max % is at point 2 (50%)
    assert max_dd_pct == 50.0
    # Max $ should be 50 (same in this case)
    assert max_dd_dollars == 50.0

def test_max_dd_dollar_differs_from_max_pct_point():
    """When max $ and max % are at different points, both should be correct."""
    calc = EquityCalculator()

    equity_df = pd.DataFrame({
        "trade_num": [1, 2, 3, 4, 5, 6],
        "equity": [100.0, 40.0, 150.0, 1000.0, 700.0, 900.0],
        "peak": [100.0, 100.0, 150.0, 1000.0, 1000.0, 1000.0],
        "drawdown": [0.0, -60.0, 0.0, 0.0, -300.0, -100.0],
    })

    max_dd_dollars, max_dd_pct, _ = calc.calculate_drawdown_metrics(equity_df)

    # Max % is at point 2: 60% (60/100)
    assert max_dd_pct == 60.0
    # Max $ is at point 5: $300
    assert max_dd_dollars == 300.0
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/unit/test_equity.py::test_max_dd_dollar_differs_from_max_pct_point -v`
Expected: FAIL (current returns $60 instead of $300)

**Step 4: Fix the implementation**

In `src/core/equity.py`, modify `calculate_drawdown_metrics` (lines 88-151):

```python
def calculate_drawdown_metrics(
    self,
    equity_df: pd.DataFrame,
) -> tuple[float | None, float | None, int | str | None]:
    """Calculate max drawdown and duration.

    Returns:
        Tuple of (max_dd_dollars, max_dd_pct, dd_duration)
        - max_dd_dollars: Maximum drawdown in absolute dollar terms
        - max_dd_pct: Maximum drawdown as percentage of peak at that point
        - dd_duration: int (trading days) or "Not recovered"

    Note:
        Returns (None, None, None) if no drawdown occurred (equity only increased)
        or if peak is zero/negative (edge case - no valid percentage).
    """
    if equity_df.empty:
        return (None, None, None)

    drawdown: np.ndarray = equity_df["drawdown"].to_numpy(dtype=float)
    peak: np.ndarray = equity_df["peak"].to_numpy(dtype=float)
    equity: np.ndarray = equity_df["equity"].to_numpy(dtype=float)

    # Check if there's any drawdown
    if np.all(drawdown >= 0):
        return (None, None, None)

    # Calculate drawdown percentage at each point
    # Avoid division by zero for zero/negative peaks
    with np.errstate(divide="ignore", invalid="ignore"):
        drawdown_pct: np.ndarray = np.where(peak > 0, (drawdown / peak) * -100.0, 0.0)

    # Find maximum DOLLAR drawdown (most negative drawdown value)
    max_dd_dollar_idx = int(np.argmin(drawdown))  # argmin because drawdown is negative
    max_dd_dollars = float(abs(drawdown[max_dd_dollar_idx]))

    # Find maximum PERCENTAGE drawdown
    max_dd_pct_idx = int(np.argmax(drawdown_pct))
    max_dd_pct_value: float | None = float(drawdown_pct[max_dd_pct_idx])
    peak_at_max_dd = float(peak[max_dd_pct_idx])

    # Edge case: if peak is zero or negative, percentage is undefined
    if peak_at_max_dd <= 0:
        max_dd_pct_value = None

    # Calculate drawdown duration (from max percentage drawdown point)
    dd_duration: int | str | None
    recovered = False
    for i in range(max_dd_pct_idx + 1, len(equity)):
        if equity[i] >= peak_at_max_dd:
            dd_duration = i - max_dd_pct_idx
            recovered = True
            break

    if not recovered:
        dd_duration = "Not recovered"

    logger.debug(
        "Drawdown metrics: max_dd=$%.2f, max_dd_pct=%s, duration=%s",
        max_dd_dollars,
        f"{max_dd_pct_value:.2f}%" if max_dd_pct_value is not None else "N/A",
        dd_duration,
    )

    return (max_dd_dollars, max_dd_pct_value, dd_duration)
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_equity.py::test_max_dd_dollar_differs_from_max_pct_point -v`
Expected: PASS

**Step 6: Run all equity tests**

Run: `pytest tests/unit/test_equity.py -v`
Expected: All PASS

**Step 7: Commit**

```bash
git add src/core/equity.py tests/unit/test_equity.py
git commit -m "fix: Max DD ($) now shows largest dollar drawdown

Previously Max DD ($) showed the dollar amount at the point of
maximum percentage drawdown. Now it correctly shows the largest
absolute dollar drawdown, which may occur at a different point
than the maximum percentage drawdown.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
"
```

---

### Task 5: Final Integration Testing

**Step 1: Run all tests**

Run: `pytest tests/ -v --tb=short`
Expected: All PASS

**Step 2: Manual testing checklist**

1. Load sample data with trades
2. Enable "Show Drawdown" checkbox - verify coral fill appears between baseline and peak curves
3. Check Max Loss % shows percentage of trades hitting stop (not worst single loss)
4. Apply a filter and wait ~500ms - verify Filtered Flat Stake metrics populate
5. Verify Max DD ($) and Max DD (%) show independent maximum values

**Step 3: Final commit**

```bash
git add -A
git commit -m "test: add integration tests for four issue fixes

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
"
```

---

## Summary

| Task | File | Change |
|------|------|--------|
| 1 | `equity_chart.py` | Add `setCurves()` call in `_replot_curves` |
| 2 | `metrics.py`, `models.py`, `metrics_grid.py` | Change max_loss_pct to count stop-hit trades |
| 3 | `pnl_stats.py` | Update filtered_metrics after debounced calculation |
| 4 | `equity.py` | Use `argmin(drawdown)` for max dollar DD |
