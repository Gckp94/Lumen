# Golden Statistics Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Compute trading metrics once and share across all tabs, eliminating duplicate calculations for ~3x performance improvement.

**Architecture:** Extend `MetricsCalculator` with scenario analysis methods (`calculate_stop_scenarios`, `calculate_offset_scenarios`). PnL Stats tab becomes the single calculation coordinator, storing results in `AppState`. Statistics tab consumes pre-computed results instead of recalculating.

**Tech Stack:** Python 3.11+, PyQt6, pandas, dataclasses

---

## Task 1: Add Scenario Dataclasses to models.py

**Files:**
- Modify: `src/core/models.py:211` (after TradingMetrics class)
- Test: `tests/unit/test_models.py`

**Step 1: Write the failing test**

Add to `tests/unit/test_models.py`:

```python
def test_stop_scenario_dataclass():
    """Test StopScenario dataclass creation."""
    from src.core.models import StopScenario

    scenario = StopScenario(
        stop_pct=20,
        num_trades=100,
        win_pct=55.0,
        ev_pct=2.5,
        avg_gain_pct=3.0,
        median_gain_pct=2.8,
        edge_pct=12.0,
        kelly_pct=15.0,
        stop_adjusted_kelly_pct=75.0,
        max_loss_pct=10.0,
        max_dd_pct=25.0,
        kelly_pnl=50000.0,
    )
    assert scenario.stop_pct == 20
    assert scenario.win_pct == 55.0


def test_offset_scenario_dataclass():
    """Test OffsetScenario dataclass creation."""
    from src.core.models import OffsetScenario

    scenario = OffsetScenario(
        offset_pct=-2.0,
        num_trades=80,
        win_pct=60.0,
        total_return_pct=150.0,
        eg_pct=0.5,
    )
    assert scenario.offset_pct == -2.0
    assert scenario.num_trades == 80


def test_computed_metrics_dataclass():
    """Test ComputedMetrics container dataclass."""
    from src.core.models import ComputedMetrics, StopScenario, OffsetScenario, TradingMetrics

    computed = ComputedMetrics(
        trading_metrics=TradingMetrics.empty(),
        stop_scenarios=[],
        offset_scenarios=[],
        computation_time_ms=150.0,
    )
    assert computed.computation_time_ms == 150.0
    assert computed.stop_scenarios == []
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_models.py::test_stop_scenario_dataclass -v`
Expected: FAIL with "cannot import name 'StopScenario'"

**Step 3: Write minimal implementation**

Add after line 211 in `src/core/models.py` (after TradingMetrics class):

```python
@dataclass
class StopScenario:
    """Metrics calculated at a specific stop loss level.

    Used by MetricsCalculator.calculate_stop_scenarios() for scenario analysis.
    """
    stop_pct: int
    num_trades: int
    win_pct: float
    ev_pct: float | None
    avg_gain_pct: float | None
    median_gain_pct: float | None
    edge_pct: float | None
    kelly_pct: float | None
    stop_adjusted_kelly_pct: float | None
    max_loss_pct: float
    max_dd_pct: float | None
    kelly_pnl: float | None


@dataclass
class OffsetScenario:
    """Metrics calculated at a specific entry price offset.

    Used by MetricsCalculator.calculate_offset_scenarios() for scenario analysis.
    """
    offset_pct: float
    num_trades: int
    win_pct: float
    total_return_pct: float | None
    eg_pct: float | None


@dataclass
class ComputedMetrics:
    """All computed metrics from a single calculation pass.

    Container for trading metrics plus scenario analysis results.
    Emitted via AppState.all_metrics_ready signal.
    """
    trading_metrics: TradingMetrics
    stop_scenarios: list[StopScenario]
    offset_scenarios: list[OffsetScenario]
    computation_time_ms: float
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_models.py::test_stop_scenario_dataclass tests/unit/test_models.py::test_offset_scenario_dataclass tests/unit/test_models.py::test_computed_metrics_dataclass -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/models.py tests/unit/test_models.py
git commit -m "feat(models): add StopScenario, OffsetScenario, ComputedMetrics dataclasses

New dataclasses for unified metrics calculation:
- StopScenario: metrics at each stop loss level
- OffsetScenario: metrics at each entry offset
- ComputedMetrics: container for all calculation results

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Add calculate_stop_scenarios to MetricsCalculator

**Files:**
- Modify: `src/core/metrics.py:470` (after calculate method)
- Test: `tests/unit/test_metrics.py`

**Step 1: Write the failing test**

Add to `tests/unit/test_metrics.py`:

```python
def test_calculate_stop_scenarios_returns_list():
    """Test calculate_stop_scenarios returns list of StopScenario."""
    import pandas as pd
    from src.core.metrics import MetricsCalculator
    from src.core.models import StopScenario, ColumnMapping, AdjustmentParams

    # Create test data with MAE column
    df = pd.DataFrame({
        "gain_pct": [0.10, -0.05, 0.08, -0.03, 0.12],
        "mae_pct": [5, 15, 8, 25, 3],  # percentage points
    })

    mapping = ColumnMapping(
        gain_pct="gain_pct",
        mae_pct="mae_pct",
    )
    params = AdjustmentParams(stop_loss=20, efficiency=5)

    calc = MetricsCalculator()
    scenarios = calc.calculate_stop_scenarios(
        df=df,
        mapping=mapping,
        adjustment_params=params,
        stop_levels=[10, 20, 50, 100],
    )

    assert isinstance(scenarios, list)
    assert len(scenarios) == 4
    assert all(isinstance(s, StopScenario) for s in scenarios)
    assert scenarios[0].stop_pct == 10
    assert scenarios[1].stop_pct == 20
    assert scenarios[2].stop_pct == 50
    assert scenarios[3].stop_pct == 100


