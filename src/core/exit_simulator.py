"""Exit simulator for trade management with scaling and stops."""

from dataclasses import dataclass
from datetime import datetime

import pandas as pd


@dataclass
class ScalingConfig:
    """Configuration for position scaling at profit targets.

    Attributes:
        scale_pct: Percentage of position to exit at profit target (0-100).
        profit_target_pct: Profit percentage to trigger scale-out.
    """

    scale_pct: float = 50.0
    profit_target_pct: float = 35.0


@dataclass
class ExitEvent:
    """Represents an exit from a position.

    Attributes:
        time: Datetime of the exit.
        price: Exit price.
        pct: Percentage of original position exited.
        reason: Reason for exit (profit_target, stop_hit, session_close).
    """

    time: datetime
    price: float
    pct: float
    reason: str


class ExitSimulator:
    """Simulates trade exits based on price action, stops, and targets.

    Supports both long and short trades:
    - Long trade: stop_level < entry_price, profit target above entry
    - Short trade: stop_level > entry_price, profit target below entry

    For each bar after entry:
    1. Check if stop is hit -> exit remaining position
    2. Check if profit target is reached -> scale out configured percentage
    3. Check if session closes -> exit remaining position
    """

    def __init__(
        self,
        entry_price: float,
        entry_time: datetime,
        stop_level: float,
        scaling_config: ScalingConfig,
        session_close_time: str = "16:00",
    ) -> None:
        """Initialize the exit simulator.

        Args:
            entry_price: Entry price for the trade.
            entry_time: Datetime when the trade was entered.
            stop_level: Stop loss price level.
            scaling_config: Configuration for profit target scaling.
            session_close_time: Time string (HH:MM) when session closes.
        """
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.stop_level = stop_level
        self.scaling_config = scaling_config
        self.session_close_time = session_close_time

        # Determine trade direction
        self.is_long = stop_level < entry_price

        # Calculate profit target price
        if self.is_long:
            self.profit_target = entry_price * (
                1 + scaling_config.profit_target_pct / 100
            )
        else:
            self.profit_target = entry_price * (
                1 - scaling_config.profit_target_pct / 100
            )

    def simulate(self, bars: pd.DataFrame) -> list[ExitEvent]:
        """Process bars and return exit events.

        Args:
            bars: DataFrame with columns: datetime, open, high, low, close

        Returns:
            List of ExitEvent objects representing exits from the position.
        """
        if bars.empty:
            return []

        exits: list[ExitEvent] = []
        remaining_pct = 100.0
        scaled_out = False

        # Parse session close time
        close_hour, close_minute = map(int, self.session_close_time.split(":"))

        for _, bar in bars.iterrows():
            bar_time: datetime = bar["datetime"].to_pydatetime()

            # Skip bars at or before entry time
            if bar_time <= self.entry_time:
                continue

            # No position left to exit
            if remaining_pct <= 0:
                break

            high = bar["high"]
            low = bar["low"]
            close = bar["close"]

            # Check session close time
            is_session_close = (
                bar_time.hour == close_hour and bar_time.minute == close_minute
            )

            if self.is_long:
                # Long trade logic
                # 1. Check stop hit (low <= stop)
                if low <= self.stop_level:
                    exits.append(
                        ExitEvent(
                            time=bar_time,
                            price=self.stop_level,
                            pct=remaining_pct,
                            reason="stop_hit",
                        )
                    )
                    remaining_pct = 0
                    break

                # 2. Check profit target (high >= target)
                if not scaled_out and high >= self.profit_target:
                    scale_amount = self.scaling_config.scale_pct
                    exits.append(
                        ExitEvent(
                            time=bar_time,
                            price=self.profit_target,
                            pct=scale_amount,
                            reason="profit_target",
                        )
                    )
                    remaining_pct -= scale_amount
                    scaled_out = True

                    # Check if stop also hit in same bar after scale-out
                    if remaining_pct > 0 and low <= self.stop_level:
                        exits.append(
                            ExitEvent(
                                time=bar_time,
                                price=self.stop_level,
                                pct=remaining_pct,
                                reason="stop_hit",
                            )
                        )
                        remaining_pct = 0
                        break

            else:
                # Short trade logic
                # 1. Check stop hit (high >= stop)
                if high >= self.stop_level:
                    exits.append(
                        ExitEvent(
                            time=bar_time,
                            price=self.stop_level,
                            pct=remaining_pct,
                            reason="stop_hit",
                        )
                    )
                    remaining_pct = 0
                    break

                # 2. Check profit target (low <= target)
                if not scaled_out and low <= self.profit_target:
                    scale_amount = self.scaling_config.scale_pct
                    exits.append(
                        ExitEvent(
                            time=bar_time,
                            price=self.profit_target,
                            pct=scale_amount,
                            reason="profit_target",
                        )
                    )
                    remaining_pct -= scale_amount
                    scaled_out = True

                    # Check if stop also hit in same bar after scale-out
                    if remaining_pct > 0 and high >= self.stop_level:
                        exits.append(
                            ExitEvent(
                                time=bar_time,
                                price=self.stop_level,
                                pct=remaining_pct,
                                reason="stop_hit",
                            )
                        )
                        remaining_pct = 0
                        break

            # 3. Check session close
            if is_session_close and remaining_pct > 0:
                exits.append(
                    ExitEvent(
                        time=bar_time,
                        price=close,
                        pct=remaining_pct,
                        reason="session_close",
                    )
                )
                remaining_pct = 0
                break

        return exits
