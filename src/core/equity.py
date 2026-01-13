"""Equity curve calculations for flat stake and Kelly position sizing.

This module provides equity curve calculation functionality for trading
performance analysis. It supports flat stake (fixed position size) calculations
and is designed to be extended for Kelly-based calculations in Story 3.5.
"""

import logging

import numpy as np
import pandas as pd

from src.core.exceptions import EquityCalculationError

logger = logging.getLogger(__name__)


class EquityCalculator:
    """Calculate equity curves for flat stake and Kelly position sizing.

    Reusable for Story 3.5 (Kelly metrics).
    """

    def calculate_flat_stake(
        self,
        df: pd.DataFrame,
        gain_col: str,
        stake: float,
        date_col: str | None = None,
    ) -> pd.DataFrame:
        """Calculate flat stake equity curve.

        Args:
            df: DataFrame containing trade data
            gain_col: Column name containing gain percentages (e.g., 5.0 = 5%)
            stake: Fixed stake amount in dollars

        Returns:
            DataFrame with columns: trade_num, pnl, equity, peak, drawdown

        Raises:
            EquityCalculationError: If gain_col not found or calculation fails
        """
        if df.empty:
            return pd.DataFrame(columns=["trade_num", "pnl", "equity", "peak", "drawdown"])

        if gain_col not in df.columns:
            raise EquityCalculationError(f"Column '{gain_col}' not found in DataFrame")

        try:
            gains: np.ndarray = df[gain_col].to_numpy(dtype=float)

            # Calculate PnL for each trade
            pnl: np.ndarray = stake * (gains / 100.0)

            # Calculate equity curve
            equity = np.cumsum(pnl)

            # Calculate running peak
            peak = np.maximum.accumulate(equity)

            # Calculate drawdown (always <= 0)
            drawdown = equity - peak

            result = pd.DataFrame({
                "trade_num": np.arange(1, len(gains) + 1),
                "pnl": pnl,
                "equity": equity,
                "peak": peak,
                "drawdown": drawdown,
            })

            # Include date column if provided
            if date_col is not None and date_col in df.columns:
                result["date"] = df[date_col].values

            logger.debug(
                "Calculated equity curve: %d trades, final equity=%.2f",
                len(gains),
                equity[-1] if len(equity) > 0 else 0,
            )

            return result

        except Exception as e:
            raise EquityCalculationError(f"Failed to calculate equity curve: {e}") from e

    def calculate_drawdown_metrics(
        self,
        equity_df: pd.DataFrame,
    ) -> tuple[float | None, float | None, int | str | None]:
        """Calculate max drawdown and duration.

        Returns:
            Tuple of (max_dd_dollars, max_dd_pct, dd_duration)
            - max_dd_dollars: Maximum drawdown in absolute dollar terms
            - max_dd_pct: Maximum drawdown as percentage of peak at that point
            - dd_duration: int (trading days) or "Not recovered"

        Note:
            Returns (None, None, None) if no drawdown occurred (equity only increased)
            or if peak is zero/negative (edge case - no valid percentage).
        """
        if equity_df.empty:
            return (None, None, None)

        drawdown: np.ndarray = equity_df["drawdown"].to_numpy(dtype=float)
        peak: np.ndarray = equity_df["peak"].to_numpy(dtype=float)
        equity: np.ndarray = equity_df["equity"].to_numpy(dtype=float)

        # Check if there's any drawdown
        if np.all(drawdown >= 0):
            return (None, None, None)

        # Calculate drawdown percentage at each point
        # Avoid division by zero for zero/negative peaks
        with np.errstate(divide="ignore", invalid="ignore"):
            drawdown_pct: np.ndarray = np.where(peak > 0, (drawdown / peak) * -100.0, 0.0)

        # Find maximum DOLLAR drawdown (most negative drawdown value)
        max_dd_dollar_idx = int(np.argmin(drawdown))  # argmin because drawdown is negative
        max_dd_dollars = float(abs(drawdown[max_dd_dollar_idx]))

        # Find maximum PERCENTAGE drawdown
        max_dd_pct_idx = int(np.argmax(drawdown_pct))
        max_dd_pct_value: float | None = float(drawdown_pct[max_dd_pct_idx])
        peak_at_max_dd = float(peak[max_dd_pct_idx])

        # Edge case: if peak is zero or negative, percentage is undefined
        if peak_at_max_dd <= 0:
            max_dd_pct_value = None

        # Calculate drawdown duration (from max percentage drawdown point)
        dd_duration: int | str | None
        recovered = False
        for i in range(max_dd_pct_idx + 1, len(equity)):
            if equity[i] >= peak_at_max_dd:
                dd_duration = i - max_dd_pct_idx
                recovered = True
                break

        if not recovered:
            dd_duration = "Not recovered"

        logger.debug(
            "Drawdown metrics: max_dd=$%.2f, max_dd_pct=%s, duration=%s",
            max_dd_dollars,
            f"{max_dd_pct_value:.2f}%" if max_dd_pct_value is not None else "N/A",
            dd_duration,
        )

        return (max_dd_dollars, max_dd_pct_value, dd_duration)

    def calculate_flat_stake_metrics(
        self,
        df: pd.DataFrame,
        gain_col: str,
        stake: float,
        date_col: str | None = None,
    ) -> dict[str, float | int | str | pd.DataFrame | None]:
        """Calculate all flat stake metrics.

        Args:
            df: DataFrame containing trade data
            gain_col: Column name containing gain percentages
            stake: Fixed stake amount in dollars
            date_col: Optional date column name to include in equity curve

        Returns:
            Dict with keys: pnl, max_dd, max_dd_pct, dd_duration, equity_curve
        """
        # Calculate equity curve
        equity_df = self.calculate_flat_stake(df, gain_col, stake, date_col=date_col)

        if equity_df.empty:
            return {
                "pnl": None,
                "max_dd": None,
                "max_dd_pct": None,
                "dd_duration": None,
                "equity_curve": equity_df,
            }

        # Get total PnL (final equity value)
        pnl = float(equity_df["equity"].iloc[-1])

        # Calculate drawdown metrics
        max_dd, max_dd_pct, dd_duration = self.calculate_drawdown_metrics(equity_df)

        return {
            "pnl": pnl,
            "max_dd": max_dd,
            "max_dd_pct": max_dd_pct,
            "dd_duration": dd_duration,
            "equity_curve": equity_df,
        }

    def calculate_kelly(
        self,
        df: pd.DataFrame,
        gain_col: str,
        start_capital: float,
        kelly_fraction: float,
        kelly_pct: float,
        date_col: str | None = None,
    ) -> pd.DataFrame:
        """Calculate compounded Kelly equity curve.

        Args:
            df: DataFrame containing trade data
            gain_col: Column name containing gain percentages (e.g., 5.0 = 5%)
            start_capital: Starting capital in dollars
            kelly_fraction: Kelly fraction as percentage (e.g., 25 = 25% of Kelly)
            kelly_pct: Base Kelly percentage from core metrics (e.g., 12.5 = 12.5%)

        Returns:
            DataFrame with columns: trade_num, pnl, equity, peak, drawdown, position_size

        Raises:
            EquityCalculationError: If gain_col not found or calculation fails
        """
        if df.empty:
            return pd.DataFrame(
                columns=["trade_num", "pnl", "equity", "peak", "drawdown", "position_size"]
            )

        if gain_col not in df.columns:
            raise EquityCalculationError(f"Column '{gain_col}' not found in DataFrame")

        try:
            gains: np.ndarray = df[gain_col].to_numpy(dtype=float)
            n_trades = len(gains)

            # Calculate effective Kelly: kelly_pct * (kelly_fraction / 100)
            effective_kelly = kelly_pct * (kelly_fraction / 100.0)

            # Preallocate arrays
            pnl = np.zeros(n_trades)
            equity = np.zeros(n_trades)
            peak = np.zeros(n_trades)
            drawdown = np.zeros(n_trades)
            position_size = np.zeros(n_trades)

            # Initialize
            current_equity = start_capital
            current_peak = start_capital
            blown = False

            for i in range(n_trades):
                if blown:
                    # Account blown - set remaining trades to 0
                    pnl[i] = 0.0
                    equity[i] = 0.0
                    peak[i] = current_peak
                    drawdown[i] = -current_peak
                    position_size[i] = 0.0
                    continue

                # Calculate position size based on current equity and Kelly
                pos_size = current_equity * (effective_kelly / 100.0)
                position_size[i] = pos_size

                # Calculate trade PnL
                trade_pnl = pos_size * (gains[i] / 100.0)
                pnl[i] = trade_pnl

                # Update equity
                new_equity = current_equity + trade_pnl
                equity[i] = new_equity

                # Check for blown account
                if new_equity <= 0:
                    logger.warning(
                        "Account blown at trade %d, equity=%.2f", i + 1, new_equity
                    )
                    equity[i] = 0.0
                    blown = True

                # Update peak and drawdown
                current_equity = equity[i]
                if current_equity > current_peak:
                    current_peak = current_equity
                peak[i] = current_peak
                drawdown[i] = current_equity - current_peak

            result = pd.DataFrame({
                "trade_num": np.arange(1, n_trades + 1),
                "pnl": pnl,
                "equity": equity,
                "peak": peak,
                "drawdown": drawdown,
                "position_size": position_size,
            })

            # Include date column if provided
            if date_col is not None and date_col in df.columns:
                result["date"] = df[date_col].values

            logger.debug(
                "Calculated Kelly equity curve: %d trades, final equity=%.2f, effective_kelly=%.2f%%",
                n_trades,
                equity[-1] if n_trades > 0 else 0,
                effective_kelly,
            )

            return result

        except Exception as e:
            raise EquityCalculationError(f"Failed to calculate Kelly equity curve: {e}") from e

    def calculate_kelly_metrics(
        self,
        df: pd.DataFrame,
        gain_col: str,
        start_capital: float,
        kelly_fraction: float,
        kelly_pct: float | None,
        date_col: str | None = None,
    ) -> dict[str, float | int | str | pd.DataFrame | None]:
        """Calculate all compounded Kelly metrics.

        Args:
            df: DataFrame containing trade data
            gain_col: Column name containing gain percentages
            start_capital: Starting capital in dollars
            kelly_fraction: Fractional Kelly as percentage (e.g., 25 = 25%)
            kelly_pct: Base Kelly percentage from core metrics (e.g., 12.5).
                       Passed from TradingMetrics.kelly calculated by MetricsCalculator.
            date_col: Optional date column name to include in equity curve

        Returns:
            Dict with keys: pnl, max_dd, max_dd_pct, dd_duration, equity_curve, warning
            - warning: None if OK, "negative_kelly" if kelly_pct < 0
        """
        # Check for negative Kelly - early return with warning
        if kelly_pct is None or kelly_pct < 0:
            if kelly_pct is not None and kelly_pct < 0:
                logger.warning(
                    "Negative Kelly detected: %.2f%%, strategy has negative expectancy", kelly_pct
                )
            return {
                "pnl": None,
                "max_dd": None,
                "max_dd_pct": None,
                "dd_duration": None,
                "equity_curve": None,
                "warning": "negative_kelly" if kelly_pct is not None and kelly_pct < 0 else None,
            }

        # Calculate equity curve
        equity_df = self.calculate_kelly(df, gain_col, start_capital, kelly_fraction, kelly_pct, date_col=date_col)

        if equity_df.empty:
            return {
                "pnl": None,
                "max_dd": None,
                "max_dd_pct": None,
                "dd_duration": None,
                "equity_curve": equity_df,
                "warning": None,
            }

        # Check if account was blown (equity went to 0)
        equity_values = equity_df["equity"].to_numpy()
        blown = any(equity_values == 0.0) and equity_values[-1] == 0.0

        # Calculate final PnL
        final_equity = float(equity_df["equity"].iloc[-1])
        pnl = final_equity - start_capital

        # Calculate drawdown metrics
        max_dd, max_dd_pct, dd_duration = self.calculate_drawdown_metrics(equity_df)

        # Override dd_duration to "Blown" if account was blown
        if blown:
            dd_duration = "Blown"

        return {
            "pnl": pnl,
            "max_dd": max_dd,
            "max_dd_pct": max_dd_pct,
            "dd_duration": dd_duration,
            "equity_curve": equity_df,
            "warning": None,
        }
