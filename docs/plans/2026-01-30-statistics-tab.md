# Statistics Tab Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Statistics tab with 5 analytical tables for trade analysis (MAE Before Win, MFE Before Loss, Stop Loss, Offset, Scaling).

**Architecture:** New `statistics_tab.py` with QTabWidget sub-tabs, backed by pure calculation functions in `statistics.py`. Tab subscribes to app_state signals for data updates.

**Tech Stack:** PyQt6, pandas, numpy, existing Observatory theme

---

## Task 1: Add mfe_pct to ColumnMapping

**Files:**
- Modify: `src/core/models.py`
- Test: `tests/unit/test_column_mapping.py`

**Step 1: Write failing test**

```python
# tests/unit/test_column_mapping.py
def test_column_mapping_requires_mfe_pct():
    """Test that ColumnMapping requires mfe_pct field."""
    mapping = ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
    )
    assert mapping.mfe_pct == "mfe_pct"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_column_mapping.py::test_column_mapping_requires_mfe_pct -v`
Expected: FAIL with "unexpected keyword argument 'mfe_pct'"

**Step 3: Add mfe_pct field to ColumnMapping**

In `src/core/models.py`, add `mfe_pct: str` field to the ColumnMapping dataclass after `mae_pct`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_column_mapping.py::test_column_mapping_requires_mfe_pct -v`
Expected: PASS

**Step 5: Fix existing tests that instantiate ColumnMapping**

Search for all ColumnMapping instantiations in tests and add `mfe_pct="mfe_pct"` parameter.

Run: `pytest tests/ -v`
Expected: All tests pass

**Step 6: Commit**

```bash
git add src/core/models.py tests/
git commit -m "feat: add mfe_pct as required field in ColumnMapping"
```

---

## Task 2: Create statistics calculation module skeleton

**Files:**
- Create: `src/core/statistics.py`
- Test: `tests/unit/test_statistics.py`

**Step 1: Write failing import test**

```python
# tests/unit/test_statistics.py
def test_statistics_module_imports():
    """Test that statistics module can be imported."""
    from src.core.statistics import (
        calculate_mae_before_win,
        calculate_mfe_before_loss,
        calculate_stop_loss_table,
        calculate_offset_table,
        calculate_scaling_table,
    )
    assert callable(calculate_mae_before_win)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_statistics.py::test_statistics_module_imports -v`
Expected: FAIL with "No module named 'src.core.statistics'"

**Step 3: Create skeleton module**

```python
# src/core/statistics.py
"""Statistics calculations for trade analysis tables."""

import pandas as pd
from src.core.models import ColumnMapping


def calculate_mae_before_win(df: pd.DataFrame, mapping: ColumnMapping) -> pd.DataFrame:
    """Calculate MAE probabilities for winning trades by gain bucket."""
    raise NotImplementedError


def calculate_mfe_before_loss(df: pd.DataFrame, mapping: ColumnMapping) -> pd.DataFrame:
    """Calculate MFE probabilities for losing trades by loss bucket."""
    raise NotImplementedError


def calculate_stop_loss_table(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    efficiency: float,
) -> pd.DataFrame:
    """Simulate stop loss levels and calculate metrics."""
    raise NotImplementedError


def calculate_offset_table(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    stop_loss: float,
    efficiency: float,
) -> pd.DataFrame:
    """Simulate entry offsets with recalculated MAE/MFE and returns."""
    raise NotImplementedError


