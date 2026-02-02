"""Debouncing utilities for UI responsiveness.

This module provides debouncing functionality to prevent rapid-fire
execution of expensive operations when the user is making quick
successive changes (e.g., dragging a slider, typing in a field).

Debouncing waits for a pause in user input before executing the
callback, which dramatically improves UI responsiveness for
operations like filtering, chart updates, and recalculations.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)


class Debouncer(QObject):
    """Debounces function calls using Qt timer.

    Delays execution until a specified time has passed without
    additional calls. Thread-safe for use in Qt applications.

    Attributes:
        delay_ms: Delay in milliseconds before executing callback.
    """

    # Signal emitted when the debounced callback executes
    triggered = pyqtSignal()

    def __init__(
        self,
        callback: Callable[[], Any] | None = None,
        delay_ms: int = 300,
        parent: QObject | None = None,
    ) -> None:
        """Initialize the debouncer.

        Args:
            callback: Function to call after debounce delay.
            delay_ms: Delay in milliseconds (default 300ms).
            parent: Parent QObject for memory management.
        """
        super().__init__(parent)
        self._callback = callback
        self._delay_ms = delay_ms
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._execute)
        self._pending_args: tuple = ()
        self._pending_kwargs: dict = {}

    @property
    def delay_ms(self) -> int:
        """Get the debounce delay in milliseconds."""
        return self._delay_ms

    @delay_ms.setter
    def delay_ms(self, value: int) -> None:
        """Set the debounce delay in milliseconds."""
        self._delay_ms = max(0, value)

    def call(self, *args: Any, **kwargs: Any) -> None:
        """Schedule a debounced call.

        Resets the timer if called before the previous delay expired.
        The callback will be executed with the most recent arguments
        after the delay period.

        Args:
            *args: Positional arguments to pass to callback.
            **kwargs: Keyword arguments to pass to callback.
        """
        self._pending_args = args
        self._pending_kwargs = kwargs
        self._timer.stop()
        self._timer.start(self._delay_ms)

    def call_now(self, *args: Any, **kwargs: Any) -> None:
        """Execute callback immediately, bypassing debounce.

        Args:
            *args: Positional arguments to pass to callback.
            **kwargs: Keyword arguments to pass to callback.
        """
        self._timer.stop()
        self._pending_args = args
        self._pending_kwargs = kwargs
        self._execute()

    def cancel(self) -> None:
        """Cancel any pending debounced call."""
        self._timer.stop()
        self._pending_args = ()
        self._pending_kwargs = {}

    def _execute(self) -> None:
        """Execute the callback with pending arguments."""
        if self._callback is not None:
            try:
                self._callback(*self._pending_args, **self._pending_kwargs)
            except Exception as e:
                logger.exception("Debounced callback failed: %s", e)

        self.triggered.emit()
        self._pending_args = ()
        self._pending_kwargs = {}

    @property
    def is_pending(self) -> bool:
        """Check if a call is pending execution."""
        return self._timer.isActive()


class ThrottledDebouncer(QObject):
    """Combines throttling with debouncing for optimal responsiveness.

    Throttling ensures a maximum execution rate (e.g., once per 100ms)
    while debouncing ensures a final execution after input stops.

    This is ideal for:
    - Slider drags (throttle shows preview, debounce does final update)
    - Search-as-you-type (throttle shows immediate feedback)
    - Chart zooming/panning
    """

    triggered = pyqtSignal()

    def __init__(
        self,
        callback: Callable[[], Any] | None = None,
        throttle_ms: int = 100,
        debounce_ms: int = 300,
        parent: QObject | None = None,
    ) -> None:
        """Initialize throttled debouncer.

        Args:
            callback: Function to call.
            throttle_ms: Minimum time between throttled calls.
            debounce_ms: Delay after last call before final execution.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._callback = callback
        self._throttle_ms = throttle_ms
        self._debounce_ms = debounce_ms

        # Throttle timer - runs callback periodically during active input
        self._throttle_timer = QTimer(self)
        self._throttle_timer.setSingleShot(False)
        self._throttle_timer.timeout.connect(self._on_throttle)

        # Debounce timer - runs callback once after input stops
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._on_debounce)

        self._pending_args: tuple = ()
        self._pending_kwargs: dict = {}
        self._has_pending = False

    def call(self, *args: Any, **kwargs: Any) -> None:
        """Schedule a throttled+debounced call.

        Args:
            *args: Positional arguments to pass to callback.
            **kwargs: Keyword arguments to pass to callback.
        """
        self._pending_args = args
        self._pending_kwargs = kwargs
        self._has_pending = True

        # Start throttle if not running
        if not self._throttle_timer.isActive():
            self._throttle_timer.start(self._throttle_ms)
            # Execute immediately for first call
            self._execute()

        # Reset debounce timer
        self._debounce_timer.stop()
        self._debounce_timer.start(self._debounce_ms)

    def cancel(self) -> None:
        """Cancel any pending calls."""
        self._throttle_timer.stop()
        self._debounce_timer.stop()
        self._has_pending = False
        self._pending_args = ()
        self._pending_kwargs = {}

    def _on_throttle(self) -> None:
        """Handle throttle timer tick."""
        if self._has_pending:
            self._execute()
            self._has_pending = False
        else:
            # No pending calls, stop throttling
            self._throttle_timer.stop()

    def _on_debounce(self) -> None:
        """Handle debounce timer completion."""
        self._throttle_timer.stop()
        if self._has_pending:
            self._execute()
            self._has_pending = False

    def _execute(self) -> None:
        """Execute the callback."""
        if self._callback is not None:
            try:
                self._callback(*self._pending_args, **self._pending_kwargs)
            except Exception as e:
                logger.exception("Throttled callback failed: %s", e)

        self.triggered.emit()


def debounced(delay_ms: int = 300) -> Callable:
    """Decorator to create a debounced function.

    Usage:
        @debounced(delay_ms=200)
        def on_filter_changed(self, value):
            # This will only execute 200ms after the last call
            self.apply_filter(value)

    Args:
        delay_ms: Debounce delay in milliseconds.

    Returns:
        Decorator function.
    """

    def decorator(func: Callable) -> Callable:
        debouncer: Debouncer | None = None

        def wrapper(*args, **kwargs):
            nonlocal debouncer
            if debouncer is None:
                # Get parent QObject from self if available
                parent = args[0] if args and isinstance(args[0], QObject) else None
                debouncer = Debouncer(
                    callback=lambda: func(*args, **kwargs),
                    delay_ms=delay_ms,
                    parent=parent,
                )
            else:
                # Update callback with new arguments
                debouncer._callback = lambda: func(*args, **kwargs)

            debouncer.call()

        return wrapper

    return decorator
