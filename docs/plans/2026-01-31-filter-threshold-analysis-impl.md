# Filter Threshold Analysis Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Repurpose the Parameter Sensitivity tab to show trading metrics at varied filter thresholds, enabling "what-if" analysis for filter values.

**Architecture:** Replace the existing neighborhood/sweep analysis with a simpler threshold variation system. User selects a filter, chooses which bound to vary (min/max), sets a step size, and sees 11 rows of metrics (5 below, current, 5 above). All calculations use stop loss and efficiency adjustments from app state.

**Tech Stack:** PyQt6, pandas, existing MetricsCalculator, FilterEngine, AppState

---

## Task 1: Create ThresholdAnalysisResult Data Model

**Files:**
- Modify: `src/core/parameter_sensitivity.py`

**Step 1: Write the data model**

Add new dataclass after the existing imports (around line 15):

```python
@dataclass
class ThresholdRow:
    """Single row of threshold analysis results.

    Attributes:
        threshold: The filter threshold value for this row.
        is_current: Whether this is the current (baseline) row.
        num_trades: Number of trades passing all filters.
        ev_pct: Expected value percentage.
        win_pct: Win rate percentage.
        median_winner_pct: Median winning trade return.
        profit_ratio: Avg winner / abs(avg loser).
        edge_pct: Edge percentage.
        eg_pct: Expected geometric growth percentage.
        kelly_pct: Full Kelly stake percentage.
        max_loss_pct: Percentage of trades hitting stop loss.
    """
    threshold: float
    is_current: bool
    num_trades: int
    ev_pct: float | None
    win_pct: float | None
    median_winner_pct: float | None
    profit_ratio: float | None
    edge_pct: float | None
    eg_pct: float | None
    kelly_pct: float | None
    max_loss_pct: float | None


@dataclass
class ThresholdAnalysisResult:
    """Result of threshold analysis for a single filter.

    Attributes:
        filter_column: Column name of the analyzed filter.
        varied_bound: Which bound was varied ('min' or 'max').
        step_size: Step size used for threshold variation.
        rows: List of ThresholdRow results, ordered by threshold ascending.
        current_index: Index of the current (baseline) row in the list.
    """
    filter_column: str
    varied_bound: Literal["min", "max"]
    step_size: float
    rows: list[ThresholdRow]
    current_index: int
```

**Step 2: Commit**

```bash
git add src/core/parameter_sensitivity.py
git commit -m "feat(threshold-analysis): add ThresholdRow and ThresholdAnalysisResult data models"
```

---

## Task 2: Create ThresholdAnalysisEngine

**Files:**
- Modify: `src/core/parameter_sensitivity.py`

**Step 1: Write the engine class**

Add after the data models (replace or add alongside existing ParameterSensitivityEngine):

