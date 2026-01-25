# src/core/portfolio_calculator.py
"""Portfolio equity and drawdown calculation."""
import logging

import pandas as pd

from src.core.portfolio_models import PositionSizeType, StrategyConfig

logger = logging.getLogger(__name__)


class PortfolioCalculator:
    """Calculates equity curves for single or multiple strategies."""

    def __init__(self, starting_capital: float = 100_000):
        self.starting_capital = starting_capital

    def _calculate_kelly_pct(
        self,
        trades_df: pd.DataFrame,
        gain_col: str,
    ) -> float | None:
        """Calculate Kelly % from trade data.

        Kelly = (win_rate) - (loss_rate / R:R ratio)

        Args:
            trades_df: DataFrame with trade data.
            gain_col: Column name for gain percentage (in decimal form).

        Returns:
            Kelly percentage, or None if cannot be calculated.
        """
        if trades_df.empty or gain_col not in trades_df.columns:
            return None

        gains = trades_df[gain_col].astype(float) * 100.0  # Convert to percentage
        winners = gains[gains > 0]
        losers = gains[gains < 0]

        if len(winners) == 0 or len(losers) == 0:
            return None

        win_rate = len(winners) / len(gains) * 100  # As percentage
        avg_win = winners.mean()
        avg_loss = abs(losers.mean())

        if avg_loss == 0:
            return None

        rr_ratio = avg_win / avg_loss

        # Kelly = win_rate% - (loss_rate% / R:R)
        kelly = (win_rate / 100) - ((1 - win_rate / 100) / rr_ratio)
        kelly_pct = kelly * 100  # Convert to percentage

        return kelly_pct

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
            return pd.DataFrame(
                columns=["date", "trade_num", "pnl", "equity", "peak", "drawdown", "win"]
            )

        mapping = config.column_mapping
        df = trades_df.copy()
        df = df.sort_values(mapping.date_col).reset_index(drop=True)

        # Pre-calculate Kelly % if using Frac Kelly sizing
        kelly_pct: float | None = None
        if config.size_type == PositionSizeType.FRAC_KELLY:
            kelly_pct = self._calculate_kelly_pct(df, mapping.gain_pct_col)
            if kelly_pct is not None:
                logger.info(f"Calculated Kelly %: {kelly_pct:.2f}% for strategy {config.name}")

        # Group by date for daily compounding
        df["_date"] = pd.to_datetime(df[mapping.date_col], dayfirst=True).dt.date

        results = []
        account_value = self.starting_capital
        peak = self.starting_capital
        trade_num = 0

        for _date, day_trades in df.groupby("_date", sort=True):
            day_opening = account_value

            for _, trade in day_trades.iterrows():
                trade_num += 1
                # Convert from decimal form (0.07) to percentage form (7.0)
                gain_pct = float(trade[mapping.gain_pct_col]) * 100.0

                # Calculate position size
                position_size = self._calculate_position_size(
                    day_opening, config, kelly_pct
                )

                # Step 1: Stop loss adjustment (if MAE column available)
                if mapping.mae_pct_col and mapping.mae_pct_col in df.columns:
                    # MAE is already in percentage form (e.g., 5.0 = 5%)
                    # Do NOT multiply by 100 like gain_pct
                    mae_pct = float(trade[mapping.mae_pct_col])
                    stop_adjusted = (
                        -config.stop_pct if mae_pct > config.stop_pct else gain_pct
                    )
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

                result_row = {
                    "date": trade[mapping.date_col],
                    "trade_num": trade_num,
                    "pnl": pnl,
                    "equity": account_value,
                    "peak": peak,
                    "drawdown": drawdown,
                    "win": adjusted_gain > 0,  # Derived from adjusted gain
                }

                # Preserve ticker if available
                if mapping.ticker_col and mapping.ticker_col in df.columns:
                    result_row["ticker"] = trade[mapping.ticker_col]

                results.append(result_row)

        return pd.DataFrame(results)

    def _calculate_position_size(
        self,
        account_value: float,
        config: StrategyConfig,
        kelly_pct: float | None = None,
    ) -> float:
        """Calculate position size based on config.

        Args:
            account_value: Current account value.
            config: Strategy configuration.
            kelly_pct: Pre-calculated Kelly % (required for FRAC_KELLY).

        Returns:
            Position size in dollars.
        """
        if config.size_type == PositionSizeType.FLAT_DOLLAR:
            size = config.size_value
        elif config.size_type == PositionSizeType.CUSTOM_PCT:
            # size_value is percentage (e.g., 10 = 10%)
            size = account_value * (config.size_value / 100.0)
        elif config.size_type == PositionSizeType.FRAC_KELLY:
            # Frac Kelly = Kelly % × fraction
            # size_value is the fraction (e.g., 0.25 = 25% of Kelly, or 25 = 25% of Kelly)
            if kelly_pct is not None and kelly_pct > 0:
                # Interpret size_value: if > 1, treat as percentage; if <= 1, treat as decimal
                fraction = (
                    config.size_value
                    if config.size_value <= 1
                    else config.size_value / 100.0
                )
                effective_kelly = kelly_pct * fraction
                size = account_value * (effective_kelly / 100.0)
            else:
                # Fallback: no Kelly available, use size_value as percentage
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
            DataFrame with columns: date, trade_num, strategy, pnl, equity, peak,
            drawdown, win, ticker
        """
        if not strategies:
            return pd.DataFrame(
                columns=[
                    "date",
                    "trade_num",
                    "strategy",
                    "pnl",
                    "equity",
                    "peak",
                    "drawdown",
                    "win",
                    "ticker",
                ]
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
            # Pre-calculate Kelly % for this strategy if using Frac Kelly
            kelly_pct: float | None = None
            if config.size_type == PositionSizeType.FRAC_KELLY:
                kelly_pct = self._calculate_kelly_pct(df, mapping.gain_pct_col)
                if kelly_pct is not None:
                    logger.info(f"Calculated Kelly %: {kelly_pct:.2f}% for strategy {config.name}")
            df["_kelly_pct"] = kelly_pct
            # Include MAE if available
            if mapping.mae_pct_col and mapping.mae_pct_col in df.columns:
                df["_mae_pct"] = df[mapping.mae_pct_col]
            else:
                df["_mae_pct"] = None
            # Include ticker if available
            if mapping.ticker_col and mapping.ticker_col in df.columns:
                df["_ticker"] = df[mapping.ticker_col]
            else:
                df["_ticker"] = None
            all_trades.append(
                df[
                    [
                        "_date",
                        "_gain_pct",
                        "_mae_pct",
                        "_strategy_name",
                        "_config",
                        "_kelly_pct",
                        "_ticker",
                    ]
                ]
            )

        if not all_trades:
            return pd.DataFrame(
                columns=[
                    "date", "trade_num", "strategy", "pnl",
                    "equity", "peak", "drawdown", "win", "ticker",
                ]
            )

        merged = pd.concat(all_trades, ignore_index=True)
        merged = merged.sort_values("_date").reset_index(drop=True)
        merged["_date_only"] = merged["_date"].dt.date

        results = []
        account_value = self.starting_capital
        peak = self.starting_capital
        trade_num = 0

        for _date, day_trades in merged.groupby("_date_only", sort=True):
            day_opening = account_value

            for _, trade in day_trades.iterrows():
                trade_num += 1
                config: StrategyConfig = trade["_config"]
                kelly_pct = trade["_kelly_pct"]
                # Convert from decimal form (0.07) to percentage form (7.0)
                gain_pct = float(trade["_gain_pct"]) * 100.0

                position_size = self._calculate_position_size(day_opening, config, kelly_pct)

                # Step 1: Stop loss adjustment (if MAE available)
                mae_pct = trade["_mae_pct"]
                if mae_pct is not None:
                    # MAE is already in percentage form (e.g., 5.0 = 5%)
                    # Do NOT multiply by 100 like gain_pct
                    mae_pct = float(mae_pct)
                    stop_adjusted = (
                        -config.stop_pct if mae_pct > config.stop_pct else gain_pct
                    )
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
                    "ticker": trade["_ticker"],
                })

        return pd.DataFrame(results)
