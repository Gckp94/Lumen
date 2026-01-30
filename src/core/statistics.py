"""Statistics calculations for trade analysis tables."""

import pandas as pd
from src.core.models import ColumnMapping


def calculate_mae_before_win(df: pd.DataFrame, mapping: ColumnMapping) -> pd.DataFrame:
    """Calculate MAE probabilities for winning trades by gain bucket.

    Args:
        df: Trade data with adjusted_gain_pct and mae_pct columns.
        mapping: Column mapping configuration.

    Returns:
        DataFrame with rows for each gain bucket and MAE probability columns.
    """
    raise NotImplementedError


def calculate_mfe_before_loss(df: pd.DataFrame, mapping: ColumnMapping) -> pd.DataFrame:
    """Calculate MFE probabilities for losing trades by loss bucket.

    Args:
        df: Trade data with adjusted_gain_pct and mfe_pct columns.
        mapping: Column mapping configuration.

    Returns:
        DataFrame with rows for each loss bucket and MFE probability columns.
    """
    raise NotImplementedError


def calculate_stop_loss_table(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    efficiency: float,
) -> pd.DataFrame:
    """Simulate stop loss levels and calculate metrics.

    Args:
        df: Trade data with gain_pct and mae_pct columns.
        mapping: Column mapping configuration.
        efficiency: Efficiency percentage (0-1) applied to stopped trades.

    Returns:
        DataFrame with rows for each stop level and performance metrics.
    """
    raise NotImplementedError


def calculate_offset_table(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    stop_loss: float,
    efficiency: float,
) -> pd.DataFrame:
    """Simulate entry offsets with recalculated MAE/MFE and returns.

    For SHORT trades:
    - Negative offset: price dropped before entry (need mfe_pct >= abs(offset))
    - Positive offset: price rose before entry (need mae_pct >= offset)

    Args:
        df: Trade data with gain_pct, mae_pct, and mfe_pct columns.
        mapping: Column mapping configuration.
        stop_loss: Stop loss percentage (e.g., 20.0 for 20%).
        efficiency: Efficiency percentage (0-1) applied to stopped trades.

    Returns:
        DataFrame with rows for each offset level and performance metrics.
    """
    raise NotImplementedError


def calculate_scaling_table(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    scale_out_pct: float,
) -> pd.DataFrame:
    """Compare blended partial-profit returns vs full hold.

    Args:
        df: Trade data with adjusted_gain_pct and mfe_pct columns.
        mapping: Column mapping configuration.
        scale_out_pct: Fraction of position to scale out (0-1, e.g., 0.5 for 50%).

    Returns:
        DataFrame with rows for each target level comparing blended vs full hold.
    """
    raise NotImplementedError
