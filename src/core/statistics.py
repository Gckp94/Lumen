"""Statistics calculations for trade analysis tables."""

import logging

import pandas as pd

from src.core.models import AdjustmentParams, ColumnMapping

logger = logging.getLogger(__name__)


def calculate_expected_growth(win_rate: float, profit_ratio: float | None) -> float | None:
    """Calculate Expected Growth (EG%) using geometric growth formula.

    EG represents the expected compound growth rate per trade when betting
    the optimal Kelly fraction.

    Formula: EG = ((1 + R * S)^p) * ((1 - S)^(1-p)) - 1
    Where:
        R = profit_ratio (avg_win / abs(avg_loss))
        S = Kelly stake fraction
        p = win probability (win_rate as decimal 0-1)

    Args:
        win_rate: Win probability as decimal (0.0 to 1.0)
        profit_ratio: Ratio of avg_win to abs(avg_loss)

    Returns:
        EG as percentage (e.g., 30.0 for 30% growth), or None if invalid
    """
    if profit_ratio is None or profit_ratio <= 0:
        return None
    if not (0 < win_rate < 1):
        return None

    # Calculate Kelly stake
    loss_rate = 1 - win_rate
    kelly = win_rate - loss_rate / profit_ratio

    # No positive growth if Kelly is <= 0
    if kelly <= 0:
        return None

    # Kelly must be < 1 (can't bet more than 100%)
    if kelly >= 1:
        kelly = 0.99  # Cap at 99% to avoid math errors

    # Geometric growth formula
    stake = kelly
    try:
        eg = ((1 + profit_ratio * stake) ** win_rate) * ((1 - stake) ** loss_rate) - 1
        return eg * 100  # Convert to percentage
    except (ValueError, OverflowError):
        return None


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

# Offset levels (fixed) for offset table
OFFSET_LEVELS = [-20, -10, 0, 10, 20, 30, 40]


def calculate_stop_loss_table(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    adjustment_params: AdjustmentParams,
) -> pd.DataFrame:
    """Simulate stop loss levels and calculate metrics.

    Args:
        df: Trade data with gain_pct and mae_pct columns.
        mapping: Column mapping configuration.
        adjustment_params: Adjustment parameters (stop_loss, efficiency).

    Returns:
        DataFrame with rows for each stop level and performance metrics.
        Columns: Stop %, Win %, EV %, Avg Gain %, Median Gain %, Profit Ratio,
                 Edge %, EG %, Max Loss %, Full Kelly (Stop Adj),
                 Half Kelly (Stop Adj), Quarter Kelly (Stop Adj)
    """
    rows = []
    gain_col = mapping.gain_pct
    mae_col = mapping.mae_pct

    # Compute adjusted gains fresh using the same method as MetricsCalculator
    # This ensures consistency between Statistics and baseline metrics
    adjusted_gains = adjustment_params.calculate_adjusted_gains(df, gain_col, mae_col)

    # Diagnostic logging
    logger.info(
        "STATISTICS DIAGNOSTIC: calculate_stop_loss_table called - "
        "stop_loss=%.1f, efficiency=%.1f, num_rows=%d, "
        "adjusted_gains min=%.6f, max=%.6f, mean=%.6f",
        adjustment_params.stop_loss,
        adjustment_params.efficiency,
        len(df),
        adjusted_gains.min() if len(adjusted_gains) > 0 else 0,
        adjusted_gains.max() if len(adjusted_gains) > 0 else 0,
        adjusted_gains.mean() if len(adjusted_gains) > 0 else 0,
    )

    for stop_level in STOP_LOSS_LEVELS:
        row = _calculate_stop_level_row(
            df, adjusted_gains, mae_col, stop_level, adjustment_params.efficiency
        )
        rows.append(row)

    # Log the 100% stop row for comparison with baseline
    row_100 = rows[-1]  # Last row should be 100% stop
    logger.info(
        "STATISTICS DIAGNOSTIC: 100%% stop row - Win%%=%.2f, Profit_Ratio=%.4f, Edge%%=%.4f",
        row_100.get("Win %", 0),
        row_100.get("Profit Ratio") or 0,
        row_100.get("Edge %") or 0,
    )

    return pd.DataFrame(rows)


