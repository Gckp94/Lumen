"""Tests for MetricsCalculator - Edge % calculation fix."""

import pandas as pd
import pytest

from src.core.metrics import MetricsCalculator


def test_edge_equals_ev() -> None:
    """Edge % should equal EV (expected value per trade)."""
    df = pd.DataFrame({
        "gain_pct": [0.10, 0.08, -0.05, 0.12, -0.03],  # 5 trades
    })

    calculator = MetricsCalculator()
    metrics, _, _ = calculator.calculate(
        df=df,
        gain_col="gain_pct",
    )

    # Edge should equal EV, not EV * num_trades
    assert metrics.edge == metrics.ev
