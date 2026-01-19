# Parameter Sensitivity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Parameter Sensitivity tab that tests filter boundary robustness to detect overfitting.

**Architecture:** New `ParameterSensitivityEngine` runs perturbation tests on baseline data via existing `FilterEngine` and `MetricsCalculator`. Async worker thread pattern mirrors Monte Carlo. New tab with sidebar configuration and visualization area.

**Tech Stack:** PyQt6, pyqtgraph (heatmap), pandas/numpy, existing FilterEngine + MetricsCalculator

---

## Task 1: Core Data Structures

**Files:**
- Create: `src/core/parameter_sensitivity.py`
- Test: `tests/unit/test_parameter_sensitivity.py`

### Step 1: Write failing test for config dataclass

```python
# tests/unit/test_parameter_sensitivity.py
"""Tests for parameter sensitivity engine."""

import pytest
import numpy as np
import pandas as pd

from src.core.parameter_sensitivity import (
    ParameterSensitivityConfig,
    NeighborhoodResult,
    SweepResult,
)


class TestParameterSensitivityConfig:
    """Tests for ParameterSensitivityConfig dataclass."""

    def test_default_config_valid(self):
        """Default configuration should be valid."""
        config = ParameterSensitivityConfig()
        assert config.mode == "neighborhood"
        assert config.perturbation_levels == (0.05, 0.10, 0.15)
        assert config.grid_resolution == 10
        assert "win_rate" in config.metrics

    def test_sweep_mode_config(self):
        """Sweep mode configuration should store filter settings."""
        config = ParameterSensitivityConfig(
            mode="sweep",
            sweep_filter_1="Entry Time",
            sweep_range_1=(9.0, 12.0),
            sweep_filter_2="Gap %",
            sweep_range_2=(2.0, 8.0),
            grid_resolution=15,
        )
        assert config.mode == "sweep"
        assert config.sweep_filter_1 == "Entry Time"
        assert config.grid_resolution == 15

    def test_invalid_mode_raises(self):
        """Invalid mode should raise ValueError."""
        with pytest.raises(ValueError, match="mode must be"):
            ParameterSensitivityConfig(mode="invalid")

    def test_invalid_grid_resolution_raises(self):
        """Grid resolution outside 5-25 should raise ValueError."""
        with pytest.raises(ValueError, match="grid_resolution"):
            ParameterSensitivityConfig(grid_resolution=3)
        with pytest.raises(ValueError, match="grid_resolution"):
            ParameterSensitivityConfig(grid_resolution=30)
```

### Step 2: Run test to verify it fails

