"""Tests for MetricsSectionCard component."""

import pytest
from PyQt6.QtWidgets import QApplication

from src.ui.components.metrics_section_card import MetricsSectionCard


@pytest.fixture(scope="module")
def app():
    """Create QApplication for widget tests."""
    application = QApplication.instance() or QApplication([])
    yield application


class TestMetricsSectionCard:
    """Tests for MetricsSectionCard widget."""

    def test_creates_with_title_and_metrics(self, app):
        """Card displays section title and metric rows."""
        metrics = [
            ("num_trades", "Trades"),
            ("win_rate", "Win Rate"),
        ]
        card = MetricsSectionCard("Core Statistics", metrics)

        assert card._title_label.text() == "Core Statistics"
        assert len(card._rows) == 2
        assert "num_trades" in card._rows
        assert "win_rate" in card._rows

    def test_set_values_updates_rows(self, app):
        """set_values updates all metric rows."""
        metrics = [("num_trades", "Trades")]
        card = MetricsSectionCard("Test", metrics)

        card.set_values(
            baseline={"num_trades": 100},
            filtered={"num_trades": 50},
        )

        row = card._rows["num_trades"]
        assert "100" in row._baseline_label.text()
        assert "50" in row._filtered_label.text()

    def test_wider_columns_for_millions(self, app):
        """Value columns are 120px wide to fit millions."""
        metrics = [("flat_stake_pnl", "Flat Stake PnL")]
        card = MetricsSectionCard("Flat Stake", metrics)

        row = card._rows["flat_stake_pnl"]
        assert row._baseline_label.minimumWidth() >= 120
        assert row._filtered_label.minimumWidth() >= 120
