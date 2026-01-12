"""Widget tests for DistributionCard."""

from PyQt6.QtWidgets import QLabel
from pytestqt.qtbot import QtBot

from src.ui.components.distribution_card import DistributionCard
from src.ui.constants import Colors


class TestDistributionCardDisplay:
    """Tests for DistributionCard display functionality."""

    def test_winner_card_has_cyan_border(self, qtbot: QtBot) -> None:
        """Winner card displays with cyan border."""
        card = DistributionCard(DistributionCard.WINNER)
        qtbot.addWidget(card)
        style = card.styleSheet()
        assert Colors.SIGNAL_CYAN in style

    def test_loser_card_has_coral_border(self, qtbot: QtBot) -> None:
        """Loser card displays with coral border."""
        card = DistributionCard(DistributionCard.LOSER)
        qtbot.addWidget(card)
        style = card.styleSheet()
        assert Colors.SIGNAL_CORAL in style

    def test_winner_header_text(self, qtbot: QtBot) -> None:
        """Winner card has 'Winners' header."""
        card = DistributionCard(DistributionCard.WINNER)
        qtbot.addWidget(card)
        assert card._header.text() == "Winners"

    def test_loser_header_text(self, qtbot: QtBot) -> None:
        """Loser card has 'Losers' header."""
        card = DistributionCard(DistributionCard.LOSER)
        qtbot.addWidget(card)
        assert card._header.text() == "Losers"


class TestDistributionCardStats:
    """Tests for DistributionCard statistics display."""

    def test_update_stats_displays_values(self, qtbot: QtBot) -> None:
        """Updated stats are displayed in the card."""
        card = DistributionCard(DistributionCard.WINNER)
        qtbot.addWidget(card)
        card.update_stats(
            count=100,
            min_val=0.5,
            max_val=25.0,
            mean=5.5,
            median=4.2,
            std=3.1,
            suggested_bins=15,
        )
        # Verify key values are visible in card
        count_label = card.findChild(QLabel, "countLabel")
        assert count_label is not None
        assert "100" in count_label.text()

    def test_update_stats_displays_range(self, qtbot: QtBot) -> None:
        """Range displays min and max values."""
        card = DistributionCard(DistributionCard.WINNER)
        qtbot.addWidget(card)
        card.update_stats(
            count=50,
            min_val=1.5,
            max_val=15.0,
            mean=5.0,
            median=4.0,
            std=2.5,
        )
        range_label = card.findChild(QLabel, "rangeLabel")
        assert range_label is not None
        assert "1.50%" in range_label.text()
        assert "15.00%" in range_label.text()

    def test_update_stats_displays_mean(self, qtbot: QtBot) -> None:
        """Mean value is displayed correctly."""
        card = DistributionCard(DistributionCard.LOSER)
        qtbot.addWidget(card)
        card.update_stats(
            count=30,
            min_val=-10.0,
            max_val=-0.5,
            mean=-4.8,
            median=-3.5,
            std=2.9,
        )
        mean_label = card.findChild(QLabel, "meanLabel")
        assert mean_label is not None
        assert "-4.80%" in mean_label.text()

    def test_clear_shows_em_dash(self, qtbot: QtBot) -> None:
        """Clear method shows em dash for all values."""
        card = DistributionCard(DistributionCard.WINNER)
        qtbot.addWidget(card)
        card.update_stats(
            count=100,
            min_val=1.0,
            max_val=10.0,
            mean=5.0,
            median=4.5,
            std=2.0,
        )
        card.clear()
        # Verify em dash is shown
        count_label = card.findChild(QLabel, "countLabel")
        assert count_label is not None
        assert count_label.text() == "\u2014"

    def test_clear_clears_all_labels(self, qtbot: QtBot) -> None:
        """Clear method resets all stat labels."""
        card = DistributionCard(DistributionCard.WINNER)
        qtbot.addWidget(card)
        card.update_stats(
            count=100,
            min_val=1.0,
            max_val=10.0,
            mean=5.0,
            median=4.5,
            std=2.0,
        )
        card.clear()
        # Check all labels are cleared
        for label_name in ["countLabel", "rangeLabel", "meanLabel", "medianLabel", "stdLabel"]:
            label = card.findChild(QLabel, label_name)
            assert label is not None
            assert label.text() == "\u2014"


