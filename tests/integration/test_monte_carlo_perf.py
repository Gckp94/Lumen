"""Performance tests for Monte Carlo simulation engine."""

import time

import numpy as np
import pytest

from src.core.monte_carlo import MonteCarloConfig, MonteCarloEngine


class TestMonteCarloPerformance:
    """Performance tests for Monte Carlo simulation engine."""

    @pytest.fixture
    def gains_1000_trades(self) -> np.ndarray:
        """Generate 1,000 trades for performance testing."""
        np.random.seed(42)
        return np.random.normal(0.005, 0.02, 1000)

    @pytest.fixture
    def gains_10000_trades(self) -> np.ndarray:
        """Generate 10,000 trades for performance testing."""
        np.random.seed(42)
        return np.random.normal(0.005, 0.02, 10000)

    @pytest.mark.slow
    def test_5000_sims_1000_trades_under_10s(
        self, gains_1000_trades: np.ndarray
    ) -> None:
        """Performance target: 5,000 simulations with 1,000 trades < 10s.

        This is the primary performance target specified in the story.
        """
        config = MonteCarloConfig(num_simulations=5000)
        engine = MonteCarloEngine(config)

        start_time = time.perf_counter()
        results = engine.run(gains_1000_trades)
        elapsed = time.perf_counter() - start_time

        # Verify results are valid
        assert results.num_trades == 1000
        assert len(results.max_dd_distribution) == 5000

        # Performance assertion
        assert elapsed < 10.0, (
            f"5,000 simulations with 1,000 trades took {elapsed:.2f}s, "
            "expected < 10s"
        )
        print(f"\n5,000 sims x 1,000 trades completed in {elapsed:.2f}s")

    @pytest.mark.slow
    def test_5000_sims_10000_trades_under_30s(
        self, gains_10000_trades: np.ndarray
    ) -> None:
        """Performance target: 5,000 simulations with 10,000 trades < 30s.

        This tests scaling behavior with larger trade counts.
        Performance should scale approximately linearly with trade count.
        """
        config = MonteCarloConfig(num_simulations=5000)
        engine = MonteCarloEngine(config)

        start_time = time.perf_counter()
        results = engine.run(gains_10000_trades)
        elapsed = time.perf_counter() - start_time

        # Verify results are valid
        assert results.num_trades == 10000
        assert len(results.max_dd_distribution) == 5000

        # Performance assertion (more lenient for larger dataset)
        assert elapsed < 30.0, (
            f"5,000 simulations with 10,000 trades took {elapsed:.2f}s, "
            "expected < 30s"
        )
        print(f"\n5,000 sims x 10,000 trades completed in {elapsed:.2f}s")

    @pytest.mark.slow
    def test_resample_vs_reshuffle_performance(
        self, gains_1000_trades: np.ndarray
    ) -> None:
        """Compare performance of resample vs reshuffle methods.

        Reshuffle may be slightly slower due to permutation generation.
        """
        n_sims = 1000

        # Resample
        config_resample = MonteCarloConfig(
            num_simulations=n_sims, simulation_type="resample"
        )
        engine_resample = MonteCarloEngine(config_resample)
        start_time = time.perf_counter()
        engine_resample.run(gains_1000_trades)
        resample_time = time.perf_counter() - start_time

        # Reshuffle
        config_reshuffle = MonteCarloConfig(
            num_simulations=n_sims, simulation_type="reshuffle"
        )
        engine_reshuffle = MonteCarloEngine(config_reshuffle)
        start_time = time.perf_counter()
        engine_reshuffle.run(gains_1000_trades)
        reshuffle_time = time.perf_counter() - start_time

        print(f"\nResample: {resample_time:.2f}s, Reshuffle: {reshuffle_time:.2f}s")

        # Both should complete in reasonable time
        assert resample_time < 5.0, f"Resample took {resample_time:.2f}s"
        assert reshuffle_time < 5.0, f"Reshuffle took {reshuffle_time:.2f}s"

    @pytest.mark.slow
    def test_progress_callback_overhead(self, gains_1000_trades: np.ndarray) -> None:
        """Progress callback should not significantly impact performance.

        Adding a progress callback should add minimal overhead.
        """
        n_sims = 1000

        # Without callback
        config = MonteCarloConfig(num_simulations=n_sims)
        engine_no_callback = MonteCarloEngine(config)
        start_time = time.perf_counter()
        engine_no_callback.run(gains_1000_trades)
        time_no_callback = time.perf_counter() - start_time

        # With callback
        callback_count = 0

        def progress_callback(completed: int, total: int) -> None:
            nonlocal callback_count
            callback_count += 1

        engine_with_callback = MonteCarloEngine(config)
        start_time = time.perf_counter()
        engine_with_callback.run(gains_1000_trades, progress_callback=progress_callback)
        time_with_callback = time.perf_counter() - start_time

        print(
            f"\nNo callback: {time_no_callback:.3f}s, "
            f"With callback: {time_with_callback:.3f}s"
        )

        # Callback overhead should be < 20%
        overhead = (time_with_callback - time_no_callback) / time_no_callback
        assert overhead < 0.20, (
            f"Callback overhead is {overhead * 100:.1f}%, expected < 20%"
        )

    @pytest.mark.slow
    def test_memory_efficiency(self, gains_10000_trades: np.ndarray) -> None:
        """Test that memory usage is reasonable for large simulations.

        Results should use efficient numpy arrays rather than Python lists.
        """
        config = MonteCarloConfig(num_simulations=5000)
        engine = MonteCarloEngine(config)

        results = engine.run(gains_10000_trades)

        # Verify arrays are numpy arrays (memory efficient)
        assert isinstance(results.max_dd_distribution, np.ndarray)
        assert isinstance(results.final_equity_distribution, np.ndarray)
        assert isinstance(results.equity_percentiles, np.ndarray)

        # Check dtypes are appropriate
        assert results.max_dd_distribution.dtype == np.float64
        assert results.win_streak_distribution.dtype == np.int64

        # Verify shapes
        assert results.max_dd_distribution.shape == (5000,)
        assert results.equity_percentiles.shape == (10000, 5)

    @pytest.mark.slow
    def test_cancellation_response_time(self, gains_1000_trades: np.ndarray) -> None:
        """Cancellation should stop simulation promptly.

        When cancelled, simulation should stop within a few iterations.
        """
        config = MonteCarloConfig(num_simulations=50000)  # Many sims
        engine = MonteCarloEngine(config)

        completed_at_cancel = 0
        final_completed = 0

        def progress_callback(completed: int, total: int) -> None:
            nonlocal completed_at_cancel, final_completed
            final_completed = completed
            if completed >= 500:  # Cancel early
                engine.cancel()
                if completed_at_cancel == 0:
                    completed_at_cancel = completed

        start_time = time.perf_counter()
        engine.run(gains_1000_trades, progress_callback=progress_callback)
        elapsed = time.perf_counter() - start_time

        # Should have stopped near the cancel point (within 200 iterations)
        overshoot = final_completed - completed_at_cancel
        assert overshoot < 200, (
            f"Simulation continued {overshoot} iterations after cancel"
        )

        # Should complete much faster than running all 50,000 simulations
        assert elapsed < 5.0, f"Cancellation took {elapsed:.2f}s to complete"
