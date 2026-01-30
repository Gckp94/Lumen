# Partial Cover % Table Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Partial Cover % table to the Scaling tab that simulates covering part of a short position when price moves against you (MAE reaches threshold).

**Architecture:** Mirror the existing Partial Target % implementation but use `mae_pct` instead of `mfe_pct`, and calculate losses at threshold levels. Add a second spinbox and table vertically stacked below the existing Partial Target % section.

**Tech Stack:** Python, pandas, PyQt6, pytest

---

### Task 1: Add `_calculate_cover_row` helper function

**Files:**
- Modify: `src/core/statistics.py:736` (insert after `_calculate_scaling_row`)

**Step 1: Write the failing test**

Add to `tests/unit/test_statistics.py`:

```python
class TestPartialCoverAnalysis:
    """Tests for partial cover analysis calculations."""

    def test_calculate_partial_cover_basic(self, sample_mapping):
        """Test basic partial cover calculation."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, -0.05, 0.08, -0.12],
                "adjusted_gain_pct": [0.10, -0.05, 0.08, -0.12],
                "mae_pct": [8.0, 15.0, 5.0, 20.0],
            }
        )

        result = calculate_partial_cover_table(df, sample_mapping, cover_pct=0.5)

        # Should have rows for each threshold level
        assert len(result) == 8  # SCALING_TARGET_LEVELS has 8 levels
        assert "Partial Cover %" in result.columns
        assert "% of Trades" in result.columns
        assert "Avg Blended Return %" in result.columns

        # First row is 5% threshold
        first_row = result.iloc[0]
        assert first_row["Partial Cover %"] == 5
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_statistics.py::TestPartialCoverAnalysis::test_calculate_partial_cover_basic -v`
Expected: FAIL with "cannot import name 'calculate_partial_cover_table'"

**Step 3: Add import to test file**

Update imports in `tests/unit/test_statistics.py`:

```python
from src.core.statistics import (
    calculate_mae_before_win,
    calculate_mfe_before_loss,
    calculate_offset_table,
    calculate_partial_cover_table,
    calculate_scaling_table,
    calculate_stop_loss_table,
)
```

**Step 4: Write minimal implementation**

Add to `src/core/statistics.py` after `_calculate_scaling_row` function (around line 828):

