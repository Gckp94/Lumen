"""Monte Carlo simulation engine for trading strategy analysis."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Callable, Literal

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class PositionSizingMode(str, Enum):
    """Position sizing mode for Monte Carlo simulation."""

    FLAT_STAKE = "flat_stake"
    COMPOUNDED_KELLY = "compounded_kelly"
    COMPOUNDED_CUSTOM = "compounded_custom"


@dataclass
class MonteCarloConfig:
    """Configuration for Monte Carlo simulation.

    Attributes:
        num_simulations: Number of simulation runs (100-50,000).
        initial_capital: Starting capital for equity calculations.
        ruin_threshold_pct: Percentage loss that defines ruin (e.g., 50 = lose half).
        var_confidence_pct: Confidence level for VaR calculation (e.g., 5 = 5th percentile).
        simulation_type: Either "resample" (with replacement) or "reshuffle" (permutation).
        position_sizing_mode: Either "flat_stake", "compounded_kelly", or "compounded_custom".
        flat_stake: Fixed dollar amount per trade (used when mode is flat_stake).
        fractional_kelly_pct: Fractional Kelly percentage (used when mode is compounded_kelly).
        custom_position_pct: Custom position size percentage (used when mode is compounded_custom).
    """

    num_simulations: int = 5000
    initial_capital: float = 100000.0
    ruin_threshold_pct: float = 50.0
    var_confidence_pct: float = 5.0
    simulation_type: Literal["resample", "reshuffle"] = "resample"
    position_sizing_mode: PositionSizingMode = PositionSizingMode.COMPOUNDED_KELLY
    flat_stake: float = 10000.0
    fractional_kelly_pct: float = 25.0
    custom_position_pct: float = 10.0

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if not 100 <= self.num_simulations <= 50000:
            raise ValueError("num_simulations must be between 100 and 50,000")
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        if not 0 < self.ruin_threshold_pct < 100:
            raise ValueError("ruin_threshold_pct must be between 0 and 100")
        if not 0 < self.var_confidence_pct < 100:
            raise ValueError("var_confidence_pct must be between 0 and 100")
        if self.simulation_type not in ("resample", "reshuffle"):
            raise ValueError("simulation_type must be 'resample' or 'reshuffle'")
        if self.flat_stake <= 0:
            raise ValueError("flat_stake must be positive")
        if not 0 < self.fractional_kelly_pct <= 100:
            raise ValueError("fractional_kelly_pct must be between 0 and 100")
        if not 0 < self.custom_position_pct <= 100:
            raise ValueError("custom_position_pct must be between 0 and 100")


@dataclass
class MonteCarloResults:
    """Results from Monte Carlo simulation.

    Contains all calculated metrics organized by category, plus raw distribution
    data for charting purposes.
    """

    # Configuration used
    config: MonteCarloConfig
    num_trades: int

    # Category 1: Maximum Drawdown Distribution
    median_max_dd: float
    p95_max_dd: float
    p99_max_dd: float
    max_dd_distribution: NDArray[np.float64]

    # Category 2: Final Equity Distribution
    mean_final_equity: float
    std_final_equity: float
    p5_final_equity: float
    p95_final_equity: float
    probability_of_profit: float
    final_equity_distribution: NDArray[np.float64]

    # Category 3: CAGR Distribution
    mean_cagr: float
    median_cagr: float
    cagr_distribution: NDArray[np.float64]

    # Category 4: Risk-Adjusted Metrics
    mean_sharpe: float
    mean_sortino: float
    mean_calmar: float
    sharpe_distribution: NDArray[np.float64]
    sortino_distribution: NDArray[np.float64]
    calmar_distribution: NDArray[np.float64]

    # Category 5: Risk of Ruin
    risk_of_ruin: float

    # Category 6: Consecutive Wins/Losses
    mean_max_win_streak: float
    max_max_win_streak: int
    mean_max_loss_streak: float
    max_max_loss_streak: int
    win_streak_distribution: NDArray[np.int64]
    loss_streak_distribution: NDArray[np.int64]

    # Category 7: Recovery Factor
    mean_recovery_factor: float
    recovery_factor_distribution: NDArray[np.float64]

    # Category 8: Profit Factor
    mean_profit_factor: float
    profit_factor_distribution: NDArray[np.float64]

    # Category 9: Drawdown Duration
    mean_avg_dd_duration: float
    mean_max_dd_duration: float
    max_dd_duration_distribution: NDArray[np.int64]

    # Category 10: VaR and CVaR
    var: float
    cvar: float

    # Raw data for charts (memory efficient)
    # Shape: (num_trades, 5) for 5th, 25th, 50th, 75th, 95th percentiles
    equity_percentiles: NDArray[np.float64]


class MonteCarloEngine:
    """Engine for running Monte Carlo simulations on trade data.

    Supports both resampling (random sampling with replacement) and
    reshuffling (random permutation) methods.

    Example:
        >>> config = MonteCarloConfig(num_simulations=1000)
        >>> engine = MonteCarloEngine(config)
        >>> results = engine.run(gains_array)
    """

    def __init__(self, config: MonteCarloConfig) -> None:
        """Initialize the Monte Carlo engine.

        Args:
            config: Configuration for the simulation.
        """
        self.config = config
        self._cancelled = False

    def cancel(self) -> None:
        """Request cancellation of the running simulation."""
        self._cancelled = True

    def _resample(self, gains: NDArray[np.float64], num_trades: int) -> NDArray[np.float64]:
        """Resample gains with replacement.

        Args:
            gains: Array of trade returns (as decimals, e.g., 0.05 for 5% gain).
            num_trades: Number of trades to sample.

        Returns:
            Resampled gains array.
        """
        return np.random.choice(gains, size=num_trades, replace=True)

    def _reshuffle(self, gains: NDArray[np.float64]) -> NDArray[np.float64]:
        """Reshuffle gains using Fisher-Yates permutation.

        Args:
            gains: Array of trade returns.

        Returns:
            Permuted gains array (all original values, different order).
        """
        return np.random.permutation(gains)

    def _simulate_equity_curve(
        self, sampled_gains: NDArray[np.float64], initial_capital: float
    ) -> NDArray[np.float64]:
        """Calculate cumulative equity curve from sampled gains.

        Args:
            sampled_gains: Array of trade returns (decimal format, e.g., 0.05 for 5%).
            initial_capital: Starting capital.

        Returns:
            Equity curve array where each element is the equity after that trade.
        """
        if self.config.position_sizing_mode == PositionSizingMode.FLAT_STAKE:
            # Flat stake: fixed dollar amount per trade (additive)
            # PnL per trade = flat_stake * gain_decimal
            pnl_per_trade = self.config.flat_stake * sampled_gains
            return initial_capital + np.cumsum(pnl_per_trade)
        elif self.config.position_sizing_mode == PositionSizingMode.COMPOUNDED_CUSTOM:
            # Compounded Custom: position size = custom_position_pct% of current equity
            # Each trade: equity *= (1 + custom_pct * gain)
            custom_fraction = self.config.custom_position_pct / 100.0
            multipliers = 1 + (custom_fraction * sampled_gains)
            return initial_capital * np.cumprod(multipliers)
        else:
            # Compounded Kelly: position size = fractional_kelly_pct% of current equity
            # Each trade: equity *= (1 + fractional_kelly * gain)
            fractional_kelly = self.config.fractional_kelly_pct / 100.0
            multipliers = 1 + (fractional_kelly * sampled_gains)
            return initial_capital * np.cumprod(multipliers)

    def _calculate_max_drawdown(self, equity_curve: NDArray[np.float64]) -> float:
        """Calculate maximum drawdown from equity curve.

        Args:
            equity_curve: Array of equity values over time.

        Returns:
            Maximum drawdown as a decimal (e.g., 0.25 for 25% drawdown).
        """
        running_max = np.maximum.accumulate(equity_curve)
        drawdown = (running_max - equity_curve) / running_max
        return float(np.max(drawdown))

    def _calculate_max_streak(self, gains: NDArray[np.float64], win: bool) -> int:
        """Calculate maximum consecutive winning or losing streak.

        Uses run-length encoding pattern for efficiency.

        Args:
            gains: Array of trade returns.
            win: If True, count winning streaks; if False, count losing streaks.

        Returns:
            Length of the longest streak.
        """
        if len(gains) == 0:
            return 0

        is_win = gains > 0 if win else gains < 0
        if not np.any(is_win):
            return 0

        # Run-length encoding
        changes = np.diff(is_win.astype(int))
        run_starts = np.where(changes != 0)[0] + 1
        run_starts = np.concatenate([[0], run_starts, [len(is_win)]])

        max_streak = 0
        for i in range(len(run_starts) - 1):
            start, end = run_starts[i], run_starts[i + 1]
            if is_win[start]:
                max_streak = max(max_streak, end - start)

        return max_streak

    def _calculate_drawdown_duration(
        self, equity_curve: NDArray[np.float64]
    ) -> tuple[float, int]:
        """Calculate average and maximum drawdown duration.

        Duration is measured in number of trades spent below the running maximum.

        Args:
            equity_curve: Array of equity values.

        Returns:
            Tuple of (average_duration, max_duration) in trades.
        """
        running_max = np.maximum.accumulate(equity_curve)
        in_drawdown = equity_curve < running_max

        if not np.any(in_drawdown):
            return 0.0, 0

        # Find drawdown periods using run-length encoding
        changes = np.diff(in_drawdown.astype(int))
        starts = np.where(changes == 1)[0] + 1
        ends = np.where(changes == -1)[0] + 1

        # Handle edge cases
        if in_drawdown[0]:
            starts = np.concatenate([[0], starts])
        if in_drawdown[-1]:
            ends = np.concatenate([ends, [len(in_drawdown)]])

        if len(starts) == 0 or len(ends) == 0:
            return 0.0, 0

        durations = ends[: len(starts)] - starts[: len(ends)]
        return float(np.mean(durations)), int(np.max(durations))

    def run(
        self,
        gains: NDArray[np.float64],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> MonteCarloResults:
        """Run Monte Carlo simulation.

        Args:
            gains: Array of trade returns as decimals (e.g., 0.05 for 5% gain).
            progress_callback: Optional callback for progress updates (completed, total).

        Returns:
            MonteCarloResults containing all calculated metrics.

        Raises:
            ValueError: If gains array is empty or has fewer than 10 trades.
        """
        import time

        start_time = time.perf_counter()
        self._cancelled = False

        # Validate input
        if len(gains) == 0:
            raise ValueError("Gains array cannot be empty")
        if len(gains) < 10:
            raise ValueError("Insufficient data: need at least 10 trades for Monte Carlo")

        gains = np.asarray(gains, dtype=np.float64)
        n_sims = self.config.num_simulations
        n_trades = len(gains)
        initial_capital = self.config.initial_capital

        # Pre-allocate result arrays
        max_dd_arr = np.zeros(n_sims, dtype=np.float64)
        final_equity_arr = np.zeros(n_sims, dtype=np.float64)
        min_equity_arr = np.zeros(n_sims, dtype=np.float64)
        cagr_arr = np.zeros(n_sims, dtype=np.float64)
        sharpe_arr = np.zeros(n_sims, dtype=np.float64)
        sortino_arr = np.zeros(n_sims, dtype=np.float64)
        calmar_arr = np.zeros(n_sims, dtype=np.float64)
        win_streak_arr = np.zeros(n_sims, dtype=np.int64)
        loss_streak_arr = np.zeros(n_sims, dtype=np.int64)
        recovery_factor_arr = np.zeros(n_sims, dtype=np.float64)
        profit_factor_arr = np.zeros(n_sims, dtype=np.float64)
        avg_dd_duration_arr = np.zeros(n_sims, dtype=np.float64)
        max_dd_duration_arr = np.zeros(n_sims, dtype=np.int64)

        # For equity percentiles chart (collect all equity curves)
        all_equity_curves = np.zeros((n_sims, n_trades), dtype=np.float64)

        # Calculate years for CAGR (each trade = 1 trading day, 252 days/year)
        years = n_trades / 252.0

        # Run simulations
        for i in range(n_sims):
            if self._cancelled:
                logger.info("Monte Carlo simulation cancelled at iteration %d", i)
                break

            # Sample trades
            if self.config.simulation_type == "resample":
                sampled = self._resample(gains, n_trades)
            else:
                sampled = self._reshuffle(gains)

            # Calculate equity curve
            equity_curve = self._simulate_equity_curve(sampled, initial_capital)
            all_equity_curves[i] = equity_curve

            # Category 1: Max Drawdown
            max_dd_arr[i] = self._calculate_max_drawdown(equity_curve)

            # Category 2: Final Equity
            final_equity = equity_curve[-1]
            final_equity_arr[i] = final_equity
            min_equity_arr[i] = np.min(equity_curve)

            # Category 3: CAGR
            if years > 0:
                cagr_arr[i] = (final_equity / initial_capital) ** (1 / years) - 1
            else:
                cagr_arr[i] = 0.0

            # Category 4: Risk-Adjusted Metrics
            mean_return = np.mean(sampled)
            std_return = np.std(sampled)
            downside_returns = sampled[sampled < 0]
            downside_std = np.std(downside_returns) if len(downside_returns) > 0 else np.nan

            # Sharpe Ratio (annualized)
            if std_return > 0:
                sharpe_arr[i] = mean_return / std_return * np.sqrt(252)
            else:
                sharpe_arr[i] = 0.0

            # Sortino Ratio (annualized)
            if downside_std > 0 and not np.isnan(downside_std):
                sortino_arr[i] = mean_return / downside_std * np.sqrt(252)
            else:
                sortino_arr[i] = 0.0 if mean_return <= 0 else np.inf

            # Calmar Ratio
            if max_dd_arr[i] > 0:
                calmar_arr[i] = cagr_arr[i] / max_dd_arr[i]
            else:
                calmar_arr[i] = np.inf if cagr_arr[i] > 0 else 0.0

            # Category 6: Streaks
            win_streak_arr[i] = self._calculate_max_streak(sampled, win=True)
            loss_streak_arr[i] = self._calculate_max_streak(sampled, win=False)

            # Category 7: Recovery Factor
            net_profit = final_equity - initial_capital
            max_dd_value = max_dd_arr[i] * initial_capital
            if max_dd_value > 0:
                recovery_factor_arr[i] = net_profit / max_dd_value
            else:
                recovery_factor_arr[i] = np.inf if net_profit > 0 else 0.0

            # Category 8: Profit Factor
            winners = sampled[sampled > 0]
            losers = sampled[sampled < 0]
            sum_winners = np.sum(winners) if len(winners) > 0 else 0.0
            sum_losers = np.abs(np.sum(losers)) if len(losers) > 0 else 0.0
            if sum_losers > 0:
                profit_factor_arr[i] = sum_winners / sum_losers
            else:
                profit_factor_arr[i] = np.inf if sum_winners > 0 else 0.0

            # Category 9: Drawdown Duration
            avg_dd_dur, max_dd_dur = self._calculate_drawdown_duration(equity_curve)
            avg_dd_duration_arr[i] = avg_dd_dur
            max_dd_duration_arr[i] = max_dd_dur

            # Progress callback every 100 simulations
            if progress_callback and (i + 1) % 100 == 0:
                progress_callback(i + 1, n_sims)

        # Final progress callback
        if progress_callback and not self._cancelled:
            progress_callback(n_sims, n_sims)

        # Category 5: Risk of Ruin
        ruin_threshold = initial_capital * (1 - self.config.ruin_threshold_pct / 100)
        risk_of_ruin = float(np.mean(min_equity_arr < ruin_threshold))

        # Category 10: VaR and CVaR
        var_pct = self.config.var_confidence_pct
        all_returns = gains  # Use original gains for VaR
        var = float(np.percentile(all_returns, var_pct))
        cvar_mask = all_returns <= var
        cvar = float(np.mean(all_returns[cvar_mask])) if np.any(cvar_mask) else var

        # Calculate equity percentiles for charting
        equity_percentiles = np.percentile(
            all_equity_curves, [5, 25, 50, 75, 95], axis=0
        ).T  # Shape: (n_trades, 5)

        elapsed = time.perf_counter() - start_time
        logger.info("Monte Carlo completed in %.2fs (%d simulations)", elapsed, n_sims)

        return MonteCarloResults(
            config=self.config,
            num_trades=n_trades,
            # Category 1
            median_max_dd=float(np.percentile(max_dd_arr, 50)),
            p95_max_dd=float(np.percentile(max_dd_arr, 95)),
            p99_max_dd=float(np.percentile(max_dd_arr, 99)),
            max_dd_distribution=max_dd_arr,
            # Category 2
            mean_final_equity=float(np.mean(final_equity_arr)),
            std_final_equity=float(np.std(final_equity_arr)),
            p5_final_equity=float(np.percentile(final_equity_arr, 5)),
            p95_final_equity=float(np.percentile(final_equity_arr, 95)),
            probability_of_profit=float(np.mean(final_equity_arr > initial_capital)),
            final_equity_distribution=final_equity_arr,
            # Category 3
            mean_cagr=float(np.mean(cagr_arr)),
            median_cagr=float(np.median(cagr_arr)),
            cagr_distribution=cagr_arr,
            # Category 4
            mean_sharpe=float(np.mean(sharpe_arr[np.isfinite(sharpe_arr)])),
            mean_sortino=float(np.mean(sortino_arr[np.isfinite(sortino_arr)])),
            mean_calmar=float(np.mean(calmar_arr[np.isfinite(calmar_arr)])),
            sharpe_distribution=sharpe_arr,
            sortino_distribution=sortino_arr,
            calmar_distribution=calmar_arr,
            # Category 5
            risk_of_ruin=risk_of_ruin,
            # Category 6
            mean_max_win_streak=float(np.mean(win_streak_arr)),
            max_max_win_streak=int(np.max(win_streak_arr)),
            mean_max_loss_streak=float(np.mean(loss_streak_arr)),
            max_max_loss_streak=int(np.max(loss_streak_arr)),
            win_streak_distribution=win_streak_arr,
            loss_streak_distribution=loss_streak_arr,
            # Category 7
            mean_recovery_factor=float(
                np.mean(recovery_factor_arr[np.isfinite(recovery_factor_arr)])
            ),
            recovery_factor_distribution=recovery_factor_arr,
            # Category 8
            mean_profit_factor=float(
                np.mean(profit_factor_arr[np.isfinite(profit_factor_arr)])
            ),
            profit_factor_distribution=profit_factor_arr,
            # Category 9
            mean_avg_dd_duration=float(np.mean(avg_dd_duration_arr)),
            mean_max_dd_duration=float(np.mean(max_dd_duration_arr)),
            max_dd_duration_distribution=max_dd_duration_arr,
            # Category 10
            var=var,
            cvar=cvar,
            # Chart data
            equity_percentiles=equity_percentiles,
        )


def extract_gains_from_app_state(
    baseline_df: "pd.DataFrame | None",
    column_mapping: "ColumnMapping | None",
    first_trigger_enabled: bool = False,
) -> NDArray[np.float64]:
    """Extract adjusted gains array from baseline DataFrame for Monte Carlo simulation.

    Uses adjusted_gain_pct column which has stop-loss capped gains.
    Falls back to gain_pct if adjusted_gain_pct is not available.

    Args:
        baseline_df: The baseline DataFrame containing adjusted_gain_pct column.
        column_mapping: Column mapping with gain_pct field.
        first_trigger_enabled: Whether to filter to first triggers only.

    Returns:
        NumPy array of trade returns (as decimals, e.g., 0.05 for 5% gain).

    Raises:
        ValueError: If DataFrame is empty, missing required columns, or has
            fewer than 10 trades after filtering.
    """
    import pandas as pd

    # Local import to avoid circular dependency
    from src.core.column_mapper import ColumnMapping  # noqa: F811

    if baseline_df is None or baseline_df.empty:
        raise ValueError("No data available: baseline DataFrame is empty")

    if column_mapping is None:
        raise ValueError("Column mapping not configured")

    # Use adjusted_gain_pct if available, otherwise fall back to gain_pct
    if "adjusted_gain_pct" in baseline_df.columns:
        gain_col = "adjusted_gain_pct"
        logger.debug("Using adjusted_gain_pct for Monte Carlo")
    else:
        gain_col = column_mapping.gain_pct
        logger.warning(
            "adjusted_gain_pct not found, falling back to %s. "
            "Results may include uncapped losses.",
            gain_col,
        )

    if gain_col not in baseline_df.columns:
        raise ValueError(f"Gain column '{gain_col}' not found in DataFrame")

    # Start with baseline_df
    df = baseline_df

    # Apply first trigger filter if enabled
    if first_trigger_enabled and "trigger_number" in df.columns:
        df = df[df["trigger_number"] == 1]
        logger.debug(
            "First trigger filter applied for Monte Carlo: %d -> %d rows",
            len(baseline_df),
            len(df),
        )

    if len(df) == 0:
        raise ValueError("No data available after first trigger filtering")

    if len(df) < 10:
        raise ValueError(
            f"Insufficient data for Monte Carlo: need at least 10 trades, got {len(df)}"
        )

    # Extract gains as numpy array - NO conversion needed
    # adjusted_gain_pct is already in decimal format with capped losses
    gains = df[gain_col].to_numpy(dtype=np.float64)

    logger.debug(
        "Extracted %d gains for Monte Carlo: min=%.4f, max=%.4f",
        len(gains),
        np.min(gains),
        np.max(gains),
    )

    return gains
