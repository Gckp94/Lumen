"""Data models for Lumen application."""

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Literal

import pandas as pd

if TYPE_CHECKING:
    pass


@dataclass
class ColumnMapping:
    """Mapping of required columns to DataFrame column names.

    Attributes:
        ticker: Column name for ticker/symbol.
        date: Column name for trade date.
        time: Column name for trade time.
        gain_pct: Column name for gain percentage.
        mae_pct: Column name for Maximum Adverse Excursion percentage.
        win_loss: Optional column name for win/loss indicator.
        win_loss_derived: Whether win/loss is derived from gain_pct.
        breakeven_is_win: When deriving, is 0% gain considered a win?
    """

    ticker: str
    date: str
    time: str
    gain_pct: str
    mae_pct: str
    win_loss: str | None = None
    win_loss_derived: bool = False
    breakeven_is_win: bool = False

    def validate(self, df_columns: list[str]) -> list[str]:
        """Validate mapping against DataFrame columns.

        Args:
            df_columns: List of column names from the DataFrame.

        Returns:
            List of validation error messages. Empty list if valid.
        """
        errors: list[str] = []
        required = [self.ticker, self.date, self.time, self.gain_pct, self.mae_pct]
        for col in required:
            if col not in df_columns:
                errors.append(f"Column '{col}' not found in data")
        if self.win_loss and self.win_loss not in df_columns:
            errors.append(f"Win/Loss column '{self.win_loss}' not found")
        return errors


@dataclass
class DetectionResult:
    """Result of column auto-detection.

    Attributes:
        mapping: Complete column mapping if all required columns detected, else None.
        statuses: Dict mapping column type to detection status.
        all_required_detected: True if all required columns were detected.
    """

    mapping: ColumnMapping | None
    statuses: dict[str, str] = field(default_factory=dict)
    all_required_detected: bool = False


