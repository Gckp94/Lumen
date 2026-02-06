# Time Stop Tab Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Time Stop sub-tab to Statistics Tab for analyzing trade performance at fixed time intervals after entry.

**Architecture:** Extend ColumnMapping with 9 optional price_X_min_after fields. Compute change_X_min columns during file processing. Add Time Statistics and Time Stop tables to new sub-tab with scale-out controls.

**Tech Stack:** PyQt6, pandas, existing Statistics Tab patterns (GradientStyler, _calculate_return_metrics)

---

## Task 1: Add Time Interval Column Mappings to ColumnMapping

**Files:**
- Modify: `src/core/models.py:11-57`
- Test: `tests/unit/test_models.py`

**Step 1: Write the failing test**

```python
# In tests/unit/test_models.py
def test_column_mapping_has_time_interval_fields():
    """Test ColumnMapping has optional time interval price fields."""
    mapping = ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
        price_10_min_after="price_10m",
        price_30_min_after="price_30m",
    )
    assert mapping.price_10_min_after == "price_10m"
    assert mapping.price_30_min_after == "price_30m"
    assert mapping.price_20_min_after is None  # Not set
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_models.py::test_column_mapping_has_time_interval_fields -v`
Expected: FAIL with "unexpected keyword argument"

**Step 3: Add time interval fields to ColumnMapping**

Add after `mfe_time` field in `src/core/models.py`:

```python
    # Time interval price columns (optional)
    price_10_min_after: str | None = None
    price_20_min_after: str | None = None
    price_30_min_after: str | None = None
    price_60_min_after: str | None = None
    price_90_min_after: str | None = None
    price_120_min_after: str | None = None
    price_150_min_after: str | None = None
    price_180_min_after: str | None = None
    price_240_min_after: str | None = None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_models.py::test_column_mapping_has_time_interval_fields -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/models.py tests/unit/test_models.py
git commit -m "feat(models): add time interval price column mappings to ColumnMapping"
```

---

## Task 2: Add Time Interval Constants

**Files:**
- Modify: `src/core/statistics.py`
- Test: `tests/unit/test_statistics.py`

**Step 1: Write the failing test**

```python
# In tests/unit/test_statistics.py
def test_time_stop_intervals_constant():
    """Test TIME_STOP_INTERVALS constant exists with expected values."""
    from src.core.statistics import TIME_STOP_INTERVALS
    assert TIME_STOP_INTERVALS == [10, 20, 30, 60, 90, 120, 150, 180, 240]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_statistics.py::test_time_stop_intervals_constant -v`
Expected: FAIL with "cannot import name"

**Step 3: Add constant to statistics.py**

Add near SCALING_TARGET_LEVELS (around line 829):

```python
# Time stop intervals in minutes
TIME_STOP_INTERVALS = [10, 20, 30, 60, 90, 120, 150, 180, 240]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_statistics.py::test_time_stop_intervals_constant -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/statistics.py tests/unit/test_statistics.py
git commit -m "feat(statistics): add TIME_STOP_INTERVALS constant"
```

---

## Task 3: Implement calculate_time_statistics_table Function

**Files:**
- Modify: `src/core/statistics.py`
- Test: `tests/unit/test_statistics.py`

**Step 1: Write the failing test**

```python
# In tests/unit/test_statistics.py
def test_calculate_time_statistics_table():
    """Test Time Statistics table calculation."""
    import pandas as pd
    from src.core.statistics import calculate_time_statistics_table
    from src.core.models import ColumnMapping

    df = pd.DataFrame({
        "adjusted_gain_pct": [0.10, -0.05, 0.15, -0.08],
        "change_10_min": [0.02, -0.01, 0.03, -0.02],
        "change_30_min": [0.05, -0.02, 0.08, -0.04],
    })

    mapping = ColumnMapping(
        ticker="ticker", date="date", time="time",
        gain_pct="gain_pct", mae_pct="mae_pct", mfe_pct="mfe_pct",
        price_10_min_after="p10", price_30_min_after="p30",
    )

    result = calculate_time_statistics_table(df, mapping)

    assert len(result) == 2  # Only 2 intervals mapped
    assert "Minutes After Entry" in result.columns
    assert "Avg. Gain %" in result.columns
    assert "Prob. of Profit (Red) %" in result.columns
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_statistics.py::test_calculate_time_statistics_table -v`
Expected: FAIL with "cannot import name"

**Step 3: Implement function**

Add to `src/core/statistics.py`:

```python
def calculate_time_statistics_table(
    df: pd.DataFrame,
    mapping: ColumnMapping,
) -> pd.DataFrame:
    """Calculate Time Statistics table showing gain/loss stats at each interval.

    Args:
        df: Trade data with change_X_min and adjusted_gain_pct columns.
        mapping: Column mapping with price_X_min_after fields.

    Returns:
        DataFrame with rows for each mapped time interval.
    """
    rows = []

    # Map intervals to their change column names
    interval_to_mapping = {
        10: mapping.price_10_min_after,
        20: mapping.price_20_min_after,
        30: mapping.price_30_min_after,
        60: mapping.price_60_min_after,
        90: mapping.price_90_min_after,
        120: mapping.price_120_min_after,
        150: mapping.price_150_min_after,
        180: mapping.price_180_min_after,
        240: mapping.price_240_min_after,
    }

    for interval in TIME_STOP_INTERVALS:
        if interval_to_mapping.get(interval) is None:
            continue

        change_col = f"change_{interval}_min"
        if change_col not in df.columns:
            continue

        row = _calculate_time_statistics_row(df, change_col, interval)
        rows.append(row)

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _calculate_time_statistics_row(
    df: pd.DataFrame,
    change_col: str,
    interval: int,
) -> dict:
    """Calculate statistics for a single time interval."""
    changes = df[change_col]
    final_gains = df["adjusted_gain_pct"]

    # Split into winners/losers at this time
    winners_mask = changes > 0
    losers_mask = changes <= 0

    # Gain/Loss stats (convert to percentage)
    avg_gain = changes[winners_mask].mean() * 100 if winners_mask.any() else None
    median_gain = changes[winners_mask].median() * 100 if winners_mask.any() else None
    avg_loss = changes[losers_mask].mean() * 100 if losers_mask.any() else None
    median_loss = changes[losers_mask].median() * 100 if losers_mask.any() else None

    # Recovery probabilities
    red_trades = df[losers_mask]
    green_trades = df[winners_mask]

    prob_profit_red = (
        (red_trades["adjusted_gain_pct"] > 0).mean() * 100
        if len(red_trades) > 0 else None
    )
    prob_profit_green = (
        (green_trades["adjusted_gain_pct"] > 0).mean() * 100
        if len(green_trades) > 0 else None
    )

    return {
        "Minutes After Entry": f"{interval} Mins",
        "Avg. Gain %": avg_gain,
        "Median Gain %": median_gain,
        "Avg. Loss %": avg_loss,
        "Median Loss %": median_loss,
        "Prob. of Profit (Red) %": prob_profit_red,
        "Prob. of Profit (Green) %": prob_profit_green,
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_statistics.py::test_calculate_time_statistics_table -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/statistics.py tests/unit/test_statistics.py
git commit -m "feat(statistics): add calculate_time_statistics_table function"
```

---

## Task 4: Implement calculate_time_stop_table Function

**Files:**
- Modify: `src/core/statistics.py`
- Test: `tests/unit/test_statistics.py`

**Step 1: Write the failing test**

```python
# In tests/unit/test_statistics.py
def test_calculate_time_stop_table():
    """Test Time Stop table calculation with blended returns."""
    import pandas as pd
    from src.core.statistics import calculate_time_stop_table
    from src.core.models import ColumnMapping

    df = pd.DataFrame({
        "adjusted_gain_pct": [0.10, -0.05, 0.15, -0.08],
        "change_10_min": [0.02, -0.01, 0.03, -0.02],
    })

    mapping = ColumnMapping(
        ticker="ticker", date="date", time="time",
        gain_pct="gain_pct", mae_pct="mae_pct", mfe_pct="mfe_pct",
        price_10_min_after="p10",
    )

    result = calculate_time_stop_table(df, mapping, scale_out_pct=0.5)

    assert len(result) == 1  # Only 1 interval mapped
    assert "Blended Win %" in result.columns
    assert "Full Hold Win %" in result.columns
    assert "Blended EV %" in result.columns
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_statistics.py::test_calculate_time_stop_table -v`
Expected: FAIL with "cannot import name"

**Step 3: Implement function**

Add to `src/core/statistics.py`:

```python
def calculate_time_stop_table(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    scale_out_pct: float,
) -> pd.DataFrame:
    """Calculate Time Stop table comparing blended vs full hold returns.

    Blending logic: If trade is RED at time X, exit scale_out_pct of position
    at that loss. If GREEN, hold 100% to final close.

    Args:
        df: Trade data with change_X_min and adjusted_gain_pct columns.
        mapping: Column mapping with price_X_min_after fields.
        scale_out_pct: Fraction of position to exit if red (0-1).

    Returns:
        DataFrame with rows for each mapped time interval.
    """
    rows = []

    interval_to_mapping = {
        10: mapping.price_10_min_after,
        20: mapping.price_20_min_after,
        30: mapping.price_30_min_after,
        60: mapping.price_60_min_after,
        90: mapping.price_90_min_after,
        120: mapping.price_120_min_after,
        150: mapping.price_150_min_after,
        180: mapping.price_180_min_after,
        240: mapping.price_240_min_after,
    }

    for interval in TIME_STOP_INTERVALS:
        if interval_to_mapping.get(interval) is None:
            continue

        change_col = f"change_{interval}_min"
        if change_col not in df.columns:
            continue

        row = _calculate_time_stop_row(df, change_col, interval, scale_out_pct)
        rows.append(row)

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _calculate_time_stop_row(
    df: pd.DataFrame,
    change_col: str,
    interval: int,
    scale_out_pct: float,
) -> dict:
    """Calculate metrics for a single time stop interval."""
    changes = df[change_col]
    final_gains = df["adjusted_gain_pct"]

    # Calculate blended returns
    # If RED at time X: blend = scale_out * change + (1-scale_out) * final
    # If GREEN at time X: blend = final (no action)
    red_mask = changes <= 0
    blended_returns = final_gains.copy()
    blended_returns[red_mask] = (
        scale_out_pct * changes[red_mask] +
        (1 - scale_out_pct) * final_gains[red_mask]
    )

    # Calculate metrics for both
    blended_metrics = _calculate_return_metrics(blended_returns)
    full_hold_metrics = _calculate_return_metrics(final_gains)

    # Calculate Kelly Stake %
    blended_kelly = (
        blended_metrics["edge_pct"] / blended_metrics["profit_ratio"]
        if blended_metrics["profit_ratio"] and blended_metrics["edge_pct"]
        else None
    )
    full_hold_kelly = (
        full_hold_metrics["edge_pct"] / full_hold_metrics["profit_ratio"]
        if full_hold_metrics["profit_ratio"] and full_hold_metrics["edge_pct"]
        else None
    )

    return {
        "Minutes After Entry": f"{interval} Mins",
        "Blended Win %": blended_metrics["win_pct"],
        "Full Hold Win %": full_hold_metrics["win_pct"],
        "Blended EV %": blended_returns.mean() * 100,
        "Full Hold EV %": final_gains.mean() * 100,
        "Blended Profit Ratio": blended_metrics["profit_ratio"],
        "Full Hold Profit Ratio": full_hold_metrics["profit_ratio"],
        "Blended Edge %": blended_metrics["edge_pct"],
        "Full Hold Edge %": full_hold_metrics["edge_pct"],
        "Blended EG %": blended_metrics["eg_pct"],
        "Full Hold EG %": full_hold_metrics["eg_pct"],
        "Blended Kelly Stake %": blended_kelly,
        "Full Hold Kelly Stake %": full_hold_kelly,
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_statistics.py::test_calculate_time_stop_table -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/statistics.py tests/unit/test_statistics.py
git commit -m "feat(statistics): add calculate_time_stop_table function"
```

---

## Task 5: Compute change_X_min Columns During File Processing

**Files:**
- Modify: `src/core/mapping_worker.py`
- Test: `tests/unit/test_mapping_worker.py`

**Step 1: Write the failing test**

```python
# In tests/unit/test_mapping_worker.py (or create if doesn't exist)
def test_change_columns_computed_from_price_mapping():
    """Test that change_X_min columns are computed when price columns are mapped."""
    import pandas as pd
    from src.core.models import ColumnMapping

    df = pd.DataFrame({
        "trigger_price_unadjusted": [100.0, 200.0],
        "price_10m": [98.0, 204.0],  # 2% gain, -2% loss
        "price_30m": [95.0, 210.0],  # 5% gain, -5% loss
    })

    mapping = ColumnMapping(
        ticker="ticker", date="date", time="time",
        gain_pct="gain_pct", mae_pct="mae_pct", mfe_pct="mfe_pct",
        price_10_min_after="price_10m",
        price_30_min_after="price_30m",
    )

    # Call the helper function that computes these columns
    from src.core.mapping_worker import compute_time_change_columns
    result = compute_time_change_columns(df, mapping)

    assert "change_10_min" in result.columns
    assert "change_30_min" in result.columns
    # (100 - 98) / 100 = 0.02
    assert abs(result["change_10_min"].iloc[0] - 0.02) < 0.001
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_mapping_worker.py::test_change_columns_computed_from_price_mapping -v`
Expected: FAIL with "cannot import name"