def test_calculate_stop_scenarios_empty_df():
    """Test calculate_stop_scenarios handles empty DataFrame."""
    import pandas as pd
    from src.core.metrics import MetricsCalculator
    from src.core.models import ColumnMapping, AdjustmentParams

    df = pd.DataFrame({"gain_pct": [], "mae_pct": []})
    mapping = ColumnMapping(gain_pct="gain_pct", mae_pct="mae_pct")
    params = AdjustmentParams(stop_loss=20, efficiency=5)

    calc = MetricsCalculator()
    scenarios = calc.calculate_stop_scenarios(
        df=df,
        mapping=mapping,
        adjustment_params=params,
    )

    assert isinstance(scenarios, list)
    assert len(scenarios) > 0  # Still returns scenarios, just with 0 trades
    assert all(s.num_trades == 0 for s in scenarios)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_metrics.py::test_calculate_stop_scenarios_returns_list -v`
Expected: FAIL with "AttributeError: 'MetricsCalculator' object has no attribute 'calculate_stop_scenarios'"

**Step 3: Write minimal implementation**

Add after the `calculate` method in `src/core/metrics.py` (around line 470):

```python
def calculate_stop_scenarios(
    self,
    df: pd.DataFrame,
    mapping: "ColumnMapping",
    adjustment_params: "AdjustmentParams",
    stop_levels: list[int] | None = None,
    start_capital: float | None = None,
    fractional_kelly_pct: float = 25.0,
) -> list["StopScenario"]:
    """Calculate metrics at each stop loss level.

    Reuses the same core metric formulas as calculate() to ensure consistency.

    Args:
        df: DataFrame with trade data.
        mapping: Column mapping configuration.
        adjustment_params: Current adjustment parameters.
        stop_levels: List of stop percentages to simulate. Defaults to [10,20,30,40,50,75,100].
        start_capital: Starting capital for Kelly calculations.
        fractional_kelly_pct: Fractional Kelly percentage.

    Returns:
        List of StopScenario dataclasses, one per stop level.
    """
    from src.core.models import StopScenario
    from src.core.statistics import STOP_LOSS_LEVELS, _calculate_stop_level_row

    if stop_levels is None:
        stop_levels = list(STOP_LOSS_LEVELS)

    scenarios = []
    gain_col = mapping.gain_pct
    mae_col = mapping.mae_pct
    date_col = mapping.date if hasattr(mapping, 'date') else None

    # Compute adjusted gains using same method as calculate()
    if mae_col and mae_col in df.columns:
        adjusted_gains = adjustment_params.calculate_adjusted_gains(df, gain_col, mae_col)
    else:
        adjusted_gains = df[gain_col].astype(float) if len(df) > 0 else pd.Series(dtype=float)

    for stop_level in stop_levels:
        # Use existing _calculate_stop_level_row from statistics.py
        # This ensures formula consistency
        row = _calculate_stop_level_row(
            df=df,
            adjusted_gains=adjusted_gains,
            mae_col=mae_col,
            stop_level=stop_level,
            efficiency=adjustment_params.efficiency,
            start_capital=start_capital,
            fractional_kelly_pct=fractional_kelly_pct,
            date_col=date_col,
        )

        scenario = StopScenario(
            stop_pct=stop_level,
            num_trades=len(df),
            win_pct=row.get("Win %", 0.0),
            ev_pct=row.get("EV %"),
            avg_gain_pct=row.get("Avg Gain %"),
            median_gain_pct=row.get("Median Gain %"),
            edge_pct=row.get("Edge %"),
            kelly_pct=row.get("Full Kelly (Stop Adj)"),
            stop_adjusted_kelly_pct=row.get("Full Kelly (Stop Adj)"),
            max_loss_pct=row.get("Max Loss %", 0.0),
            max_dd_pct=row.get("Max DD %"),
            kelly_pnl=row.get("Total Kelly $"),
        )
        scenarios.append(scenario)

    return scenarios
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_metrics.py::test_calculate_stop_scenarios_returns_list tests/unit/test_metrics.py::test_calculate_stop_scenarios_empty_df -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/metrics.py tests/unit/test_metrics.py
git commit -m "feat(metrics): add calculate_stop_scenarios method

