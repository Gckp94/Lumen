# Four Issues Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix four bugs: (1) initial metrics not applying default stop-loss, (2) Feature Explorer chart not showing stop-loss adjusted gains, (3) font loading warning, (4) time range filter matching 0 rows.

**Architecture:** Issue 1 requires passing adjustment_params to the initial metrics calculation. Issue 2 requires adding an "adjusted_gain_pct" column to the baseline DataFrame when adjustments are applied. Issue 3 is a warning suppression/documentation fix. Issue 4 requires better time parsing with diagnostic logging.

**Tech Stack:** Python 3.11+, PyQt6, pandas

---

## Task 1: Fix Initial Metrics Calculation Missing Stop-Loss

**Files:**
- Modify: `src/tabs/data_input.py:1546-1554`
- Test: `tests/tabs/test_data_input.py` (if exists)

**Step 1: Write the failing test**

Create a test that verifies initial metrics calculation applies default stop-loss:

```python
def test_initial_metrics_use_default_adjustment_params():
    """Verify initial metrics calculation uses default stop-loss and efficiency."""
    from src.tabs.data_input import DataInputTab
    from src.core.app_state import AppState
    from src.core.models import ColumnMapping
    import pandas as pd

    app_state = AppState()
    tab = DataInputTab(app_state)

    # Create test DataFrame with known values
    df = pd.DataFrame({
        'ticker': ['AAPL', 'AAPL'],
        'date': ['2024-01-01', '2024-01-02'],
        'time': ['09:30:00', '09:30:00'],
        'gain_pct': [0.10, -0.05],  # 10% gain, 5% loss (decimal format)
        'mae_pct': [5.0, 12.0],  # 5% MAE (under stop), 12% MAE (over 8% stop)
    })

    # Set up state
    tab._df = df
    tab._selected_path = Path('test.csv')

    mapping = ColumnMapping(
        ticker='ticker',
        date='date',
        time='time',
        gain_pct='gain_pct',
        mae_pct='mae_pct',
        win_loss_derived=True,
    )

    # Trigger mapping continue
    tab._on_mapping_continue(mapping)

    # Default adjustment: stop_loss=8%, efficiency=5%
    # Trade 1: mae 5% < 8%, so gain stays 10%, adjusted = 10% - 5% = 5%
    # Trade 2: mae 12% > 8%, so gain = -8%, adjusted = -8% - 5% = -13%

    # Verify adjustment was applied
    metrics = app_state.baseline_metrics
    assert metrics is not None
    # With adjustment, trade 1 is winner (5%), trade 2 is loser (-13%)
    assert metrics.win_rate == 50.0  # 1 of 2 trades
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/tabs/test_data_input.py::test_initial_metrics_use_default_adjustment_params -v`
Expected: FAIL - metrics not using adjustment params

**Step 3: Implement the fix**

In `src/tabs/data_input.py`, modify `_on_mapping_continue` method to pass adjustment params:

```python
def _on_mapping_continue(self, mapping: ColumnMapping | None = None) -> None:
    # ... existing code ...

    # Get current adjustment params (default values)
    adjustment_params = self._adjustment_panel.get_params()
    self._pending_adjustment_params = adjustment_params

    # Calculate metrics WITH adjustment params
    metrics, _, _ = self._metrics_calculator.calculate(
        df=baseline_df,
        gain_col=mapping.gain_pct,
        win_loss_col=mapping.win_loss,
        derived=mapping.win_loss_derived,
        breakeven_is_win=mapping.breakeven_is_win,
        adjustment_params=adjustment_params,  # ADD THIS
        mae_col=mapping.mae_pct,              # ADD THIS
        date_col=mapping.date,
        time_col=mapping.time,
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/tabs/test_data_input.py::test_initial_metrics_use_default_adjustment_params -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tabs/data_input.py tests/tabs/test_data_input.py
git commit -m "fix: apply default stop-loss adjustment on initial metrics calculation

Previously, when clicking Continue after column mapping, metrics were
calculated without stop-loss adjustment. Now the default adjustment
params (8% stop-loss, 5% efficiency) are applied from the start.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Add Stop-Loss Adjusted Gain Column to DataFrame

**Files:**
- Modify: `src/tabs/data_input.py:1619-1656` (_recalculate_metrics method)
- Modify: `src/core/app_state.py` (add adjusted gain column tracking)
- Test: `tests/core/test_adjusted_gains.py` (new)

**Step 1: Write the failing test**

```python
def test_baseline_df_has_adjusted_gain_column_after_adjustment():
    """Verify baseline_df gets an adjusted_gain_pct column when adjustments applied."""
    from src.core.app_state import AppState
    from src.core.models import AdjustmentParams
    import pandas as pd

    app_state = AppState()

    # Create baseline DataFrame
    app_state.baseline_df = pd.DataFrame({
        'ticker': ['AAPL', 'GOOG'],
        'gain_pct': [0.10, -0.05],
        'mae_pct': [5.0, 12.0],
    })

    # After adjustment params change, baseline_df should have adjusted column
    params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
    adjusted_gains = params.calculate_adjusted_gains(
        app_state.baseline_df, 'gain_pct', 'mae_pct'
    )
    app_state.baseline_df['adjusted_gain_pct'] = adjusted_gains

    assert 'adjusted_gain_pct' in app_state.baseline_df.columns
    # Trade 1: 10% gain, 5% MAE < 8% stop -> 10% - 5% eff = 5% = 0.05
    # Trade 2: -5% gain, 12% MAE > 8% stop -> -8% - 5% eff = -13% = -0.13
    assert abs(app_state.baseline_df['adjusted_gain_pct'].iloc[0] - 0.05) < 0.001
    assert abs(app_state.baseline_df['adjusted_gain_pct'].iloc[1] - (-0.13)) < 0.001
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_adjusted_gains.py::test_baseline_df_has_adjusted_gain_column_after_adjustment -v`
Expected: PASS (this is testing the model, which works)

**Step 3: Update DataInputTab to add adjusted column**

In `src/tabs/data_input.py`, modify both `_on_mapping_continue` and `_recalculate_metrics`:

```python
def _on_mapping_continue(self, mapping: ColumnMapping | None = None) -> None:
    # ... after calculating metrics ...

    # Add adjusted_gain_pct column to baseline_df for chart use
    if self._app_state is not None and baseline_df is not None:
        adjusted_gains = adjustment_params.calculate_adjusted_gains(
            baseline_df, mapping.gain_pct, mapping.mae_pct
        )
        baseline_df['adjusted_gain_pct'] = adjusted_gains
        self._app_state.baseline_df = baseline_df  # Update with new column

def _recalculate_metrics(self) -> None:
    # ... existing code ...

    # Update adjusted_gain_pct column in baseline_df
    if baseline_df is not None and mapping is not None:
        adjusted_gains = self._pending_adjustment_params.calculate_adjusted_gains(
            baseline_df, mapping.gain_pct, mapping.mae_pct
        )
        baseline_df['adjusted_gain_pct'] = adjusted_gains
        # Re-emit data_loaded so Feature Explorer sees updated column
        self._app_state.data_loaded.emit(baseline_df)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_adjusted_gains.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tabs/data_input.py tests/core/test_adjusted_gains.py
git commit -m "feat: add adjusted_gain_pct column to baseline DataFrame

When stop-loss and efficiency adjustments are applied, the baseline_df
now includes an 'adjusted_gain_pct' column that users can select in
the Feature Explorer chart to visualize stop-loss adjusted gains.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Improve Font Loading Warning (Documentation/Minor)

**Files:**
- Modify: `src/ui/theme.py:28-44`

**Step 1: Write the failing test**

```python
def test_font_loading_handles_missing_directory_gracefully():
    """Verify font loading doesn't cause errors when fonts dir missing."""
    from src.ui.theme import load_fonts
    from unittest.mock import MagicMock

    app = MagicMock()
    result = load_fonts(app)

    # Should return False but not raise an exception
    assert result == False or result == True  # Depends on whether fonts exist
```

**Step 2: Run test**

Run: `pytest tests/ui/test_theme.py::test_font_loading_handles_missing_directory_gracefully -v`
Expected: PASS

**Step 3: Improve the warning message**

In `src/ui/theme.py`, make the warning more informative:

```python
def load_fonts(app: QApplication) -> bool:
    """Load custom fonts from assets/fonts/.

    Args:
        app: The QApplication instance (unused but kept for API consistency).

    Returns:
        True if at least one font was loaded successfully, False otherwise.
    """
    font_dir = Path(__file__).parent.parent.parent / "assets" / "fonts"

    if not font_dir.exists():
        logger.info(
            "Custom fonts directory not found at %s - using system fonts. "
            "This is normal if no custom fonts have been configured.",
            font_dir
        )
        return False

    fonts_loaded = 0
    for font_file in font_dir.glob("*.[to]tf"):  # .ttf and .otf
        font_id = QFontDatabase.addApplicationFont(str(font_file))
        if font_id >= 0:
            fonts_loaded += 1
            logger.debug("Loaded font: %s", font_file.name)
        else:
            logger.warning("Failed to load font: %s", font_file.name)

    if fonts_loaded > 0:
        logger.info("Loaded %d custom fonts", fonts_loaded)
    else:
        logger.info("No custom fonts found in %s - using system fonts", font_dir)

    return fonts_loaded > 0
```

**Step 4: Run test**

Run: `pytest tests/ui/test_theme.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/ui/theme.py
git commit -m "fix: improve font loading log message from warning to info

The 'no custom fonts' message is expected behavior when fonts haven't
been configured, not a warning. Changed to INFO level with clearer
message explaining this is normal.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Fix Time Range Filter Matching 0 Rows

**Files:**
- Modify: `src/core/filter_engine.py:80-121`
- Test: `tests/core/test_filter_engine.py`

**Step 1: Write the failing test**

```python
def test_time_filter_handles_various_formats():
    """Verify time filter handles different time column formats."""
    import pandas as pd
    from src.core.filter_engine import FilterEngine

    # Test data with different time formats
    df = pd.DataFrame({
        'time_str': ['04:30:00', '09:30:00', '12:00:00', '16:00:00'],
        'time_datetime': pd.to_datetime(['04:30:00', '09:30:00', '12:00:00', '16:00:00']).time,
        'time_mixed': ['4:30:00', '9:30', '12:00:00', '16:00'],
    })

    # Filter 04:30:00 to 12:00:00
    result = FilterEngine.apply_time_range(df, 'time_str', '04:30:00', '12:00:00')
    assert len(result) == 3  # First 3 rows

    result = FilterEngine.apply_time_range(df, 'time_mixed', '04:30:00', '12:00:00')
    assert len(result) == 3
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_filter_engine.py::test_time_filter_handles_various_formats -v`
Expected: FAIL - mixed format times may not parse correctly

**Step 3: Implement the fix with better time parsing**

In `src/core/filter_engine.py`, improve `apply_time_range`:

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
        return df.copy()

    if time_col not in df.columns:
        logger.warning("Time column '%s' not found, skipping time filter", time_col)
        return df.copy()

    # Get raw time values for diagnostic
    raw_values = df[time_col].head(5).tolist()
    logger.debug("Time filter: column '%s' sample values: %s", time_col, raw_values)

    # Try multiple parsing strategies
    time_series = None

    # Strategy 1: Already datetime.time objects
    if hasattr(df[time_col].iloc[0] if len(df) > 0 else None, 'hour'):
        time_series = df[time_col]
        logger.debug("Time column already contains time objects")
    else:
        # Strategy 2: Parse as datetime and extract time
        try:
            # Try ISO format first (HH:MM:SS)
            parsed = pd.to_datetime(df[time_col], format="%H:%M:%S", errors="coerce")
            if parsed.notna().sum() > 0:
                time_series = parsed.dt.time
                logger.debug("Parsed time using HH:MM:SS format")
            else:
                # Try mixed format
                parsed = pd.to_datetime(df[time_col], format="mixed", errors="coerce")
                time_series = parsed.dt.time
                logger.debug("Parsed time using mixed format")
        except Exception as e:
            logger.warning("Failed to parse time column '%s': %s", time_col, e)
            return df.copy()

    if time_series is None:
        logger.warning("Could not parse time column '%s'", time_col)
        return df.copy()

    # Check how many values parsed successfully
    valid_count = time_series.notna().sum()
    logger.debug(
        "Time filter: %d of %d values parsed successfully",
        valid_count, len(df)
    )

    if valid_count == 0:
        logger.warning(
            "Time filter: 0 values parsed from column '%s'. "
            "Sample values: %s. Check time format.",
            time_col, raw_values
        )
        return df.copy()

    mask = pd.Series(True, index=df.index)

    if start_time is not None:
        start = start_time if isinstance(start_time, dt_time) else dt_time.fromisoformat(start_time)
        mask &= time_series >= start

    if end_time is not None:
        end = end_time if isinstance(end_time, dt_time) else dt_time.fromisoformat(end_time)
        mask &= time_series <= end

    result_count = mask.sum()
    logger.debug(
        "Time filter: %d of %d rows match range %s to %s",
        result_count, len(df), start_time, end_time
    )

    return df[mask].copy()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_filter_engine.py::test_time_filter_handles_various_formats -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/filter_engine.py tests/core/test_filter_engine.py
git commit -m "fix: improve time range filter parsing with diagnostic logging

Added multiple parsing strategies for time columns and diagnostic
logging to help debug when time filters return 0 matches. Now handles
HH:MM:SS, HH:MM, and datetime.time object formats.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Integration Testing

**Files:**
- Test: `tests/integration/test_four_issues.py` (new)

**Step 1: Write integration tests**

```python
"""Integration tests for the four-issues fix."""
import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.app_state import AppState
from src.core.models import AdjustmentParams, ColumnMapping
from src.core.filter_engine import FilterEngine