**Step 3: Implement helper function**

Add to `src/core/mapping_worker.py`:

```python
def compute_time_change_columns(
    df: pd.DataFrame,
    mapping: ColumnMapping,
) -> pd.DataFrame:
    """Compute change_X_min columns from price_X_min_after mappings.

    Formula: change = (trigger_price - price_X_min) / trigger_price

    Args:
        df: DataFrame with trigger_price_unadjusted column.
        mapping: Column mapping with price_X_min_after fields.

    Returns:
        DataFrame with change_X_min columns added.
    """
    if "trigger_price_unadjusted" not in df.columns:
        return df

    trigger_price = df["trigger_price_unadjusted"]

    interval_mappings = {
        10: mapping.price_10_min_after,
        20: mapping.price_20_min_after,
        30: mapping.price_30_min_after,
        60: mapping.price_60_min_after,
        90: mapping.price_90_min_after,
        120: mapping.price_120_min_after,
        150: mapping.price_150_min_after,
        180: mapping.price_180_min_after,
        240: mapping.price_240_min_after,
    }

    for interval, price_col in interval_mappings.items():
        if price_col and price_col in df.columns:
            change_col = f"change_{interval}_min"
            df[change_col] = (trigger_price - df[price_col]) / trigger_price

    return df
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_mapping_worker.py::test_change_columns_computed_from_price_mapping -v`
Expected: PASS

**Step 5: Integrate into MappingWorker.run() after adjusted_gain_pct computation**

Add after line ~141 in `src/core/mapping_worker.py`:

```python
            # 6. Compute time change columns
            baseline_df = compute_time_change_columns(baseline_df, mapping)
```

**Step 6: Commit**

```bash
git add src/core/mapping_worker.py tests/unit/test_mapping_worker.py
git commit -m "feat(mapping_worker): compute change_X_min columns from price mappings"
```

---

## Task 6: Add Time Stop Sub-Tab UI Widget

**Files:**
- Modify: `src/tabs/statistics_tab.py`
- Test: `tests/unit/test_statistics_tab.py`

**Step 1: Write the failing test**

```python
# In tests/unit/test_statistics_tab.py
def test_has_5_subtabs_including_time_stop(self, app):
    """Test that StatisticsTab has 5 sub-tabs including Time Stop."""
    app_state = AppState()
    tab = StatisticsTab(app_state)
    assert tab._tab_widget.count() == 5
    names = [tab._tab_widget.tabText(i) for i in range(5)]
    assert "Time Stop" in names
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_statistics_tab.py::TestStatisticsTab::test_has_5_subtabs_including_time_stop -v`
Expected: FAIL with assertion (currently 4 tabs)

**Step 3: Create _create_time_stop_widget method**

Add to `src/tabs/statistics_tab.py` after `_create_scaling_widget`:

```python
def _create_time_stop_widget(self) -> QWidget:
    """Create Time Stop sub-tab with statistics and stop tables."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
    layout.setSpacing(Spacing.MD)

    # Scale Out control row
    control_row = QHBoxLayout()
    control_row.setSpacing(Spacing.SM)

    scale_out_label = QLabel("Scale Out:")
    scale_out_label.setStyleSheet(
        f"""
        QLabel {{
            color: {Colors.TEXT_PRIMARY};
            font-family: '{Fonts.UI}';
            font-size: 13px;
        }}
    """
    )
    control_row.addWidget(scale_out_label)

    self._time_stop_scale_spin = QSpinBox()
    self._time_stop_scale_spin.setRange(0, 100)
    self._time_stop_scale_spin.setValue(50)
    self._time_stop_scale_spin.setSingleStep(10)
    self._time_stop_scale_spin.setSuffix("%")
    self._time_stop_scale_spin.setStyleSheet(
        f"""
        QSpinBox {{
            background-color: {Colors.BG_ELEVATED};
            color: {Colors.TEXT_PRIMARY};
            font-family: '{Fonts.DATA}';
            padding: 6px 12px;
            border: 1px solid {Colors.BG_BORDER};
            border-radius: 4px;
        }}
        QSpinBox:focus {{
            border-color: {Colors.SIGNAL_CYAN};
        }}
    """
    )
    control_row.addWidget(self._time_stop_scale_spin)

    # Export button
    self._time_stop_export_btn = QPushButton("Export")
    self._time_stop_export_btn.setStyleSheet(
        f"""
        QPushButton {{
            background-color: {Colors.BG_ELEVATED};
            color: {Colors.TEXT_PRIMARY};
            font-family: '{Fonts.UI}';
            padding: 6px 12px;
            border: 1px solid {Colors.BG_BORDER};
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {Colors.BG_BORDER};
        }}
    """
    )
    self._time_stop_export_btn.clicked.connect(self._on_time_stop_export_clicked)
    control_row.addWidget(self._time_stop_export_btn)
    control_row.addStretch()

    layout.addLayout(control_row)

    # Time Statistics table
    stats_label = QLabel("Time Statistics")
    stats_label.setStyleSheet(
        f"""
        QLabel {{
            color: {Colors.TEXT_PRIMARY};
            font-family: '{Fonts.UI}';
            font-size: 14px;
            font-weight: 600;
        }}
    """
    )
    layout.addWidget(stats_label)

    self._time_stats_table = self._create_table()
    layout.addWidget(self._time_stats_table)

    # Spacer
    layout.addSpacing(Spacing.LG)

    # Time Stop table
    stop_label = QLabel("Time Stop")
    stop_label.setStyleSheet(
        f"""
        QLabel {{
            color: {Colors.TEXT_PRIMARY};
            font-family: '{Fonts.UI}';
            font-size: 14px;
            font-weight: 600;
        }}
    """
    )
    layout.addWidget(stop_label)

    self._time_stop_table = self._create_table()
    layout.addWidget(self._time_stop_table)

    # Message for missing columns
    self._time_stop_msg = QLabel("Time interval price columns not mapped")
    self._time_stop_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self._time_stop_msg.setStyleSheet(
        f"""
        QLabel {{
            color: {Colors.TEXT_SECONDARY};
            font-family: '{Fonts.UI}';
            font-size: 14px;
            padding: 40px;
        }}
    """
    )
    self._time_stop_msg.hide()
    layout.addWidget(self._time_stop_msg)

    return widget
```

**Step 4: Add tab to _setup_ui**

In `_setup_ui`, add after the Profit/Loss Chance tab:

```python
self._tab_widget.addTab(self._create_time_stop_widget(), "Time Stop")
```

**Step 5: Update test_has_4_subtabs test**

Update existing test to expect 5 tabs and include "Time Stop".

**Step 6: Run tests to verify**

Run: `pytest tests/unit/test_statistics_tab.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add src/tabs/statistics_tab.py tests/unit/test_statistics_tab.py
git commit -m "feat(statistics_tab): add Time Stop sub-tab UI widget"
```

---

## Task 7: Wire Up Time Stop Table Refresh Logic

**Files:**
- Modify: `src/tabs/statistics_tab.py`
- Test: `tests/integration/test_statistics_tab.py`

**Step 1: Add _has_time_interval_columns helper**

```python
def _has_time_interval_columns(self, df: pd.DataFrame | None = None) -> bool:
    """Check if any time interval price columns are mapped and computed."""
    mapping = self._app_state.column_mapping
    if mapping is None:
        return False

    if df is None:
        df = self._get_current_df()
    if df is None or df.empty:
        return False

    # Check if any change_X_min columns exist
    for interval in [10, 20, 30, 60, 90, 120, 150, 180, 240]:
        if f"change_{interval}_min" in df.columns:
            return True
    return False
```

**Step 2: Add _refresh_time_stop_tables method**

```python
def _refresh_time_stop_tables(self) -> None:
    """Refresh Time Statistics and Time Stop tables."""
    if not self._app_state.column_mapping:
        return

    df = self._get_current_df()
    if df is None or df.empty:
        return

    if not self._has_time_interval_columns(df):
        self._time_stats_table.hide()
        self._time_stop_table.hide()
        self._time_stop_msg.show()
        return

    self._time_stop_msg.hide()
    self._time_stats_table.show()
    self._time_stop_table.show()

    mapping = self._app_state.column_mapping

    try:
        # Time Statistics table
        from src.core.statistics import calculate_time_statistics_table
        stats_df = calculate_time_statistics_table(df, mapping)
        self._time_stats_table.clear()
        self._time_stats_table.setRowCount(0)
        self._time_stats_table.setColumnCount(0)
        self._populate_table(self._time_stats_table, stats_df)

        # Time Stop table
        from src.core.statistics import calculate_time_stop_table
        scale_out_pct = self._time_stop_scale_spin.value() / 100.0
        stop_df = calculate_time_stop_table(df, mapping, scale_out_pct)
        self._time_stop_table.clear()
        self._time_stop_table.setRowCount(0)
        self._time_stop_table.setColumnCount(0)
        self._populate_table(self._time_stop_table, stop_df)
    except Exception as e:
        logger.warning(f"Error refreshing Time Stop tables: {e}")
```

