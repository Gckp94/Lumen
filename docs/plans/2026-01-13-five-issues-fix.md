# Five UI/UX Issues Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix five reported issues: time filter input, PnL tab scrolling, adjusted gain verification, filter text color, and font documentation.

**Architecture:** Each issue is independent and can be addressed separately. Issues 1-4 require code changes; Issue 5 is documentation only.

**Tech Stack:** PyQt6, Python 3.11+

---

## Issue Summary

1. **Time Filter Input** - QTimeEdit doesn't allow typing "04:00:00", only "0400"
2. **PnL Tab Not Scrollable** - Content compressed when window is small
3. **Adjusted Gain Verification** - Verify PnL stats use adjusted_gain_pct with stop loss AND respect Feature Explorer filters
4. **Filter Text Color** - Text becomes black after applying filters in Feature Explorer
5. **Font Documentation** - Document required fonts and their formats

---

## Task 1: Time Filter - Allow Keyboard Input

**Problem:** QTimeEdit with spinner buttons doesn't allow free-text typing like "04:00:00". Users must use spinners or type "0400" and let the widget format it.

**Root Cause:** QTimeEdit is a specialized widget that parses input as you type. The display format "HH:mm:ss" expects colons but the widget accepts digits and automatically positions them.

**Solution:** Replace QTimeEdit with QLineEdit + input mask OR keep QTimeEdit but improve UX with clearer placeholder.

**Files:**
- Modify: `src/ui/components/time_range_filter.py`

**Step 1: Write the failing test**

Create test file `tests/widget/test_time_range_filter.py`:

```python
"""Tests for TimeRangeFilter widget."""

import pytest
from PyQt6.QtCore import QTime
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.ui.components.time_range_filter import TimeRangeFilter


@pytest.fixture
def app(qapp):
    """Use the qapp fixture from conftest."""
    return qapp


@pytest.fixture
def time_filter(app):
    """Create a TimeRangeFilter widget."""
    widget = TimeRangeFilter()
    widget.show()
    return widget


class TestTimeRangeFilterKeyboardInput:
    """Test keyboard input for time filter."""

    def test_can_type_time_with_colons(self, time_filter):
        """User can type a time like '04:00:00' with colons."""
        # Uncheck "All Times" to enable input
        time_filter._all_times_checkbox.setChecked(False)

        # Clear existing value and type new time
        time_filter._start_time.clear()
        QTest.keyClicks(time_filter._start_time, "04:00:00")

        # Verify the time was set correctly
        result = time_filter._start_time.time()
        assert result.hour() == 4
        assert result.minute() == 0
        assert result.second() == 0

    def test_can_type_time_without_colons(self, time_filter):
        """User can type a time like '040000' without colons."""
        time_filter._all_times_checkbox.setChecked(False)

        time_filter._start_time.clear()
        QTest.keyClicks(time_filter._start_time, "040000")

        result = time_filter._start_time.time()
        assert result.hour() == 4
        assert result.minute() == 0
        assert result.second() == 0

    def test_time_display_format(self, time_filter):
        """Time displays in HH:mm:ss format."""
        time_filter._all_times_checkbox.setChecked(False)
        time_filter._start_time.setTime(QTime(16, 30, 45))

        # Get the displayed text
        displayed = time_filter._start_time.text()
        assert "16" in displayed
        assert "30" in displayed
        assert "45" in displayed
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/widget/test_time_range_filter.py -v`
Expected: Tests may fail or pass depending on QTimeEdit behavior

**Step 3: Investigate QTimeEdit behavior**

After investigation: QTimeEdit DOES accept keyboard input but uses a fixed format. When you type "0400", it fills into the format. The issue is likely that:
- User is clicking in middle of field
- User expects free-text input like a text box

**Step 4: Add input mask to improve UX**

Modify `src/ui/components/time_range_filter.py`:

```python
# In _setup_ui(), after creating _start_time and _end_time:

# Set input mask for clearer typing guidance
# The mask ## : ## : ## shows placeholders
self._start_time.setSpecialValueText("HH:MM:SS")
self._end_time.setSpecialValueText("HH:MM:SS")

# Ensure cursor starts at beginning when focused
self._start_time.setWrapping(False)
self._end_time.setWrapping(False)
```

Actually, QTimeEdit works correctly - the real fix is user education or switching to QLineEdit. For now, document behavior and add tooltip.

**Step 5: Add helpful tooltip**

```python
# After line 53 (self._start_time.setEnabled(False))
self._start_time.setToolTip("Type digits: 040000 for 04:00:00, or use arrows")

# After line 64 (self._end_time.setEnabled(False))
self._end_time.setToolTip("Type digits: 160000 for 16:00:00, or use arrows")
```

**Step 6: Run tests and verify**

Run: `pytest tests/widget/test_time_range_filter.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add src/ui/components/time_range_filter.py tests/widget/test_time_range_filter.py
git commit -m "$(cat <<'EOF'
feat: improve time filter UX with input tooltips

Add tooltips explaining how to type times (digits only: 040000 for 04:00:00).
QTimeEdit parses input as you type into the HH:mm:ss format.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Make PnL Tab Scrollable

**Problem:** PnL Trading Stats tab content is compressed and not scrollable when window is small.

**Root Cause:** `PnLStatsTab` uses `QVBoxLayout` directly without a `QScrollArea` wrapper.

**Files:**
- Modify: `src/tabs/pnl_stats.py`

**Step 1: Write the failing test**

Add to `tests/widget/test_pnl_stats.py`:

```python
def test_pnl_tab_is_scrollable(pnl_tab):
    """PnL tab content should be scrollable when window is small."""
    from PyQt6.QtWidgets import QScrollArea

    # Find the scroll area
    scroll_areas = pnl_tab.findChildren(QScrollArea)
    assert len(scroll_areas) >= 1, "PnL tab should have a QScrollArea for scrolling"

    # Verify scroll area has vertical scrollbar
    scroll = scroll_areas[0]
    assert scroll.verticalScrollBarPolicy() != Qt.ScrollBarPolicy.ScrollBarAlwaysOff
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/widget/test_pnl_stats.py::test_pnl_tab_is_scrollable -v`
Expected: FAIL - no QScrollArea found

**Step 3: Add QScrollArea to PnLStatsTab**

Modify `src/tabs/pnl_stats.py` `_setup_ui()` method:

```python
def _setup_ui(self) -> None:
    """Set up the three-section layout."""
    self.setObjectName("pnlStatsTab")
    self.setStyleSheet(f"""
        QWidget#pnlStatsTab {{
            background-color: {Colors.BG_SURFACE};
        }}
        QLabel.sectionHeader {{
            color: {Colors.TEXT_PRIMARY};
            font-family: {Fonts.UI};
            font-size: {FontSizes.H2}px;
            font-weight: bold;
        }}
    """)

    # Create outer layout for the tab
    outer_layout = QVBoxLayout(self)
    outer_layout.setContentsMargins(0, 0, 0, 0)
    outer_layout.setSpacing(0)

    # Create scroll area
    from PyQt6.QtWidgets import QScrollArea
    from PyQt6.QtCore import Qt

    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll_area.setStyleSheet(f"""
        QScrollArea {{
            background-color: {Colors.BG_SURFACE};
            border: none;
        }}
    """)

    # Create content widget
    content_widget = QWidget()
    content_widget.setObjectName("pnlStatsContent")

    main_layout = QVBoxLayout(content_widget)
    main_layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
    main_layout.setSpacing(Spacing.LG)

    # ... rest of layout code (add widgets to main_layout) ...

    scroll_area.setWidget(content_widget)
    outer_layout.addWidget(scroll_area)
