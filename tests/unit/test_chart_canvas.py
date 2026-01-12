"""Unit tests for ChartCanvas component."""

import numpy as np
import pandas as pd
import pytest
from PyQt6.QtCore import Qt

from src.ui.components.chart_canvas import ChartCanvas


class TestChartCanvasUpdateData:
    """Tests for ChartCanvas.update_data() method."""

    def test_update_data_sets_scatter_plot_correctly(self, qtbot):
        """ChartCanvas displays data correctly."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0, 4.0, 5.0]})
        canvas.update_data(df, "gain_pct")

        # Verify scatter plot has 5 points
        assert canvas._scatter.data is not None
        assert len(canvas._scatter.data) == 5

    def test_update_data_handles_empty_dataframe(self, qtbot):
        """ChartCanvas handles empty DataFrame gracefully."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        df = pd.DataFrame(columns=["gain_pct"])
        canvas.update_data(df, "gain_pct")

        # Should not raise, scatter should be empty
        assert len(canvas._scatter.data) == 0 or canvas._scatter.data is None

    def test_update_data_handles_single_point(self, qtbot):
        """ChartCanvas handles single data point."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        df = pd.DataFrame({"gain_pct": [1.5]})
        canvas.update_data(df, "gain_pct")

        assert len(canvas._scatter.data) == 1

    def test_update_data_handles_none_dataframe(self, qtbot):
        """ChartCanvas handles None DataFrame gracefully."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        canvas.update_data(None, "gain_pct")

        # Should clear the data without raising
        assert len(canvas._scatter.data) == 0 or canvas._scatter.data is None

    def test_update_data_handles_missing_column(self, qtbot):
        """ChartCanvas handles missing column gracefully."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0]})
        canvas.update_data(df, "nonexistent_column")

        # Should clear the data without raising
        assert len(canvas._scatter.data) == 0 or canvas._scatter.data is None

    def test_update_data_preserves_x_as_index(self, qtbot):
        """ChartCanvas uses index as x-axis values."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        df = pd.DataFrame({"gain_pct": [10.0, 20.0, 30.0]})
        canvas.update_data(df, "gain_pct")

        # X values should be 0, 1, 2 (indices)
        data = canvas._scatter.data
        x_values = [point[0] for point in data]
        assert x_values == [0, 1, 2]


class TestChartCanvasLargeDataset:
    """Tests for ChartCanvas performance with large datasets."""

    @pytest.mark.slow
    def test_handles_100k_points_without_error(self, qtbot):
        """ChartCanvas handles 100k+ points."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        np.random.seed(42)
        df = pd.DataFrame({"gain_pct": np.random.normal(0.5, 3, 100_000)})

        # Should not raise or hang
        canvas.update_data(df, "gain_pct")

        assert len(canvas._scatter.data) == 100_000


class TestChartCanvasClear:
    """Tests for ChartCanvas.clear() method."""

    def test_clear_removes_all_data(self, qtbot):
        """ChartCanvas.clear() removes all data points."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        # Add some data
        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0]})
        canvas.update_data(df, "gain_pct")
        assert len(canvas._scatter.data) == 3

        # Clear
        canvas.clear()
        assert len(canvas._scatter.data) == 0 or canvas._scatter.data is None


class TestChartCanvasSignals:
    """Tests for ChartCanvas signals."""

    def test_render_failed_signal_exists(self, qtbot):
        """ChartCanvas has render_failed signal."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        # Signal should exist
        assert hasattr(canvas, "render_failed")

    def test_point_clicked_signal_exists(self, qtbot):
        """ChartCanvas has point_clicked signal."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        # Signal should exist
        assert hasattr(canvas, "point_clicked")

    def test_range_changed_signal_exists(self, qtbot):
        """ChartCanvas has range_changed signal."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        assert hasattr(canvas, "range_changed")

    def test_view_reset_signal_exists(self, qtbot):
        """ChartCanvas has view_reset signal."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        assert hasattr(canvas, "view_reset")


class TestChartCanvasCrosshair:
    """Tests for ChartCanvas crosshair functionality."""

    def test_crosshair_lines_created(self, qtbot):
        """Crosshair lines are created on initialization."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        assert hasattr(canvas, "_crosshair_v")
        assert hasattr(canvas, "_crosshair_h")
        assert canvas._crosshair_v is not None
        assert canvas._crosshair_h is not None

    def test_crosshair_lines_styled_correctly(self, qtbot):
        """Crosshair lines have correct dashed style."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        # Verify dashed line style
        assert canvas._crosshair_v.pen.style() == Qt.PenStyle.DashLine
        assert canvas._crosshair_h.pen.style() == Qt.PenStyle.DashLine

    def test_crosshair_hidden_initially(self, qtbot):
        """Crosshair is hidden until mouse enters chart area."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        assert not canvas._crosshair_v.isVisible()
        assert not canvas._crosshair_h.isVisible()

    def test_coordinate_label_created(self, qtbot):
        """Coordinate label is created on initialization."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        assert hasattr(canvas, "_coord_label")
        assert canvas._coord_label is not None

    def test_coordinate_label_hidden_initially(self, qtbot):
        """Coordinate label is hidden until mouse enters chart area."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        assert not canvas._coord_label.isVisible()


class TestChartCanvasGrid:
    """Tests for ChartCanvas grid functionality."""

    def test_grid_off_by_default(self, qtbot):
        """Grid is off by default."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        assert canvas._show_grid is False

    def test_set_grid_visible_true(self, qtbot):
        """set_grid_visible(True) enables grid."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        canvas.set_grid_visible(True)

        assert canvas._show_grid is True

    def test_set_grid_visible_false(self, qtbot):
        """set_grid_visible(False) disables grid."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        canvas.set_grid_visible(True)
        canvas.set_grid_visible(False)

        assert canvas._show_grid is False


class TestChartCanvasRangeMethods:
    """Tests for ChartCanvas range control methods."""

    def test_set_range_method_exists(self, qtbot):
        """ChartCanvas has set_range method."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        assert hasattr(canvas, "set_range")
        assert callable(canvas.set_range)

    def test_auto_range_method_exists(self, qtbot):
        """ChartCanvas has auto_range method."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        assert hasattr(canvas, "auto_range")
        assert callable(canvas.auto_range)

    def test_get_view_range_method_exists(self, qtbot):
        """ChartCanvas has get_view_range method."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        assert hasattr(canvas, "get_view_range")
        assert callable(canvas.get_view_range)

    def test_auto_range_emits_view_reset(self, qtbot):
        """auto_range() emits view_reset signal."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        # Add some data first
        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0]})
        canvas.update_data(df, "gain_pct")

        with qtbot.waitSignal(canvas.view_reset, timeout=1000):
            canvas.auto_range()


class TestChartCanvasInteractions:
    """Tests for ChartCanvas interaction setup."""

    def test_viewbox_pan_mode_enabled(self, qtbot):
        """ViewBox is set to PanMode for left-drag panning."""
        import pyqtgraph as pg

        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        viewbox = canvas._plot_widget.getViewBox()
        assert viewbox.state["mouseMode"] == pg.ViewBox.PanMode

    def test_viewbox_menu_disabled(self, qtbot):
        """ViewBox context menu is disabled for right-click zoom."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        viewbox = canvas._plot_widget.getViewBox()
        assert viewbox.menuEnabled() is False

    def test_scatter_optimized_for_performance(self, qtbot):
        """Scatter plot is configured for performance."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        # Check that scatter uses small point size (3px) for performance
        assert canvas._scatter.opts.get("size", 0) == 3
