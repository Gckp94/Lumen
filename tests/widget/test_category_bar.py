"""Tests for CategoryBar component."""

import pytest
from PyQt6.QtCore import Qt
from pytestqt.qtbot import QtBot

from src.ui.components.category_bar import CategoryBar
from src.ui.tab_categories import get_all_categories


class TestCategoryBar:
    """Tests for CategoryBar widget."""

    def test_category_bar_emits_signal_on_click(self, qtbot: QtBot) -> None:
        """Clicking a category button emits category_changed signal."""
        bar = CategoryBar()
        qtbot.addWidget(bar)

        with qtbot.waitSignal(bar.category_changed, timeout=1000) as blocker:
            # Find and click the MONTE CARLO button
            simulate_btn = bar._category_buttons["MONTE CARLO"]
            qtbot.mouseClick(simulate_btn, Qt.MouseButton.LeftButton)

        assert blocker.args == ["MONTE CARLO"]

    def test_category_bar_has_all_categories(self, qtbot: QtBot) -> None:
        """CategoryBar has buttons for all categories."""
        bar = CategoryBar()
        qtbot.addWidget(bar)

        for category in get_all_categories():
            assert category in bar._category_buttons

    def test_category_bar_default_active_is_analyze(self, qtbot: QtBot) -> None:
        """Default active category is ANALYZE."""
        bar = CategoryBar()
        qtbot.addWidget(bar)

        assert bar.active_category == "ANALYZE"
        assert bar._category_buttons["ANALYZE"].isChecked()

    def test_set_active_category_updates_state(self, qtbot: QtBot) -> None:
        """set_active_category updates visual state without emitting signal."""
        bar = CategoryBar()
        qtbot.addWidget(bar)

        bar.set_active_category("PORTFOLIO")

        assert bar.active_category == "PORTFOLIO"
        assert bar._category_buttons["PORTFOLIO"].isChecked()
        assert not bar._category_buttons["ANALYZE"].isChecked()

    def test_set_active_category_does_not_emit_signal(self, qtbot: QtBot) -> None:
        """set_active_category does NOT emit category_changed signal."""
        bar = CategoryBar()
        qtbot.addWidget(bar)

        # Verify NO signal is emitted when calling set_active_category
        with pytest.raises(qtbot.TimeoutError):
            with qtbot.waitSignal(
                bar.category_changed, timeout=100, raising=True
            ):
                bar.set_active_category("MONTE CARLO")

        # State should still be updated
        assert bar.active_category == "MONTE CARLO"

    def test_set_active_category_invalid_category(self, qtbot: QtBot) -> None:
        """Invalid category doesn't crash or change state."""
        bar = CategoryBar()
        qtbot.addWidget(bar)

        original_category = bar.active_category

        # Passing invalid category should not crash
        bar.set_active_category("INVALID_CATEGORY")

        # State should remain unchanged
        assert bar.active_category == original_category
        assert bar._category_buttons[original_category].isChecked()
