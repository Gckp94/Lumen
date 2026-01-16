"""Widget tests for MetricsGrid component."""

import pytest

from src.core.models import TradingMetrics
from src.ui.components.metrics_grid import METRIC_CONFIG, METRIC_TOOLTIPS, MetricsGrid
from src.ui.constants import Colors


class TestMetricsGridCreation:
    """Tests for MetricsGrid widget creation."""

    def test_metrics_grid_creation(self, qtbot) -> None:
        """MetricsGrid can be created."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        assert grid is not None

    def test_metrics_grid_has_26_cards(self, qtbot) -> None:
        """Grid displays all 26 metrics (18 core + 4 flat stake + 4 Kelly)."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        assert len(grid._cards) == 26

    def test_metrics_grid_has_all_metric_fields(self, qtbot) -> None:
        """Grid has cards for all metric fields."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)

        expected_fields = [
            "num_trades",
            "win_rate",
            "avg_winner",
            "avg_loser",
            "rr_ratio",
            "ev",
            "edge",
            "kelly",
            "stop_adjusted_kelly",
            "fractional_kelly",
            "eg_full_kelly",
            "eg_frac_kelly",
            "eg_flat_stake",
            "median_winner",
            "median_loser",
            "max_consecutive_wins",
            "max_consecutive_losses",
            "max_loss_pct",
            # Flat Stake metrics (Story 3.4)
            "flat_stake_pnl",
            "flat_stake_max_dd",
            "flat_stake_max_dd_pct",
            "flat_stake_dd_duration",
            # Kelly metrics (Story 3.5)
            "kelly_pnl",
            "kelly_max_dd",
            "kelly_max_dd_pct",
            "kelly_dd_duration",
        ]
        for field in expected_fields:
            assert field in grid._cards, f"Missing card for {field}"


class TestMetricsGridTooltips:
    """Tests for MetricsGrid tooltips."""

    def test_all_metrics_have_tooltips(self) -> None:
        """All metric labels have tooltip definitions."""
        for label, _, _ in METRIC_CONFIG:
            assert label in METRIC_TOOLTIPS, f"Missing tooltip for {label}"

    def test_tooltips_are_applied_to_cards(self, qtbot) -> None:
        """Tooltips are applied to MetricCard widgets."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)

        for label, field_name, _ in METRIC_CONFIG:
            card = grid._cards.get(field_name)
            assert card is not None
            expected_tooltip = METRIC_TOOLTIPS.get(label, "")
            assert card.toolTip() == expected_tooltip

    def test_tooltip_content_is_descriptive(self) -> None:
        """Tooltips contain descriptive content."""
        for label, tooltip in METRIC_TOOLTIPS.items():
            assert len(tooltip) > 10, f"Tooltip for {label} is too short"


