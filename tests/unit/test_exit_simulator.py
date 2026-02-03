"""Tests for ExitSimulator."""

from datetime import datetime

import pandas as pd
import pytest

from src.core.exit_simulator import ExitEvent, ExitSimulator, ScalingConfig


class TestScalingConfig:
    """Tests for ScalingConfig dataclass."""

    def test_default_values(self) -> None:
        """ScalingConfig should have sensible defaults."""
        config = ScalingConfig()
        assert config.scale_pct == 50.0
        assert config.profit_target_pct == 35.0

    def test_custom_values(self) -> None:
        """ScalingConfig should accept custom values."""
        config = ScalingConfig(scale_pct=25.0, profit_target_pct=50.0)
        assert config.scale_pct == 25.0
        assert config.profit_target_pct == 50.0

    def test_scale_pct_zero_raises_error(self) -> None:
        """scale_pct of 0 should raise ValueError."""
        with pytest.raises(ValueError, match="scale_pct must be between 0"):
            ScalingConfig(scale_pct=0, profit_target_pct=35.0)

    def test_scale_pct_negative_raises_error(self) -> None:
        """Negative scale_pct should raise ValueError."""
        with pytest.raises(ValueError, match="scale_pct must be between 0"):
            ScalingConfig(scale_pct=-10, profit_target_pct=35.0)

    def test_scale_pct_over_100_raises_error(self) -> None:
        """scale_pct over 100 should raise ValueError."""
        with pytest.raises(ValueError, match="scale_pct must be between 0"):
            ScalingConfig(scale_pct=101, profit_target_pct=35.0)

    def test_scale_pct_100_is_valid(self) -> None:
        """scale_pct of exactly 100 should be valid."""
        config = ScalingConfig(scale_pct=100, profit_target_pct=35.0)
        assert config.scale_pct == 100

    def test_profit_target_pct_zero_raises_error(self) -> None:
        """profit_target_pct of 0 should raise ValueError."""
        with pytest.raises(ValueError, match="profit_target_pct must be greater than 0"):
            ScalingConfig(scale_pct=50.0, profit_target_pct=0)

    def test_profit_target_pct_negative_raises_error(self) -> None:
        """Negative profit_target_pct should raise ValueError."""
        with pytest.raises(ValueError, match="profit_target_pct must be greater than 0"):
            ScalingConfig(scale_pct=50.0, profit_target_pct=-5)


class TestExitEvent:
    """Tests for ExitEvent dataclass."""

    def test_exit_event_creation(self) -> None:
        """ExitEvent should store all required fields."""
        event = ExitEvent(
            time=datetime(2024, 1, 15, 10, 30),
            price=135.0,
            pct=50.0,
            reason="profit_target",
        )
        assert event.time == datetime(2024, 1, 15, 10, 30)
        assert event.price == 135.0
        assert event.pct == 50.0
        assert event.reason == "profit_target"


