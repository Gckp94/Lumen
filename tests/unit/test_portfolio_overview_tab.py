# tests/unit/test_portfolio_overview_tab.py
"""Unit tests for PortfolioOverviewTab widget."""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
from src.tabs.portfolio_overview import PortfolioOverviewTab
from src.core.app_state import AppState


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def mock_app_state():
    state = MagicMock(spec=AppState)
    return state


class TestPortfolioOverviewTab:
    def test_tab_creates_successfully(self, app, qtbot, mock_app_state):
        tab = PortfolioOverviewTab(mock_app_state)
        qtbot.addWidget(tab)
        assert tab is not None

    def test_tab_has_add_strategy_button(self, app, qtbot, mock_app_state):
        tab = PortfolioOverviewTab(mock_app_state)
        qtbot.addWidget(tab)
        assert tab._add_strategy_btn is not None

    def test_tab_has_account_start_input(self, app, qtbot, mock_app_state):
        tab = PortfolioOverviewTab(mock_app_state)
        qtbot.addWidget(tab)
        assert tab._account_start_spin is not None
        assert tab._account_start_spin.value() == 100_000

    def test_tab_has_strategy_table(self, app, qtbot, mock_app_state):
        tab = PortfolioOverviewTab(mock_app_state)
        qtbot.addWidget(tab)
        assert tab._strategy_table is not None

    def test_tab_has_charts(self, app, qtbot, mock_app_state):
        tab = PortfolioOverviewTab(mock_app_state)
        qtbot.addWidget(tab)
        assert tab._charts is not None

    def test_debounce_timer_configured_correctly(self, app, qtbot, mock_app_state):
        """Verify timer is configured with 300ms debounce."""
        tab = PortfolioOverviewTab(mock_app_state)
        qtbot.addWidget(tab)
        # Timer should be single shot
        assert tab._recalc_timer.isSingleShot()
        # Start the timer to verify interval is set correctly
        tab._schedule_recalculation()
        assert tab._recalc_timer.interval() == 300

    def test_schedule_recalculation_starts_timer(self, app, qtbot, mock_app_state):
        """Verify schedule_recalculation starts the debounce timer."""
        tab = PortfolioOverviewTab(mock_app_state)
        qtbot.addWidget(tab)
        tab._schedule_recalculation()
        assert tab._recalc_timer.isActive()

    def test_recalculate_updates_charts(self, app, qtbot, mock_app_state, isolated_config_manager):
        """Verify recalculation updates charts with data."""
        import pandas as pd
        from src.core.portfolio_models import PortfolioColumnMapping, StrategyConfig

        tab = PortfolioOverviewTab(mock_app_state, config_manager=isolated_config_manager)
        qtbot.addWidget(tab)

        # Add a mock strategy with data
        config = StrategyConfig(
            name="Test",
            file_path="test.csv",
            column_mapping=PortfolioColumnMapping("date", "gain_pct"),
        )
        tab._strategy_data["Test"] = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01"]),
            "gain_pct": [5.0],
        })
        tab._strategy_table.add_strategy(config)

        # Trigger recalculation directly
        tab._recalculate()

        # Charts should have data
        assert len(tab._charts._data) > 0

    def test_is_data_loaded_returns_false_for_unloaded_strategy(self, app, qtbot, mock_app_state, isolated_config_manager):
        """Verify is_data_loaded returns False when strategy data not loaded."""
        tab = PortfolioOverviewTab(mock_app_state, config_manager=isolated_config_manager)
        qtbot.addWidget(tab)

        assert tab.is_data_loaded("NonExistent") is False

    def test_is_data_loaded_returns_true_for_loaded_strategy(self, app, qtbot, mock_app_state, isolated_config_manager):
        """Verify is_data_loaded returns True when strategy data is loaded."""
        import pandas as pd
        tab = PortfolioOverviewTab(mock_app_state, config_manager=isolated_config_manager)
        qtbot.addWidget(tab)

        tab._strategy_data["TestStrategy"] = pd.DataFrame({"col": [1]})

        assert tab.is_data_loaded("TestStrategy") is True

    def test_update_row_loaded_state_dims_unloaded_rows(self, app, qtbot, mock_app_state, isolated_config_manager):
        """Verify unloaded rows have dimmed name cell."""
        from src.core.portfolio_models import StrategyConfig, PortfolioColumnMapping
        from src.ui.constants import Colors
        from PyQt6.QtGui import QColor

        tab = PortfolioOverviewTab(mock_app_state, config_manager=isolated_config_manager)
        qtbot.addWidget(tab)

        config = StrategyConfig(
            name="Test",
            file_path="test.csv",
            column_mapping=PortfolioColumnMapping("date", "gain"),
        )
        tab._strategy_table.add_strategy(config)
        tab._update_row_loaded_state("Test", loaded=False)

        name_item = tab._strategy_table.item(0, 0)
        assert name_item.foreground().color() == QColor(Colors.TEXT_DISABLED)

    def test_update_row_loaded_state_normal_for_loaded_rows(self, app, qtbot, mock_app_state, isolated_config_manager):
        """Verify loaded rows have normal name cell color."""
        from src.core.portfolio_models import StrategyConfig, PortfolioColumnMapping
        from src.ui.constants import Colors
        from PyQt6.QtGui import QColor

        tab = PortfolioOverviewTab(mock_app_state, config_manager=isolated_config_manager)
        qtbot.addWidget(tab)

        config = StrategyConfig(
            name="Test",
            file_path="test.csv",
            column_mapping=PortfolioColumnMapping("date", "gain"),
        )
        tab._strategy_table.add_strategy(config)
        tab._update_row_loaded_state("Test", loaded=True)

        name_item = tab._strategy_table.item(0, 0)
        assert name_item.foreground().color() == QColor(Colors.TEXT_PRIMARY)

    def test_load_strategy_data_loads_csv_file(self, app, qtbot, mock_app_state, isolated_config_manager, tmp_path):
        """Verify load_strategy_data loads CSV and updates state."""
        import pandas as pd
        from src.core.portfolio_models import StrategyConfig, PortfolioColumnMapping

        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame({"date": ["2024-01-01"], "gain": [5.0], "wl": ["W"]})
        df.to_csv(csv_path, index=False)

        tab = PortfolioOverviewTab(mock_app_state, config_manager=isolated_config_manager)
        qtbot.addWidget(tab)

        config = StrategyConfig(
            name="Test",
            file_path=str(csv_path),
            column_mapping=PortfolioColumnMapping("date", "gain"),
        )
        tab._strategy_table.add_strategy(config)

        success = tab.load_strategy_data("Test")

        assert success is True
        assert tab.is_data_loaded("Test") is True

    def test_load_strategy_data_returns_false_for_missing_file(self, app, qtbot, mock_app_state, isolated_config_manager):
        """Verify load_strategy_data returns False when file doesn't exist."""
        from src.core.portfolio_models import StrategyConfig, PortfolioColumnMapping

        tab = PortfolioOverviewTab(mock_app_state, config_manager=isolated_config_manager)
        qtbot.addWidget(tab)

        config = StrategyConfig(
            name="Test",
            file_path="/nonexistent/file.csv",
            column_mapping=PortfolioColumnMapping("date", "gain"),
        )
        tab._strategy_table.add_strategy(config)

        success = tab.load_strategy_data("Test")

        assert success is False
        assert tab.is_data_loaded("Test") is False

    def test_load_data_signal_triggers_data_loading(self, app, qtbot, mock_app_state, isolated_config_manager, tmp_path):
        """Verify Load Data signal triggers data loading."""
        import pandas as pd
        from src.core.portfolio_models import StrategyConfig, PortfolioColumnMapping

        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame({"date": ["2024-01-01"], "gain": [5.0], "wl": ["W"]})
        df.to_csv(csv_path, index=False)

        tab = PortfolioOverviewTab(mock_app_state, config_manager=isolated_config_manager)
        qtbot.addWidget(tab)

        config = StrategyConfig(
            name="Test",
            file_path=str(csv_path),
            column_mapping=PortfolioColumnMapping("date", "gain"),
        )
        tab._strategy_table.add_strategy(config)

        # Emit signal (simulating menu click)
        tab._strategy_table.load_data_requested.emit("Test")

        assert tab.is_data_loaded("Test") is True

    def test_load_saved_config_does_not_load_data_files(self, app, qtbot, mock_app_state, tmp_path):
        """Verify startup loads configs but not data files (lazy loading)."""
        from src.core.portfolio_config_manager import PortfolioConfigManager
        from src.core.portfolio_models import StrategyConfig, PortfolioColumnMapping

        config_manager = PortfolioConfigManager(tmp_path / "config.json")
        config = StrategyConfig(
            name="TestStrategy",
            file_path="/nonexistent/file.csv",
            column_mapping=PortfolioColumnMapping("date", "gain"),
        )
        config_manager.save([config], 100_000)

        # Should NOT fail even though file doesn't exist
        tab = PortfolioOverviewTab(mock_app_state, config_manager=config_manager)
        qtbot.addWidget(tab)

        assert tab._strategy_table.rowCount() == 1
        assert tab.is_data_loaded("TestStrategy") is False
