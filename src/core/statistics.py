"""Statistics calculations for trade analysis tables."""

import pandas as pd

from src.core.models import ColumnMapping

# Bucket definitions for MAE before win table
# Format: (label, lower_bound_pct, upper_bound_pct)
# Lower bound is exclusive (>), upper bound is inclusive (<=)
# None means unbounded
MAE_WIN_BUCKETS = [
    (">0%", 0, 10),  # 0% < gain <= 10%
    (">10%", 10, 20),  # 10% < gain <= 20%
    (">20%", 20, 30),  # 20% < gain <= 30%
    (">30%", 30, 40),  # 30% < gain <= 40%
    (">40%", 40, 50),  # 40% < gain <= 50%
    (">50%", 50, None),  # gain > 50%
]

# MAE thresholds for probability columns
MAE_THRESHOLDS = [5, 10, 15, 20]

# Bucket definitions for MFE before loss table
# Same structure as MAE buckets but for loss magnitude (absolute value)
MFE_LOSS_BUCKETS = [
    (">0%", 0, 10),  # 0% < |loss| <= 10%
    (">10%", 10, 20),  # 10% < |loss| <= 20%
    (">20%", 20, 30),  # 20% < |loss| <= 30%
    (">30%", 30, 40),  # 30% < |loss| <= 40%
    (">40%", 40, 50),  # 40% < |loss| <= 50%
    (">50%", 50, None),  # |loss| > 50%
]

# MFE thresholds for probability columns
MFE_THRESHOLDS = [5, 10, 15, 20]


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
        return pd.DataFrame(
            columns=[
                "% Gain per Trade",
                "# of Plays",
                "% of Total",
                "Avg %",
                "Median %",
                ">5% MAE Probability",
                ">10% MAE Probability",
                ">15% MAE Probability",
                ">20% MAE Probability",
            ]
        )

    # Convert adjusted_gain_pct from decimal to percentage for bucketing
    winners["gain_pct_display"] = winners["adjusted_gain_pct"] * 100

    # Get mae_pct column name from mapping
    mae_col = mapping.mae_pct

    # Build result rows
    rows = []

    # Overall row first
    overall_row = _calculate_bucket_row("Overall", winners, winners, total_winners, mae_col)
    rows.append(overall_row)

    # Bucket rows
    for label, lower, upper in MAE_WIN_BUCKETS:
        if upper is None:
            # >50% bucket: gain > 50%
            bucket_mask = winners["gain_pct_display"] > lower
        else:
            # Standard bucket: lower < gain <= upper
            bucket_mask = (winners["gain_pct_display"] > lower) & (
                winners["gain_pct_display"] <= upper
            )

        bucket_df = winners[bucket_mask]
        row = _calculate_bucket_row(label, bucket_df, winners, total_winners, mae_col)
        rows.append(row)

    return pd.DataFrame(rows)