def _calculate_stop_level_row(
    df: pd.DataFrame,
    adjusted_gains: pd.Series,
    mae_col: str,
    stop_level: int,
    efficiency: float,
) -> dict:
    """Calculate metrics for a single stop loss level.

    Args:
        df: Trade data DataFrame.
        adjusted_gains: Pre-computed adjusted gains (decimal format, from AdjustmentParams).
        mae_col: Column name for MAE percentage (percentage points).
        stop_level: Stop loss level (e.g., 20 for 20%).
        efficiency: Efficiency/slippage percentage (e.g., 5 for 5% slippage).

    Returns:
        Dictionary with metrics for this stop level.
    """
    total_trades = len(df)

    # Handle empty data
    if total_trades == 0:
        return {
            "Stop %": stop_level,
            "Win %": 0.0,
            "EV %": None,
            "Avg Gain %": None,
            "Median Gain %": None,
            "Profit Ratio": None,
            "Edge %": None,
            "EG %": None,
            "Max Loss %": 0.0,
            "Full Kelly (Stop Adj)": None,
            "Half Kelly (Stop Adj)": None,
            "Quarter Kelly (Stop Adj)": None,
        }

    # Identify trades that would be stopped at this stop level
    # mae_col is in percentage format (e.g., 27 = 27%)
    # Use > (not >=) to match AdjustmentParams: mae <= stop_loss means NOT stopped
    stopped_mask = df[mae_col] > stop_level
    stopped_count = stopped_mask.sum()

    # Start with the adjusted gains (decimal format, e.g., 0.15 = 15%)
    adjusted_returns = adjusted_gains.copy()

    # For stopped trades at THIS stop level, replace with simulated stop loss return
    # The stop loss return = -stop_level% with efficiency slippage subtracted
    # This matches how calculate_adjusted_gains works: gain - efficiency
    # So a stopped trade at 20% stop with 5% slippage = -20% - 5% = -25%
    # In decimal: -0.25
    stop_loss_return = -(stop_level + efficiency) / 100.0
    adjusted_returns[stopped_mask] = stop_loss_return

    # Calculate metrics from adjusted returns (in decimal format)
    winners = adjusted_returns > 0
    losers = adjusted_returns < 0

    win_count = winners.sum()
    loss_count = losers.sum()

    # Win %
    win_pct = (win_count / total_trades) * 100

    # Max Loss % (stopped out / total × 100)
    max_loss_pct = (stopped_count / total_trades) * 100

    # Avg Gain % and Median Gain % (from adjusted returns converted to percentage)
    adjusted_returns_pct = adjusted_returns * 100
    avg_gain_pct = adjusted_returns_pct.mean()
    median_gain_pct = adjusted_returns_pct.median()

    # EV % (expected value = average return, same as Avg Gain %)
    ev_pct = avg_gain_pct

    # Calculate avg_win and avg_loss for profit ratio
    avg_win = adjusted_returns[winners].mean() if win_count > 0 else 0.0
    avg_loss = adjusted_returns[losers].mean() if loss_count > 0 else 0.0  # Negative

    # Profit Ratio: avg_win / abs(avg_loss)
    profit_ratio = avg_win / abs(avg_loss) if avg_loss != 0 else None

    # Diagnostic logging for 100% stop level (comparing with baseline)
    if stop_level == 100:
        logger.info(
            "STATISTICS DIAGNOSTIC: 100%% stop level details - "
            "stopped_count=%d, win_count=%d, loss_count=%d, "
            "avg_win=%.6f, avg_loss=%.6f, profit_ratio=%.4f",
            stopped_count,
            win_count,
            loss_count,
            avg_win,
            avg_loss,
            profit_ratio or 0,
        )

    # Edge %: (profit_ratio + 1) × win_rate - 1 (as percentage)
    # win_rate is a decimal (0-1)
    win_rate = win_count / total_trades
    if profit_ratio is not None:
        edge_decimal = (profit_ratio + 1) * win_rate - 1
        edge_pct = edge_decimal * 100
    else:
        edge_decimal = None
        edge_pct = None

    # EG %: Geometric growth formula at full Kelly stake
    eg_pct = calculate_expected_growth(win_rate, profit_ratio)

    # Full Kelly (Stop Adj): edge / profit_ratio / (stop_level/100) * 100
    # edge_decimal is in decimal form (0.13 = 13%), result should be percentage
    if profit_ratio is not None and profit_ratio > 0 and edge_decimal is not None:
        stop_decimal = stop_level / 100.0
        full_kelly = (edge_decimal / profit_ratio / stop_decimal) * 100  # Convert to percentage
        half_kelly = full_kelly / 2
        quarter_kelly = full_kelly / 4
    else:
        full_kelly = None
        half_kelly = None
        quarter_kelly = None

    return {
        "Stop %": stop_level,
        "Win %": win_pct,
        "EV %": ev_pct,
        "Avg Gain %": avg_gain_pct,
        "Median Gain %": median_gain_pct,
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
    adjustment_params: AdjustmentParams,
) -> pd.DataFrame:
    """Simulate entry offsets with recalculated MAE/MFE and returns.

    For SHORT trades:
    - Negative offset: price dropped before entry (need mfe_pct >= abs(offset))
    - Positive offset: price rose before entry (need mae_pct >= offset)

    Args:
        df: Trade data with gain_pct, mae_pct, and mfe_pct columns.
        mapping: Column mapping configuration.
        adjustment_params: Adjustment parameters (stop_loss, efficiency).

    Returns:
        DataFrame with rows for each offset level and performance metrics.
    """
    rows = []
    gain_col = mapping.gain_pct
    mae_col = mapping.mae_pct
    mfe_col = mapping.mfe_pct

    for offset in OFFSET_LEVELS:
        row = _calculate_offset_level_row(
            df, gain_col, mae_col, mfe_col, offset, adjustment_params
        )
        rows.append(row)

    return pd.DataFrame(rows)


