"""Widget tests for ChartCanvas interactions."""

import pandas as pd
from PyQt6.QtCore import Qt

from src.ui.components.chart_canvas import ChartCanvas


class TestChartCanvasDoubleClick:
    """Tests for double-click reset behavior."""

    def test_double_click_resets_view(self, qtbot, sample_trades):
        """Double-click resets chart to auto-range."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)
        canvas.update_data(sample_trades, "gain_pct")
        canvas.show()
        qtbot.waitExposed(canvas)

        # Zoom in manually
        viewbox = canvas._plot_widget.getViewBox()
        viewbox.setRange(xRange=(0, 2), yRange=(0, 5))

        # Verify zoomed in
        x_range_before = viewbox.viewRange()[0]
        assert x_range_before[1] < len(sample_trades)

        # Double-click should reset view
        with qtbot.waitSignal(canvas.view_reset, timeout=1000):
            qtbot.mouseDClick(canvas, Qt.MouseButton.LeftButton)

        # View should have expanded
        x_range_after = viewbox.viewRange()[0]
        assert x_range_after[1] > x_range_before[1]

    def test_double_click_emits_view_reset_signal(self, qtbot):
        """Double-click emits view_reset signal."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0, 4.0, 5.0]})
        canvas.update_data(df, "gain_pct")
        canvas.show()
        qtbot.waitExposed(canvas)

        with qtbot.waitSignal(canvas.view_reset, timeout=1000):
            qtbot.mouseDClick(canvas, Qt.MouseButton.LeftButton)


class TestChartCanvasGridToggle:
    """Tests for grid toggle integration."""

    def test_grid_toggle_updates_internal_state(self, qtbot):
        """set_grid_visible() updates internal _show_grid state."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        # Grid off by default
        assert canvas._show_grid is False

        canvas.set_grid_visible(True)
        assert canvas._show_grid is True

        canvas.set_grid_visible(False)
        assert canvas._show_grid is False


class TestChartCanvasRangeSync:
    """Tests for chart range synchronization."""

    def test_range_changed_signal_emitted_on_zoom(self, qtbot):
        """range_changed signal is emitted when view range changes."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0, 4.0, 5.0]})
        canvas.update_data(df, "gain_pct")
        canvas.show()
        qtbot.waitExposed(canvas)

        received_values = []

        def on_range_changed(x_min, x_max, y_min, y_max):
            received_values.append((x_min, x_max, y_min, y_max))

        canvas.range_changed.connect(on_range_changed)

        # Change range programmatically
        canvas.set_range(0, 10, -5, 5)

        # Should have received signal
        assert len(received_values) > 0

    def test_set_range_updates_viewbox(self, qtbot):
        """set_range() updates the ViewBox range."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0, 4.0, 5.0]})
        canvas.update_data(df, "gain_pct")
        canvas.show()
        qtbot.waitExposed(canvas)

        canvas.set_range(10, 50, -20, 20)

        # Allow Qt to process
        qtbot.wait(50)

        view_range = canvas._plot_widget.viewRange()
        # ViewBox may adjust slightly, but should be close to requested
        assert abs(view_range[0][0] - 10) < 5
        assert abs(view_range[0][1] - 50) < 5


class TestChartCanvasMouseInteractions:
    """Tests for mouse interaction setup."""

    def test_zoom_rect_none_initially(self, qtbot):
        """Zoom rectangle is None initially."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        assert canvas._zoom_rect is None
        assert canvas._zoom_start is None

    def test_crosshair_hidden_when_no_data(self, qtbot):
        """Crosshair remains hidden when no data is loaded."""
        canvas = ChartCanvas()
        qtbot.addWidget(canvas)
        canvas.show()
        qtbot.waitExposed(canvas)

        assert not canvas._crosshair_v.isVisible()
        assert not canvas._crosshair_h.isVisible()
        assert not canvas._coord_label.isVisible()


class TestChartCanvas:
    """Tests for ChartCanvas configuration."""

    def test_axes_use_abbreviated_format(self, qtbot) -> None:
        """Chart axes should display K/M/B abbreviations instead of scientific notation."""
        from src.ui.components.abbreviated_axis import AbbreviatedAxisItem

        canvas = ChartCanvas()
        qtbot.addWidget(canvas)

        # Verify both axes are AbbreviatedAxisItem instances
        plot_item = canvas._plot_widget.getPlotItem()
        left_axis = plot_item.getAxis("left")
        bottom_axis = plot_item.getAxis("bottom")

        assert isinstance(left_axis, AbbreviatedAxisItem)
        assert isinstance(bottom_axis, AbbreviatedAxisItem)