```python
class ThresholdAnalysisEngine:
    """Engine for calculating metrics at varied filter thresholds."""

    def __init__(
        self,
        baseline_df: pd.DataFrame,
        column_mapping: "ColumnMapping",
        active_filters: list["FilterCriteria"],
        adjustment_params: "AdjustmentParams",
    ) -> None:
        """Initialize the threshold analysis engine.

        Args:
            baseline_df: Data BEFORE user filters (but after first-trigger).
            column_mapping: ColumnMapping dataclass with column names.
            active_filters: Current active filters.
            adjustment_params: Stop loss and efficiency parameters.
        """
        self._baseline_df = baseline_df
        self._column_mapping = column_mapping
        self._active_filters = active_filters
        self._adjustment_params = adjustment_params
        self._cancelled = False

    def cancel(self) -> None:
        """Cancel the analysis."""
        self._cancelled = True

    def analyze(
        self,
        filter_index: int,
        vary_bound: Literal["min", "max"],
        step_size: float,
        progress_callback: Callable[[int], None] | None = None,
    ) -> ThresholdAnalysisResult:
        """Run threshold analysis on a single filter.

        Args:
            filter_index: Index of filter in active_filters to vary.
            vary_bound: Which bound to vary ('min' or 'max').
            step_size: Step size for threshold variation.
            progress_callback: Optional callback for progress updates (0-100).

        Returns:
            ThresholdAnalysisResult with 11 rows of metrics.
        """
        from src.core.filter_engine import FilterEngine
        from src.core.metrics import MetricsCalculator
        from src.core.statistics import calculate_expected_growth

        target_filter = self._active_filters[filter_index]
        current_value = target_filter.min_val if vary_bound == "min" else target_filter.max_val

        if current_value is None:
            raise ValueError(f"Filter has no {vary_bound} bound to vary")

        # Generate 11 threshold values: 5 below, current, 5 above
        thresholds = [current_value + (i - 5) * step_size for i in range(11)]

        filter_engine = FilterEngine()
        calculator = MetricsCalculator()
        rows: list[ThresholdRow] = []
        current_index = 5  # Middle row is current

        for i, threshold in enumerate(thresholds):
            if self._cancelled:
                break

            # Clone filters and modify the target filter's bound
            modified_filters = []
            for j, f in enumerate(self._active_filters):
                if j == filter_index:
                    # Create modified filter
                    from src.core.models import FilterCriteria
                    if vary_bound == "min":
                        modified_filters.append(FilterCriteria(
                            column=f.column,
                            operator=f.operator,
                            min_val=threshold,
                            max_val=f.max_val,
                        ))
                    else:
                        modified_filters.append(FilterCriteria(
                            column=f.column,
                            operator=f.operator,
                            min_val=f.min_val,
                            max_val=threshold,
                        ))
                else:
                    modified_filters.append(f)

            # Apply filters
            filtered_df = filter_engine.apply_filters(self._baseline_df, modified_filters)
            num_trades = len(filtered_df)

            # Calculate metrics
            if num_trades == 0:
                rows.append(ThresholdRow(
                    threshold=threshold,
                    is_current=(i == 5),
                    num_trades=0,
                    ev_pct=None,
                    win_pct=None,
                    median_winner_pct=None,
                    profit_ratio=None,
                    edge_pct=None,
                    eg_pct=None,
                    kelly_pct=None,
                    max_loss_pct=None,
                ))
            else:
                gain_col = self._column_mapping.gain_pct
                mae_col = self._column_mapping.mae_pct

                metrics, _, _ = calculator.calculate(
                    df=filtered_df,
                    gain_col=gain_col,
                    derived=True,
                    adjustment_params=self._adjustment_params,
                    mae_col=mae_col,
                )

                # Calculate kelly from edge and profit_ratio
                kelly_pct = None
                if metrics.edge is not None and metrics.rr_ratio is not None and metrics.rr_ratio > 0:
                    kelly_pct = metrics.edge / metrics.rr_ratio

                rows.append(ThresholdRow(
                    threshold=threshold,
                    is_current=(i == 5),
                    num_trades=num_trades,
                    ev_pct=metrics.ev,
                    win_pct=metrics.win_rate,
                    median_winner_pct=metrics.median_winner,
                    profit_ratio=metrics.rr_ratio,
                    edge_pct=metrics.edge,
                    eg_pct=metrics.eg_full_kelly,
                    kelly_pct=kelly_pct,
                    max_loss_pct=metrics.max_loss_pct,
                ))

            if progress_callback:
                progress_callback(int((i + 1) / 11 * 100))

        return ThresholdAnalysisResult(
            filter_column=target_filter.column,
            varied_bound=vary_bound,
            step_size=step_size,
            rows=rows,
            current_index=current_index,
        )
```

**Step 2: Add required import at top of file**

```python
from typing import TYPE_CHECKING, Callable, Literal

if TYPE_CHECKING:
    from src.core.models import AdjustmentParams, ColumnMapping, FilterCriteria
```

**Step 3: Commit**

```bash
git add src/core/parameter_sensitivity.py
git commit -m "feat(threshold-analysis): add ThresholdAnalysisEngine for calculating metrics at varied thresholds"
```

---

## Task 3: Create ThresholdAnalysisWorker

**Files:**
- Modify: `src/core/parameter_sensitivity.py`

**Step 1: Write the worker class**

Add after ThresholdAnalysisEngine:

```python
class ThresholdAnalysisWorker(QThread):
    """Background worker for threshold analysis."""

    progress = pyqtSignal(int)  # 0-100
    completed = pyqtSignal(object)  # ThresholdAnalysisResult
    error = pyqtSignal(str)

    def __init__(
        self,
        baseline_df: pd.DataFrame,
        column_mapping: "ColumnMapping",
        active_filters: list["FilterCriteria"],
        adjustment_params: "AdjustmentParams",
        filter_index: int,
        vary_bound: Literal["min", "max"],
        step_size: float,
    ) -> None:
        """Initialize the worker.

        Args:
            baseline_df: Data BEFORE user filters.
            column_mapping: Column mapping configuration.
            active_filters: Current active filters.
            adjustment_params: Stop loss and efficiency parameters.
            filter_index: Index of filter to vary.
            vary_bound: Which bound to vary.
            step_size: Step size for threshold variation.
        """
        super().__init__()
        self._baseline_df = baseline_df
        self._column_mapping = column_mapping
        self._active_filters = active_filters
        self._adjustment_params = adjustment_params
        self._filter_index = filter_index
        self._vary_bound = vary_bound
        self._step_size = step_size
        self._engine: ThresholdAnalysisEngine | None = None

    def run(self) -> None:
        """Execute the analysis in background thread."""
        try:
            self._engine = ThresholdAnalysisEngine(
                self._baseline_df,
                self._column_mapping,
                self._active_filters,
                self._adjustment_params,
            )
            result = self._engine.analyze(
                self._filter_index,
                self._vary_bound,
                self._step_size,
                progress_callback=self.progress.emit,
            )
            self.completed.emit(result)
        except Exception as e:
            logger.exception("Threshold analysis failed")
            self.error.emit(str(e))

    def cancel(self) -> None:
        """Cancel the running analysis."""
        if self._engine:
            self._engine.cancel()
```