```bash
cd "C:\Users\Gerry Chan\gap_backtest\Lumen\.worktrees\parameter-sensitivity"
python -m pytest tests/unit/test_parameter_sensitivity.py::TestParameterSensitivityConfig -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'src.core.parameter_sensitivity'"

### Step 3: Write minimal implementation

```python
# src/core/parameter_sensitivity.py
"""Parameter sensitivity analysis engine for testing filter robustness."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ParameterSensitivityConfig:
    """Configuration for parameter sensitivity analysis.

    Attributes:
        mode: Analysis mode - 'neighborhood' for quick scan, 'sweep' for deep exploration.
        perturbation_levels: Fraction of filter range to perturb (e.g., 0.10 = ±10%).
        sweep_filter_1: Column name for first sweep filter (X-axis).
        sweep_range_1: Min/max range for first sweep filter.
        sweep_filter_2: Optional column name for second sweep filter (Y-axis).
        sweep_range_2: Min/max range for second sweep filter.
        grid_resolution: Number of steps in each dimension (5-25).
        metrics: List of metric names to calculate.
        primary_metric: Metric to use for heatmap coloring.
    """

    mode: Literal["neighborhood", "sweep"] = "neighborhood"
    perturbation_levels: tuple[float, ...] = (0.05, 0.10, 0.15)
    sweep_filter_1: str | None = None
    sweep_range_1: tuple[float, float] | None = None
    sweep_filter_2: str | None = None
    sweep_range_2: tuple[float, float] | None = None
    grid_resolution: int = 10
    metrics: tuple[str, ...] = ("win_rate", "profit_factor", "expected_value")
    primary_metric: str = "expected_value"

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.mode not in ("neighborhood", "sweep"):
            raise ValueError("mode must be 'neighborhood' or 'sweep'")
        if not 5 <= self.grid_resolution <= 25:
            raise ValueError("grid_resolution must be between 5 and 25")


@dataclass
class NeighborhoodResult:
    """Result of neighborhood scan for a single filter.

    Attributes:
        filter_name: Name of the filter tested.
        filter_column: Column name the filter applies to.
        baseline_metrics: Metrics with original filter bounds.
        perturbations: Dict mapping perturbation level to metrics dict.
        worst_degradation: Largest percentage drop in primary metric.
        worst_metric: Which metric had worst degradation.
        worst_level: Perturbation level that caused worst degradation.
        status: Classification based on worst_degradation.
    """

    filter_name: str
    filter_column: str
    baseline_metrics: dict[str, float]
    perturbations: dict[float, dict[str, float]]
    worst_degradation: float
    worst_metric: str
    worst_level: float
    status: Literal["robust", "caution", "fragile"]


@dataclass
class SweepResult:
    """Result of parameter sweep analysis.

    Attributes:
        filter_1_name: Name of first filter (X-axis).
        filter_1_values: Array of values tested for filter 1.
        filter_2_name: Name of second filter (Y-axis), None for 1D sweep.
        filter_2_values: Array of values for filter 2, None for 1D sweep.
        metric_grids: Dict mapping metric name to 2D numpy array of values.
        current_position: Grid indices of current filter position, if applicable.
    """

    filter_1_name: str
    filter_1_values: np.ndarray
    filter_2_name: str | None
    filter_2_values: np.ndarray | None
    metric_grids: dict[str, np.ndarray]
    current_position: tuple[int, int] | None
```

### Step 4: Run test to verify it passes

```bash
python -m pytest tests/unit/test_parameter_sensitivity.py::TestParameterSensitivityConfig -v
```

Expected: PASS (4 tests)

### Step 5: Commit

```bash
git add src/core/parameter_sensitivity.py tests/unit/test_parameter_sensitivity.py
git commit -m "feat(sensitivity): add core data structures

- Add ParameterSensitivityConfig with validation
- Add NeighborhoodResult and SweepResult dataclasses"
```

---

## Task 2: Neighborhood Scan Engine

**Files:**
- Modify: `src/core/parameter_sensitivity.py`
- Test: `tests/unit/test_parameter_sensitivity.py`

### Step 1: Write failing test for engine initialization

```python
# Add to tests/unit/test_parameter_sensitivity.py

from src.core.parameter_sensitivity import ParameterSensitivityEngine
from src.core.models import FilterCriteria


class TestParameterSensitivityEngine:
    """Tests for ParameterSensitivityEngine."""

    @pytest.fixture
    def sample_df(self):
        """Create sample trading data."""
        np.random.seed(42)
        n = 100
        return pd.DataFrame({
            "gain_pct": np.random.uniform(-0.05, 0.10, n),
            "entry_time": np.random.uniform(9.0, 16.0, n),
            "gap_pct": np.random.uniform(1.0, 10.0, n),
        })

    @pytest.fixture
    def sample_filters(self):
        """Create sample filters."""
        return [
            FilterCriteria(column="entry_time", operator="between", min_val=9.5, max_val=11.0),
            FilterCriteria(column="gap_pct", operator="between", min_val=2.0, max_val=6.0),
        ]

    def test_engine_initialization(self, sample_df, sample_filters):
        """Engine should initialize with baseline data and filters."""
        engine = ParameterSensitivityEngine(
            baseline_df=sample_df,
            column_mapping={"gain": "gain_pct"},
            active_filters=sample_filters,
        )
        assert engine._baseline_df is not None
        assert len(engine._active_filters) == 2

    def test_engine_cancel(self, sample_df, sample_filters):
        """Engine should support cancellation."""
        engine = ParameterSensitivityEngine(
            baseline_df=sample_df,
            column_mapping={"gain": "gain_pct"},
            active_filters=sample_filters,
        )
        assert not engine._cancelled
        engine.cancel()
        assert engine._cancelled
```

### Step 2: Run test to verify it fails

```bash
python -m pytest tests/unit/test_parameter_sensitivity.py::TestParameterSensitivityEngine::test_engine_initialization -v
```

Expected: FAIL with "cannot import name 'ParameterSensitivityEngine'"

### Step 3: Write minimal engine implementation

```python
# Add to src/core/parameter_sensitivity.py after the dataclasses

from src.core.models import FilterCriteria


class ParameterSensitivityEngine:
    """Engine for running parameter sensitivity analysis.

    Tests filter boundary robustness by applying perturbations and
    measuring metric degradation.

    Example:
        >>> config = ParameterSensitivityConfig(mode="neighborhood")
        >>> engine = ParameterSensitivityEngine(baseline_df, col_map, filters)
        >>> results = engine.run_neighborhood_scan(config)
    """

    def __init__(
        self,
        baseline_df: pd.DataFrame,
        column_mapping: dict[str, str],
        active_filters: list[FilterCriteria],
    ) -> None:
        """Initialize the sensitivity engine.

        Args:
            baseline_df: Data BEFORE user filters (but after first-trigger).
            column_mapping: Column name mappings (must include 'gain').
            active_filters: Current active filters to test.
        """
        self._baseline_df = baseline_df
        self._column_mapping = column_mapping
        self._active_filters = active_filters
        self._cancelled = False

    def cancel(self) -> None:
        """Request cancellation of running analysis."""
        self._cancelled = True
```

### Step 4: Run test to verify it passes

```bash
python -m pytest tests/unit/test_parameter_sensitivity.py::TestParameterSensitivityEngine -v
```

Expected: PASS (2 tests)

### Step 5: Commit

```bash
git add src/core/parameter_sensitivity.py tests/unit/test_parameter_sensitivity.py
git commit -m "feat(sensitivity): add engine initialization and cancel support"
```

---

## Task 3: Neighborhood Scan - Perturbation Logic

**Files:**
- Modify: `src/core/parameter_sensitivity.py`
- Test: `tests/unit/test_parameter_sensitivity.py`

### Step 1: Write failing test for perturbation generation

```python
# Add to TestParameterSensitivityEngine class

def test_generate_perturbations(self, sample_df, sample_filters):
    """Should generate perturbed filter configurations."""
    engine = ParameterSensitivityEngine(
        baseline_df=sample_df,
        column_mapping={"gain": "gain_pct"},
        active_filters=sample_filters,
    )
    
    # Test perturbation of entry_time filter (9.5 - 11.0, range = 1.5)
    original = sample_filters[0]
    perturbed = engine._generate_perturbations(original, level=0.10)
    
    # Should return 4 variations: shift down, shift up, expand, contract
    assert len(perturbed) == 4
    
    # Check shift down (both bounds - 10% of range = -0.15)
    assert perturbed[0].min_val == pytest.approx(9.35, abs=0.01)
    assert perturbed[0].max_val == pytest.approx(10.85, abs=0.01)
    
    # Check shift up (both bounds + 10% of range = +0.15)
    assert perturbed[1].min_val == pytest.approx(9.65, abs=0.01)
    assert perturbed[1].max_val == pytest.approx(11.15, abs=0.01)
```

### Step 2: Run test to verify it fails

```bash
python -m pytest tests/unit/test_parameter_sensitivity.py::TestParameterSensitivityEngine::test_generate_perturbations -v
```

Expected: FAIL with "AttributeError: 'ParameterSensitivityEngine' object has no attribute '_generate_perturbations'"

### Step 3: Implement perturbation generation

```python
# Add method to ParameterSensitivityEngine class

def _generate_perturbations(
    self,
    filter_def: FilterCriteria,
    level: float,
) -> list[FilterCriteria]:
    """Generate perturbed versions of a filter.

    Args:
        filter_def: Original filter to perturb.
        level: Perturbation level as fraction of range (e.g., 0.10 = 10%).

    Returns:
        List of 4 FilterCriteria: shift down, shift up, expand, contract.
    """
    if filter_def.min_val is None or filter_def.max_val is None:
        # Can't perturb partial bounds
        return []

    range_size = filter_def.max_val - filter_def.min_val
    delta = range_size * level

    return [
        # Shift both bounds down
        FilterCriteria(
            column=filter_def.column,
            operator=filter_def.operator,
            min_val=filter_def.min_val - delta,
            max_val=filter_def.max_val - delta,
        ),
        # Shift both bounds up
        FilterCriteria(
            column=filter_def.column,
            operator=filter_def.operator,
            min_val=filter_def.min_val + delta,
            max_val=filter_def.max_val + delta,
        ),
        # Expand range (bounds move outward)
        FilterCriteria(
            column=filter_def.column,
            operator=filter_def.operator,
            min_val=filter_def.min_val - delta,
            max_val=filter_def.max_val + delta,
        ),
        # Contract range (bounds move inward)
        FilterCriteria(
            column=filter_def.column,
            operator=filter_def.operator,
            min_val=filter_def.min_val + delta,
            max_val=filter_def.max_val - delta,
        ),
    ]
```

### Step 4: Run test to verify it passes

```bash
python -m pytest tests/unit/test_parameter_sensitivity.py::TestParameterSensitivityEngine::test_generate_perturbations -v
```

Expected: PASS

### Step 5: Commit

```bash
git add src/core/parameter_sensitivity.py tests/unit/test_parameter_sensitivity.py
git commit -m "feat(sensitivity): add perturbation generation logic"
```

---

## Task 4: Neighborhood Scan - Metrics Calculation

**Files:**
- Modify: `src/core/parameter_sensitivity.py`
- Test: `tests/unit/test_parameter_sensitivity.py`

### Step 1: Write failing test for metrics extraction

```python
# Add to TestParameterSensitivityEngine class

def test_calculate_metrics_for_config(self, sample_df, sample_filters):
    """Should calculate metrics for a filter configuration."""
    engine = ParameterSensitivityEngine(
        baseline_df=sample_df,
        column_mapping={"gain": "gain_pct"},
        active_filters=sample_filters,
    )
    
    metrics = engine._calculate_metrics_for_filters(sample_filters)
    
    assert "win_rate" in metrics
    assert "profit_factor" in metrics
    assert "expected_value" in metrics
    assert isinstance(metrics["win_rate"], float)
```

### Step 2: Run test to verify it fails

```bash
python -m pytest tests/unit/test_parameter_sensitivity.py::TestParameterSensitivityEngine::test_calculate_metrics_for_config -v
```

Expected: FAIL with "AttributeError: '_calculate_metrics_for_filters'"

### Step 3: Implement metrics calculation

```python
# Add imports at top of file
from src.core.filter_engine import FilterEngine
from src.core.metrics import MetricsCalculator

# Add method to ParameterSensitivityEngine class

def _calculate_metrics_for_filters(
    self,
    filters: list[FilterCriteria],
) -> dict[str, float]:
    """Apply filters and calculate metrics.

    Args:
        filters: List of filters to apply to baseline data.

    Returns:
        Dict mapping metric name to value.
    """
    filter_engine = FilterEngine()
    filtered_df = filter_engine.apply_filters(self._baseline_df, filters)

    if len(filtered_df) == 0:
        # No trades pass filters - return zeros
        return {
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "expected_value": 0.0,
            "num_trades": 0,
        }

    gain_col = self._column_mapping.get("gain", "gain_pct")
    calculator = MetricsCalculator()
    metrics_result, _, _ = calculator.calculate(
        df=filtered_df,
        gain_col=gain_col,
        derived=True,
    )

    return {
        "win_rate": metrics_result.win_rate or 0.0,
        "profit_factor": (
            abs(metrics_result.avg_winner / metrics_result.avg_loser)
            if metrics_result.avg_winner and metrics_result.avg_loser
            else 0.0
        ),
        "expected_value": metrics_result.ev or 0.0,
        "num_trades": metrics_result.num_trades,
    }
```

### Step 4: Run test to verify it passes

```bash
python -m pytest tests/unit/test_parameter_sensitivity.py::TestParameterSensitivityEngine::test_calculate_metrics_for_config -v
```

Expected: PASS

### Step 5: Commit

```bash
git add src/core/parameter_sensitivity.py tests/unit/test_parameter_sensitivity.py
git commit -m "feat(sensitivity): add metrics calculation for filter configs"
```

---

## Task 5: Neighborhood Scan - Full Scan Method

**Files:**
- Modify: `src/core/parameter_sensitivity.py`
- Test: `tests/unit/test_parameter_sensitivity.py`

### Step 1: Write failing test for neighborhood scan

```python
# Add to TestParameterSensitivityEngine class

def test_run_neighborhood_scan(self, sample_df, sample_filters):
    """Should run complete neighborhood scan and return results."""
    engine = ParameterSensitivityEngine(
        baseline_df=sample_df,
        column_mapping={"gain": "gain_pct"},
        active_filters=sample_filters,
    )
    config = ParameterSensitivityConfig(
        mode="neighborhood",
        perturbation_levels=(0.05, 0.10),
        metrics=("win_rate", "expected_value"),
    )
    
    results = engine.run_neighborhood_scan(config)
    
    # Should have result for each filter
    assert len(results) == 2
    
    # Check first result structure
    result = results[0]
    assert isinstance(result, NeighborhoodResult)
    assert result.filter_column == "entry_time"
    assert result.baseline_metrics is not None
    assert 0.05 in result.perturbations
    assert 0.10 in result.perturbations
    assert result.status in ("robust", "caution", "fragile")

def test_neighborhood_scan_with_progress(self, sample_df, sample_filters):
    """Should call progress callback during scan."""
    engine = ParameterSensitivityEngine(
        baseline_df=sample_df,
        column_mapping={"gain": "gain_pct"},
        active_filters=sample_filters,
    )
    config = ParameterSensitivityConfig(mode="neighborhood")
    
    progress_calls = []
    def on_progress(current, total):
        progress_calls.append((current, total))
    
    engine.run_neighborhood_scan(config, progress_callback=on_progress)
    
    assert len(progress_calls) > 0
    # Final call should be complete
    assert progress_calls[-1][0] == progress_calls[-1][1]
```

### Step 2: Run test to verify it fails

```bash
python -m pytest tests/unit/test_parameter_sensitivity.py::TestParameterSensitivityEngine::test_run_neighborhood_scan -v
```

Expected: FAIL with "AttributeError: 'run_neighborhood_scan'"

### Step 3: Implement neighborhood scan

```python
# Add to ParameterSensitivityEngine class

def _classify_degradation(self, degradation: float) -> Literal["robust", "caution", "fragile"]:
    """Classify degradation level into status category.

    Args:
        degradation: Percentage degradation (e.g., 15.0 for 15% drop).

    Returns:
        Status classification.
    """
    if degradation < 10.0:
        return "robust"
    elif degradation < 25.0:
        return "caution"
    else:
        return "fragile"

def run_neighborhood_scan(
    self,
    config: ParameterSensitivityConfig,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[NeighborhoodResult]:
    """Run neighborhood scan on all active filters.

    For each filter, tests perturbations while keeping other filters fixed.

    Args:
        config: Configuration for the scan.
        progress_callback: Optional callback for progress updates (current, total).

    Returns:
        List of NeighborhoodResult, one per active filter.
    """
    self._cancelled = False
    results: list[NeighborhoodResult] = []

    # Calculate total steps for progress
    num_filters = len(self._active_filters)
    num_levels = len(config.perturbation_levels)
    perturbations_per_level = 4  # shift down, shift up, expand, contract
    total_steps = num_filters * (1 + num_levels * perturbations_per_level)
    current_step = 0

    for filter_idx, test_filter in enumerate(self._active_filters):
        if self._cancelled:
            break

        # Get other filters (keep fixed)
        other_filters = [f for i, f in enumerate(self._active_filters) if i != filter_idx]

        # Calculate baseline metrics (with all filters including test filter)
        baseline_metrics = self._calculate_metrics_for_filters(self._active_filters)
        current_step += 1
        if progress_callback:
            progress_callback(current_step, total_steps)

        # Test perturbations
        perturbation_results: dict[float, dict[str, float]] = {}
        worst_degradation = 0.0
        worst_metric = config.primary_metric
        worst_level = config.perturbation_levels[0]

        for level in config.perturbation_levels:
            if self._cancelled:
                break

            perturbed_filters = self._generate_perturbations(test_filter, level)
            level_metrics_list: list[dict[str, float]] = []

            for perturbed in perturbed_filters:
                if self._cancelled:
                    break

                # Apply other filters + perturbed test filter
                test_filters = other_filters + [perturbed]
                metrics = self._calculate_metrics_for_filters(test_filters)
                level_metrics_list.append(metrics)

                current_step += 1
                if progress_callback:
                    progress_callback(current_step, total_steps)

            # Average metrics across all perturbation types at this level
            if level_metrics_list:
                avg_metrics: dict[str, float] = {}
                for metric_name in config.metrics:
                    values = [m.get(metric_name, 0.0) for m in level_metrics_list]
                    avg_metrics[metric_name] = sum(values) / len(values)
                perturbation_results[level] = avg_metrics

                # Check for worst degradation
                baseline_val = baseline_metrics.get(config.primary_metric, 0.0)
                perturbed_val = avg_metrics.get(config.primary_metric, 0.0)
                if baseline_val != 0:
                    degradation = ((baseline_val - perturbed_val) / abs(baseline_val)) * 100
                    if degradation > worst_degradation:
                        worst_degradation = degradation
                        worst_level = level

        # Create result
        results.append(NeighborhoodResult(
            filter_name=f"{test_filter.column}: {test_filter.min_val:.2f} - {test_filter.max_val:.2f}",
            filter_column=test_filter.column,
            baseline_metrics=baseline_metrics,
            perturbations=perturbation_results,
            worst_degradation=worst_degradation,
            worst_metric=worst_metric,
            worst_level=worst_level,
            status=self._classify_degradation(worst_degradation),
        ))

    # Final progress
    if progress_callback and not self._cancelled:
        progress_callback(total_steps, total_steps)

    return results
```

Also add the import at the top:
```python
from typing import Callable, Literal
```

### Step 4: Run test to verify it passes

```bash
python -m pytest tests/unit/test_parameter_sensitivity.py::TestParameterSensitivityEngine::test_run_neighborhood_scan -v
python -m pytest tests/unit/test_parameter_sensitivity.py::TestParameterSensitivityEngine::test_neighborhood_scan_with_progress -v
```

Expected: PASS (2 tests)

### Step 5: Commit

```bash
git add src/core/parameter_sensitivity.py tests/unit/test_parameter_sensitivity.py
git commit -m "feat(sensitivity): implement neighborhood scan algorithm

- Test perturbations for each active filter
- Calculate metrics for perturbed configurations
- Track worst degradation and classify robustness"
```

---

## Task 6: Parameter Sweep Engine

**Files:**
- Modify: `src/core/parameter_sensitivity.py`
- Test: `tests/unit/test_parameter_sensitivity.py`

### Step 1: Write failing test for 1D sweep

```python
# Add to TestParameterSensitivityEngine class

def test_run_parameter_sweep_1d(self, sample_df):
    """Should run 1D parameter sweep (single filter)."""
    engine = ParameterSensitivityEngine(
        baseline_df=sample_df,
        column_mapping={"gain": "gain_pct"},
        active_filters=[],
    )
    config = ParameterSensitivityConfig(
        mode="sweep",
        sweep_filter_1="entry_time",
        sweep_range_1=(9.0, 12.0),
        sweep_filter_2=None,
        sweep_range_2=None,
        grid_resolution=5,
        metrics=("win_rate", "expected_value"),
    )
    
    result = engine.run_parameter_sweep(config)
    
    assert isinstance(result, SweepResult)
    assert result.filter_1_name == "entry_time"
    assert len(result.filter_1_values) == 5
    assert result.filter_2_name is None
    assert result.filter_2_values is None
    assert "win_rate" in result.metric_grids
    assert result.metric_grids["win_rate"].shape == (5,)

def test_run_parameter_sweep_2d(self, sample_df):
    """Should run 2D parameter sweep (two filters)."""
    engine = ParameterSensitivityEngine(
        baseline_df=sample_df,
        column_mapping={"gain": "gain_pct"},
        active_filters=[],
    )
    config = ParameterSensitivityConfig(
        mode="sweep",
        sweep_filter_1="entry_time",
        sweep_range_1=(9.0, 12.0),
        sweep_filter_2="gap_pct",
        sweep_range_2=(2.0, 8.0),
        grid_resolution=5,
        metrics=("win_rate",),
    )
    
    result = engine.run_parameter_sweep(config)
    
    assert result.filter_2_name == "gap_pct"
    assert len(result.filter_2_values) == 5
    assert result.metric_grids["win_rate"].shape == (5, 5)
```

### Step 2: Run test to verify it fails

```bash
python -m pytest tests/unit/test_parameter_sensitivity.py::TestParameterSensitivityEngine::test_run_parameter_sweep_1d -v
```

Expected: FAIL with "AttributeError: 'run_parameter_sweep'"

### Step 3: Implement parameter sweep

```python
# Add to ParameterSensitivityEngine class

def run_parameter_sweep(
    self,
    config: ParameterSensitivityConfig,
    progress_callback: Callable[[int, int], None] | None = None,
) -> SweepResult:
    """Run parameter sweep across 1-2 filter dimensions.

    Args:
        config: Configuration with sweep settings.
        progress_callback: Optional callback for progress updates.

    Returns:
        SweepResult with metric grids.

    Raises:
        ValueError: If sweep_filter_1 or sweep_range_1 not configured.
    """
    self._cancelled = False

    if config.sweep_filter_1 is None or config.sweep_range_1 is None:
        raise ValueError("sweep_filter_1 and sweep_range_1 are required for sweep mode")

    # Generate value grids
    filter_1_values = np.linspace(
        config.sweep_range_1[0],
        config.sweep_range_1[1],
        config.grid_resolution,
    )

    is_2d = config.sweep_filter_2 is not None and config.sweep_range_2 is not None
    if is_2d:
        filter_2_values = np.linspace(
            config.sweep_range_2[0],
            config.sweep_range_2[1],
            config.grid_resolution,
        )
    else:
        filter_2_values = None

    # Initialize metric grids
    if is_2d:
        grid_shape = (config.grid_resolution, config.grid_resolution)
    else:
        grid_shape = (config.grid_resolution,)

    metric_grids: dict[str, np.ndarray] = {
        metric: np.zeros(grid_shape) for metric in config.metrics
    }

    # Calculate total steps
    total_steps = config.grid_resolution * (config.grid_resolution if is_2d else 1)
    current_step = 0

    # Run sweep
    for i, val_1 in enumerate(filter_1_values):
        if self._cancelled:
            break

        if is_2d:
            for j, val_2 in enumerate(filter_2_values):
                if self._cancelled:
                    break

                # Create filters for this grid point
                # Use a small window around the value (±5% of range)
                range_1 = config.sweep_range_1[1] - config.sweep_range_1[0]
                range_2 = config.sweep_range_2[1] - config.sweep_range_2[0]
                window_1 = range_1 * 0.05
                window_2 = range_2 * 0.05

                filters = [
                    FilterCriteria(
                        column=config.sweep_filter_1,
                        operator="between",
                        min_val=val_1 - window_1,
                        max_val=val_1 + window_1,
                    ),
                    FilterCriteria(
                        column=config.sweep_filter_2,
                        operator="between",
                        min_val=val_2 - window_2,
                        max_val=val_2 + window_2,
                    ),
                ]

                metrics = self._calculate_metrics_for_filters(filters)

                for metric_name in config.metrics:
                    metric_grids[metric_name][i, j] = metrics.get(metric_name, 0.0)

                current_step += 1
                if progress_callback:
                    progress_callback(current_step, total_steps)
        else:
            # 1D sweep
            range_1 = config.sweep_range_1[1] - config.sweep_range_1[0]
            window_1 = range_1 * 0.05

            filters = [
                FilterCriteria(
                    column=config.sweep_filter_1,
                    operator="between",
                    min_val=val_1 - window_1,
                    max_val=val_1 + window_1,
                ),
            ]

            metrics = self._calculate_metrics_for_filters(filters)

            for metric_name in config.metrics:
                metric_grids[metric_name][i] = metrics.get(metric_name, 0.0)

            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps)

    # Final progress
    if progress_callback and not self._cancelled:
        progress_callback(total_steps, total_steps)

    return SweepResult(
        filter_1_name=config.sweep_filter_1,
        filter_1_values=filter_1_values,
        filter_2_name=config.sweep_filter_2,
        filter_2_values=filter_2_values,
        metric_grids=metric_grids,
        current_position=None,  # TODO: Calculate from active filters
    )
```

### Step 4: Run test to verify it passes

```bash
python -m pytest tests/unit/test_parameter_sensitivity.py::TestParameterSensitivityEngine::test_run_parameter_sweep_1d -v
python -m pytest tests/unit/test_parameter_sensitivity.py::TestParameterSensitivityEngine::test_run_parameter_sweep_2d -v
```

Expected: PASS (2 tests)

### Step 5: Commit

```bash
git add src/core/parameter_sensitivity.py tests/unit/test_parameter_sensitivity.py
git commit -m "feat(sensitivity): implement parameter sweep for 1D and 2D analysis

- Support single filter line chart sweep
- Support two filter heatmap sweep
- Generate metric grids across parameter space"
```

---

## Task 7: AppState Signals

**Files:**
- Modify: `src/core/app_state.py`
- Test: `tests/unit/test_app_state.py` (if exists, otherwise skip test)

### Step 1: Add sensitivity signals to AppState

```python
# Add to src/core/app_state.py in the signal declarations section (around line 61-64)

# Parameter sensitivity signals
sensitivity_started = pyqtSignal()
sensitivity_progress = pyqtSignal(int, int)  # current, total
sensitivity_completed = pyqtSignal(object)  # NeighborhoodResult list or SweepResult
sensitivity_error = pyqtSignal(str)
```

### Step 2: Commit

```bash
git add src/core/app_state.py
git commit -m "feat(sensitivity): add AppState signals for sensitivity analysis"
```

---

## Task 8: Async Worker Thread

**Files:**
- Modify: `src/core/parameter_sensitivity.py`
- Test: `tests/unit/test_parameter_sensitivity.py`

### Step 1: Write failing test for worker

```python
# Add to tests/unit/test_parameter_sensitivity.py

from PyQt6.QtCore import QThread
from src.core.parameter_sensitivity import ParameterSensitivityWorker


class TestParameterSensitivityWorker:
    """Tests for async worker."""

    @pytest.fixture
    def sample_df(self):
        np.random.seed(42)
        n = 50
        return pd.DataFrame({
            "gain_pct": np.random.uniform(-0.05, 0.10, n),
            "entry_time": np.random.uniform(9.0, 16.0, n),
        })

    def test_worker_is_qthread(self, sample_df):
        """Worker should be a QThread subclass."""
        config = ParameterSensitivityConfig(mode="neighborhood")
        worker = ParameterSensitivityWorker(
            config=config,
            baseline_df=sample_df,
            column_mapping={"gain": "gain_pct"},
            active_filters=[],
        )
        assert isinstance(worker, QThread)

    def test_worker_has_signals(self, sample_df):
        """Worker should have progress, completed, and error signals."""
        config = ParameterSensitivityConfig(mode="neighborhood")
        worker = ParameterSensitivityWorker(
            config=config,
            baseline_df=sample_df,
            column_mapping={"gain": "gain_pct"},
            active_filters=[],
        )
        assert hasattr(worker, "progress")
        assert hasattr(worker, "completed")
        assert hasattr(worker, "error")
```

### Step 2: Run test to verify it fails

```bash
python -m pytest tests/unit/test_parameter_sensitivity.py::TestParameterSensitivityWorker -v
```

Expected: FAIL with "cannot import name 'ParameterSensitivityWorker'"

### Step 3: Implement worker thread

```python
# Add to src/core/parameter_sensitivity.py

from PyQt6.QtCore import QThread, pyqtSignal


class ParameterSensitivityWorker(QThread):
    """Background worker for running sensitivity analysis.

    Signals:
        progress: Emitted with (current, total) during analysis.
        completed: Emitted with results when analysis completes.
        error: Emitted with error message if analysis fails.
    """

    progress = pyqtSignal(int, int)
    completed = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(
        self,
        config: ParameterSensitivityConfig,
        baseline_df: pd.DataFrame,
        column_mapping: dict[str, str],
        active_filters: list[FilterCriteria],
    ) -> None:
        """Initialize the worker.

        Args:
            config: Analysis configuration.
            baseline_df: Baseline data for analysis.
            column_mapping: Column name mappings.
            active_filters: Active filters to test.
        """
        super().__init__()
        self._config = config
        self._baseline_df = baseline_df
        self._column_mapping = column_mapping
        self._active_filters = active_filters
        self._engine: ParameterSensitivityEngine | None = None

    def run(self) -> None:
        """Execute the analysis in background thread."""
        try:
            self._engine = ParameterSensitivityEngine(
                baseline_df=self._baseline_df,
                column_mapping=self._column_mapping,
                active_filters=self._active_filters,
            )

            def on_progress(current: int, total: int) -> None:
                self.progress.emit(current, total)

            if self._config.mode == "neighborhood":
                results = self._engine.run_neighborhood_scan(
                    self._config,
                    progress_callback=on_progress,
                )
            else:
                results = self._engine.run_parameter_sweep(
                    self._config,
                    progress_callback=on_progress,
                )

            self.completed.emit(results)

        except Exception as e:
            logger.exception("Sensitivity analysis failed")
            self.error.emit(str(e))

    def cancel(self) -> None:
        """Request cancellation of running analysis."""
        if self._engine:
            self._engine.cancel()
```

### Step 4: Run test to verify it passes

```bash
python -m pytest tests/unit/test_parameter_sensitivity.py::TestParameterSensitivityWorker -v
```

Expected: PASS (2 tests)

### Step 5: Commit

```bash
git add src/core/parameter_sensitivity.py tests/unit/test_parameter_sensitivity.py
git commit -m "feat(sensitivity): add async worker thread for background analysis"
```

---

## Task 9: Parameter Sensitivity Tab - Basic Structure

**Files:**
- Create: `src/tabs/parameter_sensitivity.py`
- Test: `tests/tabs/test_parameter_sensitivity.py`

### Step 1: Write failing test for tab creation

```python
# tests/tabs/test_parameter_sensitivity.py
"""Tests for Parameter Sensitivity tab."""

import pytest
from PyQt6.QtWidgets import QApplication

from src.core.app_state import AppState
from src.tabs.parameter_sensitivity import ParameterSensitivityTab


@pytest.fixture(scope="module")
def app():
    """Create QApplication for tests."""
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def app_state():
    """Create AppState instance."""
    return AppState()


class TestParameterSensitivityTab:
    """Tests for ParameterSensitivityTab widget."""

    def test_tab_creation(self, app, app_state):
        """Tab should create without errors."""
        tab = ParameterSensitivityTab(app_state)
        assert tab is not None

    def test_tab_has_run_button(self, app, app_state):
        """Tab should have a run analysis button."""
        tab = ParameterSensitivityTab(app_state)
        assert tab._run_btn is not None

    def test_tab_has_mode_selector(self, app, app_state):
        """Tab should have mode radio buttons."""
        tab = ParameterSensitivityTab(app_state)
        assert tab._neighborhood_radio is not None
        assert tab._sweep_radio is not None
```

### Step 2: Run test to verify it fails

```bash
python -m pytest tests/tabs/test_parameter_sensitivity.py -v
```

Expected: FAIL with "ModuleNotFoundError"

### Step 3: Write basic tab implementation

```python
# src/tabs/parameter_sensitivity.py
"""Parameter Sensitivity tab for testing filter robustness."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from src.core.app_state import AppState

