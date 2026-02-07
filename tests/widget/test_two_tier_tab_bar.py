"""Tests for TwoTierTabBar widget."""

import pytest
from pytestqt.qtbot import QtBot
from PyQt6.QtCore import Qt

from src.ui.components.two_tier_tab_bar import TwoTierTabBar


class TestTwoTierTabBarCreation:
    """Test widget creation."""

    def test_creates_with_categories(self, qtbot: QtBot) -> None:
        """Widget should show category buttons."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)

        assert len(bar._category_buttons) == 5
        assert "ANALYZE" in bar._category_buttons
        assert "CHARTS" in bar._category_buttons

    def test_first_category_active_by_default(self, qtbot: QtBot) -> None:
        """ANALYZE should be active by default."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)

        assert bar.active_category == "ANALYZE"

    def test_shows_tabs_for_active_category(self, qtbot: QtBot) -> None:
        """Should show tab buttons for active category."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)

        visible_tabs = [t for t, btn in bar._tab_buttons.items() if not btn.isHidden()]
        assert "Data Input" in visible_tabs
        assert "Feature Explorer" in visible_tabs


class TestTwoTierTabBarInteraction:
    """Test user interaction."""

    def test_clicking_category_changes_tabs(self, qtbot: QtBot) -> None:
        """Clicking category should show its tabs."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)

        qtbot.mouseClick(bar._category_buttons["PORTFOLIO"], Qt.MouseButton.LeftButton)

        assert bar.active_category == "PORTFOLIO"
        assert not bar._tab_buttons["Portfolio Overview"].isHidden()
        assert bar._tab_buttons["Data Input"].isHidden()

    def test_tab_activated_signal(self, qtbot: QtBot) -> None:
        """Clicking tab should emit tab_activated signal."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)

        with qtbot.waitSignal(bar.tab_activated, timeout=1000) as blocker:
            qtbot.mouseClick(bar._tab_buttons["Feature Explorer"], Qt.MouseButton.LeftButton)

        assert blocker.args == ["Feature Explorer"]


class TestTwoTierTabBarProperties:
    """Test property accessors."""

    def test_active_tab_property(self, qtbot: QtBot) -> None:
        """Active tab should be set after category selection."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)

        # First tab in ANALYZE should be active by default
        assert bar.active_tab == "Data Input"

    def test_active_category_property(self, qtbot: QtBot) -> None:
        """Active category should change when clicked."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)

        qtbot.mouseClick(bar._category_buttons["SIMULATE"], Qt.MouseButton.LeftButton)
        assert bar.active_category == "SIMULATE"


class TestTwoTierTabBarSetActiveTab:
    """Test set_active_tab method."""

    def test_set_active_tab_same_category(self, qtbot: QtBot) -> None:
        """set_active_tab should select tab in same category."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)

        bar.set_active_tab("Feature Explorer")

        assert bar.active_tab == "Feature Explorer"
        assert bar.active_category == "ANALYZE"

    def test_set_active_tab_different_category(self, qtbot: QtBot) -> None:
        """set_active_tab should switch category if needed."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)

        bar.set_active_tab("Monte Carlo")

        assert bar.active_tab == "Monte Carlo"
        assert bar.active_category == "SIMULATE"

    def test_set_active_tab_emits_signals(self, qtbot: QtBot) -> None:
        """set_active_tab should emit tab_activated signal."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)

        with qtbot.waitSignal(bar.tab_activated, timeout=1000) as blocker:
            bar.set_active_tab("Chart Viewer")

        assert blocker.args == ["Chart Viewer"]


class TestTwoTierTabBarCategoryChanged:
    """Test category_changed signal."""

    def test_category_changed_signal(self, qtbot: QtBot) -> None:
        """Clicking category should emit category_changed signal."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)

        with qtbot.waitSignal(bar.category_changed, timeout=1000) as blocker:
            qtbot.mouseClick(bar._category_buttons["FEATURES"], Qt.MouseButton.LeftButton)

        assert blocker.args == ["FEATURES"]

    def test_category_button_checked_state(self, qtbot: QtBot) -> None:
        """Only active category button should be checked."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)

        qtbot.mouseClick(bar._category_buttons["CHARTS"], Qt.MouseButton.LeftButton)

        assert bar._category_buttons["CHARTS"].isChecked()
        assert not bar._category_buttons["ANALYZE"].isChecked()
        assert not bar._category_buttons["PORTFOLIO"].isChecked()

    def test_tab_button_checked_state(self, qtbot: QtBot) -> None:
        """Only active tab button should be checked."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)

        qtbot.mouseClick(bar._tab_buttons["Breakdown"], Qt.MouseButton.LeftButton)

        assert bar._tab_buttons["Breakdown"].isChecked()
        assert not bar._tab_buttons["Data Input"].isChecked()


class TestTwoTierTabBarKeyboard:
    """Test keyboard navigation."""

    def test_ctrl_number_switches_category(self, qtbot: QtBot) -> None:
        """Ctrl+1-5 should switch categories."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)
        bar.setFocus()

        # Ctrl+3 should switch to FEATURES (index 2, 1-based = 3)
        qtbot.keyClick(bar, Qt.Key.Key_3, Qt.KeyboardModifier.ControlModifier)

        assert bar.active_category == "FEATURES"

    def test_ctrl_tab_cycles_tabs(self, qtbot: QtBot) -> None:
        """Ctrl+Tab should cycle to next tab in category."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)
        bar.set_active_tab("Data Input")

        qtbot.keyClick(bar, Qt.Key.Key_Tab, Qt.KeyboardModifier.ControlModifier)

        assert bar.active_tab == "Feature Explorer"

    def test_ctrl_shift_tab_cycles_backwards(self, qtbot: QtBot) -> None:
        """Ctrl+Shift+Tab should cycle to previous tab."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)
        bar.set_active_tab("Feature Explorer")

        qtbot.keyClick(bar, Qt.Key.Key_Tab,
                       Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)

        assert bar.active_tab == "Data Input"

    def test_tab_cycling_wraps_around(self, qtbot: QtBot) -> None:
        """Tab cycling should wrap around at boundaries."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)
        bar.set_active_tab("Data Binning")  # Last tab in ANALYZE

        qtbot.keyClick(bar, Qt.Key.Key_Tab, Qt.KeyboardModifier.ControlModifier)

        assert bar.active_tab == "Data Input"  # Wraps to first
