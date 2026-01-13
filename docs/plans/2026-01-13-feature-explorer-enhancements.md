# Feature Explorer Enhancements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add individual filter apply buttons, contrast color toggle for scatter plots, and fix active filter count for time/date ranges.

**Architecture:** Three independent features: (1) Add action button to ColumnFilterRow for individual filter application, (2) Add contrast color toggle to chart sidebar with per-point coloring based on value sign, (3) Fix filter count logic to include date/time range filters in the active count.

**Tech Stack:** PyQt6, PyQtGraph, Python dataclasses

---

## Task 1: Add Individual Apply Button to ColumnFilterRow

**Files:**
- Modify: `src/ui/components/column_filter_row.py`
- Modify: `src/ui/components/column_filter_panel.py`

### Step 1: Add apply_clicked signal to ColumnFilterRow

In `column_filter_row.py`, add the signal declaration.

```python
# In ColumnFilterRow class, after existing signals (around line 25-27):
from PyQt6.QtCore import pyqtSignal

class ColumnFilterRow(QWidget):
    values_changed = pyqtSignal()
    operator_changed = pyqtSignal()
    apply_clicked = pyqtSignal(str)  # Emits column name when clicked
```

### Step 2: Add apply button to row layout

In `ColumnFilterRow.__init__`, after the indicator widget (around line 80), add the apply button.

```python
# After indicator creation, before layout.addStretch():
self._apply_btn = QPushButton()
self._apply_btn.setFixedSize(20, 20)
self._apply_btn.setToolTip("Apply this filter only")
self._apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
self._apply_btn.setStyleSheet(f"""
    QPushButton {{
        background: transparent;
        border: none;
        border-radius: 4px;
        font-size: 14px;
        color: {Colors.SIGNAL_CYAN};
    }}
    QPushButton:hover {{
        background: {Colors.BG_BORDER};
    }}
    QPushButton:pressed {{
        background: {Colors.BG_ELEVATED};
    }}
    QPushButton:disabled {{
        color: {Colors.TEXT_MUTED};
    }}
""")
self._apply_btn.setText("▶")
self._apply_btn.setEnabled(False)
self._apply_btn.clicked.connect(self._on_apply_clicked)
layout.addWidget(self._apply_btn)
```

### Step 3: Add handler method and enable/disable logic

Add the handler method to ColumnFilterRow:

```python
def _on_apply_clicked(self) -> None:
    """Emit apply signal with column name."""
    self.apply_clicked.emit(self._column)
```

Update `_update_indicator` method to also enable/disable the apply button:

```python
def _update_indicator(self) -> None:
    """Update indicator and apply button based on input state."""
    has_values = self.has_values()
    self._indicator.setStyleSheet(f"""
        background: {Colors.SIGNAL_AMBER if has_values else 'transparent'};
        border-radius: 4px;
    """)
    self._apply_btn.setEnabled(has_values)
```

### Step 4: Connect signal in ColumnFilterPanel

In `column_filter_panel.py`, in the `_create_row` method (around line 85), connect the new signal:

```python
def _create_row(self, column: str, index: int) -> ColumnFilterRow:
    row = ColumnFilterRow(column, index)
    row.values_changed.connect(self._on_row_values_changed)
    row.operator_changed.connect(self._on_row_values_changed)
    row.apply_clicked.connect(self._on_row_apply_clicked)  # Add this line
    return row
```

### Step 5: Add single-filter apply handler to ColumnFilterPanel

Add method to ColumnFilterPanel:

```python
def _on_row_apply_clicked(self, column: str) -> None:
    """Apply filter for a single column only."""
    for row in self._rows:
        if row._column == column:
            criteria = row.get_criteria()
            if criteria:
                self.single_filter_applied.emit(criteria)
            break
```

### Step 6: Add single_filter_applied signal to ColumnFilterPanel

In `column_filter_panel.py`, add the signal:

```python
class ColumnFilterPanel(QWidget):
    active_count_changed = pyqtSignal(int)
    filters_changed = pyqtSignal()
    single_filter_applied = pyqtSignal(object)  # Emits single FilterCriteria
```

### Step 7: Connect signal in FilterPanel

In `filter_panel.py`, connect the ColumnFilterPanel's single_filter_applied signal:

```python
# In FilterPanel.__init__, after creating _column_filter_panel:
self._column_filter_panel.single_filter_applied.connect(self._on_single_filter_applied)
```

Add handler method:

```python
def _on_single_filter_applied(self, criteria: FilterCriteria) -> None:
    """Forward single filter criteria to parent."""
    self.single_filter_applied.emit(criteria)
```

Add signal to FilterPanel:

```python
class FilterPanel(QWidget):
    filters_applied = pyqtSignal(list)
    filters_cleared = pyqtSignal()
    first_trigger_toggled = pyqtSignal(bool)
    date_range_changed = pyqtSignal(str, str, bool)
    time_range_changed = pyqtSignal(str, str, bool)
    single_filter_applied = pyqtSignal(object)  # Add this signal
```

### Step 8: Handle single filter in FeatureExplorerTab

In `feature_explorer.py`, connect the signal:

```python
# In __init__, after other filter_panel connections:
self._filter_panel.single_filter_applied.connect(self._on_single_filter_applied)
```

Add handler:

```python
def _on_single_filter_applied(self, criteria: FilterCriteria) -> None:
    """Apply a single filter criterion without clearing others."""
    # Add this filter to existing filters, replacing if same column exists
    current_filters = list(self._app_state.filters)
    
    # Remove existing filter for same column
    current_filters = [f for f in current_filters if f.column != criteria.column]
    
    # Add new filter
    current_filters.append(criteria)
    
    self._app_state.filters = current_filters
    self._apply_current_filters()
```

### Step 9: Run tests

Run: `pytest tests/ -v -k "filter"`
Expected: All existing filter tests pass

### Step 10: Commit

```bash
git add src/ui/components/column_filter_row.py src/ui/components/column_filter_panel.py src/ui/components/filter_panel.py src/tabs/feature_explorer.py
git commit -m "feat: add individual apply button to column filter rows"
```

---

## Task 2: Add Contrast Color Toggle for Scatter Plot

**Files:**
- Modify: `src/ui/components/chart_canvas.py`
- Modify: `src/tabs/feature_explorer.py`

### Step 1: Modify ChartCanvas.update_data to accept contrast_colors flag

In `chart_canvas.py`, update the method signature:

```python
def update_data(
    self,
    df: pd.DataFrame,
    column: str,
    color: str = Colors.SIGNAL_CYAN,
    contrast_colors: bool = False,
    color_positive: str = Colors.SIGNAL_CYAN,
    color_negative: str = Colors.SIGNAL_CORAL,
) -> None:
```

### Step 2: Implement contrast coloring logic

Replace the scatter rendering section in `update_data`:

```python
def update_data(
    self,
    df: pd.DataFrame,
    column: str,
    color: str = Colors.SIGNAL_CYAN,
    contrast_colors: bool = False,
    color_positive: str = Colors.SIGNAL_CYAN,
    color_negative: str = Colors.SIGNAL_CORAL,
) -> None:
    """Update chart with new data."""
    if df.empty or column not in df.columns:
        self._scatter.setData(x=[], y=[])
        return

    try:
        y_data = df[column].values
        x_data = np.arange(len(y_data))

        if contrast_colors:
            # Create per-point brushes based on value sign
            brushes = []
            for val in y_data:
                if val >= 0:
                    brushes.append(pg.mkBrush(color=color_positive))
                else:
                    brushes.append(pg.mkBrush(color=color_negative))
            self._scatter.setData(x=x_data, y=y_data, brush=brushes)
        else:
            # Single color for all points
            self._scatter.setBrush(pg.mkBrush(color=color))
            self._scatter.setData(x=x_data, y=y_data)

        self._plot_widget.autoRange()
    except Exception as e:
        self.render_failed.emit(str(e))
```

### Step 3: Add contrast toggle checkbox to FeatureExplorerTab sidebar

In `feature_explorer.py`, in `_create_sidebar`, add a checkbox after axis controls:

```python
# After axis controls section, before return:
# Contrast colors toggle
self._contrast_toggle = QCheckBox("Contrast colors (±0)")
self._contrast_toggle.setStyleSheet(f"""
    QCheckBox {{
        color: {Colors.TEXT_PRIMARY};
        font-size: 12px;
        spacing: 6px;
    }}
    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        border: 1px solid {Colors.BG_BORDER};
        border-radius: 3px;
        background: {Colors.BG_SURFACE};
    }}
    QCheckBox::indicator:checked {{
        background: {Colors.SIGNAL_CYAN};
        border-color: {Colors.SIGNAL_CYAN};
    }}
""")
self._contrast_toggle.setToolTip("Color points cyan if ≥0, coral if <0")
self._contrast_toggle.toggled.connect(self._on_contrast_toggled)
layout.addWidget(self._contrast_toggle)
```

### Step 4: Add handler and state variable

Add state variable in `__init__`:

```python
self._contrast_colors: bool = False
```

Add handler method:

```python
def _on_contrast_toggled(self, checked: bool) -> None:
    """Toggle contrast coloring on scatter plot."""
    self._contrast_colors = checked
    self._update_chart()
```

### Step 5: Update _update_chart to use contrast flag

Modify `_update_chart` method to pass the contrast flag:

```python
def _update_chart(self) -> None:
    """Redraw chart with current data and selections."""
    df = self._app_state.filtered_df
    if df is None or df.empty:
        return

    y_col = self._y_combo.currentText()
    if not y_col or y_col not in df.columns:
        return

    self._chart_canvas.update_data(
        df,
        y_col,
        contrast_colors=self._contrast_colors,
    )
```

### Step 6: Run tests

Run: `pytest tests/ -v -k "chart"`
Expected: All existing chart tests pass

### Step 7: Commit

```bash
git add src/ui/components/chart_canvas.py src/tabs/feature_explorer.py
git commit -m "feat: add contrast color toggle for scatter plot values above/below zero"
```

---

## Task 3: Fix Active Filter Count to Include Date/Time Ranges

**Files:**
- Modify: `src/tabs/feature_explorer.py`

### Step 1: Update _update_filter_summary to count date and time filters

Replace the `_update_filter_summary` method:

```python
def _update_filter_summary(self) -> None:
    """Update filter summary label with active filter count."""
    # Count column filters
    column_filter_count = len(self._app_state.filters)
    
    # Count date filter as active if not "all dates"
    date_filter_active = not self._all_dates
    
    # Count time filter as active if not "all times"
    time_filter_active = not self._all_times
    
    # Total active filters
    total_active = column_filter_count + (1 if date_filter_active else 0) + (1 if time_filter_active else 0)
    
    # Build display parts
    parts = []
    
    if date_filter_active:
        date_display = self._filter_panel._date_range_filter.get_display_range()
        if date_display:
            parts.append(date_display)
    
    if time_filter_active:
        time_display = self._filter_panel._time_range_filter.get_display_range()
        if time_display:
            parts.append(time_display)
    
    # Build final display string
    if total_active == 0:
        display = "Filters: None"
    else:
        if parts:
            range_info = ", ".join(parts)
            display = f"Filters: {total_active} active ({range_info})"
        else:
            display = f"Filters: {total_active} active"
    
    self._filter_summary_label.setText(display)
```

### Step 2: Run tests

Run: `pytest tests/ -v -k "filter"`
Expected: All filter tests pass

### Step 3: Test manually

1. Load data in Feature Explorer
2. Set a date range (uncheck "All dates")
3. Verify bottom bar shows "Filters: 1 active (date range)"
4. Set a time range (uncheck "All times")
5. Verify bottom bar shows "Filters: 2 active (date range, time range)"
6. Add a column filter and apply
7. Verify bottom bar shows "Filters: 3 active (date range, time range)"

### Step 4: Commit

```bash
git add src/tabs/feature_explorer.py
git commit -m "fix: include date and time range filters in active filter count"
```

---

## Summary

| Task | Files Modified | Key Changes |
|------|---------------|-------------|
| 1. Individual Apply Button | column_filter_row.py, column_filter_panel.py, filter_panel.py, feature_explorer.py | Added ▶ button per row, single_filter_applied signal chain |
| 2. Contrast Color Toggle | chart_canvas.py, feature_explorer.py | Per-point coloring based on value sign, checkbox toggle |
| 3. Fix Filter Count | feature_explorer.py | Count date/time as filters when not "all" |