def calculate_scaling_table(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    scale_out_pct: float,
) -> pd.DataFrame:
    """Compare blended partial-profit returns vs full hold."""
    raise NotImplementedError
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_statistics.py::test_statistics_module_imports -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/statistics.py tests/unit/test_statistics.py
git commit -m "feat: add statistics module skeleton"
```

---

## Task 3: Implement calculate_mae_before_win

**Files:**
- Modify: `src/core/statistics.py`
- Modify: `tests/unit/test_statistics.py`

**Step 1: Write failing test**

```python
def test_calculate_mae_before_win_basic():
    """Test MAE before win calculation with basic data."""
    df = pd.DataFrame({
        "gain_pct": [0.05, 0.15, 0.25, 0.08, -0.10],  # 4 winners, 1 loser
        "adjusted_gain_pct": [0.05, 0.15, 0.25, 0.08, -0.10],
        "mae_pct": [3.0, 8.0, 12.0, 6.0, 15.0],  # MAE in percentage points
    })
    mapping = ColumnMapping(
        ticker="ticker", date="date", time="time",
        gain_pct="gain_pct", mae_pct="mae_pct", mfe_pct="mfe_pct"
    )

    result = calculate_mae_before_win(df, mapping)

    # Should have 7 rows: Overall + 6 buckets
    assert len(result) == 7
    # Overall row: 4 winners
    assert result.iloc[0]["# of Plays"] == 4
    # Check column names exist
    assert "% Gain per Trade" in result.columns
    assert ">5% MAE Probability" in result.columns
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_statistics.py::test_calculate_mae_before_win_basic -v`
Expected: FAIL with "NotImplementedError"

**Step 3: Implement calculate_mae_before_win**

```python
def calculate_mae_before_win(df: pd.DataFrame, mapping: ColumnMapping) -> pd.DataFrame:
    """Calculate MAE probabilities for winning trades by gain bucket."""
    # Filter to winners only
    winners = df[df["adjusted_gain_pct"] > 0].copy()
    total_winners = len(winners)

    if total_winners == 0:
        return _empty_mae_table()

    # Convert adjusted_gain_pct from decimal to percentage points for bucketing
    winners["gain_pct_display"] = winners["adjusted_gain_pct"] * 100

    # Define buckets
    buckets = [
        ("Overall", lambda x: True),
        (">0%", lambda x: 0 < x <= 10),
        (">10%", lambda x: 10 < x <= 20),
        (">20%", lambda x: 20 < x <= 30),
        (">30%", lambda x: 30 < x <= 40),
        (">40%", lambda x: 40 < x <= 50),
        (">50%", lambda x: x > 50),
    ]

    mae_thresholds = [5, 10, 15, 20]

    rows = []
    for label, filter_fn in buckets:
        if label == "Overall":
            bucket_df = winners
        else:
            bucket_df = winners[winners["gain_pct_display"].apply(filter_fn)]

        count = len(bucket_df)
        if count == 0:
            row = {
                "% Gain per Trade": label,
                "# of Plays": 0,
                "% of Total": 0.0,
                "Avg %": None,
                "Median %": None,
            }
            for t in mae_thresholds:
                row[f">{t}% MAE Probability"] = None
        else:
            row = {
                "% Gain per Trade": label,
                "# of Plays": count,
                "% of Total": count / total_winners * 100,
                "Avg %": bucket_df["gain_pct_display"].mean(),
                "Median %": bucket_df["gain_pct_display"].median(),
            }
            for t in mae_thresholds:
                mae_count = (bucket_df[mapping.mae_pct] > t).sum()
                row[f">{t}% MAE Probability"] = mae_count / total_winners * 100

        rows.append(row)

    return pd.DataFrame(rows)


def _empty_mae_table() -> pd.DataFrame:
    """Return empty MAE table structure."""
    columns = [
        "% Gain per Trade", "# of Plays", "% of Total", "Avg %", "Median %",
        ">5% MAE Probability", ">10% MAE Probability",
        ">15% MAE Probability", ">20% MAE Probability"
    ]
    return pd.DataFrame(columns=columns)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_statistics.py::test_calculate_mae_before_win_basic -v`
Expected: PASS

**Step 5: Add edge case tests**

```python
def test_calculate_mae_before_win_empty_data():
    """Test MAE calculation with no winners."""
    df = pd.DataFrame({
        "gain_pct": [-0.05, -0.10],
        "adjusted_gain_pct": [-0.05, -0.10],
        "mae_pct": [5.0, 10.0],
    })
    mapping = ColumnMapping(...)
    result = calculate_mae_before_win(df, mapping)
    assert len(result) == 0  # Empty table
