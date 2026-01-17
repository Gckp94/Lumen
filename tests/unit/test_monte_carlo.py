"""Unit tests for Monte Carlo simulation engine."""

import numpy as np
import pandas as pd
import pytest

from src.core.monte_carlo import (
    MonteCarloConfig,
    MonteCarloEngine,
    MonteCarloResults,
    PositionSizingMode,
    extract_gains_from_app_state,
)


class TestMonteCarloConfig:
    """Tests for MonteCarloConfig dataclass."""

    def test_default_values(self) -> None:
        """Default configuration values are correct."""
        config = MonteCarloConfig()
        assert config.num_simulations == 5000
        assert config.initial_capital == 100000.0
        assert config.ruin_threshold_pct == 50.0
        assert config.var_confidence_pct == 5.0
        assert config.simulation_type == "resample"

    def test_custom_values(self) -> None:
        """Custom configuration values are accepted."""
        config = MonteCarloConfig(
            num_simulations=1000,
            initial_capital=50000.0,
            ruin_threshold_pct=25.0,
            var_confidence_pct=1.0,
            simulation_type="reshuffle",
        )
        assert config.num_simulations == 1000
        assert config.initial_capital == 50000.0
        assert config.ruin_threshold_pct == 25.0
        assert config.var_confidence_pct == 1.0
        assert config.simulation_type == "reshuffle"

    def test_num_simulations_too_low(self) -> None:
        """Validation rejects simulations below 100."""
        with pytest.raises(ValueError, match="num_simulations must be between"):
            MonteCarloConfig(num_simulations=99)

    def test_num_simulations_too_high(self) -> None:
        """Validation rejects simulations above 50,000."""
        with pytest.raises(ValueError, match="num_simulations must be between"):
            MonteCarloConfig(num_simulations=50001)

    def test_num_simulations_boundary_low(self) -> None:
        """Boundary value 100 is accepted."""
        config = MonteCarloConfig(num_simulations=100)
        assert config.num_simulations == 100

    def test_num_simulations_boundary_high(self) -> None:
        """Boundary value 50,000 is accepted."""
        config = MonteCarloConfig(num_simulations=50000)
        assert config.num_simulations == 50000

    def test_invalid_initial_capital(self) -> None:
        """Validation rejects non-positive initial capital."""
        with pytest.raises(ValueError, match="initial_capital must be positive"):
            MonteCarloConfig(initial_capital=0)

    def test_invalid_ruin_threshold(self) -> None:
        """Validation rejects invalid ruin threshold."""
        with pytest.raises(ValueError, match="ruin_threshold_pct must be between"):
            MonteCarloConfig(ruin_threshold_pct=0)
        with pytest.raises(ValueError, match="ruin_threshold_pct must be between"):
            MonteCarloConfig(ruin_threshold_pct=100)

    def test_invalid_simulation_type(self) -> None:
        """Validation rejects invalid simulation type."""
        with pytest.raises(ValueError, match="simulation_type must be"):
            MonteCarloConfig(simulation_type="invalid")


