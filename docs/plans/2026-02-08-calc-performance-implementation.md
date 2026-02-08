# Calculation Performance Optimization - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make filter experimentation snappy by only recalculating visible tabs on background threads with loading overlays.

**Architecture:** Two layers - VisibilityTracker determines which tabs need updates, CalculationWorker runs heavy calculations off the UI thread. Tabs show a subtle dimmed overlay during calculation.

**Tech Stack:** PyQt6 (QThread, QRunnable, signals/slots), PyQt6Ads (CDockWidget visibility), pandas

---

## Task 1: Create CalculationWorker Infrastructure

**Files:**
- Create: `src/core/calculation_worker.py`
- Test: `tests/unit/test_calculation_worker.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_calculation_worker.py
"""Tests for CalculationWorker background thread execution."""

import time
from unittest.mock import MagicMock

import pandas as pd
import pytest
from pytestqt.qtbot import QtBot

from src.core.calculation_worker import CalculationWorker


class TestCalculationWorker:
    """Tests for CalculationWorker."""

    def test_worker_executes_function_and_emits_finished(self, qtbot: QtBot) -> None:
        """Worker should run calc_fn and emit finished with result."""
        def calc_fn(df: pd.DataFrame) -> int:
            return len(df)

        df = pd.DataFrame({"a": [1, 2, 3]})
        worker = CalculationWorker(calc_fn, df)

        finished_results = []
        worker.signals.finished.connect(lambda r: finished_results.append(r))

        with qtbot.waitSignal(worker.signals.finished, timeout=5000):
            worker.run()

        assert finished_results == [3]

    def test_worker_emits_error_on_exception(self, qtbot: QtBot) -> None:
        """Worker should emit error signal if calc_fn raises."""
        def calc_fn(df: pd.DataFrame) -> int:
            raise ValueError("Test error")

        df = pd.DataFrame({"a": [1, 2, 3]})
        worker = CalculationWorker(calc_fn, df)

        error_messages = []
        worker.signals.error.connect(lambda e: error_messages.append(e))

        with qtbot.waitSignal(worker.signals.error, timeout=5000):
            worker.run()

        assert len(error_messages) == 1
        assert "Test error" in error_messages[0]

    def test_worker_emits_started_signal(self, qtbot: QtBot) -> None:
        """Worker should emit started signal before running."""
        def calc_fn(df: pd.DataFrame) -> int:
            return 1

        df = pd.DataFrame({"a": [1]})
        worker = CalculationWorker(calc_fn, df)

        started_count = []
        worker.signals.started.connect(lambda: started_count.append(1))

        with qtbot.waitSignal(worker.signals.finished, timeout=5000):
            worker.run()

        assert len(started_count) == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_calculation_worker.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.core.calculation_worker'"

**Step 3: Write minimal implementation**

```python
# src/core/calculation_worker.py
"""Background worker for running calculations off the UI thread."""

from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal


class WorkerSignals(QObject):
    """Signals for CalculationWorker communication."""

    started = pyqtSignal()
    finished = pyqtSignal(object)  # result
    error = pyqtSignal(str)  # error message