```

**Step 6: Run all statistics tests**

Run: `pytest tests/unit/test_statistics.py -v`
Expected: All pass

**Step 7: Commit**

```bash
git add src/core/statistics.py tests/unit/test_statistics.py
git commit -m "feat: implement calculate_mae_before_win"
```

---

## Task 4: Implement calculate_mfe_before_loss

**Files:**
- Modify: `src/core/statistics.py`
- Modify: `tests/unit/test_statistics.py`

**Step 1: Write failing test**

```python
def test_calculate_mfe_before_loss_basic():
    """Test MFE before loss calculation with basic data."""
    df = pd.DataFrame({
        "gain_pct": [-0.05, -0.15, -0.25, 0.10],  # 3 losers, 1 winner
        "adjusted_gain_pct": [-0.05, -0.15, -0.25, 0.10],
        "mfe_pct": [8.0, 12.0, 5.0, 20.0],  # MFE in percentage points
    })
    mapping = ColumnMapping(...)

    result = calculate_mfe_before_loss(df, mapping)

    # Should have 7 rows: Overall + 6 buckets
    assert len(result) == 7
    # Overall row: 3 losers
    assert result.iloc[0]["# of Plays"] == 3
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_statistics.py::test_calculate_mfe_before_loss_basic -v`
Expected: FAIL with "NotImplementedError"

**Step 3: Implement calculate_mfe_before_loss**

Similar structure to calculate_mae_before_win but:
- Filter to losers (`adjusted_gain_pct < 0`)
- Use absolute value for bucketing
- Use `mfe_pct` column for probability calculations

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_statistics.py::test_calculate_mfe_before_loss_basic -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/statistics.py tests/unit/test_statistics.py
git commit -m "feat: implement calculate_mfe_before_loss"
```

---

## Task 5: Implement calculate_stop_loss_table

**Files:**
- Modify: `src/core/statistics.py`
- Modify: `tests/unit/test_statistics.py`

**Step 1: Write failing test**

```python
def test_calculate_stop_loss_table_basic():
    """Test stop loss table calculation."""
    df = pd.DataFrame({
        "gain_pct": [0.10, -0.05, 0.20, -0.15],
        "mae_pct": [5.0, 25.0, 8.0, 35.0],  # 2 would be stopped at 20%
    })
    mapping = ColumnMapping(...)

    result = calculate_stop_loss_table(df, mapping, efficiency=1.0)

    # Should have 10 rows (10% to 100%)
    assert len(result) == 10
    assert "Stop %" in result.columns
    assert "Win %" in result.columns
    assert "EG %" in result.columns
    # At 20% stop, 2 trades would be stopped
    row_20 = result[result["Stop %"] == 20].iloc[0]
    assert row_20["Max Loss %"] == 50.0  # 2/4 = 50%
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_statistics.py::test_calculate_stop_loss_table_basic -v`
Expected: FAIL with "NotImplementedError"

**Step 3: Implement calculate_stop_loss_table**

Key logic:
1. For each stop level (10-100%):
2. If `mae_pct >= stop_level`: trade is stopped (return = -stop_level * efficiency)
3. Else: use original gain_pct
4. Calculate win%, profit_ratio, edge%, EG%, max_loss%, kelly fractions

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_statistics.py::test_calculate_stop_loss_table_basic -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/statistics.py tests/unit/test_statistics.py
git commit -m "feat: implement calculate_stop_loss_table"
```

---

## Task 6: Implement calculate_offset_table

**Files:**
- Modify: `src/core/statistics.py`
- Modify: `tests/unit/test_statistics.py`

**Step 1: Write failing test**

```python
def test_calculate_offset_table_basic():
    """Test offset table for short trades."""
    df = pd.DataFrame({
        "gain_pct": [0.10, -0.05, 0.15],
        "mae_pct": [5.0, 30.0, 10.0],  # Price rose by these amounts
        "mfe_pct": [15.0, 8.0, 25.0],  # Price dropped by these amounts
    })
    mapping = ColumnMapping(...)

    result = calculate_offset_table(df, mapping, stop_loss=20.0, efficiency=1.0)

    # Should have 7 rows (-20% to +40%)
    assert len(result) == 7
    assert "Offset %" in result.columns
    assert "# of Trades" in result.columns
    # At +20% offset, only trades with mae_pct >= 20 qualify
    row_plus20 = result[result["Offset %"] == 20].iloc[0]
    assert row_plus20["# of Trades"] == 1  # Only the trade with 30% MAE qualifies
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_statistics.py::test_calculate_offset_table_basic -v`
Expected: FAIL with "NotImplementedError"

**Step 3: Implement calculate_offset_table**

Key logic for short trades:
1. For each offset level (-20% to +40%):
2. Filter qualifying trades:
   - Negative offset: `mfe_pct >= abs(offset)` (price dropped enough)
   - Positive offset: `mae_pct >= offset` (price rose enough)
3. Recalculate MAE/MFE from new entry point
4. Recalculate returns with stop-loss and efficiency
5. Calculate all metrics

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_statistics.py::test_calculate_offset_table_basic -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/statistics.py tests/unit/test_statistics.py
git commit -m "feat: implement calculate_offset_table"
```