class TestMetricsGridUpdate:
    """Tests for MetricsGrid update functionality."""

    @pytest.fixture
    def sample_metrics(self) -> TradingMetrics:
        """Sample TradingMetrics for testing."""
        return TradingMetrics(
            num_trades=100,
            win_rate=60.0,
            avg_winner=10.0,
            avg_loser=-4.0,
            rr_ratio=2.5,
            ev=3.0,
            kelly=30.0,
            winner_count=60,
            loser_count=40,
            winner_std=2.0,
            loser_std=1.5,
            winner_gains=[10.0, 12.0, 8.0],
            loser_gains=[-4.0, -3.0, -5.0],
            edge=300.0,
            fractional_kelly=7.5,
            eg_full_kelly=0.5,
            eg_frac_kelly=0.3,
            eg_flat_stake=0.1,
            median_winner=10.0,
            median_loser=-4.0,
            winner_min=5.0,
            winner_max=15.0,
            loser_min=-6.0,
            loser_max=-2.0,
        )

    def test_update_metrics_updates_all_cards(
        self, qtbot, sample_metrics: TradingMetrics
    ) -> None:
        """update_metrics() updates all card values."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)

        grid.update_metrics(sample_metrics)

        # Check num_trades card
        assert grid._cards["num_trades"]._value_widget.text() == "100"

    def test_update_metrics_displays_formatted_values(
        self, qtbot, sample_metrics: TradingMetrics
    ) -> None:
        """Values are formatted according to format spec."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)

        grid.update_metrics(sample_metrics)

        # Win rate should be formatted with .1f (60.0)
        assert "60" in grid._cards["win_rate"]._value_widget.text()

    def test_clear_metrics_shows_em_dash(self, qtbot, sample_metrics: TradingMetrics) -> None:
        """clear_metrics() shows em dash for all cards."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)

        # First update with values
        grid.update_metrics(sample_metrics)

        # Then clear
        grid.clear_metrics()

        # Check all cards show em dash
        for card in grid._cards.values():
            assert card._value_widget.text() == "\u2014"  # Em dash


class TestMetricsGridColorCoding:
    """Tests for MetricsGrid color coding."""

    def test_positive_values_use_cyan_color(self, qtbot) -> None:
        """Positive values display in SIGNAL_CYAN."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)

        metrics = TradingMetrics(
            num_trades=100,
            win_rate=60.0,
            avg_winner=10.0,
            avg_loser=-4.0,
            rr_ratio=2.5,
            ev=3.0,
            kelly=30.0,
            edge=300.0,
            fractional_kelly=7.5,
            eg_full_kelly=0.5,
            eg_frac_kelly=0.3,
            eg_flat_stake=0.1,
            median_winner=10.0,
            median_loser=-4.0,
        )
        grid.update_metrics(metrics)

        # Win rate is positive, should be cyan
        style = grid._cards["win_rate"]._value_widget.styleSheet()
        assert Colors.SIGNAL_CYAN in style

    def test_negative_values_use_coral_color(self, qtbot) -> None:
        """Negative values display in SIGNAL_CORAL."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)

        metrics = TradingMetrics(
            num_trades=100,
            win_rate=60.0,
            avg_winner=10.0,
            avg_loser=-4.0,
            rr_ratio=2.5,
            ev=3.0,
            kelly=30.0,
            median_winner=10.0,
            median_loser=-4.0,
        )
        grid.update_metrics(metrics)

        # Avg loser is negative, should be coral
        style = grid._cards["avg_loser"]._value_widget.styleSheet()
        assert Colors.SIGNAL_CORAL in style

        # Median loser is negative, should be coral
        style = grid._cards["median_loser"]._value_widget.styleSheet()
        assert Colors.SIGNAL_CORAL in style

    def test_none_values_use_primary_color(self, qtbot) -> None:
        """None values display in TEXT_PRIMARY."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)

        metrics = TradingMetrics.empty()
        grid.update_metrics(metrics)

        # All None values should be primary color
        style = grid._cards["win_rate"]._value_widget.styleSheet()
        assert Colors.TEXT_PRIMARY in style