class CalculationWorker(QRunnable):
    """Runs a calculation function on a background thread.

    Usage:
        worker = CalculationWorker(my_calc_fn, data)
        worker.signals.finished.connect(self._on_complete)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(self, calc_fn: Callable[[Any], Any], data: Any) -> None:
        """Initialize worker with calculation function and data.

        Args:
            calc_fn: Function to execute. Receives data as argument.
            data: Data to pass to calc_fn. Should be a copy if mutable.
        """
        super().__init__()
        self._calc_fn = calc_fn
        self._data = data
        self.signals = WorkerSignals()

    def run(self) -> None:
        """Execute the calculation function."""
        self.signals.started.emit()
        try:
            result = self._calc_fn(self._data)
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_calculation_worker.py -v`
Expected: PASS (3 passed)

**Step 5: Commit**

```bash
git add src/core/calculation_worker.py tests/unit/test_calculation_worker.py
git commit -m "feat(core): add CalculationWorker for background calculations"
```

---

## Task 2: Create LoadingOverlay Widget

**Files:**
- Create: `src/ui/components/loading_overlay.py`
- Test: `tests/widget/test_loading_overlay.py`

**Step 1: Write the failing test**

```python
# tests/widget/test_loading_overlay.py
"""Tests for LoadingOverlay widget."""

import pytest
from pytestqt.qtbot import QtBot
from PyQt6.QtWidgets import QWidget

from src.ui.components.loading_overlay import LoadingOverlay


class TestLoadingOverlay:
    """Tests for LoadingOverlay."""

    def test_overlay_hidden_by_default(self, qtbot: QtBot) -> None:
        """Overlay should be hidden when created."""
        parent = QWidget()
        qtbot.addWidget(parent)
        overlay = LoadingOverlay(parent)

        assert not overlay.isVisible()

    def test_show_overlay_makes_visible(self, qtbot: QtBot) -> None:
        """show() should make overlay visible."""
        parent = QWidget()
        parent.resize(400, 300)
        qtbot.addWidget(parent)
        overlay = LoadingOverlay(parent)

        overlay.show()

        assert overlay.isVisible()

    def test_overlay_covers_parent(self, qtbot: QtBot) -> None:
        """Overlay should match parent geometry."""
        parent = QWidget()
        parent.resize(400, 300)
        qtbot.addWidget(parent)
        overlay = LoadingOverlay(parent)

        overlay.show()

        assert overlay.geometry() == parent.rect()

    def test_overlay_has_spinner(self, qtbot: QtBot) -> None:
        """Overlay should contain a spinner widget."""
        parent = QWidget()
        qtbot.addWidget(parent)
        overlay = LoadingOverlay(parent)

        assert overlay._spinner is not None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/widget/test_loading_overlay.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.ui.components.loading_overlay'"

**Step 3: Write minimal implementation**

```python
# src/ui/components/loading_overlay.py
"""Semi-transparent loading overlay with spinner."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.ui.theme import Colors


class LoadingOverlay(QWidget):
    """Semi-transparent overlay that dims content with a centered spinner.

    Usage:
        self._overlay = LoadingOverlay(self)
        # When starting calculation:
        self._overlay.show()
        # When calculation completes:
        self._overlay.hide()
    """

    def __init__(self, parent: QWidget) -> None:
        """Initialize overlay as child of parent widget.

        Args:
            parent: Widget to overlay. Overlay will match its geometry.
        """
        super().__init__(parent)

        # Make overlay non-interactive (clicks pass through to parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Semi-transparent dark background
        self.setStyleSheet(f"""
            QWidget {{
                background: rgba(0, 0, 0, 0.35);
            }}
        """)

        # Layout with centered spinner
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._spinner = QLabel("Calculating...", self)
        self._spinner.setStyleSheet(f"""
            QLabel {{
                color: {Colors.SIGNAL_CYAN};
                font-size: 14px;
                font-weight: 500;
                background: transparent;
                padding: 12px 20px;
                border-radius: 6px;
            }}
        """)
        self._spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._spinner)

        # Animation for pulsing effect
        self._opacity = 1.0
        self._pulse_direction = -1
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(50)
        self._pulse_timer.timeout.connect(self._pulse)

        self.hide()

    def showEvent(self, event) -> None:
        """Match parent geometry when shown."""
        super().showEvent(event)
        if self.parent():
            self.setGeometry(self.parent().rect())
        self._pulse_timer.start()

    def hideEvent(self, event) -> None:
        """Stop animation when hidden."""
        super().hideEvent(event)
        self._pulse_timer.stop()

    def _pulse(self) -> None:
        """Animate opacity pulse."""
        self._opacity += self._pulse_direction * 0.04
        if self._opacity <= 0.5:
            self._opacity = 0.5
            self._pulse_direction = 1
        elif self._opacity >= 1.0:
            self._opacity = 1.0
            self._pulse_direction = -1

        self._spinner.setStyleSheet(f"""
            QLabel {{
                color: rgba(0, 255, 255, {self._opacity});
                font-size: 14px;
                font-weight: 500;
                background: transparent;
                padding: 12px 20px;
                border-radius: 6px;
            }}
        """)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/widget/test_loading_overlay.py -v`
Expected: PASS (4 passed)

**Step 5: Commit**

```bash
git add src/ui/components/loading_overlay.py tests/widget/test_loading_overlay.py
git commit -m "feat(ui): add LoadingOverlay component"
```

---

## Task 3: Create VisibilityTracker

**Files:**
- Create: `src/core/visibility_tracker.py`
- Test: `tests/unit/test_visibility_tracker.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_visibility_tracker.py
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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_visibility_tracker.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.core.visibility_tracker'"

**Step 3: Write minimal implementation**

