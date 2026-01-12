"""Widget tests for ComparisonRibbon."""

from pytestqt.qtbot import QtBot

from src.core.models import TradingMetrics
from src.ui.components.comparison_ribbon import METRICS, ComparisonRibbon
from src.ui.constants import Colors


def _create_test_metrics(
    num_trades: int = 1000,
    win_rate: float = 60.0,
    ev: float = 2.5,
    kelly: float = 12.0,
) -> TradingMetrics:
    """Create TradingMetrics for testing."""
    return TradingMetrics(
        num_trades=num_trades,
        win_rate=win_rate,
        avg_winner=5.0,
        avg_loser=-2.0,
        rr_ratio=2.5,
        ev=ev,
        kelly=kelly,
    )


class TestComparisonRibbonDisplay:
    """Tests for ComparisonRibbon display functionality."""

    def test_ribbon_displays_four_metrics(self, qtbot: QtBot) -> None:
        """Ribbon displays all 4 metrics (trades, win_rate, ev, kelly)."""
        ribbon = ComparisonRibbon()
        qtbot.addWidget(ribbon)

        assert len(ribbon._cards) == 4
        for metric in METRICS:
            assert metric in ribbon._cards

    def test_ribbon_has_correct_metrics_labels(self, qtbot: QtBot) -> None:
        """Ribbon cards show correct labels."""
        ribbon = ComparisonRibbon()
        qtbot.addWidget(ribbon)

        assert "Trades" in ribbon._cards["trades"]._label_widget.text()
        assert "Win Rate" in ribbon._cards["win_rate"]._label_widget.text()
        assert "EV" in ribbon._cards["ev"]._label_widget.text()
        assert "Kelly" in ribbon._cards["kelly"]._label_widget.text()

    def test_ribbon_has_object_name(self, qtbot: QtBot) -> None:
        """Ribbon has correct object name for styling."""
        ribbon = ComparisonRibbon()
        qtbot.addWidget(ribbon)

        assert ribbon.objectName() == "comparisonRibbon"


class TestComparisonRibbonUpdate:
    """Tests for ComparisonRibbon update method."""

    def test_update_shows_filtered_values(self, qtbot: QtBot) -> None:
        """Update shows filtered values in cards."""
        ribbon = ComparisonRibbon()
        qtbot.addWidget(ribbon)

        baseline = _create_test_metrics(num_trades=1000, win_rate=60.0, ev=2.5, kelly=12.0)
        filtered = _create_test_metrics(num_trades=500, win_rate=70.0, ev=3.5, kelly=15.0)

        ribbon.set_values(baseline, filtered)

        # Check trades value
        assert "500" in ribbon._cards["trades"]._value_widget.text()
        # Check win_rate value
        assert "70.0%" in ribbon._cards["win_rate"]._value_widget.text()
        # Check ev value
        assert "3.50%" in ribbon._cards["ev"]._value_widget.text()
        # Check kelly value
        assert "15.0%" in ribbon._cards["kelly"]._value_widget.text()

    def test_update_shows_delta_indicators(self, qtbot: QtBot) -> None:
        """Update shows delta indicators with arrows."""
        ribbon = ComparisonRibbon()
        qtbot.addWidget(ribbon)

        baseline = _create_test_metrics(num_trades=1000, win_rate=60.0, ev=2.5, kelly=12.0)
        filtered = _create_test_metrics(num_trades=500, win_rate=70.0, ev=3.5, kelly=15.0)

        ribbon.set_values(baseline, filtered)

        # Trades decreased - should show down arrow
        trades_delta = ribbon._cards["trades"]._delta_widget.text()
        assert "▼" in trades_delta
        assert "-500" in trades_delta

        # Win rate increased - should show up arrow
        win_rate_delta = ribbon._cards["win_rate"]._delta_widget.text()
        assert "▲" in win_rate_delta
        assert "pp" in win_rate_delta

    def test_update_shows_baseline_reference(self, qtbot: QtBot) -> None:
        """Update shows baseline reference values."""
        ribbon = ComparisonRibbon()
        qtbot.addWidget(ribbon)

        baseline = _create_test_metrics(num_trades=1000, win_rate=60.0, ev=2.5, kelly=12.0)
        filtered = _create_test_metrics(num_trades=500, win_rate=70.0, ev=3.5, kelly=15.0)

        ribbon.set_values(baseline, filtered)

        # Check baseline reference text
        trades_baseline = ribbon._cards["trades"]._baseline_widget.text()
        assert "Baseline:" in trades_baseline
        assert "1,000" in trades_baseline


