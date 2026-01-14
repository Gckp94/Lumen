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
    and managing dockable widgets as tabbed panels.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the dock manager.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._dock_widgets: dict[str, ads.CDockWidget] = {}
        self._center_area: ads.CDockAreaWidget | None = None

        # Configure docking behavior
        self.setConfigFlag(ads.CDockManager.eConfigFlag.OpaqueSplitterResize, True)
        self.setConfigFlag(ads.CDockManager.eConfigFlag.DockAreaHasTabsMenuButton, True)
        self.setConfigFlag(ads.CDockManager.eConfigFlag.DockAreaHasUndockButton, True)
        self.setConfigFlag(ads.CDockManager.eConfigFlag.FloatingContainerHasWidgetTitle, True)
        self.setConfigFlag(ads.CDockManager.eConfigFlag.FloatingContainerHasWidgetIcon, True)
        self.setConfigFlag(ads.CDockManager.eConfigFlag.AllTabsHaveCloseButton, False)

        # Apply dock-specific styling
        self._apply_styling()

        logger.debug("DockManager initialized")

    def _apply_styling(self) -> None:
        """Apply custom styling to dock widgets."""
        from src.ui.constants import Colors, Fonts, Spacing

        stylesheet = f"""
            /* Dock Area Widget */
            ads--CDockAreaWidget {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BG_BORDER};
            }}

            /* Dock Area Title Bar */
            ads--CDockAreaTitleBar {{
                background-color: {Colors.BG_BASE};
                border-bottom: 1px solid {Colors.BG_BORDER};
                min-height: 36px;
            }}

            /* Dock Area Tab Bar */
            ads--CDockAreaTabBar {{
                background-color: {Colors.BG_BASE};
            }}

            /* Individual Dock Widget Tabs */
            ads--CDockWidgetTab {{
                background-color: {Colors.TEXT_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                padding: {Spacing.SM}px {Spacing.LG}px;
                border: none;
                min-width: 120px;
                font-family: "{Fonts.UI}";
                font-size: 13px;
            }}

            ads--CDockWidgetTab[activeTab="true"] {{
                background-color: {Colors.BG_SURFACE};
                border-bottom: 2px solid {Colors.SIGNAL_CYAN};
            }}

            ads--CDockWidgetTab:hover {{
                background-color: {Colors.BG_ELEVATED};
            }}

            /* Tab label */
            ads--CDockWidgetTab QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: "{Fonts.UI}";
                font-size: 13px;
            }}

            ads--CDockWidgetTab[activeTab="true"] QLabel {{
                color: {Colors.TEXT_PRIMARY};
            }}

            /* Floating Dock Container */
            ads--CFloatingDockContainer {{
                background-color: {Colors.BG_BASE};
                border: 1px solid {Colors.BG_BORDER};
            }}

            /* Title bar buttons */
            ads--CTitleBarButton {{
                background-color: transparent;
                border: none;
                padding: 4px;
            }}

            ads--CTitleBarButton:hover {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: 4px;
            }}

            /* Splitter */
            ads--CDockSplitter::handle {{
                background-color: {Colors.BG_BORDER};
            }}

            ads--CDockSplitter::handle:hover {{
                background-color: {Colors.SIGNAL_CYAN};
            }}
        """
        self.setStyleSheet(stylesheet)

    def add_dock(
        self,
        title: str,
        widget: QWidget,
        area: ads.DockWidgetArea = ads.DockWidgetArea.CenterDockWidgetArea,
    ) -> ads.CDockWidget:
        """Add a dockable widget.

        Widgets added to the same area will be tabbed together.

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

        # Add to existing dock area to create tabs, or create new area
        if self._center_area is not None and area == ads.DockWidgetArea.CenterDockWidgetArea:
            # Add to existing center area as a tab
            self.addDockWidget(
                ads.DockWidgetArea.CenterDockWidgetArea, dock_widget, self._center_area
            )
        else:
            # Create new dock area
            dock_area = self.addDockWidget(area, dock_widget)
            if area == ads.DockWidgetArea.CenterDockWidgetArea and self._center_area is None:
                self._center_area = dock_area

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
