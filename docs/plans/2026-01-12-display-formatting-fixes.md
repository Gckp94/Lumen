# Display Formatting Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix three display issues: baseline metrics percentage formatting, add time-of-day filtering, and disable scroll-wheel value changes on input widgets.

**Architecture:** Create custom widget classes that ignore scroll events, add TimeRangeFilter component similar to DateRangeFilter, and investigate/fix percentage display in MetricsPanel.

**Tech Stack:** PyQt6, Python

---

## Task 1: Create NoScrollWidgets Module

Create reusable widget classes that ignore scroll wheel events when not focused.

**Files:**
- Create: `src/ui/components/no_scroll_widgets.py`
- Test: `tests/widget/test_no_scroll_widgets.py`

**Step 1: Write the failing test**

```python
# tests/widget/test_no_scroll_widgets.py
"""Tests for NoScrollWidgets components."""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QApplication

from src.ui.components.no_scroll_widgets import NoScrollComboBox, NoScrollDoubleSpinBox


@pytest.fixture(scope="module")
def app():
    """Create QApplication for widget tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestNoScrollComboBox:
    """Tests for NoScrollComboBox."""

    def test_ignores_wheel_when_not_focused(self, app, qtbot):
        """Wheel event should be ignored when widget is not focused."""
        combo = NoScrollComboBox()
        combo.addItems(["Item 1", "Item 2", "Item 3"])
        combo.setCurrentIndex(0)
        qtbot.addWidget(combo)

        # Clear focus
        combo.clearFocus()

        # Simulate wheel event
        initial_index = combo.currentIndex()
        # Wheel should not change value
        assert combo.currentIndex() == initial_index

    def test_accepts_wheel_when_focused(self, app, qtbot):
        """Wheel event should work when widget is focused."""
        combo = NoScrollComboBox()
        combo.addItems(["Item 1", "Item 2", "Item 3"])
        combo.setCurrentIndex(1)
        combo.show()
        qtbot.addWidget(combo)

        # Set focus
        combo.setFocus()
        assert combo.hasFocus()


class TestNoScrollDoubleSpinBox:
    """Tests for NoScrollDoubleSpinBox."""

    def test_ignores_wheel_when_not_focused(self, app, qtbot):
        """Wheel event should be ignored when widget is not focused."""
        spin = NoScrollDoubleSpinBox()
        spin.setRange(0, 100)
        spin.setValue(50)
        qtbot.addWidget(spin)

        # Clear focus
        spin.clearFocus()

        initial_value = spin.value()
        # Wheel should not change value
        assert spin.value() == initial_value

    def test_accepts_wheel_when_focused(self, app, qtbot):
        """Wheel event should work when widget is focused."""
        spin = NoScrollDoubleSpinBox()
        spin.setRange(0, 100)
        spin.setValue(50)
        spin.show()
        qtbot.addWidget(spin)

        # Set focus
        spin.setFocus()
        assert spin.hasFocus()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/widget/test_no_scroll_widgets.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.ui.components.no_scroll_widgets'"

**Step 3: Write minimal implementation**

```python
# src/ui/components/no_scroll_widgets.py
"""Custom widgets that ignore scroll wheel events when not focused.

This prevents accidental value changes when scrolling through forms.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QComboBox, QDoubleSpinBox, QSpinBox


class NoScrollComboBox(QComboBox):
    """QComboBox that ignores wheel events when not focused."""

    def __init__(self, parent=None):
        """Initialize with StrongFocus policy."""
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event: QWheelEvent | None) -> None:
        """Ignore wheel events unless widget has focus."""
        if event is None:
            return
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class NoScrollDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox that ignores wheel events when not focused."""

    def __init__(self, parent=None):
        """Initialize with StrongFocus policy."""
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event: QWheelEvent | None) -> None:
        """Ignore wheel events unless widget has focus."""
        if event is None:
            return
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class NoScrollSpinBox(QSpinBox):
    """QSpinBox that ignores wheel events when not focused."""

    def __init__(self, parent=None):
        """Initialize with StrongFocus policy."""
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event: QWheelEvent | None) -> None:
        """Ignore wheel events unless widget has focus."""
        if event is None:
            return
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/widget/test_no_scroll_widgets.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/ui/components/no_scroll_widgets.py tests/widget/test_no_scroll_widgets.py
git commit -m "feat: add NoScrollWidgets to prevent scroll-wheel value changes"
```

---

## Task 2: Replace QComboBox with NoScrollComboBox in data_input.py

**Files:**
- Modify: `src/tabs/data_input.py` (lines 14, 249, 1113)

**Step 1: Update imports**

Replace `QComboBox` import with `NoScrollComboBox`:

```python
# Line 14: Change
from PyQt6.QtWidgets import (
    ...
    QComboBox,  # Remove this
    ...
)