**Step 2: Commit**

```bash
git add src/core/parameter_sensitivity.py
git commit -m "feat(threshold-analysis): add ThresholdAnalysisWorker for background execution"
```

---

## Task 4: Write Unit Tests for ThresholdAnalysisEngine

**Files:**
- Create: `tests/unit/test_threshold_analysis.py`

**Step 1: Write the test file**

```python
"""Tests for threshold analysis engine."""

import pandas as pd
import pytest

from src.core.models import AdjustmentParams, ColumnMapping, FilterCriteria
from src.core.parameter_sensitivity import (
    ThresholdAnalysisEngine,
    ThresholdAnalysisResult,
    ThresholdRow,
)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Create sample trade data."""
    return pd.DataFrame({
        "price": [5, 10, 15, 20, 25, 30, 35, 40, 45, 50] * 10,
        "gain_pct": [0.05, -0.02, 0.08, -0.03, 0.10, 0.02, -0.05, 0.15, -0.01, 0.07] * 10,
        "mae_pct": [2, 5, 3, 8, 1, 4, 10, 2, 6, 3] * 10,
    })


@pytest.fixture
def column_mapping() -> ColumnMapping:
    """Create column mapping."""
    return ColumnMapping(
        gain_pct="gain_pct",
        mae_pct="mae_pct",
    )


@pytest.fixture
def adjustment_params() -> AdjustmentParams:
    """Create adjustment params."""
    return AdjustmentParams(stop_loss=8.0, efficiency=5.0)


class TestThresholdAnalysisEngine:
    """Tests for ThresholdAnalysisEngine."""

    def test_analyze_returns_11_rows(
        self, sample_df, column_mapping, adjustment_params
    ):
        """Analysis should return exactly 11 rows."""
        filters = [FilterCriteria(column="price", operator="between", min_val=20, max_val=None)]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )
        result = engine.analyze(filter_index=0, vary_bound="min", step_size=5)

        assert len(result.rows) == 11
        assert result.current_index == 5

    def test_current_row_marked_correctly(
        self, sample_df, column_mapping, adjustment_params
    ):
        """The middle row should be marked as current."""
        filters = [FilterCriteria(column="price", operator="between", min_val=20, max_val=None)]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )
        result = engine.analyze(filter_index=0, vary_bound="min", step_size=5)

        current_row = result.rows[result.current_index]
        assert current_row.is_current is True
        assert current_row.threshold == 20  # Original filter value

        # Other rows should not be marked as current
        for i, row in enumerate(result.rows):
            if i != result.current_index:
                assert row.is_current is False

    def test_thresholds_increase_with_step_size(
        self, sample_df, column_mapping, adjustment_params
    ):
        """Thresholds should be evenly spaced by step_size."""
        filters = [FilterCriteria(column="price", operator="between", min_val=20, max_val=None)]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )
        result = engine.analyze(filter_index=0, vary_bound="min", step_size=5)

        expected_thresholds = [-5, 0, 5, 10, 15, 20, 25, 30, 35, 40, 45]
        actual_thresholds = [row.threshold for row in result.rows]
        assert actual_thresholds == expected_thresholds

    def test_stricter_filter_reduces_trade_count(
        self, sample_df, column_mapping, adjustment_params
    ):
        """Higher min threshold should result in fewer trades."""
        filters = [FilterCriteria(column="price", operator="between", min_val=25, max_val=None)]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )
        result = engine.analyze(filter_index=0, vary_bound="min", step_size=5)

        # Trade counts should generally decrease as threshold increases
        trade_counts = [row.num_trades for row in result.rows]
        # First few rows (lower thresholds) should have more trades
        assert trade_counts[0] >= trade_counts[-1]

    def test_empty_result_when_no_trades_pass(
        self, sample_df, column_mapping, adjustment_params
    ):
        """Rows with no trades should have None metrics."""
        # Filter that will exclude all data at high thresholds
        filters = [FilterCriteria(column="price", operator="between", min_val=45, max_val=None)]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )
        result = engine.analyze(filter_index=0, vary_bound="min", step_size=10)

        # Last row (threshold=95) should have no trades
        last_row = result.rows[-1]
        assert last_row.num_trades == 0
        assert last_row.ev_pct is None
        assert last_row.win_pct is None

    def test_vary_max_bound(
        self, sample_df, column_mapping, adjustment_params
    ):
        """Should correctly vary max bound instead of min."""
        filters = [FilterCriteria(column="price", operator="between", min_val=None, max_val=30)]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )
        result = engine.analyze(filter_index=0, vary_bound="max", step_size=5)

        assert result.varied_bound == "max"
        current_row = result.rows[result.current_index]
        assert current_row.threshold == 30

    def test_cancel_stops_analysis(
        self, sample_df, column_mapping, adjustment_params
    ):
        """Cancelling should stop processing early."""
        filters = [FilterCriteria(column="price", operator="between", min_val=20, max_val=None)]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )
        engine.cancel()
        result = engine.analyze(filter_index=0, vary_bound="min", step_size=5)

        # Should have fewer than 11 rows due to cancellation
        assert len(result.rows) < 11
```