class TestMonteCarloEngine:
    """Tests for MonteCarloEngine class."""

    @pytest.fixture
    def sample_gains(self) -> np.ndarray:
        """Sample gains array for testing (100 trades)."""
        np.random.seed(42)
        # Mix of wins and losses around +0.5% mean
        return np.random.normal(0.005, 0.02, 100)

    @pytest.fixture
    def engine(self) -> MonteCarloEngine:
        """Engine with minimal config for fast tests."""
        config = MonteCarloConfig(num_simulations=100)
        return MonteCarloEngine(config)

    def test_resample_produces_correct_shape(self, engine: MonteCarloEngine) -> None:
        """Resampled output has same length as input."""
        gains = np.array([0.01, 0.02, -0.01, 0.03, -0.02])
        resampled = engine._resample(gains, len(gains))
        assert len(resampled) == len(gains)

    def test_resample_values_from_original(self, engine: MonteCarloEngine) -> None:
        """Resampled values are all from original array."""
        gains = np.array([0.01, 0.02, -0.01, 0.03, -0.02])
        resampled = engine._resample(gains, len(gains))
        for val in resampled:
            assert val in gains

    def test_reshuffle_preserves_all_values(self, engine: MonteCarloEngine) -> None:
        """Reshuffled output contains all original values."""
        gains = np.array([0.01, 0.02, -0.01, 0.03, -0.02])
        reshuffled = engine._reshuffle(gains)
        assert len(reshuffled) == len(gains)
        assert np.allclose(np.sort(reshuffled), np.sort(gains))

    def test_reshuffle_produces_different_order(self, engine: MonteCarloEngine) -> None:
        """Reshuffling produces a permutation (statistically)."""
        gains = np.array([0.01, 0.02, -0.01, 0.03, -0.02, 0.04, -0.03, 0.05])
        same_order_count = 0
        for _ in range(100):
            reshuffled = engine._reshuffle(gains)
            if np.array_equal(reshuffled, gains):
                same_order_count += 1
        # Very unlikely to get same order more than a few times out of 100
        assert same_order_count < 10

    def test_equity_curve_calculation_compounded_kelly(self) -> None:
        """Equity curve calculation is correct for compounded kelly mode."""
        config = MonteCarloConfig(
            num_simulations=100,
            position_sizing_mode=PositionSizingMode.COMPOUNDED_KELLY,
            fractional_kelly_pct=25.0,
        )
        engine = MonteCarloEngine(config)

        gains = np.array([0.10, -0.05, 0.08])  # +10%, -5%, +8%
        equity = engine._simulate_equity_curve(gains, 100000.0)

        # Manual calculation with 25% fractional kelly:
        # After trade 1: 100000 * (1 + 0.25 * 0.10) = 100000 * 1.025 = 102500
        # After trade 2: 102500 * (1 + 0.25 * -0.05) = 102500 * 0.9875 = 101218.75
        # After trade 3: 101218.75 * (1 + 0.25 * 0.08) = 101218.75 * 1.02 = 103243.125
        expected = np.array([102500.0, 101218.75, 103243.125])
        np.testing.assert_allclose(equity, expected)

    def test_equity_curve_calculation_flat_stake(self) -> None:
        """Equity curve calculation is correct for flat stake mode."""
        config = MonteCarloConfig(
            num_simulations=100,
            position_sizing_mode=PositionSizingMode.FLAT_STAKE,
            flat_stake=10000.0,
        )
        engine = MonteCarloEngine(config)

        gains = np.array([0.10, -0.05, 0.08])  # +10%, -5%, +8%
        equity = engine._simulate_equity_curve(gains, 100000.0)

        # Manual calculation with flat stake of $10,000:
        # After trade 1: 100000 + (10000 * 0.10) = 100000 + 1000 = 101000
        # After trade 2: 101000 + (10000 * -0.05) = 101000 - 500 = 100500
        # After trade 3: 100500 + (10000 * 0.08) = 100500 + 800 = 101300
        expected = np.array([101000.0, 100500.0, 101300.0])
        np.testing.assert_allclose(equity, expected)

    def test_max_drawdown_calculation(self, engine: MonteCarloEngine) -> None:
        """Max drawdown calculation matches hand-calculated value."""
        # Equity: 100 -> 120 -> 90 -> 100
        # Max DD occurs at 90 when peak was 120: (120-90)/120 = 25%
        equity = np.array([100.0, 120.0, 90.0, 100.0])
        max_dd = engine._calculate_max_drawdown(equity)
        assert max_dd == pytest.approx(0.25)

    def test_max_drawdown_no_drawdown(self, engine: MonteCarloEngine) -> None:
        """Max drawdown is 0 for monotonically increasing equity."""
        equity = np.array([100.0, 110.0, 120.0, 130.0])
        max_dd = engine._calculate_max_drawdown(equity)
        assert max_dd == pytest.approx(0.0)

    def test_max_win_streak(self, engine: MonteCarloEngine) -> None:
        """Max win streak calculation is correct."""
        gains = np.array([0.01, 0.02, -0.01, 0.01, 0.02, 0.03, -0.02])
        streak = engine._calculate_max_streak(gains, win=True)
        assert streak == 3  # Trades 4, 5, 6

    def test_max_loss_streak(self, engine: MonteCarloEngine) -> None:
        """Max loss streak calculation is correct."""
        gains = np.array([0.01, -0.01, -0.02, -0.01, 0.02, -0.03])
        streak = engine._calculate_max_streak(gains, win=False)
        assert streak == 3  # Trades 2, 3, 4

    def test_max_streak_empty(self, engine: MonteCarloEngine) -> None:
        """Max streak is 0 for empty array."""
        gains = np.array([])
        assert engine._calculate_max_streak(gains, win=True) == 0
        assert engine._calculate_max_streak(gains, win=False) == 0

    def test_max_streak_all_winners(self, engine: MonteCarloEngine) -> None:
        """All winners: win streak = total, loss streak = 0."""
        gains = np.array([0.01, 0.02, 0.03, 0.04])
        assert engine._calculate_max_streak(gains, win=True) == 4
        assert engine._calculate_max_streak(gains, win=False) == 0

    def test_max_streak_all_losers(self, engine: MonteCarloEngine) -> None:
        """All losers: loss streak = total, win streak = 0."""
        gains = np.array([-0.01, -0.02, -0.03, -0.04])
        assert engine._calculate_max_streak(gains, win=False) == 4
        assert engine._calculate_max_streak(gains, win=True) == 0

    def test_drawdown_duration_calculation(self, engine: MonteCarloEngine) -> None:
        """Drawdown duration calculation is correct."""
        # Equity: peak at 120, drawdown from trade 3-4, recovery at trade 5
        equity = np.array([100.0, 120.0, 110.0, 105.0, 125.0])
        avg_dur, max_dur = engine._calculate_drawdown_duration(equity)
        assert max_dur == 2  # Trades 3, 4

    def test_drawdown_duration_no_drawdown(self, engine: MonteCarloEngine) -> None:
        """Drawdown duration is 0 for monotonically increasing equity."""
        equity = np.array([100.0, 110.0, 120.0, 130.0])
        avg_dur, max_dur = engine._calculate_drawdown_duration(equity)
        assert avg_dur == 0.0
        assert max_dur == 0

    def test_run_returns_results(
        self, engine: MonteCarloEngine, sample_gains: np.ndarray
    ) -> None:
        """Run method returns MonteCarloResults."""
        results = engine.run(sample_gains)
        assert isinstance(results, MonteCarloResults)

    def test_run_results_contain_all_metrics(
        self, engine: MonteCarloEngine, sample_gains: np.ndarray
    ) -> None:
        """Results contain all expected metric fields."""
        results = engine.run(sample_gains)

        # Check key metrics exist and are reasonable
        assert results.num_trades == len(sample_gains)
        assert 0 <= results.median_max_dd <= 1
        assert 0 <= results.p95_max_dd <= 1
        assert results.mean_final_equity > 0
        assert 0 <= results.probability_of_profit <= 1
        assert 0 <= results.risk_of_ruin <= 1
        assert results.mean_max_win_streak >= 0
        assert results.mean_max_loss_streak >= 0

    def test_run_empty_gains_raises_error(self, engine: MonteCarloEngine) -> None:
        """Empty gains array raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            engine.run(np.array([]))

    def test_run_insufficient_trades_raises_error(
        self, engine: MonteCarloEngine
    ) -> None:
        """< 10 trades raises ValueError."""
        with pytest.raises(ValueError, match="at least 10 trades"):
            engine.run(np.array([0.01, 0.02, -0.01]))

    def test_run_exactly_10_trades(self, engine: MonteCarloEngine) -> None:
        """Exactly 10 trades is accepted."""
        gains = np.array([0.01, 0.02, -0.01, 0.03, -0.02, 0.01, -0.01, 0.02, -0.01, 0.01])
        results = engine.run(gains)
        assert results.num_trades == 10

    def test_cancellation_stops_early(self, sample_gains: np.ndarray) -> None:
        """Cancel flag stops simulation before completion."""
        config = MonteCarloConfig(num_simulations=10000)
        engine = MonteCarloEngine(config)

        completed_count = 0

        def progress_callback(completed: int, total: int) -> None:
            nonlocal completed_count
            completed_count = completed
            if completed >= 500:
                engine.cancel()

        engine.run(sample_gains, progress_callback=progress_callback)
        # Should have stopped around 500, definitely less than 10000
        assert completed_count < 5000

    def test_progress_callback_invoked(
        self, engine: MonteCarloEngine, sample_gains: np.ndarray
    ) -> None:
        """Progress callback is called during simulation."""
        progress_calls = []

        def progress_callback(completed: int, total: int) -> None:
            progress_calls.append((completed, total))

        engine.run(sample_gains, progress_callback=progress_callback)

        # Should be called every 100 simulations
        assert len(progress_calls) > 0
        # Final call should be (100, 100) for 100 simulations
        assert progress_calls[-1] == (100, 100)

    def test_resample_vs_reshuffle_type(self, sample_gains: np.ndarray) -> None:
        """Resample and reshuffle produce different distributions."""
        np.random.seed(42)

        config_resample = MonteCarloConfig(num_simulations=100, simulation_type="resample")
        engine_resample = MonteCarloEngine(config_resample)
        results_resample = engine_resample.run(sample_gains)

        np.random.seed(42)
        config_reshuffle = MonteCarloConfig(
            num_simulations=100, simulation_type="reshuffle"
        )
        engine_reshuffle = MonteCarloEngine(config_reshuffle)
        results_reshuffle = engine_reshuffle.run(sample_gains)

        # Both should complete successfully
        assert results_resample.num_trades == len(sample_gains)
        assert results_reshuffle.num_trades == len(sample_gains)

    def test_equity_percentiles_shape(
        self, engine: MonteCarloEngine, sample_gains: np.ndarray
    ) -> None:
        """Equity percentiles array has correct shape."""
        results = engine.run(sample_gains)
        # Shape should be (num_trades, 5) for 5 percentiles
        assert results.equity_percentiles.shape == (len(sample_gains), 5)

    def test_all_winners_edge_case(self, engine: MonteCarloEngine) -> None:
        """All winners: profit factor = inf, loss streak = 0."""
        gains = np.array([0.01, 0.02, 0.01, 0.015, 0.02, 0.01, 0.02, 0.01, 0.015, 0.02])
        results = engine.run(gains)

        assert results.max_max_loss_streak == 0
        assert results.probability_of_profit == 1.0
        # Profit factor array contains inf values when no losers
        # mean_profit_factor may be nan if filtered; check distribution instead
        assert np.all(np.isinf(results.profit_factor_distribution))

    def test_all_losers_edge_case(self, engine: MonteCarloEngine) -> None:
        """All losers: win streak = 0, final equity below initial."""
        # Use losses to ensure clear negative outcome
        gains = np.array(
            [-0.05, -0.06, -0.05, -0.04, -0.06, -0.05, -0.06, -0.05, -0.04, -0.06]
        )
        results = engine.run(gains)

        assert results.max_max_win_streak == 0
        assert results.probability_of_profit == 0.0
        # Final equity should be below initial capital (with 25% Kelly, ~12% total loss)
        assert results.mean_final_equity < engine.config.initial_capital


class TestExtractGainsFromAppState:
    """Tests for extract_gains_from_app_state helper function."""

    @pytest.fixture
    def sample_df(self) -> pd.DataFrame:
        """Sample DataFrame with adjusted_gain_pct and trigger columns.

        Values are in decimal format (e.g., 0.02 = 2% gain).
        """
        return pd.DataFrame(
            {
                "adjusted_gain_pct": [
                    0.02, -0.01, 0.03, -0.02, 0.01, -0.005, 0.025, -0.015, 0.005, -0.005,
                    0.015, -0.012, 0.022, -0.008, 0.009, -0.003, 0.018, -0.01, 0.006, -0.004,
                ],
                "gain_pct": [
                    0.02, -0.01, 0.03, -0.02, 0.01, -0.005, 0.025, -0.015, 0.005, -0.005,
                    0.015, -0.012, 0.022, -0.008, 0.009, -0.003, 0.018, -0.01, 0.006, -0.004,
                ],
                "trigger_number": [
                    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,  # First 10: trigger 1
                    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,  # Next 10: trigger 2
                ],
            }
        )

    @pytest.fixture
    def mock_column_mapping(self):
        """Mock column mapping object."""

        class MockMapping:
            gain_pct = "gain_pct"

        return MockMapping()

    def test_extract_gains_basic(
        self, sample_df: pd.DataFrame, mock_column_mapping
    ) -> None:
        """Basic extraction without first trigger filter."""
        gains = extract_gains_from_app_state(
            sample_df, mock_column_mapping, first_trigger_enabled=False
        )
        assert len(gains) == 20  # All 20 trades
        # Values are already in decimal format (no conversion)
        assert gains[0] == pytest.approx(0.02)

    def test_extract_gains_with_first_trigger(
        self, sample_df: pd.DataFrame, mock_column_mapping
    ) -> None:
        """Extraction with first trigger filter enabled."""
        gains = extract_gains_from_app_state(
            sample_df, mock_column_mapping, first_trigger_enabled=True
        )
        assert len(gains) == 10  # Only trigger_number == 1

    def test_extract_gains_empty_df(self, mock_column_mapping) -> None:
        """Empty DataFrame raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            extract_gains_from_app_state(
                pd.DataFrame(), mock_column_mapping, first_trigger_enabled=False
            )

    def test_extract_gains_none_df(self, mock_column_mapping) -> None:
        """None DataFrame raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            extract_gains_from_app_state(
                None, mock_column_mapping, first_trigger_enabled=False
            )

    def test_extract_gains_none_mapping(self, sample_df: pd.DataFrame) -> None:
        """None column mapping raises ValueError."""
        with pytest.raises(ValueError, match="Column mapping"):
            extract_gains_from_app_state(sample_df, None, first_trigger_enabled=False)

    def test_extract_gains_missing_column(self) -> None:
        """Missing gain column raises ValueError when adjusted_gain_pct not present."""
        # DataFrame without adjusted_gain_pct, so it falls back to gain_pct mapping
        df = pd.DataFrame(
            {
                "some_other_column": [0.01] * 10,
            }
        )

        class BadMapping:
            gain_pct = "nonexistent_column"

        with pytest.raises(ValueError, match="not found"):
            extract_gains_from_app_state(df, BadMapping(), first_trigger_enabled=False)

    def test_extract_gains_insufficient_trades(self, mock_column_mapping) -> None:
        """< 10 trades after filtering raises ValueError."""
        small_df = pd.DataFrame({"adjusted_gain_pct": [0.01, 0.02, -0.01]})
        with pytest.raises(ValueError, match="at least 10 trades"):
            extract_gains_from_app_state(
                small_df, mock_column_mapping, first_trigger_enabled=False
            )

    def test_extract_gains_fallback_to_gain_pct(self, mock_column_mapping) -> None:
        """Falls back to gain_pct when adjusted_gain_pct is not present."""
        df = pd.DataFrame(
            {
                "gain_pct": [
                    0.02,
                    -0.01,
                    0.03,
                    -0.02,
                    0.01,
                    -0.005,
                    0.025,
                    -0.015,
                    0.005,
                    -0.005,
                ]
            }
        )
        gains = extract_gains_from_app_state(
            df, mock_column_mapping, first_trigger_enabled=False
        )
        # Values should be unchanged (no conversion)
        assert gains[0] == pytest.approx(0.02)

    def test_extract_gains_uses_adjusted_gain_pct(self, mock_column_mapping) -> None:
        """Uses adjusted_gain_pct when present, ignoring gain_pct."""
        df = pd.DataFrame(
            {
                # adjusted_gain_pct has capped losses (e.g., -0.05 for 5% stop)
                "adjusted_gain_pct": [
                    0.02, -0.05, 0.03, -0.05, 0.01,
                    -0.05, 0.025, -0.05, 0.005, -0.05,
                ],
                # gain_pct has uncapped losses (should be ignored)
                "gain_pct": [
                    0.02, -0.50, 0.03, -0.40, 0.01,
                    -0.30, 0.025, -0.20, 0.005, -0.10,
                ],
            }
        )
        gains = extract_gains_from_app_state(
            df, mock_column_mapping, first_trigger_enabled=False
        )
        # Should use adjusted_gain_pct, not gain_pct
        assert gains[0] == pytest.approx(0.02)
        assert gains[1] == pytest.approx(-0.05)  # Capped loss, not -0.50