```python
def _calculate_cover_row(
    df: pd.DataFrame,
    mae_col: str,
    threshold: int,
    cover_pct: float,
) -> dict:
    """Calculate metrics for a single cover threshold level.

    Args:
        df: Trade data DataFrame.
        mae_col: Column name for MAE percentage (percentage points).
        threshold: Threshold level for partial cover (e.g., 10 for 10%).
        cover_pct: Fraction of position to cover (0-1).

    Returns:
        Dictionary with metrics for this threshold level.
    """
    total_trades = len(df)

    # Handle empty data
    if total_trades == 0:
        return {
            "Partial Cover %": threshold,
            "% of Trades": 0.0,
            "Avg Blended Return %": None,
            "Avg Full Hold Return %": None,
            "Total Blended Return %": 0.0,
            "Total Full Hold Return %": 0.0,
            "Blended Win %": 0.0,
            "Full Hold Win %": 0.0,
            "Blended Profit Ratio": None,
            "Full Hold Profit Ratio": None,
            "Blended Edge %": None,
            "Full Hold Edge %": None,
            "Blended EG %": None,
            "Full Hold EG %": None,
        }

    # Full hold returns (in decimal, e.g., 0.10 = 10%)
    full_hold_returns = df["adjusted_gain_pct"].copy()

    # Calculate blended returns for each trade
    # If mae_pct >= threshold: blended = cover_pct * (-threshold/100) + (1-cover_pct) * full_hold
    # If mae_pct < threshold: blended = full_hold (threshold not reached, no cover)
    threshold_reached_mask = df[mae_col] >= threshold
    reached_count = threshold_reached_mask.sum()

    # Calculate blended returns
    blended_returns = full_hold_returns.copy()
    # For trades that reached the threshold, apply the blending formula
    # Cover at a loss: -threshold/100 converts threshold to negative decimal
    blended_returns[threshold_reached_mask] = (
        cover_pct * (-threshold / 100.0)
        + (1 - cover_pct) * full_hold_returns[threshold_reached_mask]
    )

    # % of Trades reaching threshold
    pct_of_trades = (reached_count / total_trades) * 100

    # Convert returns to percentages for display
    blended_returns_pct = blended_returns * 100
    full_hold_returns_pct = full_hold_returns * 100

    # Calculate averages
    avg_blended = blended_returns_pct.mean()
    avg_full_hold = full_hold_returns_pct.mean()

    # Calculate totals
    total_blended = blended_returns_pct.sum()
    total_full_hold = full_hold_returns_pct.sum()

    # Calculate metrics for blended returns
    blended_metrics = _calculate_return_metrics(blended_returns)

    # Calculate metrics for full hold returns
    full_hold_metrics = _calculate_return_metrics(full_hold_returns)

    return {
        "Partial Cover %": threshold,
        "% of Trades": pct_of_trades,
        "Avg Blended Return %": avg_blended,
        "Avg Full Hold Return %": avg_full_hold,
        "Total Blended Return %": total_blended,
        "Total Full Hold Return %": total_full_hold,
        "Blended Win %": blended_metrics["win_pct"],
        "Full Hold Win %": full_hold_metrics["win_pct"],
        "Blended Profit Ratio": blended_metrics["profit_ratio"],
        "Full Hold Profit Ratio": full_hold_metrics["profit_ratio"],
        "Blended Edge %": blended_metrics["edge_pct"],
        "Full Hold Edge %": full_hold_metrics["edge_pct"],
        "Blended EG %": blended_metrics["eg_pct"],
        "Full Hold EG %": full_hold_metrics["eg_pct"],
    }


def calculate_partial_cover_table(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    cover_pct: float,
) -> pd.DataFrame:
    """Compare blended partial-cover returns vs full hold.

    Analyzes covering part of a short position at various MAE thresholds vs. holding to close.

    Args:
        df: Trade data with adjusted_gain_pct and mae_pct columns.
        mapping: Column mapping configuration.
        cover_pct: Fraction of position to cover (0-1, e.g., 0.5 for 50%).

    Returns:
        DataFrame with rows for each threshold level comparing blended vs full hold.
        Columns: Partial Cover %, % of Trades, Avg Blended Return %,
                 Avg Full Hold Return %, Total Blended Return %,
                 Total Full Hold Return %, Blended Win %, Full Hold Win %,
                 Blended Profit Ratio, Full Hold Profit Ratio,
                 Blended Edge %, Full Hold Edge %, Blended EG %, Full Hold EG %
    """
    rows = []
    mae_col = mapping.mae_pct

    for threshold in SCALING_TARGET_LEVELS:
        row = _calculate_cover_row(df, mae_col, threshold, cover_pct)
        rows.append(row)

    return pd.DataFrame(rows)
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_statistics.py::TestPartialCoverAnalysis::test_calculate_partial_cover_basic -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/core/statistics.py tests/unit/test_statistics.py
git commit -m "feat(statistics): add calculate_partial_cover_table function"
```

---

### Task 2: Add edge case tests for partial cover

**Files:**
- Modify: `tests/unit/test_statistics.py`

**Step 1: Write tests for edge cases**

Add to `TestPartialCoverAnalysis` class:

```python
    def test_calculate_partial_cover_empty_df(self, sample_mapping):
        """Test partial cover with empty DataFrame."""
        df = pd.DataFrame(
            columns=["gain_pct", "adjusted_gain_pct", "mae_pct"]
        )

        result = calculate_partial_cover_table(df, sample_mapping, cover_pct=0.5)

        assert len(result) == 8
        # All rows should have 0% of trades
        assert (result["% of Trades"] == 0.0).all()

    def test_calculate_partial_cover_no_threshold_reached(self, sample_mapping):
        """Test when no trades reach any threshold."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, 0.05],
                "adjusted_gain_pct": [0.10, 0.05],
                "mae_pct": [2.0, 3.0],  # All below 5% threshold
            }
        )

        result = calculate_partial_cover_table(df, sample_mapping, cover_pct=0.5)

        # No trades reach even the lowest threshold (5%)
        assert result.iloc[0]["% of Trades"] == 0.0
        # Blended should equal full hold when no threshold reached
        assert result.iloc[0]["Avg Blended Return %"] == result.iloc[0]["Avg Full Hold Return %"]

    def test_calculate_partial_cover_blended_calculation(self, sample_mapping):
        """Test blended return calculation when threshold is reached."""
        # Single trade that reaches 10% MAE with 20% gain
        df = pd.DataFrame(
            {
                "gain_pct": [0.20],
                "adjusted_gain_pct": [0.20],
                "mae_pct": [10.0],
            }
        )

        result = calculate_partial_cover_table(df, sample_mapping, cover_pct=0.5)

        # At 10% threshold (row index 1), blended = 0.5 * (-0.10) + 0.5 * 0.20 = 0.05 = 5%
        row_10 = result[result["Partial Cover %"] == 10].iloc[0]
        assert row_10["% of Trades"] == 100.0  # Trade reached threshold
        # Blended return: 0.5 * (-10%) + 0.5 * (20%) = -5% + 10% = 5%
        assert abs(row_10["Avg Blended Return %"] - 5.0) < 0.01
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/unit/test_statistics.py::TestPartialCoverAnalysis -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/unit/test_statistics.py
git commit -m "test(statistics): add edge case tests for partial cover"
```