**Step 2: Run tests to verify they fail (no implementation yet would fail, but we have impl)**

```bash
cd .worktrees/filter-threshold-analysis
python -m pytest tests/unit/test_threshold_analysis.py -v
```

**Step 3: Commit**

```bash
git add tests/unit/test_threshold_analysis.py
git commit -m "test(threshold-analysis): add unit tests for ThresholdAnalysisEngine"
```

---

## Task 5: Rewrite Parameter Sensitivity Tab UI - Sidebar

**Files:**
- Modify: `src/tabs/parameter_sensitivity.py`

**Step 1: Replace imports and class definition**

Replace the entire file content with new implementation:

```python
"""Filter Threshold Analysis tab for what-if analysis of filter values."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QButtonGroup,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QAbstractItemView,
)
from PyQt6.QtGui import QColor, QFont

from src.core.parameter_sensitivity import (
    ThresholdAnalysisResult,
    ThresholdAnalysisWorker,
    ThresholdRow,
)
from src.ui.components.no_scroll_widgets import NoScrollComboBox, NoScrollDoubleSpinBox

if TYPE_CHECKING:
    from src.core.app_state import AppState
    from src.core.models import FilterCriteria

logger = logging.getLogger(__name__)


# Color constants for the dark theme
COLORS = {
    "bg_primary": "#0d0d0f",
    "bg_secondary": "#131316",
    "bg_tertiary": "#18181b",
    "bg_elevated": "#222228",
    "row_current_bg": "#1a1814",
    "row_current_border": "#3d3425",
    "row_current_accent": "#c9a227",
    "delta_positive": "#22c55e",
    "delta_negative": "#ef4444",
    "text_primary": "#e4e4e7",
    "text_secondary": "#71717a",
    "text_muted": "#52525b",
    "border_subtle": "#27272a",
}


class ParameterSensitivityTab(QWidget):
    """Tab for filter threshold analysis.

    Allows users to see how trading metrics change when varying
    a single filter threshold up or down.
    """

    def __init__(self, app_state: "AppState") -> None:
        """Initialize the tab.

        Args:
            app_state: Application state for accessing data and filters.
        """
        super().__init__()
        self._app_state = app_state
        self._worker: ThresholdAnalysisWorker | None = None
        self._result: ThresholdAnalysisResult | None = None
        self._current_filter_index: int = -1

        self._setup_ui()
        self._connect_signals()
        self._populate_filter_dropdown()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create splitter for sidebar and main area
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Sidebar
        sidebar = self._create_sidebar()
        splitter.addWidget(sidebar)

        # Main table area
        main_area = self._create_main_area()
        splitter.addWidget(main_area)

        # Set initial splitter sizes (sidebar: 280px, main: stretch)
        splitter.setSizes([280, 800])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

    def _create_sidebar(self) -> QWidget:
        """Create the sidebar with controls."""
        sidebar = QFrame()
        sidebar.setObjectName("threshold-sidebar")
        sidebar.setStyleSheet(f"""
            QFrame#threshold-sidebar {{
                background-color: {COLORS['bg_secondary']};
                border-right: 1px solid {COLORS['border_subtle']};
            }}
        """)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(20)

        # Filter selector section
        filter_section = QVBoxLayout()
        filter_section.setSpacing(8)

        filter_label = QLabel("FILTER")
        filter_label.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1px;
            color: {COLORS['text_secondary']};
        """)
        filter_section.addWidget(filter_label)

        self._filter_combo = NoScrollComboBox()
        self._filter_combo.setPlaceholderText("Select a filter...")
        self._filter_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border_subtle']};
                border-radius: 6px;
                padding: 10px 12px;
                color: {COLORS['text_primary']};
                font-family: "Azeret Mono";
                font-size: 13px;
            }}
            QComboBox:hover {{
                border-color: {COLORS['bg_elevated']};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_tertiary']};
                color: {COLORS['text_primary']};
                selection-background-color: {COLORS['bg_elevated']};
            }}
        """)
        filter_section.addWidget(self._filter_combo)
        layout.addLayout(filter_section)

        # Bound toggle section
        bound_section = QVBoxLayout()
        bound_section.setSpacing(8)

        bound_label = QLabel("VARY BOUND")
        bound_label.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1px;
            color: {COLORS['text_secondary']};
        """)
        bound_section.addWidget(bound_label)

        self._bound_container = QFrame()
        self._bound_container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_tertiary']};
                border-radius: 6px;
                padding: 3px;
            }}
        """)
        bound_layout = QHBoxLayout(self._bound_container)
        bound_layout.setContentsMargins(3, 3, 3, 3)
        bound_layout.setSpacing(2)

        self._bound_group = QButtonGroup(self)
        self._min_radio = QRadioButton("Min")
        self._max_radio = QRadioButton("Max")
        self._min_radio.setChecked(True)

        for radio in [self._min_radio, self._max_radio]:
            radio.setStyleSheet(f"""
                QRadioButton {{
                    padding: 8px 16px;
                    border-radius: 4px;
                    color: {COLORS['text_secondary']};
                    font-size: 12px;
                    font-weight: 500;
                }}
                QRadioButton:checked {{
                    background-color: {COLORS['bg_elevated']};
                    color: {COLORS['text_primary']};
                }}
                QRadioButton::indicator {{
                    width: 0;
                    height: 0;
                }}
            """)
            self._bound_group.addButton(radio)
            bound_layout.addWidget(radio)

        bound_section.addWidget(self._bound_container)
        self._bound_container.setVisible(False)  # Hidden until dual-bound filter selected
        layout.addLayout(bound_section)

        # Step size section
        step_section = QVBoxLayout()
        step_section.setSpacing(8)

        step_label = QLabel("STEP SIZE")
        step_label.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1px;
            color: {COLORS['text_secondary']};
        """)
        step_section.addWidget(step_label)

        self._step_spin = NoScrollDoubleSpinBox()
        self._step_spin.setRange(0.01, 10000)
        self._step_spin.setValue(1.0)
        self._step_spin.setDecimals(2)
        self._step_spin.setStyleSheet(f"""
            QDoubleSpinBox {{
                background-color: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border_subtle']};
                border-radius: 6px;
                padding: 10px 12px;
                color: {COLORS['text_primary']};
                font-family: "Azeret Mono";
                font-size: 13px;
            }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                background-color: {COLORS['bg_elevated']};
                border: none;
                width: 24px;
            }}
        """)
        step_section.addWidget(self._step_spin)
        layout.addLayout(step_section)

        # Current value display
        current_section = QVBoxLayout()
        current_section.setSpacing(8)

        current_label = QLabel("CURRENT THRESHOLD")
        current_label.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1px;
            color: {COLORS['text_secondary']};
        """)
        current_section.addWidget(current_label)

        self._current_frame = QFrame()
        self._current_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['row_current_bg']};
                border: 1px solid {COLORS['row_current_border']};
                border-radius: 6px;
                padding: 12px;
            }}
        """)
        current_inner = QHBoxLayout(self._current_frame)
        current_inner.setContentsMargins(12, 8, 12, 8)

        self._current_label = QLabel("—")
        self._current_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        current_inner.addWidget(self._current_label)

        current_inner.addStretch()

        self._current_value = QLabel("—")
        self._current_value.setStyleSheet(f"""
            font-family: "Azeret Mono";
            font-size: 15px;
            font-weight: 600;
            color: {COLORS['row_current_accent']};
        """)
        current_inner.addWidget(self._current_value)

        current_section.addWidget(self._current_frame)
        layout.addLayout(current_section)

        # Run button
        self._run_btn = QPushButton("Analyze")
        self._run_btn.setEnabled(False)
        self._run_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['row_current_accent']};
                color: {COLORS['bg_primary']};
                border: none;
                border-radius: 6px;
                padding: 12px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #d4ad2f;
            }}
            QPushButton:disabled {{
                background-color: {COLORS['bg_tertiary']};
                color: {COLORS['text_muted']};
            }}
        """)
        layout.addWidget(self._run_btn)

        # Progress bar (hidden by default)
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['bg_tertiary']};
                border: none;
                border-radius: 4px;
                height: 6px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['row_current_accent']};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self._progress)

        layout.addStretch()

        # Empty state message
        self._empty_label = QLabel("Add filters in Feature Explorer\nto analyze thresholds")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            font-size: 12px;
        """)
        self._empty_label.setVisible(False)
        layout.addWidget(self._empty_label)

        return sidebar

    def _create_main_area(self) -> QWidget:
        """Create the main table area."""
        main = QFrame()
        main.setStyleSheet(f"background-color: {COLORS['bg_primary']};")

        layout = QVBoxLayout(main)
        layout.setContentsMargins(16, 16, 16, 16)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(10)
        self._table.setHorizontalHeaderLabels([
            "Threshold", "# Trades", "EV %", "Win %", "Med Win %",
            "Profit Ratio", "Edge %", "EG %", "Kelly %", "Max Loss %"
        ])

        # Style the table
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border_subtle']};
                border-radius: 8px;
                gridline-color: {COLORS['border_subtle']};
                font-family: "Azeret Mono";
                font-size: 12px;
                color: {COLORS['text_primary']};
            }}
            QTableWidget::item {{
                padding: 10px 16px;
                border-bottom: 1px solid {COLORS['border_subtle']};
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['bg_elevated']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_tertiary']};
                color: {COLORS['text_secondary']};
                font-family: "Geist";
                font-size: 10px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1px;
                padding: 12px 16px;
                border: none;
                border-bottom: 1px solid {COLORS['border_subtle']};
            }}
        """)

        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)

        # Set column widths
        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        for i in range(10):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self._table)

        return main

    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        self._filter_combo.currentIndexChanged.connect(self._on_filter_selected)
        self._min_radio.toggled.connect(self._on_bound_changed)
        self._step_spin.valueChanged.connect(self._on_step_changed)
        self._run_btn.clicked.connect(self._on_run_clicked)

        # App state signals
        self._app_state.filters_changed.connect(self._populate_filter_dropdown)
        self._app_state.data_loaded.connect(self._populate_filter_dropdown)
        self._app_state.adjustment_params_changed.connect(self._on_params_changed)

    def _populate_filter_dropdown(self) -> None:
        """Populate the filter dropdown with current filters."""
        self._filter_combo.clear()
        filters = self._app_state.filters or []

        if not filters:
            self._empty_label.setVisible(True)
            self._run_btn.setEnabled(False)
            return

        self._empty_label.setVisible(False)

        for f in filters:
            # Format: "Column > value" or "Column < value" or "Column: min - max"
            if f.min_val is not None and f.max_val is not None:
                label = f"{f.column}: {f.min_val:.2f} - {f.max_val:.2f}"
            elif f.min_val is not None:
                label = f"{f.column} > {f.min_val:.2f}"
            else:
                label = f"{f.column} < {f.max_val:.2f}"
            self._filter_combo.addItem(label)

    def _on_filter_selected(self, index: int) -> None:
        """Handle filter selection change."""
        if index < 0:
            self._run_btn.setEnabled(False)
            self._bound_container.setVisible(False)
            return

        self._current_filter_index = index
        filters = self._app_state.filters or []
        if index >= len(filters):
            return

        selected_filter = filters[index]

        # Show bound toggle only for dual-bound filters
        has_both_bounds = selected_filter.min_val is not None and selected_filter.max_val is not None
        self._bound_container.setVisible(has_both_bounds)

        # Update current value display
        if self._min_radio.isChecked() or not has_both_bounds:
            bound = "min"
            value = selected_filter.min_val
        else:
            bound = "max"
            value = selected_filter.max_val

        self._update_current_display(selected_filter.column, bound, value)
        self._auto_calculate_step_size(value)
        self._run_btn.setEnabled(True)

    def _on_bound_changed(self, checked: bool) -> None:
        """Handle bound toggle change."""
        if self._current_filter_index < 0:
            return

        filters = self._app_state.filters or []
        if self._current_filter_index >= len(filters):
            return

        selected_filter = filters[self._current_filter_index]
        bound = "min" if self._min_radio.isChecked() else "max"
        value = selected_filter.min_val if bound == "min" else selected_filter.max_val

        self._update_current_display(selected_filter.column, bound, value)
        self._auto_calculate_step_size(value)

    def _on_step_changed(self, value: float) -> None:
        """Handle step size change."""
        pass  # Just triggers re-analysis on next run

    def _on_params_changed(self) -> None:
        """Handle adjustment params change - clear results."""
        self._result = None
        self._table.setRowCount(0)

    def _update_current_display(self, column: str, bound: str, value: float | None) -> None:
        """Update the current threshold display."""
        if value is None:
            self._current_label.setText(column)
            self._current_value.setText("—")
        else:
            op = ">" if bound == "min" else "<"
            self._current_label.setText(f"{column} {op}")
            self._current_value.setText(f"{value:.2f}")

    def _auto_calculate_step_size(self, value: float | None) -> None:
        """Auto-calculate a sensible step size based on value magnitude."""
        if value is None:
            self._step_spin.setValue(1.0)
            return

        abs_val = abs(value)
        if abs_val < 1:
            step = 0.1
        elif abs_val < 10:
            step = 1
        elif abs_val < 100:
            step = 5
        elif abs_val < 1000:
            step = 50
        else:
            step = 100

        self._step_spin.setValue(step)

    def _on_run_clicked(self) -> None:
        """Run the threshold analysis."""
        if self._current_filter_index < 0:
            return

        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()

        # Get parameters
        vary_bound = "min" if self._min_radio.isChecked() else "max"
        step_size = self._step_spin.value()

        # Validate we have required data
        if self._app_state.baseline_df is None:
            logger.warning("No baseline data available")
            return
        if self._app_state.column_mapping is None:
            logger.warning("No column mapping available")
            return
        if not self._app_state.filters:
            logger.warning("No filters available")
            return

        # Get adjustment params (use defaults if not set)
        from src.core.models import AdjustmentParams
        adjustment_params = self._app_state.adjustment_params or AdjustmentParams()

        # Show progress
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._run_btn.setEnabled(False)

        # Start worker
        self._worker = ThresholdAnalysisWorker(
            baseline_df=self._app_state.baseline_df,
            column_mapping=self._app_state.column_mapping,
            active_filters=self._app_state.filters,
            adjustment_params=adjustment_params,
            filter_index=self._current_filter_index,
            vary_bound=vary_bound,
            step_size=step_size,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.completed.connect(self._on_completed)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, value: int) -> None:
        """Handle progress update."""
        self._progress.setValue(value)

    def _on_completed(self, result: ThresholdAnalysisResult) -> None:
        """Handle analysis completion."""
        self._result = result
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)
        self._display_results(result)

    def _on_error(self, message: str) -> None:
        """Handle analysis error."""
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)
        logger.error("Threshold analysis error: %s", message)

    def _display_results(self, result: ThresholdAnalysisResult) -> None:
        """Display analysis results in the table."""
        self._table.setRowCount(len(result.rows))

        # Get baseline values for delta calculation
        baseline_row = result.rows[result.current_index]

        for row_idx, row in enumerate(result.rows):
            is_current = row_idx == result.current_index

            # Set row background for current row
            row_bg = COLORS['row_current_bg'] if is_current else None

            # Column 0: Threshold
            threshold_item = self._create_cell(
                f"{row.threshold:.2f}",
                is_current=is_current,
                show_marker=is_current,
            )
            self._table.setItem(row_idx, 0, threshold_item)

            # Column 1: # Trades
            trades_delta = None if is_current else (row.num_trades - baseline_row.num_trades)
            self._table.setItem(row_idx, 1, self._create_cell(
                str(row.num_trades),
                delta=trades_delta,
                is_current=is_current,
                invert_delta=True,  # More trades = positive is good
            ))

            # Column 2: EV %
            self._table.setItem(row_idx, 2, self._create_metric_cell(
                row.ev_pct, baseline_row.ev_pct, is_current, "pct"
            ))

            # Column 3: Win %
            self._table.setItem(row_idx, 3, self._create_metric_cell(
                row.win_pct, baseline_row.win_pct, is_current, "pct"
            ))

            # Column 4: Median Winner %
            self._table.setItem(row_idx, 4, self._create_metric_cell(
                row.median_winner_pct, baseline_row.median_winner_pct, is_current, "pct"
            ))

            # Column 5: Profit Ratio
            self._table.setItem(row_idx, 5, self._create_metric_cell(
                row.profit_ratio, baseline_row.profit_ratio, is_current, "ratio"
            ))

            # Column 6: Edge %
            self._table.setItem(row_idx, 6, self._create_metric_cell(
                row.edge_pct, baseline_row.edge_pct, is_current, "pct"
            ))

            # Column 7: EG %
            self._table.setItem(row_idx, 7, self._create_metric_cell(
                row.eg_pct, baseline_row.eg_pct, is_current, "pct"
            ))

            # Column 8: Kelly %
            self._table.setItem(row_idx, 8, self._create_metric_cell(
                row.kelly_pct, baseline_row.kelly_pct, is_current, "pct"
            ))

            # Column 9: Max Loss % (lower is better)
            self._table.setItem(row_idx, 9, self._create_metric_cell(
                row.max_loss_pct, baseline_row.max_loss_pct, is_current, "pct", invert=True
            ))

    def _create_cell(
        self,
        text: str,
        delta: float | None = None,
        is_current: bool = False,
        show_marker: bool = False,
        invert_delta: bool = False,
    ) -> QTableWidgetItem:
        """Create a styled table cell."""
        display_text = text
        if show_marker:
            display_text = f"● {text}"

        if delta is not None and not is_current:
            sign = "+" if delta > 0 else ""
            display_text = f"{text}\n({sign}{delta:.0f})"
        elif is_current:
            display_text = f"{text}\n—"

        item = QTableWidgetItem(display_text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        if is_current:
            item.setBackground(QColor(COLORS['row_current_bg']))
            if show_marker:
                item.setForeground(QColor(COLORS['row_current_accent']))
        elif delta is not None:
            # Color based on delta direction
            is_good = (delta > 0) if not invert_delta else (delta < 0)
            if is_good:
                item.setForeground(QColor(COLORS['delta_positive']))
            elif delta != 0:
                item.setForeground(QColor(COLORS['delta_negative']))

        return item

    def _create_metric_cell(
        self,
        value: float | None,
        baseline: float | None,
        is_current: bool,
        fmt: str = "pct",
        invert: bool = False,
    ) -> QTableWidgetItem:
        """Create a metric cell with delta display."""
        if value is None:
            item = QTableWidgetItem("—")
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item.setForeground(QColor(COLORS['text_muted']))
            if is_current:
                item.setBackground(QColor(COLORS['row_current_bg']))
            return item

        # Format value
        if fmt == "pct":
            text = f"{value:.2f}%"
        else:  # ratio
            text = f"{value:.2f}"

        # Calculate delta
        delta = None
        if baseline is not None and not is_current:
            delta = value - baseline

        # Build display text
        if is_current:
            display_text = f"{text}\n—"
        elif delta is not None:
            sign = "+" if delta > 0 else ""
            if fmt == "pct":
                display_text = f"{text}\n({sign}{delta:.2f})"
            else:
                display_text = f"{text}\n({sign}{delta:.2f})"
        else:
            display_text = text

        item = QTableWidgetItem(display_text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        if is_current:
            item.setBackground(QColor(COLORS['row_current_bg']))
        elif delta is not None:
            is_good = (delta > 0) if not invert else (delta < 0)
            if is_good:
                item.setForeground(QColor(COLORS['delta_positive']))
            elif delta != 0:
                item.setForeground(QColor(COLORS['delta_negative']))

        return item

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()
```

