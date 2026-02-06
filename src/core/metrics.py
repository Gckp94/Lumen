"""Metrics calculation for trading data analysis."""

import logging
import time
from typing import cast

import pandas as pd

from src.core.equity import EquityCalculator
from src.core.models import AdjustmentParams, ColumnMapping, StopScenario, TradingMetrics

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
            date_col: Optional date column for chronological sorting and equity curve dates.
            time_col: Optional time column for chronological sorting (streak metrics).
            flat_stake: Optional fixed stake amount for flat stake metrics.
            start_capital: Optional starting capital for Kelly metrics.

        Returns:
            Tuple of (TradingMetrics, flat_stake_equity_curve, kelly_equity_curve).
        """
        start = time.perf_counter()

        # Sort chronologically if date/time columns provided (required for accurate streaks
        # and correct equity curve display in DATE mode)
        # Convert to datetime first to ensure correct chronological sorting
        # (string dates like DD/MM/YYYY don't sort correctly as strings)
        if date_col and date_col in df.columns:
            df = df.copy()
            df["_sort_date"] = pd.to_datetime(df[date_col], dayfirst=True, errors="coerce")
            if time_col and time_col in df.columns:
                df = df.sort_values(["_sort_date", time_col]).reset_index(drop=True)
                logger.debug("Sorted DataFrame by %s, %s", date_col, time_col)
            else:
                df = df.sort_values(["_sort_date"]).reset_index(drop=True)
                logger.debug("Sorted DataFrame by %s", date_col)
            df = df.drop(columns=["_sort_date"])

        if len(df) == 0:
            logger.debug("Empty DataFrame, returning empty metrics")
            return (TradingMetrics.empty(), None, None)

        # Apply adjustments if provided
        # Track whether adjustments were applied (affects gains format)
        adjustments_applied = False
        if adjustment_params is not None and mae_col is not None:
            gains = adjustment_params.calculate_adjusted_gains(df, gain_col, mae_col)
            adjustments_applied = True
            logger.info(
                "Applied adjustments: stop_loss=%.1f%%, efficiency=%.1f%% - "
                "DIAGNOSTIC: adjusted gains min=%.6f, max=%.6f, mean=%.6f, "
                "sample first 5: %s",
                adjustment_params.stop_loss,
                adjustment_params.efficiency,
                gains.min(),
                gains.max(),
                gains.mean(),
                gains.head(5).tolist(),
            )
        else:
            gains = df[gain_col].astype(float)

        # Diagnostic logging for data investigation
        logger.info(
            "DIAGNOSTIC: Raw gains from '%s' - min=%.6f, max=%.6f, mean=%.6f, "
            "sample first 5: %s",
            gain_col,
            gains.min(),
            gains.max(),
            gains.mean(),
            gains.head(5).tolist(),
        )
        if mae_col and mae_col in df.columns:
            mae_values = df[mae_col].astype(float)
            logger.info(
                "DIAGNOSTIC: MAE from '%s' - min=%.6f, max=%.6f, mean=%.6f, "
                "sample first 5: %s",
                mae_col,
                mae_values.min(),
                mae_values.max(),
                mae_values.mean(),
                mae_values.head(5).tolist(),
            )

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
        # Expected input: 0.05 means 5% gain, -0.03 means 3% loss
        avg_winner: float | None = None
        avg_loser: float | None = None
        if winner_count > 0:
            raw_avg_winner = sum(winner_gains) / winner_count
            # Heuristic: if raw average magnitude > 1, data might already be in percentage format
            # (e.g., 5.0 for 5% instead of 0.05 for 5%)
            if abs(raw_avg_winner) > 1:
                logger.warning(
                    "Gain values appear large (avg_winner=%.4f). "
                    "Expected decimal format (0.05 for 5%%). "
                    "Data may already be in percentage format.",
                    raw_avg_winner,
                )
            avg_winner = raw_avg_winner * 100
        if loser_count > 0:
            raw_avg_loser = sum(loser_gains) / loser_count
            # Same heuristic for losers
            if abs(raw_avg_loser) > 1:
                logger.warning(
                    "Gain values appear large (avg_loser=%.4f). "
                    "Expected decimal format (-0.03 for -3%%). "
                    "Data may already be in percentage format.",
                    raw_avg_loser,
                )
            avg_loser = raw_avg_loser * 100

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

        # Stop-Adjusted Kelly
        # Position size = Kelly Stake % / Stop Loss %
        # Tighter stops allow larger positions for same risk
        stop_adjusted_kelly: float | None = None
        if kelly is not None and adjustment_params is not None and adjustment_params.stop_loss > 0:
            stop_adjusted_kelly = (kelly / adjustment_params.stop_loss) * 100

        # Standard deviations (vectorized, multiply by 100 for percentage format)
        winner_std: float | None = None
        loser_std: float | None = None
        if winner_count > 1:
            winner_std = float(pd.Series(winner_gains).std()) * 100
        if loser_count > 1:
            loser_std = float(pd.Series(loser_gains).std()) * 100

        # Extended metrics (Story 3.2 - metrics 8-12)
        # Edge % = ((R:R + 1) × Win Rate) - 1, multiply by 100 for percentage format
        edge: float | None = None
        if rr_ratio is not None and win_rate is not None:
            edge = (((rr_ratio + 1) * (win_rate / 100)) - 1) * 100

        # Fractional Kelly = stop_adjusted_kelly * fraction (if available)
        # Falls back to raw kelly if no stop adjustment
        fractional_kelly: float | None = None
        if stop_adjusted_kelly is not None:
            fractional_kelly = stop_adjusted_kelly * (fractional_kelly_pct / 100)
        elif kelly is not None:
            fractional_kelly = kelly * (fractional_kelly_pct / 100)

        # Expected Growth calculations
        # EG = f * μ - (f² * σ²) / 2
        # where f = bet fraction, μ = EV, σ² = variance
        eg_full_kelly: float | None = None
        eg_frac_kelly: float | None = None
        eg_flat_stake: float | None = None

        all_gains = winner_gains + loser_gains
        combined_variance: float | None = None
        if len(all_gains) >= 2:
            var_result = pd.Series(all_gains).var()
            if pd.notna(var_result):
                # Variance is in decimal² format (e.g., 0.01 for 10% std dev)
                # EV is in percentage format, so multiply variance by 100
                # to make units consistent in the EG formula
                combined_variance = cast(float, var_result) * 100

        if combined_variance is not None and ev is not None:
            # EG Full Kelly - only when Kelly > 0
            if kelly is not None and kelly > 0:
                kelly_decimal = kelly / 100
                eg_full_kelly = (kelly_decimal * ev) - (
                    (kelly_decimal**2) * combined_variance / 2
                )

            # EG Fractional Kelly - only when fractional Kelly > 0
            if fractional_kelly is not None and fractional_kelly > 0:
                frac_kelly_decimal = fractional_kelly / 100
                eg_frac_kelly = (frac_kelly_decimal * ev) - (
                    (frac_kelly_decimal**2) * combined_variance / 2
                )

            # EG Flat Stake - when flat_stake and start_capital provided
            if (
                flat_stake is not None
                and start_capital is not None
                and flat_stake > 0
                and start_capital > 0
            ):
                flat_fraction = flat_stake / start_capital
                eg_flat_stake = (flat_fraction * ev) - (
                    (flat_fraction**2) * combined_variance / 2
                )

        # Median calculations (vectorized, multiply by 100 for percentage format)
        median_winner: float | None = None
        median_loser: float | None = None
        if winner_count > 0:
            winner_median = pd.Series(winner_gains).median()
            median_winner = float(winner_median) * 100 if pd.notna(winner_median) else None
        if loser_count > 0:
            loser_median = pd.Series(loser_gains).median()
            median_loser = float(loser_median) * 100 if pd.notna(loser_median) else None

        # Distribution min/max (Story 3.2 - metrics 24-25, multiply by 100 for pct format)
        winner_min: float | None = None
        winner_max: float | None = None
        loser_min: float | None = None
        loser_max: float | None = None
        if winner_count > 0:
            winner_min = min(winner_gains) * 100
            winner_max = max(winner_gains) * 100
        if loser_count > 0:
            loser_min = min(loser_gains) * 100  # Most negative
            loser_max = max(loser_gains) * 100  # Least negative

        # Streak & Loss Metrics (Story 3.3 - metrics 13-15)
        max_consecutive_wins, max_consecutive_losses = self._calculate_streaks(winners_mask)

        # Calculate max_loss_pct as percentage of trades hitting stop level
        max_loss_pct: float | None = None
        if adjustment_params is not None and mae_col is not None and mae_col in df.columns:
            mae_values = df[mae_col].astype(float)
            stop_hit_count = (mae_values > adjustment_params.stop_loss).sum()
            max_loss_pct = (stop_hit_count / num_trades) * 100 if num_trades > 0 else 0.0

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
            # Use adjusted gains for equity calculation (same as metrics)
            # IMPORTANT: If adjustments were applied, gains are in decimal format (0.20 = 20%)
            # but equity calculator expects percentage format (20 = 20%)
            # So we multiply by 100 to convert decimal -> percentage ONLY when adjustments applied
            equity_df = df.copy()
            if adjustments_applied:
                equity_df["_adjusted_gains_for_equity"] = gains * 100
            else:
                equity_df["_adjusted_gains_for_equity"] = gains
            flat_stake_result = equity_calculator.calculate_flat_stake_metrics(
                equity_df,
                gain_col="_adjusted_gains_for_equity",
                stake=flat_stake,
                start_capital=start_capital if start_capital else 0.0,
                date_col=date_col,
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
            # Use adjusted gains for Kelly calculation (same as metrics)
            # IMPORTANT: If adjustments were applied, gains are in decimal format (0.20 = 20%)
            # but equity calculator expects percentage format (20 = 20%)
            # So we multiply by 100 to convert decimal -> percentage ONLY when adjustments applied
            kelly_equity_df = df.copy()
            if adjustments_applied:
                kelly_equity_df["_adjusted_gains_for_equity"] = gains * 100
            else:
                kelly_equity_df["_adjusted_gains_for_equity"] = gains
            equity_calculator = EquityCalculator()
            # Use stop_adjusted_kelly for position sizing if available, otherwise raw kelly
            kelly_for_equity = stop_adjusted_kelly if stop_adjusted_kelly is not None else kelly
            kelly_result = equity_calculator.calculate_kelly_metrics(
                kelly_equity_df,
                "_adjusted_gains_for_equity",
                start_capital,
                fractional_kelly_pct,
                kelly_for_equity,
                date_col=date_col,
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
                stop_adjusted_kelly=stop_adjusted_kelly,
                winner_count=winner_count,
                loser_count=loser_count,
                winner_std=winner_std,
                loser_std=loser_std,
                winner_gains=winner_gains,
                loser_gains=loser_gains,
                edge=edge,
                fractional_kelly=fractional_kelly,
                eg_full_kelly=eg_full_kelly,
                eg_frac_kelly=eg_frac_kelly,
                eg_flat_stake=eg_flat_stake,
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

    def calculate_stop_scenarios(
        self,
        df: pd.DataFrame,
        mapping: ColumnMapping,
        adjustment_params: AdjustmentParams,
        stop_levels: list[int] | None = None,
        start_capital: float | None = None,
        fractional_kelly_pct: float = 25.0,
    ) -> list[StopScenario]:
        """Calculate metrics at each stop loss level.

        Reuses the same core metric formulas as calculate() to ensure consistency.

        Args:
            df: DataFrame with trade data.
            mapping: Column mapping configuration.
            adjustment_params: Current adjustment parameters.
            stop_levels: List of stop percentages to simulate. Defaults to [10,20,30,40,50,60,70,80,90,100].
            start_capital: Starting capital for Kelly calculations.
            fractional_kelly_pct: Fractional Kelly percentage.

        Returns:
            List of StopScenario dataclasses, one per stop level.
        """
        from src.core.statistics import STOP_LOSS_LEVELS, _calculate_stop_level_row

        if stop_levels is None:
            stop_levels = list(STOP_LOSS_LEVELS)

        scenarios = []
        gain_col = mapping.gain_pct
        mae_col = mapping.mae_pct
        date_col = mapping.date if hasattr(mapping, 'date') else None

        # Compute adjusted gains using same method as calculate()
        if mae_col and mae_col in df.columns:
            adjusted_gains = adjustment_params.calculate_adjusted_gains(df, gain_col, mae_col)
        else:
            adjusted_gains = df[gain_col].astype(float) if len(df) > 0 else pd.Series(dtype=float)

        for stop_level in stop_levels:
            # Use existing _calculate_stop_level_row from statistics.py
            # This ensures formula consistency
            row = _calculate_stop_level_row(
                df=df,
                adjusted_gains=adjusted_gains,
                mae_col=mae_col,
                stop_level=stop_level,
                efficiency=adjustment_params.efficiency,
                start_capital=start_capital,
                fractional_kelly_pct=fractional_kelly_pct,
                date_col=date_col,
            )

            scenario = StopScenario(
                stop_pct=stop_level,
                num_trades=len(df),
                win_pct=row.get("Win %", 0.0),
                ev_pct=row.get("EV %"),
                avg_gain_pct=row.get("Avg Gain %"),
                median_gain_pct=row.get("Median Gain %"),
                edge_pct=row.get("Edge %"),
                kelly_pct=row.get("Full Kelly (Stop Adj)"),
                stop_adjusted_kelly_pct=row.get("Full Kelly (Stop Adj)"),
                max_loss_pct=row.get("Max Loss %", 0.0),
                max_dd_pct=row.get("Max DD %"),
                kelly_pnl=row.get("Total Kelly $"),
            )
            scenarios.append(scenario)

        return scenarios


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