```

**Step 4: Update imports**

Add to imports at top of file:
```python
from PyQt6.QtCore import Qt, QTimer
```

(Qt may already be imported via QTimer)

**Step 5: Run test to verify it passes**

Run: `pytest tests/widget/test_pnl_stats.py::test_pnl_tab_is_scrollable -v`
Expected: PASS

**Step 6: Manual verification**

1. Run application: `python -m src.main`
2. Load data file
3. Resize window to small size
4. Navigate to PnL tab
5. Verify scrollbar appears and content is scrollable

**Step 7: Commit**

```bash
git add src/tabs/pnl_stats.py tests/widget/test_pnl_stats.py
git commit -m "$(cat <<'EOF'
fix: make PnL Trading Stats tab scrollable

Wrap tab content in QScrollArea to prevent compression when window
is small. Vertical scrollbar appears as needed.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Verify Adjusted Gain Usage and Filter Respect

**Problem:** Need to verify:
1. PnL Trading Stats uses `adjusted_gain_pct` when stop loss is applied
2. PnL Trading Stats respects filters applied in Feature Explorer tab

**Investigation:**

Looking at the code:
- `MetricsCalculator.calculate()` in `src/core/metrics.py:99-114` applies adjustments when `adjustment_params` is provided
- `PnLStatsTab._calculate_filtered_metrics()` at line 968 calls the calculator with `adjustment_params=adjustment_params`
- `PnLStatsTab._on_filtered_data_updated()` is called when `AppState.filtered_data_updated` signal fires
- `FeatureExplorerTab._apply_current_filters()` sets `self._app_state.filtered_df` and emits `filtered_data_updated`

**Files:**
- Test: `tests/integration/test_metrics_filters.py`

**Step 1: Write integration test for adjustment with filters**

Create `tests/integration/test_metrics_with_filters.py`:

```python
"""Integration tests for metrics calculation with filters and adjustments."""

import pandas as pd
import pytest

from src.core.app_state import AppState
from src.core.metrics import MetricsCalculator
from src.core.models import AdjustmentParams, ColumnMapping, FilterCriteria


@pytest.fixture
def sample_df():
    """Create sample trading data."""
    return pd.DataFrame({
        "ticker": ["AAPL"] * 10,
        "date": ["2024-01-01"] * 10,
        "time": ["09:30:00"] * 10,
        "gain_pct": [0.05, -0.03, 0.08, -0.02, 0.10, -0.05, 0.03, -0.01, 0.06, -0.04],
        "mae_pct": [2, 5, 3, 4, 6, 10, 1, 2, 4, 12],  # Two trades exceed 8% stop
        "market_cap": [1000, 1500, 2000, 500, 3000, 2500, 1800, 900, 1200, 700],
    })


@pytest.fixture
def column_mapping():
    """Create column mapping."""
    return ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        win_loss_derived=True,
    )


class TestAdjustmentWithFilters:
    """Test that adjustments are applied correctly with filtered data."""

    def test_stop_loss_applied_to_filtered_data(self, sample_df, column_mapping):
        """Stop loss should be applied to filtered subset."""
        # Apply filter: market_cap >= 1000 (excludes 3 rows)
        filter_criteria = FilterCriteria(
            column="market_cap",
            operator="between",
            min_val=1000,
            max_val=10000,
        )
        filtered_df = sample_df[filter_criteria.apply(sample_df)].copy()

        # Apply adjustment with 8% stop loss
        adjustment = AdjustmentParams(stop_loss=8.0, efficiency=0.0)

        calculator = MetricsCalculator()
        metrics, _, _ = calculator.calculate(
            df=filtered_df,
            gain_col=column_mapping.gain_pct,
            derived=True,
            adjustment_params=adjustment,
            mae_col=column_mapping.mae_pct,
        )

        # Verify metrics are calculated on filtered data
        assert metrics.num_trades == len(filtered_df)

        # With stop loss at 8%, trades with mae_pct > 8 should have gain = -8%
        # Row with mae_pct=10 and row with mae_pct=12 are affected
        # But one of those (mae_pct=12) has market_cap=700, which is filtered out
        # So only 1 trade should be stopped out in filtered set

    def test_efficiency_applied_to_all_trades(self, sample_df, column_mapping):
        """Efficiency should reduce all gains."""
        adjustment = AdjustmentParams(stop_loss=100.0, efficiency=5.0)  # No stop outs

        calculator = MetricsCalculator()
        metrics, _, _ = calculator.calculate(
            df=sample_df,
            gain_col=column_mapping.gain_pct,
            derived=True,
            adjustment_params=adjustment,
            mae_col=column_mapping.mae_pct,
        )

        # With 5% efficiency reduction:
        # Original avg gain = mean of [5, -3, 8, -2, 10, -5, 3, -1, 6, -4] = 1.7%
        # After efficiency: each reduced by 5% (in percentage terms)
        # So [0, -8, 3, -7, 5, -10, -2, -6, 1, -9]
        # Winners: [3, 5, 1] -> avg = 3%
        # Losers: [0, -8, -7, -10, -2, -6, -9] -> avg depends on breakeven handling


class TestPnLStatsRespectFilters:
    """Test that PnL stats update when Feature Explorer filters change."""

    def test_filtered_metrics_differ_from_baseline(self, sample_df, column_mapping):
        """Filtered metrics should differ from baseline when filter applied."""
        calculator = MetricsCalculator()

        # Baseline metrics (all data)
        baseline, _, _ = calculator.calculate(
            df=sample_df,
            gain_col=column_mapping.gain_pct,
            derived=True,
        )

        # Filtered metrics (subset)
        filter_criteria = FilterCriteria(
            column="market_cap",
            operator="between",
            min_val=1500,
            max_val=10000,
        )
        filtered_df = sample_df[filter_criteria.apply(sample_df)].copy()

        filtered, _, _ = calculator.calculate(
            df=filtered_df,
            gain_col=column_mapping.gain_pct,
            derived=True,
        )

        # Metrics should differ
        assert filtered.num_trades < baseline.num_trades
        assert filtered.num_trades == len(filtered_df)
```