def _calculate_bucket_row(
    label: str, bucket_df: pd.DataFrame, all_winners: pd.DataFrame, total_winners: int, mae_col: str
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
        Columns: % Loss per Trade, # of Plays, % of Total, Avg %, Median %,
                 >5% MFE Probability, >10% MFE Probability,
                 >15% MFE Probability, >20% MFE Probability
    """
    # Filter to losing trades only (adjusted_gain_pct < 0)
    losers = df[df["adjusted_gain_pct"] < 0].copy()
    total_losers = len(losers)

    # Handle empty case
    if total_losers == 0:
        return pd.DataFrame(
            columns=[
                "% Loss per Trade",
                "# of Plays",
                "% of Total",
                "Avg %",
                "Median %",
                ">5% MFE Probability",
                ">10% MFE Probability",
                ">15% MFE Probability",
                ">20% MFE Probability",
            ]
        )

    # Convert adjusted_gain_pct from decimal to percentage (absolute value for bucketing)
    # Loss magnitude is always positive for display
    losers["loss_pct_display"] = losers["adjusted_gain_pct"].abs() * 100

    # Get mfe_pct column name from mapping
    mfe_col = mapping.mfe_pct

    # Build result rows
    rows = []

    # Overall row first
    overall_row = _calculate_loss_bucket_row("Overall", losers, losers, total_losers, mfe_col)
    rows.append(overall_row)

    # Bucket rows
    for label, lower, upper in MFE_LOSS_BUCKETS:
        if upper is None:
            # >50% bucket: |loss| > 50%
            bucket_mask = losers["loss_pct_display"] > lower
        else:
            # Standard bucket: lower < |loss| <= upper
            bucket_mask = (losers["loss_pct_display"] > lower) & (
                losers["loss_pct_display"] <= upper
            )

        bucket_df = losers[bucket_mask]
        row = _calculate_loss_bucket_row(label, bucket_df, losers, total_losers, mfe_col)
        rows.append(row)

    return pd.DataFrame(rows)


def _calculate_loss_bucket_row(
    label: str, bucket_df: pd.DataFrame, all_losers: pd.DataFrame, total_losers: int, mfe_col: str
) -> dict:
    """Calculate metrics for a single loss bucket row.

    Args:
        label: Row label (e.g., "Overall", ">0%").
        bucket_df: DataFrame of trades in this bucket.
        all_losers: DataFrame of all losing trades (for MFE probability denominator).
        total_losers: Total number of losers.
        mfe_col: Column name for MFE percentage.

    Returns:
        Dictionary with row data.
    """
    count = len(bucket_df)

    if count == 0:
        return {
            "% Loss per Trade": label,
            "# of Plays": 0,
            "% of Total": 0.0,
            "Avg %": None,
            "Median %": None,
            ">5% MFE Probability": 0.0,
            ">10% MFE Probability": 0.0,
            ">15% MFE Probability": 0.0,
            ">20% MFE Probability": 0.0,
        }

    # Calculate statistics (using absolute loss values)
    avg_pct = bucket_df["loss_pct_display"].mean()
    median_pct = bucket_df["loss_pct_display"].median()
    pct_of_total = (count / total_losers) * 100

    # Calculate MFE probabilities
    # "Count where mfe_pct > threshold / total losers x 100"
    mfe_probs = {}
    for threshold in MFE_THRESHOLDS:
        mfe_count = (bucket_df[mfe_col] > threshold).sum()
        mfe_probs[f">{threshold}% MFE Probability"] = (mfe_count / total_losers) * 100

    return {
        "% Loss per Trade": label,
        "# of Plays": count,
        "% of Total": pct_of_total,
        "Avg %": avg_pct,
        "Median %": median_pct,
        **mfe_probs,
    }


# Stop loss levels (fixed)
STOP_LOSS_LEVELS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]


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
        Columns: Stop %, Win %, Profit Ratio, Edge %, EG %, Max Loss %,
                 Full Kelly (Stop Adj), Half Kelly (Stop Adj), Quarter Kelly (Stop Adj)
    """
    rows = []
    gain_col = mapping.gain_pct
    mae_col = mapping.mae_pct

    for stop_level in STOP_LOSS_LEVELS:
        row = _calculate_stop_level_row(df, gain_col, mae_col, stop_level, efficiency)
        rows.append(row)

    return pd.DataFrame(rows)


def _calculate_stop_level_row(
    df: pd.DataFrame,
    gain_col: str,
    mae_col: str,
    stop_level: int,
    efficiency: float,
) -> dict:
    """Calculate metrics for a single stop loss level.

    Args:
        df: Trade data DataFrame.
        gain_col: Column name for gain percentage (decimal).
        mae_col: Column name for MAE percentage (percentage points).
        stop_level: Stop loss level (e.g., 20 for 20%).
        efficiency: Efficiency factor (0-1).

    Returns:
        Dictionary with metrics for this stop level.
    """
    total_trades = len(df)

    # Handle empty data
    if total_trades == 0:
        return {
            "Stop %": stop_level,
            "Win %": 0.0,
            "Profit Ratio": None,
            "Edge %": None,
            "EG %": None,
            "Max Loss %": 0.0,
            "Full Kelly (Stop Adj)": None,
            "Half Kelly (Stop Adj)": None,
            "Quarter Kelly (Stop Adj)": None,
        }

    # Calculate adjusted returns for each trade
    # If mae_pct >= stop_level: stopped out, return = -stop_level/100 * efficiency
    # Otherwise: use original gain_pct
    stopped_mask = df[mae_col] >= stop_level
    stopped_count = stopped_mask.sum()

    # Calculate adjusted returns
    adjusted_returns = df[gain_col].copy()
    stop_loss_return = -(stop_level / 100.0) * efficiency
    adjusted_returns[stopped_mask] = stop_loss_return

    # Calculate metrics from adjusted returns
    winners = adjusted_returns > 0
    losers = adjusted_returns < 0

    win_count = winners.sum()
    loss_count = losers.sum()

    # Win %
    win_pct = (win_count / total_trades) * 100

    # Max Loss % (stopped out / total × 100)
    max_loss_pct = (stopped_count / total_trades) * 100

    # Calculate avg_win and avg_loss for profit ratio
    avg_win = adjusted_returns[winners].mean() if win_count > 0 else 0.0
    avg_loss = adjusted_returns[losers].mean() if loss_count > 0 else 0.0  # Negative

    # Profit Ratio: avg_win / abs(avg_loss)
    profit_ratio = avg_win / abs(avg_loss) if avg_loss != 0 else None

    # Edge %: (profit_ratio + 1) × win_rate - 1 (as percentage)
    # win_rate is a decimal (0-1)
    win_rate = win_count / total_trades
    if profit_ratio is not None:
        edge_decimal = (profit_ratio + 1) * win_rate - 1
        edge_pct = edge_decimal * 100
    else:
        edge_decimal = None
        edge_pct = None

    # EG %: Kelly growth formula
    # EG = edge_pct × win_rate - (1 - win_rate) × loss_rate / profit_ratio
    # Simplified: EG = win_rate * avg_win - loss_rate * avg_loss (expected value approach)
    # Or using Kelly: g = p * ln(1 + b) + q * ln(1 - 1) where b is odds
    # Let's use: EG = win_rate - (1 - win_rate) / profit_ratio (standard Kelly EV formula)
    if profit_ratio is not None and profit_ratio > 0:
        loss_rate = 1 - win_rate
        eg_decimal = win_rate - loss_rate / profit_ratio
        eg_pct = eg_decimal * 100
    else:
        eg_pct = None

    # Full Kelly (Stop Adj): edge / profit_ratio / (stop_level/100)
    # edge here is in decimal form
    if profit_ratio is not None and profit_ratio > 0 and edge_decimal is not None:
        stop_decimal = stop_level / 100.0
        full_kelly = edge_decimal / profit_ratio / stop_decimal
        half_kelly = full_kelly / 2
        quarter_kelly = full_kelly / 4
    else:
        full_kelly = None
        half_kelly = None
        quarter_kelly = None

    return {
        "Stop %": stop_level,
        "Win %": win_pct,
        "Profit Ratio": profit_ratio,
        "Edge %": edge_pct,
        "EG %": eg_pct,
        "Max Loss %": max_loss_pct,
        "Full Kelly (Stop Adj)": full_kelly,
        "Half Kelly (Stop Adj)": half_kelly,
        "Quarter Kelly (Stop Adj)": quarter_kelly,
    }


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
