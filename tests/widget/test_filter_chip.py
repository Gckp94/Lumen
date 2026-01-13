"""Widget tests for FilterChip component."""

from pytestqt.qtbot import QtBot

from src.core.models import FilterCriteria
from src.ui.components.filter_chip import FilterChip
from src.ui.constants import Colors


class TestFilterChipDisplay:
    """Tests for FilterChip display."""

    def test_chip_displays_between_summary(self, qtbot: QtBot) -> None:
        """FilterChip shows filter criteria summary for 'between' operator."""
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=0, max_val=10
        )
        chip = FilterChip(criteria)
        qtbot.addWidget(chip)

        label_text = chip._label.text()
        assert "gain_pct" in label_text
        assert "between" in label_text
        assert "0" in label_text
        assert "10" in label_text

    def test_chip_displays_not_between_summary(self, qtbot: QtBot) -> None:
        """FilterChip shows filter criteria summary for 'not_between' operator."""
        criteria = FilterCriteria(
            column="volume", operator="not_between", min_val=100, max_val=500
        )
        chip = FilterChip(criteria)
        qtbot.addWidget(chip)

        label_text = chip._label.text()
        assert "volume" in label_text
        assert "not between" in label_text
        assert "100" in label_text
        assert "500" in label_text


class TestFilterChipRemoveSignal:
    """Tests for remove button signal."""

    def test_remove_button_emits_signal(self, qtbot: QtBot) -> None:
        """Remove button emits signal with criteria."""
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=0, max_val=10
        )
        chip = FilterChip(criteria)
        qtbot.addWidget(chip)

        with qtbot.waitSignal(chip.removed, timeout=1000) as blocker:
            chip._remove_btn.click()

        assert blocker.args[0] == criteria

    def test_remove_signal_passes_original_criteria(self, qtbot: QtBot) -> None:
        """Remove signal passes the exact criteria object."""
        criteria = FilterCriteria(
            column="price", operator="not_between", min_val=-5.5, max_val=5.5
        )
        chip = FilterChip(criteria)
        qtbot.addWidget(chip)

        received_criteria = None

        def capture_criteria(c: FilterCriteria) -> None:
            nonlocal received_criteria
            received_criteria = c

        chip.removed.connect(capture_criteria)
        chip._remove_btn.click()

        assert received_criteria is criteria


class TestFilterChipStyle:
    """Tests for FilterChip styling."""

    def test_chip_has_amber_background(self, qtbot: QtBot) -> None:
        """FilterChip is styled with amber background."""
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=0, max_val=10
        )
        chip = FilterChip(criteria)
        qtbot.addWidget(chip)

        stylesheet = chip.styleSheet()
        assert Colors.SIGNAL_AMBER in stylesheet

    def test_chip_has_remove_button(self, qtbot: QtBot) -> None:
        """FilterChip has a remove button."""
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=0, max_val=10
        )
        chip = FilterChip(criteria)
        qtbot.addWidget(chip)

        assert chip._remove_btn is not None
        # Check button is not hidden (isHidden() returns False when not explicitly hidden)
        assert not chip._remove_btn.isHidden()

    def test_chip_label_has_dark_text_color(self, qtbot: QtBot) -> None:
        """FilterChip label text is dark for readability on amber background."""
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=0, max_val=10
        )
        chip = FilterChip(criteria)
        qtbot.addWidget(chip)

        stylesheet = chip.styleSheet()
        # Text should be dark (BG_BASE) for contrast on amber
        assert f"color: {Colors.BG_BASE}" in stylesheet