def _calculate_offset_level_row(
    df: pd.DataFrame,
    gain_col: str,
    mae_col: str,
    mfe_col: str,
    offset: int,
    adjustment_params: AdjustmentParams,
) -> dict:
    """Calculate metrics for a single offset level.

    Args:
        df: Trade data DataFrame.
        gain_col: Column name for gain percentage (decimal).
        mae_col: Column name for MAE percentage (percentage points).
        mfe_col: Column name for MFE percentage (percentage points).
        offset: Offset level (e.g., -10 for -10%, 20 for +20%).
        adjustment_params: Adjustment parameters (stop_loss, efficiency).

    Returns:
        Dictionary with metrics for this offset level.
    """
    stop_loss = adjustment_params.stop_loss
    efficiency = adjustment_params.efficiency

    # Filter qualifying trades based on offset
    if offset < 0:
        # Negative offset: price dropped before entry
        # Include if mfe_pct >= abs(offset) (price dropped enough to reach lower entry)
        qualifying_mask = df[mfe_col] >= abs(offset)
    elif offset > 0:
        # Positive offset: price rose before entry
        # Include if mae_pct >= offset (price rose enough to reach higher entry)
        qualifying_mask = df[mae_col] >= offset
    else:
        # 0% offset: all trades qualify
        qualifying_mask = pd.Series([True] * len(df), index=df.index)

    qualifying_df = df[qualifying_mask].copy()
    num_trades = len(qualifying_df)

    # Handle empty qualifying trades
    if num_trades == 0:
        return {
            "Offset %": offset,
            "# of Trades": 0,
            "Win %": 0.0,
            "Avg. Gain %": None,
            "Median Gain %": None,
            "EV %": None,
            "Profit Ratio": None,
            "Edge %": None,
            "EG %": None,
            "Max Loss %": 0.0,
            "Total Gain %": 0.0,
        }

    # Recalculate MAE/MFE from new entry point
    original_entry = 1.0
    new_entry = original_entry * (1 + offset / 100)

    # Derive price levels from original percentages
    # For SHORT trades:
    # mae_pct = how much price rose (bad for short) -> highest_price = 1.0 * (1 + mae_pct/100)
    # mfe_pct = how much price dropped (good for short) -> lowest_price = 1.0 * (1 - mfe_pct/100)
    highest_price = original_entry * (1 + qualifying_df[mae_col] / 100)
    lowest_price = original_entry * (1 - qualifying_df[mfe_col] / 100)

    # Recalculate from new entry
    # For SHORT: MAE is how much higher price went above entry (bad)
    new_mae_pct = (highest_price - new_entry) / new_entry * 100

    # Calculate adjusted returns from the offset entry point
    # Use ORIGINAL gains (not pre-adjusted) to derive exit price
    # This ensures we apply adjustments consistently from this entry point
    original_gains = qualifying_df[gain_col].astype(float)

    # exit_price = 1.0 * (1 - original_gain) for SHORT
    exit_price = original_entry * (1 - original_gains)

    # new_return = (new_entry - exit_price) / new_entry for SHORT
    # This is the raw return from the offset entry point
    raw_returns = (new_entry - exit_price) / new_entry

    # Convert to percentage for adjustment calculation (matching AdjustmentParams format)
    raw_returns_pct = raw_returns * 100

    # Apply stop-loss: if new_mae > stop_loss, trade is stopped
    # (matching AdjustmentParams: mae <= stop_loss means NOT stopped)
    stopped_mask = new_mae_pct > stop_loss
    stopped_count = stopped_mask.sum()

    # Stopped trades get -stop_loss return (in percentage)
    raw_returns_pct[stopped_mask] = -stop_loss

    # Clip any losses to not exceed stop_loss (matching AdjustmentParams)
    # This ensures consistency even if MAE data is inconsistent
    raw_returns_pct = raw_returns_pct.clip(lower=-stop_loss)

    # Apply efficiency deduction (slippage) to all trades
    adjusted_returns_pct = raw_returns_pct - efficiency

    # Convert back to decimal for metric calculations
    adjusted_returns = adjusted_returns_pct / 100

    # Calculate metrics
    winners_mask = adjusted_returns > 0
    losers_mask = adjusted_returns < 0

    win_count = winners_mask.sum()
    loss_count = losers_mask.sum()

    # Win %
    win_pct = (win_count / num_trades) * 100 if num_trades > 0 else 0.0

    # Max Loss % (stopped out / qualifying × 100)
    max_loss_pct = (stopped_count / num_trades) * 100 if num_trades > 0 else 0.0

    # Avg. Gain % and Median Gain %
    avg_gain_pct = adjusted_returns_pct.mean()
    median_gain_pct = adjusted_returns_pct.median()

    # EV % (expected value = avg return, same as Avg. Gain %)
    ev_pct = avg_gain_pct

    # Total Gain %
    total_gain_pct = adjusted_returns_pct.sum()

    # Calculate avg_win and avg_loss for profit ratio
    avg_win = adjusted_returns[winners_mask].mean() if win_count > 0 else 0.0
    avg_loss = adjusted_returns[losers_mask].mean() if loss_count > 0 else 0.0  # Negative

    # Profit Ratio: avg_win / abs(avg_loss)
    profit_ratio = avg_win / abs(avg_loss) if avg_loss != 0 else None

    # Edge %: (profit_ratio + 1) × win_rate - 1 (as percentage)
    win_rate = win_count / num_trades if num_trades > 0 else 0.0
    if profit_ratio is not None:
        edge_decimal = (profit_ratio + 1) * win_rate - 1
        edge_pct = edge_decimal * 100
    else:
        edge_pct = None

    # EG %: Geometric growth formula at full Kelly stake
    eg_pct = calculate_expected_growth(win_rate, profit_ratio)

    return {
        "Offset %": offset,
        "# of Trades": num_trades,
        "Win %": win_pct,
        "Avg. Gain %": avg_gain_pct,
        "Median Gain %": median_gain_pct,
        "EV %": ev_pct,
        "Profit Ratio": profit_ratio,
        "Edge %": edge_pct,
        "EG %": eg_pct,
        "Max Loss %": max_loss_pct,
        "Total Gain %": total_gain_pct,
    }


