# Profit/Loss Chance Tables Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a new "Profit/Loss Chance" sub-tab to the Statistics tab with two tables analyzing trade probabilities based on MFE and MAE thresholds.

**Architecture:** New calculation functions in `src/core/statistics.py` compute bucket metrics for 8 fixed thresholds (5%-40%). The Statistics tab gets a new sub-tab with two stacked tables following the existing Stop Loss/Offset pattern. Tables use existing gradient styling and export infrastructure.

**Tech Stack:** Python, pandas, PyQt6, existing Statistics tab infrastructure

---

### Task 1: Add Profit Chance Table Calculation Function

**Files:**
- Modify: `src/core/statistics.py`
- Test: `tests/unit/test_statistics.py`

**Step 1: Write the failing test**

Add to `tests/unit/test_statistics.py`:

```python
class TestCalculateProfitChanceTable:
    """Tests for calculate_profit_chance_table function."""

    def test_basic_data(self, sample_mapping, default_adjustment_params):
        """Test profit chance table with basic data."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, 0.05, -0.08, 0.25],  # 3 win, 1 loss
                "mae_pct": [3.0, 5.0, 15.0, 4.0],  # MAE values
                "mfe_pct": [15.0, 8.0, 3.0, 30.0],  # MFE values
            }
        )
        result = calculate_profit_chance_table(df, sample_mapping, default_adjustment_params)

        assert len(result) == 8  # 8 buckets: 5%, 10%, 15%, 20%, 25%, 30%, 35%, 40%
        assert "Profit Reached %" in result.columns
        assert "Chance of Next %" in result.columns
        assert "Chance of Max Loss %" in result.columns
        assert "Win %" in result.columns
        assert "Profit Ratio" in result.columns
        assert "Edge %" in result.columns
        assert "EG %" in result.columns
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_statistics.py::TestCalculateProfitChanceTable::test_basic_data -v`
Expected: FAIL with "cannot import name 'calculate_profit_chance_table'"

**Step 3: Write minimal implementation**

Add to `src/core/statistics.py`:

```python
# Add near top with other constants
PROFIT_LOSS_BUCKETS = [5, 10, 15, 20, 25, 30, 35, 40]


def calculate_profit_chance_table(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    adjustment_params: AdjustmentParams,
) -> pd.DataFrame:
    """Calculate profit chance metrics by MFE bucket.

    For each bucket threshold, calculates metrics on trades where mfe_pct >= threshold.

    Args:
        df: Trade data with gain_pct, mae_pct, mfe_pct columns.
        mapping: Column mapping configuration.
        adjustment_params: Adjustment parameters (stop_loss, efficiency).

    Returns:
        DataFrame with rows for each bucket and columns:
        Profit Reached %, Chance of Next %, Chance of Max Loss %,
        Win %, Profit Ratio, Edge %, EG %
    """
    mfe_col = mapping.mfe_pct
    mae_col = mapping.mae_pct
    gain_col = mapping.gain_pct
    stop_loss = adjustment_params.stop_loss

    rows = []
    buckets = PROFIT_LOSS_BUCKETS

    for i, threshold in enumerate(buckets):
        next_threshold = buckets[i + 1] if i + 1 < len(buckets) else None
        row = _calculate_profit_chance_row(
            df, mfe_col, mae_col, gain_col, threshold, next_threshold, stop_loss
        )
        rows.append(row)

    return pd.DataFrame(rows)


def _calculate_profit_chance_row(
    df: pd.DataFrame,
    mfe_col: str,
    mae_col: str,
    gain_col: str,
    threshold: int,
    next_threshold: int | None,
    stop_loss: float,
) -> dict:
    """Calculate metrics for a single profit chance bucket.

    Args:
        df: Trade data DataFrame.
        mfe_col: Column name for MFE percentage.
        mae_col: Column name for MAE percentage.
        gain_col: Column name for gain percentage.
        threshold: Current bucket threshold (e.g., 5 for 5%).
        next_threshold: Next bucket threshold (None for last bucket).
        stop_loss: Stop loss percentage from adjustment params.

    Returns:
        Dictionary with row metrics.
    """
    # Filter to trades that reached this MFE threshold
    # mfe_pct is in percentage format (e.g., 15 = 15%)
    bucket_df = df[df[mfe_col] >= threshold]
    count = len(bucket_df)

    if count == 0:
        return {
            "Profit Reached %": threshold,
            "Chance of Next %": None,
            "Chance of Max Loss %": None,
            "Win %": None,
            "Profit Ratio": None,
            "Edge %": None,
            "EG %": None,
        }

    # Chance of Next %: probability of reaching next bucket
    if next_threshold is not None:
        next_count = (bucket_df[mfe_col] >= next_threshold).sum()
        chance_of_next = (next_count / count) * 100
    else:
        chance_of_next = None  # No next bucket for 40%

    # Chance of Max Loss %: trades that hit stop loss
    hit_stop = (bucket_df[mae_col] > stop_loss).sum()
    chance_of_max_loss = (hit_stop / count) * 100

    # Win %: trades with positive gain
    # gain_pct is in decimal format (0.10 = 10%)
    winners = bucket_df[gain_col] > 0
    win_count = winners.sum()
    win_pct = (win_count / count) * 100

    # Profit Ratio: avg winner / abs(avg loser)
    losers = bucket_df[gain_col] < 0
    loss_count = losers.sum()

    if win_count > 0:
        avg_win = bucket_df.loc[winners, gain_col].mean()
    else:
        avg_win = 0.0

    if loss_count > 0:
        avg_loss = bucket_df.loc[losers, gain_col].mean()  # Negative value
        profit_ratio = avg_win / abs(avg_loss) if avg_loss != 0 else None
    else:
        profit_ratio = None  # No losers, can't calculate ratio

    # Edge %: (profit_ratio + 1) * win_rate - 1
    win_rate = win_count / count
    if profit_ratio is not None:
        edge_decimal = (profit_ratio + 1) * win_rate - 1
        edge_pct = edge_decimal * 100
    else:
        edge_decimal = None
        edge_pct = None

    # EG %: geometric growth formula
    eg_pct = calculate_expected_growth(win_rate, profit_ratio)

    return {
        "Profit Reached %": threshold,
        "Chance of Next %": chance_of_next,
        "Chance of Max Loss %": chance_of_max_loss,
        "Win %": win_pct,
        "Profit Ratio": profit_ratio,
        "Edge %": edge_pct,
        "EG %": eg_pct,
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_statistics.py::TestCalculateProfitChanceTable::test_basic_data -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/statistics.py tests/unit/test_statistics.py
git commit -m "feat(statistics): add calculate_profit_chance_table function"
```

---

### Task 2: Add More Tests for Profit Chance Table

**Files:**
- Test: `tests/unit/test_statistics.py`

**Step 1: Write additional tests**

Add to `tests/unit/test_statistics.py` in `TestCalculateProfitChanceTable`:

```python
    def test_bucket_thresholds(self, sample_mapping, default_adjustment_params):
        """Test that all 8 bucket thresholds are present."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10],
                "mae_pct": [5.0],
                "mfe_pct": [50.0],  # Reaches all buckets
            }
        )
        result = calculate_profit_chance_table(df, sample_mapping, default_adjustment_params)

        expected_thresholds = [5, 10, 15, 20, 25, 30, 35, 40]
        assert result["Profit Reached %"].tolist() == expected_thresholds

    def test_chance_of_next_calculation(self, sample_mapping, default_adjustment_params):
        """Test Chance of Next % is calculated correctly."""
        # 4 trades: 3 reach 5%, 2 reach 10%, 1 reaches 15%
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, 0.05, 0.08, -0.05],
                "mae_pct": [3.0, 3.0, 3.0, 3.0],
                "mfe_pct": [5.0, 12.0, 18.0, 3.0],  # 3 reach 5%, 2 reach 10%, 1 reaches 15%
            }
        )
        result = calculate_profit_chance_table(df, sample_mapping, default_adjustment_params)

        # At 5% bucket: 3 trades, 2 reach 10% -> 66.67%
        row_5 = result[result["Profit Reached %"] == 5].iloc[0]
        assert abs(row_5["Chance of Next %"] - 66.67) < 0.1

    def test_chance_of_max_loss_uses_stop_loss(self, sample_mapping, default_adjustment_params):
        """Test Chance of Max Loss % uses stop_loss from adjustment params."""
        # default_adjustment_params has stop_loss = 8
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, 0.05, -0.08],
                "mae_pct": [5.0, 10.0, 15.0],  # 2 exceed 8% stop loss
                "mfe_pct": [10.0, 10.0, 10.0],  # All reach 10%
            }
        )
        result = calculate_profit_chance_table(df, sample_mapping, default_adjustment_params)

        row_10 = result[result["Profit Reached %"] == 10].iloc[0]
        # 2 out of 3 exceeded 8% stop loss -> 66.67%
        assert abs(row_10["Chance of Max Loss %"] - 66.67) < 0.1

    def test_empty_bucket_returns_none(self, sample_mapping, default_adjustment_params):
        """Test that empty buckets return None for metrics."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10],
                "mae_pct": [5.0],
                "mfe_pct": [3.0],  # Doesn't reach any bucket
            }
        )
        result = calculate_profit_chance_table(df, sample_mapping, default_adjustment_params)

        # All buckets should have None values
        assert result["Chance of Next %"].isna().all()

    def test_last_bucket_has_no_next(self, sample_mapping, default_adjustment_params):
        """Test that 40% bucket has None for Chance of Next %."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10],
                "mae_pct": [5.0],
                "mfe_pct": [50.0],  # Reaches all buckets
            }
        )
        result = calculate_profit_chance_table(df, sample_mapping, default_adjustment_params)

        row_40 = result[result["Profit Reached %"] == 40].iloc[0]
        assert pd.isna(row_40["Chance of Next %"])

    def test_profit_ratio_no_losers(self, sample_mapping, default_adjustment_params):
        """Test Profit Ratio is None when no losers."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, 0.20],  # All winners
                "mae_pct": [3.0, 3.0],
                "mfe_pct": [15.0, 20.0],
            }
        )
        result = calculate_profit_chance_table(df, sample_mapping, default_adjustment_params)

        row_5 = result[result["Profit Reached %"] == 5].iloc[0]
        assert pd.isna(row_5["Profit Ratio"])
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/unit/test_statistics.py::TestCalculateProfitChanceTable -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add tests/unit/test_statistics.py
git commit -m "test(statistics): add comprehensive tests for profit chance table"
```

---

### Task 3: Add Loss Chance Table Calculation Function

**Files:**
- Modify: `src/core/statistics.py`
- Test: `tests/unit/test_statistics.py`

**Step 1: Write the failing test**

Add to `tests/unit/test_statistics.py`:

```python
class TestCalculateLossChanceTable:
    """Tests for calculate_loss_chance_table function."""

    def test_basic_data(self, sample_mapping, default_adjustment_params):
        """Test loss chance table with basic data."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, 0.05, -0.08, -0.15],
                "mae_pct": [15.0, 8.0, 20.0, 30.0],  # MAE values
                "mfe_pct": [10.0, 5.0, 3.0, 2.0],
            }
        )
        result = calculate_loss_chance_table(df, sample_mapping, default_adjustment_params)

        assert len(result) == 8  # 8 buckets
        assert "Loss Reached %" in result.columns
        assert "Chance of Next %" in result.columns
        assert "Chance of Profit %" in result.columns
        assert "Win %" in result.columns
        assert "Profit Ratio" in result.columns
        assert "Edge %" in result.columns
        assert "EG %" in result.columns

    def test_chance_of_profit_calculation(self, sample_mapping, default_adjustment_params):
        """Test Chance of Profit % is trades that ended profitable."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, -0.05, -0.08],  # 1 winner despite MAE
                "mae_pct": [15.0, 15.0, 15.0],  # All reach 15% MAE
                "mfe_pct": [10.0, 5.0, 3.0],
            }
        )
        result = calculate_loss_chance_table(df, sample_mapping, default_adjustment_params)

        row_15 = result[result["Loss Reached %"] == 15].iloc[0]
        # 1 out of 3 ended profitable -> 33.33%
        assert abs(row_15["Chance of Profit %"] - 33.33) < 0.1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_statistics.py::TestCalculateLossChanceTable::test_basic_data -v`
