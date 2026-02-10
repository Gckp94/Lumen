"""Tests for breakdown metrics calculation.

Note: All gain_pct values are in DECIMAL format (0.05 = 5%)
to match the expected format in the application.
"""

import pandas as pd
import pytest

from src.core.breakdown import BreakdownCalculator
from src.core.models import AdjustmentParams


@pytest.fixture
def sample_df():
    """Create sample trade data spanning multiple years and months.

    Gains are in decimal format: 0.05 = 5%, -0.02 = -2%, etc.
    """
    return pd.DataFrame({
        "date": pd.to_datetime([
            "2023-01-15", "2023-03-20", "2023-06-10",
            "2024-02-05", "2024-02-20", "2024-07-15", "2024-11-30",
            "2025-01-10",
        ]),
        # Decimal format: 0.05 = 5%, -0.02 = -2%, etc.
        "gain_pct": [0.05, -0.02, 0.035, -0.015, 0.04, 0.02, -0.03, 0.06],
        "win_loss": ["W", "L", "W", "L", "W", "W", "L", "W"],
    })


def test_yearly_breakdown_total_gain(sample_df):
    """Test yearly total gain calculation."""
    calc = BreakdownCalculator()
    result = calc.calculate_yearly(sample_df, "date", "gain_pct", "win_loss")

    assert "2023" in result
    assert "2024" in result
    assert "2025" in result
    # 2023: 0.05 + (-0.02) + 0.035 = 0.065 -> 6.5%
    assert result["2023"]["total_gain_pct"] == pytest.approx(6.5)
    # 2024: (-0.015) + 0.04 + 0.02 + (-0.03) = 0.015 -> 1.5%
    assert result["2024"]["total_gain_pct"] == pytest.approx(1.5)


def test_yearly_breakdown_count(sample_df):
    """Test yearly trade count."""
    calc = BreakdownCalculator()
    result = calc.calculate_yearly(sample_df, "date", "gain_pct", "win_loss")

    assert result["2023"]["count"] == 3
    assert result["2024"]["count"] == 4
    assert result["2025"]["count"] == 1


def test_yearly_breakdown_win_rate(sample_df):
    """Test yearly win rate calculation."""
    calc = BreakdownCalculator()
    result = calc.calculate_yearly(sample_df, "date", "gain_pct", "win_loss")

    # 2023: 2 wins out of 3 = 66.67%
    assert result["2023"]["win_rate"] == pytest.approx(66.67, rel=0.01)
    # 2024: 2 wins out of 4 = 50%
    assert result["2024"]["win_rate"] == pytest.approx(50.0)


def test_monthly_breakdown(sample_df):
    """Test monthly breakdown for a specific year."""
    calc = BreakdownCalculator()
    result = calc.calculate_monthly(sample_df, 2024, "date", "gain_pct", "win_loss")

    assert "Feb" in result
    assert "Jul" in result
    assert "Nov" in result
    # Feb 2024: -0.015 + 0.04 = 0.025 -> 2.5%
    assert result["Feb"]["total_gain_pct"] == pytest.approx(2.5)
    assert result["Feb"]["count"] == 2


def test_get_available_years(sample_df):
    """Test year detection."""
    calc = BreakdownCalculator()
    years = calc.get_available_years(sample_df, "date")
    assert years == [2023, 2024, 2025]


def test_yearly_breakdown_flat_stake(sample_df):
    """Test yearly flat stake calculation."""
    stake = 1000.0
    calc = BreakdownCalculator(stake=stake)
    result = calc.calculate_yearly(sample_df, "date", "gain_pct", "win_loss")

    # 2023: 5% + (-2%) + 3.5% = 6.5%
    # Flat stake per trade: 1000 * 0.05 + 1000 * -0.02 + 1000 * 0.035 = 50 - 20 + 35 = 65
    assert result["2023"]["total_flat_stake"] == pytest.approx(65.0)


def test_empty_dataframe():
    """Test handling of empty DataFrame."""
    calc = BreakdownCalculator()
    empty_df = pd.DataFrame(columns=["date", "gain_pct", "win_loss"])

    yearly = calc.calculate_yearly(empty_df, "date", "gain_pct", "win_loss")
    assert yearly == {}

    monthly = calc.calculate_monthly(empty_df, 2024, "date", "gain_pct", "win_loss")
    assert monthly == {}

    years = calc.get_available_years(empty_df, "date")
    assert years == []


def test_monthly_breakdown_no_data_for_year(sample_df):
    """Test monthly breakdown when no data exists for the year."""
    calc = BreakdownCalculator()
    result = calc.calculate_monthly(sample_df, 2022, "date", "gain_pct", "win_loss")
    assert result == {}