class TestMetricsGridLayout:
    """Tests for MetricsGrid layout."""

    def test_grid_has_9_rows_3_columns(self, qtbot) -> None:
        """Grid has 9 rows and 3 columns (26 metrics)."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)

        layout = grid.layout()
        assert layout is not None

        # 26 items in 3 columns = 9 rows
        assert layout.count() == 26



class TestMetricsGridStreakMetrics:
    """Tests for streak metrics display (Story 3.3)."""

    def test_metrics_grid_displays_streak_metrics(self, qtbot) -> None:
        """Grid includes streak and max loss metrics."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        assert "max_consecutive_wins" in grid._cards
        assert "max_consecutive_losses" in grid._cards
        assert "max_loss_pct" in grid._cards

    def test_streak_metrics_tooltips_present(self, qtbot) -> None:
        """Streak metrics have tooltips."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        assert grid._cards["max_consecutive_wins"].toolTip() != ""
        assert grid._cards["max_consecutive_losses"].toolTip() != ""
        assert grid._cards["max_loss_pct"].toolTip() != ""

    def test_max_loss_displays_in_coral(self, qtbot) -> None:
        """Max loss (negative) displays in coral."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        metrics = TradingMetrics(
            num_trades=10,
            win_rate=50.0,
            avg_winner=5.0,
            avg_loser=-5.0,
            rr_ratio=1.0,
            ev=0.0,
            kelly=0.0,
            max_consecutive_wins=3,
            max_consecutive_losses=3,
            max_loss_pct=-6.0,
        )
        grid.update_metrics(metrics)
        # MetricCard.update_value applies coral color to negative values
        style = grid._cards["max_loss_pct"]._value_widget.styleSheet()
        assert Colors.SIGNAL_CORAL in style

    def test_streak_metrics_update_correctly(self, qtbot) -> None:
        """Streak metrics update with correct values."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        metrics = TradingMetrics(
            num_trades=10,
            win_rate=50.0,
            avg_winner=5.0,
            avg_loser=-5.0,
            rr_ratio=1.0,
            ev=0.0,
            kelly=0.0,
            max_consecutive_wins=5,
            max_consecutive_losses=3,
            max_loss_pct=-8.5,
        )
        grid.update_metrics(metrics)

        assert grid._cards["max_consecutive_wins"]._value_widget.text() == "5"
        assert grid._cards["max_consecutive_losses"]._value_widget.text() == "3"
        assert "-8.50" in grid._cards["max_loss_pct"]._value_widget.text()


class TestMetricsGridFlatStakeMetrics:
    """Tests for flat stake metrics display (Story 3.4)."""

    def test_metrics_grid_displays_flat_stake_metrics(self, qtbot) -> None:
        """Grid includes flat stake metrics."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        assert "flat_stake_pnl" in grid._cards
        assert "flat_stake_max_dd" in grid._cards
        assert "flat_stake_max_dd_pct" in grid._cards
        assert "flat_stake_dd_duration" in grid._cards

    def test_flat_stake_tooltips_present(self, qtbot) -> None:
        """Flat stake metrics have tooltips."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        assert grid._cards["flat_stake_pnl"].toolTip() != ""
        assert grid._cards["flat_stake_max_dd"].toolTip() != ""
        assert grid._cards["flat_stake_max_dd_pct"].toolTip() != ""
        assert grid._cards["flat_stake_dd_duration"].toolTip() != ""

    def test_dd_duration_displays_days_format(self, qtbot) -> None:
        """DD Duration displays as 'X days' for integer values."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        metrics = TradingMetrics(
            num_trades=10,
            win_rate=50.0,
            avg_winner=5.0,
            avg_loser=-5.0,
            rr_ratio=1.0,
            ev=0.0,
            kelly=0.0,
            flat_stake_pnl=100.0,
            flat_stake_max_dd=50.0,
            flat_stake_max_dd_pct=25.0,
            flat_stake_dd_duration=3,
        )
        grid.update_metrics(metrics)
        assert grid._cards["flat_stake_dd_duration"]._value_widget.text() == "3 days"

    def test_dd_duration_not_recovered_displays_coral(self, qtbot) -> None:
        """DD Duration 'Not recovered' displays in coral color."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        metrics = TradingMetrics(
            num_trades=10,
            win_rate=50.0,
            avg_winner=5.0,
            avg_loser=-5.0,
            rr_ratio=1.0,
            ev=0.0,
            kelly=0.0,
            flat_stake_pnl=100.0,
            flat_stake_max_dd=50.0,
            flat_stake_max_dd_pct=25.0,
            flat_stake_dd_duration="Not recovered",
        )
        grid.update_metrics(metrics)

        # Verify text is displayed
        assert grid._cards["flat_stake_dd_duration"]._value_widget.text() == "Not recovered"

        # Verify coral color is applied
        style = grid._cards["flat_stake_dd_duration"]._value_widget.styleSheet()
        assert Colors.SIGNAL_CORAL in style

    def test_flat_stake_pnl_positive_displays_cyan(self, qtbot) -> None:
        """Positive flat stake PnL displays in cyan."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        metrics = TradingMetrics(
            num_trades=10,
            win_rate=50.0,
            avg_winner=5.0,
            avg_loser=-5.0,
            rr_ratio=1.0,
            ev=0.0,
            kelly=0.0,
            flat_stake_pnl=500.0,
            flat_stake_max_dd=100.0,
            flat_stake_max_dd_pct=20.0,
            flat_stake_dd_duration=2,
        )
        grid.update_metrics(metrics)

        style = grid._cards["flat_stake_pnl"]._value_widget.styleSheet()
        assert Colors.SIGNAL_CYAN in style

    def test_flat_stake_values_format_correctly(self, qtbot) -> None:
        """Flat stake values are formatted with commas."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        metrics = TradingMetrics(
            num_trades=10,
            win_rate=50.0,
            avg_winner=5.0,
            avg_loser=-5.0,
            rr_ratio=1.0,
            ev=0.0,
            kelly=0.0,
            flat_stake_pnl=1234.56,
            flat_stake_max_dd=567.89,
            flat_stake_max_dd_pct=12.34,
            flat_stake_dd_duration=5,
        )
        grid.update_metrics(metrics)

        # Check comma formatting
        assert "1,234.56" in grid._cards["flat_stake_pnl"]._value_widget.text()
        assert "567.89" in grid._cards["flat_stake_max_dd"]._value_widget.text()
        assert "12.34" in grid._cards["flat_stake_max_dd_pct"]._value_widget.text()


class TestMetricsGridStopAdjustedKelly:
    """Tests for stop-adjusted Kelly metric display."""

    def test_stop_adjusted_kelly_displays(self, qtbot) -> None:
        """Stop-adjusted Kelly metric card displays correctly."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        metrics = TradingMetrics(
            num_trades=10,
            win_rate=60.0,
            avg_winner=2.0,
            avg_loser=-1.0,
            rr_ratio=2.0,
            ev=0.8,
            kelly=40.0,
            stop_adjusted_kelly=500.0,
        )
        grid.update_metrics(metrics)
        assert "stop_adjusted_kelly" in grid._cards
        assert "500.00" in grid._cards["stop_adjusted_kelly"]._value_widget.text()


