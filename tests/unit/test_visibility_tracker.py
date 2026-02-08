"""Tests for VisibilityTracker."""

from unittest.mock import MagicMock, patch

import pytest
from pytestqt.qtbot import QtBot

from src.core.visibility_tracker import VisibilityTracker


class TestVisibilityTracker:
    """Tests for VisibilityTracker."""

    def test_is_visible_returns_false_for_hidden_dock(self, qtbot: QtBot) -> None:
        """Hidden dock widget should not be visible."""
        tracker = VisibilityTracker()

        dock = MagicMock()
        dock.isVisible.return_value = False

        assert tracker.is_visible(dock) is False

    def test_is_visible_returns_false_when_behind_other_tab(
        self, qtbot: QtBot
    ) -> None:
        """Dock behind another tab in same area should not be visible."""
        tracker = VisibilityTracker()

        dock = MagicMock()
        dock.isVisible.return_value = True

        area = MagicMock()
        other_dock = MagicMock()
        area.currentDockWidget.return_value = other_dock  # Different dock is active
        dock.dockAreaWidget.return_value = area

        assert tracker.is_visible(dock) is False

    def test_is_visible_returns_true_when_active_tab(self, qtbot: QtBot) -> None:
        """Dock that is the active tab should be visible."""
        tracker = VisibilityTracker()

        dock = MagicMock()
        dock.isVisible.return_value = True

        area = MagicMock()
        area.currentDockWidget.return_value = dock  # This dock is active
        dock.dockAreaWidget.return_value = area

        container = MagicMock()
        container.isFloating.return_value = False
        dock.dockContainer.return_value = container

        assert tracker.is_visible(dock) is True

    def test_is_visible_returns_false_when_floating_minimized(
        self, qtbot: QtBot
    ) -> None:
        """Floating minimized window should not be visible."""
        tracker = VisibilityTracker()

        dock = MagicMock()
        dock.isVisible.return_value = True

        area = MagicMock()
        area.currentDockWidget.return_value = dock
        dock.dockAreaWidget.return_value = area

        container = MagicMock()
        container.isFloating.return_value = True
        container.isMinimized.return_value = True
        dock.dockContainer.return_value = container

        assert tracker.is_visible(dock) is False

    def test_mark_stale_and_is_stale(self, qtbot: QtBot) -> None:
        """mark_stale should flag tab, is_stale should return True."""
        tracker = VisibilityTracker()

        tracker.mark_stale("PnL Stats")

        assert tracker.is_stale("PnL Stats") is True
        assert tracker.is_stale("Statistics") is False

    def test_clear_stale_removes_flag(self, qtbot: QtBot) -> None:
        """clear_stale should remove stale flag."""
        tracker = VisibilityTracker()

        tracker.mark_stale("PnL Stats")
        tracker.clear_stale("PnL Stats")

        assert tracker.is_stale("PnL Stats") is False
