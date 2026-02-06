"""Tests for mapping_worker module."""

import pytest
import pandas as pd
from src.core.models import ColumnMapping


def test_change_columns_computed_from_price_mapping():
    """Test that change_X_min columns are computed when price columns are mapped."""
    from src.core.mapping_worker import compute_time_change_columns

    df = pd.DataFrame({
        "trigger_price_unadjusted": [100.0, 200.0],
        "price_10m": [98.0, 204.0],  # 2% gain, -2% loss
        "price_30m": [95.0, 210.0],  # 5% gain, -5% loss
    })

    mapping = ColumnMapping(
        ticker="ticker", date="date", time="time",
        gain_pct="gain_pct", mae_pct="mae_pct", mfe_pct="mfe_pct",
        price_10_min_after="price_10m",
        price_30_min_after="price_30m",
    )

    result = compute_time_change_columns(df, mapping)

    assert "change_10_min" in result.columns
    assert "change_30_min" in result.columns
    # (100 - 98) / 100 = 0.02
    assert abs(result["change_10_min"].iloc[0] - 0.02) < 0.001