```python
# src/core/visibility_tracker.py
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
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_visibility_tracker.py -v`
Expected: PASS (6 passed)

**Step 5: Commit**

```bash
git add src/core/visibility_tracker.py tests/unit/test_visibility_tracker.py
git commit -m "feat(core): add VisibilityTracker for lazy tab updates"
```

---

## Task 4: Integrate VisibilityTracker into AppState

**Files:**
- Modify: `src/core/app_state.py`
- Test: `tests/unit/test_app_state.py` (add test)

**Step 1: Write the failing test**

Add to existing test file:

```python
# In tests/unit/test_app_state.py, add:

class TestAppStateVisibilityTracker:
    """Tests for VisibilityTracker integration."""

    def test_app_state_has_visibility_tracker(self) -> None:
        """AppState should have visibility_tracker attribute."""
        from src.core.app_state import AppState

        app_state = AppState()

        assert hasattr(app_state, "visibility_tracker")
        assert app_state.visibility_tracker is not None

    def test_visibility_tracker_is_singleton(self) -> None:
        """Same visibility_tracker instance should be returned."""
        from src.core.app_state import AppState

        app_state = AppState()
        tracker1 = app_state.visibility_tracker
        tracker2 = app_state.visibility_tracker

        assert tracker1 is tracker2
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_app_state.py::TestAppStateVisibilityTracker -v`
Expected: FAIL with "AttributeError: 'AppState' object has no attribute 'visibility_tracker'"

**Step 3: Modify app_state.py**

In `src/core/app_state.py`:

1. Add import at top:
```python
from src.core.visibility_tracker import VisibilityTracker
```

2. In `__init__`, add after other initializations:
```python
# Visibility tracking for lazy tab updates
self._visibility_tracker = VisibilityTracker()
```

3. Add property:
```python
@property
def visibility_tracker(self) -> VisibilityTracker:
    """Get the visibility tracker for lazy tab updates."""
    return self._visibility_tracker
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_app_state.py::TestAppStateVisibilityTracker -v`
Expected: PASS (2 passed)

**Step 5: Commit**

```bash
git add src/core/app_state.py tests/unit/test_app_state.py
git commit -m "feat(core): integrate VisibilityTracker into AppState"
```

---

## Task 5: Add Background Calculation Mixin