Expected: FAIL with "cannot import name 'calculate_loss_chance_table'"

**Step 3: Write minimal implementation**

Add to `src/core/statistics.py`:

```python
def calculate_loss_chance_table(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    adjustment_params: AdjustmentParams,
) -> pd.DataFrame:
    """Calculate loss chance metrics by MAE bucket.

    For each bucket threshold, calculates metrics on trades where mae_pct >= threshold.

    Args:
        df: Trade data with gain_pct, mae_pct, mfe_pct columns.
        mapping: Column mapping configuration.
        adjustment_params: Adjustment parameters (stop_loss, efficiency).

    Returns:
        DataFrame with rows for each bucket and columns:
        Loss Reached %, Chance of Next %, Chance of Profit %,
        Win %, Profit Ratio, Edge %, EG %
    """
    mae_col = mapping.mae_pct
    gain_col = mapping.gain_pct

    rows = []
    buckets = PROFIT_LOSS_BUCKETS

    for i, threshold in enumerate(buckets):
        next_threshold = buckets[i + 1] if i + 1 < len(buckets) else None
        row = _calculate_loss_chance_row(
            df, mae_col, gain_col, threshold, next_threshold
        )
        rows.append(row)

    return pd.DataFrame(rows)


def _calculate_loss_chance_row(
    df: pd.DataFrame,
    mae_col: str,
    gain_col: str,
    threshold: int,
    next_threshold: int | None,
) -> dict:
    """Calculate metrics for a single loss chance bucket.

    Args:
        df: Trade data DataFrame.
        mae_col: Column name for MAE percentage.
        gain_col: Column name for gain percentage.
        threshold: Current bucket threshold (e.g., 5 for 5%).
        next_threshold: Next bucket threshold (None for last bucket).

    Returns:
        Dictionary with row metrics.
    """
    # Filter to trades that reached this MAE threshold
    bucket_df = df[df[mae_col] >= threshold]
    count = len(bucket_df)

    if count == 0:
        return {
            "Loss Reached %": threshold,
            "Chance of Next %": None,
            "Chance of Profit %": None,
            "Win %": None,
            "Profit Ratio": None,
            "Edge %": None,
            "EG %": None,
        }

    # Chance of Next %: probability of reaching next MAE bucket
    if next_threshold is not None:
        next_count = (bucket_df[mae_col] >= next_threshold).sum()
        chance_of_next = (next_count / count) * 100
    else:
        chance_of_next = None  # No next bucket for 40%

    # Chance of Profit %: trades that ended profitable
    winners = bucket_df[gain_col] > 0
    win_count = winners.sum()
    chance_of_profit = (win_count / count) * 100

    # Win % (same as Chance of Profit % for this table)
    win_pct = chance_of_profit

    # Profit Ratio: avg winner / abs(avg loser)
    losers = bucket_df[gain_col] < 0
    loss_count = losers.sum()

    if win_count > 0:
        avg_win = bucket_df.loc[winners, gain_col].mean()
    else:
        avg_win = 0.0

    if loss_count > 0:
        avg_loss = bucket_df.loc[losers, gain_col].mean()
        profit_ratio = avg_win / abs(avg_loss) if avg_loss != 0 else None
    else:
        profit_ratio = None

    # Edge %
    win_rate = win_count / count
    if profit_ratio is not None:
        edge_decimal = (profit_ratio + 1) * win_rate - 1
        edge_pct = edge_decimal * 100
    else:
        edge_decimal = None
        edge_pct = None

    # EG %
    eg_pct = calculate_expected_growth(win_rate, profit_ratio)

    return {
        "Loss Reached %": threshold,
        "Chance of Next %": chance_of_next,
        "Chance of Profit %": chance_of_profit,
        "Win %": win_pct,
        "Profit Ratio": profit_ratio,
        "Edge %": edge_pct,
        "EG %": eg_pct,
    }
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_statistics.py::TestCalculateLossChanceTable -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/core/statistics.py tests/unit/test_statistics.py
git commit -m "feat(statistics): add calculate_loss_chance_table function"
```