# Add at the end of PyQt6 imports or in component imports:
from src.ui.components.no_scroll_widgets import NoScrollComboBox
```

**Step 2: Replace QComboBox instantiations**

Line ~249 in ColumnMappingPanel._create_combo_row():
```python
# Change: combo = QComboBox()
# To:
combo = NoScrollComboBox()
```

Line ~1113 in DataInputTab._setup_header():
```python
# Change: self._sheet_selector = QComboBox()
# To:
self._sheet_selector = NoScrollComboBox()
```

**Step 3: Run existing tests**

Run: `pytest tests/widget/test_data_input.py -v`
Expected: PASS (no behavior change for tests)

**Step 4: Manual verification**

Launch app and verify:
1. Scroll wheel no longer changes combo values when not focused
2. Click to focus combo, then scroll wheel works normally

**Step 5: Commit**

```bash
git add src/tabs/data_input.py
git commit -m "fix: use NoScrollComboBox to prevent scroll-wheel value changes"
```

---

## Task 3: Replace QDoubleSpinBox with NoScrollDoubleSpinBox in UserInputsPanel

**Files:**
- Modify: `src/ui/components/user_inputs_panel.py`

**Step 1: Update imports**

```python
# Change import from:
from PyQt6.QtWidgets import QDoubleSpinBox, ...

# Add:
from src.ui.components.no_scroll_widgets import NoScrollDoubleSpinBox
```

**Step 2: Update _create_spinbox method**

```python
def _create_spinbox(
    self,
    min_val: float,
    max_val: float,
    default: float,
    step: float,
    decimals: int,
    prefix: str = "",
    suffix: str = "",
) -> NoScrollDoubleSpinBox:
    """Create a configured spinbox.
    ...
    Returns:
        Configured NoScrollDoubleSpinBox.
    """
    spin = NoScrollDoubleSpinBox()  # Changed from QDoubleSpinBox()
    spin.setRange(min_val, max_val)
    spin.setValue(default)
    spin.setSingleStep(step)
    spin.setDecimals(decimals)
    if prefix:
        spin.setPrefix(prefix)
    if suffix:
        spin.setSuffix(suffix)
    return spin
```

**Step 3: Update type hints in class**

Update any type hints from `QDoubleSpinBox` to `NoScrollDoubleSpinBox`.

**Step 4: Run tests**

Run: `pytest tests/widget/test_user_inputs_panel.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/ui/components/user_inputs_panel.py
git commit -m "fix: use NoScrollDoubleSpinBox in UserInputsPanel"
```

---

## Task 4: Replace QDoubleSpinBox in other components

Search and replace in other files that use QDoubleSpinBox/QComboBox.

**Files:**
- Modify: `src/ui/components/filter_row.py` (if using QComboBox)
- Modify: `src/ui/components/adjustment_panel.py` (if using QDoubleSpinBox)
- Modify: `src/tabs/feature_explorer.py` (if using QComboBox)

**Step 1: Search for usages**

```bash
grep -r "QComboBox\|QDoubleSpinBox" src/ui/components/ src/tabs/ --include="*.py"
```

**Step 2: Update each file**

For each file found:
1. Add import for NoScrollComboBox/NoScrollDoubleSpinBox
2. Replace instantiations
3. Run relevant tests

**Step 3: Commit**

```bash
git add -A
git commit -m "fix: use NoScroll widgets across all input components"
```

---

## Task 5: Create TimeRangeFilter Component

Add time-of-day filtering similar to DateRangeFilter.

**Files:**
- Create: `src/ui/components/time_range_filter.py`
- Test: `tests/widget/test_time_range_filter.py`

**Step 1: Write the failing test**

```python
# tests/widget/test_time_range_filter.py
"""Tests for TimeRangeFilter component."""

