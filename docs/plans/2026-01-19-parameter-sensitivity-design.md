# Parameter Sensitivity Feature Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement the implementation plan that follows this design.

## Overview

Parameter Sensitivity is a new tab for testing whether filter boundaries are robust or overfitted. It answers the question: "If I had set my filter boundaries slightly differently, would my edge disappear?"

## Two Analysis Modes

### 1. Neighborhood Scan (Quick Robustness Check)

- Takes current active filters from Feature Explorer
- Tests ±5%, ±10%, ±15% perturbations of each filter's boundaries
- Perturbation = percentage of current filter range (self-scaling)
- Shows summary verdict: "Robust" / "Caution" / "Fragile"
- Expandable detail table shows metric degradation per filter

**Perturbation Types per Level:**
- Shift both bounds down
- Shift both bounds up
- Expand range (bounds move outward)
- Contract range (bounds move inward)

### 2. Parameter Sweep (Deep Exploration)

- Select 1-2 filters to sweep across a custom range
- User-configurable grid resolution (5x5 to 25x25)
- Generates line chart (1 filter) or heatmap (2 filters)
- Shows metric values across the parameter space
- Current filter position highlighted on visualization

## Key Design Decisions

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Data Source | `baseline_df` | Must test filters against full opportunity set, not already-filtered data |
| Perturbation Method | % of filter range | Self-scaling, works for any filter type, future-proof |
| Metrics | Multi-metric view | Different strategies prioritize different metrics |
| Computation | Async with progress | Consistent with Monte Carlo UX, handles large sweeps |
| Results | View + Export | CSV for data, PNG for visuals, no complex state management |

## Data Flow

### Neighborhood Scan
```
For each filter F in active_filters:
    1. Start with baseline_df
    2. Apply all filters EXCEPT F (fixed)
    3. For each perturbation level (±5%, ±10%, ±15%):
        - Apply F with perturbed bounds
        - Calculate metrics
    4. Compare to baseline (all filters applied normally)
    5. Compute degradation percentages
```

### Parameter Sweep
```
For each grid point (x, y):
    1. Start with baseline_df
    2. Apply sweep filter(s) at grid values
    3. Calculate metrics
    4. Store in result grid
```

## UI Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PARAMETER SENSITIVITY                                           [Export ▾] │
├──────────────────────┬──────────────────────────────────────────────────────┤
│                      │                                                      │
│  ┌────────────────┐  │  ┌──────────────────────────────────────────────┐   │
│  │ ANALYSIS MODE  │  │  │                                              │   │
│  │                │  │  │           VISUALIZATION AREA                 │   │
│  │ ○ Neighborhood │  │  │                                              │   │
│  │   Scan         │  │  │   - Robustness Summary (Neighborhood)        │   │
│  │                │  │  │   - Line Chart (1D Sweep)                    │   │
│  │ ○ Parameter    │  │  │   - Heatmap (2D Sweep)                       │   │
│  │   Sweep        │  │  │                                              │   │
│  │                │  │  └──────────────────────────────────────────────┘   │
│  ├────────────────┤  │                                                      │
│  │ CONFIGURATION  │  │  ┌──────────────────────────────────────────────┐   │
│  │ [Mode-specific │  │  │              DETAIL TABLE                     │   │
│  │  controls]     │  │  │   (Expandable metric degradation grid)       │   │
│  ├────────────────┤  │  └──────────────────────────────────────────────┘   │
│  │ METRIC SELECT  │  │                                                      │
│  │ ☑ Win Rate     │  │  ┌──────────────────────────────────────────────┐   │
│  │ ☑ Profit Factor│  │  │  [Run Analysis]              [Cancel]        │   │
│  │ ☑ Expected Val │  │  │  ████████████░░░░░░░░░░░░░  45%              │   │
│  └────────────────┘  │  └──────────────────────────────────────────────┘   │
│                      │                                                      │
└──────────────────────┴──────────────────────────────────────────────────────┘
```

## Color Language

| Element | Color | Meaning |
|---------|-------|---------|
| Robust | `#22C55E` (Emerald) | Metric degradation < 10% |
| Caution | `#F59E0B` (Amber) | Degradation 10-25% |
| Fragile | `#EF4444` (Red) | Degradation > 25% |
| Neutral | `#64748B` (Slate) | Unchanged/baseline |
| Heatmap | Emerald → Amber → Red | Continuous robustness scale |

## File Structure

```
src/
├── core/
│   └── parameter_sensitivity.py    # Engine, Config, Results dataclasses
│
├── tabs/
│   └── parameter_sensitivity.py    # ParameterSensitivityTab (QWidget)
│
└── ui/
    └── components/
        ├── sensitivity_sidebar.py   # Mode selector, config panels
        ├── sensitivity_heatmap.py   # pyqtgraph-based heatmap widget
        └── sensitivity_table.py     # Degradation detail table

tests/
├── unit/
│   └── test_parameter_sensitivity_engine.py
│
└── widget/
    └── test_parameter_sensitivity_tab.py
```

## Core Data Structures

```python
@dataclass
class ParameterSensitivityConfig:
    mode: Literal["neighborhood", "sweep"]
    
    # Neighborhood scan settings
    perturbation_levels: tuple[float, ...] = (0.05, 0.10, 0.15)
    
    # Sweep settings
    sweep_filter_1: str | None = None
    sweep_range_1: tuple[float, float] | None = None
    sweep_filter_2: str | None = None
    sweep_range_2: tuple[float, float] | None = None
    grid_resolution: int = 10
    
    # Metrics to compute
    metrics: list[str] = ("win_rate", "profit_factor", "expected_value")
    primary_metric: str = "expected_value"


@dataclass
class NeighborhoodResult:
    filter_name: str
    baseline_metrics: dict[str, float]
    perturbations: dict[float, dict[str, float]]  # level → metric → value
    worst_degradation: float
    worst_metric: str
    worst_level: float
    status: Literal["robust", "caution", "fragile"]


@dataclass
class SweepResult:
    filter_1_name: str
    filter_1_values: np.ndarray
    filter_2_name: str | None
    filter_2_values: np.ndarray | None
    metric_grids: dict[str, np.ndarray]  # metric_name → 2D array
    current_position: tuple[int, int] | None
```

## Integration Points

1. **Main Window**: Register new tab with dock manager
2. **AppState**: Add sensitivity signals (started, progress, completed, error)
3. **FilterEngine**: Reuse existing `apply_filters()` - no changes needed
4. **MetricsCalculator**: Reuse existing `calculate()` - no changes needed
5. **Export**: Add CSV export for sweep grids, PNG export for heatmap

## Dependencies

No new external dependencies. Uses existing:
- `pyqtgraph` – Heatmap (ImageItem) and line charts
- `pandas` / `numpy` – Data manipulation
- `PyQt6` – UI components