logger = logging.getLogger(__name__)


class ParameterSensitivityTab(QWidget):
    """Tab for parameter sensitivity analysis.

    Provides two analysis modes:
    - Neighborhood Scan: Quick robustness check of current filters
    - Parameter Sweep: Deep exploration across parameter ranges
    """

    def __init__(self, app_state: AppState) -> None:
        """Initialize the tab.

        Args:
            app_state: Application state for accessing data and filters.
        """
        super().__init__()
        self._app_state = app_state
        self._worker = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create splitter for sidebar and main area
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Sidebar
        sidebar = self._create_sidebar()
        splitter.addWidget(sidebar)

        # Main visualization area
        main_area = self._create_main_area()
        splitter.addWidget(main_area)

        # Set initial splitter sizes (sidebar: 280px, main: stretch)
        splitter.setSizes([280, 800])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

    def _create_sidebar(self) -> QWidget:
        """Create the sidebar with configuration controls."""
        sidebar = QFrame()
        sidebar.setObjectName("sensitivity_sidebar")
        sidebar.setMaximumWidth(320)
        sidebar.setMinimumWidth(250)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Mode selection
        mode_group = QGroupBox("Analysis Mode")
        mode_layout = QVBoxLayout(mode_group)

        self._neighborhood_radio = QRadioButton("Neighborhood Scan")
        self._neighborhood_radio.setToolTip("Quick robustness check of current filter boundaries")
        self._neighborhood_radio.setChecked(True)

        self._sweep_radio = QRadioButton("Parameter Sweep")
        self._sweep_radio.setToolTip("Deep exploration across parameter ranges")

        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._neighborhood_radio, 0)
        self._mode_group.addButton(self._sweep_radio, 1)

        mode_layout.addWidget(self._neighborhood_radio)
        mode_layout.addWidget(self._sweep_radio)
        layout.addWidget(mode_group)

        # Configuration area (changes based on mode)
        self._config_stack = QWidget()
        self._config_layout = QVBoxLayout(self._config_stack)
        self._config_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._config_stack)

        # Metric selection
        metric_group = QGroupBox("Primary Metric")
        metric_layout = QVBoxLayout(metric_group)
        self._metric_combo = QComboBox()
        self._metric_combo.addItems(["Expected Value", "Win Rate", "Profit Factor"])
        metric_layout.addWidget(self._metric_combo)
        layout.addWidget(metric_group)

        # Grid resolution (for sweep mode)
        self._resolution_group = QGroupBox("Grid Resolution")
        resolution_layout = QVBoxLayout(self._resolution_group)
        self._resolution_spin = QSpinBox()
        self._resolution_spin.setRange(5, 25)
        self._resolution_spin.setValue(10)
        resolution_layout.addWidget(self._resolution_spin)
        self._resolution_group.setVisible(False)
        layout.addWidget(self._resolution_group)

        layout.addStretch()

        # Run button and progress
        self._run_btn = QPushButton("Run Analysis")
        self._run_btn.setObjectName("primary_button")
        layout.addWidget(self._run_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setVisible(False)
        layout.addWidget(self._cancel_btn)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        return sidebar

    def _create_main_area(self) -> QWidget:
        """Create the main visualization area."""
        main = QFrame()
        main.setObjectName("sensitivity_main")

        layout = QVBoxLayout(main)
        layout.setContentsMargins(12, 12, 12, 12)

        # Placeholder for results
        self._results_label = QLabel("Run an analysis to see results")
        self._results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._results_label)

        return main

    def _connect_signals(self) -> None:
        """Connect widget signals."""
        self._mode_group.buttonClicked.connect(self._on_mode_changed)
        self._run_btn.clicked.connect(self._on_run_clicked)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)

    def _on_mode_changed(self) -> None:
        """Handle mode selection change."""
        is_sweep = self._sweep_radio.isChecked()
        self._resolution_group.setVisible(is_sweep)

    def _on_run_clicked(self) -> None:
        """Handle run button click."""
        logger.info("Run analysis clicked")
        # TODO: Implement analysis execution

    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        if self._worker:
            self._worker.cancel()

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(5000)
```

### Step 4: Run test to verify it passes

```bash
python -m pytest tests/tabs/test_parameter_sensitivity.py -v
```

Expected: PASS (3 tests)

### Step 5: Commit

```bash
git add src/tabs/parameter_sensitivity.py tests/tabs/test_parameter_sensitivity.py
git commit -m "feat(sensitivity): add basic tab structure with sidebar and main area"
```

---

## Task 10: Main Window Integration

**Files:**
- Modify: `src/ui/main_window.py`

### Step 1: Add tab import and registration

```python
# Add import at top of src/ui/main_window.py (around line 17)
from src.tabs.parameter_sensitivity import ParameterSensitivityTab