class TestComparisonRibbonClear:
    """Tests for ComparisonRibbon clear method."""

    def test_clear_shows_empty_state(self, qtbot: QtBot) -> None:
        """Clear shows empty state with em dash."""
        ribbon = ComparisonRibbon()
        qtbot.addWidget(ribbon)

        # First update with values
        baseline = _create_test_metrics()
        filtered = _create_test_metrics()
        ribbon.set_values(baseline, filtered)

        # Then clear
        ribbon.clear()

        # All cards should show em dash
        for metric in METRICS:
            assert "—" in ribbon._cards[metric]._value_widget.text()

    def test_clear_shows_no_filter_message(self, qtbot: QtBot) -> None:
        """Clear shows '(no filter applied)' subtitle."""
        ribbon = ComparisonRibbon()
        qtbot.addWidget(ribbon)

        ribbon.clear()

        # All cards should show no filter message
        for metric in METRICS:
            delta_text = ribbon._cards[metric]._delta_widget.text()
            assert "(no filter applied)" in delta_text

    def test_clear_removes_baseline_reference(self, qtbot: QtBot) -> None:
        """Clear removes baseline reference text."""
        ribbon = ComparisonRibbon()
        qtbot.addWidget(ribbon)

        # First update with values
        baseline = _create_test_metrics()
        filtered = _create_test_metrics()
        ribbon.set_values(baseline, filtered)

        # Then clear
        ribbon.clear()

        # Baseline text should be empty
        for metric in METRICS:
            baseline_text = ribbon._cards[metric]._baseline_widget.text()
            assert baseline_text == ""


class TestComparisonRibbonDeltaColors:
    """Tests for ComparisonRibbon delta color semantics."""

    def test_positive_delta_uses_cyan(self, qtbot: QtBot) -> None:
        """Positive delta (improvement) uses SIGNAL_CYAN."""
        ribbon = ComparisonRibbon()
        qtbot.addWidget(ribbon)

        baseline = _create_test_metrics(win_rate=60.0)
        filtered = _create_test_metrics(win_rate=70.0)  # Improvement

        ribbon.set_values(baseline, filtered)

        style = ribbon._cards["win_rate"]._delta_widget.styleSheet()
        assert Colors.SIGNAL_CYAN in style

    def test_negative_delta_uses_coral(self, qtbot: QtBot) -> None:
        """Negative delta (decline) uses SIGNAL_CORAL."""
        ribbon = ComparisonRibbon()
        qtbot.addWidget(ribbon)

        baseline = _create_test_metrics(win_rate=70.0)
        filtered = _create_test_metrics(win_rate=60.0)  # Decline

        ribbon.set_values(baseline, filtered)

        style = ribbon._cards["win_rate"]._delta_widget.styleSheet()
        assert Colors.SIGNAL_CORAL in style

    def test_zero_delta_uses_secondary(self, qtbot: QtBot) -> None:
        """Zero delta (neutral) uses TEXT_SECONDARY."""
        ribbon = ComparisonRibbon()
        qtbot.addWidget(ribbon)

        baseline = _create_test_metrics(win_rate=60.0)
        filtered = _create_test_metrics(win_rate=60.0)  # No change

        ribbon.set_values(baseline, filtered)

        style = ribbon._cards["win_rate"]._delta_widget.styleSheet()
        assert Colors.TEXT_SECONDARY in style


class TestComparisonRibbonNullHandling:
    """Tests for ComparisonRibbon handling of None values."""

    def test_none_filtered_value_shows_na(self, qtbot: QtBot) -> None:
        """None filtered value shows 'N/A'."""
        ribbon = ComparisonRibbon()
        qtbot.addWidget(ribbon)

        baseline = _create_test_metrics(win_rate=60.0)
        filtered = TradingMetrics(
            num_trades=100,
            win_rate=None,  # None value
            avg_winner=None,
            avg_loser=None,
            rr_ratio=None,
            ev=2.0,
            kelly=10.0,
        )

        ribbon.set_values(baseline, filtered)

        # Win rate should show N/A
        assert "N/A" in ribbon._cards["win_rate"]._value_widget.text()