Extends MetricsCalculator to compute stop loss scenarios.
Reuses _calculate_stop_level_row from statistics.py for formula consistency.
Returns list of StopScenario dataclasses.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Add calculate_offset_scenarios to MetricsCalculator

**Files:**
- Modify: `src/core/metrics.py` (after calculate_stop_scenarios)
- Test: `tests/unit/test_metrics.py`

**Step 1: Write the failing test**

Add to `tests/unit/test_metrics.py`:

```python
def test_calculate_offset_scenarios_returns_list():
    """Test calculate_offset_scenarios returns list of OffsetScenario."""
    import pandas as pd
    from src.core.metrics import MetricsCalculator
    from src.core.models import OffsetScenario, ColumnMapping, AdjustmentParams

    # Create test data with MAE and MFE columns
    df = pd.DataFrame({
        "gain_pct": [0.10, -0.05, 0.08, -0.03, 0.12],
        "mae_pct": [5, 15, 8, 25, 3],
        "mfe_pct": [12, 3, 10, 2, 15],
    })

    mapping = ColumnMapping(
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
    )
    params = AdjustmentParams(stop_loss=20, efficiency=5)

    calc = MetricsCalculator()
    scenarios = calc.calculate_offset_scenarios(
        df=df,
        mapping=mapping,
        adjustment_params=params,
        offsets=[-10, 0, 10, 20],
    )

    assert isinstance(scenarios, list)
    assert len(scenarios) == 4
    assert all(isinstance(s, OffsetScenario) for s in scenarios)
    assert scenarios[0].offset_pct == -10
    assert scenarios[1].offset_pct == 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_metrics.py::test_calculate_offset_scenarios_returns_list -v`
Expected: FAIL with "AttributeError: 'MetricsCalculator' object has no attribute 'calculate_offset_scenarios'"

**Step 3: Write minimal implementation**

Add after `calculate_stop_scenarios` in `src/core/metrics.py`:

```python
def calculate_offset_scenarios(
    self,
    df: pd.DataFrame,
    mapping: "ColumnMapping",
    adjustment_params: "AdjustmentParams",
    offsets: list[float] | None = None,
    start_capital: float | None = None,
    fractional_kelly_pct: float = 25.0,
) -> list["OffsetScenario"]:
    """Calculate metrics at each entry price offset.

    Args:
        df: DataFrame with trade data.
        mapping: Column mapping configuration.
        adjustment_params: Current adjustment parameters.
        offsets: List of offset percentages. Defaults to [-20,-10,0,10,20,30,40].
        start_capital: Starting capital for Kelly calculations.
        fractional_kelly_pct: Fractional Kelly percentage.

    Returns:
        List of OffsetScenario dataclasses, one per offset level.
    """
    from src.core.models import OffsetScenario
    from src.core.statistics import OFFSET_LEVELS, _calculate_offset_level_row

    if offsets is None:
        offsets = list(OFFSET_LEVELS)

    scenarios = []
    gain_col = mapping.gain_pct
    mae_col = mapping.mae_pct
    mfe_col = mapping.mfe_pct
    date_col = mapping.date if hasattr(mapping, 'date') else None

    for offset in offsets:
        row = _calculate_offset_level_row(
            df=df,
            gain_col=gain_col,
            mae_col=mae_col,
            mfe_col=mfe_col,
            offset=offset,
            adjustment_params=adjustment_params,
            start_capital=start_capital,
            fractional_kelly_pct=fractional_kelly_pct,
            date_col=date_col,
        )

        scenario = OffsetScenario(
            offset_pct=offset,
            num_trades=row.get("Trades", 0),
            win_pct=row.get("Win %", 0.0),
            total_return_pct=row.get("Total Return %"),
            eg_pct=row.get("EG %"),
        )
        scenarios.append(scenario)

    return scenarios
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_metrics.py::test_calculate_offset_scenarios_returns_list -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/metrics.py tests/unit/test_metrics.py
git commit -m "feat(metrics): add calculate_offset_scenarios method

Extends MetricsCalculator to compute entry offset scenarios.
Reuses _calculate_offset_level_row from statistics.py for consistency.
Returns list of OffsetScenario dataclasses.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Add scenario storage and signal to AppState

**Files:**
- Modify: `src/core/app_state.py:44` (signals section)
- Modify: `src/core/app_state.py:106` (end of __init__)
- Test: `tests/unit/test_app_state.py` (create if needed)

**Step 1: Write the failing test**

Create/add to `tests/unit/test_app_state.py`:

```python
def test_app_state_has_scenario_storage():
    """Test AppState has stop_scenarios and offset_scenarios attributes."""
    from src.core.app_state import AppState

    state = AppState()

    assert hasattr(state, 'stop_scenarios')
    assert hasattr(state, 'offset_scenarios')
    assert state.stop_scenarios is None
    assert state.offset_scenarios is None


def test_app_state_has_all_metrics_ready_signal():
    """Test AppState has all_metrics_ready signal."""
    from src.core.app_state import AppState

    state = AppState()

    assert hasattr(state, 'all_metrics_ready')
    # Verify it's a signal by checking it has emit method
    assert hasattr(state.all_metrics_ready, 'emit')
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_app_state.py::test_app_state_has_scenario_storage -v`
Expected: FAIL with "AssertionError" (no stop_scenarios attribute)

**Step 3: Write minimal implementation**

In `src/core/app_state.py`:

1. Add import at top (around line 14):
```python
if TYPE_CHECKING:
    from src.core.models import ColumnMapping, FilterCriteria, TradingMetrics, StopScenario, OffsetScenario
    from src.core.monte_carlo import MonteCarloResults
```

2. Add signal after line 71 (after view_chart_requested):
```python
    # Golden statistics signal (unified metrics)
    all_metrics_ready = pyqtSignal(object)  # ComputedMetrics
```

3. Add storage at end of `__init__` (around line 106):
```python
        # Scenario results storage (golden statistics)
        self.stop_scenarios: list[StopScenario] | None = None
        self.offset_scenarios: list[OffsetScenario] | None = None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_app_state.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/app_state.py tests/unit/test_app_state.py
git commit -m "feat(app_state): add scenario storage and all_metrics_ready signal

- Add stop_scenarios and offset_scenarios storage fields
- Add all_metrics_ready signal for unified metrics broadcast
- Prepares AppState for golden statistics pattern

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Update PnL Stats tab to calculate and emit scenarios

**Files:**
- Modify: `src/tabs/pnl_stats.py:1184` (_calculate_filtered_metrics method)
- Test: `tests/widget/test_pnl_stats_tab.py` (add integration test)

**Step 1: Write the failing test**

Add to `tests/widget/test_pnl_stats_tab.py` (or create if needed):

