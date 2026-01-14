"""Tests for FeatureExplorerTab axis column selection."""

import pandas as pd
import pytest
from pytestqt.qtbot import QtBot
from unittest.mock import patch

from src.core.app_state import AppState
from src.tabs.feature_explorer import FeatureExplorerTab
from src.ui.components.axis_column_selector import AxisColumnSelector


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

    def test_axis_selector_present(self, qtbot: QtBot, app_state: AppState) -> None:
        """FeatureExplorerTab has AxisColumnSelector in sidebar."""
        tab = FeatureExplorerTab(app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_axis_selector")
        assert isinstance(tab._axis_selector, AxisColumnSelector)

    def test_x_column_passed_to_chart(
        self, qtbot: QtBot, app_state: AppState
    ) -> None:
        """Selected X column is passed to chart update."""
        tab = FeatureExplorerTab(app_state)
        qtbot.addWidget(tab)

        # Set columns and select
        tab._axis_selector.set_columns(["feature_a", "feature_b", "pnl"])
        tab._axis_selector._x_combo.setCurrentText("feature_a")
        tab._axis_selector._y_combo.setCurrentText("pnl")

        with patch.object(tab._chart_canvas, "update_data") as mock_update:
            tab._update_chart()
            mock_update.assert_called_once()
            kwargs = mock_update.call_args.kwargs
            assert kwargs.get("x_column") == "feature_a"
            assert kwargs.get("y_column") == "pnl"

    def test_update_chart_passes_y_column(
        self, qtbot: QtBot, app_state: AppState
    ) -> None:
        """_update_chart passes y_column parameter to ChartCanvas."""
        tab = FeatureExplorerTab(app_state)
        qtbot.addWidget(tab)

        # Set columns and select pnl for Y axis
        tab._axis_selector.set_columns(["feature_a", "pnl"])
        tab._axis_selector._y_combo.setCurrentText("pnl")

        with patch.object(tab._chart_canvas, "update_data") as mock_update:
            tab._update_chart()
            mock_update.assert_called_once()
            call_kwargs = mock_update.call_args
            assert call_kwargs.kwargs.get("y_column") == "pnl"

    def test_index_x_column_passed_as_none(
        self, qtbot: QtBot, app_state: AppState
    ) -> None:
        """When X is set to (Index), x_column should be None."""
        tab = FeatureExplorerTab(app_state)
        qtbot.addWidget(tab)

        # Set columns and keep X at (Index) default
        tab._axis_selector.set_columns(["feature_a", "feature_b", "pnl"])
        tab._axis_selector._y_combo.setCurrentText("pnl")
        # X combo should default to (Index)

        with patch.object(tab._chart_canvas, "update_data") as mock_update:
            tab._update_chart()
            mock_update.assert_called_once()
            kwargs = mock_update.call_args.kwargs
            assert kwargs.get("x_column") is None
            assert kwargs.get("y_column") == "pnl"