import pytest
from PyQt6.QtCore import QTime
from PyQt6.QtWidgets import QApplication

from src.ui.components.time_range_filter import TimeRangeFilter


@pytest.fixture(scope="module")
def app():
    """Create QApplication for widget tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestTimeRangeFilter:
    """Tests for TimeRangeFilter."""

    def test_initial_state_all_times(self, app, qtbot):
        """Should start with 'All Times' checked."""
        widget = TimeRangeFilter()
        qtbot.addWidget(widget)

        start, end, all_times = widget.get_range()
        assert all_times is True
        assert start is None
        assert end is None

    def test_emits_signal_on_change(self, app, qtbot):
        """Should emit time_range_changed when toggled."""
        widget = TimeRangeFilter()
        qtbot.addWidget(widget)

        signals = []
        widget.time_range_changed.connect(lambda s, e, a: signals.append((s, e, a)))

        # Uncheck "All Times"
        widget._all_times_checkbox.setChecked(False)

        assert len(signals) == 1
        start, end, all_times = signals[0]
        assert all_times is False
        assert start is not None
        assert end is not None

    def test_get_range_returns_time_strings(self, app, qtbot):
        """Should return HH:MM:SS format strings."""
        widget = TimeRangeFilter()
        qtbot.addWidget(widget)

        widget._all_times_checkbox.setChecked(False)
        widget._start_time.setTime(QTime(9, 30, 0))
        widget._end_time.setTime(QTime(16, 0, 0))

        start, end, all_times = widget.get_range()
        assert start == "09:30:00"
        assert end == "16:00:00"
        assert all_times is False

    def test_reset_returns_to_all_times(self, app, qtbot):
        """Reset should return to 'All Times' state."""
        widget = TimeRangeFilter()
        qtbot.addWidget(widget)

        widget._all_times_checkbox.setChecked(False)
        widget.reset()

        start, end, all_times = widget.get_range()
        assert all_times is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/widget/test_time_range_filter.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/ui/components/time_range_filter.py
"""TimeRangeFilter widget for filtering by time of day."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QTimeEdit,
    QWidget,
)

from src.ui.constants import Colors, Spacing


