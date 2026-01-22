# tests/unit/test_portfolio_config_manager.py
import pytest
import json
from pathlib import Path
from src.core.portfolio_config_manager import PortfolioConfigManager
from src.core.portfolio_models import StrategyConfig, PortfolioColumnMapping, PositionSizeType


class TestPortfolioConfigManager:
    def test_save_and_load_config(self, tmp_path):
        config_file = tmp_path / "portfolio_config.json"
        manager = PortfolioConfigManager(config_file)

        strategies = [
            StrategyConfig(
                name="Strategy A",
                file_path="/path/to/a.csv",
                column_mapping=PortfolioColumnMapping("date", "gain", "wl"),
                is_baseline=True,
                size_value=15.0,
            ),
            StrategyConfig(
                name="Strategy B",
                file_path="/path/to/b.csv",
                column_mapping=PortfolioColumnMapping("dt", "pct", "outcome"),
                is_candidate=True,
            ),
        ]

        manager.save(strategies, account_start=150_000)

        loaded_strategies, account_start = manager.load()

        assert len(loaded_strategies) == 2
        assert loaded_strategies[0].name == "Strategy A"
        assert loaded_strategies[0].is_baseline is True
        assert loaded_strategies[0].size_value == 15.0
        assert loaded_strategies[1].is_candidate is True
        assert account_start == 150_000

    def test_load_missing_file_returns_empty(self, tmp_path):
        config_file = tmp_path / "nonexistent.json"
        manager = PortfolioConfigManager(config_file)

        strategies, account_start = manager.load()

        assert strategies == []
        assert account_start == 100_000  # default
