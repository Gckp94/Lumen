"""Lazy loading container for tabs.

This module provides a lazy loading wrapper that defers the creation of
heavy tab widgets until they are first accessed. This dramatically improves
application startup time by not initializing all tabs upfront.
"""

from __future__ import annotations

import logging
from typing import Callable, TypeVar

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=QWidget)


class LazyTabContainer(QWidget):
    """Container that lazily loads a widget on first access.

    The actual widget is only created when the container becomes visible
    for the first time, or when explicitly requested. This saves memory
    and startup time for tabs that may never be accessed.

    Attributes:
        is_loaded: Whether the actual widget has been created.
    """

    def __init__(
        self,
        factory: Callable[[], T],
        loading_text: str = "Loading...",
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the lazy container.

        Args:
            factory: Callable that creates the actual widget when invoked.
            loading_text: Text to display while loading.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._factory = factory
        self._loading_text = loading_text
        self._actual_widget: T | None = None
        self._is_loaded = False

        # Set up layout
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        # Stacked widget to switch between loading placeholder and actual widget
        self._stack = QStackedWidget()
        self._layout.addWidget(self._stack)

        # Create loading placeholder
        self._placeholder = self._create_placeholder()
        self._stack.addWidget(self._placeholder)

    def _create_placeholder(self) -> QWidget:
        """Create the loading placeholder widget.

        Returns:
            Placeholder widget with loading message.
        """
        from src.ui.constants import Colors, Fonts

        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(self._loading_text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: "{Fonts.UI}";
                font-size: 14px;
            }}
        """)
        layout.addWidget(label)

        return placeholder

    @property
    def is_loaded(self) -> bool:
        """Check if the actual widget has been loaded."""
        return self._is_loaded

    @property
    def widget(self) -> T | None:
        """Get the actual widget, or None if not yet loaded."""
        return self._actual_widget

    def ensure_loaded(self) -> T:
        """Ensure the actual widget is loaded and return it.

        Creates the widget using the factory if not already created.

        Returns:
            The actual widget.
        """
        if not self._is_loaded:
            self._load_widget()
        return self._actual_widget  # type: ignore[return-value]

    def _load_widget(self) -> None:
        """Load the actual widget using the factory."""
        if self._is_loaded:
            return

        logger.debug("Lazily loading widget...")

        # Create the actual widget
        self._actual_widget = self._factory()

        # Add to stack and switch to it
        self._stack.addWidget(self._actual_widget)
        self._stack.setCurrentWidget(self._actual_widget)

        self._is_loaded = True
        logger.debug("Widget loaded successfully")

    def showEvent(self, event) -> None:
        """Handle show event to trigger lazy loading.

        Args:
            event: Show event.
        """
        super().showEvent(event)

        # Load widget on first show
        if not self._is_loaded:
            self._load_widget()


class LazyTabManager:
    """Manager for lazy tab loading.

    Provides a convenient interface for registering tab factories
    and creating lazy containers.
    """

    def __init__(self) -> None:
        """Initialize the lazy tab manager."""
        self._factories: dict[str, Callable[[], QWidget]] = {}
        self._containers: dict[str, LazyTabContainer] = {}

    def register(
        self,
        name: str,
        factory: Callable[[], QWidget],
    ) -> None:
        """Register a tab factory.

        Args:
            name: Tab name.
            factory: Callable that creates the tab widget.
        """
        self._factories[name] = factory

    def get_container(
        self,
        name: str,
        loading_text: str | None = None,
    ) -> LazyTabContainer:
        """Get or create a lazy container for a tab.

        Args:
            name: Tab name.
            loading_text: Optional loading text. Defaults to "Loading {name}..."

        Returns:
            LazyTabContainer for the tab.

        Raises:
            KeyError: If no factory is registered for the name.
        """
        if name in self._containers:
            return self._containers[name]

        if name not in self._factories:
            raise KeyError(f"No factory registered for tab: {name}")

        loading = loading_text or f"Loading {name}..."
        container = LazyTabContainer(self._factories[name], loading)
        self._containers[name] = container

        return container

    def is_loaded(self, name: str) -> bool:
        """Check if a tab is loaded.

        Args:
            name: Tab name.

        Returns:
            True if the tab is loaded, False otherwise.
        """
        if name not in self._containers:
            return False
        return self._containers[name].is_loaded

    def preload(self, *names: str) -> None:
        """Preload specified tabs.

        Useful for tabs that should be ready immediately
        (e.g., the default tab).

        Args:
            *names: Tab names to preload.
        """
        for name in names:
            if name in self._containers:
                self._containers[name].ensure_loaded()
            elif name in self._factories:
                self.get_container(name).ensure_loaded()
