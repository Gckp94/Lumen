"""Data models for Portfolio Overview feature."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PositionSizeType(Enum):
    """Position sizing method."""
    FRAC_KELLY = "frac_kelly"
    CUSTOM_PCT = "custom_pct"
    FLAT_DOLLAR = "flat_dollar"


@dataclass
class PortfolioColumnMapping:
    """Maps CSV columns to required fields.

    Note: Win/loss is derived from gain_pct (positive = win, negative = loss)
    after stop loss and efficiency adjustments are applied.
    """
    date_col: str
    gain_pct_col: str
    mae_pct_col: Optional[str] = None
    ticker_col: Optional[str] = None  # Optional ticker column for overlap analysis


@dataclass
class StrategyConfig:
    """Configuration for a single strategy."""
    name: str
    file_path: str
    column_mapping: PortfolioColumnMapping
    sheet_name: Optional[str] = None
    stop_pct: float = 2.0
    efficiency: float = 5.0  # 5% default (stored as percentage points)
    size_type: PositionSizeType = PositionSizeType.CUSTOM_PCT
    size_value: float = 10.0  # 10% default
    max_compound: Optional[float] = 50000.0  # $50,000 default
    is_baseline: bool = False
    is_candidate: bool = False
