"""Unit tests for EquityChart component."""

import numpy as np
import pandas as pd
from PyQt6.QtCore import Qt

from src.ui.components.equity_chart import EquityChart, _ChartPanel


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


class TestEquityChartSetBaseline:
    """Tests for EquityChart.set_baseline() method."""

    def test_set_baseline_updates_baseline_curve(self, qtbot):
        """set_baseline() updates baseline PlotDataItem with correct data."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        df = create_equity_df(50)
        chart.set_baseline(df)

        # Verify baseline curve has data
        x_data, y_data = chart._baseline_curve.getData()
        assert len(x_data) == 50
        assert len(y_data) == 50
        np.testing.assert_array_equal(x_data, df["trade_num"].values)
        np.testing.assert_array_equal(y_data, df["equity"].values)

    def test_set_baseline_none_clears_baseline_series(self, qtbot):
        """set_baseline(None) clears baseline series."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        # First set some data
        df = create_equity_df(50)
        chart.set_baseline(df)

        # Then clear it
        chart.set_baseline(None)

        x_data, y_data = chart._baseline_curve.getData()
        assert x_data is None or len(x_data) == 0
        assert y_data is None or len(y_data) == 0

    def test_set_baseline_empty_df_clears_series(self, qtbot):
        """set_baseline() with empty DataFrame clears series."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        # First set some data
        df = create_equity_df(50)
        chart.set_baseline(df)

        # Then set empty DataFrame
        empty_df = pd.DataFrame(columns=["trade_num", "equity", "peak"])
        chart.set_baseline(empty_df)

        x_data, _y_data = chart._baseline_curve.getData()
        assert x_data is None or len(x_data) == 0

    def test_set_baseline_updates_peak_curve(self, qtbot):
        """set_baseline() also updates peak curve for drawdown."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        df = create_equity_df(50)
        chart.set_baseline(df)

        x_data, y_data = chart._peak_curve.getData()
        assert len(x_data) == 50
        np.testing.assert_array_equal(y_data, df["peak"].values)


class TestEquityChartSetFiltered:
    """Tests for EquityChart.set_filtered() method."""

    def test_set_filtered_updates_filtered_curve(self, qtbot):
        """set_filtered() updates filtered PlotDataItem."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        df = create_equity_df(30)
        chart.set_filtered(df)

        x_data, y_data = chart._filtered_curve.getData()
        assert len(x_data) == 30
        np.testing.assert_array_equal(x_data, df["trade_num"].values)
        np.testing.assert_array_equal(y_data, df["equity"].values)

    def test_set_filtered_none_hides_filtered_series(self, qtbot):
        """set_filtered(None) hides filtered series."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        # First set some data
        df = create_equity_df(30)
        chart.set_filtered(df)

        # Then clear it
        chart.set_filtered(None)

        x_data, _y_data = chart._filtered_curve.getData()
        assert x_data is None or len(x_data) == 0

    def test_set_filtered_empty_df_clears_series(self, qtbot):
        """set_filtered() with empty DataFrame clears series."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        df = create_equity_df(30)
        chart.set_filtered(df)

        empty_df = pd.DataFrame(columns=["trade_num", "equity"])
        chart.set_filtered(empty_df)

        x_data, _y_data = chart._filtered_curve.getData()
        assert x_data is None or len(x_data) == 0


class TestEquityChartClear:
    """Tests for EquityChart.clear() method."""

    def test_clear_resets_both_series(self, qtbot):
        """clear() resets both baseline and filtered series."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        # Set both baseline and filtered
        df = create_equity_df(50)
        chart.set_baseline(df)
        chart.set_filtered(df)

        # Clear all
        chart.clear()

        baseline_x, _baseline_y = chart._baseline_curve.getData()
        filtered_x, _filtered_y = chart._filtered_curve.getData()

        assert baseline_x is None or len(baseline_x) == 0
        assert filtered_x is None or len(filtered_x) == 0


