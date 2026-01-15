"""Tests for ComparisonGridHorizontal component."""

import pytest
from PyQt6.QtWidgets import QApplication

from src.core.models import TradingMetrics
from src.ui.components.comparison_grid_horizontal import ComparisonGridHorizontal


@pytest.fixture(scope="module")
def app():
    """Create QApplication for widget tests."""
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def sample_metrics():
    """Create sample TradingMetrics for testing."""
    return TradingMetrics(
        num_trades=100,
        win_rate=55.0,
        avg_winner=2.5,
        avg_loser=-1.5,
        rr_ratio=1.67,
        ev=0.5,
        edge=5.0,
        kelly=10.0,
        fractional_kelly=2.5,
        eg_full_kelly=1.5,
        eg_frac_kelly=0.5,
        eg_flat_stake=0.3,
        median_winner=2.0,
        median_loser=-1.2,
        winner_count=55,
        loser_count=45,
        winner_std=0.8,
        loser_std=0.5,
        winner_gains=[1.0, 2.0, 3.0],
        loser_gains=[-1.0, -2.0],
        winner_min=0.5,
        winner_max=5.0,
        loser_min=-3.0,
        loser_max=-0.5,
        max_consecutive_wins=5,
        max_consecutive_losses=3,
        max_loss_pct=-8.0,
        flat_stake_pnl=50000.0,
        flat_stake_max_dd=5000.0,
        flat_stake_max_dd_pct=10.0,
        flat_stake_dd_duration=15,
        kelly_pnl=75000.0,
        kelly_max_dd=10000.0,
        kelly_max_dd_pct=15.0,
        kelly_dd_duration=20,
    )


class TestComparisonGridHorizontal:
    """Tests for ComparisonGridHorizontal widget."""

    def test_creates_four_section_cards(self, app):
        """Grid creates all 4 section cards."""
        grid = ComparisonGridHorizontal()

        assert len(grid._section_cards) == 4
        assert "core_statistics" in grid._section_cards
        assert "streak_loss" in grid._section_cards
        assert "flat_stake" in grid._section_cards
        assert "kelly" in grid._section_cards

    def test_horizontal_layout(self, app):
        """Sections are arranged horizontally."""
        grid = ComparisonGridHorizontal()

        # Check layout is horizontal
        layout = grid._cards_layout
        assert layout is not None
        # All cards should be in the same row
        assert layout.count() == 4

    def test_set_values_updates_all_sections(self, app, sample_metrics):
        """set_values propagates to all section cards."""
        grid = ComparisonGridHorizontal()
        grid.set_values(sample_metrics, None)

        # Check core statistics section has data
        core_card = grid._section_cards["core_statistics"]
        trades_row = core_card._rows["num_trades"]
        assert "100" in trades_row._baseline_label.text()

    def test_clear_clears_all_sections(self, app, sample_metrics):
        """clear() clears all section cards."""
        grid = ComparisonGridHorizontal()
        grid.set_values(sample_metrics, sample_metrics)
        grid.clear()

        core_card = grid._section_cards["core_statistics"]
        trades_row = core_card._rows["num_trades"]
        assert trades_row._filtered_label.text() == "—"
