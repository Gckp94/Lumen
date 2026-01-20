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