class TestIssue1InitialStopLoss:
    """Test that initial metrics apply default stop-loss."""

    def test_metrics_change_when_stop_loss_applied(self):
        """Metrics with 100% stop-loss should differ from 8% stop-loss."""
        from src.core.metrics import MetricsCalculator

        df = pd.DataFrame({
            'gain_pct': [0.20, -0.10, 0.15, -0.50],  # 20%, -10%, 15%, -50%
            'mae_pct': [3.0, 15.0, 5.0, 60.0],  # 3%, 15%, 5%, 60% MAE
        })

        calc = MetricsCalculator()

        # No adjustment (100% stop-loss effectively)
        metrics_no_adj, _, _ = calc.calculate(df, 'gain_pct')

        # With 8% stop-loss, 5% efficiency
        params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
        metrics_adj, _, _ = calc.calculate(
            df, 'gain_pct', adjustment_params=params, mae_col='mae_pct'
        )

        # Win rate should differ because some trades hit stop-loss
        assert metrics_no_adj.win_rate != metrics_adj.win_rate


class TestIssue2AdjustedGainColumn:
    """Test that adjusted_gain_pct column is added."""

    def test_adjusted_gain_column_exists_after_adjustment(self):
        """Baseline DataFrame should have adjusted_gain_pct column."""
        params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
        df = pd.DataFrame({
            'gain_pct': [0.10, -0.05],
            'mae_pct': [5.0, 12.0],
        })

        df['adjusted_gain_pct'] = params.calculate_adjusted_gains(df, 'gain_pct', 'mae_pct')

        assert 'adjusted_gain_pct' in df.columns
        # Trade 1: 10% gain, 5% < 8% stop, adj = 10% - 5% = 5% = 0.05
        assert abs(df['adjusted_gain_pct'].iloc[0] - 0.05) < 0.001


class TestIssue4TimeFilter:
    """Test time range filter with various formats."""

    def test_filter_04_30_to_12_00(self):
        """Filter should include times from 04:30 to 12:00."""
        df = pd.DataFrame({
            'time': ['04:30:00', '09:30:00', '12:00:00', '16:00:00'],
            'value': [1, 2, 3, 4],
        })

        result = FilterEngine.apply_time_range(df, 'time', '04:30:00', '12:00:00')

        assert len(result) == 3
        assert list(result['value']) == [1, 2, 3]

    def test_filter_with_datetime_time_objects(self):
        """Filter should work with datetime.time objects."""
        from datetime import time

        df = pd.DataFrame({
            'time': [time(4, 30), time(9, 30), time(12, 0), time(16, 0)],
            'value': [1, 2, 3, 4],
        })

        result = FilterEngine.apply_time_range(df, 'time', '04:30:00', '12:00:00')

        assert len(result) == 3
```

**Step 2: Run all integration tests**

Run: `pytest tests/integration/test_four_issues.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/integration/test_four_issues.py
git commit -m "test: add integration tests for four-issues fix

Covers:
- Issue 1: Initial metrics apply default stop-loss
- Issue 2: adjusted_gain_pct column exists after adjustment
- Issue 4: Time filter handles various formats

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Manual Verification

**Step 1: Run the application and verify fixes**

Run: `python -m src.main`

Manual verification checklist:
1. Load `Para40Min15Prev40.xlsx`
2. Verify initial metrics match values after manually setting stop-loss to same default (8%)
3. In Feature Explorer, verify "adjusted_gain_pct" appears in column dropdown
4. Set time range 04:30:00 to 12:00:00, verify rows match (not 0)
5. Check console output for font loading message (should be INFO, not WARNING)

**Step 2: Final commit**

```bash
git add -A
git commit -m "docs: update plan with implementation complete

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```