# Partial profit target levels (fixed)
SCALING_TARGET_LEVELS = [5, 10, 15, 20, 25, 30, 35, 40]

# Profit/Loss chance bucket levels (fixed)
PROFIT_LOSS_BUCKETS = [5, 10, 15, 20, 25, 30, 35, 40]


def calculate_scaling_table(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    scale_out_pct: float,
) -> pd.DataFrame:
    """Compare blended partial-profit returns vs full hold.

    Analyzes taking partial profits at various MFE targets vs. holding to close.

    Args:
        df: Trade data with adjusted_gain_pct and mfe_pct columns.
        mapping: Column mapping configuration.
        scale_out_pct: Fraction of position to scale out (0-1, e.g., 0.5 for 50%).

    Returns:
        DataFrame with rows for each target level comparing blended vs full hold.
        Columns: Partial Target %, % of Trades, Avg Blended Return %,
                 Avg Full Hold Return %, Total Blended Return %,
                 Total Full Hold Return %, Blended Win %, Full Hold Win %,
                 Blended Profit Ratio, Full Hold Profit Ratio,
                 Blended Edge %, Full Hold Edge %, Blended EG %, Full Hold EG %
    """
    rows = []
    mfe_col = mapping.mfe_pct

    for target in SCALING_TARGET_LEVELS:
        row = _calculate_scaling_row(df, mfe_col, target, scale_out_pct)
        rows.append(row)

    return pd.DataFrame(rows)


