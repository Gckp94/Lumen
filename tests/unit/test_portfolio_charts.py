# tests/unit/test_portfolio_charts.py
"""Unit tests for PortfolioChartsWidget."""

import pytest
import pandas as pd
import numpy as np
from PyQt6.QtWidgets import QApplication
from src.ui.components.portfolio_charts import PortfolioChartsWidget


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance() or QApplication([])
    yield app


class TestPortfolioChartsWidget:
    def test_widget_creates_successfully(self, app, qtbot):
        widget = PortfolioChartsWidget()
        qtbot.addWidget(widget)
        assert widget is not None

    def test_set_data_updates_charts(self, app, qtbot):
        widget = PortfolioChartsWidget()
        qtbot.addWidget(widget)

        data = {
            "Strategy A": pd.DataFrame({
                "trade_num": [1, 2, 3],
                "equity": [100000, 101000, 102000],
                "drawdown": [0, 0, 0],
                "peak": [100000, 101000, 102000],
                "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            }),
            "baseline": pd.DataFrame({
                "trade_num": [1, 2],
                "equity": [100000, 100500],
                "drawdown": [0, 0],
                "peak": [100000, 100500],
                "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            }),
        }
        widget.set_data(data)
        # Should not raise

    def test_toggle_series_visibility(self, app, qtbot):
        widget = PortfolioChartsWidget()
        qtbot.addWidget(widget)

        widget.set_series_visible("Strategy A", False)
        assert widget.is_series_visible("Strategy A") is False

        widget.set_series_visible("Strategy A", True)
        assert widget.is_series_visible("Strategy A") is True

    def test_set_data_with_combined_portfolio(self, app, qtbot):
        """Test with combined portfolio data."""
        widget = PortfolioChartsWidget()
        qtbot.addWidget(widget)

        data = {
            "combined": pd.DataFrame({
                "trade_num": [1, 2, 3, 4],
                "equity": [100000, 105000, 103000, 108000],
                "drawdown": [0, 0, 2000, 0],
                "peak": [100000, 105000, 105000, 108000],
                "date": pd.to_datetime([
                    "2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"
                ]),
            }),
            "Strategy A": pd.DataFrame({
                "trade_num": [1, 2],
                "equity": [50000, 52000],
                "drawdown": [0, 0],
                "peak": [50000, 52000],
                "date": pd.to_datetime(["2024-01-01", "2024-01-03"]),
            }),
            "Strategy B": pd.DataFrame({
                "trade_num": [1, 2],
                "equity": [50000, 53000],
                "drawdown": [0, 0],
                "peak": [50000, 53000],
                "date": pd.to_datetime(["2024-01-02", "2024-01-04"]),
            }),
        }
        widget.set_data(data)
        # Should not raise

    def test_series_visibility_persists_after_set_data(self, app, qtbot):
        """Test that visibility state is preserved when data is updated."""
        widget = PortfolioChartsWidget()
        qtbot.addWidget(widget)

        # Set initial visibility
        widget.set_series_visible("Strategy A", False)

        # Set data
        data = {
            "Strategy A": pd.DataFrame({
                "trade_num": [1, 2, 3],
                "equity": [100000, 101000, 102000],
                "drawdown": [0, 0, 0],
                "peak": [100000, 101000, 102000],
                "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            }),
        }
        widget.set_data(data)

        # Visibility should be preserved
        assert widget.is_series_visible("Strategy A") is False

    def test_axis_mode_signal_emitted(self, app, qtbot):
        """Test that axis_mode_changed signal is emitted."""
        widget = PortfolioChartsWidget()
        qtbot.addWidget(widget)

        signal_received = []
        widget.axis_mode_changed.connect(lambda mode: signal_received.append(mode))

        # Simulate mode change via the toggle
        from src.ui.components.axis_mode_toggle import AxisMode
        widget._axis_toggle.set_mode(AxisMode.DATE)

        assert len(signal_received) == 1
        assert signal_received[0] == AxisMode.DATE

    def test_empty_data(self, app, qtbot):
        """Test setting empty data dict."""
        widget = PortfolioChartsWidget()
        qtbot.addWidget(widget)

        widget.set_data({})
        # Should not raise

    def test_legend_checkboxes_created(self, app, qtbot):
        """Test that legend checkboxes are created for each series."""
        widget = PortfolioChartsWidget()
        qtbot.addWidget(widget)

        data = {
            "Strategy A": pd.DataFrame({
                "trade_num": [1, 2],
                "equity": [100000, 101000],
                "drawdown": [0, 0],
                "peak": [100000, 101000],
                "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            }),
            "Strategy B": pd.DataFrame({
                "trade_num": [1, 2],
                "equity": [100000, 102000],
                "drawdown": [0, 0],
                "peak": [100000, 102000],
                "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            }),
        }
        widget.set_data(data)

        # Check that checkboxes exist
        assert "Strategy A" in widget._legend_checkboxes
        assert "Strategy B" in widget._legend_checkboxes
