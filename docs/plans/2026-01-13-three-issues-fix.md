# Three Issues Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix Edge % calculation formula, add date/trade toggle for chart X-axis, and fix adjustment params not updating comparison stats.

**Architecture:** Three independent fixes: (1) Edge % is multiplying EV by num_trades which creates unreasonable values - should just be EV itself; (2) Add X-axis mode toggle to _ChartPanel and plumb date data through equity calculations; (3) Fix signal flow so adjustment param changes trigger comparison grid/ribbon updates.

**Tech Stack:** PyQt6, PyQtGraph, Python dataclasses

---

## Task 1: Investigate Edge % Formula

**Files:**
- Read: `src/core/metrics.py:213-216`
- Read: `src/ui/components/comparison_grid.py` (to see how Edge is displayed)

**Step 1: Read the current Edge % calculation**

Look at lines 213-216 in metrics.py to confirm the formula:
```python
edge: float | None = None
if ev is not None:
    edge = ev * num_trades
```

**Step 2: Analyze the issue**

The current formula `Edge = EV × num_trades` is problematic:
- If EV = 0.5% and num_trades = 2000, Edge = 1000%
- This produces values in the thousands of percent

The correct interpretation: **Edge % should simply equal EV (Expected Value)**. Edge % is the per-trade expected return, which is exactly what EV calculates. The multiplication by num_trades conflates "edge percentage" with "total expected return in aggregate."

**Step 3: Document decision**

Edge % = EV. The field becomes redundant with EV, but we keep it for semantic clarity (traders often refer to "edge" as the expected return per trade).

---

## Task 2: Fix Edge % Calculation

**Files:**
- Modify: `src/core/metrics.py:213-216`
- Test: `tests/core/test_metrics.py`

**Step 1: Write failing test for correct Edge % value**

Add test to `tests/core/test_metrics.py`:

```python
def test_edge_equals_ev() -> None:
    """Edge % should equal EV (expected value per trade)."""
    df = pd.DataFrame({
        "gain_pct": [0.10, 0.08, -0.05, 0.12, -0.03],  # 5 trades
    })
    
    calculator = MetricsCalculator()
    metrics, _, _ = calculator.calculate(
        df=df,
        gain_col="gain_pct",
    )
    
    # Edge should equal EV, not EV * num_trades
    assert metrics.edge == metrics.ev
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_metrics.py::test_edge_equals_ev -v`
Expected: FAIL (edge currently equals ev * num_trades)

**Step 3: Fix the Edge calculation in metrics.py**

Change lines 213-216 from:
```python
edge: float | None = None
if ev is not None:
    edge = ev * num_trades
```

To:
```python
edge: float | None = None
if ev is not None:
    edge = ev  # Edge % equals EV (expected return per trade)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_metrics.py::test_edge_equals_ev -v`
Expected: PASS

**Step 5: Run full metrics test suite**

Run: `pytest tests/core/test_metrics.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/core/metrics.py tests/core/test_metrics.py
git commit -m "fix: Edge % now equals EV instead of EV × num_trades

Edge % represents the expected return per trade, which is exactly
what EV calculates. The previous formula multiplied by num_trades,
producing unreasonably high percentage values."
```

---

## Task 3: Add Date Column to Equity DataFrames

**Files:**
- Modify: `src/core/equity.py` - `calculate_flat_stake()` and `calculate_kelly()`
- Test: `tests/core/test_equity.py`

**Step 1: Write failing test for date column in flat stake equity**

Add to `tests/core/test_equity.py`:

```python
def test_flat_stake_includes_date_column() -> None:
    """Flat stake equity DataFrame should include date column when provided."""
    df = pd.DataFrame({
        "gain_pct": [0.05, -0.02, 0.03],
        "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
    })
    
    calculator = EquityCalculator()
    result = calculator.calculate_flat_stake(df, "gain_pct", stake=1000, date_col="date")
    
    assert "date" in result.columns
    assert len(result["date"]) == 3
    assert result["date"].iloc[0] == pd.Timestamp("2024-01-01")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_equity.py::test_flat_stake_includes_date_column -v`