def _calculate_scaling_row(
    df: pd.DataFrame,
    mfe_col: str,
    target: int,
    scale_out_pct: float,
) -> dict:
    """Calculate metrics for a single scaling target level.

    Args:
        df: Trade data DataFrame.
        mfe_col: Column name for MFE percentage (percentage points).
        target: Target level for partial profit (e.g., 10 for 10%).
        scale_out_pct: Fraction of position to scale out (0-1).

    Returns:
        Dictionary with metrics for this target level.
    """
    total_trades = len(df)

    # Handle empty data
    if total_trades == 0:
        return {
            "Partial Target %": target,
            "% of Trades": 0.0,
            "Avg Blended Return %": None,
            "Avg Full Hold Return %": None,
            "Total Blended Return %": 0.0,
            "Total Full Hold Return %": 0.0,
            "Blended Win %": 0.0,
            "Full Hold Win %": 0.0,
            "Blended Profit Ratio": None,
            "Full Hold Profit Ratio": None,
            "Blended Edge %": None,
            "Full Hold Edge %": None,
            "Blended EG %": None,
            "Full Hold EG %": None,
        }

    # Full hold returns (in decimal, e.g., 0.10 = 10%)
    full_hold_returns = df["adjusted_gain_pct"].copy()

    # Calculate blended returns for each trade
    # If mfe_pct >= target: blended = scale_out_pct * (target/100) + (1-scale_out_pct) * full_hold
    # If mfe_pct < target: blended = full_hold (couldn't reach target, so no scaling)
    target_reached_mask = df[mfe_col] >= target
    reached_count = target_reached_mask.sum()

    # Calculate blended returns
    blended_returns = full_hold_returns.copy()
    # For trades that reached the target, apply the blending formula
    # target/100 converts target (percentage points) to decimal
    blended_returns[target_reached_mask] = (
        scale_out_pct * (target / 100.0)
        + (1 - scale_out_pct) * full_hold_returns[target_reached_mask]
    )

    # % of Trades reaching target
    pct_of_trades = (reached_count / total_trades) * 100

    # Convert returns to percentages for display
    blended_returns_pct = blended_returns * 100
    full_hold_returns_pct = full_hold_returns * 100

    # Calculate averages
    avg_blended = blended_returns_pct.mean()
    avg_full_hold = full_hold_returns_pct.mean()

    # Calculate totals
    total_blended = blended_returns_pct.sum()
    total_full_hold = full_hold_returns_pct.sum()

    # Calculate metrics for blended returns
    blended_metrics = _calculate_return_metrics(blended_returns)

    # Calculate metrics for full hold returns
    full_hold_metrics = _calculate_return_metrics(full_hold_returns)

    return {
        "Partial Target %": target,
        "% of Trades": pct_of_trades,
        "Avg Blended Return %": avg_blended,
        "Avg Full Hold Return %": avg_full_hold,
        "Total Blended Return %": total_blended,
        "Total Full Hold Return %": total_full_hold,
        "Blended Win %": blended_metrics["win_pct"],
        "Full Hold Win %": full_hold_metrics["win_pct"],
        "Blended Profit Ratio": blended_metrics["profit_ratio"],
        "Full Hold Profit Ratio": full_hold_metrics["profit_ratio"],
        "Blended Edge %": blended_metrics["edge_pct"],
        "Full Hold Edge %": full_hold_metrics["edge_pct"],
        "Blended EG %": blended_metrics["eg_pct"],
        "Full Hold EG %": full_hold_metrics["eg_pct"],
    }


