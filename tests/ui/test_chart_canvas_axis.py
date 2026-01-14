"""Tests for ChartCanvas X/Y axis column selection."""

import numpy as np
import pandas as pd
import pytest
from pytestqt.qtbot import QtBot

from src.ui.components.chart_canvas import ChartCanvas


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Create sample DataFrame for testing."""
    return pd.DataFrame({
        "feature_a": [1.0, 2.0, 3.0, 4.0, 5.0],
        "feature_b": [10.0, 20.0, 30.0, 40.0, 50.0],
        "pnl": [0.1, -0.2, 0.3, -0.1, 0.2],
    })


class TestChartCanvasAxisSelection:
    """Tests for X/Y axis column selection in ChartCanvas."""

    def test_update_data_with_x_column(
        self, qtbot: QtBot, sample_df: pd.DataFrame
    ) -> None:
        """Chart plots specified x_column on X-axis."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        canvas.update_data(sample_df, y_column="pnl", x_column="feature_a")

        # Verify scatter data uses feature_a for X
        scatter_data = canvas._scatter.data
        assert scatter_data is not None
        np.testing.assert_array_equal(scatter_data["x"], sample_df["feature_a"].values)
        np.testing.assert_array_equal(scatter_data["y"], sample_df["pnl"].values)

    def test_update_data_without_x_column_uses_index(
        self, qtbot: QtBot, sample_df: pd.DataFrame
    ) -> None:
        """Without x_column, chart uses row index for X-axis (backward compatible)."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        canvas.update_data(sample_df, y_column="pnl")

        scatter_data = canvas._scatter.data
        assert scatter_data is not None
        np.testing.assert_array_equal(scatter_data["x"], np.arange(len(sample_df)))

    def test_x_axis_label_shows_column_name(
        self, qtbot: QtBot, sample_df: pd.DataFrame
    ) -> None:
        """X-axis label displays the selected column name."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        canvas.update_data(sample_df, y_column="pnl", x_column="feature_a")

        plot_item = canvas._plot_widget.getPlotItem()
        x_label = plot_item.getAxis("bottom").labelText
        assert x_label == "feature_a"

    def test_x_axis_label_shows_index_when_no_column(
        self, qtbot: QtBot, sample_df: pd.DataFrame
    ) -> None:
        """X-axis label shows 'Index' when using row index."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        canvas.update_data(sample_df, y_column="pnl")

        plot_item = canvas._plot_widget.getPlotItem()
        x_label = plot_item.getAxis("bottom").labelText
        assert x_label == "Index"

    def test_update_data_with_invalid_x_column_clears_chart(
        self, qtbot: QtBot, sample_df: pd.DataFrame
    ) -> None:
        """Chart clears when x_column doesn't exist in DataFrame."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        canvas.update_data(sample_df, y_column="pnl", x_column="nonexistent")

        scatter_data = canvas._scatter.data
        assert len(scatter_data) == 0
