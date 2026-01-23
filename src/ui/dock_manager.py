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
        # Allow closing only when floating (undocked)
        dock_widget.setFeature(ads.CDockWidget.DockWidgetFeature.DockWidgetClosable, True)
        dock_widget.setFeature(ads.CDockWidget.DockWidgetFeature.DockWidgetFloatable, True)
        dock_widget.setFeature(ads.CDockWidget.DockWidgetFeature.DockWidgetMovable, True)

        # Handle close to re-dock instead of destroy
        dock_widget.closeRequested.connect(lambda: self._on_dock_close_requested(dock_widget))

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

    def _on_dock_close_requested(self, dock_widget: ads.CDockWidget) -> None:
        """Handle dock widget close request by re-docking instead of closing.

        Args:
            dock_widget: The dock widget requesting to close.
        """
        if dock_widget.isFloating():
            # Re-dock to center area instead of closing
            # Note: PyQtAds setFloating() is parameter-less and only makes widgets float,
            # it doesn't dock them back. Use addDockWidget to re-dock.
            self.addDockWidget(
                ads.DockWidgetArea.CenterDockWidgetArea, dock_widget, self._center_area
            )
            logger.debug("Re-docked floating widget: %s", dock_widget.windowTitle())

    def toggle_dock_visibility(self, title: str) -> None:
        """Toggle visibility of a dock widget.

        Args:
            title: Tab title of the dock to toggle.
        """
        dock_widget = self._dock_widgets.get(title)
        if dock_widget is None:
            logger.warning("Cannot toggle visibility: dock '%s' not found", title)
            return

        if dock_widget.isClosed():
            dock_widget.toggleView(True)
            # If it was floating and closed, re-dock it
            if dock_widget.isFloating():
                self.addDockWidget(
                    ads.DockWidgetArea.CenterDockWidgetArea,
                    dock_widget,
                    self._center_area,
                )
            logger.debug("Shown dock widget: %s", title)
        else:
            dock_widget.toggleView(False)
            logger.debug("Hidden dock widget: %s", title)

    def show_all_docks(self) -> None:
        """Show all dock widgets, restoring any that were hidden."""
        for title, dock_widget in self._dock_widgets.items():
            if dock_widget.isClosed():
                dock_widget.toggleView(True)
                # Re-dock if it was floating
                if dock_widget.isFloating():
                    self.addDockWidget(
                        ads.DockWidgetArea.CenterDockWidgetArea,
                        dock_widget,
                        self._center_area,
                    )
                logger.debug("Restored dock widget: %s", title)

    def set_active_dock(self, title: str) -> None:
        """Set a dock widget as the active/current tab.

        Args:
            title: Tab title of the dock to activate.
        """
        dock_widget = self._dock_widgets.get(title)
        if dock_widget is None:
            logger.warning("Cannot set active: dock '%s' not found", title)
            return

        # Ensure it's visible first (not closed)
        if dock_widget.isClosed():
            dock_widget.toggleView(True)

        # Raise the tab
        dock_widget.raise_()
        logger.debug("Set active dock: %s", title)

    def is_dock_visible(self, title: str) -> bool:
        """Check if a dock widget is visible (not closed).

        Args:
            title: Tab title of the dock to check.

        Returns:
            True if the dock is visible (not closed), False otherwise.
        """
        dock_widget = self._dock_widgets.get(title)
        if dock_widget is None:
            return False
        return not dock_widget.isClosed()

    def get_all_dock_titles(self) -> list[str]:
        """Get all dock widget titles.

        Returns:
            List of all dock widget titles.
        """
        return list(self._dock_widgets.keys())

    def dock_all_floating(self) -> None:
        """Dock all floating widgets back to the center area.

        Iterates through all floating containers and re-docks their
        dock widgets to the center dock area. This ensures a consistent
        startup state with all tabs docked.
        """
        if self._center_area is None:
            logger.warning("Cannot dock floating widgets: center area not initialized")
            return

        floating_containers = self.floatingWidgets()
        for container in floating_containers:
            # Each floating container holds dock widgets
            dock_widget = container.dockWidget()
            if dock_widget is not None:
                self.addDockWidget(
                    ads.DockWidgetArea.CenterDockWidgetArea,
                    dock_widget,
                    self._center_area,
                )
                logger.debug("Docked floating widget: %s", dock_widget.windowTitle())
