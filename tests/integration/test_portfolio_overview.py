# tests/integration/test_portfolio_overview.py
import pytest
import pandas as pd
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from src.tabs.portfolio_overview import PortfolioOverviewTab
from src.core.app_state import AppState
from src.core.portfolio_models import StrategyConfig, PortfolioColumnMapping


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def sample_csv(tmp_path):
    """Create a sample CSV file for testing."""
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=10),
        "gain_pct": [2.5, -1.0, 3.0, -0.5, 4.0, 1.5, -2.0, 2.0, -1.5, 3.5],
        "wl": ["W", "L", "W", "L", "W", "W", "L", "W", "L", "W"],
    })
    csv_path = tmp_path / "test_strategy.csv"
    df.to_csv(csv_path, index=False)
    return csv_path


class TestPortfolioOverviewIntegration:
    def test_full_workflow(self, app, qtbot, sample_csv, tmp_path, isolated_config_manager):
        """Test adding strategy, configuring, and seeing charts update."""
        app_state = AppState()
        tab = PortfolioOverviewTab(app_state, config_manager=isolated_config_manager)
        qtbot.addWidget(tab)

        # Load CSV data directly (simulating import dialog)
        df = pd.read_csv(sample_csv)
        config = StrategyConfig(
            name="Test Strategy",
            file_path=str(sample_csv),
            column_mapping=PortfolioColumnMapping("date", "gain_pct", "wl"),
            is_baseline=True,
        )
        tab._strategy_data[config.name] = df
        tab._strategy_table.add_strategy(config)

        # Trigger recalculation
        tab._recalculate()

        # Verify charts have data
        assert "Test Strategy" in tab._charts._data
        assert len(tab._charts._data["Test Strategy"]) == 10

    def test_baseline_vs_combined_calculation(self, app, qtbot, tmp_path, isolated_config_manager):
        """Test that baseline and combined are calculated correctly."""
        # Create two CSV files
        df1 = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=5),
            "gain_pct": [5.0, 3.0, -2.0, 4.0, 1.0],
            "wl": ["W", "W", "L", "W", "W"],
        })
        df2 = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=5),
            "gain_pct": [2.0, -1.0, 3.0, 2.0, -1.0],
            "wl": ["W", "L", "W", "W", "L"],
        })

        csv1 = tmp_path / "strategy1.csv"
        csv2 = tmp_path / "strategy2.csv"
        df1.to_csv(csv1, index=False)
        df2.to_csv(csv2, index=False)

        app_state = AppState()
        tab = PortfolioOverviewTab(app_state, config_manager=isolated_config_manager)
        qtbot.addWidget(tab)

        # Add baseline strategy
        config1 = StrategyConfig(
            name="Baseline Strategy",
            file_path=str(csv1),
            column_mapping=PortfolioColumnMapping("date", "gain_pct", "wl"),
            is_baseline=True,
        )
        tab._strategy_data[config1.name] = df1
        tab._strategy_table.add_strategy(config1)

        # Add candidate strategy
        config2 = StrategyConfig(
            name="Candidate Strategy",
            file_path=str(csv2),
            column_mapping=PortfolioColumnMapping("date", "gain_pct", "wl"),
            is_candidate=True,
        )
        tab._strategy_data[config2.name] = df2
        tab._strategy_table.add_strategy(config2)

        # Trigger recalculation
        tab._recalculate()

        # Verify all expected series exist
        assert "Baseline Strategy" in tab._charts._data
        assert "Candidate Strategy" in tab._charts._data
        assert "baseline" in tab._charts._data
        assert "combined" in tab._charts._data