---

## Task 7: Implement calculate_scaling_table

**Files:**
- Modify: `src/core/statistics.py`
- Modify: `tests/unit/test_statistics.py`

**Step 1: Write failing test**

```python
def test_calculate_scaling_table_basic():
    """Test scaling table calculation."""
    df = pd.DataFrame({
        "gain_pct": [0.10, 0.20, -0.05],  # Full hold returns
        "adjusted_gain_pct": [0.10, 0.20, -0.05],
        "mfe_pct": [15.0, 8.0, 3.0],  # MFE reached during trade
    })
    mapping = ColumnMapping(...)

    result = calculate_scaling_table(df, mapping, scale_out_pct=0.5)

    # Should have 8 rows (5% to 40%)
    assert len(result) == 8
    assert "Partial Target %" in result.columns
    assert "% of Trades" in result.columns
    # At 10% target: 1 trade qualifies (15% MFE)
    row_10 = result[result["Partial Target %"] == 10].iloc[0]
    assert row_10["% of Trades"] == pytest.approx(33.33, rel=0.01)  # 1/3
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_statistics.py::test_calculate_scaling_table_basic -v`
Expected: FAIL with "NotImplementedError"

**Step 3: Implement calculate_scaling_table**

Key logic:
1. For each target level (5% to 40%):
2. For each trade:
   - If `mfe_pct >= target`: `blended = scale_out * (target/100) + (1-scale_out) * full_hold`
   - Else: `blended = full_hold`
3. Calculate metrics for both blended and full hold

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_statistics.py::test_calculate_scaling_table_basic -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/statistics.py tests/unit/test_statistics.py
git commit -m "feat: implement calculate_scaling_table"
```

---

## Task 8: Create StatisticsTab UI skeleton

**Files:**
- Create: `src/tabs/statistics_tab.py`
- Test: `tests/unit/test_statistics_tab.py`

**Step 1: Write failing test**

```python
# tests/unit/test_statistics_tab.py
import pytest
from PyQt6.QtWidgets import QApplication
from src.tabs.statistics_tab import StatisticsTab
from src.core.app_state import AppState


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance() or QApplication([])
    yield app


def test_statistics_tab_creates():
    """Test that StatisticsTab can be instantiated."""
    app_state = AppState()
    tab = StatisticsTab(app_state)
    assert tab is not None


def test_statistics_tab_has_5_subtabs(app):
    """Test that StatisticsTab has 5 sub-tabs."""
    app_state = AppState()
    tab = StatisticsTab(app_state)
    assert tab._tab_widget.count() == 5
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_statistics_tab.py -v`
Expected: FAIL with "No module named 'src.tabs.statistics_tab'"

**Step 3: Create skeleton tab**

```python
# src/tabs/statistics_tab.py
"""Statistics tab with 5 analytical tables for trade analysis."""

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QTabWidget,
    QTableWidget,
)

from src.core.app_state import AppState
from src.ui.constants import Colors


