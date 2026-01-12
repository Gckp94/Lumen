# Lumen Technical Architecture Document

**Version:** 1.0
**Date:** 2026-01-09
**Author:** Winston (Architect Agent)
**Status:** Approved for Development

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Data Models](#4-data-models)
5. [Components](#5-components)
6. [Core Workflows](#6-core-workflows)
7. [Development Workflow](#7-development-workflow)
8. [Testing Strategy](#8-testing-strategy)
9. [Coding Standards](#9-coding-standards)
10. [Error Handling & Resilience](#10-error-handling--resilience)
11. [Build & Distribution](#11-build--distribution)
12. [Operational Considerations](#12-operational-considerations)

---

## 1. Introduction

### Purpose & Scope

This document defines the technical architecture for **Lumen**, a desktop application for trading data analysis. It provides implementation-level guidance for developers and AI agents, covering system design, component specifications, data models, workflows, and coding standards.

### Document Conventions

- **Code blocks** contain implementation-ready examples
- **Tables** summarize specifications and mappings
- **Diagrams** use ASCII art for portability
- **Cross-references** link to PRD (docs/prd.md) and Front-End Spec (docs/front-end-spec.md)

### Relationship to Other Documents

| Document | Purpose | Authority |
|----------|---------|-----------|
| PRD (docs/prd.md) | Requirements, user stories, acceptance criteria | What to build |
| Front-End Spec (docs/front-end-spec.md) | UX design, visual specifications, animations | How it looks |
| Architecture (this document) | Technical design, implementation patterns | How to build it |

**Note:** Where PRD and Front-End Spec differ (e.g., directory structure, fonts), this architecture document is authoritative for implementation.

### Revision History

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-01-09 | 1.0 | Initial architecture | Winston (Architect) |

---

## 2. High-Level Architecture

### System Overview

Lumen is a **monolithic desktop application** built with Python and PyQt6. All processing occurs locally on the user's machine with no network dependencies.

```
┌─────────────────────────────────────────────────────────────┐
│                    Lumen Application                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    UI Layer                          │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │    │
│  │  │Data Input│ │ Feature  │ │PnL Stats │ │ Monte  │  │    │
│  │  │   Tab    │ │ Explorer │ │   Tab    │ │ Carlo  │  │    │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────────┘  │    │
│  └───────┼────────────┼────────────┼───────────────────┘    │
│          │            │            │                         │
│          ▼            ▼            ▼                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                  AppState (QObject)                  │    │
│  │         Centralized State + Signal Emission          │    │
│  └─────────────────────────────────────────────────────┘    │
│          │            │            │                         │
│          ▼            ▼            ▼                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   Core Layer                         │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │    │
│  │  │  File    │ │  Filter  │ │ Metrics  │ │ Equity │  │    │
│  │  │ Loader   │ │  Engine  │ │Calculator│ │  Calc  │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
│          │                                                   │
│          ▼                                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   I/O Layer                          │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐             │    │
│  │  │  Cache   │ │  Export  │ │  Config  │             │    │
│  │  │ Manager  │ │ Manager  │ │ Manager  │             │    │
│  │  └──────────┘ └──────────┘ └──────────┘             │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Repository Structure

```
Lumen/
├── src/
│   ├── __init__.py
│   ├── __version__.py          # Version string
│   ├── main.py                 # Entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── app_state.py        # Centralized state (QObject)
│   │   ├── models.py           # Data models (dataclasses)
│   │   ├── constants.py        # Application constants
│   │   ├── exceptions.py       # Custom exceptions
│   │   ├── file_loader.py      # Excel/CSV/Parquet loading
│   │   ├── column_mapper.py    # Auto-detection + manual mapping
│   │   ├── first_trigger.py    # First trigger algorithm
│   │   ├── filter_engine.py    # Bounds filtering logic
│   │   ├── metrics.py          # 25 trading metrics
│   │   ├── equity.py           # Equity curve calculations
│   │   ├── cache_manager.py    # Parquet caching
│   │   └── export_manager.py   # CSV/Parquet/PNG export
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── theme.py            # QSS stylesheet, font loading
│   │   ├── constants.py        # Colors, fonts, spacing, animation
│   │   ├── main_window.py      # QMainWindow + tab container
│   │   └── components/
│   │       ├── __init__.py
│   │       ├── metric_card.py
│   │       ├── comparison_ribbon.py
│   │       ├── filter_chip.py
│   │       ├── toggle_switch.py
│   │       ├── data_grid.py
│   │       ├── chart_canvas.py
│   │       ├── toast.py
│   │       └── empty_state.py
│   └── tabs/
│       ├── __init__.py
│       ├── data_input.py       # Tab 1: File loading, column config
│       ├── feature_explorer.py # Tab 2: Filtering, charting
│       ├── pnl_stats.py        # Tab 3: Metrics, comparison, charts
│       └── monte_carlo.py      # Tab 4: Placeholder
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Shared fixtures
│   ├── unit/
│   │   ├── test_first_trigger.py
│   │   ├── test_filter_engine.py
│   │   ├── test_metrics.py
│   │   ├── test_equity.py
│   │   ├── test_cache_manager.py
│   │   └── test_export_manager.py
│   ├── widget/
│   │   ├── test_metric_card.py
│   │   ├── test_filter_chip.py
│   │   ├── test_comparison_ribbon.py
│   │   └── test_data_grid.py
│   └── integration/
│       ├── test_file_load_workflow.py
│       ├── test_filter_workflow.py
│       ├── test_session.py
│       └── test_performance.py
├── assets/
│   └── fonts/
│       ├── AzeretMono-Regular.ttf
│       ├── AzeretMono-Bold.ttf
│       ├── AzeretMono-Medium.ttf
│       ├── Geist-Regular.otf
│       ├── Geist-Bold.otf
│       ├── Geist-Medium.otf
│       └── Geist-Light.otf
├── docs/
│   ├── prd.md
│   ├── front-end-spec.md
│   └── architecture.md         # This document
├── .lumen_cache/               # Git-ignored cache directory
├── pyproject.toml
├── uv.lock
├── Makefile
├── lumen.spec                  # PyInstaller config
├── .pre-commit-config.yaml
└── .gitignore
```

### AppState Critical Path

AppState is the single source of truth for application data. All components communicate through its signals.

```
┌─────────────────────────────────────────────────────────────┐
│                        AppState                              │
├─────────────────────────────────────────────────────────────┤
│ Properties:                                                  │
│   raw_df: pd.DataFrame | None                               │
│   baseline_df: pd.DataFrame | None                          │
│   filtered_df: pd.DataFrame | None                          │
│   column_mapping: ColumnMapping | None                      │
│   filters: list[FilterCriteria]                             │
│   first_trigger_enabled: bool                               │
│   baseline_metrics: TradingMetrics | None                   │
│   filtered_metrics: TradingMetrics | None                   │
├─────────────────────────────────────────────────────────────┤
│ Signals:                                                     │
│   data_loaded(pd.DataFrame)                                 │
│   column_mapping_changed(ColumnMapping)                     │
│   baseline_calculated(TradingMetrics)                       │
│   filters_changed(list[FilterCriteria])                     │
│   filtered_data_updated(pd.DataFrame)                       │
│   metrics_updated(TradingMetrics, TradingMetrics)           │
│   first_trigger_toggled(bool)                               │
│   request_tab_change(int)                                   │
│   state_corrupted(str)                                      │
│   state_recovered()                                         │
└─────────────────────────────────────────────────────────────┘
```

### Signal Flow

```
User loads file
       │
       ▼
┌─────────────┐    data_loaded    ┌─────────────┐
│ DataInputTab│ ───────────────▶  │  AppState   │
└─────────────┘                   └──────┬──────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
           baseline_calculated   column_mapping_changed  filters_changed
                    │                    │                    │
                    ▼                    ▼                    ▼
            ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
            │  PnLStats   │      │   Feature   │      │   Feature   │
            │    Tab      │      │  Explorer   │      │  Explorer   │
            └─────────────┘      └─────────────┘      └─────────────┘
```

---

## 3. Tech Stack

### Technology Table

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| **Runtime** | Python | 3.11+ | Core language |
| **UI Framework** | PyQt6 | 6.6+ | Desktop UI |
| **Charting** | PyQtGraph | 0.13+ | GPU-accelerated charts, 83k+ points |
| **Data Processing** | Pandas | 2.1+ | DataFrame operations |
| **File I/O** | PyArrow | 14.0+ | Parquet read/write |
| **Excel Reading** | openpyxl | 3.1+ | .xlsx file support |
| **Package Manager** | uv | Latest | Fast dependency management |
| **Formatter** | Black | 24.4+ | Code formatting |
| **Linter** | Ruff | 0.4+ | Fast linting |
| **Type Checker** | mypy | 1.10+ | Static type analysis |
| **Testing** | pytest | 8.0+ | Test framework |
| **Qt Testing** | pytest-qt | 4.3+ | Widget testing |
| **Build** | PyInstaller | 6.0+ | Executable packaging |

### Rationale for Key Choices

| Choice | Rationale |
|--------|-----------|
| PyQt6 over Tkinter | Professional widgets, native look, better documentation |
| PyQtGraph over Matplotlib | GPU acceleration, handles 83k+ points at 60fps |
| Pandas over Polars | More mature, better documentation, sufficient for single-user |
| Parquet over SQLite | 10-20x faster for analytical workloads, columnar storage |
| uv over pip | 10-100x faster installs, reliable lockfiles |

---

## 4. Data Models

### ColumnMapping

```python
# src/core/models.py
from dataclasses import dataclass, field
from typing import Literal

@dataclass
class ColumnMapping:
    """Mapping of required columns to DataFrame column names."""

    ticker: str
    date: str
    time: str
    gain_pct: str
    win_loss: str | None = None  # None = derive from gain_pct
    win_loss_derived: bool = False
    breakeven_is_win: bool = False  # When deriving, is 0% gain a win?

    def validate(self, df_columns: list[str]) -> list[str]:
        """Validate mapping against DataFrame columns. Returns list of errors."""
        errors = []
        required = [self.ticker, self.date, self.time, self.gain_pct]
        for col in required:
            if col not in df_columns:
                errors.append(f"Column '{col}' not found in data")
        if self.win_loss and self.win_loss not in df_columns:
            errors.append(f"Win/Loss column '{self.win_loss}' not found")
        return errors

    @classmethod
    def auto_detect(cls, df_columns: list[str]) -> "ColumnMapping | None":
        """Attempt to auto-detect column mapping."""
        # Implementation in column_mapper.py
        ...
```

### FilterCriteria

```python
@dataclass
class FilterCriteria:
    """Single filter criterion for bounds-based filtering."""

    column: str
    operator: Literal["between", "not_between"]
    min_val: float
    max_val: float

    def validate(self) -> str | None:
        """Validate filter. Returns error message or None if valid."""
        if self.min_val > self.max_val:
            return "Min value must be less than max value"
        return None

    def apply(self, df: pd.DataFrame) -> pd.Series:
        """Return boolean mask for this filter."""
        col = df[self.column]
        if self.operator == "between":
            return (col >= self.min_val) & (col <= self.max_val)
        else:  # not_between
            return (col < self.min_val) | (col > self.max_val)
```

### TradingMetrics

```python
@dataclass
class TradingMetrics:
    """All 25 trading metrics as defined in PRD Appendix D."""

    # Core Statistics (1-12)
    num_trades: int
    win_rate: float | None          # Percentage (0-100)
    avg_winner: float | None        # Percentage
    avg_loser: float | None         # Percentage (negative)
    rr_ratio: float | None          # Risk:Reward ratio
    ev: float | None                # Expected Value percentage
    edge: float | None              # Edge percentage
    kelly: float | None             # Kelly criterion percentage
    fractional_kelly: float | None  # User-adjusted Kelly
    expected_growth: float | None   # EG percentage
    median_winner: float | None
    median_loser: float | None

    # Streak & Loss (13-15)
    max_consecutive_wins: int | None
    max_consecutive_losses: int | None
    max_loss_pct: float | None

    # Flat Stake (16-19)
    flat_stake_pnl: float | None      # Dollar amount
    flat_stake_max_dd: float | None   # Dollar amount
    flat_stake_max_dd_pct: float | None
    flat_stake_dd_duration: int | None  # Trading days

    # Compounded Kelly (20-23)
    kelly_pnl: float | None
    kelly_max_dd: float | None
    kelly_max_dd_pct: float | None
    kelly_dd_duration: int | None

    # Distribution Data (24-25)
    winner_count: int | None
    loser_count: int | None
    winner_std: float | None
    loser_std: float | None
    winner_gains: list[float] = field(default_factory=list)  # Raw data for histogram
    loser_gains: list[float] = field(default_factory=list)

    @classmethod
    def empty(cls) -> "TradingMetrics":
        """Return metrics with all None/zero values."""
        return cls(
            num_trades=0,
            win_rate=None,
            avg_winner=None,
            avg_loser=None,
            # ... all None
        )
```

### AppState

```python
# src/core/app_state.py
from PyQt6.QtCore import QObject, Signal
from dataclasses import dataclass
from copy import deepcopy

@dataclass
class StateSnapshot:
    """Snapshot for state rollback."""
    filters: list[FilterCriteria]
    filtered_df: pd.DataFrame | None
    first_trigger_enabled: bool

class AppState(QObject):
    """Centralized application state with signal-based updates."""

    # Signals
    data_loaded = Signal(object)  # pd.DataFrame
    column_mapping_changed = Signal(object)  # ColumnMapping
    baseline_calculated = Signal(object)  # TradingMetrics
    filters_changed = Signal(list)  # list[FilterCriteria]
    filtered_data_updated = Signal(object)  # pd.DataFrame
    metrics_updated = Signal(object, object)  # baseline, filtered TradingMetrics
    first_trigger_toggled = Signal(bool)
    request_tab_change = Signal(int)
    state_corrupted = Signal(str)
    state_recovered = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.raw_df: pd.DataFrame | None = None
        self.baseline_df: pd.DataFrame | None = None
        self.filtered_df: pd.DataFrame | None = None
        self.column_mapping: ColumnMapping | None = None
        self.filters: list[FilterCriteria] = []
        self.first_trigger_enabled: bool = True
        self.baseline_metrics: TradingMetrics | None = None
        self.filtered_metrics: TradingMetrics | None = None
        self._snapshot: StateSnapshot | None = None

    @property
    def has_data(self) -> bool:
        """Check if data is loaded and configured."""
        return self.baseline_df is not None and self.column_mapping is not None
```

### WindowState

```python
@dataclass
class WindowState:
    """Persisted window state for session restoration."""

    x: int
    y: int
    width: int
    height: int
    maximized: bool
    active_tab: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "WindowState":
        return cls(**data)
```

### Constants

```python
# src/core/constants.py
class Limits:
    """Application limits."""
    MAX_FILTERS = 10
    MIN_WINDOW_WIDTH = 1280
    MIN_WINDOW_HEIGHT = 720
    MAX_RECENT_FILES = 10
    CACHE_MAX_AGE_DAYS = 30
```

---

## 5. Components

### UI Components

#### MetricCard

```python
# src/ui/components/metric_card.py
class MetricCard(QFrame):
    """Display a single metric value with optional delta."""

    # Variants
    HERO = "hero"        # 56px value, for Comparison Ribbon
    STANDARD = "standard"  # 24px value, for metrics grid
    COMPACT = "compact"    # 16px value, for dense displays

    # Signals
    clicked = Signal()

    def __init__(
        self,
        label: str,
        variant: str = STANDARD,
        parent: QWidget | None = None,
    ) -> None:
        ...

    def update_value(
        self,
        value: float | int | None,
        delta: float | None = None,
        baseline: float | None = None,
        format_spec: str = ".2f",
    ) -> None:
        """Update displayed value with optional delta indicator."""
        ...
```

#### ComparisonRibbon

```python
# src/ui/components/comparison_ribbon.py
class ComparisonRibbon(QFrame):
    """Signature element: 4 key metrics with large numbers and deltas."""

    METRICS = ["trades", "win_rate", "ev", "kelly"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._apply_style()

    def update(
        self,
        baseline: TradingMetrics,
        filtered: TradingMetrics,
    ) -> None:
        """Update all 4 metric cards with comparison data."""
        ...

    def clear(self) -> None:
        """Show empty state (no filters applied)."""
        ...
```

#### FilterChip

```python
# src/ui/components/filter_chip.py
class FilterChip(QFrame):
    """Display active filter with remove action."""

    removed = Signal(FilterCriteria)

    def __init__(
        self,
        criteria: FilterCriteria,
        parent: QWidget | None = None,
    ) -> None:
        ...
```

#### ToggleSwitch

```python
# src/ui/components/toggle_switch.py
class ToggleSwitch(QWidget):
    """Binary toggle with animated transition."""

    toggled = Signal(bool)

    def __init__(
        self,
        label: str = "",
        initial: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        ...
```

#### DataGrid

```python
# src/ui/components/data_grid.py
class MetricsGrid(QWidget):
    """25-metric comparison grid with collapsible sections."""

    SECTIONS = [
        ("core_statistics", "Core Statistics", range(1, 13)),
        ("streak_loss", "Streak & Loss", range(13, 16)),
        ("flat_stake", "Flat Stake", range(16, 20)),
        ("kelly", "Compounded Kelly", range(20, 24)),
        ("distribution", "Distribution", range(24, 26)),
    ]

    def update(
        self,
        baseline: TradingMetrics,
        filtered: TradingMetrics,
    ) -> None:
        """Update grid with baseline vs filtered comparison."""
        ...

    def toggle_section(self, section_id: str) -> None:
        """Collapse/expand a section."""
        ...
```

#### ChartCanvas

```python
# src/ui/components/chart_canvas.py
class ChartCanvas(QWidget):
    """PyQtGraph chart wrapper with error handling."""

    point_clicked = Signal(int, float, float)  # index, x, y
    render_failed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_pyqtgraph()

    def update_data(
        self,
        df: pd.DataFrame,
        column: str,
        color: str = Colors.SIGNAL_CYAN,
    ) -> None:
        """Update scatter plot with column data."""
        ...

    def add_baseline_series(
        self,
        df: pd.DataFrame,
        column: str,
    ) -> None:
        """Add baseline data as secondary series."""
        ...
```

#### Toast

```python
# src/ui/components/toast.py
class Toast(QFrame):
    """Transient notification for feedback messages."""

    VARIANTS = {
        "success": (Colors.SIGNAL_CYAN, "✓"),
        "error": (Colors.SIGNAL_CORAL, "✗"),
        "warning": (Colors.SIGNAL_AMBER, "⚠"),
        "info": (Colors.SIGNAL_BLUE, "ℹ"),
    }

    def show(self, parent: QWidget, duration: int = 3000) -> None:
        """Show toast, auto-dismiss after duration (0 = persistent)."""
        ...
```

#### EmptyState

```python
# src/ui/components/empty_state.py
class EmptyState(QFrame):
    """Consistent empty state display."""

    def set_message(
        self,
        icon: str,
        title: str,
        description: str,
        action_text: str | None = None,
        action_callback: Callable[[], None] | None = None,
    ) -> None:
        """Configure empty state content."""
        ...
```

### Core Components

#### FileLoader

```python
# src/core/file_loader.py
class FileLoader:
    """Load Excel, CSV, and Parquet files."""

    SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".parquet"}

    def load(self, path: Path, sheet: str | None = None) -> pd.DataFrame:
        """Load file into DataFrame."""
        ...

    def get_sheet_names(self, path: Path) -> list[str]:
        """Get sheet names from Excel file."""
        ...
```

#### ColumnMapper

```python
# src/core/column_mapper.py
class ColumnMapper:
    """Auto-detect and manage column mappings."""

    PATTERNS = {
        "ticker": ["ticker", "symbol", "stock", "security"],
        "date": ["date", "trade_date", "entry_date"],
        "time": ["time", "trade_time", "entry_time"],
        "gain_pct": ["gain", "return", "pnl", "profit", "%"],
        "win_loss": ["win", "loss", "result", "outcome"],
    }

    def auto_detect(self, columns: list[str]) -> ColumnMapping | None:
        """Attempt auto-detection of column mapping."""
        ...

    def save_mapping(self, file_path: Path, mapping: ColumnMapping) -> None:
        """Persist mapping to cache."""
        ...

    def load_mapping(self, file_path: Path) -> ColumnMapping | None:
        """Load persisted mapping if exists."""
        ...
```

#### FirstTriggerEngine

```python
# src/core/first_trigger.py
class FirstTriggerEngine:
    """First trigger algorithm implementation."""

    def apply(
        self,
        df: pd.DataFrame,
        ticker_col: str,
        date_col: str,
        time_col: str,
    ) -> pd.DataFrame:
        """Identify first signal per ticker-date combination."""
        ...

    def apply_filtered(
        self,
        df: pd.DataFrame,
        ticker_col: str,
        date_col: str,
        time_col: str,
    ) -> pd.DataFrame:
        """Apply first trigger to already-filtered data."""
        ...
```

#### FilterEngine

```python
# src/core/filter_engine.py
class FilterEngine:
    """Apply bounds-based filters to DataFrames."""

    def apply_filters(
        self,
        df: pd.DataFrame,
        filters: list[FilterCriteria],
    ) -> pd.DataFrame:
        """Apply all filters with AND logic."""
        ...

    def apply_date_range(
        self,
        df: pd.DataFrame,
        date_col: str,
        start: str | None = None,
        end: str | None = None,
        all_dates: bool = False,
    ) -> pd.DataFrame:
        """Filter by date range."""
        ...
```

#### MetricsCalculator

```python
# src/core/metrics.py
class MetricsCalculator:
    """Calculate all 25 trading metrics."""

    def calculate(
        self,
        df: pd.DataFrame,
        gain_col: str,
        win_loss_col: str | None = None,
        user_inputs: dict | None = None,
    ) -> TradingMetrics:
        """Calculate full metrics suite."""
        ...
```

#### EquityCalculator

```python
# src/core/equity.py
class EquityCalculator:
    """Calculate equity curves for flat stake and Kelly."""

    def calculate_flat_stake(
        self,
        df: pd.DataFrame,
        gain_col: str,
        stake: float,
    ) -> pd.DataFrame:
        """Calculate flat stake equity curve."""
        ...

    def calculate_kelly(
        self,
        df: pd.DataFrame,
        gain_col: str,
        start_capital: float,
        kelly_fraction: float,
    ) -> pd.DataFrame:
        """Calculate compounded Kelly equity curve."""
        ...
```

#### ExportManager

```python
# src/core/export_manager.py
class ExportManager:
    """Export data in various formats."""

    def to_csv(
        self,
        df: pd.DataFrame,
        path: Path,
        include_metadata: bool = True,
    ) -> None:
        """Export to CSV with optional metadata header."""
        ...

    def to_parquet(
        self,
        df: pd.DataFrame,
        path: Path,
        metadata: dict | None = None,
    ) -> None:
        """Export to Parquet with metadata."""
        ...

    def metrics_to_csv(
        self,
        baseline: TradingMetrics,
        filtered: TradingMetrics,
        path: Path,
    ) -> None:
        """Export metrics comparison to CSV."""
        ...

    def chart_to_png(
        self,
        chart: ChartCanvas,
        path: Path,
        resolution: tuple[int, int] = (1920, 1080),
    ) -> None:
        """Export chart to PNG."""
        ...
```

#### CacheManager

```python
# src/core/cache_manager.py
class CacheManager:
    """Manage Parquet cache for faster loads."""

    def __init__(self, cache_dir: Path = Path(".lumen_cache")) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)

    def get_cached(self, file_path: Path, sheet: str | None = None) -> pd.DataFrame | None:
        """Load from cache if valid."""
        ...

    def save_to_cache(
        self,
        df: pd.DataFrame,
        file_path: Path,
        sheet: str | None = None,
    ) -> None:
        """Save DataFrame to cache."""
        ...

    def invalidate(self, file_path: Path) -> None:
        """Remove cache for file."""
        ...
```

---

## 6. Core Workflows

### Workflow 1: File Load → First Trigger → Baseline

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │     │DataInput │     │ AppState │     │  Core    │
│          │     │   Tab    │     │          │     │ Engines  │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │
     │ Select File    │                │                │
     │───────────────▶│                │                │
     │                │                │                │
     │                │ Check Cache    │                │
     │                │───────────────▶│                │
     │                │                │ get_cached()   │
     │                │                │───────────────▶│
     │                │◀───────────────│                │
     │                │ Cache Miss     │                │
     │                │                │                │
     │                │ Load File      │                │
     │                │───────────────▶│                │
     │                │                │ FileLoader     │
     │                │                │───────────────▶│
     │                │                │◀───────────────│
     │                │                │ raw_df         │
     │                │                │                │
     │                │ Auto-detect    │                │
     │                │ Columns        │                │
     │                │───────────────▶│                │
     │                │                │ ColumnMapper   │
     │                │                │───────────────▶│
     │                │                │◀───────────────│
     │                │◀───────────────│ mapping        │
     │                │                │                │
     │ [If mapping    │                │                │
     │  incomplete]   │                │                │
     │◀───────────────│                │                │
     │ Show Config    │                │                │
     │ Panel          │                │                │
     │───────────────▶│                │                │
     │ Complete       │                │                │
     │ Mapping        │                │                │
     │                │                │                │
     │                │ Apply First    │                │
     │                │ Trigger        │                │
     │                │───────────────▶│                │
     │                │                │ FirstTrigger   │
     │                │                │───────────────▶│
     │                │                │◀───────────────│
     │                │                │ baseline_df    │
     │                │                │                │
     │                │ Calculate      │                │
     │                │ Metrics        │                │
     │                │───────────────▶│                │
     │                │                │ Metrics        │
     │                │                │ Calculator     │
     │                │                │───────────────▶│
     │                │                │◀───────────────│
     │                │                │                │
     │                │ Emit Signals   │                │
     │                │                │                │
     │                │  data_loaded ──┼───────────────▶│
     │                │  baseline_calculated ──────────▶│
     │                │                │                │
     │ Display        │                │                │
     │ Baseline       │                │                │
     │◀───────────────│                │                │
     │                │                │                │
     ▼                ▼                ▼                ▼

Performance: < 3 seconds for 100k rows (NFR1)
```

### Workflow 2: Filter Apply → Metrics Update

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │     │ Feature  │     │ AppState │     │  Core    │
│          │     │ Explorer │     │          │     │ Engines  │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │
     │ Add Filter     │                │                │
     │───────────────▶│                │                │
     │                │                │                │
     │                │ Validate       │                │
     │                │ Criteria       │                │
     │                │───────────────▶│                │
     │                │                │ FilterEngine   │
     │                │                │ .validate()    │
     │                │◀───────────────│                │
     │                │                │                │
     │ [If invalid]   │                │                │
     │◀───────────────│                │                │
     │ Show Error     │                │                │
     │                │                │                │
     │ Click Apply    │                │                │
     │───────────────▶│                │                │
     │                │                │                │
     │                │ apply_filter() │                │
     │                │───────────────▶│                │
     │                │                │                │
     │                │                │ Take Snapshot  │
     │                │                │ (for rollback) │
     │                │                │                │
     │                │                │ FilterEngine   │
     │                │                │ .apply()       │
     │                │                │───────────────▶│
     │                │                │◀───────────────│
     │                │                │ filtered_df    │
     │                │                │                │
     │                │                │ [If FT toggle] │
     │                │                │ FirstTrigger   │
     │                │                │ .apply()       │
     │                │                │───────────────▶│
     │                │                │◀───────────────│
     │                │                │                │
     │                │                │ Calculate      │
     │                │                │ Filtered       │
     │                │                │ Metrics        │
     │                │                │───────────────▶│
     │                │                │◀───────────────│
     │                │                │                │
     │                │ Emit Signals   │                │
     │                │                │                │
     │                │  filters_changed ─────────────▶│
     │                │  filtered_data_updated ───────▶│
     │                │  metrics_updated ─────────────▶│
     │                │                │                │
     │ Update Chart   │                │                │
     │ Update Count   │                │                │
     │◀───────────────│                │                │
     │                │                │                │
     ▼                ▼                ▼                ▼

Performance: < 500ms (NFR2)
```

### Workflow 3: First-Trigger Toggle

```
User toggles switch
       │
       ▼
┌─────────────┐    first_trigger_toggled(bool)    ┌─────────────┐
│   Feature   │ ─────────────────────────────────▶│  AppState   │
│  Explorer   │                                   └──────┬──────┘
└─────────────┘                                          │
                                                         │
                              ┌───────────────────────────┤
                              │                           │
                              ▼                           ▼
                   [If enabled]                  [If disabled]
                   Apply FirstTrigger            Return raw filtered
                   to filtered_df                 │
                              │                   │
                              ▼                   ▼
                        filtered_data_updated + metrics_updated
                              │
                              ▼
                   Update chart + row count

Performance: < 200ms
```

### Workflow 4: Export

```
User clicks Export
       │
       ▼
┌─────────────┐    Show save dialog    ┌─────────────┐
│   Tab       │ ──────────────────────▶│    OS       │
└─────────────┘                        └──────┬──────┘
                                              │
                                    User selects path
                                              │
       ┌──────────────────────────────────────┘
       │
       ▼
┌─────────────┐    export()    ┌─────────────┐
│   Tab       │ ──────────────▶│ExportManager│
└─────────────┘                └──────┬──────┘
                                      │
                               [Try write]
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              ▼                       ▼                       ▼
        [Success]               [Permission]            [Disk Full]
        Show Toast              Show Error              Show Error
        (success)               Toast                   Toast
```

### Workflow 5: Window State Restore

```
Application Launch
       │
       ▼
┌─────────────┐    Load window_state.json    ┌─────────────┐
│ MainWindow  │ ────────────────────────────▶│   Cache     │
└─────────────┘                              └──────┬──────┘
                                                    │
                              ┌─────────────────────┤
                              │                     │
                              ▼                     ▼
                    [State exists]          [No state / Error]
                              │                     │
                              ▼                     ▼
                    Validate position       Use defaults
                    (on-screen check)       (centered, 1280x720)
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
        [Valid]         [Off-screen]    [Maximized]
        Restore         Reset to        Restore
        position        center          maximized
```

---

## 7. Development Workflow

### Environment Setup

```bash
# Clone repository
git clone <repo-url>
cd Lumen

# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync

# Verify installation
uv run python -c "import PyQt6; print('PyQt6 OK')"
uv run python -c "import pyqtgraph; print('PyQtGraph OK')"
```

### pyproject.toml

```toml
[project]
name = "lumen"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "PyQt6>=6.6.0",
    "pyqtgraph>=0.13.0",
    "pandas>=2.1.0",
    "pyarrow>=14.0.0",
    "openpyxl>=3.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-qt>=4.3.0",
    "pytest-cov>=4.1.0",
    "black>=24.4.0",
    "ruff>=0.4.0",
    "mypy>=1.10.0",
    "pandas-stubs",
    "PyQt6-stubs",
    "pre-commit>=3.7.0",
    "pyinstaller>=6.0.0",
]

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.isort]
profile = "black"
line_length = 100

[tool.ruff]
line-length = 100
select = ["E", "F", "W", "I", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.11"
strict = true
plugins = ["numpy.typing.mypy_plugin"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "widget: marks tests requiring Qt event loop",
]
```

### Makefile

```makefile
.PHONY: run test test-quick test-perf lint format typecheck coverage build clean

# Run application
run:
	uv run python -m src.main

# Run all tests
test:
	uv run pytest

# Quick tests (skip slow)
test-quick:
	uv run pytest -m "not slow"

# Performance tests only
test-perf:
	uv run pytest -m slow --timeout=60 -v

# Lint code
lint:
	uv run ruff check src tests

# Format code
format:
	uv run black src tests
	uv run ruff check --fix src tests

# Type check
typecheck:
	uv run mypy src

# Coverage report
coverage:
	uv run pytest --cov=src --cov-report=html --cov-report=term-missing

# Build executable
build:
	uv run pyinstaller lumen.spec --clean --noconfirm

# Clean build artifacts
clean:
	rm -rf build/ dist/ .pytest_cache/ .mypy_cache/ htmlcov/ .coverage
```

### VS Code Configuration

```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.analysis.typeCheckingMode": "strict",
    "editor.formatOnSave": true,
    "editor.rulers": [100],
    "[python]": {
        "editor.defaultFormatter": "ms-python.black-formatter",
        "editor.codeActionsOnSave": {
            "source.organizeImports": "explicit"
        }
    },
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"]
}
```

### Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        additional_dependencies: [pandas-stubs, PyQt6-stubs]
        args: [--strict]
```

### GitHub Actions CI

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v2

      - name: Set up Python
        run: uv python install 3.11

      - name: Install dependencies
        run: uv sync --all-extras

      - name: Lint
        run: uv run ruff check src tests

      - name: Type check
        run: uv run mypy src

      - name: Test
        run: uv run pytest -m "not slow" --tb=short

  build:
    runs-on: windows-latest
    needs: test
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v2

      - name: Set up Python
        run: uv python install 3.11

      - name: Install dependencies
        run: uv sync --all-extras

      - name: Build executable
        run: uv run pyinstaller lumen.spec --clean --noconfirm

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: Lumen-Windows
          path: dist/Lumen.exe
```

---

## 8. Testing Strategy

### Test Pyramid

```
                    ┌─────────┐
                   ╱           ╲
                  ╱   Manual    ╲     5%  - Visual verification
                 ╱   Testing     ╲         - Exploratory testing
                ╱─────────────────╲
               ╱                   ╲
              ╱    Integration      ╲   15%  - Tab workflows
             ╱      Tests           ╲        - File → Metrics flow
            ╱─────────────────────────╲
           ╱                           ╲
          ╱       Widget Tests          ╲  20%  - Component behavior
         ╱         (pytest-qt)           ╲       - Signal emission
        ╱─────────────────────────────────╲
       ╱                                   ╲
      ╱           Unit Tests                ╲  60%  - Core logic
     ╱            (pytest)                   ╲       - Calculations
    ╱─────────────────────────────────────────╲
```

### Fixtures (conftest.py)

```python
# tests/conftest.py
import pytest
import pandas as pd
from pathlib import Path

@pytest.fixture
def sample_trades() -> pd.DataFrame:
    """Standard 1000-row trade dataset."""
    return pd.DataFrame({
        "ticker": ["AAPL"] * 500 + ["GOOGL"] * 500,
        "date": pd.date_range("2024-01-01", periods=1000, freq="h").date,
        "time": pd.date_range("2024-01-01", periods=1000, freq="h").time,
        "gain_pct": np.random.normal(0.5, 3, 1000),
    })

@pytest.fixture
def column_mapping() -> ColumnMapping:
    """Default column mapping."""
    return ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        win_loss_derived=True,
    )

@pytest.fixture
def sample_filters() -> list[FilterCriteria]:
    """Sample filter set."""
    return [
        FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10),
    ]

@pytest.fixture(scope="session")
def large_dataset_path(tmp_path_factory) -> Path:
    """Generate 100k row dataset for performance tests."""
    path = tmp_path_factory.mktemp("data") / "large.parquet"
    df = generate_sample_trades(n_rows=100_000)
    df.to_parquet(path)
    return path
```

### Unit Tests

```python
# tests/unit/test_first_trigger.py
def test_first_trigger_basic(sample_trades, column_mapping):
    """First trigger returns one row per ticker-date."""
    engine = FirstTriggerEngine()
    result = engine.apply(
        sample_trades,
        ticker_col=column_mapping.ticker,
        date_col=column_mapping.date,
        time_col=column_mapping.time,
    )
    # Verify uniqueness
    groups = result.groupby([column_mapping.ticker, column_mapping.date]).size()
    assert (groups == 1).all()

def test_first_trigger_empty_input():
    """Empty DataFrame returns empty DataFrame."""
    engine = FirstTriggerEngine()
    empty = pd.DataFrame(columns=["ticker", "date", "time", "gain_pct"])
    result = engine.apply(empty, "ticker", "date", "time")
    assert len(result) == 0

def test_first_trigger_null_times(sample_trades):
    """Null times are sorted first within groups."""
    sample_trades.loc[0, "time"] = None
    engine = FirstTriggerEngine()
    result = engine.apply(sample_trades, "ticker", "date", "time")
    # Row with null time should be first for its group
    ...
```

```python
# tests/unit/test_filter_engine.py
def test_filter_between(sample_trades):
    """BETWEEN filter includes boundary values."""
    engine = FilterEngine()
    criteria = FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=5)
    result = engine.apply_filters(sample_trades, [criteria])
    assert (result["gain_pct"] >= 0).all()
    assert (result["gain_pct"] <= 5).all()

def test_filter_not_between(sample_trades):
    """NOT BETWEEN filter excludes range."""
    engine = FilterEngine()
    criteria = FilterCriteria(column="gain_pct", operator="not_between", min_val=0, max_val=5)
    result = engine.apply_filters(sample_trades, [criteria])
    assert ((result["gain_pct"] < 0) | (result["gain_pct"] > 5)).all()

def test_filter_invalid_range_raises():
    """Min > max raises FilterValidationError."""
    criteria = FilterCriteria(column="gain_pct", operator="between", min_val=10, max_val=5)
    assert criteria.validate() is not None

def test_date_range_filter(sample_trades):
    """Date range selection filters data by date."""
    engine = FilterEngine()
    filtered = engine.apply_date_range(
        sample_trades,
        date_col="date",
        start="2024-01-15",
        end="2024-01-20",
    )
    assert all(filtered["date"] >= pd.Timestamp("2024-01-15").date())
    assert all(filtered["date"] <= pd.Timestamp("2024-01-20").date())
```

```python
# tests/unit/test_metrics.py
def test_metrics_basic(sample_trades, column_mapping):
    """Basic metrics calculation."""
    calc = MetricsCalculator()
    metrics = calc.calculate(sample_trades, column_mapping.gain_pct)
    assert metrics.num_trades == len(sample_trades)
    assert 0 <= metrics.win_rate <= 100

def test_metrics_empty_df():
    """Empty DataFrame returns empty metrics."""
    calc = MetricsCalculator()
    empty = pd.DataFrame(columns=["gain_pct"])
    metrics = calc.calculate(empty, "gain_pct")
    assert metrics.num_trades == 0
    assert metrics.win_rate is None

def test_metrics_no_winners(sample_trades):
    """All losers handled gracefully."""
    sample_trades["gain_pct"] = -abs(sample_trades["gain_pct"])
    calc = MetricsCalculator()
    metrics = calc.calculate(sample_trades, "gain_pct")
    assert metrics.win_rate == 0
    assert metrics.avg_winner is None
```

```python
# tests/unit/test_export_manager.py
def test_export_csv(sample_trades, tmp_path):
    """Export filtered dataset to CSV."""
    exporter = ExportManager()
    path = tmp_path / "export.csv"
    exporter.to_csv(sample_trades, path)
    assert path.exists()
    reloaded = pd.read_csv(path)
    assert len(reloaded) == len(sample_trades)

def test_export_parquet_with_metadata(sample_trades, tmp_path):
    """Export to Parquet with filter metadata."""
    exporter = ExportManager()
    path = tmp_path / "export.parquet"
    exporter.to_parquet(sample_trades, path, metadata={"filters": "gain_pct: 0-5"})
    assert path.exists()
```

### Widget Tests

```python
# tests/widget/test_metric_card.py
def test_metric_card_display(qtbot):
    """MetricCard displays value correctly."""
    card = MetricCard(label="Win Rate", variant=MetricCard.STANDARD)
    qtbot.addWidget(card)
    card.update_value(67.5, format_spec=".1f")
    assert "67.5" in card._value_label.text()

def test_metric_card_delta_colors(qtbot):
    """Delta indicator uses correct colors."""
    card = MetricCard(label="EV", variant=MetricCard.STANDARD)
    qtbot.addWidget(card)
    card.update_value(3.2, delta=1.5, baseline=1.7)
    # Positive delta should use cyan
    assert Colors.SIGNAL_CYAN in card._delta_label.styleSheet()
```

```python
# tests/widget/test_comparison_ribbon.py
def test_ribbon_displays_four_metrics(qtbot):
    """Ribbon shows Trades, Win Rate, EV, Kelly."""
    ribbon = ComparisonRibbon()
    qtbot.addWidget(ribbon)
    baseline = TradingMetrics(num_trades=12847, win_rate=58.2, ev=1.87, kelly=12.1)
    filtered = TradingMetrics(num_trades=4231, win_rate=67.1, ev=3.21, kelly=15.4)
    ribbon.update(baseline, filtered)
    assert "4,231" in ribbon._trades_card._value_label.text()
    assert "67.1" in ribbon._win_rate_card._value_label.text()

def test_ribbon_empty_state(qtbot):
    """Empty state when no filters applied."""
    ribbon = ComparisonRibbon()
    qtbot.addWidget(ribbon)
    ribbon.clear()
    assert "—" in ribbon._trades_card._value_label.text()
```

### Integration Tests

```python
# tests/integration/test_file_load_workflow.py
def test_full_load_workflow(qtbot, tmp_path):
    """Complete file load → first trigger → baseline flow."""
    # Create test file
    test_file = tmp_path / "trades.csv"
    sample_df = generate_sample_trades(100)
    sample_df.to_csv(test_file, index=False)

    # Create app state
    app_state = AppState()

    # Track signal emissions
    signals = []
    app_state.data_loaded.connect(lambda df: signals.append("data_loaded"))
    app_state.baseline_calculated.connect(lambda m: signals.append("baseline_calculated"))

    # Load file
    loader = FileLoader()
    df = loader.load(test_file)

    # Auto-detect columns
    mapper = ColumnMapper()
    mapping = mapper.auto_detect(df.columns.tolist())
    assert mapping is not None

    # Set data in app state
    app_state.set_data(df, mapping)

    # Verify signals
    assert "data_loaded" in signals
    assert "baseline_calculated" in signals
    assert app_state.baseline_df is not None
    assert app_state.baseline_metrics is not None
```

```python
# tests/integration/test_performance.py
import pytest
from time import perf_counter
import tracemalloc

@pytest.mark.slow
def test_data_load_performance(large_dataset_path):
    """NFR1: Data load < 3 seconds for 100k rows."""
    start = perf_counter()
    loader = FileLoader()
    df = loader.load(large_dataset_path)
    elapsed = perf_counter() - start
    assert elapsed < 3.0, f"Load took {elapsed:.2f}s, exceeds 3s limit"
    assert len(df) >= 100_000

@pytest.mark.slow
def test_filter_response_time(large_dataset_path):
    """NFR2: Filter response < 500ms."""
    loader = FileLoader()
    df = loader.load(large_dataset_path)

    engine = FilterEngine()
    criteria = FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10)

    start = perf_counter()
    result = engine.apply_filters(df, [criteria])
    elapsed = perf_counter() - start
    assert elapsed < 0.5, f"Filter took {elapsed:.3f}s, exceeds 500ms limit"

@pytest.mark.slow
def test_memory_footprint_nfr4(large_dataset_path):
    """NFR4: Memory footprint < 500MB with 100k row dataset."""
    tracemalloc.start()

    # Simulate full application load
    app_state = AppState()
    loader = FileLoader()
    df = loader.load(large_dataset_path)

    mapping = ColumnMapping(
        ticker="ticker", date="date", time="time", gain_pct="gain_pct"
    )
    app_state.set_data(df, mapping)

    # Calculate metrics
    metrics_calc = MetricsCalculator()
    baseline_metrics = metrics_calc.calculate(app_state.baseline_df, "gain_pct")

    # Measure peak memory
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak / (1024 * 1024)
    assert peak_mb < 500, f"Memory peak {peak_mb:.1f}MB exceeds 500MB limit"
```

### Manual Testing Checklist

| Test | Steps | Expected |
|------|-------|----------|
| File Load | Load 100k row Excel file | < 3s, no errors |
| Column Detection | Load file with standard column names | All 4 required columns auto-detected |
| Filter Apply | Add 3 filters, click Apply | Chart updates < 500ms |
| First Trigger Toggle | Toggle switch ON/OFF | Row count changes, chart updates |
| Export CSV | Export filtered data | File saved, openable in Excel |
| Chart Pan/Zoom | Mouse wheel, drag | 60fps, no lag |
| Window Resize | Resize to 1920x1080 | Layout adapts, no clipping |
| Session Restore | Close and reopen | Window position/size restored |

---

## 9. Coding Standards

### Language & Formatting

```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ["py311"]

[tool.ruff]
line-length = 100
select = ["E", "F", "W", "I", "UP", "B", "SIM"]
```

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Modules | snake_case | `filter_engine.py` |
| Classes | PascalCase | `FilterEngine` |
| Functions | snake_case | `apply_first_trigger()` |
| Constants | SCREAMING_SNAKE | `MAX_FILTERS = 10` |
| Private | Leading underscore | `_calculate_delta()` |
| Qt Signals | snake_case | `metrics_updated` |
| Qt Slots | on_noun_verb | `on_filter_applied` |

### Type Hints

```python
# Required for all public APIs
def calculate_metrics(
    trades: pd.DataFrame,
    column_mapping: ColumnMapping,
) -> TradingMetrics:
    """Calculate all 25 trading metrics."""
    ...
```

### Qt Patterns

```python
# Signal/Slot naming
class AppState(QObject):
    # Signals: noun_verb (past tense)
    data_loaded = Signal(object)
    filters_applied = Signal(list)
    metrics_updated = Signal(object, object)

class MetricsPanel(QWidget):
    # Slots: on_noun_verb
    def on_metrics_updated(
        self,
        baseline: TradingMetrics,
        filtered: TradingMetrics,
    ) -> None:
        ...
```

```python
# Background I/O with QThread
class FileLoadWorker(QThread):
    progress = Signal(int)
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, path: Path, sheet: str | None = None) -> None:
        super().__init__()
        self.path = path
        self.sheet = sheet

    def run(self) -> None:
        try:
            self.progress.emit(10)
            df = self._load_file()
            self.progress.emit(100)
            self.finished.emit(df)
        except Exception as e:
            self.error.emit(str(e))
```

```python
# Debounce with QTimer
class UserInputsPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._apply_inputs)

    def _on_input_changed(self) -> None:
        self._debounce_timer.start(Animation.DEBOUNCE_INPUT)
```

### Pandas Patterns

```python
# GOOD: Explicit copy when modifying
filtered = df[mask].copy()
filtered["new_col"] = values

# GOOD: Method chaining with pipe
result = (
    df
    .pipe(apply_date_filter, start, end)
    .pipe(apply_feature_filters, filters)
    .pipe(apply_first_trigger, columns)
)

# GOOD: Explicit dtype enforcement
df = df.astype({
    "ticker": "string",
    "date": "datetime64[ns]",
    "gain_pct": "float64",
})
```

### Exception Hierarchy

```python
# src/core/exceptions.py
class LumenError(Exception):
    """Base exception for Lumen application."""

class FileLoadError(LumenError):
    """Raised when file loading fails."""

class ColumnMappingError(LumenError):
    """Raised when column mapping is invalid."""

class FilterValidationError(LumenError):
    """Raised when filter criteria invalid."""

class MetricsCalculationError(LumenError):
    """Raised when metrics calculation fails."""

class EquityCalculationError(LumenError):
    """Raised when equity curve calculation fails."""

class ExportError(LumenError):
    """Raised when export fails."""

class CacheError(LumenError):
    """Raised when cache operations fail."""

class ChartRenderError(LumenError):
    """Raised when chart rendering fails."""
```

### Theme Constants

```python
# src/ui/constants.py
class Colors:
    """Observatory Palette — semantic colors are inviolable."""
    # Backgrounds
    BG_BASE = "#0C0C12"
    BG_SURFACE = "#141420"
    BG_ELEVATED = "#1E1E2C"
    BG_BORDER = "#2A2A3A"

    # Signal Colors
    SIGNAL_CYAN = "#00FFD4"   # ALWAYS positive
    SIGNAL_CORAL = "#FF4757"  # ALWAYS negative
    SIGNAL_AMBER = "#FFAA00"  # ALWAYS attention
    SIGNAL_BLUE = "#4A9EFF"   # ALWAYS reference

    # Text
    TEXT_PRIMARY = "#F4F4F8"
    TEXT_SECONDARY = "#9898A8"
    TEXT_DISABLED = "#5C5C6C"

class Fonts:
    DATA = "Azeret Mono"
    UI = "Geist"

class FontSizes:
    KPI_HERO = 48
    KPI_LARGE = 32
    H1 = 24
    H2 = 18
    BODY = 13

class Spacing:
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32

class Animation:
    NUMBER_TICKER = 150
    DELTA_FLASH = 200
    TAB_SWITCH = 150
    DEBOUNCE_INPUT = 150
    DEBOUNCE_METRICS = 300
    LOADING_MIN_DURATION = 400
```

### Logging Guidelines

```python
import logging
logger = logging.getLogger(__name__)

# DEBUG: Internal state, loop iterations
logger.debug("Filter mask: %d rows match", mask.sum())

# INFO: User actions, workflow milestones
logger.info("Loaded %d rows from %s", len(df), path.name)

# WARNING: Recoverable issues, fallbacks
logger.warning("Cache hash mismatch, reloading from source")

# ERROR: Failures that stop operation
logger.error("Failed to load file: %s", error)
```

---

## 10. Error Handling & Resilience

### Philosophy

| Principle | Implementation |
|-----------|----------------|
| Fail gracefully | Show user-friendly message, never crash |
| Preserve data | Never lose user's loaded data on error |
| Enable recovery | Provide clear path forward after error |
| Log for debugging | Capture details for troubleshooting |

### Exception Layers

```
┌─────────────────────────────────────────────────────────────┐
│  UI Layer (Tabs, Widgets)                                   │
│  • Catch LumenError → Show toast/dialog                     │
│  • Catch Exception → Log + generic error message            │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│  Core Layer (Engines, Calculators)                          │
│  • Validate inputs → Raise specific LumenError              │
│  • Catch pandas/numpy errors → Wrap in LumenError           │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│  I/O Layer (File, Cache, Export)                            │
│  • Catch OSError → Wrap in FileLoadError/ExportError        │
│  • Catch format errors → Wrap with context                  │
└─────────────────────────────────────────────────────────────┘
```

### Error Messages

| Error Case | User Message |
|------------|--------------|
| File not found | "File not found: {filename}" |
| Permission denied | "Cannot access file. Check permissions." |
| Corrupt file | "Unable to read file. The file may be corrupted." |
| Column missing | "Required column not mapped: {column}" |
| Invalid range | "Min value must be less than max value." |
| No matches | "No rows match your filter criteria." |
| Export failed | "Cannot write to selected location." |

### Graceful Degradation

```python
class MetricsCalculator:
    def calculate(self, df: pd.DataFrame) -> TradingMetrics:
        if len(df) == 0:
            logger.warning("Empty DataFrame, returning default metrics")
            return TradingMetrics.empty()

        winners = df[df["gain_pct"] > 0]
        losers = df[df["gain_pct"] < 0]

        if len(winners) == 0:
            logger.warning("No winners in dataset")
            avg_winner = None
            rr_ratio = None
        else:
            avg_winner = winners["gain_pct"].mean()
            rr_ratio = self._calculate_rr(winners, losers)

        return TradingMetrics(
            num_trades=len(df),
            avg_winner=avg_winner,
            rr_ratio=rr_ratio,
            # ...
        )
```

### State Recovery

```python
class AppState(QObject):
    def apply_filter(self, criteria: FilterCriteria) -> None:
        if not self._validate_state():
            self.state_corrupted.emit("State invalid. Please reload data.")
            return

        self._take_snapshot()

        try:
            self._do_apply_filter(criteria)
        except Exception as e:
            logger.error("Filter failed: %s", e)
            self._rollback()
            raise

    def _take_snapshot(self) -> None:
        self._snapshot = StateSnapshot(
            filters=deepcopy(self.filters),
            filtered_df=self.filtered_df.copy() if self.filtered_df is not None else None,
            first_trigger_enabled=self.first_trigger_enabled,
        )

    def _rollback(self) -> None:
        if self._snapshot:
            self.filters = self._snapshot.filters
            self.filtered_df = self._snapshot.filtered_df
            self.state_recovered.emit()
```

### Tab Navigation Guards

```python
class FeatureExplorerTab(QWidget):
    requires_data = True

    def show_empty_state(self) -> None:
        self._content_stack.setCurrentWidget(self._empty_state)
        self._empty_state.set_message(
            icon="📁",
            title="No Data Loaded",
            description="Load a trading data file in the Data Input tab.",
            action_text="Go to Data Input",
            action_callback=lambda: self._app_state.request_tab_change.emit(0),
        )
```

### Global Exception Handler

```python
# src/main.py
import sys
from PyQt6.QtWidgets import QApplication, QMessageBox

def exception_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    QMessageBox.critical(
        None,
        "Unexpected Error",
        "An unexpected error occurred. Please save your work and restart.",
    )

def main():
    sys.excepthook = exception_handler
    app = QApplication(sys.argv)
    # ...
```

### Font Loading with Fallback

```python
# src/ui/theme.py
class FontLoader:
    FALLBACKS = {
        "Azeret Mono": ["SF Mono", "Consolas", "Courier New"],
        "Geist": ["SF Pro Text", "Segoe UI", "Arial"],
    }

    def load_fonts(self) -> tuple[bool, list[str]]:
        """Load fonts, return (success, warnings)."""
        warnings = []

        for family, weights in self.REQUIRED_FONTS.items():
            if family not in self._loaded_fonts:
                fallback = self._find_fallback(family)
                if fallback:
                    self._using_fallbacks[family] = fallback
                    warnings.append(f"Using {fallback} instead of {family}")

        return len(self._using_fallbacks) == 0, warnings
```

---

## 11. Build & Distribution

### PyInstaller Configuration

```python
# lumen.spec
block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/fonts/*.ttf', 'assets/fonts'),
        ('assets/fonts/*.otf', 'assets/fonts'),
    ],
    hiddenimports=[
        'PyQt6.QtSvg',
        'pyqtgraph.opengl',
    ],
    excludes=['tkinter', 'matplotlib', 'scipy'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Lumen',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/icon.ico',
)
```

### Build Commands

```makefile
# Production build
build:
	uv run pyinstaller lumen.spec --clean --noconfirm

# Development build (with console)
build-dev:
	uv run pyinstaller src/main.py --name Lumen-Dev --onedir --console --add-data "assets/fonts:assets/fonts"
```

### Version Management

```python
# src/__version__.py
__version__ = "1.0.0"

# src/main.py
from src.__version__ import __version__

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Lumen v{__version__}")
```

### Distribution Checklist

| Item | Requirement |
|------|-------------|
| Single .exe file | PyInstaller --onefile |
| No installer needed | Portable executable |
| Fonts bundled | Azeret Mono, Geist |
| Icon embedded | assets/icon.ico |
| Version in title | "Lumen v1.0.0" |
| Windows 10/11 | Target platform |
| No admin required | User-space execution |

---

## 12. Operational Considerations

### Logging Configuration

```python
# src/logging_config.py
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logging(debug: bool = False) -> None:
    log_dir = Path.home() / ".lumen" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_dir / "lumen.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    ))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)
    root_logger.addHandler(file_handler)

    # Reduce third-party noise
    logging.getLogger("PyQt6").setLevel(logging.WARNING)
    logging.getLogger("pyqtgraph").setLevel(logging.WARNING)
```

### Crash Reporting

```python
# src/crash_reporter.py
import traceback
from datetime import datetime
from pathlib import Path

def save_crash_report(exc_type, exc_value, exc_traceback) -> Path:
    crash_dir = Path.home() / ".lumen" / "crashes"
    crash_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    crash_file = crash_dir / f"crash_{timestamp}.txt"

    with open(crash_file, "w") as f:
        f.write(f"Lumen Crash Report\n")
        f.write(f"Time: {datetime.now().isoformat()}\n")
        f.write(f"Version: {__version__}\n\n")
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)

    return crash_file
```

### User Data Locations

```
~/.lumen/                      # User data directory
├── logs/
│   └── lumen.log              # Application log (rotated)
└── crashes/
    └── crash_*.txt            # Crash reports

.lumen_cache/                  # Project-local cache
├── {file_hash}.parquet        # Cached data files
├── {file_hash}_mappings.json  # Column mappings
└── window_state.json          # Window position/size
```

### Performance Monitoring (Development)

```python
# src/utils/profiling.py
from functools import wraps
from time import perf_counter

def timed(func):
    """Decorator to log function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = perf_counter()
        result = func(*args, **kwargs)
        elapsed = perf_counter() - start
        logger.debug("%s completed in %.3fs", func.__name__, elapsed)
        return result
    return wrapper
```

---

## Appendix: Requirements Traceability

| PRD Requirement | Architecture Section |
|----------------|---------------------|
| FR1-3 (File Loading) | §5 FileLoader, §10 FileLoadError |
| FR4-5 (Column Config) | §4 ColumnMapping, §5 ColumnMapper |
| FR6-7 (First Trigger) | §5 FirstTriggerEngine, §6 Workflow 1 |
| FR8-14 (Metrics) | §4 TradingMetrics, §5 MetricsCalculator |
| FR9-10 (Filtering) | §4 FilterCriteria, §5 FilterEngine |
| FR15 (User Inputs) | §4 AppState, §6 Workflow 2 |
| FR16-18 (Charts) | §5 ChartCanvas |
| FR19-20 (Comparison) | §5 ComparisonRibbon, DataGrid |
| FR21-23 (Export) | §5 ExportManager |
| FR24-25 (Tabs) | §5 Tab Components |
| FR26-27 (Cache) | §5 CacheManager |
| NFR1-3 (Performance) | §6 Annotations, §8 Performance Tests |
| NFR4 (Memory) | §8 Memory Test |
| NFR5 (Crash Rate) | §10 Global Exception Handler |
| NFR6-7 (Platform) | §11 Build & Distribution |
| NFR8 (Dark Mode) | §9 Theme Constants |
| NFR9 (Flexible Schemas) | §10 Error Handling |
| NFR10-11 (Tech Stack) | §3 Tech Stack |

---

*Generated with BMAD-METHOD Architecture Template v4.0*