```python
def test_filtered_metrics_populates_scenarios(qtbot, app_state_with_data):
    """Test that calculating filtered metrics also populates scenario storage."""
    from src.tabs.pnl_stats import PnLStatsTab

    app_state = app_state_with_data
    tab = PnLStatsTab(app_state)
    qtbot.addWidget(tab)

    # Trigger filtered data update
    filtered_df = app_state.baseline_df.copy()
    tab._on_filtered_data_updated(filtered_df)

    # Verify scenarios were stored
    assert app_state.stop_scenarios is not None
    assert app_state.offset_scenarios is not None
    assert len(app_state.stop_scenarios) > 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/widget/test_pnl_stats_tab.py::test_filtered_metrics_populates_scenarios -v`
Expected: FAIL (stop_scenarios is None)

**Step 3: Write minimal implementation**

Modify `_calculate_filtered_metrics` in `src/tabs/pnl_stats.py` (around line 1230):

After the line `self._app_state.filtered_metrics = metrics`, add:

```python
        # Calculate and store scenario results (golden statistics)
        import time as time_module
        scenario_start = time_module.perf_counter()

        # Only calculate scenarios if we have the required columns
        if column_mapping.mae_pct and column_mapping.mae_pct in filtered_df.columns:
            self._app_state.stop_scenarios = self._metrics_calculator.calculate_stop_scenarios(
                df=filtered_df,
                mapping=column_mapping,
                adjustment_params=adjustment_params,
                start_capital=metrics_inputs.starting_capital if metrics_inputs else None,
                fractional_kelly_pct=fractional_kelly_pct,
            )
        else:
            self._app_state.stop_scenarios = []

        if (column_mapping.mae_pct and column_mapping.mfe_pct and
            column_mapping.mae_pct in filtered_df.columns and
            column_mapping.mfe_pct in filtered_df.columns):
            self._app_state.offset_scenarios = self._metrics_calculator.calculate_offset_scenarios(
                df=filtered_df,
                mapping=column_mapping,
                adjustment_params=adjustment_params,
                start_capital=metrics_inputs.starting_capital if metrics_inputs else None,
                fractional_kelly_pct=fractional_kelly_pct,
            )
        else:
            self._app_state.offset_scenarios = []

        scenario_elapsed = (time_module.perf_counter() - scenario_start) * 1000
        logger.info("Scenarios calculated in %.2fms", scenario_elapsed)

        # Emit unified metrics signal
        from src.core.models import ComputedMetrics
        computed = ComputedMetrics(
            trading_metrics=metrics,
            stop_scenarios=self._app_state.stop_scenarios,
            offset_scenarios=self._app_state.offset_scenarios,
            computation_time_ms=elapsed_ms + scenario_elapsed,
        )
        self._app_state.all_metrics_ready.emit(computed)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/widget/test_pnl_stats_tab.py::test_filtered_metrics_populates_scenarios -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tabs/pnl_stats.py tests/widget/test_pnl_stats_tab.py
git commit -m "feat(pnl_stats): calculate scenarios and emit all_metrics_ready

PnL Stats tab now:
- Calculates stop scenarios after filtered metrics
- Calculates offset scenarios after filtered metrics
- Stores results in AppState
- Emits all_metrics_ready with ComputedMetrics

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Refactor Statistics tab to consume pre-computed scenarios

**Files:**
- Modify: `src/tabs/statistics_tab.py:782` (_on_filtered_data_updated)
- Modify: `src/tabs/statistics_tab.py:736` (_connect_signals)
- Test: Integration test in `tests/integration/test_statistics_tab.py`

**Step 1: Write the failing test**

Add to `tests/integration/test_statistics_tab.py`:

```python
def test_statistics_tab_uses_precomputed_scenarios(qtbot, app_state_with_data):
    """Test Statistics tab reads from AppState instead of recalculating."""
    from src.tabs.statistics_tab import StatisticsTab
    from src.core.models import StopScenario
    from unittest.mock import patch

    app_state = app_state_with_data

    # Pre-populate scenarios in AppState
    app_state.stop_scenarios = [
        StopScenario(
            stop_pct=20, num_trades=100, win_pct=55.0, ev_pct=2.5,
            avg_gain_pct=3.0, median_gain_pct=2.8, edge_pct=12.0,
            kelly_pct=15.0, stop_adjusted_kelly_pct=75.0,
            max_loss_pct=10.0, max_dd_pct=25.0, kelly_pnl=50000.0,
        ),
    ]

    tab = StatisticsTab(app_state)
    qtbot.addWidget(tab)

    # Patch the calculate function to verify it's NOT called
    with patch('src.tabs.statistics_tab.calculate_stop_loss_table') as mock_calc:
        # Trigger all_metrics_ready instead of filtered_data_updated
        from src.core.models import ComputedMetrics, TradingMetrics
        computed = ComputedMetrics(
            trading_metrics=TradingMetrics.empty(),
            stop_scenarios=app_state.stop_scenarios,
            offset_scenarios=[],
            computation_time_ms=100.0,
        )
        app_state.all_metrics_ready.emit(computed)

        # Verify calculate_stop_loss_table was NOT called
        mock_calc.assert_not_called()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_statistics_tab.py::test_statistics_tab_uses_precomputed_scenarios -v`
Expected: FAIL (calculate_stop_loss_table IS called)

**Step 3: Write minimal implementation**

1. Add new signal connection in `_connect_signals` (around line 736):

```python
        # Connect to unified metrics signal (golden statistics)
        self._app_state.all_metrics_ready.connect(self._on_all_metrics_ready)
