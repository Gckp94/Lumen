# tests/unit/test_portfolio_overview_startup.py
"""Tests for portfolio overview startup behavior."""
import json
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication

from src.core.app_state import AppState
from src.core.portfolio_config_manager import PortfolioConfigManager
from src.tabs.portfolio_overview import PortfolioOverviewTab


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for widget tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestPortfolioOverviewStartup:
    """Test startup behavior with missing files."""

    def test_skips_strategies_with_missing_files(self, tmp_path, qapp, qtbot):
        """Strategies with non-existent files should be skipped entirely."""
        # Create config with a strategy pointing to non-existent file
        config_file = tmp_path / "portfolio_config.json"
        config_data = {
            "account_start": 100000,
            "strategies": [
                {
                    "name": "MissingFile",
                    "file_path": str(tmp_path / "nonexistent.csv"),
                    "column_mapping": {
                        "date_col": "date",
                        "gain_pct_col": "gain_pct",
                    },
                }
            ],
        }
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config_manager = PortfolioConfigManager(config_file)
        app_state = AppState()

        tab = PortfolioOverviewTab(app_state, config_manager=config_manager)
        qtbot.addWidget(tab)

        # Strategy should NOT be added to table if file doesn't exist
        assert tab._strategy_table.rowCount() == 0
        assert len(tab._strategy_data) == 0

    def test_loads_strategies_with_existing_files(self, tmp_path, qapp, qtbot):
        """Strategies with valid files should be loaded normally."""
        # Create a valid CSV file
        csv_file = tmp_path / "valid.csv"
        csv_file.write_text("date,gain_pct\n2024-01-01,1.5\n2024-01-02,-0.5\n")

        config_file = tmp_path / "portfolio_config.json"
        config_data = {
            "account_start": 100000,
            "strategies": [
                {
                    "name": "ValidStrategy",
                    "file_path": str(csv_file),
                    "column_mapping": {
                        "date_col": "date",
                        "gain_pct_col": "gain_pct",
                    },
                }
            ],
        }
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config_manager = PortfolioConfigManager(config_file)
        app_state = AppState()

        tab = PortfolioOverviewTab(app_state, config_manager=config_manager)
        qtbot.addWidget(tab)

        # Strategy should be added with data
        assert tab._strategy_table.rowCount() == 1
        assert "ValidStrategy" in tab._strategy_data
        assert len(tab._strategy_data["ValidStrategy"]) == 2

    def test_cleans_up_config_when_invalid_entries_removed(self, tmp_path, qapp, qtbot):
        """Config should be saved without invalid strategies after cleanup."""
        # Create config with one valid and one invalid strategy
        csv_file = tmp_path / "valid.csv"
        csv_file.write_text("date,gain_pct\n2024-01-01,1.5\n")

        config_file = tmp_path / "portfolio_config.json"
        config_data = {
            "account_start": 100000,
            "strategies": [
                {
                    "name": "ValidStrategy",
                    "file_path": str(csv_file),
                    "column_mapping": {
                        "date_col": "date",
                        "gain_pct_col": "gain_pct",
                    },
                },
                {
                    "name": "MissingFile",
                    "file_path": str(tmp_path / "nonexistent.csv"),
                    "column_mapping": {
                        "date_col": "date",
                        "gain_pct_col": "gain_pct",
                    },
                },
            ],
        }
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config_manager = PortfolioConfigManager(config_file)
        app_state = AppState()

        tab = PortfolioOverviewTab(app_state, config_manager=config_manager)
        qtbot.addWidget(tab)

        # Only valid strategy should be loaded
        assert tab._strategy_table.rowCount() == 1
        assert "ValidStrategy" in tab._strategy_data
        assert "MissingFile" not in tab._strategy_data

        # Config should be updated (reload and check)
        with open(config_file) as f:
            saved_config = json.load(f)

        assert len(saved_config["strategies"]) == 1
        assert saved_config["strategies"][0]["name"] == "ValidStrategy"
