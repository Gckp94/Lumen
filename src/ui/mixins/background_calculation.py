# src/ui/mixins/background_calculation.py
"""Mixin providing background calculation capabilities for tabs."""

from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING

from PyQt6.QtCore import QThreadPool

from src.core.calculation_worker import CalculationWorker
from src.ui.components.loading_overlay import LoadingOverlay

if TYPE_CHECKING:
    from PyQt6Ads import CDockWidget

    from src.core.app_state import AppState


class BackgroundCalculationMixin:
    """Mixin that adds background calculation with loading overlay.

    Usage:
        class MyTab(BackgroundCalculationMixin, QWidget):
            def __init__(self, app_state):
                QWidget.__init__(self)
                BackgroundCalculationMixin.__init__(self, app_state, "My Tab")
                self._setup_background_calculation()

            def _on_filtered_data_updated(self, df):
                self._maybe_start_background_calculation(
                    self._calculate_metrics,
                    df.copy(),
                    self._on_calculation_complete
                )
    """

    def __init__(self, app_state: AppState, tab_name: str) -> None:
        """Initialize mixin.

        Args:
            app_state: Application state with visibility_tracker.
            tab_name: Name of this tab for stale tracking.
        """
        self._app_state = app_state
        self._tab_name = tab_name
        self._dock_widget: CDockWidget | None = None
        self._loading_overlay: LoadingOverlay | None = None
        self._current_worker: CalculationWorker | None = None
        self._pending_callback: Callable[[Any], None] | None = None

    def _setup_background_calculation(self) -> None:
        """Set up loading overlay. Call in subclass __init__ after UI setup."""
        self._loading_overlay = LoadingOverlay(self)  # type: ignore

    def set_dock_widget(self, dock_widget: CDockWidget) -> None:
        """Set the dock widget wrapper for visibility checking.

        Args:
            dock_widget: The CDockWidget wrapping this tab.
        """
        self._dock_widget = dock_widget

    def _maybe_start_background_calculation(
        self,
        calc_fn: Callable[[Any], Any],
        data: Any,
        on_complete: Callable[[Any], None],
    ) -> bool:
        """Start calculation if visible, otherwise mark stale.

        Args:
            calc_fn: Calculation function to run.
            data: Data to pass to calc_fn.
            on_complete: Callback when calculation completes.

        Returns:
            True if calculation started, False if marked stale.
        """
        if self._dock_widget is None:
            # No dock widget set yet, run calculation
            self._start_background_calculation(calc_fn, data, on_complete)
            return True

        if not self._app_state.visibility_tracker.is_visible(self._dock_widget):
            self._app_state.visibility_tracker.mark_stale(self._tab_name)
            return False

        self._start_background_calculation(calc_fn, data, on_complete)
        return True

    def _start_background_calculation(
        self,
        calc_fn: Callable[[Any], Any],
        data: Any,
        on_complete: Callable[[Any], None],
    ) -> None:
        """Start a background calculation with loading overlay.

        Args:
            calc_fn: Calculation function to run.
            data: Data to pass to calc_fn.
            on_complete: Callback when calculation completes.
        """
        if self._loading_overlay:
            self._loading_overlay.show()

        self._pending_callback = on_complete

        worker = CalculationWorker(calc_fn, data)
        worker.signals.finished.connect(self._on_background_calculation_complete)
        worker.signals.error.connect(self._on_background_calculation_error)
        self._current_worker = worker

        QThreadPool.globalInstance().start(worker)

    def _on_background_calculation_complete(self, result: Any) -> None:
        """Handle calculation completion.

        Args:
            result: Result from calc_fn.
        """
        if self._loading_overlay:
            self._loading_overlay.hide()

        if self._pending_callback:
            self._pending_callback(result)
            self._pending_callback = None

        self._current_worker = None

    def _on_background_calculation_error(self, error: str) -> None:
        """Handle calculation error.

        Args:
            error: Error message.
        """
        if self._loading_overlay:
            self._loading_overlay.hide()

        self._current_worker = None
        # Subclasses can override to show error UI
