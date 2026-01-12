"""Widget tests for BaselineInfoCard."""

from PyQt6.QtWidgets import QLabel
from pytestqt.qtbot import QtBot

from src.tabs.data_input import BaselineInfoCard


class TestBaselineInfoCardDisplay:
    """Tests for BaselineInfoCard display functionality."""

    def test_card_displays_correct_message(self, qtbot: QtBot) -> None:
        """Card displays correct formatted message."""
        card = BaselineInfoCard()
        qtbot.addWidget(card)

        card.update_counts(total_rows=12847, baseline_rows=4231)

        label = card.findChild(QLabel, "message_label")
        assert label is not None
        text = label.text()
        assert "4,231" in text
        assert "12,847" in text
        assert "first triggers" in text.lower()

    def test_card_displays_baseline_keyword(self, qtbot: QtBot) -> None:
        """Card displays 'Baseline' in message."""
        card = BaselineInfoCard()
        qtbot.addWidget(card)

        card.update_counts(total_rows=1000, baseline_rows=500)

        label = card.findChild(QLabel, "message_label")
        assert label is not None
        assert "Baseline" in label.text()


class TestBaselineInfoCardFormatting:
    """Tests for BaselineInfoCard number formatting."""

    def test_thousands_separator_large_numbers(self, qtbot: QtBot) -> None:
        """Numbers use thousands separator."""
        card = BaselineInfoCard()
        qtbot.addWidget(card)

        card.update_counts(total_rows=100000, baseline_rows=50000)

        label = card.findChild(QLabel, "message_label")
        assert label is not None
        assert "100,000" in label.text()
        assert "50,000" in label.text()

    def test_thousands_separator_small_numbers(self, qtbot: QtBot) -> None:
        """Small numbers don't have separators."""
        card = BaselineInfoCard()
        qtbot.addWidget(card)

        card.update_counts(total_rows=100, baseline_rows=50)

        label = card.findChild(QLabel, "message_label")
        assert label is not None
        # Small numbers shouldn't have commas
        assert "100" in label.text()
        assert "50" in label.text()

    def test_update_counts_changes_display(self, qtbot: QtBot) -> None:
        """update_counts method updates the display."""
        card = BaselineInfoCard()
        qtbot.addWidget(card)

        # Initial update
        card.update_counts(total_rows=1000, baseline_rows=500)
        label = card.findChild(QLabel, "message_label")
        assert label is not None
        assert "1,000" in label.text()
        assert "500" in label.text()

        # Second update with different values
        card.update_counts(total_rows=2000, baseline_rows=750)
        assert "2,000" in label.text()
        assert "750" in label.text()


class TestBaselineInfoCardStyling:
    """Tests for BaselineInfoCard styling."""

    def test_card_has_blue_border_in_stylesheet(self, qtbot: QtBot) -> None:
        """Card has stellar-blue left border in stylesheet."""
        card = BaselineInfoCard()
        qtbot.addWidget(card)

        style = card.styleSheet()
        # Check for blue border color (#4A9EFF or SIGNAL_BLUE)
        assert "4A9EFF" in style.upper() or "#4a9eff" in style.lower()

    def test_card_has_correct_object_name(self, qtbot: QtBot) -> None:
        """Card has correct object name for styling."""
        card = BaselineInfoCard()
        qtbot.addWidget(card)

        assert card.objectName() == "baselineInfoCard"

    def test_message_label_has_object_name(self, qtbot: QtBot) -> None:
        """Message label has correct object name."""
        card = BaselineInfoCard()
        qtbot.addWidget(card)

        label = card.findChild(QLabel, "message_label")
        assert label is not None
        assert label.objectName() == "message_label"
