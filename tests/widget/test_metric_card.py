"""Widget tests for MetricCard."""

from pytestqt.qtbot import QtBot

from src.ui.components.metric_card import MetricCard
from src.ui.constants import Colors


class TestMetricCardDisplay:
    """Tests for MetricCard display functionality."""

    def test_card_displays_label(self, qtbot: QtBot) -> None:
        """Card displays label correctly."""
        card = MetricCard(label="Win Rate")
        qtbot.addWidget(card)

        assert "Win Rate" in card._label_widget.text()

    def test_card_displays_value(self, qtbot: QtBot) -> None:
        """Card displays formatted value."""
        card = MetricCard(label="Win Rate")
        qtbot.addWidget(card)

        card.update_value(67.5, format_spec=".1f")
        assert "67.5" in card._value_widget.text()

    def test_card_displays_dash_initially(self, qtbot: QtBot) -> None:
        """Card displays em dash initially."""
        card = MetricCard(label="EV")
        qtbot.addWidget(card)

        # Em dash character
        assert "\u2014" in card._value_widget.text()


class TestMetricCardColorCoding:
    """Tests for MetricCard color coding."""

    def test_positive_color(self, qtbot: QtBot) -> None:
        """Positive values use SIGNAL_CYAN."""
        card = MetricCard(label="EV")
        qtbot.addWidget(card)

        card.update_value(3.2)
        style = card._value_widget.styleSheet()
        assert Colors.SIGNAL_CYAN in style

    def test_negative_color(self, qtbot: QtBot) -> None:
        """Negative values use SIGNAL_CORAL."""
        card = MetricCard(label="Avg Loser")
        qtbot.addWidget(card)

        card.update_value(-2.5)
        style = card._value_widget.styleSheet()
        assert Colors.SIGNAL_CORAL in style

    def test_zero_color(self, qtbot: QtBot) -> None:
        """Zero values use TEXT_PRIMARY."""
        card = MetricCard(label="EV")
        qtbot.addWidget(card)

        card.update_value(0.0)
        style = card._value_widget.styleSheet()
        assert Colors.TEXT_PRIMARY in style

    def test_none_displays_dash(self, qtbot: QtBot) -> None:
        """None values display em dash."""
        card = MetricCard(label="R:R")
        qtbot.addWidget(card)

        card.update_value(None)
        assert "\u2014" in card._value_widget.text()

    def test_none_uses_primary_color(self, qtbot: QtBot) -> None:
        """None values use TEXT_PRIMARY color."""
        card = MetricCard(label="R:R")
        qtbot.addWidget(card)

        card.update_value(None)
        style = card._value_widget.styleSheet()
        assert Colors.TEXT_PRIMARY in style


class TestMetricCardFormatting:
    """Tests for MetricCard number formatting."""

    def test_integer_formatting(self, qtbot: QtBot) -> None:
        """Integer values use thousands separator."""
        card = MetricCard(label="Trades")
        qtbot.addWidget(card)

        card.update_value(12847)
        assert "12,847" in card._value_widget.text()

    def test_format_spec_applied(self, qtbot: QtBot) -> None:
        """Format spec is applied correctly."""
        card = MetricCard(label="Win Rate")
        qtbot.addWidget(card)

        card.update_value(67.567, format_spec=".1f")
        assert "67.6" in card._value_widget.text()

    def test_signed_format(self, qtbot: QtBot) -> None:
        """Signed format shows plus sign for positive."""
        card = MetricCard(label="Avg Winner")
        qtbot.addWidget(card)

        card.update_value(2.5, format_spec="+.2f")
        assert "+2.50" in card._value_widget.text()

    def test_signed_format_negative(self, qtbot: QtBot) -> None:
        """Signed format shows minus sign for negative."""
        card = MetricCard(label="Avg Loser")
        qtbot.addWidget(card)

        card.update_value(-1.5, format_spec="+.2f")
        assert "-1.50" in card._value_widget.text()


class TestMetricCardVariants:
    """Tests for MetricCard size variants."""

    def test_standard_variant(self, qtbot: QtBot) -> None:
        """Standard variant has 24px font."""
        card = MetricCard(label="Test", variant=MetricCard.STANDARD)
        qtbot.addWidget(card)

        style = card.styleSheet()
        assert "24px" in style

    def test_hero_variant(self, qtbot: QtBot) -> None:
        """Hero variant has 56px font."""
        card = MetricCard(label="Test", variant=MetricCard.HERO)
        qtbot.addWidget(card)

        style = card.styleSheet()
        assert "56px" in style

    def test_compact_variant(self, qtbot: QtBot) -> None:
        """Compact variant has 16px font."""
        card = MetricCard(label="Test", variant=MetricCard.COMPACT)
        qtbot.addWidget(card)

        style = card.styleSheet()
        assert "16px" in style


class TestMetricCardStyling:
    """Tests for MetricCard styling."""

    def test_card_has_object_name(self, qtbot: QtBot) -> None:
        """Card has correct object name for styling."""
        card = MetricCard(label="Test")
        qtbot.addWidget(card)

        assert card.objectName() == "metricCard"

    def test_card_has_elevated_background(self, qtbot: QtBot) -> None:
        """Card has BG_ELEVATED background in stylesheet."""
        card = MetricCard(label="Test")
        qtbot.addWidget(card)

        style = card.styleSheet()
        assert Colors.BG_ELEVATED in style

    def test_label_has_secondary_color(self, qtbot: QtBot) -> None:
        """Label has TEXT_SECONDARY color in stylesheet."""
        card = MetricCard(label="Test")
        qtbot.addWidget(card)

        style = card.styleSheet()
        assert Colors.TEXT_SECONDARY in style