class TestEquityChartDrawdown:
    """Tests for EquityChart drawdown visualization."""

    def test_drawdown_fill_hidden_by_default(self, qtbot):
        """Drawdown fill is hidden by default."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        assert chart._show_drawdown is False
        assert not chart._drawdown_fill.isVisible()

    def test_set_drawdown_visible_true_shows_fill(self, qtbot):
        """set_drawdown_visible(True) shows drawdown fill when data exists."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        # Need data for drawdown to show
        df = create_equity_df(50)
        chart.set_baseline(df)

        chart.set_drawdown_visible(True)

        assert chart._show_drawdown is True
        assert chart._drawdown_fill.isVisible()

    def test_set_drawdown_visible_false_hides_fill(self, qtbot):
        """set_drawdown_visible(False) hides drawdown fill."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        df = create_equity_df(50)
        chart.set_baseline(df)
        chart.set_drawdown_visible(True)

        chart.set_drawdown_visible(False)

        assert chart._show_drawdown is False
        assert not chart._drawdown_fill.isVisible()

    def test_drawdown_fill_not_visible_without_data(self, qtbot):
        """Drawdown fill stays hidden even with show_drawdown=True if no data."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        chart.set_drawdown_visible(True)

        # Still hidden because no data
        assert chart._show_drawdown is True
        assert not chart._drawdown_fill.isVisible()

    def test_show_drawdown_property(self, qtbot):
        """show_drawdown property reflects current state."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        assert chart.show_drawdown is False

        chart.set_drawdown_visible(True)
        assert chart.show_drawdown is True


class TestEquityChartSignals:
    """Tests for EquityChart signals."""

    def test_render_failed_signal_exists(self, qtbot):
        """EquityChart has render_failed signal."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        assert hasattr(chart, "render_failed")

    def test_render_failed_emits_on_invalid_data(self, qtbot):
        """render_failed signal emits on invalid data input."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        # Create DataFrame missing required columns
        invalid_df = pd.DataFrame({"wrong_column": [1, 2, 3]})

        with qtbot.waitSignal(chart.render_failed, timeout=1000) as blocker:
            chart.set_baseline(invalid_df)

        assert "ChartRenderError" in blocker.args[0]

    def test_range_changed_signal_exists(self, qtbot):
        """EquityChart has range_changed signal."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        assert hasattr(chart, "range_changed")

    def test_view_reset_signal_exists(self, qtbot):
        """EquityChart has view_reset signal."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        assert hasattr(chart, "view_reset")

    def test_auto_range_emits_view_reset(self, qtbot):
        """auto_range() emits view_reset signal."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        df = create_equity_df(50)
        chart.set_baseline(df)

        with qtbot.waitSignal(chart.view_reset, timeout=1000):
            chart.auto_range()


class TestEquityChartCrosshair:
    """Tests for EquityChart crosshair functionality."""

    def test_crosshair_lines_created(self, qtbot):
        """Crosshair lines are created on initialization."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        assert hasattr(chart, "_crosshair_v")
        assert hasattr(chart, "_crosshair_h")
        assert chart._crosshair_v is not None
        assert chart._crosshair_h is not None

    def test_crosshair_lines_styled_correctly(self, qtbot):
        """Crosshair lines have correct dashed style."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        assert chart._crosshair_v.pen.style() == Qt.PenStyle.DashLine
        assert chart._crosshair_h.pen.style() == Qt.PenStyle.DashLine

    def test_crosshair_hidden_initially(self, qtbot):
        """Crosshair is hidden until mouse enters chart area."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        assert not chart._crosshair_v.isVisible()
        assert not chart._crosshair_h.isVisible()

    def test_coordinate_label_created(self, qtbot):
        """Coordinate label is created on initialization."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        assert hasattr(chart, "_coord_label")
        assert chart._coord_label is not None

    def test_coordinate_label_hidden_initially(self, qtbot):
        """Coordinate label is hidden until mouse enters chart area."""
        chart = EquityChart()
        qtbot.addWidget(chart)

        assert not chart._coord_label.isVisible()


class TestChartPanelContainer:
    """Tests for _ChartPanel container widget."""

    def test_chart_panel_has_chart(self, qtbot):
        """_ChartPanel contains an EquityChart."""
        panel = _ChartPanel("Test Title")
        qtbot.addWidget(panel)

        assert hasattr(panel, "chart")
        assert isinstance(panel.chart, EquityChart)

    def test_chart_panel_set_baseline_passthrough(self, qtbot):
        """_ChartPanel.set_baseline() passes through to chart."""
        panel = _ChartPanel("Test Title")
        qtbot.addWidget(panel)

        df = create_equity_df(30)
        panel.set_baseline(df)

        x_data, _y_data = panel.chart._baseline_curve.getData()
        assert len(x_data) == 30

    def test_chart_panel_set_filtered_passthrough(self, qtbot):
        """_ChartPanel.set_filtered() passes through to chart."""
        panel = _ChartPanel("Test Title")
        qtbot.addWidget(panel)

        df = create_equity_df(30)
        panel.set_filtered(df)

        x_data, _y_data = panel.chart._filtered_curve.getData()
        assert len(x_data) == 30

    def test_chart_panel_clear_passthrough(self, qtbot):
        """_ChartPanel.clear() passes through to chart."""
        panel = _ChartPanel("Test Title")
        qtbot.addWidget(panel)

        df = create_equity_df(30)
        panel.set_baseline(df)
        panel.clear()

        x_data, _y_data = panel.chart._baseline_curve.getData()
        assert x_data is None or len(x_data) == 0

    def test_chart_panel_has_drawdown_checkbox(self, qtbot):
        """_ChartPanel has drawdown toggle checkbox."""
        panel = _ChartPanel("Test Title")
        qtbot.addWidget(panel)

        assert hasattr(panel, "_drawdown_checkbox")

    def test_chart_panel_checkbox_toggles_drawdown(self, qtbot):
        """Checkbox toggles chart drawdown visibility."""
        panel = _ChartPanel("Test Title")
        qtbot.addWidget(panel)

        df = create_equity_df(30)
        panel.set_baseline(df)

        # Toggle checkbox on
        panel._drawdown_checkbox.setChecked(True)
        assert panel.chart.show_drawdown is True
        assert panel.chart._drawdown_fill.isVisible()

        # Toggle checkbox off
        panel._drawdown_checkbox.setChecked(False)
        assert panel.chart.show_drawdown is False
        assert not panel.chart._drawdown_fill.isVisible()