def _calculate_cover_row(
    df: pd.DataFrame,
    mae_col: str,
    threshold: int,
    cover_pct: float,
) -> dict:
    """Calculate metrics for a single cover threshold level.

    Args:
        df: Trade data DataFrame.
        mae_col: Column name for MAE percentage (percentage points).
        threshold: Threshold level for partial cover (e.g., 10 for 10%).
        cover_pct: Fraction of position to cover (0-1).

    Returns:
        Dictionary with metrics for this threshold level.
    """
    total_trades = len(df)

    # Handle empty data
    if total_trades == 0:
        return {
            "Partial Cover %": threshold,
            "% of Trades": 0.0,
            "Avg Blended Return %": None,
            "Avg Full Hold Return %": None,
            "Total Blended Return %": 0.0,
            "Total Full Hold Return %": 0.0,
            "Blended Win %": 0.0,
            "Full Hold Win %": 0.0,
            "Blended Profit Ratio": None,
            "Full Hold Profit Ratio": None,
            "Blended Edge %": None,
            "Full Hold Edge %": None,
            "Blended EG %": None,
            "Full Hold EG %": None,
        }

    # Full hold returns (in decimal, e.g., 0.10 = 10%)
    full_hold_returns = df["adjusted_gain_pct"].copy()

    # Calculate blended returns for each trade
    # If mae_pct >= threshold: blended = cover_pct * (-threshold/100) + (1-cover_pct) * full_hold
    # If mae_pct < threshold: blended = full_hold (threshold not reached, no cover)
    threshold_reached_mask = df[mae_col] >= threshold
    reached_count = threshold_reached_mask.sum()

    # Calculate blended returns
    blended_returns = full_hold_returns.copy()
    # For trades that reached the threshold, apply the blending formula
    # Cover at a loss: -threshold/100 converts threshold to negative decimal
    blended_returns[threshold_reached_mask] = (
        cover_pct * (-threshold / 100.0)
        + (1 - cover_pct) * full_hold_returns[threshold_reached_mask]
    )

    # % of Trades reaching threshold
    pct_of_trades = (reached_count / total_trades) * 100

    # Convert returns to percentages for display
    blended_returns_pct = blended_returns * 100
    full_hold_returns_pct = full_hold_returns * 100

    # Calculate averages
    avg_blended = blended_returns_pct.mean()
    avg_full_hold = full_hold_returns_pct.mean()

    # Calculate totals
    total_blended = blended_returns_pct.sum()
    total_full_hold = full_hold_returns_pct.sum()

    # Calculate metrics for blended returns
    blended_metrics = _calculate_return_metrics(blended_returns)

    # Calculate metrics for full hold returns
    full_hold_metrics = _calculate_return_metrics(full_hold_returns)

    return {
        "Partial Cover %": threshold,
        "% of Trades": pct_of_trades,
        "Avg Blended Return %": avg_blended,
        "Avg Full Hold Return %": avg_full_hold,
        "Total Blended Return %": total_blended,
        "Total Full Hold Return %": total_full_hold,
        "Blended Win %": blended_metrics["win_pct"],
        "Full Hold Win %": full_hold_metrics["win_pct"],
        "Blended Profit Ratio": blended_metrics["profit_ratio"],
        "Full Hold Profit Ratio": full_hold_metrics["profit_ratio"],
        "Blended Edge %": blended_metrics["edge_pct"],
        "Full Hold Edge %": full_hold_metrics["edge_pct"],
        "Blended EG %": blended_metrics["eg_pct"],
        "Full Hold EG %": full_hold_metrics["eg_pct"],
    }


