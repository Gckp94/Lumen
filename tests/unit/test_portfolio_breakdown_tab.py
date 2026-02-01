# tests/unit/test_portfolio_breakdown_tab.py
"""Tests for PortfolioBreakdownTab."""

import pytest
from PyQt6.QtWidgets import QApplication

from src.tabs.portfolio_breakdown import PortfolioBreakdownTab


@pytest.fixture(scope="module")
def app():
    """Ensure QApplication exists."""
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def breakdown_tab(qtbot):
    """Create PortfolioBreakdownTab instance."""
    tab = PortfolioBreakdownTab()
    qtbot.addWidget(tab)
    return tab


class TestPortfolioBreakdownTabSignalIntegration:
    """Tests for signal integration with Portfolio Overview."""

    def test_on_portfolio_data_changed_updates_data(self, app, breakdown_tab):
        """Verify signal handler stores incoming data."""
        import pandas as pd

        baseline_df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-02-01"]),
            "trade_num": [1, 2],
            "gain_pct": [1.0, 2.0],  # Adjusted gain in percentage form
            "pnl": [100.0, 200.0],
            "equity": [10100.0, 10300.0],
            "peak": [10100.0, 10300.0],
            "drawdown": [0.0, 0.0],
            "win": [True, True],
        })

        breakdown_tab.on_portfolio_data_changed({"baseline": baseline_df})

        assert breakdown_tab._baseline_data is not None
        assert len(breakdown_tab._baseline_data) == 2


class TestPortfolioBreakdownTabStructure:
    """Tests for tab structure."""

    def test_tab_creates_without_error(self, app, breakdown_tab):
        """Verify tab instantiates."""
        assert breakdown_tab is not None

    def test_has_period_tabs(self, app, breakdown_tab):
        """Verify yearly/monthly period tabs exist."""
        assert breakdown_tab._yearly_btn is not None
        assert breakdown_tab._monthly_btn is not None

    def test_has_visibility_toggles(self, app, breakdown_tab):
        """Verify baseline/combined toggles exist."""
        assert breakdown_tab._baseline_toggle is not None
        assert breakdown_tab._combined_toggle is not None

    def test_has_year_selector(self, app, breakdown_tab):
        """Verify year selector exists."""
        assert breakdown_tab._year_selector is not None

    def test_has_chart_containers(self, app, breakdown_tab):
        """Verify chart containers exist."""
        assert breakdown_tab._yearly_charts is not None
        assert breakdown_tab._monthly_charts is not None
        # Should have 16 charts each (8 metrics × 2 portfolios)
        assert len(breakdown_tab._yearly_charts) == 16
        assert len(breakdown_tab._monthly_charts) == 16