---

### Task 4: Add UI Widget for Profit/Loss Chance Tab

**Files:**
- Modify: `src/tabs/statistics_tab.py`

**Step 1: Add imports**

Add to the imports in `src/tabs/statistics_tab.py`:

```python
from src.core.statistics import (
    calculate_mae_before_win,
    calculate_mfe_before_loss,
    calculate_offset_table,
    calculate_partial_cover_table,
    calculate_profit_chance_table,  # Add this
    calculate_loss_chance_table,    # Add this
    calculate_scaling_table,
    calculate_stop_loss_table,
)
```

**Step 2: Run existing tests to ensure imports work**

Run: `pytest tests/unit/test_statistics_tab.py -v -k "test_" --maxfail=1`
Expected: Tests should still pass

**Step 3: Commit**

```bash
git add src/tabs/statistics_tab.py
git commit -m "refactor(statistics): add imports for profit/loss chance functions"
```

---

### Task 5: Create Profit/Loss Chance Widget Method

**Files:**
- Modify: `src/tabs/statistics_tab.py`

**Step 1: Add widget creation method**

Add to `StatisticsTab` class (after `_create_stop_loss_offset_widget`):

```python
def _create_profit_loss_chance_widget(self) -> QWidget:
    """Create Profit/Loss Chance sub-tab with stacked tables."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
    layout.setSpacing(Spacing.MD)

    # Chance of Profit section label
    profit_label = QLabel("Chance of Profit")
    profit_label.setStyleSheet(
        f"""
        QLabel {{
            color: {Colors.TEXT_PRIMARY};
            font-family: '{Fonts.UI}';
            font-size: 14px;
            font-weight: 600;
        }}
    """
    )
    layout.addWidget(profit_label)

    # Profit Chance table
    self._profit_chance_table = self._create_table()
    layout.addWidget(self._profit_chance_table, 1)

    # Spacer
    layout.addSpacing(Spacing.LG)

    # Chance of Loss section label
    loss_label = QLabel("Chance of Loss")
    loss_label.setStyleSheet(
        f"""
        QLabel {{
            color: {Colors.TEXT_PRIMARY};
            font-family: '{Fonts.UI}';
            font-size: 14px;
            font-weight: 600;
        }}
    """
    )
    layout.addWidget(loss_label)

    # Loss Chance table
    self._loss_chance_table = self._create_table()
    layout.addWidget(self._loss_chance_table, 1)

    return widget
```

**Step 2: Run linter/type check**

Run: `python -m py_compile src/tabs/statistics_tab.py`
Expected: No errors

**Step 3: Commit**

```bash
git add src/tabs/statistics_tab.py
git commit -m "feat(statistics): add _create_profit_loss_chance_widget method"
```

---

### Task 6: Register New Tab in Setup UI

**Files:**
- Modify: `src/tabs/statistics_tab.py`

**Step 1: Find and update _setup_ui method**

In `_setup_ui()`, after the line that adds Stop Loss/Offset tab, add:

```python
# Profit/Loss Chance tab
self._profit_loss_chance_widget = self._create_profit_loss_chance_widget()
self._tab_widget.addTab(self._profit_loss_chance_widget, "Profit/Loss Chance")
```

**Step 2: Run app to verify tab appears**

Run: `python src/main.py`
Expected: New "Profit/Loss Chance" tab visible in Statistics tab

**Step 3: Commit**