@dataclass
class TradingMetrics:
    """Trading metrics for baseline and filtered data analysis.

    Story 1.6 implements 7 core metrics. Story 3.2 adds metrics 8-12
    and distribution statistics.

    Attributes:
        num_trades: Total number of trades.
        win_rate: Win rate as percentage (0-100).
        avg_winner: Average gain of winning trades (percentage).
        avg_loser: Average gain of losing trades (negative percentage).
        rr_ratio: Risk:Reward ratio (abs(avg_winner / avg_loser)).
        ev: Expected Value per trade (percentage).
        kelly: Kelly criterion optimal bet fraction (percentage).
        winner_count: Number of winning trades.
        loser_count: Number of losing trades.
        winner_std: Standard deviation of winner gains.
        loser_std: Standard deviation of loser gains.
        winner_gains: List of individual winner gain percentages.
        loser_gains: List of individual loser gain percentages.
        edge: Total edge (EV * num_trades).
        fractional_kelly: User-adjusted Kelly (Kelly * fraction).
        expected_growth: Expected geometric growth rate.
        median_winner: Median gain of winning trades.
        median_loser: Median loss of losing trades.
        winner_min: Minimum winner gain.
        winner_max: Maximum winner gain.
        loser_min: Minimum loser gain (most negative).
        loser_max: Maximum loser gain (least negative).
        max_consecutive_wins: Maximum consecutive winning trades.
        max_consecutive_losses: Maximum consecutive losing trades.
        max_loss_pct: Maximum single trade loss percentage.
        flat_stake_pnl: Total PnL in dollars with fixed position size.
        flat_stake_max_dd: Maximum drawdown in dollars.
        flat_stake_max_dd_pct: Maximum drawdown as percentage of peak equity.
        flat_stake_dd_duration: Trading days to recover from max drawdown, or "Not recovered".
        kelly_pnl: Total PnL in dollars with compounded Kelly position sizing.
        kelly_max_dd: Maximum drawdown in dollars (Kelly sizing).
        kelly_max_dd_pct: Maximum drawdown as percentage of peak (Kelly sizing).
        kelly_dd_duration: Days to recover, "Not recovered", or "Blown" (account wiped).
    """

    # Core Statistics (Story 1.6)
    num_trades: int
    win_rate: float | None  # Percentage (0-100)
    avg_winner: float | None  # Percentage
    avg_loser: float | None  # Percentage (negative)
    rr_ratio: float | None  # Risk:Reward ratio
    ev: float | None  # Expected Value percentage
    kelly: float | None  # Kelly criterion percentage

    # Distribution Data (Story 1.6)
    winner_count: int | None = None
    loser_count: int | None = None
    winner_std: float | None = None
    loser_std: float | None = None
    winner_gains: list[float] = field(default_factory=list)
    loser_gains: list[float] = field(default_factory=list)

    # Extended Core Statistics (Story 3.2 - metrics 8-12)
    edge: float | None = None  # Edge = EV * num_trades
    fractional_kelly: float | None = None  # Kelly * fractional_pct
    expected_growth: float | None = None  # Expected growth rate
    median_winner: float | None = None
    median_loser: float | None = None

    # Extended Distribution Data (Story 3.2 - metrics 24-25 prep)
    winner_min: float | None = None
    winner_max: float | None = None
    loser_min: float | None = None  # Most negative (worst loss)
    loser_max: float | None = None  # Least negative (smallest loss)

    # Streak & Loss Metrics (Story 3.3 - metrics 13-15)
    max_consecutive_wins: int | None = None
    max_consecutive_losses: int | None = None
    max_loss_pct: float | None = None  # Worst single-trade loss percentage

    # Flat Stake Metrics (Story 3.4 - metrics 16-19)
    flat_stake_pnl: float | None = None  # Total PnL in dollars
    flat_stake_max_dd: float | None = None  # Maximum drawdown in dollars
    flat_stake_max_dd_pct: float | None = None  # Maximum drawdown as percentage of peak
    flat_stake_dd_duration: int | str | None = None  # Days or "Not recovered"

    # Compounded Kelly Metrics (Story 3.5 - metrics 20-23)
    kelly_pnl: float | None = None  # Final portfolio value minus start capital
    kelly_max_dd: float | None = None  # Maximum drawdown in dollars
    kelly_max_dd_pct: float | None = None  # Maximum drawdown as percentage of peak
    kelly_dd_duration: int | str | None = None  # Days, "Not recovered", or "Blown"

    @classmethod
    def empty(cls) -> "TradingMetrics":
        """Return metrics with all None/zero values for empty datasets."""
        return cls(
            num_trades=0,
            win_rate=None,
            avg_winner=None,
            avg_loser=None,
            rr_ratio=None,
            ev=None,
            kelly=None,
            winner_count=0,
            loser_count=0,
            winner_std=None,
            loser_std=None,
            winner_gains=[],
            loser_gains=[],
            edge=None,
            fractional_kelly=None,
            expected_growth=None,
            median_winner=None,
            median_loser=None,
            winner_min=None,
            winner_max=None,
            loser_min=None,
            loser_max=None,
            max_consecutive_wins=None,
            max_consecutive_losses=None,
            max_loss_pct=None,
            flat_stake_pnl=None,
            flat_stake_max_dd=None,
            flat_stake_max_dd_pct=None,
            flat_stake_dd_duration=None,
            kelly_pnl=None,
            kelly_max_dd=None,
            kelly_max_dd_pct=None,
            kelly_dd_duration=None,
        )


