"""Background worker for running calculations off the UI thread."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal


class WorkerSignals(QObject):
    """Signals for CalculationWorker communication."""

    started = pyqtSignal()
    finished = pyqtSignal(object)  # result
    error = pyqtSignal(str)  # error message


class CalculationWorker(QRunnable):
    """Runs a calculation function on a background thread.

    Usage:
        worker = CalculationWorker(my_calc_fn, data)
        worker.signals.finished.connect(self._on_complete)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(self, calc_fn: Callable[[Any], Any], data: Any) -> None:
        """Initialize worker with calculation function and data.

        Args:
            calc_fn: Function to execute. Receives data as argument.
            data: Data to pass to calc_fn. Should be a copy if mutable.
        """
        super().__init__()
        self._calc_fn = calc_fn
        self._data = data
        self.signals = WorkerSignals()

    def run(self) -> None:
        """Execute the calculation function."""
        self.signals.started.emit()
        try:
            result = self._calc_fn(self._data)
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))