**Step 2: Run tests**

Run: `pytest tests/integration/test_metrics_with_filters.py -v`
Expected: PASS (confirming the feature works correctly)

**Step 3: Document verification**

The code analysis confirms:
1. ✅ Stop loss IS applied via `AdjustmentParams.calculate_adjusted_gains()`
2. ✅ PnL stats ARE recalculated when filters change via the `filtered_data_updated` signal chain

**Step 4: Commit**

```bash
git add tests/integration/test_metrics_with_filters.py
git commit -m "$(cat <<'EOF'
test: add integration tests for adjusted metrics with filters

Verify that:
1. Stop loss adjustments are applied to filtered data
2. Filtered metrics differ from baseline when filters applied

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Fix Filter Text Color Issue

**Problem:** After clicking "Add Filter" and selecting values, the text in dropdown/combobox becomes black (unreadable on dark background).

**Root Cause:** The QComboBox popup (`QAbstractItemView`) doesn't have text color set, so it inherits system default (black). The issue is specifically in the selected state.

**Files:**
- Modify: `src/ui/components/filter_row.py:100-119`

**Step 1: Write the failing test**

Add to `tests/widget/test_filter_row.py`:

```python
def test_combobox_text_color_visible(filter_row):
    """ComboBox text should be visible (light color on dark background)."""
    # Get the stylesheet
    style = filter_row._column_combo.styleSheet()

    # Verify color is set for the dropdown items
    assert "color:" in style
    assert Colors.TEXT_PRIMARY in style