class StatisticsTab(QWidget):
    """Tab displaying 5 statistics tables as sub-tabs."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._app_state = app_state
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the tab UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Sub-tabs
        self._tab_widget = QTabWidget()
        self._tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                background-color: {Colors.BG_SURFACE};
                border: none;
            }}
            QTabBar::tab {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_SECONDARY};
                padding: 8px 16px;
            }}
            QTabBar::tab:selected {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)

        # Create 5 sub-tabs
        self._mae_table = self._create_table()
        self._mfe_table = self._create_table()
        self._stop_loss_table = self._create_table()
        self._offset_table = self._create_table()
        self._scaling_widget = self._create_scaling_widget()

        self._tab_widget.addTab(self._mae_table, "MAE Before Win")
        self._tab_widget.addTab(self._mfe_table, "MFE Before Loss")
        self._tab_widget.addTab(self._stop_loss_table, "Stop Loss")
        self._tab_widget.addTab(self._offset_table, "Offset")
        self._tab_widget.addTab(self._scaling_widget, "Scaling")

        layout.addWidget(self._tab_widget)

    def _create_table(self) -> QTableWidget:
        """Create a styled table widget."""
        table = QTableWidget()
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                gridline-color: {Colors.BG_BORDER};
                border: none;
            }}
        """)
        return table

    def _create_scaling_widget(self) -> QWidget:
        """Create scaling sub-tab with spinbox control."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        # TODO: Add scale out spinbox and table
        return widget

    def _connect_signals(self) -> None:
        """Connect app state signals."""
        pass  # TODO: Connect to data change signals
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_statistics_tab.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tabs/statistics_tab.py tests/unit/test_statistics_tab.py
git commit -m "feat: add StatisticsTab UI skeleton with 5 sub-tabs"
```

---

## Task 9: Add Statistics tab to DockManager

**Files:**
- Modify: `src/ui/dock_manager.py`
- Modify: `tests/ui/test_main_window_docking.py`
- Modify: `tests/widget/test_main_window.py`

**Step 1: Update expected dock count in tests**

Update tests to expect 12 docks (was 11, adding Statistics).

**Step 2: Run tests to verify they fail**

Run: `pytest tests/ui/test_main_window_docking.py tests/widget/test_main_window.py -v`
Expected: FAIL with count mismatch

**Step 3: Add Statistics tab to DockManager**

In `src/ui/dock_manager.py`:
1. Import StatisticsTab
2. Add to `_create_docks()` method
3. Add to dock list

**Step 4: Run tests to verify they pass**

Run: `pytest tests/ui/test_main_window_docking.py tests/widget/test_main_window.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/ui/dock_manager.py tests/
git commit -m "feat: add Statistics tab to DockManager"
```

---

## Task 10: Wire up StatisticsTab to AppState signals

**Files:**
- Modify: `src/tabs/statistics_tab.py`
- Modify: `tests/unit/test_statistics_tab.py`

**Step 1: Write failing test**

```python
def test_statistics_tab_updates_on_data_change(app, qtbot):
    """Test that tables update when baseline data changes."""
    app_state = AppState()
    tab = StatisticsTab(app_state)
    qtbot.addWidget(tab)

    # Set test data
    df = pd.DataFrame({...})
    mapping = ColumnMapping(...)

    app_state.set_baseline_df(df, mapping)

    # Verify tables populated
    assert tab._mae_table.rowCount() > 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_statistics_tab.py::test_statistics_tab_updates_on_data_change -v`
Expected: FAIL (tables not populated)

**Step 3: Implement signal connections**

Connect to `app_state.baseline_df_changed` and call calculation functions, populate tables.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_statistics_tab.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tabs/statistics_tab.py tests/unit/test_statistics_tab.py
git commit -m "feat: wire StatisticsTab to AppState data signals"
```

---

## Task 11: Implement table styling and conditional formatting

**Files:**
- Modify: `src/tabs/statistics_tab.py`
- Modify: `tests/unit/test_statistics_tab.py`

**Step 1: Write failing test**

```python
def test_statistics_tab_positive_cell_styling(app, qtbot):
    """Test that positive values get cyan styling."""
    # Setup with data that has positive EG%
    # Check cell background color
    pass
```

**Step 2: Run test to verify it fails**

**Step 3: Implement conditional cell styling**

Add helper methods:
- `_style_positive_cell(item)` - Cyan tint for positive metrics
- `_style_negative_cell(item)` - Coral tint for negative metrics
- `_highlight_optimal_row(table)` - Highlight best EG% row

**Step 4: Run test to verify it passes**

**Step 5: Commit**

```bash
git add src/tabs/statistics_tab.py tests/unit/test_statistics_tab.py
git commit -m "feat: add conditional cell styling to statistics tables"
```

---

## Task 12: Implement Scale Out spinbox for Scaling sub-tab

**Files:**
- Modify: `src/tabs/statistics_tab.py`
- Modify: `tests/unit/test_statistics_tab.py`

**Step 1: Write failing test**

```python
def test_scaling_subtab_has_spinbox(app, qtbot):
    """Test that Scaling sub-tab has Scale Out spinbox."""
    app_state = AppState()
    tab = StatisticsTab(app_state)

    scaling_widget = tab._scaling_widget
    spinbox = scaling_widget.findChild(QSpinBox)

    assert spinbox is not None
    assert spinbox.minimum() == 10
    assert spinbox.maximum() == 90
    assert spinbox.value() == 50  # Default
```

**Step 2: Run test to verify it fails**

**Step 3: Implement Scale Out spinbox**

Add spinbox above scaling table with 10-90% range, 10% step, 50% default.

**Step 4: Run test to verify it passes**

**Step 5: Commit**

```bash
git add src/tabs/statistics_tab.py tests/unit/test_statistics_tab.py
git commit -m "feat: add Scale Out spinbox to Scaling sub-tab"
```

---

## Task 13: Handle empty states and missing columns

**Files:**
- Modify: `src/tabs/statistics_tab.py`
- Modify: `tests/unit/test_statistics_tab.py`

**Step 1: Write failing tests**

```python
def test_statistics_tab_shows_empty_message_no_data(app, qtbot):
    """Test empty state message when no data loaded."""
    app_state = AppState()
    tab = StatisticsTab(app_state)
    qtbot.addWidget(tab)

    # Should show empty message
    assert "Load trade data" in tab._get_visible_text()


def test_statistics_tab_disables_mfe_tables_when_missing(app, qtbot):
    """Test MFE-dependent tables disabled when mfe_pct missing."""
    # Load data without mfe_pct column
    # Check MFE Before Loss and Scaling tabs are disabled
    pass
```

**Step 2: Implement empty state handling**

Add:
- Empty state label when no data
- Disable MFE-dependent tabs when `mfe_pct` column missing
- Disable MAE-dependent tabs when `mae_pct` column missing

**Step 3: Run all tests**

Run: `pytest tests/unit/test_statistics_tab.py -v`
Expected: All pass

**Step 4: Commit**

```bash
git add src/tabs/statistics_tab.py tests/unit/test_statistics_tab.py
git commit -m "feat: handle empty states and missing columns in StatisticsTab"
```

---

## Task 14: Final integration test

**Files:**
- Create: `tests/integration/test_statistics_tab.py`

**Step 1: Write integration test**

```python
def test_statistics_tab_full_workflow(app, qtbot, sample_data):
    """Test complete workflow: load data, apply filter, verify updates."""
    app_state = AppState()
    tab = StatisticsTab(app_state)
    qtbot.addWidget(tab)

    # Load baseline data
    app_state.set_baseline_df(sample_data, mapping)

    # Verify all 5 tables populated
    assert tab._mae_table.rowCount() == 7
    assert tab._mfe_table.rowCount() == 7
    assert tab._stop_loss_table.rowCount() == 10
    assert tab._offset_table.rowCount() == 7
    assert tab._scaling_table.rowCount() == 8

    # Apply filter
    filtered_df = sample_data[sample_data["gain_pct"] > 0]
    app_state.set_filtered_df(filtered_df)

    # Verify tables updated with filtered data
    # (check counts changed)
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/integration/test_statistics_tab.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/integration/test_statistics_tab.py
git commit -m "test: add integration test for Statistics tab"
```

---

## Task 15: Run full test suite and cleanup

**Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: All pass (except performance benchmarks)

**Step 2: Check for any TODO comments**

Run: `grep -r "TODO" src/tabs/statistics_tab.py src/core/statistics.py`
Expected: No TODOs remaining

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete Statistics tab implementation"
```

---

## Summary

| Task | Description | Estimated Steps |
|------|-------------|-----------------|
| 1 | Add mfe_pct to ColumnMapping | 6 |
| 2 | Create statistics module skeleton | 5 |
| 3 | Implement calculate_mae_before_win | 7 |
| 4 | Implement calculate_mfe_before_loss | 5 |
| 5 | Implement calculate_stop_loss_table | 5 |
| 6 | Implement calculate_offset_table | 5 |
| 7 | Implement calculate_scaling_table | 5 |
| 8 | Create StatisticsTab UI skeleton | 5 |
| 9 | Add Statistics tab to DockManager | 5 |
| 10 | Wire up to AppState signals | 5 |
| 11 | Implement table styling | 5 |
| 12 | Implement Scale Out spinbox | 5 |
| 13 | Handle empty states | 5 |
| 14 | Integration test | 3 |
| 15 | Final cleanup | 3 |
