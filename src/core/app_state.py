"""Centralized application state with signal-based updates."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd
from PyQt6.QtCore import QObject, pyqtSignal

from src.core.models import AdjustmentParams, MetricsUserInputs

if TYPE_CHECKING:
    from src.core.models import ColumnMapping, FilterCriteria, TradingMetrics
    from src.core.monte_carlo import MonteCarloResults

logger = logging.getLogger(__name__)


class AppState(QObject):
    """Centralized application state with signal-based updates.

    This class manages all shared state across the application and emits signals
    when state changes occur, enabling reactive updates in all connected components.

    Attributes:
        raw_df: Original DataFrame as loaded from file.
        baseline_df: DataFrame after first trigger algorithm applied.
        filtered_df: DataFrame after user filters applied.
        column_mapping: Mapping of required columns to DataFrame column names.
        filters: List of active filter criteria.
        first_trigger_enabled: Whether first trigger filtering is enabled.
        baseline_metrics: TradingMetrics calculated from baseline data.
        filtered_metrics: TradingMetrics calculated from filtered data.
        adjustment_params: Parameters for stop loss and efficiency adjustments.
        flat_stake_equity_curve: DataFrame with flat stake equity curve data for charts.
        kelly_equity_curve: DataFrame with Kelly equity curve data for charts.
    """

    # Signals
    data_loaded = pyqtSignal(object)  # pd.DataFrame
    column_mapping_changed = pyqtSignal(object)  # ColumnMapping
    baseline_calculated = pyqtSignal(object)  # TradingMetrics (Story 1.6)
    adjustment_params_changed = pyqtSignal(object)  # AdjustmentParams
    metrics_user_inputs_changed = pyqtSignal(object)  # MetricsUserInputs
    filters_changed = pyqtSignal(list)  # list[FilterCriteria]
    filtered_data_updated = pyqtSignal(object)  # pd.DataFrame
    metrics_updated = pyqtSignal(object, object)  # baseline, filtered TradingMetrics
    first_trigger_toggled = pyqtSignal(bool)
    request_tab_change = pyqtSignal(int)
    state_corrupted = pyqtSignal(str)
    state_recovered = pyqtSignal()
    equity_curve_updated = pyqtSignal(object)  # pd.DataFrame (Story 3.4)
    kelly_equity_curve_updated = pyqtSignal(object)  # pd.DataFrame (Story 3.5)
    # Filtered equity curve signals (Story 4.1)
    filtered_equity_curve_updated = pyqtSignal(object)  # pd.DataFrame (filtered flat stake)
    filtered_kelly_equity_curve_updated = pyqtSignal(object)  # pd.DataFrame (filtered Kelly)
    # Calculation status signals (Story 4.1)
    filtered_calculation_started = pyqtSignal()
    filtered_calculation_completed = pyqtSignal()
    # Monte Carlo signals (Story 7.2)
    monte_carlo_started = pyqtSignal()
    monte_carlo_progress = pyqtSignal(int, int)  # completed, total
    monte_carlo_completed = pyqtSignal(object)  # MonteCarloResults
    monte_carlo_error = pyqtSignal(str)

    def __init__(self) -> None:
        """Initialize AppState with default empty values."""
        super().__init__()
        self.raw_df: pd.DataFrame | None = None
        self.baseline_df: pd.DataFrame | None = None
        self.filtered_df: pd.DataFrame | None = None
        self.column_mapping: ColumnMapping | None = None
        self.filters: list[FilterCriteria] = []
        self.first_trigger_enabled: bool = True
        self.baseline_metrics: TradingMetrics | None = None
        self.filtered_metrics: TradingMetrics | None = None
        self.adjustment_params: AdjustmentParams = AdjustmentParams()
        self.metrics_user_inputs: MetricsUserInputs = MetricsUserInputs()
        # Equity curves for charts (Story 3.4 + Story 3.5)
        self.flat_stake_equity_curve: pd.DataFrame | None = None
        self.kelly_equity_curve: pd.DataFrame | None = None
        # Filtered equity curves (Story 4.1)
        self.filtered_flat_stake_equity_curve: pd.DataFrame | None = None
        self.filtered_kelly_equity_curve: pd.DataFrame | None = None
        # Calculation status (Story 4.1)
        self._is_calculating_filtered: bool = False
        # Monte Carlo state (Story 7.2)
        self.monte_carlo_results: MonteCarloResults | None = None
        self._monte_carlo_running: bool = False

    @property
    def has_data(self) -> bool:
        """Check if data is loaded and configured.

        Returns:
            True if baseline_df and column_mapping are both set, False otherwise.
        """
        return self.baseline_df is not None and self.column_mapping is not None

    @property
    def is_calculating_filtered(self) -> bool:
        """Check if filtered metrics calculation is in progress.

        Returns:
            True if filtered calculation is ongoing, False otherwise.
        """
        return self._is_calculating_filtered

    @is_calculating_filtered.setter
    def is_calculating_filtered(self, value: bool) -> None:
        """Set filtered calculation status.

        Args:
            value: Whether calculation is in progress.
        """
        self._is_calculating_filtered = value

    @property
    def monte_carlo_running(self) -> bool:
        """Check if Monte Carlo simulation is in progress.

        Returns:
            True if simulation is running, False otherwise.
        """
        return self._monte_carlo_running

    @monte_carlo_running.setter
    def monte_carlo_running(self, value: bool) -> None:
        """Set Monte Carlo running status.

        Args:
            value: Whether simulation is in progress.
        """
        self._monte_carlo_running = value