---

### Task 3: Update Scale Out spinbox range to 0-100%

**Files:**
- Modify: `src/tabs/statistics_tab.py:241-242`

**Step 1: Write the failing test**

Add to `tests/unit/test_statistics_tab.py`:

```python
    def test_scale_out_spinbox_range(self, app, test_df, test_mapping):
        """Test that scale out spinbox allows 0-100% range."""
        tab = StatisticsTab()

        assert tab._scale_out_spin.minimum() == 0
        assert tab._scale_out_spin.maximum() == 100
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_statistics_tab.py::TestStatisticsTabTables::test_scale_out_spinbox_range -v`
Expected: FAIL (current range is 10-90)

**Step 3: Update spinbox range**

In `src/tabs/statistics_tab.py`, in `_create_scaling_widget` method, change:

```python
        self._scale_out_spin.setRange(10, 90)
```

to:

```python
        self._scale_out_spin.setRange(0, 100)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_statistics_tab.py::TestStatisticsTabTables::test_scale_out_spinbox_range -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tabs/statistics_tab.py tests/unit/test_statistics_tab.py
git commit -m "fix(statistics): expand Scale Out spinbox range to 0-100%"
```

---

### Task 4: Add Cover spinbox and table to Scaling widget

**Files:**
- Modify: `src/tabs/statistics_tab.py:218-270` (`_create_scaling_widget` method)

**Step 1: Write the failing test**

Add to `tests/unit/test_statistics_tab.py`:

```python
    def test_cover_spinbox_exists(self, app, test_df, test_mapping):
        """Test that cover spinbox exists with correct range."""
        tab = StatisticsTab()

        assert hasattr(tab, "_cover_spin")
        assert tab._cover_spin.minimum() == 0
        assert tab._cover_spin.maximum() == 100
        assert tab._cover_spin.value() == 50

    def test_cover_table_exists(self, app, test_df, test_mapping):
        """Test that cover table exists."""
        tab = StatisticsTab()

        assert hasattr(tab, "_cover_table")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_statistics_tab.py::TestStatisticsTabTables::test_cover_spinbox_exists -v`
Expected: FAIL with "has no attribute '_cover_spin'"

**Step 3: Update `_create_scaling_widget` method**

Replace the entire `_create_scaling_widget` method in `src/tabs/statistics_tab.py`:

```python
    def _create_scaling_widget(self) -> QWidget:
        """Create scaling sub-tab with spinbox controls for target and cover."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # Scale Out control row
        scale_out_row = QHBoxLayout()
        scale_out_row.setSpacing(Spacing.SM)

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
        scale_out_row.addWidget(scale_out_label)

        self._scale_out_spin = QSpinBox()
        self._scale_out_spin.setRange(0, 100)
        self._scale_out_spin.setValue(50)
        self._scale_out_spin.setSingleStep(10)
        self._scale_out_spin.setSuffix("%")
        self._scale_out_spin.setStyleSheet(
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
        scale_out_row.addWidget(self._scale_out_spin)
        scale_out_row.addStretch()

        layout.addLayout(scale_out_row)

        # Scaling table (Partial Target %)
        self._scaling_table = self._create_table()
        layout.addWidget(self._scaling_table)

        # Spacer between sections
        layout.addSpacing(Spacing.LG)

        # Cover control row
        cover_row = QHBoxLayout()
        cover_row.setSpacing(Spacing.SM)

        cover_label = QLabel("Cover:")
        cover_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: 13px;
            }}
        """
        )
        cover_row.addWidget(cover_label)

        self._cover_spin = QSpinBox()
        self._cover_spin.setRange(0, 100)
        self._cover_spin.setValue(50)
        self._cover_spin.setSingleStep(10)
        self._cover_spin.setSuffix("%")
        self._cover_spin.setStyleSheet(
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
        cover_row.addWidget(self._cover_spin)
        cover_row.addStretch()

        layout.addLayout(cover_row)

        # Cover table (Partial Cover %)
        self._cover_table = self._create_table()
        layout.addWidget(self._cover_table)

        return widget
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_statistics_tab.py::TestStatisticsTabTables::test_cover_spinbox_exists tests/unit/test_statistics_tab.py::TestStatisticsTabTables::test_cover_table_exists -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tabs/statistics_tab.py tests/unit/test_statistics_tab.py
git commit -m "feat(statistics): add Cover spinbox and table to Scaling widget"
```

