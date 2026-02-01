"""Tests for strategy name synchronization in portfolio overview."""

import pandas as pd
import pytest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication

from src.core.app_state import AppState
from src.core.portfolio_models import PortfolioColumnMapping, StrategyConfig
from src.tabs.portfolio_overview import PortfolioOverviewTab


@pytest.fixture(scope="module")
def app():
    """Create QApplication for tests."""
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def mock_app_state():
    """Create a mock AppState."""
    return MagicMock(spec=AppState)


@pytest.fixture
def sample_strategy_df():
    """Create a sample strategy DataFrame."""
    return pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
        "gain_pct": [0.05, -0.02, 0.03],
    })


class TestStrategyNameSync:
    """Tests for strategy name synchronization."""

    def test_on_strategy_name_changed_updates_key(self, app, qtbot, mock_app_state, sample_strategy_df):
        """Test that _on_strategy_name_changed updates _strategy_data key."""
        tab = PortfolioOverviewTab(mock_app_state)
        qtbot.addWidget(tab)

        # Set up initial state
        tab._strategy_data = {"OldName": sample_strategy_df}

        # Simulate name change
        tab._on_strategy_name_changed("OldName", "NewName")

        # Verify key was updated
        assert "NewName" in tab._strategy_data
        assert "OldName" not in tab._strategy_data
        assert tab._strategy_data["NewName"].equals(sample_strategy_df)

    def test_on_strategy_name_changed_handles_missing_key(self, app, qtbot, mock_app_state):
        """Test that _on_strategy_name_changed handles missing old key gracefully."""
        tab = PortfolioOverviewTab(mock_app_state)
        qtbot.addWidget(tab)

        # Set up empty state
        tab._strategy_data = {}

        # Should not raise, just log warning
        tab._on_strategy_name_changed("NonExistent", "NewName")

        # Verify no crash and no key added
        assert "NewName" not in tab._strategy_data

    def test_on_strategy_name_changed_preserves_other_keys(self, app, qtbot, mock_app_state, sample_strategy_df):
        """Test that renaming one strategy doesn't affect other strategies."""
        tab = PortfolioOverviewTab(mock_app_state)
        qtbot.addWidget(tab)

        other_df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01"]),
            "gain_pct": [0.10],
        })

        # Set up state with multiple strategies
        tab._strategy_data = {
            "Strategy1": sample_strategy_df,
            "Strategy2": other_df,
        }

        # Rename Strategy1
        tab._on_strategy_name_changed("Strategy1", "RenamedStrategy")

        # Verify Strategy1 was renamed
        assert "RenamedStrategy" in tab._strategy_data
        assert "Strategy1" not in tab._strategy_data

        # Verify Strategy2 is unchanged
        assert "Strategy2" in tab._strategy_data
        assert tab._strategy_data["Strategy2"].equals(other_df)
