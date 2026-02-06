# Golden Statistics: Unified Metrics Calculation

**Date:** 2026-02-06
**Status:** Implemented

## Problem

When filters change in Lumen, multiple tabs independently calculate the same metrics:
- PnL Stats tab uses `MetricsCalculator`
- Statistics tab uses custom functions in `statistics.py` (duplicate formulas)
- Each tab recalculates from scratch

This causes:
1. **3-4x slower performance** than necessary
2. **Risk of formula drift** between duplicate implementations
3. **Wasted computation** on large datasets (200k+ trades)

## Solution

**Compute once, share everywhere.**

Extend `MetricsCalculator` to be the single source of truth for all trading metrics including scenario analysis. Calculate everything in one pass, store results in `AppState`, and have tabs display pre-computed results.

## Architecture

### Current Flow (Problem)
```
Filter Change
    ↓
filtered_data_updated signal
    ↓
Each tab independently calculates metrics:
  • PnL Stats → MetricsCalculator
  • Statistics → Custom functions (duplicate)
  • Breakdown → BreakdownCalculator
```

### New Flow (Solution)
```
Filter Change
    ↓
filtered_data_updated signal
    ↓
Single Calculation Coordinator (PnL Stats tab):
  1. MetricsCalculator.calculate() → core metrics
  2. MetricsCalculator.calculate_stop_scenarios()
  3. MetricsCalculator.calculate_offset_scenarios()
  4. Store ALL results in AppState
    ↓
all_metrics_ready signal
    ↓
Tabs display pre-computed results:
  • PnL Stats → reads core metrics
  • Statistics → reads scenario results
  • Breakdown → unchanged (time-based aggregation)
```

## New Data Models

### models.py additions

```python
@dataclass
class StopScenario:
    """Metrics calculated at a specific stop loss level."""
    stop_pct: int
    num_trades: int
    win_rate: float
    ev_pct: float
    avg_gain_pct: float
    median_gain_pct: float
    edge_pct: float
    kelly_pct: float
    stop_adjusted_kelly_pct: float
    max_dd_pct: float


@dataclass
class OffsetScenario:
    """Metrics calculated at a specific entry price offset."""
    offset_pct: float
    num_trades: int
    win_rate: float
    total_return_pct: float
    eg_pct: float


@dataclass
class ComputedMetrics:
    """All computed metrics from a single calculation pass."""
    trading_metrics: TradingMetrics
    stop_scenarios: list[StopScenario]
    offset_scenarios: list[OffsetScenario]
    computation_time_ms: float
```

## MetricsCalculator Extensions

### New methods

```python
class MetricsCalculator:
    # Existing (unchanged)
    def calculate(self, df, ...) -> TradingMetrics:
        ...

    # NEW: Stop loss scenario analysis
    def calculate_stop_scenarios(
        self,
        df: pd.DataFrame,
        stop_levels: list[int] = [5, 10, 15, 20, 25, 30, 40, 50, 75, 100],
        efficiency_pct: float = 5.0
    ) -> list[StopScenario]:
        """Calculate metrics at each stop loss level.

        Reuses internal _calculate_core_metrics() for consistency.
        Requires 'mae_pct' column in DataFrame.
        """
        ...

    # NEW: Entry offset scenario analysis
    def calculate_offset_scenarios(
        self,
        df: pd.DataFrame,
        offsets: list[float] = [-2, -1, -0.5, 0, 0.5, 1, 2]
    ) -> list[OffsetScenario]:
        """Calculate metrics at each entry price offset."""
        ...

    # NEW: Internal shared logic
    def _calculate_core_metrics(
        self,
        gains: pd.Series
    ) -> dict:
        """Calculate win_rate, ev, kelly, edge from a gains series.

        Used by calculate(), calculate_stop_scenarios(), etc.
        Single source of truth for all metric formulas.
        """
        ...
```

## AppState Changes

### New fields and signals

