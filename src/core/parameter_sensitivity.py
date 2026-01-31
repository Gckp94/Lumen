# src/core/parameter_sensitivity.py
"""Parameter sensitivity analysis engine for testing filter robustness."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Literal

import numpy as np
import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

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


@dataclass
class ThresholdRow:
    """Single row of threshold analysis results.

    Attributes:
        threshold: The filter threshold value for this row.
        is_current: Whether this is the current (baseline) row.
        num_trades: Number of trades passing all filters.
        ev_pct: Expected value percentage.
        win_pct: Win rate percentage.
        median_winner_pct: Median winning trade return.
        profit_ratio: Avg winner / abs(avg loser).
        edge_pct: Edge percentage.
        eg_pct: Expected geometric growth percentage.
        kelly_pct: Full Kelly stake percentage.
        max_loss_pct: Percentage of trades hitting stop loss.
    """
    threshold: float
    is_current: bool
    num_trades: int
    ev_pct: float | None
    win_pct: float | None
    median_winner_pct: float | None
    profit_ratio: float | None
    edge_pct: float | None
    eg_pct: float | None
    kelly_pct: float | None
    max_loss_pct: float | None


@dataclass
class ThresholdAnalysisResult:
    """Result of threshold analysis for a single filter.

    Attributes:
        filter_column: Column name of the analyzed filter.
        varied_bound: Which bound was varied ('min' or 'max').
        step_size: Step size used for threshold variation.
        rows: List of ThresholdRow results, ordered by threshold ascending.
        current_index: Index of the current (baseline) row in the list.
    """
    filter_column: str
    varied_bound: Literal["min", "max"]
    step_size: float
    rows: list[ThresholdRow]
    current_index: int


# Import after dataclasses to avoid circular import issues
from src.core.models import ColumnMapping, FilterCriteria
from src.core.filter_engine import FilterEngine
from src.core.metrics import MetricsCalculator


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
        column_mapping: ColumnMapping,
        active_filters: list[FilterCriteria],
    ) -> None:
        """Initialize the sensitivity engine.

        Args:
            baseline_df: Data BEFORE user filters (but after first-trigger).
            column_mapping: ColumnMapping dataclass with column names.
            active_filters: Current active filters to test.
        """
        self._baseline_df = baseline_df
        self._column_mapping = column_mapping
        self._active_filters = active_filters
        self._cancelled = False

    def cancel(self) -> None:
        """Request cancellation of running analysis."""
        self._cancelled = True

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

        gain_col = self._column_mapping.gain_pct
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

        # Calculate total steps for progress (only count filters with complete bounds)
        valid_filters = [
            f for f in self._active_filters
            if f.min_val is not None and f.max_val is not None
        ]
        num_filters = len(valid_filters)
        num_levels = len(config.perturbation_levels)
        perturbations_per_level = 4  # shift down, shift up, expand, contract
        total_steps = num_filters * (1 + num_levels * perturbations_per_level)
        current_step = 0

        for filter_idx, test_filter in enumerate(self._active_filters):
            if self._cancelled:
                break

            # Skip filters with partial bounds - can't do neighborhood analysis
            if test_filter.min_val is None or test_filter.max_val is None:
                continue

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
        column_mapping: ColumnMapping,
        active_filters: list[FilterCriteria],
    ) -> None:
        """Initialize the worker.

        Args:
            config: Analysis configuration.
            baseline_df: Baseline data for analysis.
            column_mapping: ColumnMapping dataclass with column names.
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
