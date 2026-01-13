"""Tests for MetricsCalculator - Edge % calculation fix."""

import pandas as pd
import pytest

from src.core.metrics import MetricsCalculator


def test_edge_formula() -> None:
    """Edge % = ((R:R + 1) × Win Rate) - 1"""
    # Example: 60% win rate, R:R = 1.5
    # Edge = ((1.5 + 1) * 0.60) - 1 = (2.5 * 0.60) - 1 = 1.5 - 1 = 0.5 = 50%
    df = pd.DataFrame({
        "gain_pct": [15.0, 12.0, 18.0, -10.0, -10.0],  # 3 wins avg 15%, 2 losses avg -10%
    })
    # Win rate = 60%, R:R = 15/10 = 1.5
    # Edge = ((1.5 + 1) * 0.60) - 1 = 0.5

    calculator = MetricsCalculator()
    metrics, _, _ = calculator.calculate(df=df, gain_col="gain_pct")

    expected_rr = 15.0 / 10.0  # 1.5
    expected_edge = ((expected_rr + 1) * 0.60) - 1  # 0.5
    assert metrics.edge == pytest.approx(expected_edge, abs=0.01)