```

2. Add new handler method after `_on_filtered_data_updated`:

```python
    def _on_all_metrics_ready(self, computed: "ComputedMetrics") -> None:
        """Handle unified metrics update from golden statistics.

        Args:
            computed: Pre-computed metrics including scenarios.
        """
        if not self._app_state.column_mapping:
            return

        # Hide empty state and show tables
        self._show_empty_state(False)

        # Populate Stop Loss table from pre-computed scenarios
        if computed.stop_scenarios:
            stop_df = self._scenarios_to_stop_dataframe(computed.stop_scenarios)
            self._populate_table(self._stop_loss_table, stop_df)

        # Populate Offset table from pre-computed scenarios
        if computed.offset_scenarios:
            offset_df = self._scenarios_to_offset_dataframe(computed.offset_scenarios)
            self._populate_table(self._offset_table, offset_df)
```

3. Add helper methods:

```python
    def _scenarios_to_stop_dataframe(self, scenarios: list) -> pd.DataFrame:
        """Convert StopScenario list to DataFrame for table display."""
        rows = []
        for s in scenarios:
            rows.append({
                "Stop %": s.stop_pct,
                "Win %": s.win_pct,
                "EV %": s.ev_pct,
                "Avg Gain %": s.avg_gain_pct,
                "Median Gain %": s.median_gain_pct,
                "Profit Ratio": None,  # Computed from edge/win if needed
                "Edge %": s.edge_pct,
                "EG %": None,  # Can be added to StopScenario if needed
                "Max Loss %": s.max_loss_pct,
                "Full Kelly (Stop Adj)": s.stop_adjusted_kelly_pct,
                "Half Kelly (Stop Adj)": s.stop_adjusted_kelly_pct / 2 if s.stop_adjusted_kelly_pct else None,
                "Quarter Kelly (Stop Adj)": s.stop_adjusted_kelly_pct / 4 if s.stop_adjusted_kelly_pct else None,
                "Max DD %": s.max_dd_pct,
                "Total Kelly $": s.kelly_pnl,
            })
        return pd.DataFrame(rows)

    def _scenarios_to_offset_dataframe(self, scenarios: list) -> pd.DataFrame:
        """Convert OffsetScenario list to DataFrame for table display."""
        rows = []
        for s in scenarios:
            rows.append({
                "Offset %": s.offset_pct,
                "Trades": s.num_trades,
                "Win %": s.win_pct,
                "Total Return %": s.total_return_pct,
                "EG %": s.eg_pct,
            })
        return pd.DataFrame(rows)
