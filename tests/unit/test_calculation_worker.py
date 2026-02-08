"""Tests for CalculationWorker background thread execution."""

import pandas as pd
from pytestqt.qtbot import QtBot

from src.core.calculation_worker import CalculationWorker


class TestCalculationWorker:
    """Tests for CalculationWorker."""

    def test_worker_executes_function_and_emits_finished(self, qtbot: QtBot) -> None:
        """Worker should run calc_fn and emit finished with result."""
        def calc_fn(df: pd.DataFrame) -> int:
            return len(df)

        df = pd.DataFrame({"a": [1, 2, 3]})
        worker = CalculationWorker(calc_fn, df)

        finished_results = []
        worker.signals.finished.connect(lambda r: finished_results.append(r))

        with qtbot.waitSignal(worker.signals.finished, timeout=5000):
            worker.run()

        assert finished_results == [3]

    def test_worker_emits_error_on_exception(self, qtbot: QtBot) -> None:
        """Worker should emit error signal if calc_fn raises."""
        def calc_fn(df: pd.DataFrame) -> int:
            raise ValueError("Test error")

        df = pd.DataFrame({"a": [1, 2, 3]})
        worker = CalculationWorker(calc_fn, df)

        error_messages = []
        worker.signals.error.connect(lambda e: error_messages.append(e))

        with qtbot.waitSignal(worker.signals.error, timeout=5000):
            worker.run()

        assert len(error_messages) == 1
        assert "Test error" in error_messages[0]

    def test_worker_emits_started_signal(self, qtbot: QtBot) -> None:
        """Worker should emit started signal before running."""
        def calc_fn(df: pd.DataFrame) -> int:
            return 1

        df = pd.DataFrame({"a": [1]})
        worker = CalculationWorker(calc_fn, df)

        started_count = []
        worker.signals.started.connect(lambda: started_count.append(1))

        with qtbot.waitSignal(worker.signals.finished, timeout=5000):
            worker.run()

        assert len(started_count) == 1
