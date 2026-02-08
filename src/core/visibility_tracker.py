"""Track which tabs are visible across all windows."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

if TYPE_CHECKING:
    from PyQt6Ads import CDockWidget


class VisibilityTracker(QObject):
    """Tracks visibility of dock widgets across main and floating windows.

    Usage:
        tracker = VisibilityTracker()
        if tracker.is_visible(dock_widget):
            # Recalculate immediately
        else:
            tracker.mark_stale(tab_name)
    """

    tab_became_visible = pyqtSignal(str)  # tab_name

    def __init__(self) -> None:
        """Initialize tracker."""
        super().__init__()
        self._stale_tabs: set[str] = set()

    def is_visible(self, dock_widget: CDockWidget) -> bool:
        """Check if a dock widget is actually visible to the user.

        Args:
            dock_widget: The CDockWidget to check.

        Returns:
            True if the dock is visible, not behind other tabs,
            and not in a minimized floating window.
        """
        # Is the dock widget itself visible?
        if not dock_widget.isVisible():
            return False

        # If in a tab group, is it the active tab?
        area = dock_widget.dockAreaWidget()
        if area is not None and area.currentDockWidget() != dock_widget:
            return False  # Hidden behind another tab

        # Is the containing window visible (not minimized)?
        container = dock_widget.dockContainer()
        if container is not None and container.isFloating():
            if container.isMinimized():
                return False

        return True

    def mark_stale(self, tab_name: str) -> None:
        """Mark a tab as needing recalculation when it becomes visible.

        Args:
            tab_name: Name of the tab to mark stale.
        """
        self._stale_tabs.add(tab_name)

    def is_stale(self, tab_name: str) -> bool:
        """Check if a tab is marked as stale.

        Args:
            tab_name: Name of the tab to check.

        Returns:
            True if tab needs recalculation.
        """
        return tab_name in self._stale_tabs

    def clear_stale(self, tab_name: str) -> None:
        """Clear stale flag for a tab.

        Args:
            tab_name: Name of the tab to clear.
        """
        self._stale_tabs.discard(tab_name)
