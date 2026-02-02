"""Background worker for breakdown calculations.

This module provides a QThread-based worker for running breakdown calculations
in the background, keeping the UI responsive during expensive computations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from src.core.breakdown import BreakdownCalculator
from src.core.computation_cache import get_breakdown_cache

if TYPE_CHECKING:
    from src.core.models import AdjustmentParams

logger = logging.getLogger(__name__)


@dataclass
class BreakdownRequest:
    """Request for breakdown calculation."""

    df: pd.DataFrame
    date_col: str
    gain_col: str
    win_loss_col: str | None
    stake: float
    start_capital: float
    adjustment_params: "AdjustmentParams | None" = None
    mae_col: str | None = None
    year: int | None = None  # For monthly breakdown


@dataclass
class BreakdownResult:
    """Result from breakdown calculation."""

    yearly: dict[str, dict] | None = None
    monthly: dict[str, dict] | None = None
    available_years: list[int] | None = None
    error: str | None = None


class BreakdownWorker(QThread):
    """Background worker for breakdown calculations.

    Runs breakdown calculations in a separate thread to avoid
    blocking the UI. Emits signals for progress and completion.

    Signals:
        started: Emitted when calculation starts.
        progress: Emitted with (current_step, total_steps) during calculation.
        completed: Emitted with BreakdownResult when done.
        error: Emitted with error message if calculation fails.
    """

    started = pyqtSignal()
    progress = pyqtSignal(int, int)  # current, total
    completed = pyqtSignal(object)  # BreakdownResult
    error = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        """Initialize the worker.

        Args:
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._request: BreakdownRequest | None = None
        self._cancelled = False

    def set_request(self, request: BreakdownRequest) -> None:
        """Set the calculation request.

        Args:
            request: Breakdown calculation request.
        """
        self._request = request
        self._cancelled = False

    def cancel(self) -> None:
        """Request cancellation of the current calculation."""
        self._cancelled = True

    def run(self) -> None:
        """Execute the breakdown calculation in background thread."""
        if self._request is None:
            self.error.emit("No request set")
            return

        self.started.emit()
        request = self._request
        cache = get_breakdown_cache()

        try:
            # Create calculator
            calculator = BreakdownCalculator(
                stake=request.stake,
                start_capital=request.start_capital,
                adjustment_params=request.adjustment_params,
                mae_col=request.mae_col,
            )

            result = BreakdownResult()

            # Generate cache key based on request parameters
            cache_key = cache._generate_key(
                "breakdown",
                len(request.df),
                request.date_col,
                request.gain_col,
                request.win_loss_col,
                request.stake,
                request.start_capital,
                str(request.adjustment_params),
                request.year,
            )

            # Check cache first
            hit, cached_result = cache.get(cache_key)
            if hit and isinstance(cached_result, BreakdownResult):
                logger.debug("Breakdown cache hit")
                self.completed.emit(cached_result)
                return

            # Get available years
            result.available_years = calculator.get_available_years(
                request.df, request.date_col
            )

            if self._cancelled:
                return

            self.progress.emit(1, 3)

            # Calculate yearly breakdown
            if request.year is None:
                result.yearly = calculator.calculate_yearly(
                    request.df,
                    request.date_col,
                    request.gain_col,
                    request.win_loss_col,
                )

            if self._cancelled:
                return

            self.progress.emit(2, 3)

            # Calculate monthly breakdown if year specified
            if request.year is not None:
                result.monthly = calculator.calculate_monthly(
                    request.df,
                    request.year,
                    request.date_col,
                    request.gain_col,
                    request.win_loss_col,
                )

            if self._cancelled:
                return

            self.progress.emit(3, 3)

            # Cache the result
            cache.set(cache_key, result)

            self.completed.emit(result)
            logger.debug("Breakdown calculation completed")

        except Exception as e:
            logger.exception("Breakdown calculation failed")
            self.error.emit(str(e))


class BreakdownManager:
    """Manager for breakdown calculations with worker pooling.

    Provides a simple interface for requesting breakdown calculations
    that run in the background. Manages worker lifecycle and cancellation.
    """

    def __init__(self) -> None:
        """Initialize the manager."""
        self._worker: BreakdownWorker | None = None

    def calculate(
        self,
        request: BreakdownRequest,
        on_started: callable | None = None,
        on_progress: callable | None = None,
        on_completed: callable | None = None,
        on_error: callable | None = None,
    ) -> None:
        """Start a breakdown calculation.

        Args:
            request: Breakdown calculation request.
            on_started: Callback when calculation starts.
            on_progress: Callback with (current, total) for progress updates.
            on_completed: Callback with BreakdownResult when done.
            on_error: Callback with error message if calculation fails.
        """
        # Cancel any existing calculation
        self.cancel()

        # Create new worker
        self._worker = BreakdownWorker()
        self._worker.set_request(request)

        # Connect signals
        if on_started:
            self._worker.started.connect(on_started)
        if on_progress:
            self._worker.progress.connect(on_progress)
        if on_completed:
            self._worker.completed.connect(on_completed)
        if on_error:
            self._worker.error.connect(on_error)

        # Start calculation
        self._worker.start()

    def cancel(self) -> None:
        """Cancel any running calculation."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(1000)  # Wait up to 1 second
            if self._worker.isRunning():
                self._worker.terminate()
            self._worker = None

    @property
    def is_running(self) -> bool:
        """Check if a calculation is running."""
        return self._worker is not None and self._worker.isRunning()