Expected: FAIL (date_col parameter doesn't exist)

**Step 3: Update calculate_flat_stake signature and implementation**

In `src/core/equity.py`, modify `calculate_flat_stake()`:

Add parameter:
```python
def calculate_flat_stake(
    self,
    df: pd.DataFrame,
    gain_col: str,
    stake: float = 1000.0,
    date_col: str | None = None,  # NEW
) -> pd.DataFrame:
```

Add date column handling after creating result DataFrame:
```python
# After creating result_df with trade_num, pnl, equity, peak, drawdown...

# Include date column if provided
if date_col is not None and date_col in df.columns:
    result_df["date"] = df[date_col].values
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_equity.py::test_flat_stake_includes_date_column -v`
Expected: PASS

**Step 5: Write failing test for date column in kelly equity**

Add to `tests/core/test_equity.py`:

```python
def test_kelly_includes_date_column() -> None:
    """Kelly equity DataFrame should include date column when provided."""
    df = pd.DataFrame({
        "gain_pct": [0.05, -0.02, 0.03],
        "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
    })
    
    calculator = EquityCalculator()
    result = calculator.calculate_kelly(
        df, "gain_pct", 
        start_capital=10000, 
        kelly_pct=10.0, 
        kelly_fraction=25.0,
        date_col="date",
    )
    
    assert "date" in result.columns
    assert len(result["date"]) == 3
```

**Step 6: Run test to verify it fails**

Run: `pytest tests/core/test_equity.py::test_kelly_includes_date_column -v`
Expected: FAIL

**Step 7: Update calculate_kelly signature and implementation**

Add `date_col: str | None = None` parameter and include date in result DataFrame.

**Step 8: Run test to verify it passes**

Run: `pytest tests/core/test_equity.py::test_kelly_includes_date_column -v`
Expected: PASS

**Step 9: Run full equity test suite**

Run: `pytest tests/core/test_equity.py -v`
Expected: All tests PASS

**Step 10: Commit**

```bash
git add src/core/equity.py tests/core/test_equity.py
git commit -m "feat: add date column support to equity calculations

Both calculate_flat_stake() and calculate_kelly() now accept an
optional date_col parameter to include dates in the result DataFrame."
```

---

## Task 4: Create X-Axis Mode Toggle Component

**Files:**
- Create: `src/ui/components/axis_mode_toggle.py`
- Test: `tests/ui/components/test_axis_mode_toggle.py`

**Step 1: Write failing test for AxisModeToggle widget**

Create `tests/ui/components/test_axis_mode_toggle.py`:

```python
"""Tests for AxisModeToggle component."""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.ui.components.axis_mode_toggle import AxisModeToggle, AxisMode


@pytest.fixture(scope="module")
def app():
    """Create QApplication for widget tests."""
    app = QApplication.instance() or QApplication([])
    yield app


def test_toggle_default_mode_is_trades(app) -> None:
    """Default mode should be TRADES."""
    toggle = AxisModeToggle()
    assert toggle.mode == AxisMode.TRADES


def test_toggle_emits_signal_on_mode_change(app, qtbot) -> None:
    """mode_changed signal should emit when mode changes."""
    toggle = AxisModeToggle()
    
    with qtbot.waitSignal(toggle.mode_changed, timeout=1000) as blocker:
        toggle.set_mode(AxisMode.DATE)
    
    assert blocker.args == [AxisMode.DATE]


def test_toggle_switches_mode_on_click(app, qtbot) -> None:
    """Clicking inactive option should switch mode."""
    toggle = AxisModeToggle()
    assert toggle.mode == AxisMode.TRADES
    
    # Click the DATE option
    with qtbot.waitSignal(toggle.mode_changed):
        toggle._date_btn.click()
    
    assert toggle.mode == AxisMode.DATE
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/ui/components/test_axis_mode_toggle.py -v`
Expected: FAIL (module doesn't exist)

**Step 3: Create AxisModeToggle component**

Create `src/ui/components/axis_mode_toggle.py`:

```python
"""X-axis mode toggle for equity charts.

Provides a segmented control to switch between trade number and date
display on the chart X-axis.
"""

from enum import Enum, auto

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from src.ui.constants import Colors, Fonts, FontSizes, Spacing


class AxisMode(Enum):
    """X-axis display mode."""

    TRADES = auto()
    DATE = auto()


class AxisModeToggle(QWidget):
    """Segmented toggle control for chart X-axis mode.

    Observatory-themed toggle with subtle glow effects and crisp typography.
    Designed to complement the equity chart controls.

    Signals:
        mode_changed: Emitted when mode changes, with new AxisMode value.

    Attributes:
        mode: Current axis mode (TRADES or DATE).
    """

    mode_changed = pyqtSignal(object)  # AxisMode

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the toggle.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._mode = AxisMode.TRADES
        self._setup_ui()

    @property
    def mode(self) -> AxisMode:
        """Current axis mode."""
        return self._mode

    def set_mode(self, mode: AxisMode) -> None:
        """Set the axis mode.

        Args:
            mode: New axis mode to set.
        """
        if mode != self._mode:
            self._mode = mode
            self._update_button_states()
            self.mode_changed.emit(mode)

    def _setup_ui(self) -> None:
        """Set up the toggle layout and styling."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Container styling - pill-shaped with subtle border
        self.setStyleSheet(f"""
            AxisModeToggle {{
                background: {Colors.BG_ELEVATED};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
            }}
        """)

        # Base button style
        base_style = f"""
            QPushButton {{
                background: transparent;
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
                font-weight: 500;
                padding: {Spacing.XS}px {Spacing.MD}px;
                border: none;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                color: {Colors.TEXT_PRIMARY};
                background: rgba(255, 255, 255, 0.05);
            }}
        """

        # Active button style with cyan glow
        active_style = f"""
            QPushButton {{
                background: rgba(0, 255, 212, 0.12);
                color: {Colors.SIGNAL_CYAN};
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
                font-weight: 600;
                padding: {Spacing.XS}px {Spacing.MD}px;
                border: 1px solid rgba(0, 255, 212, 0.3);
                border-radius: 3px;
            }}
        """

        # Trades button
        self._trades_btn = QPushButton("Trades")
        self._trades_btn.setStyleSheet(active_style)  # Default active
        self._trades_btn.clicked.connect(lambda: self.set_mode(AxisMode.TRADES))
        self._trades_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._trades_btn)

        # Date button
        self._date_btn = QPushButton("Date")
        self._date_btn.setStyleSheet(base_style)
        self._date_btn.clicked.connect(lambda: self.set_mode(AxisMode.DATE))
        self._date_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._date_btn)

        # Store styles for updates
        self._base_style = base_style
        self._active_style = active_style

    def _update_button_states(self) -> None:
        """Update button styling based on current mode."""
        if self._mode == AxisMode.TRADES:
            self._trades_btn.setStyleSheet(self._active_style)
            self._date_btn.setStyleSheet(self._base_style)
        else:
            self._trades_btn.setStyleSheet(self._base_style)
            self._date_btn.setStyleSheet(self._active_style)
```

**Step 4: Fix import for Qt cursor**

Add missing import at top of file:
```python
from PyQt6.QtCore import Qt, pyqtSignal
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/ui/components/test_axis_mode_toggle.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/ui/components/axis_mode_toggle.py tests/ui/components/test_axis_mode_toggle.py
git commit -m "feat: add AxisModeToggle component for chart X-axis selection

Observatory-themed segmented toggle to switch between trade number
and date display on equity chart X-axis. Includes cyan glow effect
for active state."
```

---

## Task 5: Integrate Toggle into _ChartPanel

**Files:**
- Modify: `src/ui/components/equity_chart.py` - `_ChartPanel` class
- Modify: `src/ui/components/equity_chart.py` - `EquityChart` class

**Step 1: Add AxisModeToggle to _ChartPanel**

In `_ChartPanel._setup_ui()`, add the toggle next to the drawdown checkbox.

Import at top:
```python
from src.ui.components.axis_mode_toggle import AxisModeToggle, AxisMode
```

In `_setup_ui()`, after creating drawdown checkbox, add:
```python
# Controls row with toggle and checkbox
controls_layout = QHBoxLayout()
controls_layout.setContentsMargins(0, 0, 0, 0)
controls_layout.setSpacing(Spacing.MD)

# Axis mode toggle
self._axis_toggle = AxisModeToggle()
self._axis_toggle.mode_changed.connect(self._on_axis_mode_changed)
controls_layout.addWidget(self._axis_toggle)

controls_layout.addStretch()

# Drawdown checkbox (move here from direct add)
controls_layout.addWidget(self._drawdown_checkbox)

layout.addLayout(controls_layout)
```

**Step 2: Add _on_axis_mode_changed handler**

Add method to `_ChartPanel`:
```python
def _on_axis_mode_changed(self, mode: AxisMode) -> None:
    """Handle axis mode change.

    Args:
        mode: New axis mode.
    """
    self.chart.set_axis_mode(mode)
```

**Step 3: Store date data in _ChartPanel**

Add methods to store date data from equity DataFrames:
```python
def set_baseline(self, equity_df: pd.DataFrame | None) -> None:
    """Pass-through to chart's set_baseline method.

    Args:
        equity_df: DataFrame with equity data (may include date column).
    """
    self._baseline_dates = None
    if equity_df is not None and "date" in equity_df.columns:
        self._baseline_dates = equity_df["date"].values
    self.chart.set_baseline(equity_df, self._baseline_dates)

def set_filtered(self, equity_df: pd.DataFrame | None) -> None:
    """Pass-through to chart's set_filtered method.

    Args:
        equity_df: DataFrame with equity data (may include date column).
    """
    self._filtered_dates = None
    if equity_df is not None and "date" in equity_df.columns:
        self._filtered_dates = equity_df["date"].values
    self.chart.set_filtered(equity_df, self._filtered_dates)
```

**Step 4: Update EquityChart to support axis mode**

Add to `EquityChart.__init__()`:
```python
self._axis_mode = AxisMode.TRADES
self._baseline_dates: np.ndarray | None = None
self._filtered_dates: np.ndarray | None = None
```

Add method:
```python
def set_axis_mode(self, mode: AxisMode) -> None:
    """Set the X-axis display mode.

    Args:
        mode: TRADES for trade number, DATE for calendar date.
    """
    self._axis_mode = mode
    self._update_axis_display()
```

Add `_update_axis_display()` method to refresh X-axis based on mode.

**Step 5: Update signature of set_baseline/set_filtered**

Update to accept dates:
```python
def set_baseline(
    self, 
    equity_df: pd.DataFrame | None,
    dates: np.ndarray | None = None,
) -> None:
    # ... existing logic ...
    self._baseline_dates = dates
    self._update_axis_display()

def set_filtered(
    self, 
    equity_df: pd.DataFrame | None,
    dates: np.ndarray | None = None,
) -> None:
    # ... existing logic ...
    self._filtered_dates = dates
    self._update_axis_display()
```

**Step 6: Implement _update_axis_display**

```python
def _update_axis_display(self) -> None:
    """Update X-axis display based on current mode."""
    plot_item = self._plot_widget.getPlotItem()
    bottom_axis = plot_item.getAxis("bottom")
    
    if self._axis_mode == AxisMode.DATE and self._baseline_dates is not None:
        # Use date-based axis
        plot_item.setLabel("bottom", "Date")
        # Convert dates to tick positions and labels
        # ... date axis configuration ...
    else:
        # Use trade number axis
        plot_item.setLabel("bottom", "Trade #")
```

**Step 7: Run existing equity chart tests**

Run: `pytest tests/ui/components/test_equity_chart.py -v`
Expected: PASS (no breaking changes)

**Step 8: Commit**

```bash
git add src/ui/components/equity_chart.py
git commit -m "feat: integrate axis mode toggle into chart panel

_ChartPanel now includes AxisModeToggle control and passes date
data to EquityChart for date-based X-axis display."
```

---

## Task 6: Plumb Date Column Through MetricsCalculator

**Files:**
- Modify: `src/core/metrics.py` - `MetricsCalculator.calculate()`
- Modify: `src/tabs/pnl_stats.py` - calls to calculate()

**Step 1: Add date_col parameter to MetricsCalculator.calculate()**

Update signature:
```python
def calculate(
    self,
    df: pd.DataFrame,
    gain_col: str,
    # ... existing params ...
    date_col: str | None = None,  # NEW
) -> tuple[TradingMetrics, pd.DataFrame | None, pd.DataFrame | None]:
```

**Step 2: Pass date_col to equity calculations**

In calculate(), update calls to EquityCalculator:
```python
flat_equity = self._equity_calc.calculate_flat_stake(
    df, gain_col, stake=flat_stake, date_col=date_col
)

kelly_equity = self._equity_calc.calculate_kelly(
    df, gain_col, 
    start_capital=start_capital,
    kelly_pct=kelly_pct,
    kelly_fraction=fractional_kelly_pct,
    date_col=date_col,
)
```

**Step 3: Update callers in pnl_stats.py**

In `_recalculate_metrics()` and `_calculate_filtered_metrics()`, pass date column:
```python
metrics, flat_equity, kelly_equity = self._metrics_calculator.calculate(
    # ... existing params ...
    date_col=column_mapping.date if column_mapping else None,
)
```

**Step 4: Run metrics tests**

Run: `pytest tests/core/test_metrics.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/metrics.py src/tabs/pnl_stats.py
git commit -m "feat: plumb date column through metrics calculator to equity curves

MetricsCalculator.calculate() now accepts date_col parameter and
passes it to equity calculations for date-based chart display."
```

---

## Task 7: Investigate Adjustment Params Not Updating Comparison Stats

**Files:**
- Read: `src/tabs/pnl_stats.py` - signal connections and recalculation flow
- Read: `src/ui/components/comparison_grid.py` - set_values method

**Step 1: Trace the signal flow for adjustment_params_changed**

Read `src/tabs/pnl_stats.py` to trace:
1. UserInputsPanel emits `adjustment_params_changed`
2. `_on_panel_adjustment_changed()` updates AppState
3. AppState emits `adjustment_params_changed` 
4. Debounced `_schedule_recalculation()` called
5. `_recalculate_metrics()` calculates new metrics
6. Verify: Does it call `_comparison_grid.set_values()`?

**Step 2: Identify the bug**

Look at `_recalculate_metrics()` to see if it updates both baseline and filtered metrics, and if it calls `set_values` on comparison components.

---

## Task 8: Fix Adjustment Params Update Flow

**Files:**
- Modify: `src/tabs/pnl_stats.py`
- Test: Manual verification

**Step 1: Locate the issue in _recalculate_metrics()**

The issue is that `_recalculate_metrics()` recalculates baseline metrics when adjustment params change, but it may not be properly updating the comparison ribbon/grid.

Check if `_on_metrics_updated()` is being called after recalculation, or if metrics need to be explicitly pushed to UI components.

**Step 2: Fix: Ensure comparison components are updated**

After recalculating metrics in `_recalculate_metrics()`, explicitly update UI:

```python
# After calculating new metrics...
self._app_state.baseline_metrics = metrics

# Emit signal to trigger UI updates
self._app_state.metrics_updated.emit(metrics, self._app_state.filtered_metrics)
```

Or directly update the comparison components:
```python
# Update comparison displays
self._comparison_ribbon.set_values(metrics, self._app_state.filtered_metrics)
self._comparison_grid.set_values(metrics, self._app_state.filtered_metrics)
```

**Step 3: Write test for adjustment params triggering comparison update**

Add to `tests/tabs/test_pnl_stats.py`:

```python
def test_adjustment_params_update_comparison_grid(pnl_tab, qtbot) -> None:
    """Changing stop loss should update comparison grid values."""
    # Setup: Load data and get initial metrics
    initial_edge = pnl_tab._comparison_grid.get_baseline_value("edge")
    
    # Change stop loss
    pnl_tab._user_inputs_panel.set_stop_loss(15.0)
    
    # Wait for debounced recalculation
    qtbot.wait(600)
    
    # Verify comparison grid was updated
    new_edge = pnl_tab._comparison_grid.get_baseline_value("edge")
    assert new_edge != initial_edge  # Value should have changed
```

**Step 4: Run test to verify fix works**

Run: `pytest tests/tabs/test_pnl_stats.py::test_adjustment_params_update_comparison_grid -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tabs/pnl_stats.py tests/tabs/test_pnl_stats.py
git commit -m "fix: adjustment params now update comparison stats immediately

Stop Loss, Efficiency, and Fractional Kelly changes now properly
trigger updates to the Comparison Ribbon and Comparison Grid."
```

---

## Task 9: Run Full Test Suite

**Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 2: Fix any failing tests**

If any tests fail, investigate and fix.

**Step 3: Final commit if needed**

```bash
git add .
git commit -m "test: fix any test regressions from three-issues-fix"
```

---

## Task 10: Manual Verification

**Step 1: Launch the application**

Run: `python -m src.main` or appropriate entry point

**Step 2: Verify Edge % fix**

1. Load a trade dataset
2. Check Edge % value in Comparison Grid
3. Verify it matches EV (not EV × num_trades)
4. Value should be reasonable (e.g., 0.5% not 1000%)

**Step 3: Verify chart axis toggle**

1. Go to PnL Trading Stats tab
2. Find the axis toggle on the charts
3. Click "Date" - X-axis should show dates
4. Click "Trades" - X-axis should show trade numbers
5. Both Flat Stake and Kelly charts should respect the toggle

**Step 4: Verify adjustment params updating comparison**

1. Note current values in Comparison Grid
2. Change Stop Loss value
3. Verify Comparison Grid updates immediately (after debounce)
4. Change Efficiency value
5. Verify Comparison Grid updates
6. Change Fractional Kelly
7. Verify Comparison Grid updates

---

## Summary of Changes

| File | Change |
|------|--------|
| `src/core/metrics.py` | Edge = EV (not EV × num_trades) |
| `src/core/equity.py` | Add date_col parameter to both calculate methods |
| `src/ui/components/axis_mode_toggle.py` | NEW: Segmented toggle component |
| `src/ui/components/equity_chart.py` | Integrate toggle, support date axis |
| `src/tabs/pnl_stats.py` | Plumb date column, fix comparison updates |
| `tests/core/test_metrics.py` | Test for Edge = EV |
| `tests/core/test_equity.py` | Tests for date column support |
| `tests/ui/components/test_axis_mode_toggle.py` | NEW: Toggle component tests |
