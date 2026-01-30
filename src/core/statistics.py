"""Statistics calculations for trade analysis tables."""

import pandas as pd
import numpy as np
from src.core.models import ColumnMapping


# Bucket definitions for MAE before win table
# Format: (label, lower_bound_pct, upper_bound_pct)
# Lower bound is exclusive (>), upper bound is inclusive (<=)
# None means unbounded
MAE_WIN_BUCKETS = [
    (">0%", 0, 10),      # 0% < gain <= 10%
    (">10%", 10, 20),    # 10% < gain <= 20%
    (">20%", 20, 30),    # 20% < gain <= 30%
    (">30%", 30, 40),    # 30% < gain <= 40%
    (">40%", 40, 50),    # 40% < gain <= 50%
    (">50%", 50, None),  # gain > 50%
]

# MAE thresholds for probability columns
MAE_THRESHOLDS = [5, 10, 15, 20]


def calculate_mae_before_win(df: pd.DataFrame, mapping: ColumnMapping) -> pd.DataFrame:
    """Calculate MAE probabilities for winning trades by gain bucket.

    Args:
        df: Trade data with adjusted_gain_pct and mae_pct columns.
        mapping: Column mapping configuration.

    Returns:
        DataFrame with rows for each gain bucket and MAE probability columns.
        Columns: % Gain per Trade, # of Plays, % of Total, Avg %, Median %,
                 >5% MAE Probability, >10% MAE Probability,
                 >15% MAE Probability, >20% MAE Probability
    """
    # Filter to winning trades only (adjusted_gain_pct > 0)
    winners = df[df["adjusted_gain_pct"] > 0].copy()
    total_winners = len(winners)

    # Handle empty case
    if total_winners == 0:
        return pd.DataFrame(columns=[
            "% Gain per Trade", "# of Plays", "% of Total", "Avg %", "Median %",
            ">5% MAE Probability", ">10% MAE Probability",
            ">15% MAE Probability", ">20% MAE Probability"
        ])

    # Convert adjusted_gain_pct from decimal to percentage for bucketing
    winners["gain_pct_display"] = winners["adjusted_gain_pct"] * 100

    # Get mae_pct column name from mapping
    mae_col = mapping.mae_pct

    # Build result rows
    rows = []

    # Overall row first
    overall_row = _calculate_bucket_row(
        "Overall", winners, winners, total_winners, mae_col
    )
    rows.append(overall_row)

    # Bucket rows
    for label, lower, upper in MAE_WIN_BUCKETS:
        if upper is None:
            # >50% bucket: gain > 50%
            bucket_mask = winners["gain_pct_display"] > lower
        else:
            # Standard bucket: lower < gain <= upper
            bucket_mask = (winners["gain_pct_display"] > lower) & (winners["gain_pct_display"] <= upper)

        bucket_df = winners[bucket_mask]
        row = _calculate_bucket_row(label, bucket_df, winners, total_winners, mae_col)
        rows.append(row)

    return pd.DataFrame(rows)


def _calculate_bucket_row(
    label: str,
    bucket_df: pd.DataFrame,
    all_winners: pd.DataFrame,
    total_winners: int,
    mae_col: str
) -> dict:
    """Calculate metrics for a single bucket row.

    Args:
        label: Row label (e.g., "Overall", ">0%").
        bucket_df: DataFrame of trades in this bucket.
        all_winners: DataFrame of all winning trades (for MAE probability denominator).
        total_winners: Total number of winners.
        mae_col: Column name for MAE percentage.

    Returns:
        Dictionary with row data.
    """
    count = len(bucket_df)

    if count == 0:
        return {
            "% Gain per Trade": label,
            "# of Plays": 0,
            "% of Total": 0.0,
            "Avg %": None,
            "Median %": None,
            ">5% MAE Probability": 0.0,
            ">10% MAE Probability": 0.0,
            ">15% MAE Probability": 0.0,
            ">20% MAE Probability": 0.0,
        }

    # Calculate statistics
    avg_pct = bucket_df["gain_pct_display"].mean()
    median_pct = bucket_df["gain_pct_display"].median()
    pct_of_total = (count / total_winners) * 100

    # Calculate MAE probabilities
    # "Count where mae_pct > threshold / total winners × 100"
    mae_probs = {}
    for threshold in MAE_THRESHOLDS:
        mae_count = (bucket_df[mae_col] > threshold).sum()
        mae_probs[f">{threshold}% MAE Probability"] = (mae_count / total_winners) * 100

    return {
        "% Gain per Trade": label,
        "# of Plays": count,
        "% of Total": pct_of_total,
        "Avg %": avg_pct,
        "Median %": median_pct,
        **mae_probs,
    }


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
