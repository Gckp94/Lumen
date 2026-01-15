"""Widget tests for EquityChart component."""

import numpy as np
import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from src.ui.components.equity_chart import EquityChart, _ChartPanel
from src.ui.constants import Colors


def create_equity_df(n_points: int = 100) -> pd.DataFrame:
    """Create sample equity curve DataFrame for testing."""
    np.random.seed(42)
    pnl = np.random.normal(50, 100, n_points)
    equity = 10000 + np.cumsum(pnl)
    peak = np.maximum.accumulate(equity)
    return pd.DataFrame({
        "trade_num": np.arange(1, n_points + 1),
        "pnl": pnl,
        "equity": equity,
        "peak": peak,
        "drawdown": equity - peak,
    })


class TestEquityChartCurveColors:
    """Tests for EquityChart curve colors."""

    def test_baseline_curve_uses_signal_blue(self, qtbot):
        """Baseline curve uses SIGNAL_BLUE (stellar-blue)."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        df = create_equity_df(50)
        chart.set_baseline(df)

        # Get pen color from baseline curve
        pen = chart._baseline_curve.opts.get("pen")
        assert pen is not None
        # Pen color should be SIGNAL_BLUE
        color = pen.color().name()
        assert color.upper() == Colors.SIGNAL_BLUE.upper()

    def test_filtered_curve_uses_signal_cyan(self, qtbot):
        """Filtered curve uses SIGNAL_CYAN (plasma-cyan)."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        df = create_equity_df(50)
        chart.set_filtered(df)

        pen = chart._filtered_curve.opts.get("pen")
        assert pen is not None
        color = pen.color().name()
        assert color.upper() == Colors.SIGNAL_CYAN.upper()

    def test_curves_have_2px_width(self, qtbot):
        """Curves have 2px line width."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        baseline_pen = chart._baseline_curve.opts.get("pen")
        filtered_pen = chart._filtered_curve.opts.get("pen")

        assert baseline_pen.width() == 2
        assert filtered_pen.width() == 2


class TestEquityChartInteractions:
    """Tests for EquityChart user interactions."""

    def test_double_click_triggers_auto_range(self, qtbot):
        """Double-click triggers auto-range and emits view_reset."""
        chart = EquityChart()
        qtbot.addWidget(chart)
        chart.show()
        qtbot.waitExposed(chart)

        df = create_equity_df(50)
        chart.set_baseline(df)

        # Zoom in to change the range
        chart._plot_widget.setRange(xRange=(0, 10), yRange=(10000, 10100))

        with qtbot.waitSignal(chart.view_reset, timeout=1000):
            # Simulate double-click at center
            center = chart.rect().center()
            QTest.mouseDClick(chart, Qt.MouseButton.LeftButton, pos=center)

    def test_range_changed_signal_emits_on_zoom(self, qtbot):
        """range_changed signal emits when view is zoomed."""
        chart = EquityChart()
        qtbot.addWidget(chart)
        chart.show()
        qtbot.waitExposed(chart)

        df = create_equity_df(50)
        chart.set_baseline(df)

        with qtbot.waitSignal(chart.range_changed, timeout=1000):
            chart._plot_widget.setRange(xRange=(0, 10), yRange=(10000, 10100))

    def test_home_key_triggers_auto_range(self, qtbot):
        """Home key triggers auto-range (accessibility)."""
        chart = EquityChart()
        qtbot.addWidget(chart)
        chart.show()
        qtbot.waitExposed(chart)

        df = create_equity_df(50)
        chart.set_baseline(df)

        # Zoom in first
        chart._plot_widget.setRange(xRange=(0, 10), yRange=(10000, 10100))

        with qtbot.waitSignal(chart.view_reset, timeout=1000):
            QTest.keyPress(chart, Qt.Key.Key_Home)

    def test_plus_key_zooms_in(self, qtbot):
        """Plus key zooms in."""
        chart = EquityChart()
        qtbot.addWidget(chart)
        chart.show()
        qtbot.waitExposed(chart)

        df = create_equity_df(50)
        chart.set_baseline(df)

        # Get initial range
        initial_range = chart._plot_widget.viewRange()
        initial_x_width = initial_range[0][1] - initial_range[0][0]

        # Press plus key
        QTest.keyPress(chart, Qt.Key.Key_Plus)
        qtbot.wait(50)

        # Get new range - should be narrower (zoomed in)
        new_range = chart._plot_widget.viewRange()
        new_x_width = new_range[0][1] - new_range[0][0]

        assert new_x_width < initial_x_width

    def test_minus_key_zooms_out(self, qtbot):
        """Minus key zooms out."""
        chart = EquityChart()
        qtbot.addWidget(chart)
        chart.show()
        qtbot.waitExposed(chart)

        df = create_equity_df(50)
        chart.set_baseline(df)

        # Zoom in first
        chart._plot_widget.setRange(xRange=(10, 30), yRange=(10000, 10500))
        qtbot.wait(50)

        # Get initial range after zoom
        initial_range = chart._plot_widget.viewRange()
        initial_x_width = initial_range[0][1] - initial_range[0][0]

        # Press minus key
        QTest.keyPress(chart, Qt.Key.Key_Minus)
        qtbot.wait(50)

        # Get new range - should be wider (zoomed out)
        new_range = chart._plot_widget.viewRange()
        new_x_width = new_range[0][1] - new_range[0][0]

        assert new_x_width > initial_x_width


class TestEquityChartCrosshairWidget:
    """Widget tests for crosshair interaction."""

    def test_crosshair_appears_on_mouse_hover(self, qtbot):
        """Crosshair appears when mouse enters chart area."""
        chart = EquityChart()
        qtbot.addWidget(chart)
        chart.show()
        qtbot.waitExposed(chart)

        df = create_equity_df(50)
        chart.set_baseline(df)

        # Initially hidden
        assert not chart._crosshair_v.isVisible()
        assert not chart._crosshair_h.isVisible()

        # Move mouse into chart area - use scene coordinates
        plot_widget = chart._plot_widget
        scene_rect = plot_widget.sceneBoundingRect()
        center = scene_rect.center()

        # Manually trigger the mouse moved signal
        chart._on_mouse_moved(center)

        # Crosshair should now be visible
        assert chart._crosshair_v.isVisible()
        assert chart._crosshair_h.isVisible()
        assert chart._coord_label.isVisible()


class TestEquityChartPanMode:
    """Tests for pan mode configuration."""

    def test_viewbox_pan_mode_enabled(self, qtbot):
        """ViewBox is set to PanMode for left-drag panning."""
        import pyqtgraph as pg

        chart = EquityChart()
        qtbot.addWidget(chart)

        viewbox = chart._plot_widget.getViewBox()
        assert viewbox.state["mouseMode"] == pg.ViewBox.PanMode

    def test_viewbox_menu_disabled(self, qtbot):
        """ViewBox context menu is disabled for right-click zoom."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        viewbox = chart._plot_widget.getViewBox()
        assert viewbox.menuEnabled() is False