# Add to tab list in _create_tabs method (around line 58)
# Find the line with MonteCarloTab and add after it:
("Parameter Sensitivity", ParameterSensitivityTab(self._app_state)),
```

### Step 2: Run app to verify tab appears

```bash
python -m src.main
```

Expected: Parameter Sensitivity tab visible in dock manager

### Step 3: Update docking test expected count

```python
# In tests/ui/test_main_window_docking.py, update expected_tabs list to include "Parameter Sensitivity"
```

### Step 4: Commit

```bash
git add src/ui/main_window.py
git commit -m "feat(sensitivity): register Parameter Sensitivity tab in main window"
```

---

## Task 11: Wire Up Analysis Execution

**Files:**
- Modify: `src/tabs/parameter_sensitivity.py`

### Step 1: Implement full analysis execution

```python
# Add these methods to ParameterSensitivityTab class

def _on_run_clicked(self) -> None:
    """Handle run button click - start analysis."""
    if not self._app_state.has_data:
        logger.warning("No data loaded")
        return

    # Build config from UI state
    is_sweep = self._sweep_radio.isChecked()
    metric_map = {
        "Expected Value": "expected_value",
        "Win Rate": "win_rate",
        "Profit Factor": "profit_factor",
    }
    primary_metric = metric_map.get(self._metric_combo.currentText(), "expected_value")

    config = ParameterSensitivityConfig(
        mode="sweep" if is_sweep else "neighborhood",
        primary_metric=primary_metric,
        grid_resolution=self._resolution_spin.value() if is_sweep else 10,
    )

    # Get baseline data and filters
    baseline_df = self._app_state.baseline_df
    column_mapping = self._app_state.column_mapping or {}
    active_filters = self._app_state.filters or []

    if not active_filters and not is_sweep:
        logger.warning("No active filters for neighborhood scan")
        self._results_label.setText("Apply filters in Feature Explorer first")
        return

    # Start worker
    self._worker = ParameterSensitivityWorker(
        config=config,
        baseline_df=baseline_df,
        column_mapping=column_mapping,
        active_filters=active_filters,
    )
    self._worker.progress.connect(self._on_progress)
    self._worker.completed.connect(self._on_completed)
    self._worker.error.connect(self._on_error)
    self._worker.start()

    # Update UI state
    self._run_btn.setVisible(False)
    self._cancel_btn.setVisible(True)
    self._progress_bar.setVisible(True)
    self._progress_bar.setValue(0)

