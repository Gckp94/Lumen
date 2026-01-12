# 9. Coding Standards

## Language & Formatting

```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ["py311"]

[tool.ruff]
line-length = 100
select = ["E", "F", "W", "I", "UP", "B", "SIM"]
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Modules | snake_case | `filter_engine.py` |
| Classes | PascalCase | `FilterEngine` |
| Functions | snake_case | `apply_first_trigger()` |
| Constants | SCREAMING_SNAKE | `MAX_FILTERS = 10` |
| Private | Leading underscore | `_calculate_delta()` |
| Qt Signals | snake_case | `metrics_updated` |
| Qt Slots | on_noun_verb | `on_filter_applied` |

## Type Hints

```python
# Required for all public APIs
def calculate_metrics(
    trades: pd.DataFrame,
    column_mapping: ColumnMapping,
) -> TradingMetrics:
    """Calculate all 25 trading metrics."""
    ...
```

## Qt Patterns

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

## Pandas Patterns

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

## Exception Hierarchy

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

## Theme Constants

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

## Logging Guidelines

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
