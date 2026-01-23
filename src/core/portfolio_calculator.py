# src/core/portfolio_calculator.py
"""Portfolio equity and drawdown calculation."""
import logging
from typing import Optional

import numpy as np
import pandas as pd

from src.core.portfolio_models import StrategyConfig, PositionSizeType

logger = logging.getLogger(__name__)


class PortfolioCalculator:
    """Calculates equity curves for single or multiple strategies."""

    def __init__(self, starting_capital: float = 100_000):
        self.starting_capital = starting_capital

    def calculate_single_strategy(
        self,
        trades_df: pd.DataFrame,
        config: StrategyConfig,
    ) -> pd.DataFrame:
        """Calculate equity curve for a single strategy with daily compounding.

        Args:
            trades_df: DataFrame with trade data (must have columns from config.column_mapping)
            config: Strategy configuration

        Returns:
            DataFrame with columns: date, trade_num, pnl, equity, peak, drawdown
        """
        if trades_df.empty:
            return pd.DataFrame(columns=["date", "trade_num", "pnl", "equity", "peak", "drawdown", "win"])

        mapping = config.column_mapping
        df = trades_df.copy()
        df = df.sort_values(mapping.date_col).reset_index(drop=True)

        # Group by date for daily compounding
        df["_date"] = pd.to_datetime(df[mapping.date_col], dayfirst=True).dt.date

        results = []
        account_value = self.starting_capital
        peak = self.starting_capital
        trade_num = 0

        for date, day_trades in df.groupby("_date", sort=True):
            day_opening = account_value

            for _, trade in day_trades.iterrows():
                trade_num += 1
                # Convert from decimal form (0.07) to percentage form (7.0)
                raw_gain = float(trade[mapping.gain_pct_col])
                gain_pct = raw_gain * 100.0

                # Calculate position size
                position_size = self._calculate_position_size(
                    day_opening, config
                )

                # Step 1: Stop loss adjustment (if MAE column available)
                if mapping.mae_pct_col and mapping.mae_pct_col in df.columns:
                    # MAE is already in percentage form (e.g., 5.0 = 5%)
                    # Do NOT multiply by 100 like gain_pct
                    mae_pct = float(trade[mapping.mae_pct_col])
                    if mae_pct > config.stop_pct:
                        stop_adjusted = -config.stop_pct
                    else:
                        stop_adjusted = gain_pct
                else:
                    stop_adjusted = gain_pct

                # Step 2: Efficiency adjustment
                # efficiency is stored as percentage (e.g., 5.0 = 5%)
                # We subtract it directly from the gain percentage
                adjusted_gain = stop_adjusted - config.efficiency

                pnl = position_size * (adjusted_gain / 100.0)

                # DEBUG: Log first 5 trades to understand calculation
                if trade_num <= 5:
                    mae_info = f", mae={mae_pct}%" if mapping.mae_pct_col and mapping.mae_pct_col in df.columns else ""
                    logger.info(
                        f"Trade {trade_num}: raw_gain={raw_gain}, gain_pct={gain_pct}%{mae_info}, "
                        f"stop_adjusted={stop_adjusted}%, efficiency={config.efficiency}%, "
                        f"adjusted_gain={adjusted_gain}%, position={position_size}, pnl={pnl}"
                    )

                account_value += pnl
                peak = max(peak, account_value)
                drawdown = account_value - peak

                results.append({
                    "date": trade[mapping.date_col],
                    "trade_num": trade_num,
                    "pnl": pnl,
                    "equity": account_value,
                    "peak": peak,
                    "drawdown": drawdown,
                    "win": adjusted_gain > 0,  # Derived from adjusted gain
                })

        return pd.DataFrame(results)

    def _calculate_position_size(
        self,
        account_value: float,
        config: StrategyConfig,
    ) -> float:
        """Calculate position size based on config."""
        if config.size_type == PositionSizeType.FLAT_DOLLAR:
            size = config.size_value
        elif config.size_type == PositionSizeType.CUSTOM_PCT:
            size = account_value * (config.size_value / 100.0)
        elif config.size_type == PositionSizeType.FRAC_KELLY:
            # For frac kelly, size_value is the fraction (e.g., 0.25 for quarter kelly)
            # Simplified: treat as percentage for now
            size = account_value * (config.size_value / 100.0)
        else:
            size = account_value * 0.10  # fallback 10%

        # Apply max compound limit
        if config.max_compound is not None:
            size = min(size, config.max_compound)

        return size

    def calculate_portfolio(
        self,
        strategies: list[tuple[pd.DataFrame, StrategyConfig]],
    ) -> pd.DataFrame:
        """Calculate combined equity curve for multiple strategies.

        Trades are merged chronologically. All trades on the same day use
        that day's opening account value for position sizing.

        Args:
            strategies: List of (trades_df, config) tuples

        Returns:
            DataFrame with columns: date, trade_num, strategy, pnl, equity, peak, drawdown
        """
        if not strategies:
            return pd.DataFrame(
                columns=["date", "trade_num", "strategy", "pnl", "equity", "peak", "drawdown", "win"]
            )

        all_trades = []
        for trades_df, config in strategies:
            if trades_df.empty:
                continue
            df = trades_df.copy()
            mapping = config.column_mapping
            df["_strategy_name"] = config.name
            df["_gain_pct"] = df[mapping.gain_pct_col]
            df["_date"] = pd.to_datetime(df[mapping.date_col], dayfirst=True)
            df["_config"] = [config] * len(df)
            # Include MAE if available
            if mapping.mae_pct_col and mapping.mae_pct_col in df.columns:
                df["_mae_pct"] = df[mapping.mae_pct_col]
            else:
                df["_mae_pct"] = None
            all_trades.append(df[["_date", "_gain_pct", "_mae_pct", "_strategy_name", "_config"]])

        if not all_trades:
            return pd.DataFrame(
                columns=["date", "trade_num", "strategy", "pnl", "equity", "peak", "drawdown"]
            )

        merged = pd.concat(all_trades, ignore_index=True)
        merged = merged.sort_values("_date").reset_index(drop=True)
        merged["_date_only"] = merged["_date"].dt.date

        results = []
        account_value = self.starting_capital
        peak = self.starting_capital
        trade_num = 0

        for date, day_trades in merged.groupby("_date_only", sort=True):
            day_opening = account_value

            for _, trade in day_trades.iterrows():
                trade_num += 1
                config: StrategyConfig = trade["_config"]
                # Convert from decimal form (0.07) to percentage form (7.0)
                gain_pct = float(trade["_gain_pct"]) * 100.0

                position_size = self._calculate_position_size(day_opening, config)

                # Step 1: Stop loss adjustment (if MAE available)
                mae_pct = trade["_mae_pct"]
                if mae_pct is not None:
                    # MAE is already in percentage form (e.g., 5.0 = 5%)
                    # Do NOT multiply by 100 like gain_pct
                    mae_pct = float(mae_pct)
                    if mae_pct > config.stop_pct:
                        stop_adjusted = -config.stop_pct
                    else:
                        stop_adjusted = gain_pct
                else:
                    stop_adjusted = gain_pct

                # Step 2: Efficiency adjustment
                # efficiency is stored as percentage (e.g., 5.0 = 5%)
                # We subtract it directly from the gain percentage
                adjusted_gain = stop_adjusted - config.efficiency

                pnl = position_size * (adjusted_gain / 100.0)

                account_value += pnl
                peak = max(peak, account_value)
                drawdown = account_value - peak

                results.append({
                    "date": trade["_date"],
                    "trade_num": trade_num,
                    "strategy": trade["_strategy_name"],
                    "pnl": pnl,
                    "equity": account_value,
                    "peak": peak,
                    "drawdown": drawdown,
                    "win": adjusted_gain > 0,  # Derived from adjusted gain
                })

        return pd.DataFrame(results)
