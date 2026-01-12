"""Widget tests for MetricsPanel."""

from pytestqt.qtbot import QtBot

from src.core.models import TradingMetrics
from src.tabs.data_input import MetricsPanel


class TestMetricsPanelDisplay:
    """Tests for MetricsPanel display functionality."""

    def test_panel_displays_all_seven_cards(self, qtbot: QtBot) -> None:
        """Panel displays all 7 metric cards."""
        panel = MetricsPanel()
        qtbot.addWidget(panel)

        assert len(panel._cards) == 7
        assert "trades" in panel._cards
        assert "win_rate" in panel._cards
        assert "avg_winner" in panel._cards
        assert "avg_loser" in panel._cards
        assert "rr_ratio" in panel._cards
        assert "ev" in panel._cards
        assert "kelly" in panel._cards

    def test_panel_has_object_name(self, qtbot: QtBot) -> None:
        """Panel has correct object name."""
        panel = MetricsPanel()
        qtbot.addWidget(panel)

        assert panel.objectName() == "metrics_panel"


class TestMetricsPanelUpdate:
    """Tests for MetricsPanel update functionality."""

    def test_update_with_metrics(self, qtbot: QtBot) -> None:
        """Update with TradingMetrics updates all cards."""
        panel = MetricsPanel()
        qtbot.addWidget(panel)

        metrics = TradingMetrics(
            num_trades=100,
            win_rate=60.0,
            avg_winner=2.5,
            avg_loser=-1.25,
            rr_ratio=2.0,
            ev=0.875,
            kelly=40.0,
            winner_count=60,
            loser_count=40,
        )

        panel.update_metrics(metrics)

        # Check trades card shows integer
        assert "100" in panel._cards["trades"]._value_widget.text()

    def test_update_with_none(self, qtbot: QtBot) -> None:
        """Update with None clears all cards."""
        panel = MetricsPanel()
        qtbot.addWidget(panel)

        # First update with values
        metrics = TradingMetrics(
            num_trades=100,
            win_rate=60.0,
            avg_winner=2.5,
            avg_loser=-1.25,
            rr_ratio=2.0,
            ev=0.875,
            kelly=40.0,
        )
        panel.update_metrics(metrics)

        # Then clear
        panel.update_metrics(None)

        # All cards should show em dash
        for card in panel._cards.values():
            assert "\u2014" in card._value_widget.text()


class TestMetricsPanelFormatting:
    """Tests for MetricsPanel value formatting."""

    def test_trades_integer_format(self, qtbot: QtBot) -> None:
        """Trades displays as integer with thousands separator."""
        panel = MetricsPanel()
        qtbot.addWidget(panel)

        metrics = TradingMetrics(
            num_trades=12847,
            win_rate=60.0,
            avg_winner=2.5,
            avg_loser=-1.25,
            rr_ratio=2.0,
            ev=0.875,
            kelly=40.0,
        )
        panel.update_metrics(metrics)

        assert "12,847" in panel._cards["trades"]._value_widget.text()

    def test_win_rate_percent_format(self, qtbot: QtBot) -> None:
        """Win rate displays with percent sign."""
        panel = MetricsPanel()
        qtbot.addWidget(panel)

        metrics = TradingMetrics(
            num_trades=100,
            win_rate=67.5,
            avg_winner=2.5,
            avg_loser=-1.25,
            rr_ratio=2.0,
            ev=0.875,
            kelly=40.0,
        )
        panel.update_metrics(metrics)

        text = panel._cards["win_rate"]._value_widget.text()
        assert "67.5" in text
        assert "%" in text

    def test_avg_winner_signed_percent(self, qtbot: QtBot) -> None:
        """Avg winner displays with sign and percent."""
        panel = MetricsPanel()
        qtbot.addWidget(panel)

        metrics = TradingMetrics(
            num_trades=100,
            win_rate=60.0,
            avg_winner=2.5,
            avg_loser=-1.25,
            rr_ratio=2.0,
            ev=0.875,
            kelly=40.0,
        )
        panel.update_metrics(metrics)

        text = panel._cards["avg_winner"]._value_widget.text()
        assert "+" in text
        assert "%" in text

    def test_avg_loser_negative_percent(self, qtbot: QtBot) -> None:
        """Avg loser displays as negative with percent."""
        panel = MetricsPanel()
        qtbot.addWidget(panel)

        metrics = TradingMetrics(
            num_trades=100,
            win_rate=60.0,
            avg_winner=2.5,
            avg_loser=-1.25,
            rr_ratio=2.0,
            ev=0.875,
            kelly=40.0,
        )
        panel.update_metrics(metrics)

        text = panel._cards["avg_loser"]._value_widget.text()
        assert "-" in text
        assert "%" in text

    def test_rr_ratio_format(self, qtbot: QtBot) -> None:
        """R:R ratio displays as decimal without :1 suffix."""
        panel = MetricsPanel()
        qtbot.addWidget(panel)

        metrics = TradingMetrics(
            num_trades=100,
            win_rate=60.0,
            avg_winner=2.5,
            avg_loser=-1.25,
            rr_ratio=2.0,
            ev=0.875,
            kelly=40.0,
        )
        panel.update_metrics(metrics)

        text = panel._cards["rr_ratio"]._value_widget.text()
        assert text == "2.00"

    def test_ev_signed_percent(self, qtbot: QtBot) -> None:
        """EV displays with sign and percent."""
        panel = MetricsPanel()
        qtbot.addWidget(panel)

        metrics = TradingMetrics(
            num_trades=100,
            win_rate=60.0,
            avg_winner=2.5,
            avg_loser=-1.25,
            rr_ratio=2.0,
            ev=0.875,
            kelly=40.0,
        )
        panel.update_metrics(metrics)

        text = panel._cards["ev"]._value_widget.text()
        assert "+" in text
        assert "%" in text

    def test_kelly_percent(self, qtbot: QtBot) -> None:
        """Kelly displays with percent sign."""
        panel = MetricsPanel()
        qtbot.addWidget(panel)

        metrics = TradingMetrics(
            num_trades=100,
            win_rate=60.0,
            avg_winner=2.5,
            avg_loser=-1.25,
            rr_ratio=2.0,
            ev=0.875,
            kelly=40.0,
        )
        panel.update_metrics(metrics)

        text = panel._cards["kelly"]._value_widget.text()
        assert "40.0" in text
        assert "%" in text

    def test_none_values_display_dash(self, qtbot: QtBot) -> None:
        """None values display em dash."""
        panel = MetricsPanel()
        qtbot.addWidget(panel)

        # Metrics with None values (edge case: no losers)
        metrics = TradingMetrics(
            num_trades=100,
            win_rate=100.0,
            avg_winner=2.5,
            avg_loser=None,
            rr_ratio=None,
            ev=None,
            kelly=None,
        )
        panel.update_metrics(metrics)

        # avg_loser should show dash
        assert "\u2014" in panel._cards["avg_loser"]._value_widget.text()
        assert "\u2014" in panel._cards["rr_ratio"]._value_widget.text()
