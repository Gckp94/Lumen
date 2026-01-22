# tests/unit/test_portfolio_calculator.py
import pytest
import pandas as pd
import numpy as np
from src.core.portfolio_calculator import PortfolioCalculator
from src.core.portfolio_models import (
    StrategyConfig,
    PortfolioColumnMapping,
    PositionSizeType,
)


class TestPortfolioCalculatorSingleStrategy:
    @pytest.fixture
    def sample_trades(self):
        """Sample trade data with 5 trades."""
        return pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-02", "2024-01-03", "2024-01-04"]),
            "gain_pct": [5.0, -2.0, 3.0, 4.0, -1.0],
            "wl": ["W", "L", "W", "W", "L"],
        })

    @pytest.fixture
    def strategy_config(self):
        return StrategyConfig(
            name="Test",
            file_path="test.csv",
            column_mapping=PortfolioColumnMapping("date", "gain_pct", "wl"),
            size_type=PositionSizeType.CUSTOM_PCT,
            size_value=10.0,  # 10% of account
            stop_pct=2.0,
            efficiency=1.0,
        )

    def test_calculate_single_strategy_equity(self, sample_trades, strategy_config):
        calc = PortfolioCalculator(starting_capital=100_000)
        result = calc.calculate_single_strategy(sample_trades, strategy_config)

        assert "equity" in result.columns
        assert "drawdown" in result.columns
        assert "date" in result.columns
        assert len(result) == 5

    def test_daily_compounding(self, sample_trades, strategy_config):
        """All trades on same day use same opening account value."""
        calc = PortfolioCalculator(starting_capital=100_000)
        result = calc.calculate_single_strategy(sample_trades, strategy_config)

        # Day 1: 1 trade, 5% gain on 10% position = 0.5% account gain
        # Account ends at 100,500
        # Day 2: 2 trades, both use 100,500 opening value
        #   Trade 1: -2% on 10,050 position = -201
        #   Trade 2: +3% on 10,050 position = +301.50
        # Account ends at 100,500 + 100.50 = 100,600.50
        assert result.iloc[0]["equity"] == pytest.approx(100_500, rel=0.01)
        # After day 2 trades (indices 1 and 2)
        assert result.iloc[2]["equity"] == pytest.approx(100_600.50, rel=0.01)

    def test_max_compound_limits_position_size(self, sample_trades, strategy_config):
        """Max compound caps position size."""
        strategy_config.max_compound = 5_000  # Cap at $5k position
        calc = PortfolioCalculator(starting_capital=100_000)
        result = calc.calculate_single_strategy(sample_trades, strategy_config)

        # 10% of 100k = 10k, but capped at 5k
        # Day 1: 5% of 5k = 250 gain
        assert result.iloc[0]["equity"] == pytest.approx(100_250, rel=0.01)

    def test_flat_dollar_position_sizing(self, sample_trades):
        """FLAT_DOLLAR uses fixed dollar amount as position size."""
        config = StrategyConfig(
            name="FlatDollar",
            file_path="test.csv",
            column_mapping=PortfolioColumnMapping("date", "gain_pct", "wl"),
            size_type=PositionSizeType.FLAT_DOLLAR,
            size_value=5_000,  # Fixed $5k position
            stop_pct=2.0,
            efficiency=1.0,
        )
        calc = PortfolioCalculator(starting_capital=100_000)
        result = calc.calculate_single_strategy(sample_trades, config)

        # Day 1: 5% gain on $5k position = $250 gain
        assert result.iloc[0]["equity"] == pytest.approx(100_250, rel=0.01)

    def test_flat_dollar_with_max_compound(self, sample_trades):
        """FLAT_DOLLAR respects max_compound cap."""
        config = StrategyConfig(
            name="FlatDollarCapped",
            file_path="test.csv",
            column_mapping=PortfolioColumnMapping("date", "gain_pct", "wl"),
            size_type=PositionSizeType.FLAT_DOLLAR,
            size_value=10_000,  # $10k position
            max_compound=5_000,  # But capped at $5k
            stop_pct=2.0,
            efficiency=1.0,
        )
        calc = PortfolioCalculator(starting_capital=100_000)
        result = calc.calculate_single_strategy(sample_trades, config)

        # Day 1: 5% gain on $5k (capped) position = $250 gain
        assert result.iloc[0]["equity"] == pytest.approx(100_250, rel=0.01)

    def test_frac_kelly_position_sizing(self, sample_trades):
        """FRAC_KELLY uses size_value as percentage multiplier."""
        config = StrategyConfig(
            name="FracKelly",
            file_path="test.csv",
            column_mapping=PortfolioColumnMapping("date", "gain_pct", "wl"),
            size_type=PositionSizeType.FRAC_KELLY,
            size_value=25.0,  # 25% (quarter kelly simplified as percentage)
            stop_pct=2.0,
            efficiency=1.0,
        )
        calc = PortfolioCalculator(starting_capital=100_000)
        result = calc.calculate_single_strategy(sample_trades, config)

        # Day 1: 5% gain on 25% of 100k = 5% on $25k = $1250 gain
        assert result.iloc[0]["equity"] == pytest.approx(101_250, rel=0.01)

    def test_efficiency_multiplier(self, sample_trades):
        """Efficiency multiplies the gain_pct."""
        config = StrategyConfig(
            name="Efficiency",
            file_path="test.csv",
            column_mapping=PortfolioColumnMapping("date", "gain_pct", "wl"),
            size_type=PositionSizeType.CUSTOM_PCT,
            size_value=10.0,  # 10% position
            stop_pct=2.0,
            efficiency=0.5,  # 50% efficiency
        )
        calc = PortfolioCalculator(starting_capital=100_000)
        result = calc.calculate_single_strategy(sample_trades, config)

        # Day 1: 5% gain * 0.5 efficiency = 2.5% effective gain
        # Position: 10% of 100k = $10k
        # PnL: 2.5% of $10k = $250
        assert result.iloc[0]["equity"] == pytest.approx(100_250, rel=0.01)

    def test_empty_dataframe_returns_empty_with_columns(self):
        """Empty DataFrame returns empty DataFrame with correct columns."""
        config = StrategyConfig(
            name="Empty",
            file_path="test.csv",
            column_mapping=PortfolioColumnMapping("date", "gain_pct", "wl"),
            size_type=PositionSizeType.CUSTOM_PCT,
            size_value=10.0,
            stop_pct=2.0,
            efficiency=1.0,
        )
        calc = PortfolioCalculator(starting_capital=100_000)
        empty_df = pd.DataFrame(columns=["date", "gain_pct", "wl"])
        result = calc.calculate_single_strategy(empty_df, config)

        assert len(result) == 0
        assert "date" in result.columns
        assert "trade_num" in result.columns
        assert "pnl" in result.columns
        assert "equity" in result.columns
        assert "peak" in result.columns
        assert "drawdown" in result.columns