def _on_progress(self, current: int, total: int) -> None:
    """Handle progress update."""
    if total > 0:
        self._progress_bar.setValue(int(current / total * 100))

def _on_completed(self, results) -> None:
    """Handle analysis completion."""
    self._run_btn.setVisible(True)
    self._cancel_btn.setVisible(False)
    self._progress_bar.setVisible(False)

    if isinstance(results, list):
        # Neighborhood scan results
        self._display_neighborhood_results(results)
    else:
        # Sweep result
        self._display_sweep_results(results)

def _on_error(self, message: str) -> None:
    """Handle analysis error."""
    self._run_btn.setVisible(True)
    self._cancel_btn.setVisible(False)
    self._progress_bar.setVisible(False)
    self._results_label.setText(f"Error: {message}")
    logger.error("Sensitivity analysis error: %s", message)

def _display_neighborhood_results(self, results: list) -> None:
    """Display neighborhood scan results."""
    if not results:
        self._results_label.setText("No filters to analyze")
        return

    # Build summary text
    lines = ["<h3>Neighborhood Scan Results</h3>"]
    for r in results:
        status_color = {"robust": "#22C55E", "caution": "#F59E0B", "fragile": "#EF4444"}
        color = status_color.get(r.status, "#64748B")
        lines.append(
            f"<p><b>{r.filter_name}</b>: "
            f"<span style='color:{color}'>{r.status.upper()}</span> "
            f"(worst: -{r.worst_degradation:.1f}% at ±{r.worst_level*100:.0f}%)</p>"
        )

    self._results_label.setText("".join(lines))

