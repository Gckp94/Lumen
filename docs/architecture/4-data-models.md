# 4. Data Models

## ColumnMapping

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
    mae_pct: str  # Required for stop loss calculations
    win_loss: str | None = None  # None = derive from gain_pct
    win_loss_derived: bool = False
    breakeven_is_win: bool = False  # When deriving, is 0% gain a win?

    def validate(self, df_columns: list[str]) -> list[str]:
        """Validate mapping against DataFrame columns. Returns list of errors."""
        errors = []
        required = [self.ticker, self.date, self.time, self.gain_pct, self.mae_pct]
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

## FilterCriteria

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

## AdjustmentParams

```python
@dataclass
class AdjustmentParams:
    """User-configurable parameters for trade adjustment calculations.

    These adjustments are applied to every trade before metric calculation:
    1. Stop loss adjustment: If mae_pct > stop_loss, gain is capped at -stop_loss
    2. Efficiency adjustment: Efficiency is subtracted from all trades
    """

    stop_loss: float = 8.0      # Stop loss percentage (e.g., 8 = 8%)
    efficiency: float = 5.0     # Efficiency/slippage percentage (e.g., 5 = 5%)

    def calculate_adjusted_gain(self, gain_pct: float, mae_pct: float) -> float:
        """Calculate efficiency-adjusted gain for a single trade.

        Args:
            gain_pct: Original gain percentage (whole number, e.g., 20 = 20%)
            mae_pct: Maximum adverse excursion percentage

        Returns:
            Efficiency-adjusted gain percentage
        """
        # Step 1: Stop loss adjustment
        if mae_pct > self.stop_loss:
            stop_adjusted = -self.stop_loss
        else:
            stop_adjusted = gain_pct

        # Step 2: Efficiency adjustment
        return stop_adjusted - self.efficiency

    def calculate_adjusted_gains(self, df: pd.DataFrame, gain_col: str, mae_col: str) -> pd.Series:
        """Calculate adjusted gains for entire DataFrame (vectorized).

        Args:
            df: DataFrame with trade data
            gain_col: Column name for gain percentage
            mae_col: Column name for MAE percentage

        Returns:
            Series of efficiency-adjusted gain percentages
        """
        gains = df[gain_col]
        maes = df[mae_col]

        # Step 1: Stop loss adjustment (vectorized)
        stop_adjusted = gains.where(maes <= self.stop_loss, -self.stop_loss)

        # Step 2: Efficiency adjustment
        return stop_adjusted - self.efficiency
```

## TradingMetrics

```python
@dataclass
class TradingMetrics:
    """All 25 trading metrics as defined in PRD Appendix D."""

    # Core Statistics (1-12)
    num_trades: int
    win_rate: float | None          # Percentage (0-100)
    avg_winner: float | None        # Percentage (always positive - classified by adjusted gain > 0)
    avg_loser: float | None         # Percentage (always negative - classified by adjusted gain <= 0)
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

## AppState

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
    adjustment_params_changed = Signal(object)  # AdjustmentParams
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
        self.adjustment_params: AdjustmentParams = AdjustmentParams()  # Default values
        self._snapshot: StateSnapshot | None = None

    @property
    def has_data(self) -> bool:
        """Check if data is loaded and configured."""
        return self.baseline_df is not None and self.column_mapping is not None
```

## WindowState

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

## Constants

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
