"""Unit tests for SweepChart component."""

import numpy as np
import pytest
from pytestqt.qtbot import QtBot

from src.ui.components.sweep_chart import SweepChart


class TestSweepChart1D:
    """Tests for 1D sweep visualization."""

    def test_create_chart(self, qtbot: QtBot):
        """Chart widget can be created."""
        chart = SweepChart()
        qtbot.addWidget(chart)
        assert chart is not None

    def test_set_1d_data(self, qtbot: QtBot):
        """Can set 1D sweep data."""
        chart = SweepChart()
        qtbot.addWidget(chart)

        x_values = np.linspace(0, 10, 10)
        y_values = np.array([0.5, 0.52, 0.55, 0.58, 0.60, 0.58, 0.55, 0.52, 0.50, 0.48])

        chart.set_1d_data(
            x_values=x_values,
            y_values=y_values,
            x_label="change_from_prev_close_pct",
            y_label="win_rate",
        )

        assert chart._is_2d is False
        assert chart._x_values is not None
        assert len(chart._x_values) == 10

    def test_set_current_position_1d(self, qtbot: QtBot):
        """Can mark current filter position on 1D chart."""
        chart = SweepChart()
        qtbot.addWidget(chart)

        x_values = np.linspace(0, 10, 10)
        y_values = np.array([0.5, 0.52, 0.55, 0.58, 0.60, 0.58, 0.55, 0.52, 0.50, 0.48])

        chart.set_1d_data(x_values, y_values, "filter", "metric")
        chart.set_current_position(x_index=4)

        assert chart._current_marker is not None
        x_data, y_data = chart._current_marker.getData()
        assert len(x_data) == 1
        assert x_data[0] == x_values[4]
        assert y_data[0] == y_values[4]

    def test_clear(self, qtbot: QtBot):
        """Clear method resets all data."""
        chart = SweepChart()
        qtbot.addWidget(chart)

        x_values = np.linspace(0, 10, 10)
        y_values = np.array([0.5, 0.52, 0.55, 0.58, 0.60, 0.58, 0.55, 0.52, 0.50, 0.48])

        chart.set_1d_data(x_values, y_values, "filter", "metric")
        chart.clear()

        assert chart._x_values is None
        assert chart._y_values is None


class TestSweepChart2D:
    """Tests for 2D sweep heatmap visualization."""

    def test_set_2d_data(self, qtbot: QtBot):
        """Can set 2D sweep data."""
        chart = SweepChart()
        qtbot.addWidget(chart)

        x_values = np.linspace(0, 10, 5)
        y_values = np.linspace(0, 5, 4)
        z_values = np.random.rand(4, 5)  # Shape: (len(y), len(x))

        chart.set_2d_data(
            x_values=x_values,
            y_values=y_values,
            z_values=z_values,
            x_label="filter_1",
            y_label="filter_2",
            z_label="win_rate",
        )

        assert chart._is_2d is True
        assert chart._z_values is not None
        assert chart._z_values.shape == (4, 5)

    def test_set_current_position_2d(self, qtbot: QtBot):
        """Can mark current filter position on 2D heatmap."""
        chart = SweepChart()
        qtbot.addWidget(chart)

        x_values = np.linspace(0, 10, 5)
        y_values = np.linspace(0, 5, 4)
        z_values = np.random.rand(4, 5)

        chart.set_2d_data(x_values, y_values, z_values, "f1", "f2", "metric")
        chart.set_current_position(x_index=2, y_index=1)

        assert chart._current_marker is not None
        x_data, y_data = chart._current_marker.getData()
        assert len(x_data) == 1
        assert x_data[0] == x_values[2]
        assert y_data[0] == y_values[1]