class TestExitSimulator:
    """Tests for ExitSimulator."""

    def test_profit_target_hit_scales_out(self) -> None:
        """When price hits profit target, scale out configured percentage."""
        bars = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",
                "2024-01-15 09:34",
            ]),
            "open": [100.0, 110.0, 130.0],
            "high": [105.0, 120.0, 140.0],  # 140 hits 35% target (entry 100 -> target 135)
            "low": [98.0, 108.0, 125.0],
            "close": [102.0, 115.0, 138.0],
        })

        config = ScalingConfig(scale_pct=50, profit_target_pct=35)
        simulator = ExitSimulator(
            entry_price=100.0,
            entry_time=datetime(2024, 1, 15, 9, 32),
            stop_level=95.0,  # Below entry = long trade
            scaling_config=config,
            session_close_time="16:00",
        )

        exits = simulator.simulate(bars)

        assert len(exits) == 1
        assert exits[0].reason == "profit_target"
        assert exits[0].price == 135.0  # Exactly at target
        assert exits[0].pct == 50

    def test_stop_hit_exits_full_position(self) -> None:
        """When price hits stop level, exit remaining position."""
        bars = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",
                "2024-01-15 09:34",
            ]),
            "open": [100.0, 98.0, 93.0],
            "high": [102.0, 99.0, 94.0],
            "low": [98.0, 94.0, 90.0],  # 94 hits stop at 95
            "close": [99.0, 95.0, 92.0],
        })

        config = ScalingConfig(scale_pct=50, profit_target_pct=35)
        simulator = ExitSimulator(
            entry_price=100.0,
            entry_time=datetime(2024, 1, 15, 9, 32),
            stop_level=95.0,
            scaling_config=config,
            session_close_time="16:00",
        )

        exits = simulator.simulate(bars)

        assert len(exits) == 1
        assert exits[0].reason == "stop_hit"
        assert exits[0].price == 95.0  # Exactly at stop
        assert exits[0].pct == 100  # Full position

    def test_session_close_exits_remaining(self) -> None:
        """At session close, exit any remaining position."""
        bars = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 15:59",
                "2024-01-15 16:00",  # Session close
            ]),
            "open": [100.0, 105.0, 106.0],
            "high": [102.0, 107.0, 108.0],  # Never hits 135 target
            "low": [99.0, 104.0, 105.0],  # Never hits 95 stop
            "close": [101.0, 106.0, 107.0],
        })

        config = ScalingConfig(scale_pct=50, profit_target_pct=35)
        simulator = ExitSimulator(
            entry_price=100.0,
            entry_time=datetime(2024, 1, 15, 9, 32),
            stop_level=95.0,
            scaling_config=config,
            session_close_time="16:00",
        )

        exits = simulator.simulate(bars)

        assert len(exits) == 1
        assert exits[0].reason == "session_close"
        assert exits[0].price == 107.0  # Close price at session end
        assert exits[0].pct == 100  # Full remaining position

    def test_profit_target_then_stop_exits_remaining(self) -> None:
        """Profit target scales out, then stop exits remaining."""
        bars = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",  # Hits profit target
                "2024-01-15 09:34",  # Reverses and hits stop
            ]),
            "open": [100.0, 130.0, 100.0],
            "high": [105.0, 140.0, 102.0],  # 140 hits target
            "low": [98.0, 125.0, 90.0],  # 90 hits stop
            "close": [102.0, 138.0, 92.0],
        })

        config = ScalingConfig(scale_pct=50, profit_target_pct=35)
        simulator = ExitSimulator(
            entry_price=100.0,
            entry_time=datetime(2024, 1, 15, 9, 32),
            stop_level=95.0,
            scaling_config=config,
            session_close_time="16:00",
        )

        exits = simulator.simulate(bars)

        assert len(exits) == 2
        # First exit: profit target
        assert exits[0].reason == "profit_target"
        assert exits[0].price == 135.0
        assert exits[0].pct == 50
        # Second exit: stop hit on remaining
        assert exits[1].reason == "stop_hit"
        assert exits[1].price == 95.0
        assert exits[1].pct == 50  # Remaining 50%

    def test_profit_target_then_session_close(self) -> None:
        """Profit target scales out, then session close exits remaining."""
        bars = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",  # Hits profit target
                "2024-01-15 16:00",  # Session close
            ]),
            "open": [100.0, 130.0, 140.0],
            "high": [105.0, 140.0, 142.0],  # Hits target
            "low": [98.0, 125.0, 138.0],  # Never hits stop
            "close": [102.0, 138.0, 141.0],
        })

        config = ScalingConfig(scale_pct=50, profit_target_pct=35)
        simulator = ExitSimulator(
            entry_price=100.0,
            entry_time=datetime(2024, 1, 15, 9, 32),
            stop_level=95.0,
            scaling_config=config,
            session_close_time="16:00",
        )

        exits = simulator.simulate(bars)

        assert len(exits) == 2
        assert exits[0].reason == "profit_target"
        assert exits[0].pct == 50
        assert exits[1].reason == "session_close"
        assert exits[1].pct == 50  # Remaining

    def test_bars_before_entry_ignored(self) -> None:
        """Bars before entry time should not trigger exits."""
        bars = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:30",  # Before entry
                "2024-01-15 09:31",  # Before entry
                "2024-01-15 09:32",  # Entry time
                "2024-01-15 09:33",  # After entry - hits target
            ]),
            "open": [90.0, 130.0, 100.0, 130.0],
            "high": [95.0, 140.0, 105.0, 140.0],  # Would hit target if processed
            "low": [85.0, 125.0, 98.0, 125.0],
            "close": [92.0, 135.0, 102.0, 138.0],
        })

        config = ScalingConfig(scale_pct=50, profit_target_pct=35)
        simulator = ExitSimulator(
            entry_price=100.0,
            entry_time=datetime(2024, 1, 15, 9, 32),
            stop_level=95.0,
            scaling_config=config,
            session_close_time="16:00",
        )

        exits = simulator.simulate(bars)

        # Only one exit from the bar after entry
        assert len(exits) == 1
        assert exits[0].time == datetime(2024, 1, 15, 9, 33)

    def test_empty_bars_returns_empty_list(self) -> None:
        """Empty bars DataFrame returns empty exit list."""
        bars = pd.DataFrame({
            "datetime": pd.to_datetime([]),
            "open": [],
            "high": [],
            "low": [],
            "close": [],
        })

        config = ScalingConfig()
        simulator = ExitSimulator(
            entry_price=100.0,
            entry_time=datetime(2024, 1, 15, 9, 32),
            stop_level=95.0,
            scaling_config=config,
            session_close_time="16:00",
        )

        exits = simulator.simulate(bars)
        assert exits == []

    def test_short_trade_stop_above_entry(self) -> None:
        """Short trade: stop above entry, profit target below entry."""
        bars = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",  # Price drops to hit profit target
            ]),
            "open": [100.0, 90.0],
            "high": [102.0, 92.0],  # Never hits stop at 105
            "low": [95.0, 60.0],  # 60 hits 35% target (entry 100 -> target 65)
            "close": [98.0, 62.0],
        })

        config = ScalingConfig(scale_pct=50, profit_target_pct=35)
        simulator = ExitSimulator(
            entry_price=100.0,
            entry_time=datetime(2024, 1, 15, 9, 32),
            stop_level=105.0,  # Above entry = short trade
            scaling_config=config,
            session_close_time="16:00",
        )

        exits = simulator.simulate(bars)

        assert len(exits) == 1
        assert exits[0].reason == "profit_target"
        assert exits[0].price == 65.0  # Target for short
        assert exits[0].pct == 50

    def test_short_trade_stop_hit(self) -> None:
        """Short trade: price rises to hit stop."""
        bars = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",  # Price rises to hit stop
            ]),
            "open": [100.0, 102.0],
            "high": [102.0, 108.0],  # 108 hits stop at 105
            "low": [98.0, 100.0],
            "close": [101.0, 106.0],
        })

        config = ScalingConfig(scale_pct=50, profit_target_pct=35)
        simulator = ExitSimulator(
            entry_price=100.0,
            entry_time=datetime(2024, 1, 15, 9, 32),
            stop_level=105.0,  # Above entry = short trade
            scaling_config=config,
            session_close_time="16:00",
        )

        exits = simulator.simulate(bars)

        assert len(exits) == 1
        assert exits[0].reason == "stop_hit"
        assert exits[0].price == 105.0  # Stop price
        assert exits[0].pct == 100  # Full position

    def test_entry_price_zero_raises_error(self) -> None:
        """entry_price of 0 should raise ValueError."""
        config = ScalingConfig()
        with pytest.raises(ValueError, match="entry_price must be greater than 0"):
            ExitSimulator(
                entry_price=0,
                entry_time=datetime(2024, 1, 15, 9, 32),
                stop_level=95.0,
                scaling_config=config,
            )

    def test_entry_price_negative_raises_error(self) -> None:
        """Negative entry_price should raise ValueError."""
        config = ScalingConfig()
        with pytest.raises(ValueError, match="entry_price must be greater than 0"):
            ExitSimulator(
                entry_price=-100.0,
                entry_time=datetime(2024, 1, 15, 9, 32),
                stop_level=95.0,
                scaling_config=config,
            )

    def test_stop_level_zero_raises_error(self) -> None:
        """stop_level of 0 should raise ValueError."""
        config = ScalingConfig()
        with pytest.raises(ValueError, match="stop_level must be greater than 0"):
            ExitSimulator(
                entry_price=100.0,
                entry_time=datetime(2024, 1, 15, 9, 32),
                stop_level=0,
                scaling_config=config,
            )

    def test_stop_level_negative_raises_error(self) -> None:
        """Negative stop_level should raise ValueError."""
        config = ScalingConfig()
        with pytest.raises(ValueError, match="stop_level must be greater than 0"):
            ExitSimulator(
                entry_price=100.0,
                entry_time=datetime(2024, 1, 15, 9, 32),
                stop_level=-50.0,
                scaling_config=config,
            )

    def test_entry_price_equals_stop_level_raises_error(self) -> None:
        """entry_price equal to stop_level should raise ValueError."""
        config = ScalingConfig()
        with pytest.raises(ValueError, match="entry_price and stop_level must be different"):
            ExitSimulator(
                entry_price=100.0,
                entry_time=datetime(2024, 1, 15, 9, 32),
                stop_level=100.0,
                scaling_config=config,
            )

    def test_session_close_time_invalid_format_raises_error(self) -> None:
        """Invalid session_close_time format should raise ValueError."""
        config = ScalingConfig()
        with pytest.raises(ValueError, match="session_close_time must be in HH:MM format"):
            ExitSimulator(
                entry_price=100.0,
                entry_time=datetime(2024, 1, 15, 9, 32),
                stop_level=95.0,
                scaling_config=config,
                session_close_time="16-00",
            )

    def test_session_close_time_invalid_hours_raises_error(self) -> None:
        """Invalid hours in session_close_time should raise ValueError."""
        config = ScalingConfig()
        with pytest.raises(ValueError, match="hours must be 0-23"):
            ExitSimulator(
                entry_price=100.0,
                entry_time=datetime(2024, 1, 15, 9, 32),
                stop_level=95.0,
                scaling_config=config,
                session_close_time="25:00",
            )

    def test_session_close_time_invalid_minutes_raises_error(self) -> None:
        """Invalid minutes in session_close_time should raise ValueError."""
        config = ScalingConfig()
        with pytest.raises(ValueError, match="minutes must be 0-59"):
            ExitSimulator(
                entry_price=100.0,
                entry_time=datetime(2024, 1, 15, 9, 32),
                stop_level=95.0,
                scaling_config=config,
                session_close_time="16:60",
            )

    def test_session_close_time_non_numeric_raises_error(self) -> None:
        """Non-numeric session_close_time should raise ValueError."""
        config = ScalingConfig()
        with pytest.raises(ValueError, match="session_close_time must be in HH:MM format"):
            ExitSimulator(
                entry_price=100.0,
                entry_time=datetime(2024, 1, 15, 9, 32),
                stop_level=95.0,
                scaling_config=config,
                session_close_time="ab:cd",
            )