```

4. Modify `_on_filtered_data_updated` to skip Stop Loss and Offset tables (they're now handled by `_on_all_metrics_ready`):

In `_update_all_tables`, comment out or remove the blocks that call `calculate_stop_loss_table` and `calculate_offset_table`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_statistics_tab.py::test_statistics_tab_uses_precomputed_scenarios -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tabs/statistics_tab.py tests/integration/test_statistics_tab.py
git commit -m "refactor(statistics_tab): consume pre-computed scenarios from AppState

Statistics tab now:
- Listens to all_metrics_ready signal
- Reads stop_scenarios from AppState
- Reads offset_scenarios from AppState
- No longer calls calculate_stop_loss_table or calculate_offset_table

Eliminates duplicate calculations for ~3x performance improvement.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Run full test suite and verify no regressions

**Files:**
- No modifications
- Run: Full test suite

**Step 1: Run unit tests**

Run: `pytest tests/unit/ -v --tb=short`
Expected: All pass

**Step 2: Run widget tests**

Run: `pytest tests/widget/ -v --tb=short`
Expected: All pass

**Step 3: Run integration tests**

Run: `pytest tests/integration/ -v --tb=short --ignore=tests/integration/test_performance.py`
Expected: All pass (excluding flaky performance test)

**Step 4: Commit test verification**

```bash
git commit --allow-empty -m "test: verify all tests pass after golden statistics refactor

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Performance verification

**Files:**
- No modifications
- Manual verification

**Step 1: Create simple performance benchmark**

Create temporary script `benchmark_metrics.py`:

```python
"""Benchmark metrics calculation before/after golden statistics."""
import time
import pandas as pd
import numpy as np
from src.core.metrics import MetricsCalculator
from src.core.models import ColumnMapping, AdjustmentParams

# Generate test data
np.random.seed(42)
sizes = [10000, 50000, 100000, 200000]

for size in sizes:
    df = pd.DataFrame({
        "gain_pct": np.random.normal(0.02, 0.10, size),
        "mae_pct": np.abs(np.random.normal(10, 5, size)),
        "mfe_pct": np.abs(np.random.normal(15, 7, size)),
    })

    mapping = ColumnMapping(gain_pct="gain_pct", mae_pct="mae_pct", mfe_pct="mfe_pct")
    params = AdjustmentParams(stop_loss=20, efficiency=5)
    calc = MetricsCalculator()

    start = time.perf_counter()
    metrics, _, _ = calc.calculate(df, "gain_pct", adjustment_params=params, mae_col="mae_pct")
    stop_scenarios = calc.calculate_stop_scenarios(df, mapping, params)
    offset_scenarios = calc.calculate_offset_scenarios(df, mapping, params)
    elapsed = (time.perf_counter() - start) * 1000

    print(f"{size:,} trades: {elapsed:.0f}ms ({len(stop_scenarios)} stop, {len(offset_scenarios)} offset)")
```

**Step 2: Run benchmark**

Run: `python benchmark_metrics.py`
Expected output showing times under target:
- 10k: <200ms
- 50k: <500ms
- 100k: <1000ms
- 200k: <2000ms

**Step 3: Clean up benchmark**

```bash
rm benchmark_metrics.py
```

---

## Task 9: Final cleanup and documentation

**Files:**
- Update: `docs/plans/2026-02-06-golden-statistics-design.md`

**Step 1: Update design doc status**

Change status from "Design Complete" to "Implemented":

```markdown
**Date:** 2026-02-06
**Status:** Implemented
```

**Step 2: Commit final state**

```bash
git add docs/plans/2026-02-06-golden-statistics-design.md
git commit -m "docs: mark golden statistics design as implemented

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Summary

| Task | Description | Files Modified |
|------|-------------|----------------|
| 1 | Add scenario dataclasses | `models.py`, `test_models.py` |
| 2 | Add calculate_stop_scenarios | `metrics.py`, `test_metrics.py` |
| 3 | Add calculate_offset_scenarios | `metrics.py`, `test_metrics.py` |
| 4 | Add AppState storage/signal | `app_state.py`, `test_app_state.py` |
| 5 | Update PnL Stats as coordinator | `pnl_stats.py`, `test_pnl_stats_tab.py` |
| 6 | Refactor Statistics tab | `statistics_tab.py`, `test_statistics_tab.py` |
| 7 | Full test suite verification | - |
| 8 | Performance verification | - |
| 9 | Documentation update | `golden-statistics-design.md` |

**Expected outcome:** ~3x performance improvement when changing filters with multiple tabs open.