def calculate_partial_cover_table(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    cover_pct: float,
) -> pd.DataFrame:
    """Compare blended partial-cover returns vs full hold.

    Analyzes covering part of a short position at various MAE thresholds vs. holding to close.

    Args:
        df: Trade data with adjusted_gain_pct and mae_pct columns.
        mapping: Column mapping configuration.
        cover_pct: Fraction of position to cover (0-1, e.g., 0.5 for 50%).

    Returns:
        DataFrame with rows for each threshold level comparing blended vs full hold.
        Columns: Partial Cover %, % of Trades, Avg Blended Return %,
                 Avg Full Hold Return %, Total Blended Return %,
                 Total Full Hold Return %, Blended Win %, Full Hold Win %,
                 Blended Profit Ratio, Full Hold Profit Ratio,
                 Blended Edge %, Full Hold Edge %, Blended EG %, Full Hold EG %
    """
    rows = []
    mae_col = mapping.mae_pct

    for threshold in SCALING_TARGET_LEVELS:
        row = _calculate_cover_row(df, mae_col, threshold, cover_pct)
        rows.append(row)

    return pd.DataFrame(rows)


def _calculate_return_metrics(returns: pd.Series) -> dict:
    """Calculate win %, profit ratio, edge %, and EG % from returns.

    Args:
        returns: Series of returns in decimal form (e.g., 0.10 = 10%).

    Returns:
        Dictionary with win_pct, profit_ratio, edge_pct, eg_pct.
    """
    total = len(returns)
    if total == 0:
        return {
            "win_pct": 0.0,
            "profit_ratio": None,
            "edge_pct": None,
            "eg_pct": None,
        }

    winners_mask = returns > 0
    losers_mask = returns < 0

    win_count = winners_mask.sum()
    loss_count = losers_mask.sum()

    # Win %
    win_pct = (win_count / total) * 100
    win_rate = win_count / total  # decimal for calculations

    # Avg win and avg loss
    avg_win = returns[winners_mask].mean() if win_count > 0 else 0.0
    avg_loss = returns[losers_mask].mean() if loss_count > 0 else 0.0  # Negative

    # Profit Ratio: avg_win / abs(avg_loss)
    profit_ratio = avg_win / abs(avg_loss) if avg_loss != 0 else None

    # Edge %: (profit_ratio + 1) * win_rate - 1
    if profit_ratio is not None:
        edge_decimal = (profit_ratio + 1) * win_rate - 1
        edge_pct = edge_decimal * 100
    else:
        edge_pct = None

    # EG %: Geometric growth formula at full Kelly stake
    eg_pct = calculate_expected_growth(win_rate, profit_ratio)

    return {
        "win_pct": win_pct,
        "profit_ratio": profit_ratio,
        "edge_pct": edge_pct,
        "eg_pct": eg_pct,
    }


def calculate_profit_chance_table(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    adjustment_params: AdjustmentParams,
) -> pd.DataFrame:
    """Calculate profit chance metrics for trades reaching MFE thresholds.

    For each profit threshold, analyzes trades where MFE >= threshold:
    - Chance of reaching the next profit level
    - Chance of hitting max loss (MAE > stop_loss)
    - Win %, Profit Ratio, Edge %, EG % for trades in each bucket

    Args:
        df: Trade data with gain_pct, mae_pct, and mfe_pct columns.
        mapping: Column mapping configuration.
        adjustment_params: Adjustment parameters (stop_loss, efficiency).

    Returns:
        DataFrame with rows for each profit bucket and metrics.
        Columns: Profit Reached %, # of Trades, Chance of Next %,
                 Chance of Max Loss %, Win %, Profit Ratio, Edge %, EG %
    """
    rows = []
    gain_col = mapping.gain_pct
    mae_col = mapping.mae_pct
    mfe_col = mapping.mfe_pct
    stop_loss = adjustment_params.stop_loss

    for i, threshold in enumerate(PROFIT_LOSS_BUCKETS):
        # Determine next threshold (None if last bucket)
        next_threshold = (
            PROFIT_LOSS_BUCKETS[i + 1] if i + 1 < len(PROFIT_LOSS_BUCKETS) else None
        )

        row = _calculate_profit_chance_row(
            df, mfe_col, mae_col, gain_col, threshold, next_threshold, stop_loss
        )
        rows.append(row)

    return pd.DataFrame(rows)


