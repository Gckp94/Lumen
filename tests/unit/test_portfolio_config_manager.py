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
                column_mapping=PortfolioColumnMapping("date", "gain"),
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


class TestPortfolioConfigManagerSheetName:
    def test_saves_sheet_name(self, tmp_path):
        config_path = tmp_path / "test_config.json"
        manager = PortfolioConfigManager(config_path)

        config = StrategyConfig(
            name="Test",
            file_path="/path/to/file.xlsx",
            column_mapping=PortfolioColumnMapping(
                date_col="date",
                gain_pct_col="gain",
            ),
            sheet_name="Sheet2",
        )
        manager.save([config], 100_000)

        with open(config_path) as f:
            data = json.load(f)

        assert data["strategies"][0]["sheet_name"] == "Sheet2"

    def test_loads_sheet_name(self, tmp_path):
        config_path = tmp_path / "test_config.json"
        data = {
            "account_start": 100_000,
            "strategies": [{
                "name": "Test",
                "file_path": "/path/to/file.xlsx",
                "column_mapping": {
                    "date_col": "date",
                    "gain_pct_col": "gain",
                },
                "sheet_name": "Sheet2",
            }],
        }
        with open(config_path, "w") as f:
            json.dump(data, f)

        manager = PortfolioConfigManager(config_path)
        strategies, _ = manager.load()

        assert strategies[0].sheet_name == "Sheet2"

    def test_loads_none_when_sheet_name_missing(self, tmp_path):
        config_path = tmp_path / "test_config.json"
        data = {
            "account_start": 100_000,
            "strategies": [{
                "name": "Test",
                "file_path": "/path/to/file.csv",
                "column_mapping": {
                    "date_col": "date",
                    "gain_pct_col": "gain",
                },
            }],
        }
        with open(config_path, "w") as f:
            json.dump(data, f)

        manager = PortfolioConfigManager(config_path)
        strategies, _ = manager.load()

        assert strategies[0].sheet_name is None


class TestPortfolioConfigManagerMaePctCol:
    def test_saves_mae_pct_col(self, tmp_path):
        config_path = tmp_path / "test_config.json"
        manager = PortfolioConfigManager(config_path)

        config = StrategyConfig(
            name="Test",
            file_path="/path/to/file.csv",
            column_mapping=PortfolioColumnMapping(
                date_col="date",
                gain_pct_col="gain",
                mae_pct_col="mae",
            ),
        )
        manager.save([config], 100_000)

        with open(config_path) as f:
            data = json.load(f)

        assert data["strategies"][0]["column_mapping"]["mae_pct_col"] == "mae"

    def test_loads_mae_pct_col(self, tmp_path):
        config_path = tmp_path / "test_config.json"
        data = {
            "account_start": 100_000,
            "strategies": [{
                "name": "Test",
                "file_path": "/path/to/file.csv",
                "column_mapping": {
                    "date_col": "date",
                    "gain_pct_col": "gain",
                    "mae_pct_col": "mae_column",
                },
            }],
        }
        with open(config_path, "w") as f:
            json.dump(data, f)

        manager = PortfolioConfigManager(config_path)
        strategies, _ = manager.load()

        assert strategies[0].column_mapping.mae_pct_col == "mae_column"

    def test_backward_compat_loads_none_when_mae_missing(self, tmp_path):
        config_path = tmp_path / "test_config.json"
        data = {
            "account_start": 100_000,
            "strategies": [{
                "name": "Test",
                "file_path": "/path/to/file.csv",
                "column_mapping": {
                    "date_col": "date",
                    "gain_pct_col": "gain",
                },
            }],
        }
        with open(config_path, "w") as f:
            json.dump(data, f)

        manager = PortfolioConfigManager(config_path)
        strategies, _ = manager.load()

        assert strategies[0].column_mapping.mae_pct_col is None


class TestPortfolioConfigManagerMultipleEntry:
    """Tests for allow_multiple_entry config field with backwards compatibility."""

    def test_old_config_without_allow_multiple_entry_defaults_to_true(self, tmp_path):
        """Old configs without allow_multiple_entry should default to True."""
        config_path = tmp_path / "test_config.json"
        data = {
            "account_start": 100_000,
            "strategies": [{
                "name": "Test",
                "file_path": "/path/to/file.csv",
                "column_mapping": {
                    "date_col": "date",
                    "gain_pct_col": "gain",
                },
            }],
        }
        with open(config_path, "w") as f:
            json.dump(data, f)

        manager = PortfolioConfigManager(config_path)
        strategies, _ = manager.load()

        assert strategies[0].allow_multiple_entry is True

    def test_save_and_load_preserves_allow_multiple_entry_false(self, tmp_path):
        """Saving and loading config with allow_multiple_entry=False preserves the value."""
        config_path = tmp_path / "test_config.json"
        manager = PortfolioConfigManager(config_path)

        config = StrategyConfig(
            name="Test",
            file_path="/path/to/file.csv",
            column_mapping=PortfolioColumnMapping(
                date_col="date",
                gain_pct_col="gain",
            ),
            allow_multiple_entry=False,
        )
        manager.save([config], 100_000)

        strategies, _ = manager.load()
        assert strategies[0].allow_multiple_entry is False

    def test_save_and_load_preserves_allow_multiple_entry_true(self, tmp_path):
        """Saving and loading config with allow_multiple_entry=True preserves the value."""
        config_path = tmp_path / "test_config.json"
        manager = PortfolioConfigManager(config_path)

        config = StrategyConfig(
            name="Test",
            file_path="/path/to/file.csv",
            column_mapping=PortfolioColumnMapping(
                date_col="date",
                gain_pct_col="gain",
            ),
            allow_multiple_entry=True,
        )
        manager.save([config], 100_000)

        strategies, _ = manager.load()
        assert strategies[0].allow_multiple_entry is True

    def test_saves_allow_multiple_entry_to_json(self, tmp_path):
        """The allow_multiple_entry field should be written to the JSON file."""
        config_path = tmp_path / "test_config.json"
        manager = PortfolioConfigManager(config_path)

        config = StrategyConfig(
            name="Test",
            file_path="/path/to/file.csv",
            column_mapping=PortfolioColumnMapping(
                date_col="date",
                gain_pct_col="gain",
            ),
            allow_multiple_entry=False,
        )
        manager.save([config], 100_000)

        with open(config_path) as f:
            data = json.load(f)

        assert data["strategies"][0]["allow_multiple_entry"] is False


def test_portfolio_overview_accepts_config_manager(tmp_path):
    """PortfolioOverviewTab should accept injected config manager."""
    from PyQt6.QtWidgets import QApplication
    from src.tabs.portfolio_overview import PortfolioOverviewTab
    from src.core.app_state import AppState
    from src.core.portfolio_config_manager import PortfolioConfigManager

    app = QApplication.instance() or QApplication([])
    config_file = tmp_path / "test_portfolio_config.json"
    config_manager = PortfolioConfigManager(config_file)
    app_state = AppState()

    # This should work without error
    tab = PortfolioOverviewTab(app_state, config_manager=config_manager)
    assert tab._config_manager._config_path == config_file