def test_monthly_breakdown_avg_winner_loser(sample_df):
    """Test monthly breakdown includes avg winner/loser."""
    calc = BreakdownCalculator()
    result = calc.calculate_monthly(sample_df, 2024, "date", "gain_pct", "win_loss")

    # Feb 2024 has trades: -0.015 (L) -> -1.5%, 0.04 (W) -> 4%
    assert "avg_winner_pct" in result["Feb"]
    assert "avg_loser_pct" in result["Feb"]
    assert result["Feb"]["avg_winner_pct"] == pytest.approx(4.0)
    assert result["Feb"]["avg_loser_pct"] == pytest.approx(-1.5)


def test_yearly_breakdown_avg_winner_loser(sample_df):
    """Test yearly breakdown includes avg winner/loser."""
    calc = BreakdownCalculator()
    result = calc.calculate_yearly(sample_df, "date", "gain_pct", "win_loss")

    # 2024 has trades: -0.015 (L), 0.04 (W), 0.02 (W), -0.03 (L)
    # Winners: 4%, 2% -> avg = 3%
    # Losers: -1.5%, -3% -> avg = -2.25%
    assert "avg_winner_pct" in result["2024"]
    assert "avg_loser_pct" in result["2024"]
    assert result["2024"]["avg_winner_pct"] == pytest.approx(3.0)
    assert result["2024"]["avg_loser_pct"] == pytest.approx(-2.25)


def test_yearly_breakdown_ev_pct(sample_df: pd.DataFrame) -> None:
    """Test that yearly breakdown calculates EV % correctly."""
    calculator = BreakdownCalculator()
    result = calculator.calculate_yearly(sample_df, "date", "gain_pct", None)

    # 2023: gains are 0.05, -0.02, 0.035 (5%, -2%, 3.5%) = 6.5% total / 3 trades = 2.167% EV
    assert "ev_pct" in result["2023"]
    assert result["2023"]["ev_pct"] == pytest.approx(2.167, rel=0.01)

    # 2024: gains are -0.015, 0.04, 0.02, -0.03 (-1.5%, 4%, 2%, -3%) = 1.5% total / 4 trades = 0.375% EV
    assert "ev_pct" in result["2024"]
    assert result["2024"]["ev_pct"] == pytest.approx(0.375, rel=0.01)


def test_win_loss_without_column():
    """Test win rate calculation when no win_loss column is provided."""
    df = pd.DataFrame({
        "date": pd.to_datetime(["2023-01-15", "2023-03-20", "2023-06-10"]),
        # Decimal format: 0.05 = 5%, -0.02 = -2%, 0.035 = 3.5%
        "gain_pct": [0.05, -0.02, 0.035],
    })
    calc = BreakdownCalculator()
    result = calc.calculate_yearly(df, "date", "gain_pct", None)

    # Win rate should be based on positive gains: 2 out of 3
    assert result["2023"]["win_rate"] == pytest.approx(66.67, rel=0.01)


def test_yearly_breakdown_max_drawdown(sample_df):
    """Test yearly max drawdown calculation."""
    calc = BreakdownCalculator()
    result = calc.calculate_yearly(sample_df, "date", "gain_pct", "win_loss")

    # 2023 has trades: 0.05, -0.02, 0.035 (decimal) -> 5%, -2%, 3.5% (percentage)
    # With stake=1000, start_capital=10000:
    # Equity: start 10000, then 10050, 10030, 10065
    # Drawdown occurs after first trade: peak 10050, low 10030, DD = 20 (0.199% of peak)
    assert "max_dd_pct" in result["2023"]
    assert "max_dd_dollars" in result["2023"]
    assert result["2023"]["max_dd_dollars"] == pytest.approx(20.0)


def test_custom_stake_and_capital():
    """Test with custom stake and start capital."""
    df = pd.DataFrame({
        "date": pd.to_datetime(["2023-01-15"]),
        # Decimal format: 0.10 = 10%
        "gain_pct": [0.10],
        "win_loss": ["W"],
    })
    stake = 2000.0
    start_capital = 20000.0
    calc = BreakdownCalculator(stake=stake, start_capital=start_capital)
    result = calc.calculate_yearly(df, "date", "gain_pct", "win_loss")

    # 10% gain on $2000 stake = $200
    assert result["2023"]["total_flat_stake"] == pytest.approx(200.0)


