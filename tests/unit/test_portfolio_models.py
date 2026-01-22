# tests/unit/test_portfolio_models.py
import pytest
from src.core.portfolio_models import (
    PositionSizeType,
    StrategyConfig,
    PortfolioColumnMapping,
)


class TestStrategyConfig:
    def test_create_strategy_config_with_defaults(self):
        config = StrategyConfig(
            name="Test Strategy",
            file_path="/path/to/file.csv",
            column_mapping=PortfolioColumnMapping(
                date_col="date",
                gain_pct_col="gain_pct",
                win_loss_col="wl",
            ),
        )
        assert config.name == "Test Strategy"
        assert config.stop_pct == 2.0  # default
        assert config.efficiency == 1.0  # default
        assert config.size_type == PositionSizeType.CUSTOM_PCT
        assert config.size_value == 10.0  # default 10%
        assert config.max_compound is None
        assert config.is_baseline is False
        assert config.is_candidate is False

    def test_position_size_type_enum(self):
        assert PositionSizeType.FRAC_KELLY.value == "frac_kelly"
        assert PositionSizeType.CUSTOM_PCT.value == "custom_pct"
        assert PositionSizeType.FLAT_DOLLAR.value == "flat_dollar"

    def test_column_mapping_validation(self):
        mapping = PortfolioColumnMapping(
            date_col="trade_date",
            gain_pct_col="return_pct",
            win_loss_col="outcome",
        )
        assert mapping.date_col == "trade_date"
        assert mapping.gain_pct_col == "return_pct"
        assert mapping.win_loss_col == "outcome"


class TestStrategyConfigSheetName:
    def test_strategy_config_sheet_name_defaults_to_none(self):
        config = StrategyConfig(
            name="Test",
            file_path="/path/to/file.xlsx",
            column_mapping=PortfolioColumnMapping(
                date_col="date",
                gain_pct_col="gain",
                win_loss_col="wl",
            ),
        )
        assert config.sheet_name is None

    def test_strategy_config_stores_sheet_name(self):
        config = StrategyConfig(
            name="Test",
            file_path="/path/to/file.xlsx",
            column_mapping=PortfolioColumnMapping(
                date_col="date",
                gain_pct_col="gain",
                win_loss_col="wl",
            ),
            sheet_name="Sheet2",
        )
        assert config.sheet_name == "Sheet2"