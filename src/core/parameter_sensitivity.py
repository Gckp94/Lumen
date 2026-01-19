# src/core/parameter_sensitivity.py
"""Parameter sensitivity analysis engine for testing filter robustness."""

from __future__ import annotations

import logging
from dataclasses import dataclass
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


# Import after dataclasses to avoid circular import issues
from src.core.models import FilterCriteria
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