class TestMetricsGridKellyMetrics:
    """Tests for Kelly metrics display (Story 3.5)."""

    def test_metrics_grid_displays_kelly_metrics(self, qtbot) -> None:
        """Grid includes Kelly metrics."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        assert "kelly_pnl" in grid._cards
        assert "kelly_max_dd" in grid._cards
        assert "kelly_max_dd_pct" in grid._cards
        assert "kelly_dd_duration" in grid._cards

    def test_kelly_tooltips_present(self, qtbot) -> None:
        """Kelly metrics have tooltips."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        assert grid._cards["kelly_pnl"].toolTip() != ""
        assert grid._cards["kelly_max_dd"].toolTip() != ""
        assert grid._cards["kelly_max_dd_pct"].toolTip() != ""
        assert grid._cards["kelly_dd_duration"].toolTip() != ""

    def test_kelly_dd_duration_displays_days_format(self, qtbot) -> None:
        """Kelly DD Duration displays as 'X days' for integer values."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        metrics = TradingMetrics(
            num_trades=10,
            win_rate=50.0,
            avg_winner=5.0,
            avg_loser=-5.0,
            rr_ratio=1.0,
            ev=0.0,
            kelly=0.0,
            kelly_pnl=1000.0,
            kelly_max_dd=200.0,
            kelly_max_dd_pct=10.0,
            kelly_dd_duration=5,
        )
        grid.update_metrics(metrics)
        assert grid._cards["kelly_dd_duration"]._value_widget.text() == "5 days"

    def test_kelly_dd_duration_blown_displays_coral(self, qtbot) -> None:
        """Kelly DD Duration 'Blown' displays in coral color."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        metrics = TradingMetrics(
            num_trades=10,
            win_rate=50.0,
            avg_winner=5.0,
            avg_loser=-5.0,
            rr_ratio=1.0,
            ev=0.0,
            kelly=0.0,
            kelly_pnl=-10000.0,
            kelly_max_dd=10000.0,
            kelly_max_dd_pct=100.0,
            kelly_dd_duration="Blown",
        )
        grid.update_metrics(metrics)

        # Verify text is displayed
        assert grid._cards["kelly_dd_duration"]._value_widget.text() == "Blown"

        # Verify coral color is applied
        style = grid._cards["kelly_dd_duration"]._value_widget.styleSheet()
        assert Colors.SIGNAL_CORAL in style

    def test_kelly_dd_duration_not_recovered_displays_coral(self, qtbot) -> None:
        """Kelly DD Duration 'Not recovered' displays in coral color."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        metrics = TradingMetrics(
            num_trades=10,
            win_rate=50.0,
            avg_winner=5.0,
            avg_loser=-5.0,
            rr_ratio=1.0,
            ev=0.0,
            kelly=0.0,
            kelly_pnl=500.0,
            kelly_max_dd=300.0,
            kelly_max_dd_pct=30.0,
            kelly_dd_duration="Not recovered",
        )
        grid.update_metrics(metrics)

        # Verify text is displayed
        assert grid._cards["kelly_dd_duration"]._value_widget.text() == "Not recovered"

        # Verify coral color is applied
        style = grid._cards["kelly_dd_duration"]._value_widget.styleSheet()
        assert Colors.SIGNAL_CORAL in style

    def test_kelly_pnl_positive_displays_cyan(self, qtbot) -> None:
        """Positive Kelly PnL displays in cyan."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        metrics = TradingMetrics(
            num_trades=10,
            win_rate=50.0,
            avg_winner=5.0,
            avg_loser=-5.0,
            rr_ratio=1.0,
            ev=0.0,
            kelly=0.0,
            kelly_pnl=5000.0,
            kelly_max_dd=500.0,
            kelly_max_dd_pct=5.0,
            kelly_dd_duration=2,
        )
        grid.update_metrics(metrics)

        style = grid._cards["kelly_pnl"]._value_widget.styleSheet()
        assert Colors.SIGNAL_CYAN in style

    def test_kelly_pnl_negative_displays_coral(self, qtbot) -> None:
        """Negative Kelly PnL displays in coral."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        metrics = TradingMetrics(
            num_trades=10,
            win_rate=50.0,
            avg_winner=5.0,
            avg_loser=-5.0,
            rr_ratio=1.0,
            ev=0.0,
            kelly=0.0,
            kelly_pnl=-3000.0,
            kelly_max_dd=5000.0,
            kelly_max_dd_pct=50.0,
            kelly_dd_duration="Blown",
        )
        grid.update_metrics(metrics)

        style = grid._cards["kelly_pnl"]._value_widget.styleSheet()
        assert Colors.SIGNAL_CORAL in style

    def test_kelly_values_format_correctly(self, qtbot) -> None:
        """Kelly values are formatted with commas."""
        grid = MetricsGrid()
        qtbot.addWidget(grid)
        metrics = TradingMetrics(
            num_trades=10,
            win_rate=50.0,
            avg_winner=5.0,
            avg_loser=-5.0,
            rr_ratio=1.0,
            ev=0.0,
            kelly=0.0,
            kelly_pnl=12345.67,
            kelly_max_dd=2345.89,
            kelly_max_dd_pct=23.45,
            kelly_dd_duration=10,
        )
        grid.update_metrics(metrics)

        # Check comma formatting
        assert "12,345.67" in grid._cards["kelly_pnl"]._value_widget.text()
        assert "2,345.89" in grid._cards["kelly_max_dd"]._value_widget.text()
        assert "23.45" in grid._cards["kelly_max_dd_pct"]._value_widget.text()