**Step 2: Commit**

```bash
git add src/tabs/parameter_sensitivity.py
git commit -m "feat(threshold-analysis): rewrite Parameter Sensitivity tab with new threshold analysis UI"
```

---

## Task 6: Run All Tests and Verify

**Files:**
- None (verification only)

**Step 1: Run unit tests**

```bash
cd .worktrees/filter-threshold-analysis
python -m pytest tests/unit/test_threshold_analysis.py -v
```

Expected: All tests pass

**Step 2: Run full test suite**

```bash
python -m pytest tests/ -q --tb=short
```

Expected: All existing tests still pass + new tests pass

**Step 3: Commit any test fixes if needed**

---

## Task 7: Manual Integration Test

**Files:**
- None (manual testing)

**Step 1: Run the application**

```bash
cd .worktrees/filter-threshold-analysis
python -m src.main
```

**Step 2: Test workflow**

1. Load sample data via Data Input tab
2. Add a filter in Feature Explorer (e.g., Price > 10)
3. Navigate to Parameter Sensitivity tab
4. Verify filter appears in dropdown
5. Select the filter
6. Verify step size auto-calculates
7. Click "Analyze"
8. Verify table shows 11 rows with current row highlighted
9. Verify deltas show green/red coloring correctly

**Step 3: Document any issues found**

---

## Task 8: Final Cleanup and Merge Preparation

**Files:**
- None

**Step 1: Run linting**

```bash
ruff check src/tabs/parameter_sensitivity.py src/core/parameter_sensitivity.py
ruff format src/tabs/parameter_sensitivity.py src/core/parameter_sensitivity.py
```

**Step 2: Commit any formatting fixes**

```bash
git add -A
git commit -m "style: format threshold analysis code"
```

**Step 3: Final test run**

```bash
python -m pytest tests/ -q
```

**Step 4: Summary commit if needed**

All implementation complete. Ready for merge to main branch.