def _display_sweep_results(self, result) -> None:
    """Display sweep results."""
    self._results_label.setText(
        f"<h3>Parameter Sweep Complete</h3>"
        f"<p>Filter: {result.filter_1_name}</p>"
        f"<p>Grid: {len(result.filter_1_values)} points</p>"
    )
```

Also add the import:
```python
from src.core.parameter_sensitivity import (
    ParameterSensitivityConfig,
    ParameterSensitivityWorker,
)
```

### Step 2: Commit

```bash
git add src/tabs/parameter_sensitivity.py
git commit -m "feat(sensitivity): wire up analysis execution with worker thread"
```

---

## Task 12: Run All Tests

### Step 1: Run full test suite

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -50
```

### Step 2: Verify new tests pass

```bash
python -m pytest tests/unit/test_parameter_sensitivity.py tests/tabs/test_parameter_sensitivity.py -v
```

### Step 3: Final commit

```bash
git add -A
git commit -m "feat(sensitivity): complete parameter sensitivity feature

- Core engine with neighborhood scan and parameter sweep
- Async worker thread for background processing
- Basic tab UI with mode selection and results display
- Main window integration"
```

---

## Summary

This plan implements the core Parameter Sensitivity feature:

| Task | Component | Tests |
|------|-----------|-------|
| 1 | Config/Result dataclasses | 4 |
| 2 | Engine initialization | 2 |
| 3 | Perturbation generation | 1 |
| 4 | Metrics calculation | 1 |
| 5 | Neighborhood scan | 2 |
| 6 | Parameter sweep | 2 |
| 7 | AppState signals | - |
| 8 | Async worker | 2 |
| 9 | Tab basic structure | 3 |
| 10 | Main window integration | - |
| 11 | Analysis execution | - |
| 12 | Full test run | - |

**Future tasks** (not in this plan):
- Heatmap visualization widget (pyqtgraph ImageItem)
- Degradation detail table
- Export functionality (CSV/PNG)
- Sweep filter selection UI
- Current position marker on heatmap