```python
class AppState(QObject):
    # Existing signals (keep)
    filtered_data_updated = pyqtSignal(pd.DataFrame)
    metrics_updated = pyqtSignal(object, object)  # backward compat

    # NEW signal
    all_metrics_ready = pyqtSignal(object)  # ComputedMetrics

    # Existing storage (keep)
    baseline_metrics: TradingMetrics | None
    filtered_metrics: TradingMetrics | None

    # NEW storage
    stop_scenarios: list[StopScenario] | None
    offset_scenarios: list[OffsetScenario] | None
```

## Signal Flow

```
User changes filter
    ↓
FilterPanel emits filtered_data_updated(df)
    ↓
PnL Stats tab._on_filtered_data_updated():
    ├─ 1. trading_metrics = MetricsCalculator.calculate(df)
    ├─ 2. stop_scenarios = MetricsCalculator.calculate_stop_scenarios(df)
    ├─ 3. offset_scenarios = MetricsCalculator.calculate_offset_scenarios(df)
    ├─ 4. Store all in AppState
    └─ 5. Emit: app_state.all_metrics_ready.emit(computed_metrics)
    ↓
Tabs receive all_metrics_ready:
    ├─ PnL Stats: Update displays (already has data)
    ├─ Statistics: Read from app_state.stop_scenarios
    └─ Feature Explorer: No change (doesn't use metrics)
```

## Tab Changes

### PnL Stats Tab (coordinator)
- Add calls to new scenario methods after existing `calculate()`
- Store scenario results in AppState
- Emit `all_metrics_ready` signal
- Display logic unchanged

### Statistics Tab (consumer)
- **Remove:** Direct calls to `calculate_stop_loss_table()`, etc.
- **Add:** Listen to `all_metrics_ready` signal
- **Change:** Read from `app_state.stop_scenarios` instead of calculating
- **Keep:** Table rendering logic

### Other Tabs
- Feature Explorer: No changes (doesn't calculate metrics)
- Chart Viewer: No changes (doesn't calculate metrics)
- Breakdown: No changes (time-based aggregation is different)
- Data Input: No changes (handles baseline only)

## Performance Expectations

| Dataset Size | Current | After | Speedup |
|--------------|---------|-------|---------|
| 10k trades   | ~300-500ms | ~100-150ms | 3x |
| 50k trades   | ~800-1200ms | ~250-400ms | 3x |
| 200k trades  | ~2000-3000ms | ~600-900ms | 3x |

## Memory Impact

Negligible additional memory:
- `StopScenario`: ~10 fields × 10 levels = ~800 bytes
- `OffsetScenario`: ~5 fields × 7 offsets = ~280 bytes
- Total: ~1KB per calculation

Heavy data (winner_gains, loser_gains lists) already exists in TradingMetrics.

## Edge Cases

1. **Empty filtered dataset** - Return zeroed metrics and empty scenario lists
2. **Missing MAE/MFE columns** - Return empty scenario lists; Statistics tab shows message
3. **Tab not visible** - Tabs can skip rendering if not visible
4. **Rapid filter changes** - Existing debounce patterns sufficient

## Files to Modify

| File | Changes |
|------|---------|
| `src/core/models.py` | Add dataclasses |
| `src/core/metrics.py` | Add scenario methods, extract shared logic |
| `src/core/app_state.py` | Add fields and signal |
| `src/tabs/pnl_stats.py` | Coordinate calculation, emit signal |
| `src/tabs/statistics_tab.py` | Remove calculations, consume from AppState |

## Files Unchanged

- `src/tabs/feature_explorer.py`
- `src/tabs/chart_viewer.py`
- `src/tabs/breakdown.py`
- `src/tabs/data_input.py`

## Testing Approach

1. Unit tests for new `MetricsCalculator` methods
2. Verify Statistics tab shows identical values before/after
3. Performance benchmarks at 10k, 50k, 200k trades

## Future Optimizations

If 600-900ms for 200k trades is still slow:
- Move scenario calculations to background thread
- Add incremental caching for repeated filter states
