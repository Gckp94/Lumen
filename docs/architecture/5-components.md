# 5. Components

## UI Components

### MetricCard

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

### ComparisonRibbon

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

### FilterChip

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

### ToggleSwitch

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

### DataGrid

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

### ChartCanvas

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

### Toast

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

### EmptyState

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

## Core Components

### FileLoader

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

### ColumnMapper

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

### FirstTriggerEngine

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

### FilterEngine

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

### MetricsCalculator

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

### EquityCalculator

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

### ExportManager

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

### CacheManager

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
