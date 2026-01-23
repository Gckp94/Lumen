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
            ),
        )
        assert config.name == "Test Strategy"
        assert config.stop_pct == 2.0  # default
        assert config.efficiency == 5.0  # default 5% (stored as percentage points)
        assert config.size_type == PositionSizeType.CUSTOM_PCT
        assert config.size_value == 10.0  # default 10%
        assert config.max_compound == 50000.0  # default $50,000
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
        )
        assert mapping.date_col == "trade_date"
        assert mapping.gain_pct_col == "return_pct"


class TestPortfolioColumnMappingMae:
    def test_mae_pct_col_defaults_to_none(self):
        mapping = PortfolioColumnMapping("date", "gain")
        assert mapping.mae_pct_col is None

    def test_mae_pct_col_can_be_set(self):
        mapping = PortfolioColumnMapping("date", "gain", mae_pct_col="mae")
        assert mapping.mae_pct_col == "mae"


class TestStrategyConfigSheetName:
    def test_strategy_config_sheet_name_defaults_to_none(self):
        config = StrategyConfig(
            name="Test",
            file_path="/path/to/file.xlsx",
            column_mapping=PortfolioColumnMapping(
                date_col="date",
                gain_pct_col="gain",
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
            ),
            sheet_name="Sheet2",
        )
        assert config.sheet_name == "Sheet2"