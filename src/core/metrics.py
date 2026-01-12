"""Metrics calculation for trading data analysis."""

import logging
import time
from typing import cast

import pandas as pd

from src.core.equity import EquityCalculator
from src.core.models import AdjustmentParams, TradingMetrics

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculate trading metrics from DataFrame.

    Supports both explicit Win/Loss column and derived classification
    based on Gain % column.
    """


    def _calculate_streaks(
        self,
        winners_mask: pd.Series,
    ) -> tuple[int | None, int | None]:
        """Calculate max consecutive wins and losses using run-length encoding.

        Args:
            winners_mask: Boolean Series where True = win, False = loss.

        Returns:
            Tuple of (max_consecutive_wins, max_consecutive_losses).
        """
        if len(winners_mask) == 0:
            return (None, None)

        # Create groups where consecutive same values are grouped together
        # When winners_mask changes value, start a new group
        groups = (winners_mask != winners_mask.shift()).cumsum()

        # Count the size of each group
        group_sizes = winners_mask.groupby(groups).agg(["first", "count"])

        # Find max streak for wins (first=True) and losses (first=False)
        wins = group_sizes[group_sizes["first"] == True]["count"]  # noqa: E712
        losses = group_sizes[group_sizes["first"] == False]["count"]  # noqa: E712

        max_wins = int(wins.max()) if len(wins) > 0 else 0
        max_losses = int(losses.max()) if len(losses) > 0 else 0

        return (max_wins, max_losses)

    def calculate(
        self,
        df: pd.DataFrame,
        gain_col: str,
        win_loss_col: str | None = None,
        derived: bool = False,
        breakeven_is_win: bool = False,
        adjustment_params: AdjustmentParams | None = None,
        mae_col: str | None = None,
        fractional_kelly_pct: float = 25.0,
        date_col: str | None = None,
        time_col: str | None = None,
        flat_stake: float | None = None,
        start_capital: float | None = None,
    ) -> tuple[TradingMetrics, pd.DataFrame | None, pd.DataFrame | None]:
        """Calculate all trading metrics including flat stake and Kelly metrics.

        Args:
            df: DataFrame with trade data.
            gain_col: Column name for gain percentage.
            win_loss_col: Optional column name for explicit win/loss.
            derived: If True, derive win/loss from gain_col.
            breakeven_is_win: When deriving, treat 0% as win.
            adjustment_params: Optional parameters for stop loss and efficiency adjustments.
            mae_col: Column name for MAE % (required if adjustment_params provided).
            fractional_kelly_pct: Fractional Kelly percentage (default 25%).
            date_col: Optional date column for chronological sorting (streak metrics).
            time_col: Optional time column for chronological sorting (streak metrics).
            flat_stake: Optional fixed stake amount for flat stake metrics.
            start_capital: Optional starting capital for Kelly metrics.

        Returns:
            Tuple of (TradingMetrics, flat_stake_equity_curve, kelly_equity_curve).
        """
        start = time.perf_counter()

        # Sort chronologically if date/time columns provided (required for accurate streaks)
        if date_col and time_col and date_col in df.columns and time_col in df.columns:
            df = df.sort_values([date_col, time_col]).reset_index(drop=True)
            logger.debug("Sorted DataFrame by %s, %s for streak calculation", date_col, time_col)

        if len(df) == 0:
            logger.debug("Empty DataFrame, returning empty metrics")
            return (TradingMetrics.empty(), None, None)

        # Apply adjustments if provided
        if adjustment_params is not None and mae_col is not None:
            gains = adjustment_params.calculate_adjusted_gains(df, gain_col, mae_col)
            logger.debug(
                "Applied adjustments: stop_loss=%.1f%%, efficiency=%.1f%%",
                adjustment_params.stop_loss,
                adjustment_params.efficiency,
            )
        else:
            gains = df[gain_col].astype(float)

        # Classify wins/losses based on adjusted gain sign
        # Note: Always use adjusted gains for classification per FR15c
        # This ensures avg_winner is always positive and avg_loser is always negative
        if breakeven_is_win:
            winners_mask = gains >= 0
            losers_mask = gains < 0
        else:
            winners_mask = gains > 0
            losers_mask = gains <= 0

        winner_gains = gains[winners_mask].tolist()
        loser_gains = gains[losers_mask].tolist()

        num_trades = len(df)
        winner_count = len(winner_gains)
        loser_count = len(loser_gains)

        # Win rate
        win_rate: float | None = None
        if num_trades > 0:
            win_rate = (winner_count / num_trades) * 100

        # Averages (multiply by 100 to convert decimal to percentage format)
        avg_winner: float | None = None
        avg_loser: float | None = None
        if winner_count > 0:
            avg_winner = (sum(winner_gains) / winner_count) * 100
        if loser_count > 0:
            avg_loser = (sum(loser_gains) / loser_count) * 100

        # R:R Ratio
        rr_ratio: float | None = None
        if avg_winner is not None and avg_loser is not None and avg_loser != 0:
            rr_ratio = abs(avg_winner / avg_loser)

        # Expected Value
        ev: float | None = None
        if win_rate is not None and avg_winner is not None and avg_loser is not None:
            ev = (win_rate / 100 * avg_winner) + ((1 - win_rate / 100) * avg_loser)

        # Kelly Criterion
        kelly: float | None = None
        if win_rate is not None and rr_ratio is not None and rr_ratio > 0:
            kelly = (win_rate / 100) - ((1 - win_rate / 100) / rr_ratio)
            kelly = kelly * 100  # Convert to percentage

        # Standard deviations (vectorized)
        winner_std: float | None = None
        loser_std: float | None = None
        if winner_count > 1:
            winner_std = float(pd.Series(winner_gains).std())
        if loser_count > 1:
            loser_std = float(pd.Series(loser_gains).std())

        # Extended metrics (Story 3.2 - metrics 8-12)
        # Edge = EV * num_trades
        edge: float | None = None
        if ev is not None:
            edge = ev * num_trades

        # Fractional Kelly = Kelly * (fractional_kelly_pct / 100)
        fractional_kelly: float | None = None
        if kelly is not None:
            fractional_kelly = kelly * (fractional_kelly_pct / 100)

        # Expected Growth (EG) = f * m - (f² * σ²) / 2
        # where f = Kelly fraction (decimal), m = EV, σ² = combined variance
        expected_growth: float | None = None
        if kelly is not None and ev is not None:
            all_gains = winner_gains + loser_gains
            if len(all_gains) >= 2:
                var_result = pd.Series(all_gains).var()
                if pd.notna(var_result):
                    combined_variance = cast(float, var_result)
                    kelly_decimal = kelly / 100  # Convert percentage to decimal
                    expected_growth = (kelly_decimal * ev) - (
                        (kelly_decimal**2) * combined_variance / 2
                    )

        # Median calculations (vectorized)
        median_winner: float | None = None
        median_loser: float | None = None
        if winner_count > 0:
            winner_median = pd.Series(winner_gains).median()
            median_winner = winner_median if pd.notna(winner_median) else None
        if loser_count > 0:
            loser_median = pd.Series(loser_gains).median()
            median_loser = loser_median if pd.notna(loser_median) else None

        # Distribution min/max (Story 3.2 - metrics 24-25 prep)
        winner_min: float | None = None
        winner_max: float | None = None
        loser_min: float | None = None
        loser_max: float | None = None
        if winner_count > 0:
            winner_min = min(winner_gains)
            winner_max = max(winner_gains)
        if loser_count > 0:
            loser_min = min(loser_gains)  # Most negative
            loser_max = max(loser_gains)  # Least negative

        # Streak & Loss Metrics (Story 3.3 - metrics 13-15)
        max_consecutive_wins, max_consecutive_losses = self._calculate_streaks(winners_mask)
        max_loss_pct: float | None = loser_min  # Worst single-trade loss (same as loser_min)
        logger.debug(
            "Calculated streaks: max_wins=%s, max_losses=%s, max_loss_pct=%s",
            max_consecutive_wins,
            max_consecutive_losses,
            max_loss_pct,
        )

        # Flat Stake Metrics (Story 3.4 - metrics 16-19)
        flat_stake_pnl: float | None = None
        flat_stake_max_dd: float | None = None
        flat_stake_max_dd_pct: float | None = None
        flat_stake_dd_duration: int | str | None = None
        equity_curve: pd.DataFrame | None = None

        if flat_stake is not None and num_trades > 0:
            equity_calculator = EquityCalculator()
            flat_stake_result = equity_calculator.calculate_flat_stake_metrics(
                df, gain_col, flat_stake
            )
            pnl_val = flat_stake_result["pnl"]
            if isinstance(pnl_val, (int, float)):
                flat_stake_pnl = float(pnl_val)
            max_dd_val = flat_stake_result["max_dd"]
            if isinstance(max_dd_val, (int, float)):
                flat_stake_max_dd = float(max_dd_val)
            max_dd_pct_val = flat_stake_result["max_dd_pct"]
            if isinstance(max_dd_pct_val, (int, float)):
                flat_stake_max_dd_pct = float(max_dd_pct_val)
            dd_duration_val = flat_stake_result["dd_duration"]
            if isinstance(dd_duration_val, (int, str)):
                flat_stake_dd_duration = dd_duration_val
            curve_val = flat_stake_result["equity_curve"]
            if isinstance(curve_val, pd.DataFrame):
                equity_curve = curve_val
            logger.debug(
                "Calculated flat stake metrics: pnl=%.2f, max_dd=%.2f, dd_pct=%s, duration=%s",
                flat_stake_pnl or 0,
                flat_stake_max_dd or 0,
                f"{flat_stake_max_dd_pct:.2f}%" if flat_stake_max_dd_pct else "N/A",
                flat_stake_dd_duration,
            )

        # Kelly Metrics (Story 3.5 - metrics 20-23)
        kelly_pnl: float | None = None
        kelly_max_dd: float | None = None
        kelly_max_dd_pct: float | None = None
        kelly_dd_duration: int | str | None = None
        kelly_equity_curve: pd.DataFrame | None = None

        if start_capital is not None and num_trades > 0:
            equity_calculator = EquityCalculator()
            kelly_result = equity_calculator.calculate_kelly_metrics(
                df, gain_col, start_capital, fractional_kelly_pct, kelly
            )
            pnl_val = kelly_result["pnl"]
            if isinstance(pnl_val, (int, float)):
                kelly_pnl = float(pnl_val)
            max_dd_val = kelly_result["max_dd"]
            if isinstance(max_dd_val, (int, float)):
                kelly_max_dd = float(max_dd_val)
            max_dd_pct_val = kelly_result["max_dd_pct"]
            if isinstance(max_dd_pct_val, (int, float)):
                kelly_max_dd_pct = float(max_dd_pct_val)
            dd_duration_val = kelly_result["dd_duration"]
            if isinstance(dd_duration_val, (int, str)):
                kelly_dd_duration = dd_duration_val
            curve_val = kelly_result["equity_curve"]
            if isinstance(curve_val, pd.DataFrame):
                kelly_equity_curve = curve_val
            logger.debug(
                "Calculated Kelly metrics: pnl=%.2f, max_dd=%.2f, dd_pct=%s, duration=%s",
                kelly_pnl or 0,
                kelly_max_dd or 0,
                f"{kelly_max_dd_pct:.2f}%" if kelly_max_dd_pct else "N/A",
                kelly_dd_duration,
            )

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug("Calculated metrics in %.2fms for %d trades", elapsed_ms, num_trades)
        logger.info(
            "Calculated baseline metrics: %d trades, %.1f%% win rate",
            num_trades,
            win_rate or 0,
        )

        return (
            TradingMetrics(
                num_trades=num_trades,
                win_rate=win_rate,
                avg_winner=avg_winner,
                avg_loser=avg_loser,
                rr_ratio=rr_ratio,
                ev=ev,
                kelly=kelly,
                winner_count=winner_count,
                loser_count=loser_count,
                winner_std=winner_std,
                loser_std=loser_std,
                winner_gains=winner_gains,
                loser_gains=loser_gains,
                edge=edge,
                fractional_kelly=fractional_kelly,
                expected_growth=expected_growth,
                median_winner=median_winner,
                median_loser=median_loser,
                winner_min=winner_min,
                winner_max=winner_max,
                loser_min=loser_min,
                loser_max=loser_max,
                max_consecutive_wins=max_consecutive_wins,
                max_consecutive_losses=max_consecutive_losses,
                max_loss_pct=max_loss_pct,
                flat_stake_pnl=flat_stake_pnl,
                flat_stake_max_dd=flat_stake_max_dd,
                flat_stake_max_dd_pct=flat_stake_max_dd_pct,
                flat_stake_dd_duration=flat_stake_dd_duration,
                kelly_pnl=kelly_pnl,
                kelly_max_dd=kelly_max_dd,
                kelly_max_dd_pct=kelly_max_dd_pct,
                kelly_dd_duration=kelly_dd_duration,
            ),
            equity_curve,
            kelly_equity_curve,
        )


def calculate_suggested_bins(data: list[float], method: str = "freedman_diaconis") -> int:
    """Calculate suggested histogram bin count using Freedman-Diaconis rule.

    Args:
        data: List of values for the histogram.
        method: Algorithm to use (only "freedman_diaconis" supported).

    Returns:
        Suggested number of bins (minimum 5, maximum 50).
        Returns 10 for edge cases: empty list, single value, or identical values.

    Freedman-Diaconis rule: bin_width = 2 * IQR * n^(-1/3)
    """
    import numpy as np

    # Handle edge cases: empty list or insufficient data
    if not data or len(data) < 2:
        return 10  # Default for small/empty datasets

    q75, q25 = np.percentile(data, [75, 25])
    iqr = q75 - q25

    if iqr == 0:
        return 10  # Default when all values are the same

    n = len(data)
    bin_width = 2 * iqr * (n ** (-1 / 3))
    data_range = max(data) - min(data)

    suggested = max(5, min(50, int(np.ceil(data_range / bin_width))))
    return suggested