class TestEquityChartLegend:
    """Tests for EquityChart legend."""

    def test_legend_exists(self, qtbot):
        """Chart has a legend."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        assert hasattr(chart, "_legend")
        assert chart._legend is not None

    def test_legend_has_baseline_entry(self, qtbot):
        """Legend contains Baseline entry."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        # Legend should have items
        items = chart._legend.items
        labels = [item[1].text for item in items]
        assert "Baseline" in labels

    def test_legend_has_filtered_entry(self, qtbot):
        """Legend contains Filtered entry."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        items = chart._legend.items
        labels = [item[1].text for item in items]
        assert "Filtered" in labels


class TestChartPanelDateAxisSwitching:
    """Tests for date axis switching in both chart panels."""

    def _create_equity_df_with_dates(
        self, n_points: int = 10, include_dates: bool = True
    ) -> pd.DataFrame:
        """Create equity DataFrame with optional date column."""
        np.random.seed(42)
        pnl = np.random.normal(50, 100, n_points)
        equity = 10000 + np.cumsum(pnl)
        peak = np.maximum.accumulate(equity)

        data = {
            "trade_num": np.arange(1, n_points + 1),
            "pnl": pnl,
            "equity": equity,
            "peak": peak,
            "drawdown": equity - peak,
        }

        if include_dates:
            data["date"] = pd.date_range("2024-01-01", periods=n_points, freq="D")

        return pd.DataFrame(data)

    def test_flat_stake_chart_switches_to_date_axis(self, qtbot):
        """Flat stake chart switches X-axis to dates when date data available."""
        from src.ui.components.axis_mode_toggle import AxisMode

        panel = _ChartPanel("Flat Stake PnL")
        qtbot.addWidget(panel)

        df = self._create_equity_df_with_dates(10, include_dates=True)
        panel.set_baseline(df)

        # Verify dates were extracted
        assert panel._baseline_dates is not None
        assert len(panel._baseline_dates) == 10
        assert panel.chart._baseline_timestamps is not None

        # Switch to date mode
        panel._on_axis_mode_changed(AxisMode.DATE)

        # Verify axis mode is DATE
        assert panel.chart._axis_mode == AxisMode.DATE

        # Verify curve X data is timestamps (large values)
        x_data = panel.chart._baseline_curve.xData
        assert x_data is not None
        assert x_data[0] > 1000000000  # Unix timestamp > 1 billion

    def test_kelly_chart_switches_to_date_axis(self, qtbot):
        """Kelly chart switches X-axis to dates when date data available."""
        from src.ui.components.axis_mode_toggle import AxisMode

        panel = _ChartPanel("Compounded Kelly PnL")
        qtbot.addWidget(panel)

        # Create Kelly-style DataFrame with position_size column
        df = self._create_equity_df_with_dates(10, include_dates=True)
        df["position_size"] = 1000.0

        panel.set_baseline(df)

        # Verify dates were extracted
        assert panel._baseline_dates is not None
        assert len(panel._baseline_dates) == 10
        assert panel.chart._baseline_timestamps is not None

        # Switch to date mode
        panel._on_axis_mode_changed(AxisMode.DATE)

        # Verify axis mode is DATE
        assert panel.chart._axis_mode == AxisMode.DATE

        # Verify curve X data is timestamps (large values)
        x_data = panel.chart._baseline_curve.xData
        assert x_data is not None
        assert x_data[0] > 1000000000  # Unix timestamp > 1 billion

    def test_both_charts_identical_date_handling(self, qtbot):
        """Flat stake and Kelly charts handle dates identically."""
        from src.ui.components.axis_mode_toggle import AxisMode

        flat_panel = _ChartPanel("Flat Stake PnL")
        kelly_panel = _ChartPanel("Compounded Kelly PnL")
        qtbot.addWidget(flat_panel)
        qtbot.addWidget(kelly_panel)

        # Create DataFrames with same dates
        flat_df = self._create_equity_df_with_dates(10, include_dates=True)
        kelly_df = self._create_equity_df_with_dates(10, include_dates=True)
        kelly_df["position_size"] = 1000.0

        flat_panel.set_baseline(flat_df)
        kelly_panel.set_baseline(kelly_df)

        # Both should have timestamps
        assert flat_panel.chart._baseline_timestamps is not None
        assert kelly_panel.chart._baseline_timestamps is not None

        # Timestamps should be identical
        np.testing.assert_array_equal(
            flat_panel.chart._baseline_timestamps,
            kelly_panel.chart._baseline_timestamps
        )

        # Switch both to date mode
        flat_panel._on_axis_mode_changed(AxisMode.DATE)
        kelly_panel._on_axis_mode_changed(AxisMode.DATE)

        # Both should have same X data
        np.testing.assert_array_equal(
            flat_panel.chart._baseline_curve.xData,
            kelly_panel.chart._baseline_curve.xData
        )

    def test_chart_without_dates_stays_numeric(self, qtbot):
        """Chart without date column stays in numeric mode."""
        from src.ui.components.axis_mode_toggle import AxisMode

        panel = _ChartPanel("Test Chart")
        qtbot.addWidget(panel)

        # Create DataFrame WITHOUT dates
        df = self._create_equity_df_with_dates(10, include_dates=False)
        panel.set_baseline(df)

        # Verify no dates extracted
        assert panel._baseline_dates is None
        assert panel.chart._baseline_timestamps is None

        # Switch to date mode (should fallback to numeric)
        panel._on_axis_mode_changed(AxisMode.DATE)

        # Mode is set to DATE but chart uses trade numbers since no timestamps
        assert panel.chart._axis_mode == AxisMode.DATE

        # X data should be trade numbers (1-10)
        x_data = panel.chart._baseline_curve.xData
        assert x_data is not None
        assert x_data[0] == 1
        assert x_data[-1] == 10


class TestChartPanelWidgetBehavior:
    """Widget tests for _ChartPanel behavior."""

    def test_chart_panel_renders_title(self, qtbot):
        """_ChartPanel displays title correctly."""
        panel = _ChartPanel("Flat Stake PnL")
        qtbot.addWidget(panel)
        panel.show()
        qtbot.waitExposed(panel)

        # Check that title is set in layout
        layout = panel.layout()
        title_widget = layout.itemAt(0).widget()
        assert title_widget.text() == "Flat Stake PnL"

    def test_chart_panel_minimum_height(self, qtbot):
        """_ChartPanel chart has minimum height of 250px."""
        panel = _ChartPanel("Test")
        qtbot.addWidget(panel)

        assert panel.chart.minimumHeight() == 250

    def test_chart_panel_checkbox_default_unchecked(self, qtbot):
        """Drawdown checkbox is unchecked by default."""
        panel = _ChartPanel("Test")
        qtbot.addWidget(panel)

        assert not panel._drawdown_checkbox.isChecked()

    def test_chart_panel_checkbox_label_correct(self, qtbot):
        """Drawdown checkbox has correct label."""
        panel = _ChartPanel("Test")
        qtbot.addWidget(panel)

        assert panel._drawdown_checkbox.text() == "Show Drawdown"
