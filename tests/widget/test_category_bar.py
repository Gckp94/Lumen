"""Tests for CategoryBar component."""

import pytest
from PyQt6.QtCore import Qt
from pytestqt.qtbot import QtBot

from src.ui.components.category_bar import CategoryBar


class TestCategoryBar:
    """Tests for CategoryBar widget."""

    def test_category_bar_emits_signal_on_click(self, qtbot: QtBot) -> None:
        """Clicking a category button emits category_changed signal."""
        bar = CategoryBar()
        qtbot.addWidget(bar)

        with qtbot.waitSignal(bar.category_changed, timeout=1000) as blocker:
            # Find and click the SIMULATE button
            simulate_btn = bar._category_buttons["SIMULATE"]
            qtbot.mouseClick(simulate_btn, Qt.MouseButton.LeftButton)

        assert blocker.args == ["SIMULATE"]

    def test_category_bar_has_all_categories(self, qtbot: QtBot) -> None:
        """CategoryBar has buttons for all categories."""
        bar = CategoryBar()
        qtbot.addWidget(bar)

        from src.ui.tab_categories import get_all_categories

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