---

### Task 5: Wire up Cover spinbox and table population

**Files:**
- Modify: `src/tabs/statistics_tab.py` (imports, `_setup_connections`, `_update_all_tables`, `_clear_all_tables`)

**Step 1: Add import for `calculate_partial_cover_table`**

In `src/tabs/statistics_tab.py`, update imports:

```python
from src.core.statistics import (
    calculate_mae_before_win,
    calculate_mfe_before_loss,
    calculate_offset_table,
    calculate_partial_cover_table,
    calculate_scaling_table,
    calculate_stop_loss_table,
)
```

**Step 2: Add signal connection for cover spinbox**

In `_setup_connections` method, add after the scale out spinbox connection:

```python
        self._cover_spin.valueChanged.connect(self._on_cover_changed)
```

**Step 3: Add `_on_cover_changed` method**

Add new method after `_on_scale_out_changed`:

```python
    def _on_cover_changed(self, value: int) -> None:
        """Handle cover percentage spinbox value change.

        Args:
            value: New cover percentage (0-100).
        """
        self._refresh_cover_table()
```

**Step 4: Add `_refresh_cover_table` method**

Add new method after `_refresh_scaling_table`:

```python
    def _refresh_cover_table(self) -> None:
        """Refresh only the cover table with current data."""
        if not self._app_state.column_mapping:
            return

        mapping = self._app_state.column_mapping
        df = self._get_data_source()

        if df is None or df.empty:
            return

        try:
            cover_pct = self._cover_spin.value() / 100.0
            cover_df = calculate_partial_cover_table(df, mapping, cover_pct)
            self._populate_table(self._cover_table, cover_df)
        except Exception as e:
            logger.warning(f"Error refreshing Cover table: {e}")
```

**Step 5: Update `_update_all_tables` to populate cover table**

In `_update_all_tables`, add after the scaling table section:

```python
        # Calculate and populate Cover table
        try:
            cover_pct = self._cover_spin.value() / 100.0
            cover_df = calculate_partial_cover_table(df, mapping, cover_pct)
            self._populate_table(self._cover_table, cover_df)
        except Exception as e:
            logger.warning(f"Error calculating Cover table: {e}")
            self._cover_table.setRowCount(0)
```

**Step 6: Update `_clear_all_tables` to clear cover table**

In `_clear_all_tables`, add:

```python
        self._cover_table.setRowCount(0)
        self._cover_table.setColumnCount(0)
```

**Step 7: Run existing tests to verify nothing broke**

Run: `pytest tests/unit/test_statistics_tab.py -v`
Expected: PASS

**Step 8: Commit**

```bash
git add src/tabs/statistics_tab.py
git commit -m "feat(statistics): wire up Cover spinbox and table population"
```

---

### Task 6: Add integration test for cover spinbox refresh

**Files:**
- Modify: `tests/integration/test_statistics_tab.py`

**Step 1: Write the integration test**

Add to the integration test file:

```python
    def test_cover_spinbox_refreshes_table(
        self, qtbot, sample_df, sample_mapping, temp_file
    ):
        """Test that changing cover spinbox refreshes the cover table."""
        app_state = AppState()
        app_state.load_data(temp_file)
        app_state.set_column_mapping(sample_mapping)

        tab = StatisticsTab()
        tab.set_app_state(app_state)
        tab._show_empty_state(False)
        tab._update_all_tables(sample_df)

        initial_row_count = tab._cover_table.rowCount()
        assert initial_row_count > 0

        # Change cover percentage
        tab._cover_spin.setValue(75)

        # Table should still have data (refreshed)
        assert tab._cover_table.rowCount() > 0
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/integration/test_statistics_tab.py::TestStatisticsTabIntegration::test_cover_spinbox_refreshes_table -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/integration/test_statistics_tab.py
git commit -m "test(statistics): add integration test for cover spinbox"
```

---

### Task 7: Run full test suite and verify

**Step 1: Run all statistics tests**

Run: `pytest tests/unit/test_statistics.py tests/unit/test_statistics_tab.py tests/integration/test_statistics_tab.py -v`
Expected: All PASS

**Step 2: Commit final state**

```bash
git add -A
git commit -m "feat(statistics): complete Partial Cover % table implementation"
```
