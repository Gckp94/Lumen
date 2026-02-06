"""Background worker thread for post-mapping data processing.

Moves heavy computation (trigger number assignment, metrics calculation,
adjusted gains, time_to_minutes) off the main thread so the UI stays
responsive for large datasets (1M+ rows, 300+ columns).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from src.core.filter_engine import time_to_minutes
from src.core.first_trigger import FirstTriggerEngine
from src.core.metrics import MetricsCalculator
from src.core.models import AdjustmentParams, ColumnMapping, TradingMetrics

logger = logging.getLogger(__name__)


def compute_time_change_columns(
    df: pd.DataFrame,
    mapping: "ColumnMapping",
) -> pd.DataFrame:
    """Compute change_X_min columns from price_X_min_after mappings.

    Formula: change = (trigger_price - price_X_min) / trigger_price

    Args:
        df: DataFrame with trigger_price_unadjusted column.
        mapping: Column mapping with price_X_min_after fields.

    Returns:
        DataFrame with change_X_min columns added.
    """
    if "trigger_price_unadjusted" not in df.columns:
        return df

    trigger_price = df["trigger_price_unadjusted"]

    interval_mappings = {
        10: mapping.price_10_min_after,
        20: mapping.price_20_min_after,
        30: mapping.price_30_min_after,
        60: mapping.price_60_min_after,
        90: mapping.price_90_min_after,
        120: mapping.price_120_min_after,
        150: mapping.price_150_min_after,
        180: mapping.price_180_min_after,
        240: mapping.price_240_min_after,
    }

    for interval, price_col in interval_mappings.items():
        if price_col and price_col in df.columns:
            change_col = f"change_{interval}_min"
            df[change_col] = (trigger_price - df[price_col]) / trigger_price

    return df


@dataclass
class MappingResult:
    """Result of background mapping worker computation.

    Attributes:
        baseline_df: DataFrame with trigger_number, adjusted_gain_pct, and time_minutes columns added.
        first_triggers_df: Subset of baseline_df where trigger_number == 1.
        metrics: TradingMetrics computed from first triggers.
        flat_equity: Flat-stake equity curve DataFrame, or None.
        kelly_equity: Kelly equity curve DataFrame, or None.
        total_rows: Total number of rows in baseline_df.
        baseline_rows: Number of first-trigger rows.
    """

    baseline_df: pd.DataFrame
    first_triggers_df: pd.DataFrame
    metrics: TradingMetrics
    flat_equity: pd.DataFrame | None
    kelly_equity: pd.DataFrame | None
    total_rows: int
    baseline_rows: int


class MappingWorker(QThread):
    """Worker thread for post-mapping data processing.

    Performs the heavy computation that previously ran on the main thread
    inside ``DataInputTab._on_mapping_continue()``:

    1. ``assign_trigger_numbers()``
    2. Filter to first triggers
    3. ``MetricsCalculator.calculate()``
    4. ``calculate_adjusted_gains()``
    5. ``compute_time_change_columns()``
    6. ``time_to_minutes()``

    Signals:
        progress: Emitted with progress percentage (0-100).
        finished: Emitted with MappingResult on success.
        error: Emitted with error message string on failure.
    """

    progress = pyqtSignal(int)
    finished = pyqtSignal(object)  # MappingResult
    error = pyqtSignal(str)

    def __init__(
        self,
        df: pd.DataFrame,
        mapping: ColumnMapping,
        adjustment_params: AdjustmentParams,
        flat_stake: float,
        start_capital: float,
    ) -> None:
        """Initialize the worker.

        Args:
            df: Raw DataFrame loaded from file.
            mapping: Column mapping configuration.
            adjustment_params: Stop loss / efficiency parameters.
            flat_stake: Flat stake dollar amount for equity curve.
            start_capital: Starting capital for Kelly equity curve.
        """
        super().__init__()
        self._df = df
        self._mapping = mapping
        self._adjustment_params = adjustment_params
        self._flat_stake = flat_stake
        self._start_capital = start_capital

    def run(self) -> None:
        """Execute the post-mapping computation."""
        try:
            mapping = self._mapping
            self.progress.emit(5)

            # 1. Assign trigger numbers (heaviest step for wide DataFrames)
            engine = FirstTriggerEngine()
            baseline_df = engine.assign_trigger_numbers(
                self._df,
                ticker_col=mapping.ticker,
                date_col=mapping.date,
                time_col=mapping.time,
            )
            self.progress.emit(40)

            # 2. Filter to first triggers for metrics
            total_rows = len(baseline_df)
            if total_rows > 0:
                first_triggers_df = baseline_df[baseline_df["trigger_number"] == 1].copy()
                baseline_rows = len(first_triggers_df)
            else:
                first_triggers_df = baseline_df.copy()
                baseline_rows = 0
            self.progress.emit(50)

            # 3. Calculate metrics
            calculator = MetricsCalculator()
            metrics, flat_equity, kelly_equity = calculator.calculate(
                df=first_triggers_df,
                gain_col=mapping.gain_pct,
                win_loss_col=mapping.win_loss,
                derived=mapping.win_loss_derived,
                breakeven_is_win=mapping.breakeven_is_win,
                adjustment_params=self._adjustment_params,
                mae_col=mapping.mae_pct,
                date_col=mapping.date,
                time_col=mapping.time,
                flat_stake=self._flat_stake,
                start_capital=self._start_capital,
            )
            self.progress.emit(70)

            # 4. Add adjusted_gain_pct column
            if mapping.mae_pct is not None:
                adjusted_gains = self._adjustment_params.calculate_adjusted_gains(
                    baseline_df, mapping.gain_pct, mapping.mae_pct
                )
                baseline_df["adjusted_gain_pct"] = adjusted_gains
            self.progress.emit(80)

            # 5. Compute time change columns
            baseline_df = compute_time_change_columns(baseline_df, mapping)
            self.progress.emit(88)

            # 6. Add time_minutes column
            if mapping.time and mapping.time in baseline_df.columns:
                baseline_df["time_minutes"] = time_to_minutes(baseline_df[mapping.time])
            self.progress.emit(95)

            result = MappingResult(
                baseline_df=baseline_df,
                first_triggers_df=first_triggers_df,
                metrics=metrics,
                flat_equity=flat_equity,
                kelly_equity=kelly_equity,
                total_rows=total_rows,
                baseline_rows=baseline_rows,
            )
            self.progress.emit(100)
            self.finished.emit(result)

        except Exception as e:
            logger.exception("MappingWorker failed")
            self.error.emit(str(e))