```bash
git add src/tabs/statistics_tab.py
git commit -m "feat(statistics): register Profit/Loss Chance tab in UI"
```

---

### Task 7: Add Table Population Logic

**Files:**
- Modify: `src/tabs/statistics_tab.py`

**Step 1: Update _update_all_tables method**

Find `_update_all_tables` method and add after the offset table population:

```python
# Profit/Loss Chance tables
try:
    profit_chance_df = calculate_profit_chance_table(df, mapping, params)
    self._populate_table(self._profit_chance_table, profit_chance_df)
except Exception as e:
    logger.error(f"Failed to calculate profit chance table: {e}")
    self._profit_chance_table.setRowCount(0)

try:
    loss_chance_df = calculate_loss_chance_table(df, mapping, params)
    self._populate_table(self._loss_chance_table, loss_chance_df)
except Exception as e:
    logger.error(f"Failed to calculate loss chance table: {e}")
    self._loss_chance_table.setRowCount(0)
```

**Step 2: Update _clear_all_tables method**

Find `_clear_all_tables` and add:

```python
self._profit_chance_table.setRowCount(0)
self._profit_chance_table.setColumnCount(0)
self._loss_chance_table.setRowCount(0)
self._loss_chance_table.setColumnCount(0)
```

**Step 3: Run app and load data to verify tables populate**

Run: `python src/main.py`
Expected: Tables populate with data when file is loaded

**Step 4: Commit**

```bash
git add src/tabs/statistics_tab.py
git commit -m "feat(statistics): add table population for profit/loss chance"
```

---

### Task 8: Add Export Support

**Files:**
- Modify: `src/tabs/statistics_tab.py`

**Step 1: Update _on_export_clicked method**

Find `_on_export_clicked` and add to the tables list:

```python
("Profit Chance", self._profit_chance_table),
("Loss Chance", self._loss_chance_table),
```

**Step 2: Verify export works**

Run: `python src/main.py`
Expected: Export button includes new tables in markdown output

**Step 3: Commit**

```bash
git add src/tabs/statistics_tab.py
git commit -m "feat(statistics): add profit/loss chance tables to export"
```

---

### Task 9: Add Column Availability Check

**Files:**
- Modify: `src/tabs/statistics_tab.py`

**Step 1: Update _check_column_availability method**

Find `_check_column_availability` and add logic to disable Profit/Loss Chance tab when mfe_pct or mae_pct are missing:

```python
# Find the index of Profit/Loss Chance tab
profit_loss_idx = None
for i in range(self._tab_widget.count()):
    if self._tab_widget.tabText(i) == "Profit/Loss Chance":
        profit_loss_idx = i
        break

if profit_loss_idx is not None:
    has_mfe_mae = has_mfe and has_mae
    self._tab_widget.setTabEnabled(profit_loss_idx, has_mfe_mae)
```

**Step 2: Test with data missing mfe_pct column**

Run: `python src/main.py` with test data
Expected: Tab is disabled when columns are missing

**Step 3: Commit**

```bash
git add src/tabs/statistics_tab.py
git commit -m "feat(statistics): disable profit/loss chance tab when columns missing"
```

---

### Task 10: Run Full Test Suite and Final Verification

**Files:**
- All modified files

**Step 1: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass

**Step 2: Run app and verify functionality**

Run: `python src/main.py`
Verify:
- Profit/Loss Chance tab appears
- Both tables populate with data
- Gradient styling applies
- Export includes both tables
- Tab disables when columns missing

**Step 3: Final commit if any cleanup needed**

```bash
git status
# If clean, done. Otherwise:
git add -A
git commit -m "chore: cleanup and final adjustments"
```

---

## Summary

**Files Modified:**
- `src/core/statistics.py` - Added `calculate_profit_chance_table`, `calculate_loss_chance_table`, and helper functions
- `src/tabs/statistics_tab.py` - Added new tab widget, population logic, export support
- `tests/unit/test_statistics.py` - Added comprehensive tests for new functions

**Total Tasks:** 10 bite-sized tasks with TDD approach