**Files:**
- Create: `src/ui/mixins/background_calculation.py`
- Test: `tests/unit/test_background_calculation_mixin.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_background_calculation_mixin.py
"""Tests for BackgroundCalculationMixin."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from pytestqt.qtbot import QtBot
from PyQt6.QtCore import QThreadPool
from PyQt6.QtWidgets import QWidget

from src.ui.mixins.background_calculation import BackgroundCalculationMixin


class TestWidget(BackgroundCalculationMixin, QWidget):
    """Test widget using the mixin."""

    def __init__(self, app_state: MagicMock) -> None:
        QWidget.__init__(self)
        BackgroundCalculationMixin.__init__(self, app_state, "Test Tab")


class TestBackgroundCalculationMixin:
    """Tests for BackgroundCalculationMixin."""

    def test_start_calculation_shows_overlay(self, qtbot: QtBot) -> None:
        """start_background_calculation should show loading overlay."""
        app_state = MagicMock()
        widget = TestWidget(app_state)
        qtbot.addWidget(widget)

        widget._setup_background_calculation()

        # Mock the calculation function
        def calc_fn(df):
            return {"result": 42}

        widget._start_background_calculation(
            calc_fn, pd.DataFrame({"a": [1]}), lambda r: None
        )

        assert widget._loading_overlay.isVisible()

    def test_calculation_complete_hides_overlay(self, qtbot: QtBot) -> None:
        """Completing calculation should hide loading overlay."""
        app_state = MagicMock()
        widget = TestWidget(app_state)
        qtbot.addWidget(widget)

        widget._setup_background_calculation()
        widget._loading_overlay.show()

        # Simulate completion callback
        widget._on_background_calculation_complete({"result": 42})

        assert not widget._loading_overlay.isVisible()

    def test_skips_calculation_when_not_visible(self, qtbot: QtBot) -> None:
        """Should mark stale and skip when tab not visible."""
        app_state = MagicMock()
        dock_widget = MagicMock()
        dock_widget.isVisible.return_value = False

        app_state.visibility_tracker.is_visible.return_value = False

        widget = TestWidget(app_state)
        widget._dock_widget = dock_widget
        qtbot.addWidget(widget)

        widget._setup_background_calculation()

        calculation_ran = []

        def calc_fn(df):
            calculation_ran.append(True)
            return {"result": 42}

        result = widget._maybe_start_background_calculation(
            calc_fn, pd.DataFrame({"a": [1]}), lambda r: None
        )

        assert result is False
        assert len(calculation_ran) == 0
        app_state.visibility_tracker.mark_stale.assert_called_once_with("Test Tab")
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_background_calculation_mixin.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.ui.mixins.background_calculation'"

**Step 3: Write minimal implementation**

```python
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
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_background_calculation_mixin.py -v`
Expected: PASS (3 passed)

**Step 5: Commit**

```bash
git add src/ui/mixins/__init__.py src/ui/mixins/background_calculation.py tests/unit/test_background_calculation_mixin.py
git commit -m "feat(ui): add BackgroundCalculationMixin for tabs"
```

---

## Task 6: Integrate into Statistics Tab (Heaviest Tab)

**Files:**
- Modify: `src/tabs/statistics_tab.py`
- Test: `tests/widget/test_statistics_tab_background.py`

**Step 1: Write the failing test**

```python
# tests/widget/test_statistics_tab_background.py
"""Tests for Statistics tab background calculation integration."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from pytestqt.qtbot import QtBot


class TestStatisticsTabBackground:
    """Tests for background calculation in Statistics tab."""

    def test_statistics_tab_has_loading_overlay(self, qtbot: QtBot) -> None:
        """Statistics tab should have loading overlay."""
        from src.tabs.statistics_tab import StatisticsTab

        app_state = MagicMock()
        app_state.column_mapping = None
        app_state.filtered_df = None
        app_state.visibility_tracker = MagicMock()

        tab = StatisticsTab(app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_loading_overlay")
        assert tab._loading_overlay is not None

    def test_filtered_data_update_checks_visibility(self, qtbot: QtBot) -> None:
        """Tab should check visibility before calculating."""
        from src.tabs.statistics_tab import StatisticsTab

        app_state = MagicMock()
        app_state.column_mapping = MagicMock()
        app_state.filtered_df = pd.DataFrame({"gain_pct": [0.01, -0.02]})
        app_state.visibility_tracker = MagicMock()
        app_state.visibility_tracker.is_visible.return_value = False

        tab = StatisticsTab(app_state)
        qtbot.addWidget(tab)

        # Simulate dock widget being set
        dock = MagicMock()
        tab.set_dock_widget(dock)

        # Simulate filter update
        tab._on_filtered_data_updated(pd.DataFrame({"gain_pct": [0.01]}))

        # Should have checked visibility
        app_state.visibility_tracker.is_visible.assert_called()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/widget/test_statistics_tab_background.py -v`
Expected: FAIL (tab doesn't have _loading_overlay yet)

**Step 3: Modify statistics_tab.py**

In `src/tabs/statistics_tab.py`:

1. Add import:
```python
from src.ui.mixins.background_calculation import BackgroundCalculationMixin
```

2. Change class definition:
```python
class StatisticsTab(BackgroundCalculationMixin, QWidget):
```

3. In `__init__`, add after `QWidget.__init__(self)`:
```python
BackgroundCalculationMixin.__init__(self, app_state, "Statistics")
```

4. After UI setup (after `_setup_ui()` call), add:
```python
self._setup_background_calculation()
```

5. Modify `_on_filtered_data_updated` method:
```python
def _on_filtered_data_updated(self, df: pd.DataFrame) -> None:
    """Handle filtered data update."""
    if not self._app_state.column_mapping:
        return

    self._show_empty_state(False)
    self._check_column_availability(df)

    # Use background calculation with visibility check
    started = self._maybe_start_background_calculation(
        self._calculate_all_tables,
        df.copy(),
        self._on_tables_calculated,
    )
    if not started:
        return  # Marked as stale, will recalculate when visible

def _calculate_all_tables(self, df: pd.DataFrame) -> dict:
    """Calculate all table data (runs in background thread)."""
    # Move existing _update_all_tables logic here
    # Return dict with all calculated table data
    ...

def _on_tables_calculated(self, result: dict) -> None:
    """Handle table calculation complete (runs on main thread)."""
    # Update UI with calculated results
    ...
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/widget/test_statistics_tab_background.py -v`
Expected: PASS (2 passed)

**Step 5: Commit**

```bash
git add src/tabs/statistics_tab.py tests/widget/test_statistics_tab_background.py
git commit -m "feat(statistics): integrate background calculation with visibility check"
```

---

## Task 7: Wire Dock Widget to Tabs

**Files:**
- Modify: `src/ui/dock_manager.py`
- Test: `tests/unit/test_dock_manager.py` (add test)

**Step 1: Write the failing test**

```python
# Add to tests/unit/test_dock_manager.py

class TestDockManagerVisibility:
    """Tests for dock visibility integration."""

    def test_add_dock_sets_dock_widget_on_tab(self, qtbot: QtBot) -> None:
        """add_dock should call set_dock_widget on tab if available."""
        from src.ui.dock_manager import DockManager

        manager = DockManager()
        qtbot.addWidget(manager)

        tab = MagicMock()
        tab.set_dock_widget = MagicMock()

        manager.add_dock("Test", tab)

        tab.set_dock_widget.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_dock_manager.py::TestDockManagerVisibility -v`
Expected: FAIL (set_dock_widget not called)

**Step 3: Modify dock_manager.py**

In `src/ui/dock_manager.py`, in the `add_dock` method, after creating the dock_widget:

```python
# Set dock widget on tab for visibility tracking
if hasattr(widget, "set_dock_widget"):
    widget.set_dock_widget(dock_widget)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_dock_manager.py::TestDockManagerVisibility -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/ui/dock_manager.py tests/unit/test_dock_manager.py
git commit -m "feat(dock): wire dock widget to tabs for visibility tracking"
```

---

## Task 8: Handle Stale Tab Recalculation on Visibility Change

**Files:**
- Modify: `src/ui/dock_manager.py`
- Modify: `src/core/app_state.py`
- Test: `tests/integration/test_stale_tab_recalc.py`

**Step 1: Write the failing test**

```python
# tests/integration/test_stale_tab_recalc.py
"""Tests for stale tab recalculation on visibility change."""

from unittest.mock import MagicMock

import pandas as pd
import pytest
from pytestqt.qtbot import QtBot


class TestStaleTabRecalculation:
    """Tests for recalculating stale tabs when they become visible."""

    def test_tab_recalculates_when_becoming_visible(self, qtbot: QtBot) -> None:
        """Stale tab should recalculate when it becomes visible."""
        from src.core.app_state import AppState

        app_state = AppState()

        # Mark a tab as stale
        app_state.visibility_tracker.mark_stale("Statistics")

        # Emit visibility signal
        recalc_triggered = []
        app_state.tab_became_visible.connect(
            lambda name: recalc_triggered.append(name)
        )

        app_state.notify_tab_visible("Statistics")

        assert "Statistics" in recalc_triggered
        assert not app_state.visibility_tracker.is_stale("Statistics")
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_stale_tab_recalc.py -v`
Expected: FAIL (no tab_became_visible signal)

**Step 3: Modify app_state.py**

Add signal and method:

```python
# In signal definitions:
tab_became_visible = pyqtSignal(str)  # tab_name

# Add method:
def notify_tab_visible(self, tab_name: str) -> None:
    """Notify that a tab became visible, triggering recalc if stale.

    Args:
        tab_name: Name of tab that became visible.
    """
    if self._visibility_tracker.is_stale(tab_name):
        self._visibility_tracker.clear_stale(tab_name)
        self.tab_became_visible.emit(tab_name)
```

**Step 4: Modify dock_manager.py**

In `_on_dock_visibility_changed`, add stale check:

```python
def _on_dock_visibility_changed(self, title: str, visible: bool) -> None:
    """Handle dock visibility change."""
    if visible:
        # Notify app state for stale tab recalculation
        if hasattr(self, "_app_state") and self._app_state:
            self._app_state.notify_tab_visible(title)
    # ... existing logic
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_stale_tab_recalc.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/core/app_state.py src/ui/dock_manager.py tests/integration/test_stale_tab_recalc.py
git commit -m "feat: recalculate stale tabs when they become visible"
```

---

## Task 9: Integrate into PnL Stats Tab

**Files:**
- Modify: `src/tabs/pnl_stats.py`
- Test: `tests/widget/test_pnl_stats_background.py`

**Step 1: Write the failing test**

```python
# tests/widget/test_pnl_stats_background.py
"""Tests for PnL Stats tab background calculation integration."""

from unittest.mock import MagicMock

import pandas as pd
import pytest
from pytestqt.qtbot import QtBot


class TestPnlStatsBackground:
    """Tests for background calculation in PnL Stats tab."""

    def test_pnl_stats_has_loading_overlay(self, qtbot: QtBot) -> None:
        """PnL Stats tab should have loading overlay."""
        from src.tabs.pnl_stats import PnlStatsTab

        app_state = MagicMock()
        app_state.column_mapping = None
        app_state.baseline_df = None
        app_state.filtered_df = None
        app_state.visibility_tracker = MagicMock()

        tab = PnlStatsTab(app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_loading_overlay")
```

Follow same pattern as Task 6 for implementation.

**Step 2-5:** Same as Task 6, adapted for PnL Stats tab.

**Step 6: Commit**

```bash
git add src/tabs/pnl_stats.py tests/widget/test_pnl_stats_background.py
git commit -m "feat(pnl-stats): integrate background calculation with visibility check"
```

---

## Task 10: Integrate into Breakdown Tab

**Files:**
- Modify: `src/tabs/breakdown.py`
- Test: `tests/widget/test_breakdown_background.py`

Follow same pattern as Task 6 and Task 9.

---

## Task 11: Integrate into Remaining Tabs

**Files:**
- Modify: `src/tabs/data_binning.py`
- Modify: `src/tabs/feature_impact.py`
- Modify: `src/tabs/feature_insights.py`

Follow same pattern for each tab.

---

## Task 12: Pre-compute Columns on Data Load

**Files:**
- Modify: `src/core/file_loader.py`
- Test: `tests/unit/test_file_loader.py` (add test)

**Step 1: Write the failing test**

```python
# Add to tests/unit/test_file_loader.py

class TestPrecomputedColumns:
    """Tests for pre-computed columns on load."""

    def test_time_minutes_precomputed(self) -> None:
        """Loaded DataFrame should have _time_minutes column."""
        from src.core.file_loader import FileLoader

        loader = FileLoader()
        # Create test data with time column
        df = pd.DataFrame({
            "time": ["09:30:00", "10:15:00"],
            "gain_pct": [0.01, -0.02],
        })

        result = loader._precompute_columns(df, {"time": "time"})

        assert "_time_minutes" in result.columns
        assert result["_time_minutes"].iloc[0] == 570  # 9*60 + 30
```

**Step 2-5:** Implement `_precompute_columns` method that adds `_time_minutes` column.

**Step 6: Commit**

```bash
git add src/core/file_loader.py tests/unit/test_file_loader.py
git commit -m "feat(loader): pre-compute time_minutes on data load"
```

---

## Task 13: Final Integration Test

**Files:**
- Test: `tests/integration/test_calculation_performance.py`

**Step 1: Write integration test**

```python
# tests/integration/test_calculation_performance.py
"""Integration tests for calculation performance optimizations."""

import time
from unittest.mock import MagicMock

import pandas as pd
import pytest
from pytestqt.qtbot import QtBot


class TestCalculationPerformance:
    """Integration tests for performance features."""

    def test_hidden_tabs_do_not_block_ui(self, qtbot: QtBot) -> None:
        """Hidden tabs should not calculate on filter change."""
        # Setup app with multiple tabs
        # Hide some tabs
        # Trigger filter change
        # Verify only visible tabs calculated
        pass

    def test_background_calculation_does_not_freeze_ui(self, qtbot: QtBot) -> None:
        """Heavy calculation should run in background."""
        # Trigger heavy calculation
        # Verify UI remains responsive (can process events)
        pass

    def test_stale_tab_recalculates_on_focus(self, qtbot: QtBot) -> None:
        """Stale tab should recalculate when focused."""
        # Mark tab stale
        # Make tab visible
        # Verify recalculation triggered
        pass
```

**Step 2: Implement tests**

**Step 3: Run full test suite**

Run: `uv run pytest tests/ -v --tb=short`
Expected: All tests pass

**Step 4: Commit**

```bash
git add tests/integration/test_calculation_performance.py
git commit -m "test: add integration tests for calculation performance"
```

---

## Summary

After completing all tasks:

1. **Infrastructure (Tasks 1-5):** CalculationWorker, LoadingOverlay, VisibilityTracker, BackgroundCalculationMixin
2. **Tab Integration (Tasks 6-11):** All heavy tabs use background calculation with visibility check
3. **Initial Load (Task 12):** Pre-computed columns reduce repeated work
4. **Verification (Task 13):** Integration tests confirm behavior

Run final verification:
```bash
uv run pytest tests/ -v
```

Create PR when all tests pass.
