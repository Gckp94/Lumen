"""Dockable tab manager using PyQt6Ads.

Provides VS Code-like docking behavior where tabs can be dragged out
to floating windows and docked back.
"""

import logging

import PyQt6Ads as ads
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class DockManager(ads.CDockManager):
    """Manager for dockable tabs using PyQt6Ads.

    Wraps CDockManager to provide a simplified API for adding
    and managing dockable widgets.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the dock manager.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._dock_widgets: dict[str, ads.CDockWidget] = {}

        # Configure docking behavior
        self.setConfigFlag(ads.CDockManager.eConfigFlag.OpaqueSplitterResize, True)
        self.setConfigFlag(ads.CDockManager.eConfigFlag.DockAreaHasTabsMenuButton, True)
        self.setConfigFlag(ads.CDockManager.eConfigFlag.DockAreaHasUndockButton, True)
        self.setConfigFlag(ads.CDockManager.eConfigFlag.FloatingContainerHasWidgetTitle, True)
        self.setConfigFlag(ads.CDockManager.eConfigFlag.FloatingContainerHasWidgetIcon, True)
        self.setConfigFlag(ads.CDockManager.eConfigFlag.AllTabsHaveCloseButton, False)

        logger.debug("DockManager initialized")

    def add_dock(
        self,
        title: str,
        widget: QWidget,
        area: ads.DockWidgetArea = ads.DockWidgetArea.CenterDockWidgetArea,
    ) -> ads.CDockWidget:
        """Add a dockable widget.

        Args:
            title: Tab title.
            widget: Widget to dock.
            area: Initial dock area.

        Returns:
            The created dock widget.
        """
        dock_widget = ads.CDockWidget(title)
        dock_widget.setWidget(widget)
        dock_widget.setFeature(ads.CDockWidget.DockWidgetFeature.DockWidgetClosable, False)
        dock_widget.setFeature(ads.CDockWidget.DockWidgetFeature.DockWidgetFloatable, True)
        dock_widget.setFeature(ads.CDockWidget.DockWidgetFeature.DockWidgetMovable, True)

        self.addDockWidget(area, dock_widget)
        self._dock_widgets[title] = dock_widget

        logger.debug("Added dock widget: %s", title)
        return dock_widget

    def dock_count(self) -> int:
        """Get the number of dock widgets.

        Returns:
            Number of dock widgets.
        """
        return len(self._dock_widgets)

    def get_dock(self, title: str) -> ads.CDockWidget | None:
        """Get a dock widget by title.

        Args:
            title: Tab title.

        Returns:
            The dock widget or None if not found.
        """
        return self._dock_widgets.get(title)
