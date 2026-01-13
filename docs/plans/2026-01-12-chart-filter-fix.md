# Chart Filter Update Fix

> **Status:** COMPLETED

**Goal:** Fix Feature Explorer chart not updating when filters are applied

**Root Cause:** Missing `autoRange()` call after scatter plot data update

---

## Problem Description

When users applied filters in Feature Explorer:
- The bottom bar count correctly showed reduced rows (e.g., "Showing 500 of 1000")
- But the chart visualization appeared unchanged
- Both axes seemed to show the same values

## Investigation Summary

### Data Flow Traced
1. `FilterPanel._on_apply_filters()` → emits `filters_applied` signal
2. `FeatureExplorerTab._on_filters_applied()` → calls `_apply_current_filters()`
3. `_apply_current_filters()` → applies filters, emits `filtered_data_updated` signal
4. `_on_filtered_data_updated()` → calls `_update_chart()`
5. `_update_chart()` → calls `ChartCanvas.update_data(df, column)`
6. `update_data()` → calls `scatter.setData(x=x_data, y=y_data)`

### Root Cause Identified
The scatter plot data WAS being updated correctly, but PyQtGraph's view range was NOT auto-adjusting to show the new data extent.

Example scenario:
- Original data: 1000 points, X range 0-999
- Filtered data: 500 points, X range 0-499
- View remained at 0-999, making filtered data appear compressed/unchanged

## Fix Applied

**File:** `src/ui/components/chart_canvas.py`

**Change:** Added `self._plot_widget.autoRange()` call after `setData()` in `update_data()` method.

```python
# Update scatter plot with new color
self._scatter.setBrush(pg.mkBrush(color=color))
self._scatter.setData(x=x_data, y=y_data)

# Auto-fit view to new data range to ensure filtered data is visible
self._plot_widget.autoRange()
```

## Trade-offs

**Benefit:** Chart always shows the full extent of current data after filtering

**Trade-off:** User's manual zoom/pan state is reset on each data update. Users can use the "Auto Fit" button in the Axis Control Panel if they want to restore zoom after manual adjustment.

## Files Modified

- `src/ui/components/chart_canvas.py:update_data()` - Added autoRange() call