@dataclass
class AdjustmentParams:
    """User-configurable parameters for trade adjustment calculations.

    Attributes:
        stop_loss: Stop loss percentage (e.g., 8 = 8%).
        efficiency: Efficiency/slippage percentage (e.g., 5 = 5%).
    """

    stop_loss: float = 8.0
    efficiency: float = 5.0

    def calculate_adjusted_gain(self, gain_pct: float, mae_pct: float) -> float:
        """Calculate efficiency-adjusted gain for a single trade.

        Note: This method expects PERCENTAGE format inputs (20 = 20%).
        For decimal-format inputs (0.20 = 20%), use calculate_adjusted_gains()
        which is the preferred method for production use with DataFrames.

        Args:
            gain_pct: Original gain in percentage format (e.g., 20 for 20%).
            mae_pct: Maximum adverse excursion in percentage format (e.g., 8 for 8%).

        Returns:
            Efficiency-adjusted gain in percentage format.
        """
        # Step 1: Stop loss adjustment
        stop_adjusted = -self.stop_loss if mae_pct > self.stop_loss else gain_pct
        # Step 2: Efficiency adjustment
        return stop_adjusted - self.efficiency

    def calculate_adjusted_gains(
        self, df: pd.DataFrame, gain_col: str, mae_col: str
    ) -> pd.Series:
        """Calculate efficiency-adjusted gains for all trades (vectorized).

        Args:
            df: DataFrame with trade data.
            gain_col: Column name for gain percentage (decimal format, e.g., 0.20 = 20%).
            mae_col: Column name for MAE percentage (percentage format, e.g., 27 = 27%).

        Returns:
            Series of efficiency-adjusted gain percentages (decimal format).
        """
        gains = df[gain_col].astype(float)
        mae = df[mae_col].astype(float)

        # Diagnostic logging for adjustment calculation
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            "DIAGNOSTIC (adjust): Raw gains from '%s' - min=%.6f, max=%.6f, mean=%.6f, "
            "sample first 5: %s",
            gain_col,
            gains.min(),
            gains.max(),
            gains.mean(),
            gains.head(5).tolist(),
        )
        logger.info(
            "DIAGNOSTIC (adjust): MAE from '%s' - min=%.6f, max=%.6f, mean=%.6f, "
            "sample first 5: %s",
            mae_col,
            mae.min(),
            mae.max(),
            mae.mean(),
            mae.head(5).tolist(),
        )

        # Convert gains from decimal to percentage format for adjustment
        gains_pct = gains * 100

        # Step 1: Stop loss adjustment (vectorized)
        # If MAE > stop_loss, gain becomes -stop_loss (in percentage)
        stop_adjusted = gains_pct.where(mae <= self.stop_loss, -self.stop_loss)

        # Step 2: Efficiency adjustment (in percentage)
        adjusted_pct = stop_adjusted - self.efficiency

        # Convert back to decimal format for MetricsCalculator compatibility
        return adjusted_pct / 100


@dataclass
class MetricsUserInputs:
    """User inputs for PnL metrics calculations.

    These parameters are used by Epic 3 metrics:
    - flat_stake: Used for flat stake PnL calculations (Story 3.4)
    - starting_capital: Used for compounded Kelly calculations (Story 3.5)
    - fractional_kelly: Kelly fraction to apply (Story 3.2, 3.5)

    Attributes:
        flat_stake: Flat stake amount in dollars.
        starting_capital: Starting capital for Kelly calculations.
        fractional_kelly: Fractional Kelly percentage (e.g., 25 = 25%).
    """

    flat_stake: float = 1000.0
    starting_capital: float = 10000.0
    fractional_kelly: float = 25.0

    def validate(self) -> list[str]:
        """Validate inputs.

        Returns:
            List of error messages. Empty list if valid.
        """
        errors = []
        if self.flat_stake <= 0:
            errors.append("Flat stake must be positive")
        if self.starting_capital <= 0:
            errors.append("Starting capital must be positive")
        if not 1 <= self.fractional_kelly <= 100:
            errors.append("Fractional Kelly must be between 1 and 100")
        return errors

    def to_dict(self) -> dict[str, float]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of inputs.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> "MetricsUserInputs":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with input values.

        Returns:
            New MetricsUserInputs instance.
        """
        return cls(
            flat_stake=data.get("flat_stake", 1000.0),
            starting_capital=data.get("starting_capital", 10000.0),
            fractional_kelly=data.get("fractional_kelly", 25.0),
        )


@dataclass
class FilterCriteria:
    """Single filter criterion for bounds-based filtering.

    Attributes:
        column: Name of the column to filter on.
        operator: Filter operator - 'between' (inclusive) or 'not_between'.
        min_val: Minimum value for the range.
        max_val: Maximum value for the range.
    """

    column: str
    operator: Literal["between", "not_between"]
    min_val: float
    max_val: float

    def validate(self) -> str | None:
        """Validate filter criteria.

        Returns:
            Error message if invalid, None if valid.
        """
        if self.min_val > self.max_val:
            return "Min value must be less than or equal to max value"
        return None

    def apply(self, df: pd.DataFrame) -> pd.Series:
        """Apply filter to DataFrame and return boolean mask.

        Args:
            df: DataFrame containing the column to filter.

        Returns:
            Boolean Series mask where True indicates rows that match the filter.
        """
        col = df[self.column]
        if self.operator == "between":
            return (col >= self.min_val) & (col <= self.max_val)
        else:  # not_between
            return (col < self.min_val) | (col > self.max_val)