**Step 3: Connect signals in _connect_signals**

```python
self._time_stop_scale_spin.valueChanged.connect(self._on_time_stop_scale_changed)
```

**Step 4: Add handler**

```python
def _on_time_stop_scale_changed(self) -> None:
    """Handle Time Stop scale out spinbox change."""
    self._refresh_time_stop_tables()
```

**Step 5: Call _refresh_time_stop_tables from _update_all_tables**

**Step 6: Run integration tests**

Run: `pytest tests/integration/test_statistics_tab.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add src/tabs/statistics_tab.py tests/integration/test_statistics_tab.py
git commit -m "feat(statistics_tab): wire up Time Stop table refresh logic"
```

---

## Task 8: Add Time Stop Export Functionality

**Files:**
- Modify: `src/tabs/statistics_tab.py`

**Step 1: Implement _on_time_stop_export_clicked**

```python
def _on_time_stop_export_clicked(self) -> None:
    """Export Time Statistics and Time Stop tables to CSV."""
    from datetime import datetime
    from PyQt6.QtWidgets import QFileDialog

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_name = f"time_stop_export_{timestamp}.csv"

    file_path, _ = QFileDialog.getSaveFileName(
        self, "Export Time Stop Tables", default_name, "CSV Files (*.csv)"
    )

    if not file_path:
        return

    try:
        stats_df = self._table_to_dataframe(self._time_stats_table)
        stop_df = self._table_to_dataframe(self._time_stop_table)

        scale_out = self._time_stop_scale_spin.value()

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            f.write("# Time Statistics\n")
            stats_df.to_csv(f, index=False)
            f.write(f"\n# Time Stop (Scale Out: {scale_out}%)\n")
            stop_df.to_csv(f, index=False)

    except Exception as e:
        logger.error(f"Export failed: {e}")
```

**Step 2: Commit**

```bash
git add src/tabs/statistics_tab.py
git commit -m "feat(statistics_tab): add Time Stop export functionality"
```

---

## Task 9: Add Column Mapping UI for Time Interval Prices

**Files:**
- Modify: `src/tabs/data_input.py`

**Step 1: Add combo boxes for time interval columns**

In the column mapping section, add 9 new optional combo boxes for:
- price_10_min_after, price_20_min_after, price_30_min_after
- price_60_min_after, price_90_min_after, price_120_min_after
- price_150_min_after, price_180_min_after, price_240_min_after

Follow the existing pattern used for mae_time and mfe_time.

**Step 2: Update _get_column_mapping to include new fields**

**Step 3: Test manually with sample data**

**Step 4: Commit**

```bash
git add src/tabs/data_input.py
git commit -m "feat(data_input): add column mapping UI for time interval prices"
```

---

## Task 10: Final Integration Testing

**Files:**
- Test all integration points

**Step 1: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

**Step 2: Manual testing with real data**

1. Load trade data with price_X_min_after columns
2. Map the columns in Data Input tab
3. Navigate to Statistics > Time Stop tab
4. Verify Time Statistics table shows correct data
5. Verify Time Stop table shows blended vs full hold comparison
6. Test scale out spinbox updates table
7. Test export functionality

**Step 3: Final commit**

```bash
git add .
git commit -m "feat: complete Time Stop tab implementation"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Add column mapping fields | models.py |
| 2 | Add TIME_STOP_INTERVALS constant | statistics.py |
| 3 | Implement calculate_time_statistics_table | statistics.py |
| 4 | Implement calculate_time_stop_table | statistics.py |
| 5 | Compute change_X_min columns | mapping_worker.py |
| 6 | Create Time Stop sub-tab UI | statistics_tab.py |
| 7 | Wire up table refresh logic | statistics_tab.py |
| 8 | Add export functionality | statistics_tab.py |
| 9 | Add column mapping UI | data_input.py |
| 10 | Integration testing | all |