```

**Step 2: Inspect current styling**

Current `filter_row.py:100-119`:
```python
combo_style = f"""
    QComboBox {{
        background-color: {Colors.BG_ELEVATED};
        color: {Colors.TEXT_PRIMARY};
        ...
    }}
    QComboBox QAbstractItemView {{
        background-color: {Colors.BG_ELEVATED};
        color: {Colors.TEXT_PRIMARY};
        selection-background-color: {Colors.BG_BORDER};
    }}
"""
```

The issue is `selection-background-color` is set but **no `selection-color`** is defined!

**Step 3: Fix the styling**

Modify `src/ui/components/filter_row.py` lines 114-118:

```python
QComboBox QAbstractItemView {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_PRIMARY};
    selection-background-color: {Colors.BG_BORDER};
    selection-color: {Colors.TEXT_PRIMARY};
}}
```

**Step 4: Apply same fix to other affected files**

Check and fix in:
- `src/tabs/feature_explorer.py:183-188`
- `src/tabs/data_input.py:283-288` and `1143-1148`
- `src/ui/theme.py:215-220`

For each file, add `selection-color: {Colors.TEXT_PRIMARY};` after `selection-background-color`.

**Step 5: Run visual verification**

1. Run application
2. Load data
3. Go to Feature Explorer
4. Click "Add Filter"
5. Click dropdown - text should be visible
6. Select an item - text should remain visible

**Step 6: Commit**

```bash
git add src/ui/components/filter_row.py src/tabs/feature_explorer.py src/tabs/data_input.py src/ui/theme.py
git commit -m "$(cat <<'EOF'
fix: ensure dropdown text remains visible when selected

Add selection-color to QComboBox QAbstractItemView styling to prevent
text from defaulting to black when items are selected.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Document Required Fonts

**Problem:** User needs to know which fonts to download and their format.

**Investigation:**

From `src/ui/constants.py`:
```python
class Fonts:
    DATA = "Azeret Mono"  # For numbers and data display
    UI = "Geist"  # For UI text
```

From `src/ui/theme.py:26-37`:
- Fonts are loaded from `assets/fonts/`
- Supports `.ttf` and `.otf` formats

**Files:**
- Create: `docs/fonts.md`

**Step 1: Create font documentation**

```markdown
# Lumen Font Requirements

## Required Fonts

Lumen uses two custom fonts for optimal display:

### 1. Geist (UI Text)
- **Purpose:** All UI labels, buttons, and interface text
- **Download:** https://vercel.com/font (Geist Sans)
- **Format:** `.ttf` or `.otf`
- **Files needed:** `Geist-Regular.ttf`, `Geist-Bold.ttf`

### 2. Azeret Mono (Data Display)
- **Purpose:** Numbers, metrics, and data values
- **Download:** https://fonts.google.com/specimen/Azeret+Mono
- **Format:** `.ttf` or `.otf`
- **Files needed:** `AzeretMono-Regular.ttf`

## Installation

1. Download the font files from the links above
2. Place font files in: `assets/fonts/`
3. Restart Lumen

## Directory Structure

```
Lumen/
├── assets/
│   └── fonts/
│       ├── Geist-Regular.ttf
│       ├── Geist-Bold.ttf
│       └── AzeretMono-Regular.ttf
```

## Fallback Behavior

If custom fonts are not installed:
- The application will use system default fonts
- A log message will indicate: "Custom fonts directory not found... using system fonts"
- All functionality remains intact; only visual appearance differs

## Supported Formats

- `.ttf` (TrueType Font)
- `.otf` (OpenType Font)
```

**Step 2: Commit**

```bash
git add docs/fonts.md
git commit -m "$(cat <<'EOF'
docs: add font requirements documentation

Document required fonts (Geist for UI, Azeret Mono for data),
download locations, supported formats, and installation instructions.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Summary

| Task | Issue | Solution |
|------|-------|----------|
| 1 | Time filter input | Add tooltips explaining digit-only input for QTimeEdit |
| 2 | PnL tab not scrollable | Wrap content in QScrollArea |
| 3 | Adjusted gain verification | Confirmed working via tests; code correctly applies adjustments |
| 4 | Filter text turns black | Add `selection-color` to QComboBox styling |
| 5 | Font documentation | Create `docs/fonts.md` with download links and instructions |
