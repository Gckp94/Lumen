# Three UI Bugs Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix three UI bugs: Show Drawdown button not working, Distribution Statistics showing wrong row counts, and Kelly chart not switching to date axis mode.

**Architecture:** Each bug requires targeted fixes in specific areas - drawdown visibility state sync, distribution card data source selection, and Kelly chart date handling already works (verification needed).

**Tech Stack:** Python, PyQt6, pyqtgraph

---

## Bug Analysis Summary

### Bug 1: Show Drawdown Button Clickable But Nothing Happens
**Root Cause:** The FillBetweenItem requires both curves to have data with same X coordinates. When `set_drawdown_visible(True)` is called, `setCurves()` is called but only if `_baseline_data` exists. However, the actual plotting with `setData()` happens in `_replot_curves()` and the fill might not update until data changes.

**Actual Issue Found:** After reading the code, the implementation looks correct. The fill is updated in `set_drawdown_visible()` and in `_replot_curves()`. The bug is likely that when toggling the checkbox, the `_baseline_data` check passes but the fill doesn't render because pyqtgraph's FillBetweenItem needs a nudge to redraw. We need to verify this and potentially call `update()` or refresh the plot.

### Bug 2: Distribution Statistics Not Adjusted to Filtered Rows
**Root Cause:** In `pnl_stats.py:951`, `_update_distribution_cards(metrics)` always passes the **baseline** `metrics` parameter, never the `filtered_metrics`. The distribution cards always show baseline statistics regardless of any filter applied.

### Bug 3: Compounded Kelly PnL Chart Does Not Switch to Date Mode
**Root Cause:** After reviewing the code, both charts use the same `_ChartPanel` class which includes the axis toggle. The Kelly chart should work the same as Flat Stake. However, the bug may be that the Kelly equity curve DataFrame doesn't have dates included, OR the toggle is not triggering properly. Need to verify the Kelly equity curve actually has a "date" column.

---

## Task 1: Fix Show Drawdown Button

**Files:**
- Modify: `src/ui/components/equity_chart.py:395-407`
- Test: Manual verification (visual chart update)

**Step 1: Read current implementation**

The `set_drawdown_visible()` method at line 395-407 currently:
```python
def set_drawdown_visible(self, visible: bool) -> None:
    self._show_drawdown = visible
    if visible and self._baseline_data is not None:
        self._drawdown_fill.setCurves(self._baseline_curve, self._peak_curve)
        self._drawdown_fill.setVisible(True)
    else:
        self._drawdown_fill.setVisible(False)
```

**Step 2: Add plot update after visibility change**

Add an explicit update to force redraw:

```python
def set_drawdown_visible(self, visible: bool) -> None:
    """Show or hide the drawdown fill.

    Args:
        visible: Whether to show drawdown fill.
    """
    self._show_drawdown = visible
    if visible and self._baseline_data is not None:
        # Refresh FillBetweenItem curves when making visible to ensure sync
        self._drawdown_fill.setCurves(self._baseline_curve, self._peak_curve)
        self._drawdown_fill.setVisible(True)
    else:
        self._drawdown_fill.setVisible(False)
    # Force plot update to ensure fill renders
    self._plot_widget.update()
```

**Step 3: Verify fix manually**

Run the application, load data, check "Show Drawdown" checkbox.
Expected: Coral-colored fill appears between equity curve and peak curve.

**Step 4: Commit**

```bash
git add src/ui/components/equity_chart.py
git commit -m "fix: force plot update when toggling drawdown visibility"
```

---

## Task 2: Fix Distribution Statistics Using Wrong Data Source

**Files:**
- Modify: `src/tabs/pnl_stats.py:951`
- Test: Manual verification (filter data, check distribution stats update)

**Step 1: Analyze current bug**

At line 951 in `_on_baseline_metrics_calculated()`:
```python
self._update_distribution_cards(metrics)  # Always uses baseline!
```

The `metrics` variable is the baseline metrics. When there's filtered data, it should use `filtered_metrics` instead.

**Step 2: Implement fix**

Change line 951 to conditionally use filtered metrics when available:

```python
# Update distribution cards: use filtered metrics if available, else baseline
if filtered_metrics is not None:
    self._update_distribution_cards(filtered_metrics)
else:
    self._update_distribution_cards(metrics)
```

**Step 3: Also update `_on_metrics_updated()` for consistency**

In `_on_metrics_updated()` (lines 785-810), ensure distribution cards also update when metrics change:

After line 807 (`self._comparison_grid.set_values(baseline, None)`), add:
```python
self._update_distribution_cards(baseline)
```

And in the `if filtered is not None:` branch (after line 803), add:
```python
self._update_distribution_cards(filtered)
```

**Step 4: Verify fix manually**

1. Load data
2. Apply a filter to reduce rows
3. Check Distribution Statistics cards
4. Expected: Count should match filtered row count, not baseline count

**Step 5: Commit**

```bash
git add src/tabs/pnl_stats.py
git commit -m "fix: distribution cards now show filtered metrics when filter applied"
```

---

## Task 3: Fix Kelly Chart Date Axis Switching

**Files:**
- Verify: `src/core/equity.py` (Kelly calculation includes date)
- Verify: `src/tabs/pnl_stats.py` (date_col passed to Kelly calculation)
- Potential fix: Ensure date column is included in Kelly equity curve

**Step 1: Verify date_col is passed to Kelly calculation**

In `metrics.py:321`, verify the `date_col` parameter is passed:
```python
kelly_result = equity_calculator.calculate_kelly_metrics(
    df, gain_col, start_capital, fractional_kelly_pct, kelly, date_col=date_col
)
```

This looks correct. The date_col is passed.

**Step 2: Verify `calculate_kelly()` includes date in result**

In `equity.py:304-306`:
```python
if date_col is not None and date_col in df.columns:
    result["date"] = df[date_col].values
```

This looks correct. The date is included when available.

**Step 3: Verify `_ChartPanel.set_baseline()` extracts dates**

In `equity_chart.py:756-759`:
```python
self._baseline_dates = None
if equity_df is not None and "date" in equity_df.columns:
    self._baseline_dates = equity_df["date"].values
self.chart.set_baseline(equity_df, self._baseline_dates)
```

This looks correct.

**Step 4: Debug the actual issue**

The code path looks correct. The issue may be:
1. The `date_col` passed to metrics.py is None
2. The date column doesn't exist in the DataFrame
3. Something else is happening

Add logging to verify. In `src/ui/components/equity_chart.py:750-759`, add debug logging:

```python
def set_baseline(self, equity_df: pd.DataFrame | None) -> None:
    """Pass-through to chart's set_baseline method.

    Args:
        equity_df: DataFrame with equity data (may include date column).
    """
    self._baseline_dates = None
    if equity_df is not None:
        logger.debug("set_baseline: columns=%s", list(equity_df.columns))
        if "date" in equity_df.columns:
            self._baseline_dates = equity_df["date"].values
            logger.debug("set_baseline: found %d dates", len(self._baseline_dates))
    self.chart.set_baseline(equity_df, self._baseline_dates)
```

**Step 5: Run and check logs**

Load data and check logs for both Flat Stake and Kelly charts.
Expected: Both should log "found X dates" if dates are present.

If Kelly doesn't log dates, trace back to verify date_col is being passed.

**Step 6: If date_col not passed to Kelly calculation**

Check `pnl_stats.py` where Kelly calculation is called. Ensure `date_col` is passed through the full chain.

**Step 7: Commit**

```bash
git add src/ui/components/equity_chart.py src/core/metrics.py
git commit -m "fix: Kelly chart now properly includes date column for axis switching"
```

---

## Summary of Changes

| Bug | File | Change |
|-----|------|--------|
| Show Drawdown | `equity_chart.py:407` | Add `self._plot_widget.update()` |
| Distribution Stats | `pnl_stats.py:951` | Use `filtered_metrics` when available |
| Kelly Date Axis | Verify chain works; add logging if needed | Ensure date_col flows through |

---

## Verification Checklist

- [ ] Show Drawdown checkbox toggles coral fill visibility
- [ ] Distribution Statistics match filtered row count when filter applied
- [ ] Both Flat Stake and Kelly charts switch to date axis when Date button pressed
- [ ] No regressions in existing chart functionality