def test_yearly_max_dd_uses_full_equity_context():
    """Test that yearly max DD uses accumulated equity from prior years.

    This tests the "full history context" behavior where yearly drawdowns
    are calculated relative to all-time peaks, not fresh starts.
    """
    # Create data where equity grows significantly in year 1,
    # then has a drawdown in year 2
    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2023-01-15",  # Big win - equity goes from 10000 to 10500
            "2024-01-15",  # Loss - equity goes from 10500 to 10300
        ]),
        # Decimal format: 0.50 = 50%, -0.20 = -20%
        "gain_pct": [0.50, -0.20],  # 50% win then 20% loss
        "win_loss": ["W", "L"],
    })

    stake = 1000.0
    start_capital = 10000.0
    calc = BreakdownCalculator(stake=stake, start_capital=start_capital)
    result = calc.calculate_yearly(df, "date", "gain_pct", "win_loss")

    # Year 1: Equity goes 10000 -> 10500, no drawdown
    assert result["2023"]["max_dd_dollars"] == pytest.approx(0.0)

    # Year 2: Equity goes 10500 -> 10300
    # The 200 dollar loss should be calculated relative to the all-time peak of 10500
    # (NOT relative to a fresh 10000 starting point)
    # DD = 10500 - 10300 = 200
    assert result["2024"]["max_dd_dollars"] == pytest.approx(200.0)
    # DD % = (200 / 10500) * 100 = 1.905%
    assert result["2024"]["max_dd_pct"] == pytest.approx(1.905, rel=0.01)


def test_monthly_max_dd_uses_full_equity_context():
    """Test that monthly max DD uses accumulated equity from prior months/years.

    Similar to yearly test but for monthly breakdown.
    """
    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2024-01-15",  # Big win in January
            "2024-02-15",  # Loss in February
        ]),
        # Decimal format
        "gain_pct": [0.50, -0.20],  # 50% win then 20% loss
        "win_loss": ["W", "L"],
    })

    stake = 1000.0
    start_capital = 10000.0
    calc = BreakdownCalculator(stake=stake, start_capital=start_capital)
    result = calc.calculate_monthly(df, 2024, "date", "gain_pct", "win_loss")

    # January: Equity goes 10000 -> 10500, no drawdown
    assert result["Jan"]["max_dd_dollars"] == pytest.approx(0.0)

    # February: Equity goes 10500 -> 10300
    # DD = 200 (relative to all-time peak of 10500)
    assert result["Feb"]["max_dd_dollars"] == pytest.approx(200.0)
    # DD % = (200 / 10500) * 100 = 1.905%
    assert result["Feb"]["max_dd_pct"] == pytest.approx(1.905, rel=0.01)


def test_yearly_breakdown_with_adjustment_params():
    """Test yearly breakdown uses adjusted gains when adjustment_params provided.

    When efficiency adjustment is applied, gains are reduced, resulting in
    different equity curves and lower total gains.
    """
    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2023-01-15", "2023-03-20", "2023-06-10",
        ]),
        # Decimal format: 0.10 = 10%, -0.05 = -5%, 0.08 = 8%
        "gain_pct": [0.10, -0.05, 0.08],
        "mae": [5.0, 8.0, 3.0],  # MAE in percentage format (5%, 8%, 3%)
        "win_loss": ["W", "L", "W"],
    })

    # Without adjustments: total = 10% + (-5%) + 8% = 13%
    calc_raw = BreakdownCalculator(stake=1000.0, start_capital=10000.0)
    result_raw = calc_raw.calculate_yearly(df, "date", "gain_pct", "win_loss")
    assert result_raw["2023"]["total_gain_pct"] == pytest.approx(13.0)

    # With 5% efficiency adjustment: gains reduced by 5% each
    # Trade 1: 10% - 5% = 5%
    # Trade 2: -5% - 5% = -10%
    # Trade 3: 8% - 5% = 3%
    # Total adjusted = 5% + (-10%) + 3% = -2%
    adjustment_params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
    calc_adj = BreakdownCalculator(
        stake=1000.0,
        start_capital=10000.0,
        adjustment_params=adjustment_params,
        mae_col="mae",
    )
    result_adj = calc_adj.calculate_yearly(df, "date", "gain_pct", "win_loss")
    assert result_adj["2023"]["total_gain_pct"] == pytest.approx(-2.0)

    # Flat stake with adjustment: 1000 * (-2/100) = -20
    assert result_adj["2023"]["total_flat_stake"] == pytest.approx(-20.0)


def test_monthly_breakdown_with_adjustment_params():
    """Test monthly breakdown uses adjusted gains when adjustment_params provided."""
    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2024-01-15",  # 10% gain, 5% MAE -> adjusted: 5%
            "2024-02-10",  # -5% loss, 8% MAE -> adjusted: -10%
            "2024-02-20",  # 8% gain, 3% MAE -> adjusted: 3%
        ]),
        "gain_pct": [0.10, -0.05, 0.08],
        "mae": [5.0, 8.0, 3.0],
        "win_loss": ["W", "L", "W"],
    })

    adjustment_params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
    calc = BreakdownCalculator(
        stake=1000.0,
        start_capital=10000.0,
        adjustment_params=adjustment_params,
        mae_col="mae",
    )
    result = calc.calculate_monthly(df, 2024, "date", "gain_pct", "win_loss")

    # January: 10% - 5% = 5%
    assert result["Jan"]["total_gain_pct"] == pytest.approx(5.0)

    # February: (-5% - 5%) + (8% - 5%) = -10% + 3% = -7%
    assert result["Feb"]["total_gain_pct"] == pytest.approx(-7.0)