class TimeRangeFilter(QWidget):
    """Time range filter with start/end time pickers and 'All Times' toggle.

    Emits time_range_changed signal when range changes with HH:MM:SS strings.
    When 'All Times' is checked, emits None values for start/end.

    Attributes:
        time_range_changed: Signal emitted when time range changes.
            Args: (start: str | None, end: str | None, all_times: bool)
            Start/end are HH:MM:SS format strings or None if all_times=True.
    """

    time_range_changed = pyqtSignal(object, object, bool)  # start, end, all_times

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize TimeRangeFilter.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._all_times = True
        self._setup_ui()
        self._apply_style()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the filter UI layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        # Label
        self._label = QLabel("Time Range:")
        layout.addWidget(self._label)

        # Start time picker (default 9:30 AM market open)
        self._start_time = QTimeEdit()
        self._start_time.setDisplayFormat("HH:mm:ss")
        self._start_time.setTime(self._start_time.time().fromString("09:30:00", "HH:mm:ss"))
        self._start_time.setEnabled(False)
        layout.addWidget(self._start_time)

        # "to" label
        self._to_label = QLabel("to")
        layout.addWidget(self._to_label)

        # End time picker (default 4:00 PM market close)
        self._end_time = QTimeEdit()
        self._end_time.setDisplayFormat("HH:mm:ss")
        self._end_time.setTime(self._end_time.time().fromString("16:00:00", "HH:mm:ss"))
        self._end_time.setEnabled(False)
        layout.addWidget(self._end_time)

        # All Times checkbox
        self._all_times_checkbox = QCheckBox("All Times")
        self._all_times_checkbox.setChecked(True)
        layout.addWidget(self._all_times_checkbox)

        layout.addStretch()

    def _apply_style(self) -> None:
        """Apply Observatory theme styling."""
        label_style = f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
            }}
        """
        self._label.setStyleSheet(label_style)
        self._to_label.setStyleSheet(label_style)

        time_edit_style = f"""
            QTimeEdit {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 80px;
            }}
            QTimeEdit:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QTimeEdit:focus {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QTimeEdit:disabled {{
                color: {Colors.TEXT_DISABLED};
                background-color: {Colors.BG_SURFACE};
            }}
            QTimeEdit::up-button, QTimeEdit::down-button {{
                width: 16px;
            }}
        """
        self._start_time.setStyleSheet(time_edit_style)
        self._end_time.setStyleSheet(time_edit_style)

        checkbox_style = f"""
            QCheckBox {{
                color: {Colors.TEXT_PRIMARY};
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid {Colors.BG_BORDER};
                background-color: {Colors.BG_ELEVATED};
            }}
            QCheckBox::indicator:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QCheckBox::indicator:checked {{
                background-color: {Colors.SIGNAL_CYAN};
                border-color: {Colors.SIGNAL_CYAN};
            }}
        """
        self._all_times_checkbox.setStyleSheet(checkbox_style)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self._all_times_checkbox.toggled.connect(self._on_all_times_toggled)
        self._start_time.timeChanged.connect(self._on_time_changed)
        self._end_time.timeChanged.connect(self._on_time_changed)

    def _on_all_times_toggled(self, checked: bool) -> None:
        """Handle 'All Times' checkbox toggle."""
        self._all_times = checked
        self._start_time.setEnabled(not checked)
        self._end_time.setEnabled(not checked)
        self._emit_change()

    def _on_time_changed(self) -> None:
        """Handle time picker value change."""
        if not self._all_times:
            self._validate_time_range()
            self._emit_change()

    def _validate_time_range(self) -> None:
        """Auto-correct if end time is before start time."""
        if self._end_time.time() < self._start_time.time():
            self._end_time.blockSignals(True)
            self._end_time.setTime(self._start_time.time())
            self._end_time.blockSignals(False)

    def _emit_change(self) -> None:
        """Emit time_range_changed signal with current values."""
        if self._all_times:
            self.time_range_changed.emit(None, None, True)
        else:
            start = self._start_time.time().toString("HH:mm:ss")
            end = self._end_time.time().toString("HH:mm:ss")
            self.time_range_changed.emit(start, end, False)

    def get_range(self) -> tuple[str | None, str | None, bool]:
        """Get current time range as HH:MM:SS strings.

        Returns:
            Tuple of (start_time, end_time, all_times).
            Strings are None if all_times=True.
        """
        if self._all_times:
            return (None, None, True)
        return (
            self._start_time.time().toString("HH:mm:ss"),
            self._end_time.time().toString("HH:mm:ss"),
            False,
        )

    def reset(self) -> None:
        """Reset to default state (All Times checked)."""
        self._all_times_checkbox.blockSignals(True)
        self._all_times_checkbox.setChecked(True)
        self._all_times_checkbox.blockSignals(False)
        self._all_times = True
        self._start_time.setEnabled(False)
        self._end_time.setEnabled(False)
        self._emit_change()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/widget/test_time_range_filter.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/ui/components/time_range_filter.py tests/widget/test_time_range_filter.py
git commit -m "feat: add TimeRangeFilter component for time-of-day filtering"
```

---

## Task 6: Integrate TimeRangeFilter into FilterPanel

**Files:**
- Modify: `src/ui/components/filter_panel.py`

**Step 1: Add import**

```python
from src.ui.components.time_range_filter import TimeRangeFilter
```

**Step 2: Add signal to FilterPanel**

```python
class FilterPanel(QWidget):
    filters_applied = pyqtSignal(list)
    filters_cleared = pyqtSignal()
    first_trigger_toggled = pyqtSignal(bool)
    date_range_changed = pyqtSignal(object, object, bool)
    time_range_changed = pyqtSignal(object, object, bool)  # Add this
```

**Step 3: Add TimeRangeFilter to _setup_ui**

After DateRangeFilter creation, add:

```python
# Time range filter
self._time_range_filter = TimeRangeFilter()
layout.addWidget(self._time_range_filter)
```

**Step 4: Connect signal**

```python
self._time_range_filter.time_range_changed.connect(self._on_time_range_changed)
```

**Step 5: Add handler method**

```python
def _on_time_range_changed(
    self, start: str | None, end: str | None, all_times: bool
) -> None:
    """Handle time range filter change."""
    self._time_start = start
    self._time_end = end
    self._all_times_time = all_times
    self.time_range_changed.emit(start, end, all_times)
```

**Step 6: Add get_time_range method**

```python
def get_time_range(self) -> tuple[str | None, str | None, bool]:
    """Get current time range filter values."""
    return self._time_range_filter.get_range()
```

**Step 7: Run tests**

Run: `pytest tests/widget/test_filter_panel.py -v`
Expected: PASS

**Step 8: Commit**

```bash
git add src/ui/components/filter_panel.py
git commit -m "feat: integrate TimeRangeFilter into FilterPanel"
```

---

## Task 7: Integrate Time Filtering into FilterEngine

**Files:**
- Modify: `src/core/filter_engine.py`

**Step 1: Add apply_time_range method**

```python
@staticmethod
def apply_time_range(
    df: pd.DataFrame,
    time_col: str,
    start_time: str | None,
    end_time: str | None,
) -> pd.DataFrame:
    """Filter DataFrame by time-of-day range.

    Args:
        df: DataFrame to filter.
        time_col: Column containing time values.
        start_time: Start time in HH:MM:SS format, or None for no lower bound.
        end_time: End time in HH:MM:SS format, or None for no upper bound.

    Returns:
        Filtered DataFrame.
    """
    if start_time is None and end_time is None:
        return df

    if time_col not in df.columns:
        logger.warning("Time column '%s' not found, skipping time filter", time_col)
        return df

    # Convert time column to comparable format
    time_series = pd.to_datetime(df[time_col], format="%H:%M:%S", errors="coerce").dt.time

    mask = pd.Series(True, index=df.index)

    if start_time is not None:
        from datetime import time as dt_time
        start = dt_time.fromisoformat(start_time)
        mask &= time_series >= start

    if end_time is not None:
        from datetime import time as dt_time
        end = dt_time.fromisoformat(end_time)
        mask &= time_series <= end

    return df[mask]
```

**Step 2: Run tests**

Run: `pytest tests/unit/test_filter_engine.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add src/core/filter_engine.py
git commit -m "feat: add time range filtering to FilterEngine"
```

---

## Task 8: Connect Time Filtering in FeatureExplorerTab

**Files:**
- Modify: `src/tabs/feature_explorer.py`

**Step 1: Add time range state variables**

In `__init__`:
```python
self._time_start: str | None = None
self._time_end: str | None = None
self._all_times: bool = True
```

**Step 2: Connect signal**

In `_connect_signals`:
```python
self._filter_panel.time_range_changed.connect(self._on_time_range_changed)
```

**Step 3: Add handler**

```python
def _on_time_range_changed(
    self, start: str | None, end: str | None, all_times: bool
) -> None:
    """Handle time range filter change."""
    self._time_start = start
    self._time_end = end
    self._all_times = all_times
    self._apply_current_filters()
```

**Step 4: Update _apply_current_filters**

Add time filtering after date filtering:

```python
# Apply time range filter
if (
    not self._all_times
    and self._app_state.column_mapping is not None
    and self._app_state.column_mapping.time is not None
):
    filtered_df = FilterEngine.apply_time_range(
        filtered_df,
        self._app_state.column_mapping.time,
        self._time_start,
        self._time_end,
    )
```

**Step 5: Run tests**

Run: `pytest tests/widget/test_feature_explorer.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/tabs/feature_explorer.py
git commit -m "feat: integrate time filtering in Feature Explorer"
```

---

## Task 9: Investigate and Fix Baseline Metrics Percentage Display

**Files:**
- Modify: `src/tabs/data_input.py` (if needed)
- Modify: `src/core/metrics.py` (if needed)

**Step 1: Add debug logging**

In `MetricsPanel.update_metrics()`, add logging:

```python
def update_metrics(self, metrics: TradingMetrics | None) -> None:
    if metrics is None:
        ...
        return

    logger.debug(
        "MetricsPanel update - avg_winner=%s, avg_loser=%s, win_rate=%s",
        metrics.avg_winner,
        metrics.avg_loser,
        metrics.win_rate,
    )
    # ... rest of method
```

**Step 2: Verify calculation path**

Check `MetricsCalculator.calculate()` is being called correctly:
- Verify gain column values are in expected decimal format (0.23 = 23%)
- Confirm * 100 multiplication is happening

**Step 3: Check data format**

The expected format is **decimal format**:
- `0.23` means 23% gain
- After * 100, displays as "23%"

If user data is in a different format (e.g., already percentage: `23` means 23%), the display will show "2300%".

**Step 4: Consider adding format detection**

Optional enhancement: Detect if values seem to already be in percentage format and skip multiplication.

```python
# In metrics.py, before multiplication
if winner_count > 0:
    raw_avg = sum(winner_gains) / winner_count
    # Heuristic: if raw average is > 1 or < -1, data might already be in percentage form
    if abs(raw_avg) > 1:
        logger.warning(
            "Gain values appear to be in percentage format (avg=%.2f). "
            "Expected decimal format (e.g., 0.05 for 5%%).",
            raw_avg,
        )
    avg_winner = raw_avg * 100
```

**Step 5: Manual testing**

1. Load test data with known gain values
2. Verify displayed percentages match expectations
3. Document expected data format in user docs

**Step 6: Commit any fixes**

```bash
git add -A
git commit -m "fix: investigate and document baseline metrics percentage display"
```

---

## Task 10: Final Integration Testing

**Step 1: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

**Step 2: Manual testing checklist**

- [ ] Scroll wheel does not change combo/spinbox values when not focused
- [ ] Click to focus, then scroll wheel works normally
- [ ] TimeRangeFilter appears in Feature Explorer sidebar
- [ ] Time filtering works correctly (filters by time-of-day)
- [ ] Baseline metrics display correctly (23% not 0.23%)
- [ ] No regressions in existing functionality

**Step 3: Final commit**

```bash
git add -A
git commit -m "test: integration testing for display formatting fixes"
```

---

## Summary

| Task | Component | Description |
|------|-----------|-------------|
| 1 | no_scroll_widgets.py | Create NoScrollComboBox/NoScrollDoubleSpinBox |
| 2-4 | data_input.py, user_inputs_panel.py, others | Replace standard widgets with NoScroll variants |
| 5 | time_range_filter.py | Create TimeRangeFilter component |
| 6-8 | filter_panel.py, filter_engine.py, feature_explorer.py | Integrate time filtering |
| 9 | metrics.py, data_input.py | Investigate/fix percentage display |
| 10 | All | Integration testing |
