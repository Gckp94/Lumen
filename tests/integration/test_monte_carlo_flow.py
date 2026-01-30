"""Integration tests for Monte Carlo simulation flow."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from src.core.app_state import AppState
from src.core.column_mapper import ColumnMapping
from src.core.monte_carlo import MonteCarloConfig, MonteCarloEngine, MonteCarloResults
from src.tabs.monte_carlo import MonteCarloTab, MonteCarloWorker


@pytest.fixture
def app_state():
    """Create a fresh AppState for each test."""
    return AppState()


@pytest.fixture
def sample_df():
    """Create sample trading data for tests."""
    np.random.seed(42)
    n = 100
    return pd.DataFrame({
        "ticker": ["AAPL"] * n,
        "date": pd.date_range("2024-01-01", periods=n),
        "time": ["09:30:00"] * n,
        "gain_pct": np.random.randn(n) * 2,  # Random gains around 0
        "mae_pct": np.abs(np.random.randn(n) * 1),  # MAE percentage
        "trigger_number": np.random.choice([1, 2, 3], size=n),
    })


@pytest.fixture
def column_mapping():
    """Create column mapping for tests."""
    return ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
        win_loss=None,
        breakeven_is_win=True,
        win_loss_derived=True,
    )


@pytest.fixture
def configured_app_state(app_state, sample_df, column_mapping):
    """Create AppState with loaded data."""
    app_state.raw_df = sample_df
    app_state.baseline_df = sample_df.copy()
    app_state.filtered_df = sample_df.copy()
    app_state.column_mapping = column_mapping
    return app_state


class TestMonteCarloTabInitialization:
    """Tests for Monte Carlo tab initialization."""

    def test_tab_initializes_with_empty_state(self, qtbot, app_state):
        """Tab shows empty state when no data loaded."""
        tab = MonteCarloTab(app_state)
        qtbot.addWidget(tab)

        assert tab._content_stack.currentIndex() == 0  # Empty state

    def test_tab_run_button_disabled_without_data(self, qtbot, app_state):
        """Run button is disabled when no data is loaded."""
        tab = MonteCarloTab(app_state)
        qtbot.addWidget(tab)

        # Button should be disabled
        assert tab._config_panel._run_btn._is_enabled is False

    def test_tab_run_button_enabled_with_data(self, qtbot, configured_app_state):
        """Run button is enabled when data is loaded."""
        tab = MonteCarloTab(configured_app_state)
        qtbot.addWidget(tab)

        # Button should be enabled
        assert tab._config_panel._run_btn._is_enabled is True


class TestMonteCarloTabSignals:
    """Tests for Monte Carlo tab signal handling."""

    def test_filtered_data_updated_invalidates_results(
        self, qtbot, configured_app_state
    ):
        """filtered_data_updated signal clears Monte Carlo results."""
        tab = MonteCarloTab(configured_app_state)
        qtbot.addWidget(tab)

        # Simulate having results
        configured_app_state.monte_carlo_results = MagicMock()

        # Emit signal
        configured_app_state.filtered_data_updated.emit(pd.DataFrame())

        # Results should be cleared
        assert configured_app_state.monte_carlo_results is None
        assert tab._content_stack.currentIndex() == 0  # Empty state

    def test_first_trigger_toggled_invalidates_results(
        self, qtbot, configured_app_state
    ):
        """first_trigger_toggled signal clears Monte Carlo results."""
        tab = MonteCarloTab(configured_app_state)
        qtbot.addWidget(tab)

        # Simulate having results
        configured_app_state.monte_carlo_results = MagicMock()

        # Emit signal
        configured_app_state.first_trigger_toggled.emit(True)

        # Results should be cleared
        assert configured_app_state.monte_carlo_results is None


class TestMonteCarloTabResultsDisplay:
    """Tests for Monte Carlo results display."""

    def test_results_displayed_after_simulation(
        self, qtbot, configured_app_state
    ):
        """Results are displayed after simulation completes."""
        tab = MonteCarloTab(configured_app_state)
        qtbot.addWidget(tab)

        # Create mock results
        config = MonteCarloConfig(num_simulations=100)
        results = MonteCarloResults(
            config=config,
            num_trades=100,
            median_max_dd=0.15,
            p95_max_dd=0.25,
            p99_max_dd=0.35,
            max_dd_distribution=np.zeros(100),
            mean_final_equity=150000.0,
            std_final_equity=25000.0,
            p5_final_equity=100000.0,
            p95_final_equity=200000.0,
            probability_of_profit=0.75,
            final_equity_distribution=np.zeros(100),
            mean_cagr=0.15,
            median_cagr=0.12,
            cagr_distribution=np.zeros(100),
            mean_sharpe=1.5,
            mean_sortino=2.0,
            mean_calmar=1.2,
            sharpe_distribution=np.zeros(100),
            sortino_distribution=np.zeros(100),
            calmar_distribution=np.zeros(100),
            risk_of_ruin=0.05,
            mean_max_win_streak=5.0,
            max_max_win_streak=10,
            mean_max_loss_streak=3.0,
            max_max_loss_streak=7,
            win_streak_distribution=np.zeros(100, dtype=np.int64),
            loss_streak_distribution=np.zeros(100, dtype=np.int64),
            mean_recovery_factor=2.5,
            recovery_factor_distribution=np.zeros(100),
            mean_profit_factor=1.8,
            profit_factor_distribution=np.zeros(100),
            mean_avg_dd_duration=10.0,
            mean_max_dd_duration=20.0,
            max_dd_duration_distribution=np.zeros(100, dtype=np.int64),
            var=-0.02,
            cvar=-0.03,
            equity_percentiles=np.zeros((100, 5)),
        )

        # Store results in app state and display directly
        # (avoids recursion issues with full _on_simulation_complete path)
        configured_app_state.monte_carlo_results = results
        tab._display_results(results)

        # Results should be displayed
        assert tab._content_stack.currentIndex() == 1  # Results view
        assert configured_app_state.monte_carlo_results is results


class TestMonteCarloWorker:
    """Tests for MonteCarloWorker."""

    def test_worker_emits_finished_signal(self, qtbot):
        """Worker emits finished signal with results."""
        config = MonteCarloConfig(num_simulations=100)
        engine = MonteCarloEngine(config)
        gains = np.random.randn(50) * 0.02  # 50 trades

        worker = MonteCarloWorker(engine, gains)

        with qtbot.waitSignal(worker.finished, timeout=10000) as blocker:
            worker.run()

        assert blocker.args[0] is not None  # Results object

    def test_worker_emits_progress_signal(self, qtbot):
        """Worker emits progress signals during simulation."""
        config = MonteCarloConfig(num_simulations=200)  # Enough for progress callbacks
        engine = MonteCarloEngine(config)
        gains = np.random.randn(50) * 0.02

        worker = MonteCarloWorker(engine, gains)
        progress_calls = []

        def on_progress(completed, total):
            progress_calls.append((completed, total))

        worker.progress.connect(on_progress)

        with qtbot.waitSignal(worker.finished, timeout=10000):
            worker.run()

        # Should have received at least one progress update
        assert len(progress_calls) >= 1

    def test_worker_emits_error_on_exception(self, qtbot):
        """Worker emits error signal on exception."""
        config = MonteCarloConfig(num_simulations=100)
        engine = MonteCarloEngine(config)
        gains = np.array([])  # Empty array will cause error

        worker = MonteCarloWorker(engine, gains)

        with qtbot.waitSignal(worker.error, timeout=5000) as blocker:
            worker.run()

        assert "empty" in blocker.args[0].lower() or "cannot be empty" in blocker.args[0].lower()


class TestMonteCarloTabStatePersistence:
    """Tests for Monte Carlo state persistence across tab switches."""

    def test_results_persist_after_hide_show(self, qtbot, configured_app_state):
        """Results are preserved when tab is hidden and shown again."""
        tab = MonteCarloTab(configured_app_state)
        qtbot.addWidget(tab)

        # Create and display results
        config = MonteCarloConfig(num_simulations=100)
        results = MonteCarloResults(
            config=config,
            num_trades=100,
            median_max_dd=0.15,
            p95_max_dd=0.25,
            p99_max_dd=0.35,
            max_dd_distribution=np.zeros(100),
            mean_final_equity=150000.0,
            std_final_equity=25000.0,
            p5_final_equity=100000.0,
            p95_final_equity=200000.0,
            probability_of_profit=0.75,
            final_equity_distribution=np.zeros(100),
            mean_cagr=0.15,
            median_cagr=0.12,
            cagr_distribution=np.zeros(100),
            mean_sharpe=1.5,
            mean_sortino=2.0,
            mean_calmar=1.2,
            sharpe_distribution=np.zeros(100),
            sortino_distribution=np.zeros(100),
            calmar_distribution=np.zeros(100),
            risk_of_ruin=0.05,
            mean_max_win_streak=5.0,
            max_max_win_streak=10,
            mean_max_loss_streak=3.0,
            max_max_loss_streak=7,
            win_streak_distribution=np.zeros(100, dtype=np.int64),
            loss_streak_distribution=np.zeros(100, dtype=np.int64),
            mean_recovery_factor=2.5,
            recovery_factor_distribution=np.zeros(100),
            mean_profit_factor=1.8,
            profit_factor_distribution=np.zeros(100),
            mean_avg_dd_duration=10.0,
            mean_max_dd_duration=20.0,
            max_dd_duration_distribution=np.zeros(100, dtype=np.int64),
            var=-0.02,
            cvar=-0.03,
            equity_percentiles=np.zeros((100, 5)),
        )

        configured_app_state.monte_carlo_results = results
        tab._display_results(results)

        # Simulate hide and show
        tab.hide()
        tab.show()

        # Results should still be displayed
        assert tab._content_stack.currentIndex() == 1
        assert configured_app_state.monte_carlo_results is results


class TestMonteCarloTabCancellation:
    """Tests for Monte Carlo simulation cancellation."""

    def test_cancel_stops_simulation(self, qtbot, configured_app_state):
        """Cancellation stops running simulation."""
        tab = MonteCarloTab(configured_app_state)
        qtbot.addWidget(tab)

        # Create engine
        config = MonteCarloConfig(num_simulations=50000)  # Long-running
        tab._engine = MonteCarloEngine(config)
        configured_app_state.monte_carlo_running = True

        # Cancel
        tab._on_cancel_simulation()

        # State should be updated
        assert configured_app_state.monte_carlo_running is False
        assert tab._engine is None


class TestAppStateMonteCarloSignals:
    """Tests for AppState Monte Carlo signals."""

    def test_monte_carlo_started_signal(self, qtbot, app_state):
        """monte_carlo_started signal is emitted."""
        signal_received = []

        def on_started():
            signal_received.append(True)

        app_state.monte_carlo_started.connect(on_started)
        app_state.monte_carlo_started.emit()

        assert len(signal_received) == 1

    def test_monte_carlo_progress_signal(self, qtbot, app_state):
        """monte_carlo_progress signal carries correct data."""
        progress_data = []

        def on_progress(completed, total):
            progress_data.append((completed, total))

        app_state.monte_carlo_progress.connect(on_progress)
        app_state.monte_carlo_progress.emit(500, 1000)

        assert progress_data == [(500, 1000)]

    def test_monte_carlo_completed_signal(self, qtbot, app_state):
        """monte_carlo_completed signal carries results."""
        results_received = []

        def on_completed(results):
            results_received.append(results)

        app_state.monte_carlo_completed.connect(on_completed)

        mock_results = MagicMock()
        app_state.monte_carlo_completed.emit(mock_results)

        assert results_received == [mock_results]

    def test_monte_carlo_error_signal(self, qtbot, app_state):
        """monte_carlo_error signal carries error message."""
        errors_received = []

        def on_error(message):
            errors_received.append(message)

        app_state.monte_carlo_error.connect(on_error)
        app_state.monte_carlo_error.emit("Test error")

        assert errors_received == ["Test error"]

    def test_monte_carlo_running_property(self, app_state):
        """monte_carlo_running property works correctly."""
        assert app_state.monte_carlo_running is False

        app_state.monte_carlo_running = True
        assert app_state.monte_carlo_running is True

        app_state.monte_carlo_running = False
        assert app_state.monte_carlo_running is False