def _calculate_profit_chance_row(
    df: pd.DataFrame,
    mfe_col: str,
    mae_col: str,
    gain_col: str,
    threshold: int,
    next_threshold: int | None,
    stop_loss: float,
) -> dict:
    """Calculate metrics for a single profit chance bucket.

    Args:
        df: Trade data DataFrame.
        mfe_col: Column name for MFE percentage (percentage points).
        mae_col: Column name for MAE percentage (percentage points).
        gain_col: Column name for gain percentage (decimal).
        threshold: Current profit threshold (e.g., 10 for 10%).
        next_threshold: Next profit threshold, or None if last bucket.
        stop_loss: Stop loss level (percentage points).

    Returns:
        Dictionary with metrics for this profit bucket.
    """
    # Filter trades where MFE >= threshold
    bucket_mask = df[mfe_col] >= threshold
    bucket_df = df[bucket_mask]
    num_trades = len(bucket_df)

    # Handle empty bucket
    if num_trades == 0:
        return {
            "Profit Reached %": threshold,
            "# of Trades": 0,
            "Chance of Next %": 0.0,
            "Chance of Max Loss %": 0.0,
            "Win %": 0.0,
            "Profit Ratio": None,
            "Edge %": None,
            "EG %": None,
        }

    # Chance of Next %: count reaching next bucket / count in current bucket
    if next_threshold is not None:
        next_mask = bucket_df[mfe_col] >= next_threshold
        next_count = next_mask.sum()
        chance_of_next = (next_count / num_trades) * 100
    else:
        # Last bucket - no next threshold
        chance_of_next = 0.0

    # Chance of Max Loss %: count where mae_pct > stop_loss / count in bucket
    max_loss_mask = bucket_df[mae_col] > stop_loss
    max_loss_count = max_loss_mask.sum()
    chance_of_max_loss = (max_loss_count / num_trades) * 100

    # Calculate Win %, Profit Ratio, Edge %, EG % for trades in this bucket
    # Use gain_pct (decimal format) for calculations
    gains = bucket_df[gain_col].astype(float)

    winners_mask = gains > 0
    losers_mask = gains < 0

    win_count = winners_mask.sum()
    loss_count = losers_mask.sum()

    # Win %
    win_pct = (win_count / num_trades) * 100
    win_rate = win_count / num_trades  # decimal for calculations

    # Avg win and avg loss (in decimal form)
    avg_win = gains[winners_mask].mean() if win_count > 0 else 0.0
    avg_loss = gains[losers_mask].mean() if loss_count > 0 else 0.0  # Negative

    # Profit Ratio: avg_win / abs(avg_loss)
    profit_ratio = avg_win / abs(avg_loss) if avg_loss != 0 else None

    # Edge %: (profit_ratio + 1) * win_rate - 1
    if profit_ratio is not None:
        edge_decimal = (profit_ratio + 1) * win_rate - 1
        edge_pct = edge_decimal * 100
    else:
        edge_pct = None

    # EG %: Geometric growth formula at full Kelly stake
    eg_pct = calculate_expected_growth(win_rate, profit_ratio)

    return {
        "Profit Reached %": threshold,
        "# of Trades": num_trades,
        "Chance of Next %": chance_of_next,
        "Chance of Max Loss %": chance_of_max_loss,
        "Win %": win_pct,
        "Profit Ratio": profit_ratio,
        "Edge %": edge_pct,
        "EG %": eg_pct,
    }