class TestDistributionCardSignals:
    """Tests for DistributionCard signals."""

    def test_view_histogram_signal_emitted(self, qtbot: QtBot) -> None:
        """Clicking View Histogram emits signal."""
        card = DistributionCard(DistributionCard.WINNER)
        qtbot.addWidget(card)

        with qtbot.waitSignal(card.view_histogram_clicked, timeout=1000):
            # Simulate click on histogram link via clicked signal
            card._histogram_link.clicked.emit()

    def test_histogram_link_exists(self, qtbot: QtBot) -> None:
        """Histogram link is present in the card."""
        card = DistributionCard(DistributionCard.WINNER)
        qtbot.addWidget(card)

        link = card.findChild(QLabel, "histogramLink")
        assert link is not None
        assert "View Histogram" in link.text()


class TestDistributionCardProperties:
    """Tests for DistributionCard properties."""

    def test_card_type_property_winner(self, qtbot: QtBot) -> None:
        """Card type property returns WINNER for winner card."""
        card = DistributionCard(DistributionCard.WINNER)
        qtbot.addWidget(card)
        assert card.card_type == DistributionCard.WINNER

    def test_card_type_property_loser(self, qtbot: QtBot) -> None:
        """Card type property returns LOSER for loser card."""
        card = DistributionCard(DistributionCard.LOSER)
        qtbot.addWidget(card)
        assert card.card_type == DistributionCard.LOSER

    def test_suggested_bins_stored(self, qtbot: QtBot) -> None:
        """Suggested bins value is stored."""
        card = DistributionCard(DistributionCard.WINNER)
        qtbot.addWidget(card)
        card.update_stats(
            count=100,
            min_val=0.5,
            max_val=25.0,
            mean=5.5,
            median=4.2,
            std=3.1,
            suggested_bins=15,
        )
        assert card._suggested_bins == 15


class TestDistributionCardStyling:
    """Tests for DistributionCard styling."""

    def test_card_has_elevated_background(self, qtbot: QtBot) -> None:
        """Card has BG_ELEVATED background in stylesheet."""
        card = DistributionCard(DistributionCard.WINNER)
        qtbot.addWidget(card)

        style = card.styleSheet()
        assert Colors.BG_ELEVATED in style

    def test_histogram_link_has_blue_color(self, qtbot: QtBot) -> None:
        """Histogram link has SIGNAL_BLUE color."""
        card = DistributionCard(DistributionCard.WINNER)
        qtbot.addWidget(card)

        link = card._histogram_link
        style = link.styleSheet()
        assert Colors.SIGNAL_BLUE in style

    def test_card_has_minimum_size(self, qtbot: QtBot) -> None:
        """Card has minimum width and height set."""
        card = DistributionCard(DistributionCard.WINNER)
        qtbot.addWidget(card)

        assert card.minimumWidth() >= 200
        assert card.minimumHeight() >= 180


class TestDistributionCardNoneHandling:
    """Tests for DistributionCard handling None values."""

    def test_none_count_shows_dash(self, qtbot: QtBot) -> None:
        """None count shows em dash."""
        card = DistributionCard(DistributionCard.WINNER)
        qtbot.addWidget(card)
        card.update_stats(
            count=None,
            min_val=1.0,
            max_val=10.0,
            mean=5.0,
            median=4.5,
            std=2.0,
        )
        count_label = card.findChild(QLabel, "countLabel")
        assert count_label is not None
        assert count_label.text() == "\u2014"

    def test_none_range_shows_dash(self, qtbot: QtBot) -> None:
        """None range values show em dash."""
        card = DistributionCard(DistributionCard.WINNER)
        qtbot.addWidget(card)
        card.update_stats(
            count=100,
            min_val=None,
            max_val=None,
            mean=5.0,
            median=4.5,
            std=2.0,
        )
        range_label = card.findChild(QLabel, "rangeLabel")
        assert range_label is not None
        assert range_label.text() == "\u2014"

    def test_none_mean_shows_dash(self, qtbot: QtBot) -> None:
        """None mean shows em dash."""
        card = DistributionCard(DistributionCard.WINNER)
        qtbot.addWidget(card)
        card.update_stats(
            count=100,
            min_val=1.0,
            max_val=10.0,
            mean=None,
            median=4.5,
            std=2.0,
        )
        mean_label = card.findChild(QLabel, "meanLabel")
        assert mean_label is not None
        assert mean_label.text() == "\u2014"
