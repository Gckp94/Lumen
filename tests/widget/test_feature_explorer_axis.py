"""Tests for FeatureExplorerTab axis column selection."""

import pandas as pd
import pytest
from pytestqt.qtbot import QtBot
from unittest.mock import MagicMock, patch

from src.core.app_state import AppState
from src.tabs.feature_explorer import FeatureExplorerTab


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Create sample DataFrame for testing."""
    return pd.DataFrame({
        "feature_a": [1.0, 2.0, 3.0],
        "feature_b": [10.0, 20.0, 30.0],
        "pnl": [0.1, -0.2, 0.3],
    })


@pytest.fixture
def app_state(sample_df: pd.DataFrame) -> AppState:
    """Create AppState with sample data."""
    state = AppState()
    state.baseline_df = sample_df
    state.filtered_df = sample_df
    return state


class TestFeatureExplorerAxisSelection:
    """Tests for X/Y column selection in FeatureExplorerTab."""

    def test_update_chart_passes_y_column(
        self, qtbot: QtBot, app_state: AppState
    ) -> None:
        """_update_chart passes y_column parameter to ChartCanvas."""
        tab = FeatureExplorerTab(app_state)
        qtbot.addWidget(tab)

        # Simulate column selection
        tab._column_selector.addItems(["feature_a", "pnl"])
        tab._column_selector.setCurrentText("pnl")

        with patch.object(tab._chart_canvas, "update_data") as mock_update:
            tab._update_chart()
            mock_update.assert_called_once()
            call_kwargs = mock_update.call_args
            assert call_kwargs.kwargs.get("y_column") == "pnl" or call_kwargs.args[1] == "pnl"
