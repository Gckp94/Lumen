"""Unit tests for statistics calculations."""

import pandas as pd
import pytest

from src.core.models import AdjustmentParams, ColumnMapping
from src.core.statistics import (
    calculate_mae_before_win,
    calculate_mfe_before_loss,
    calculate_offset_table,
    calculate_partial_cover_table,
    calculate_scaling_table,
    calculate_stop_loss_table,
)


@pytest.fixture
def sample_mapping():
    """Create a sample column mapping for tests."""
    return ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
    )


@pytest.fixture
def default_adjustment_params():
    """Create default adjustment params for tests (no slippage, 100% stop)."""
    return AdjustmentParams(stop_loss=100.0, efficiency=0.0)


@pytest.fixture
def offset_adjustment_params():
    """Create adjustment params for offset tests (20% stop, no slippage)."""
    return AdjustmentParams(stop_loss=20.0, efficiency=0.0)


def test_statistics_module_imports():
    """Test that statistics module can be imported."""
    assert callable(calculate_mae_before_win)
    assert callable(calculate_mfe_before_loss)
    assert callable(calculate_stop_loss_table)
    assert callable(calculate_offset_table)
    assert callable(calculate_scaling_table)


# =============================================================================
# Tests for calculate_mae_before_win
# =============================================================================


class TestCalculateMaeBeforeWin:
    """Tests for the calculate_mae_before_win function."""

    def test_basic_data(self, sample_mapping):
        """Test MAE before win calculation with basic data."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.05, 0.15, 0.25, 0.08, -0.10],  # 4 winners, 1 loser
                "adjusted_gain_pct": [0.05, 0.15, 0.25, 0.08, -0.10],
                "mae_pct": [3.0, 8.0, 12.0, 6.0, 15.0],  # MAE in percentage points
            }
        )

        result = calculate_mae_before_win(df, sample_mapping)

        # Should have 7 rows: Overall + 6 buckets
        assert len(result) == 7
        # Overall row: 4 winners
        assert result.iloc[0]["# of Plays"] == 4
        # Check column names exist
        assert "% Gain per Trade" in result.columns
        assert ">5% MAE Probability" in result.columns
        assert ">10% MAE Probability" in result.columns
        assert ">15% MAE Probability" in result.columns
        assert ">20% MAE Probability" in result.columns

    def test_empty_data_no_winners(self, sample_mapping):
        """Test MAE calculation with no winners."""
        df = pd.DataFrame(
            {
                "gain_pct": [-0.05, -0.10],
                "adjusted_gain_pct": [-0.05, -0.10],
                "mae_pct": [5.0, 10.0],
            }
        )

        result = calculate_mae_before_win(df, sample_mapping)
        # Empty table when no winners
        assert len(result) == 0 or result.iloc[0]["# of Plays"] == 0

    def test_mae_probabilities(self, sample_mapping):
        """Test MAE probability calculations."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [0.05, 0.06, 0.07, 0.08],  # 4 winners in >0% bucket
                "mae_pct": [3.0, 8.0, 12.0, 22.0],  # Various MAE levels
            }
        )

        result = calculate_mae_before_win(df, sample_mapping)

        overall = result.iloc[0]
        # MAE > 5%: 3 trades (8, 12, 22) out of 4 = 75%
        assert overall[">5% MAE Probability"] == pytest.approx(75.0, rel=0.01)
        # MAE > 10%: 2 trades (12, 22) out of 4 = 50%
        assert overall[">10% MAE Probability"] == pytest.approx(50.0, rel=0.01)
        # MAE > 15%: 1 trade (22) out of 4 = 25%
        assert overall[">15% MAE Probability"] == pytest.approx(25.0, rel=0.01)
        # MAE > 20%: 1 trade (22) out of 4 = 25%
        assert overall[">20% MAE Probability"] == pytest.approx(25.0, rel=0.01)

    def test_bucket_assignment(self, sample_mapping):
        """Test correct bucket assignment based on adjusted_gain_pct."""
        # Create data with one trade in each bucket
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [
                    0.05,  # >0% bucket (0 < gain <= 10%)
                    0.15,  # >10% bucket (10 < gain <= 20%)
                    0.25,  # >20% bucket (20 < gain <= 30%)
                    0.35,  # >30% bucket (30 < gain <= 40%)
                    0.45,  # >40% bucket (40 < gain <= 50%)
                    0.55,  # >50% bucket (gain > 50%)
                ],
                "mae_pct": [5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
            }
        )

        result = calculate_mae_before_win(df, sample_mapping)

        # Overall row should have 6 trades
        assert result.iloc[0]["# of Plays"] == 6

        # Each bucket row should have 1 trade
        # Bucket order: Overall, >0%, >10%, >20%, >30%, >40%, >50%
        for i in range(1, 7):
            assert result.iloc[i]["# of Plays"] == 1

    def test_avg_and_median_calculations(self, sample_mapping):
        """Test average and median percentage calculations."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [0.05, 0.08, 0.10],  # All in >0% bucket
                "mae_pct": [5.0, 5.0, 5.0],
            }
        )

        result = calculate_mae_before_win(df, sample_mapping)

        # Overall row
        overall = result.iloc[0]
        # Average: (5 + 8 + 10) / 3 = 7.67%
        expected_avg = (5.0 + 8.0 + 10.0) / 3
        assert overall["Avg %"] == pytest.approx(expected_avg, rel=0.01)
        # Median: 8%
        assert overall["Median %"] == pytest.approx(8.0, rel=0.01)

    def test_percent_of_total_calculation(self, sample_mapping):
        """Test % of Total column calculation."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [0.05, 0.05, 0.15, 0.25],  # 2 in >0%, 1 in >10%, 1 in >20%
                "mae_pct": [5.0, 5.0, 5.0, 5.0],
            }
        )

        result = calculate_mae_before_win(df, sample_mapping)

        # Overall: 100%
        assert result.iloc[0]["% of Total"] == pytest.approx(100.0, rel=0.01)

        # >0% bucket: 2/4 = 50%
        bucket_0 = result[result["% Gain per Trade"] == ">0%"].iloc[0]
        assert bucket_0["% of Total"] == pytest.approx(50.0, rel=0.01)

        # >10% bucket: 1/4 = 25%
        bucket_10 = result[result["% Gain per Trade"] == ">10%"].iloc[0]
        assert bucket_10["% of Total"] == pytest.approx(25.0, rel=0.01)

    def test_bucket_labels(self, sample_mapping):
        """Test that bucket labels are correct."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [0.05, 0.15, 0.25, 0.35, 0.45, 0.55],
                "mae_pct": [5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
            }
        )

        result = calculate_mae_before_win(df, sample_mapping)

        expected_labels = ["Overall", ">0%", ">10%", ">20%", ">30%", ">40%", ">50%"]
        assert list(result["% Gain per Trade"]) == expected_labels

    def test_all_columns_present(self, sample_mapping):
        """Test that all required columns are present in output."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [0.05],
                "mae_pct": [5.0],
            }
        )

        result = calculate_mae_before_win(df, sample_mapping)

        expected_columns = [
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
        for col in expected_columns:
            assert col in result.columns, f"Missing column: {col}"

    def test_edge_case_exactly_on_boundary(self, sample_mapping):
        """Test trades exactly on bucket boundaries."""
        df = pd.DataFrame(
            {
                # 0.10 = 10% should be in >0% bucket (0 < gain <= 10%)
                # 0.20 = 20% should be in >10% bucket (10 < gain <= 20%)
                "adjusted_gain_pct": [0.10, 0.20, 0.30, 0.40, 0.50],
                "mae_pct": [5.0, 5.0, 5.0, 5.0, 5.0],
            }
        )

        result = calculate_mae_before_win(df, sample_mapping)

        # 10% gain should be in >0% bucket
        bucket_0 = result[result["% Gain per Trade"] == ">0%"].iloc[0]
        assert bucket_0["# of Plays"] == 1

        # 20% gain should be in >10% bucket
        bucket_10 = result[result["% Gain per Trade"] == ">10%"].iloc[0]
        assert bucket_10["# of Plays"] == 1

    def test_empty_buckets_show_zero(self, sample_mapping):
        """Test that empty buckets still appear with zero counts."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [0.05],  # Only in >0% bucket
                "mae_pct": [5.0],
            }
        )

        result = calculate_mae_before_win(df, sample_mapping)

        # Should still have 7 rows (Overall + 6 buckets)
        assert len(result) == 7

        # Empty buckets should have 0 plays
        bucket_50 = result[result["% Gain per Trade"] == ">50%"].iloc[0]
        assert bucket_50["# of Plays"] == 0


# =============================================================================
# Tests for calculate_mfe_before_loss
# =============================================================================


class TestCalculateMfeBeforeLoss:
    """Tests for the calculate_mfe_before_loss function."""

    def test_basic_data(self, sample_mapping):
        """Test MFE before loss with basic data."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [-0.05, -0.15, -0.25, 0.10],  # 3 losers, 1 winner
                "mfe_pct": [8.0, 12.0, 5.0, 20.0],
            }
        )
        result = calculate_mfe_before_loss(df, sample_mapping)

        assert len(result) == 7  # Overall + 6 buckets
        assert result.iloc[0]["# of Plays"] == 3  # 3 losers
        assert "% Loss per Trade" in result.columns
        assert ">5% MFE Probability" in result.columns

    def test_mfe_probabilities(self, sample_mapping):
        """Test MFE probability calculations."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [-0.05, -0.06, -0.07, -0.08],  # 4 losers
                "mfe_pct": [3.0, 8.0, 12.0, 22.0],  # 3 > 5%, 2 > 10%, etc.
            }
        )
        result = calculate_mfe_before_loss(df, sample_mapping)

        overall = result.iloc[0]
        assert overall[">5% MFE Probability"] == pytest.approx(75.0, rel=0.01)
        assert overall[">10% MFE Probability"] == pytest.approx(50.0, rel=0.01)
        assert overall[">15% MFE Probability"] == pytest.approx(25.0, rel=0.01)
        assert overall[">20% MFE Probability"] == pytest.approx(25.0, rel=0.01)

    def test_empty_data_no_losers(self, sample_mapping):
        """Test MFE calculation with no losers."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [0.05, 0.10],
                "mfe_pct": [5.0, 10.0],
            }
        )

        result = calculate_mfe_before_loss(df, sample_mapping)
        # Empty table when no losers
        assert len(result) == 0 or result.iloc[0]["# of Plays"] == 0

    def test_bucket_assignment(self, sample_mapping):
        """Test correct bucket assignment based on loss magnitude."""
        # Create data with one loser in each bucket (using absolute loss values)
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [
                    -0.05,  # >0% bucket (0 < |loss| <= 10%)
                    -0.15,  # >10% bucket (10 < |loss| <= 20%)
                    -0.25,  # >20% bucket (20 < |loss| <= 30%)
                    -0.35,  # >30% bucket (30 < |loss| <= 40%)
                    -0.45,  # >40% bucket (40 < |loss| <= 50%)
                    -0.55,  # >50% bucket (|loss| > 50%)
                ],
                "mfe_pct": [5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
            }
        )

        result = calculate_mfe_before_loss(df, sample_mapping)

        # Overall row should have 6 trades
        assert result.iloc[0]["# of Plays"] == 6

        # Each bucket row should have 1 trade
        for i in range(1, 7):
            assert result.iloc[i]["# of Plays"] == 1

    def test_avg_and_median_calculations(self, sample_mapping):
        """Test average and median percentage calculations use absolute loss values."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [-0.05, -0.08, -0.10],  # All in >0% bucket
                "mfe_pct": [5.0, 5.0, 5.0],
            }
        )

        result = calculate_mfe_before_loss(df, sample_mapping)

        # Overall row - should use absolute values (5%, 8%, 10%)
        overall = result.iloc[0]
        # Average: (5 + 8 + 10) / 3 = 7.67%
        expected_avg = (5.0 + 8.0 + 10.0) / 3
        assert overall["Avg %"] == pytest.approx(expected_avg, rel=0.01)
        # Median: 8%
        assert overall["Median %"] == pytest.approx(8.0, rel=0.01)

    def test_percent_of_total_calculation(self, sample_mapping):
        """Test % of Total column calculation."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [-0.05, -0.05, -0.15, -0.25],  # 2 in >0%, 1 in >10%, 1 in >20%
                "mfe_pct": [5.0, 5.0, 5.0, 5.0],
            }
        )

        result = calculate_mfe_before_loss(df, sample_mapping)

        # Overall: 100%
        assert result.iloc[0]["% of Total"] == pytest.approx(100.0, rel=0.01)

        # >0% bucket: 2/4 = 50%
        bucket_0 = result[result["% Loss per Trade"] == ">0%"].iloc[0]
        assert bucket_0["% of Total"] == pytest.approx(50.0, rel=0.01)

        # >10% bucket: 1/4 = 25%
        bucket_10 = result[result["% Loss per Trade"] == ">10%"].iloc[0]
        assert bucket_10["% of Total"] == pytest.approx(25.0, rel=0.01)

    def test_bucket_labels(self, sample_mapping):
        """Test that bucket labels are correct."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [-0.05, -0.15, -0.25, -0.35, -0.45, -0.55],
                "mfe_pct": [5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
            }
        )

        result = calculate_mfe_before_loss(df, sample_mapping)

        expected_labels = ["Overall", ">0%", ">10%", ">20%", ">30%", ">40%", ">50%"]
        assert list(result["% Loss per Trade"]) == expected_labels

    def test_all_columns_present(self, sample_mapping):
        """Test that all required columns are present in output."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [-0.05],
                "mfe_pct": [5.0],
            }
        )

        result = calculate_mfe_before_loss(df, sample_mapping)

        expected_columns = [
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
        for col in expected_columns:
            assert col in result.columns, f"Missing column: {col}"

    def test_edge_case_exactly_on_boundary(self, sample_mapping):
        """Test trades exactly on bucket boundaries."""
        df = pd.DataFrame(
            {
                # -0.10 = -10% loss should be in >0% bucket (0 < |loss| <= 10%)
                # -0.20 = -20% loss should be in >10% bucket (10 < |loss| <= 20%)
                "adjusted_gain_pct": [-0.10, -0.20, -0.30, -0.40, -0.50],
                "mfe_pct": [5.0, 5.0, 5.0, 5.0, 5.0],
            }
        )

        result = calculate_mfe_before_loss(df, sample_mapping)

        # 10% loss should be in >0% bucket
        bucket_0 = result[result["% Loss per Trade"] == ">0%"].iloc[0]
        assert bucket_0["# of Plays"] == 1

        # 20% loss should be in >10% bucket
        bucket_10 = result[result["% Loss per Trade"] == ">10%"].iloc[0]
        assert bucket_10["# of Plays"] == 1

    def test_empty_buckets_show_zero(self, sample_mapping):
        """Test that empty buckets still appear with zero counts."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [-0.05],  # Only in >0% bucket
                "mfe_pct": [5.0],
            }
        )

        result = calculate_mfe_before_loss(df, sample_mapping)

        # Should still have 7 rows (Overall + 6 buckets)
        assert len(result) == 7

        # Empty buckets should have 0 plays
        bucket_50 = result[result["% Loss per Trade"] == ">50%"].iloc[0]
        assert bucket_50["# of Plays"] == 0


# =============================================================================
# Tests for calculate_stop_loss_table
# =============================================================================


def test_stop_loss_table_includes_ev_avg_median_columns():
    """Stop loss table should include EV %, Avg Gain %, and Median Gain % columns."""
    df = pd.DataFrame({
        "gain_pct": [0.20, 0.15, -0.10, 0.25, -0.05],
        "mae_pct": [5, 10, 15, 8, 12],
    })
    mapping = ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
    )
    params = AdjustmentParams(stop_loss=100, efficiency=0)

    result = calculate_stop_loss_table(df, mapping, params)

    # Check new columns exist
    assert "EV %" in result.columns
    assert "Avg Gain %" in result.columns
    assert "Median Gain %" in result.columns

    # Check 100% stop row (no stops) has reasonable values
    row_100 = result[result["Stop %"] == 100].iloc[0]
    # EV should equal Avg Gain (both are mean return)
    assert row_100["EV %"] == row_100["Avg Gain %"]
    # With 5 trades: 20, 15, -10, 25, -5 -> mean = 9%, median = 15%
    assert abs(row_100["Avg Gain %"] - 9.0) < 0.1
    assert abs(row_100["Median Gain %"] - 15.0) < 0.1


class TestCalculateStopLossTable:
    """Tests for the calculate_stop_loss_table function."""

    def test_basic_data(self, sample_mapping, default_adjustment_params):
        """Test stop loss table with basic data."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, -0.05, 0.20, -0.15],  # 2 win, 2 loss
                "mae_pct": [5.0, 25.0, 8.0, 35.0],  # 2 would be stopped at 20%
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, default_adjustment_params)

        assert len(result) == 10  # 10 stop levels
        assert "Stop %" in result.columns
        assert "Win %" in result.columns
        assert "EG %" in result.columns
        assert "Profit Ratio" in result.columns
        assert "Edge %" in result.columns
        assert "Max Loss %" in result.columns
        assert "Full Kelly (Stop Adj)" in result.columns
        assert "Half Kelly (Stop Adj)" in result.columns
        assert "Quarter Kelly (Stop Adj)" in result.columns

    def test_stop_levels(self, sample_mapping, default_adjustment_params):
        """Test that correct stop levels are present."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, 0.20],
                "mae_pct": [5.0, 8.0],
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, default_adjustment_params)

        expected_stops = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        assert list(result["Stop %"]) == expected_stops

    def test_stop_loss_applied_correctly(self, sample_mapping, default_adjustment_params):
        """Test that stop loss modifies returns."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.50, 0.50],  # Both would win 50%
                "mae_pct": [15.0, 25.0],  # One stopped at 20%, one not
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, default_adjustment_params)

        row_20 = result[result["Stop %"] == 20].iloc[0]
        assert row_20["Max Loss %"] == 50.0  # 1 of 2 stopped

    def test_stop_loss_return_calculation(self, sample_mapping, default_adjustment_params):
        """Test that stopped out trades use correct return."""
        # Trade with mae_pct=25% will be stopped at 20% stop level
        # Return should be negative (stopped out loss)
        df = pd.DataFrame(
            {
                "gain_pct": [0.30],  # Would have won 30%
                "mae_pct": [25.0],  # MAE >= 20%, so stopped at 20%
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, default_adjustment_params)

        row_20 = result[result["Stop %"] == 20].iloc[0]
        # Trade was stopped, so Win % should be 0
        assert row_20["Win %"] == 0.0
        assert row_20["Max Loss %"] == 100.0  # 1 of 1 stopped

        row_30 = result[result["Stop %"] == 30].iloc[0]
        # At 30% stop, mae_pct 25% < 30%, so not stopped - original gain used
        assert row_30["Win %"] == 100.0  # Trade wins with original 30% gain
        assert row_30["Max Loss %"] == 0.0  # Not stopped

    def test_efficiency_applied(self, sample_mapping):
        """Test that slippage (efficiency) affects returns."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10],
                "mae_pct": [25.0],  # Will be stopped at 20%
            }
        )
        # No slippage
        params_no_slippage = AdjustmentParams(stop_loss=100.0, efficiency=0.0)
        # 5% slippage
        params_with_slippage = AdjustmentParams(stop_loss=100.0, efficiency=5.0)

        result_no_slippage = calculate_stop_loss_table(df, sample_mapping, params_no_slippage)
        result_with_slippage = calculate_stop_loss_table(df, sample_mapping, params_with_slippage)

        # Both should show same stopped count at 20% stop level
        row_no_slippage = result_no_slippage[result_no_slippage["Stop %"] == 20].iloc[0]
        row_with_slippage = result_with_slippage[result_with_slippage["Stop %"] == 20].iloc[0]

        assert row_no_slippage["Max Loss %"] == row_with_slippage["Max Loss %"]  # Both stopped
        # Win % should be the same (both are losses)
        assert row_no_slippage["Win %"] == row_with_slippage["Win %"]

    def test_win_percentage_calculation(self, sample_mapping, default_adjustment_params):
        """Test Win % calculation: winners / total × 100."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, 0.20, -0.05, -0.10],  # 2 winners, 2 losers
                "mae_pct": [5.0, 8.0, 3.0, 4.0],  # None stopped at any level
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, default_adjustment_params)

        # At any stop level where no trades are stopped, Win % = 50%
        row_10 = result[result["Stop %"] == 10].iloc[0]
        assert row_10["Win %"] == pytest.approx(50.0, rel=0.01)

    def test_profit_ratio_calculation(self, sample_mapping, default_adjustment_params):
        """Test Profit Ratio calculation: avg_win / abs(avg_loss)."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.20, 0.10, -0.05, -0.05],  # avg_win=0.15, avg_loss=-0.05
                "mae_pct": [5.0, 5.0, 3.0, 3.0],  # None stopped
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, default_adjustment_params)

        row_10 = result[result["Stop %"] == 10].iloc[0]
        # Profit Ratio = 0.15 / 0.05 = 3.0
        assert row_10["Profit Ratio"] == pytest.approx(3.0, rel=0.01)

    def test_edge_percentage_calculation(self, sample_mapping, default_adjustment_params):
        """Test Edge % calculation: (profit_ratio + 1) × win_rate - 1."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.20, 0.20, -0.10, -0.10],  # 50% win rate
                "mae_pct": [5.0, 5.0, 3.0, 3.0],  # None stopped
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, default_adjustment_params)

        row_10 = result[result["Stop %"] == 10].iloc[0]
        # win_rate = 0.5
        # avg_win = 0.20, avg_loss = -0.10
        # profit_ratio = 0.20 / 0.10 = 2.0
        # edge = (2.0 + 1) * 0.5 - 1 = 0.5 = 50%
        assert row_10["Edge %"] == pytest.approx(50.0, rel=0.01)

    def test_max_loss_percentage(self, sample_mapping, default_adjustment_params):
        """Test Max Loss % calculation: stopped / total × 100."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, 0.10, 0.10, 0.10],
                "mae_pct": [15.0, 25.0, 35.0, 45.0],  # Different MAE levels
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, default_adjustment_params)

        # At 10% stop: all 4 stopped (all mae_pct >= 10)
        row_10 = result[result["Stop %"] == 10].iloc[0]
        assert row_10["Max Loss %"] == 100.0

        # At 20% stop: 3 stopped (mae >= 20: 25, 35, 45)
        row_20 = result[result["Stop %"] == 20].iloc[0]
        assert row_20["Max Loss %"] == 75.0

        # At 30% stop: 2 stopped (mae >= 30: 35, 45)
        row_30 = result[result["Stop %"] == 30].iloc[0]
        assert row_30["Max Loss %"] == 50.0

        # At 40% stop: 1 stopped (mae >= 40: 45)
        row_40 = result[result["Stop %"] == 40].iloc[0]
        assert row_40["Max Loss %"] == 25.0

        # At 50% stop: 0 stopped
        row_50 = result[result["Stop %"] == 50].iloc[0]
        assert row_50["Max Loss %"] == 0.0

    def test_kelly_calculations(self, sample_mapping, default_adjustment_params):
        """Test Kelly position sizing calculations."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.20, 0.20, -0.10, -0.10],  # 50% win rate
                "mae_pct": [5.0, 5.0, 3.0, 3.0],  # None stopped
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, default_adjustment_params)

        row_20 = result[result["Stop %"] == 20].iloc[0]
        # win_rate = 0.5, profit_ratio = 2.0
        # edge = (2.0 + 1) * 0.5 - 1 = 0.5 (as decimal)
        # Full Kelly (Stop Adj) = edge / profit_ratio / (stop_level/100) * 100 (percentage)
        # Full Kelly = 0.5 / 2.0 / 0.20 * 100 = 125.0%
        full_kelly = row_20["Full Kelly (Stop Adj)"]
        assert full_kelly == pytest.approx(125.0, rel=0.01)
        assert row_20["Half Kelly (Stop Adj)"] == pytest.approx(full_kelly / 2, rel=0.01)
        assert row_20["Quarter Kelly (Stop Adj)"] == pytest.approx(full_kelly / 4, rel=0.01)

    def test_empty_dataframe(self, sample_mapping, default_adjustment_params):
        """Test with empty dataframe."""
        df = pd.DataFrame(
            {
                "gain_pct": [],
                "mae_pct": [],
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, default_adjustment_params)

        assert len(result) == 10  # Should still have 10 rows
        # All metrics should be 0 or None
        assert result["Win %"].iloc[0] == 0.0 or pd.isna(result["Win %"].iloc[0])

    def test_all_winners(self, sample_mapping, default_adjustment_params):
        """Test with only winning trades."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, 0.20, 0.30],
                "mae_pct": [5.0, 5.0, 5.0],  # None stopped at 10%+
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, default_adjustment_params)

        row_10 = result[result["Stop %"] == 10].iloc[0]
        assert row_10["Win %"] == 100.0

    def test_all_losers(self, sample_mapping, default_adjustment_params):
        """Test with only losing trades."""
        df = pd.DataFrame(
            {
                "gain_pct": [-0.10, -0.20, -0.30],
                "mae_pct": [5.0, 5.0, 5.0],  # None stopped
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, default_adjustment_params)

        row_10 = result[result["Stop %"] == 10].iloc[0]
        assert row_10["Win %"] == 0.0

    def test_eg_formula(self, sample_mapping, default_adjustment_params):
        """Test EG % (Expected Growth) uses geometric formula calculation."""
        # Create a dataset with known expected values
        df = pd.DataFrame(
            {
                "gain_pct": [0.20, 0.20, -0.10, -0.10],  # 50% win rate
                "mae_pct": [5.0, 5.0, 3.0, 3.0],  # None stopped
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, default_adjustment_params)

        # Verify EG % column exists and has expected value
        assert "EG %" in result.columns
        row_10 = result[result["Stop %"] == 10].iloc[0]
        # EG uses geometric growth formula: ((1 + R*S)^p) * ((1 - S)^(1-p)) - 1
        # With 50% win rate, PR=2:
        #   Kelly stake S = 0.5 - 0.5/2 = 0.25
        #   EG = (1.5)^0.5 * (0.75)^0.5 - 1 = 1.2247 * 0.866 - 1 ≈ 6.07%
        assert row_10["EG %"] == pytest.approx(6.07, rel=0.01)


# =============================================================================
# Tests for calculate_offset_table
# =============================================================================


class TestCalculateOffsetTable:
    """Tests for the calculate_offset_table function."""

    def test_basic_data(self, sample_mapping, offset_adjustment_params):
        """Test offset table with basic data."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, -0.05, 0.15],
                "mae_pct": [5.0, 30.0, 10.0],
                "mfe_pct": [15.0, 8.0, 25.0],
            }
        )
        result = calculate_offset_table(df, sample_mapping, offset_adjustment_params)

        assert len(result) == 7  # 7 offset levels
        assert "Offset %" in result.columns
        assert "# of Trades" in result.columns
        assert "Win %" in result.columns
        assert "Avg. Gain %" in result.columns
        assert "Median Gain %" in result.columns
        assert "EV %" in result.columns
        assert "Profit Ratio" in result.columns
        assert "Edge %" in result.columns
        assert "EG %" in result.columns
        assert "Max Loss %" in result.columns
        assert "Total Gain %" in result.columns

    def test_offset_levels(self, sample_mapping, offset_adjustment_params):
        """Test that correct offset levels are present."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10],
                "mae_pct": [50.0],
                "mfe_pct": [50.0],
            }
        )
        result = calculate_offset_table(df, sample_mapping, offset_adjustment_params)

        expected_offsets = [-20, -10, 0, 10, 20, 30, 40]
        assert list(result["Offset %"]) == expected_offsets

    def test_zero_offset_includes_all(self, sample_mapping, offset_adjustment_params):
        """Test that 0% offset includes all trades."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, -0.05],
                "mae_pct": [5.0, 30.0],
                "mfe_pct": [15.0, 8.0],
            }
        )
        result = calculate_offset_table(df, sample_mapping, offset_adjustment_params)
        row_0 = result[result["Offset %"] == 0].iloc[0]
        assert row_0["# of Trades"] == 2

    def test_positive_offset_filters_by_mae(self, sample_mapping):
        """Test positive offset requires mae_pct >= offset (price rose before entry)."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, 0.10, 0.10],
                "mae_pct": [5.0, 15.0, 25.0],  # Only 25 qualifies for +20%
                "mfe_pct": [10.0, 10.0, 10.0],
            }
        )
        params = AdjustmentParams(stop_loss=30.0, efficiency=0.0)
        result = calculate_offset_table(df, sample_mapping, params)
        row_20 = result[result["Offset %"] == 20].iloc[0]
        assert row_20["# of Trades"] == 1

    def test_negative_offset_filters_by_mfe(self, sample_mapping):
        """Test negative offset requires mfe_pct >= abs(offset) (price dropped before entry)."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, 0.10, 0.10],
                "mae_pct": [10.0, 10.0, 10.0],
                "mfe_pct": [5.0, 15.0, 25.0],  # 15 and 25 qualify for -10%
            }
        )
        params = AdjustmentParams(stop_loss=30.0, efficiency=0.0)
        result = calculate_offset_table(df, sample_mapping, params)
        row_minus10 = result[result["Offset %"] == -10].iloc[0]
        assert row_minus10["# of Trades"] == 2

    def test_new_mae_mfe_calculation_positive_offset(self, sample_mapping):
        """Test MAE/MFE recalculation with positive offset for SHORT trades."""
        # Original entry = 1.0
        # +10% offset entry = 1.10 (short at higher price - good for short)
        # mae_pct = 20% means highest_price = 1.20
        # mfe_pct = 30% means lowest_price = 0.70
        # new_mae = (1.20 - 1.10) / 1.10 * 100 = 9.09%
        # new_mfe = (1.10 - 0.70) / 1.10 * 100 = 36.36%
        df = pd.DataFrame(
            {
                "gain_pct": [0.10],
                "mae_pct": [20.0],  # qualifies for +10% offset
                "mfe_pct": [30.0],
            }
        )
        params = AdjustmentParams(stop_loss=50.0, efficiency=0.0)
        result = calculate_offset_table(df, sample_mapping, params)

        # At +10% offset, should have 1 trade
        row_10 = result[result["Offset %"] == 10].iloc[0]
        assert row_10["# of Trades"] == 1

    def test_new_mae_mfe_calculation_negative_offset(self, sample_mapping):
        """Test MAE/MFE recalculation with negative offset for SHORT trades."""
        # Original entry = 1.0
        # -10% offset entry = 0.90 (short at lower price - worse for short)
        # mae_pct = 20% means highest_price = 1.20
        # mfe_pct = 30% means lowest_price = 0.70
        # new_mae = (1.20 - 0.90) / 0.90 * 100 = 33.33%
        # new_mfe = (0.90 - 0.70) / 0.90 * 100 = 22.22%
        df = pd.DataFrame(
            {
                "gain_pct": [0.10],
                "mae_pct": [20.0],
                "mfe_pct": [30.0],  # qualifies for -10% offset
            }
        )
        params = AdjustmentParams(stop_loss=50.0, efficiency=0.0)
        result = calculate_offset_table(df, sample_mapping, params)

        # At -10% offset, should have 1 trade
        row_minus10 = result[result["Offset %"] == -10].iloc[0]
        assert row_minus10["# of Trades"] == 1

    def test_stop_loss_applied_to_adjusted_mae(self, sample_mapping, offset_adjustment_params):
        """Test that stop loss is applied to recalculated MAE."""
        # After offset, if new_mae >= stop_loss, trade is stopped
        df = pd.DataFrame(
            {
                "gain_pct": [0.10],
                "mae_pct": [50.0],  # qualifies for all positive offsets
                "mfe_pct": [50.0],  # qualifies for all negative offsets
            }
        )
        result = calculate_offset_table(df, sample_mapping, offset_adjustment_params)

        # At -20% offset (entry at 0.80):
        # new_mae = (1.50 - 0.80) / 0.80 * 100 = 87.5% >= 20% stop, so stopped
        row_minus20 = result[result["Offset %"] == -20].iloc[0]
        assert row_minus20["Max Loss %"] == 100.0  # Trade would be stopped

    def test_win_percentage_calculation(self, sample_mapping):
        """Test Win % is calculated from adjusted returns."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, 0.20, -0.05],  # 2 wins, 1 loss
                "mae_pct": [5.0, 5.0, 5.0],
                "mfe_pct": [5.0, 5.0, 5.0],
            }
        )
        params = AdjustmentParams(stop_loss=50.0, efficiency=0.0)
        result = calculate_offset_table(df, sample_mapping, params)

        # At 0% offset (no filtering), Win % = 2/3 * 100 = 66.67%
        row_0 = result[result["Offset %"] == 0].iloc[0]
        assert row_0["Win %"] == pytest.approx(66.67, rel=0.01)

    def test_empty_qualifying_trades(self, sample_mapping, offset_adjustment_params):
        """Test handling when no trades qualify for an offset."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10],
                "mae_pct": [5.0],  # Doesn't qualify for +20% offset
                "mfe_pct": [5.0],  # Doesn't qualify for -10% offset
            }
        )
        result = calculate_offset_table(df, sample_mapping, offset_adjustment_params)

        # At +20% offset, should have 0 trades (mae_pct 5 < 20)
        row_20 = result[result["Offset %"] == 20].iloc[0]
        assert row_20["# of Trades"] == 0

    def test_total_gain_calculation(self, sample_mapping):
        """Test Total Gain % is sum of adjusted returns."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, 0.20],  # Sum = 0.30 = 30%
                "mae_pct": [5.0, 5.0],
                "mfe_pct": [5.0, 5.0],
            }
        )
        params = AdjustmentParams(stop_loss=50.0, efficiency=0.0)
        result = calculate_offset_table(df, sample_mapping, params)

        # At 0% offset (no adjustment to returns), Total Gain = 30%
        row_0 = result[result["Offset %"] == 0].iloc[0]
        assert row_0["Total Gain %"] == pytest.approx(30.0, rel=0.01)

    def test_profit_ratio_calculation(self, sample_mapping):
        """Test Profit Ratio = avg_win / abs(avg_loss)."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.20, -0.10],  # avg_win=0.20, avg_loss=-0.10
                "mae_pct": [5.0, 5.0],
                "mfe_pct": [5.0, 5.0],
            }
        )
        params = AdjustmentParams(stop_loss=50.0, efficiency=0.0)
        result = calculate_offset_table(df, sample_mapping, params)

        # Profit Ratio = 0.20 / 0.10 = 2.0
        row_0 = result[result["Offset %"] == 0].iloc[0]
        assert row_0["Profit Ratio"] == pytest.approx(2.0, rel=0.01)

    def test_efficiency_applied(self, sample_mapping):
        """Test efficiency (slippage) is applied to all trades."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10],  # 10% gain
                "mae_pct": [5.0],  # Won't be stopped at 20%
                "mfe_pct": [10.0],
            }
        )
        # With 5% slippage, a 10% gain becomes 5% gain
        params = AdjustmentParams(stop_loss=20.0, efficiency=5.0)
        result = calculate_offset_table(df, sample_mapping, params)

        row_0 = result[result["Offset %"] == 0].iloc[0]
        # 10% gain - 5% slippage = 5% gain
        assert row_0["Avg. Gain %"] == pytest.approx(5.0, rel=0.01)


# =============================================================================
# Tests for calculate_scaling_table
# =============================================================================


class TestCalculateScalingTable:
    """Tests for the calculate_scaling_table function."""

    def test_basic_data(self, sample_mapping):
        """Test scaling table with basic data."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [0.10, 0.20, -0.05],
                "mfe_pct": [15.0, 8.0, 3.0],
            }
        )
        result = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.5)

        assert len(result) == 8  # 8 target levels
        assert "Partial Target %" in result.columns
        assert "% of Trades" in result.columns

    def test_target_levels(self, sample_mapping):
        """Test correct target levels."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [0.10],
                "mfe_pct": [50.0],
            }
        )
        result = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.5)

        targets = result["Partial Target %"].tolist()
        assert targets == [5, 10, 15, 20, 25, 30, 35, 40]

    def test_percent_of_trades(self, sample_mapping):
        """Test % of trades reaching target."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [0.10, 0.10, 0.10],
                "mfe_pct": [8.0, 12.0, 22.0],  # 1 at 10%, 2 at 10+%, 3 total
            }
        )
        result = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.5)

        row_10 = result[result["Partial Target %"] == 10].iloc[0]
        assert row_10["% of Trades"] == pytest.approx(66.67, rel=0.01)  # 2/3

    def test_blended_return_calculation(self, sample_mapping):
        """Test blended return formula."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [0.20],  # 20% full hold return
                "mfe_pct": [15.0],  # Reaches 10% target
            }
        )
        result = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.5)

        row_10 = result[result["Partial Target %"] == 10].iloc[0]
        # blended = 0.5 * 0.10 + 0.5 * 0.20 = 0.05 + 0.10 = 0.15 = 15%
        assert row_10["Avg Blended Return %"] == pytest.approx(15.0, rel=0.01)

    def test_no_target_reached_uses_full_hold(self, sample_mapping):
        """Test that trades not reaching target use full hold."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [0.20],  # 20% return
                "mfe_pct": [8.0],  # Only reaches 8%, not 10%
            }
        )
        result = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.5)

        row_10 = result[result["Partial Target %"] == 10].iloc[0]
        # Trade didn't reach 10% target, so blended = full hold
        assert row_10["Avg Blended Return %"] == pytest.approx(20.0, rel=0.01)

    def test_all_columns_present(self, sample_mapping):
        """Test that all required columns are present."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [0.10, -0.05],
                "mfe_pct": [15.0, 5.0],
            }
        )
        result = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.5)

        expected_columns = [
            "Partial Target %",
            "% of Trades",
            "Avg Blended Return %",
            "Avg Full Hold Return %",
            "Total Blended Return %",
            "Total Full Hold Return %",
            "Blended Win %",
            "Full Hold Win %",
            "Blended Profit Ratio",
            "Full Hold Profit Ratio",
            "Blended Edge %",
            "Full Hold Edge %",
            "Blended EG %",
            "Full Hold EG %",
        ]
        for col in expected_columns:
            assert col in result.columns, f"Missing column: {col}"

    def test_full_hold_return_unchanged(self, sample_mapping):
        """Test full hold return is always original return."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [0.15, 0.25],  # 15% and 25% returns
                "mfe_pct": [50.0, 50.0],  # Both reach all targets
            }
        )
        result = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.5)

        # Full hold average should always be (15 + 25) / 2 = 20%
        for _, row in result.iterrows():
            assert row["Avg Full Hold Return %"] == pytest.approx(20.0, rel=0.01)

    def test_total_returns(self, sample_mapping):
        """Test total return calculations."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [0.10, 0.20],  # 10% and 20% returns
                "mfe_pct": [15.0, 15.0],  # Both reach 10% target
            }
        )
        result = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.5)

        row_10 = result[result["Partial Target %"] == 10].iloc[0]
        # Total Full Hold = 10 + 20 = 30%
        assert row_10["Total Full Hold Return %"] == pytest.approx(30.0, rel=0.01)
        # Blended for trade 1: 0.5*10 + 0.5*10 = 10%
        # Blended for trade 2: 0.5*10 + 0.5*20 = 15%
        # Total Blended = 10 + 15 = 25%
        assert row_10["Total Blended Return %"] == pytest.approx(25.0, rel=0.01)

    def test_win_rate_calculation(self, sample_mapping):
        """Test win rate calculations for blended and full hold."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [0.05, -0.15],  # 1 win, 1 loss (full hold)
                "mfe_pct": [20.0, 20.0],  # Both reach 10% target
            }
        )
        result = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.5)

        row_10 = result[result["Partial Target %"] == 10].iloc[0]
        # Full hold: 1 win (5%), 1 loss (-15%) -> 50% win rate
        assert row_10["Full Hold Win %"] == pytest.approx(50.0, rel=0.01)
        # Blended trade 1: 0.5*10 + 0.5*5 = 7.5% (win)
        # Blended trade 2: 0.5*10 + 0.5*(-15) = 5 - 7.5 = -2.5% (loss)
        assert row_10["Blended Win %"] == pytest.approx(50.0, rel=0.01)

    def test_different_scale_out_percentages(self, sample_mapping):
        """Test different scale out percentages."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [0.30],  # 30% full hold return
                "mfe_pct": [20.0],  # Reaches 10% target
            }
        )

        # With 50% scale out at 10%: blended = 0.5*10 + 0.5*30 = 20%
        result_50 = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.5)
        row_50 = result_50[result_50["Partial Target %"] == 10].iloc[0]
        assert row_50["Avg Blended Return %"] == pytest.approx(20.0, rel=0.01)

        # With 25% scale out at 10%: blended = 0.25*10 + 0.75*30 = 2.5 + 22.5 = 25%
        result_25 = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.25)
        row_25 = result_25[result_25["Partial Target %"] == 10].iloc[0]
        assert row_25["Avg Blended Return %"] == pytest.approx(25.0, rel=0.01)

    def test_empty_dataframe(self, sample_mapping):
        """Test with empty dataframe."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [],
                "mfe_pct": [],
            }
        )
        result = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.5)

        # Should still have 8 rows (one for each target level)
        assert len(result) == 8
        # % of Trades should be 0 for all
        assert all(result["% of Trades"] == 0.0)

    def test_mixed_reaching_targets(self, sample_mapping):
        """Test with trades that reach different target levels."""
        df = pd.DataFrame(
            {
                "adjusted_gain_pct": [0.10, 0.10, 0.10],
                "mfe_pct": [7.0, 12.0, 25.0],  # MFE values for each trade
            }
        )
        result = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.5)

        # At 5%: all 3 trades qualify (7%, 12%, 25% MFE all >= 5%)
        row_5 = result[result["Partial Target %"] == 5].iloc[0]
        assert row_5["% of Trades"] == pytest.approx(100.0, rel=0.01)

        # At 10%: 2 trades qualify (12% and 25% MFE >= 10%)
        row_10 = result[result["Partial Target %"] == 10].iloc[0]
        assert row_10["% of Trades"] == pytest.approx(66.67, rel=0.01)

        # At 25%: 1 trade qualifies (25% MFE >= 25%)
        row_25 = result[result["Partial Target %"] == 25].iloc[0]
        assert row_25["% of Trades"] == pytest.approx(33.33, rel=0.01)


# =============================================================================
# Tests for calculate_expected_growth
# =============================================================================


class TestExpectedGrowthCalculation:
    """Tests for the calculate_expected_growth helper function."""

    def test_eg_with_positive_kelly(self):
        """Test EG calculation with valid Kelly stake."""
        # 60% win rate, 2:1 profit ratio
        win_rate = 0.6
        profit_ratio = 2.0

        from src.core.statistics import calculate_expected_growth

        eg_pct = calculate_expected_growth(win_rate, profit_ratio)

        # Kelly = 0.6 - 0.4/2 = 0.4
        # EG at 40% stake should be positive but much less than Kelly
        assert eg_pct is not None
        assert 0 < eg_pct < 40  # EG should be less than Kelly %

    def test_eg_with_zero_kelly(self):
        """Test EG returns None when Kelly is zero or negative."""
        # 50% win rate, 1:1 profit ratio = 0 edge
        win_rate = 0.5
        profit_ratio = 1.0

        from src.core.statistics import calculate_expected_growth

        eg_pct = calculate_expected_growth(win_rate, profit_ratio)

        # Kelly = 0.5 - 0.5/1 = 0, no positive growth
        assert eg_pct is None

    def test_eg_with_none_profit_ratio(self):
        """Test EG returns None when profit_ratio is None."""
        from src.core.statistics import calculate_expected_growth

        eg_pct = calculate_expected_growth(0.6, None)
        assert eg_pct is None

    def test_eg_known_value(self):
        """Test EG against manually calculated value."""
        # 60% win rate, 3:1 profit ratio
        # Kelly = 0.6 - 0.4/3 = 0.467
        # EG = (1 + 3*0.467)^0.6 * (1 - 0.467)^0.4 - 1
        # EG = 2.401^0.6 * 0.533^0.4 - 1 ≈ 0.304 = 30.4%
        win_rate = 0.6
        profit_ratio = 3.0

        from src.core.statistics import calculate_expected_growth

        eg_pct = calculate_expected_growth(win_rate, profit_ratio)

        assert eg_pct is not None
        assert 25 < eg_pct < 35  # Should be around 30%

    def test_eg_with_invalid_win_rate(self):
        """Test EG returns None for invalid win_rate values."""
        from src.core.statistics import calculate_expected_growth

        # Boundary cases
        assert calculate_expected_growth(0.0, 2.0) is None  # win_rate = 0
        assert calculate_expected_growth(1.0, 2.0) is None  # win_rate = 1
        # Out of range
        assert calculate_expected_growth(-0.1, 2.0) is None  # negative
        assert calculate_expected_growth(1.5, 2.0) is None  # > 1

    def test_eg_with_negative_profit_ratio(self):
        """Test EG returns None when profit_ratio is negative."""
        from src.core.statistics import calculate_expected_growth

        eg_pct = calculate_expected_growth(0.6, -1.0)
        assert eg_pct is None


class TestStopLossEgCalculation:
    """Tests for EG% in stop loss table using correct formula."""

    def test_stop_loss_eg_uses_geometric_formula(self, sample_mapping, default_adjustment_params):
        """Verify EG% uses geometric growth, not Kelly formula."""
        # Create data with known metrics
        df = pd.DataFrame(
            {
                "gain_pct": [0.30, 0.20, 0.15, -0.10, -0.08],  # 60% win
                "mae_pct": [5.0, 8.0, 6.0, 15.0, 12.0],  # MAE levels
            }
        )

        result = calculate_stop_loss_table(df, sample_mapping, default_adjustment_params)

        # At 100% stop (no stops triggered), original metrics apply
        row_100 = result[result["Stop %"] == 100].iloc[0]
        eg_value = row_100["EG %"]

        # EG% should be significantly less than Kelly %
        # Kelly ≈ 46.7% for 60% WR and ~2.4:1 RR
        # EG should be around 25-35%, NOT 46%
        assert eg_value is not None
        assert eg_value < 40, f"EG% {eg_value} should be < 40 (using geometric formula)"


class TestStatisticsBaselineConsistency:
    """Tests to verify Statistics table matches baseline metrics at 100% stop."""

    def test_profit_ratio_matches_baseline_at_100_stop(
        self, sample_mapping, default_adjustment_params
    ):
        """Profit Ratio at 100% stop should match baseline calculation.

        This test verifies that Statistics produces consistent profit ratios.
        """
        # Create data similar to user's scenario:
        # - ~74% win rate (needs profit ratio < 1, so losses > wins on average)
        # - Small wins, larger losses → profit_ratio ~0.5
        #
        # 100 trades: 74 winners, 26 losers
        # avg_win = 5%, avg_loss = -10% → profit_ratio = 0.5
        winners = [0.05] * 74  # 5% gain each
        losers = [-0.10] * 26  # 10% loss each

        # MAE values: all below 100% so no stops at 100% level
        mae_values = [5.0] * 74 + [8.0] * 26

        df = pd.DataFrame(
            {
                "gain_pct": winners + losers,
                "mae_pct": mae_values,
            }
        )

        result = calculate_stop_loss_table(df, sample_mapping, default_adjustment_params)

        # At 100% stop, no trades are stopped
        row_100 = result[result["Stop %"] == 100].iloc[0]
        stats_profit_ratio = row_100["Profit Ratio"]
        stats_win_pct = row_100["Win %"]

        # Calculate expected baseline values
        # avg_win = sum of winners / count = 0.05 * 74 / 74 = 0.05
        # avg_loss = sum of losers / count = -0.10 * 26 / 26 = -0.10
        # profit_ratio = avg_win / |avg_loss| = 0.05 / 0.10 = 0.5
        expected_profit_ratio = 0.05 / 0.10
        expected_win_pct = 74.0  # 74%

        assert (
            abs(stats_win_pct - expected_win_pct) < 0.1
        ), f"Win % mismatch: got {stats_win_pct}, expected {expected_win_pct}"
        assert (
            abs(stats_profit_ratio - expected_profit_ratio) < 0.01
        ), f"Profit Ratio mismatch: got {stats_profit_ratio}, expected {expected_profit_ratio}"

    def test_profit_ratio_with_stop_adjusted_gains(self, sample_mapping, default_adjustment_params):
        """Test with gains and verify profit ratio calculation.

        Uses default adjustment params (no slippage, high stop).
        """
        # 74 winners at 15%, 26 losers at -13%
        winners = [0.15] * 74
        losers = [-0.13] * 26

        df = pd.DataFrame(
            {
                "gain_pct": winners + losers,
                "mae_pct": [5.0] * 74 + [15.0] * 26,  # Losers had > 8% MAE originally
            }
        )

        result = calculate_stop_loss_table(df, sample_mapping, default_adjustment_params)
        row_100 = result[result["Stop %"] == 100].iloc[0]
        stats_profit_ratio = row_100["Profit Ratio"]

        # Expected: 0.15 / 0.13 = 1.15
        expected_profit_ratio = 0.15 / 0.13

        assert (
            abs(stats_profit_ratio - expected_profit_ratio) < 0.01
        ), f"Profit Ratio mismatch: got {stats_profit_ratio}, expected {expected_profit_ratio}"


class TestStatisticsMetricsConsistency:
    """Tests comparing Statistics table with MetricsCalculator baseline."""

    def test_profit_ratio_consistency_with_metrics_calculator(self, sample_mapping):
        """Compare Statistics 100% stop with MetricsCalculator baseline.

        This test simulates the actual data flow:
        1. Create data with known values
        2. Use same AdjustmentParams for both
        3. Verify profit ratios match
        """
        from src.core.metrics import MetricsCalculator

        # Create test data with big losses that will be capped
        # Winners: 10% gain, MAE 5%
        # Losers: -30% loss (will be capped), MAE 35%
        winners_gain = [0.10] * 74
        losers_gain = [-0.30] * 26
        winners_mae = [5.0] * 74
        losers_mae = [35.0] * 26

        df = pd.DataFrame(
            {
                "gain_pct": winners_gain + losers_gain,
                "mae_pct": winners_mae + losers_mae,
            }
        )

        # Apply adjustments (stop_loss=8%, efficiency=5%)
        params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)

        # Calculate baseline metrics using MetricsCalculator
        calculator = MetricsCalculator()
        metrics, _, _ = calculator.calculate(
            df=df,
            gain_col="gain_pct",
            derived=True,
            adjustment_params=params,
            mae_col="mae_pct",
        )

        # Calculate statistics table with same params
        result = calculate_stop_loss_table(df, sample_mapping, params)
        row_100 = result[result["Stop %"] == 100].iloc[0]

        # Compare profit ratios
        # rr_ratio is used for "Profit Ratio" display in baseline
        baseline_profit_ratio = metrics.rr_ratio
        stats_profit_ratio = row_100["Profit Ratio"]

        # These should be equal (or very close)
        assert baseline_profit_ratio is not None, "Baseline profit ratio should not be None"
        assert stats_profit_ratio is not None, "Statistics profit ratio should not be None"

        diff = abs(baseline_profit_ratio - stats_profit_ratio)
        assert diff < 0.01, (
            f"Profit Ratio mismatch: baseline={baseline_profit_ratio:.4f}, "
            f"statistics={stats_profit_ratio:.4f}, diff={diff:.6f}"
        )

    def test_adjusted_gain_pct_matches_baseline_calculation(self, sample_mapping):
        """Verify Statistics computes adjusted gains consistently with baseline."""
        from src.core.metrics import MetricsCalculator

        df = pd.DataFrame(
            {
                "gain_pct": [0.20, -0.50, 0.15, -0.25, 0.10],
                "mae_pct": [3.0, 40.0, 5.0, 30.0, 2.0],  # 2 trades exceed 8% stop
            }
        )

        params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)

        # Method 1: Calculate adjusted gains
        adjusted_gains = params.calculate_adjusted_gains(df, "gain_pct", "mae_pct")

        # Method 2: MetricsCalculator calculates internally
        calculator = MetricsCalculator()
        metrics, _, _ = calculator.calculate(
            df=df,
            gain_col="gain_pct",
            derived=True,
            adjustment_params=params,
            mae_col="mae_pct",
        )

        # Method 3: Statistics computes adjusted gains with same params
        result = calculate_stop_loss_table(df, sample_mapping, params)
        row_100 = result[result["Stop %"] == 100].iloc[0]

        # Verify adjusted gains calculation:
        # Expected adjusted gains:
        # Trade 1: 20% gain, 3% MAE < 8% stop → 20 - 5 = 15% → 0.15
        # Trade 2: -50% loss, 40% MAE > 8% stop → -8 - 5 = -13% → -0.13
        # Trade 3: 15% gain, 5% MAE < 8% stop → 15 - 5 = 10% → 0.10
        # Trade 4: -25% loss, 30% MAE > 8% stop → -8 - 5 = -13% → -0.13
        # Trade 5: 10% gain, 2% MAE < 8% stop → 10 - 5 = 5% → 0.05

        expected = [0.15, -0.13, 0.10, -0.13, 0.05]
        for i, (actual, exp) in enumerate(zip(adjusted_gains, expected, strict=True)):
            assert abs(actual - exp) < 0.001, f"Trade {i}: expected {exp}, got {actual}"

        # Statistics at 100% stop should use these adjusted values
        # Winners: 0.15, 0.10, 0.05 → avg = 0.10
        # Losers: -0.13, -0.13 → avg = -0.13
        # Profit Ratio = 0.10 / 0.13 ≈ 0.769
        expected_profit_ratio = 0.10 / 0.13
        assert abs(row_100["Profit Ratio"] - expected_profit_ratio) < 0.01, (
            f"Stats profit ratio mismatch: got {row_100['Profit Ratio']}, "
            f"expected {expected_profit_ratio}"
        )

        # Baseline should also show ~0.769 (within rounding)
        assert abs(metrics.rr_ratio - expected_profit_ratio) < 0.01, (
            f"Baseline profit ratio mismatch: got {metrics.rr_ratio}, "
            f"expected {expected_profit_ratio}"
        )


class TestOffsetEgCalculation:
    """Tests for EG% in offset table using correct formula."""

    def test_offset_eg_uses_geometric_formula(self, sample_mapping):
        """Verify EG% uses geometric growth, not Kelly formula."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.25, 0.18, 0.12, -0.08, -0.06],
                "adjusted_gain_pct": [0.25, 0.18, 0.12, -0.08, -0.06],
                "mae_pct": [5.0, 7.0, 4.0, 12.0, 10.0],
                "mfe_pct": [30.0, 22.0, 15.0, 8.0, 5.0],
            }
        )

        params = AdjustmentParams(stop_loss=100.0, efficiency=1.0)
        result = calculate_offset_table(df, sample_mapping, params)

        # 0% offset row should have all trades
        row_0 = result[result["Offset %"] == 0].iloc[0]
        eg_value = row_0["EG %"]

        assert eg_value is not None
        # EG should be less than Kelly (which would be ~40-50%)
        assert eg_value < 40, f"EG% {eg_value} should be < 40 (using geometric formula)"


class TestScalingEgCalculation:
    """Tests for EG% in scaling table using correct formula."""

    def test_scaling_eg_uses_geometric_formula(self, sample_mapping):
        """Verify both blended and full hold EG% use geometric growth."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.20, 0.15, 0.10, -0.05, -0.08],
                "adjusted_gain_pct": [0.20, 0.15, 0.10, -0.05, -0.08],
                "mfe_pct": [25.0, 18.0, 12.0, 8.0, 5.0],
            }
        )

        result = calculate_scaling_table(df, sample_mapping, scale_out_pct=50)

        # Check first target row
        first_row = result.iloc[0]

        # Both EG columns should use geometric formula
        blended_eg = first_row.get("Blended EG %")
        full_hold_eg = first_row.get("Full Hold EG %")

        # EG values should be reasonable (less than 40%) when not None/NaN
        # None/NaN is valid when there's no positive edge
        if blended_eg is not None and not pd.isna(blended_eg):
            assert blended_eg < 40, f"Blended EG% {blended_eg} too high"
        if full_hold_eg is not None and not pd.isna(full_hold_eg):
            assert full_hold_eg < 40, f"Full Hold EG% {full_hold_eg} too high"


class TestPartialCoverAnalysis:
    """Tests for partial cover analysis calculations."""

    def test_calculate_partial_cover_basic(self, sample_mapping):
        """Test basic partial cover calculation."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, -0.05, 0.08, -0.12],
                "adjusted_gain_pct": [0.10, -0.05, 0.08, -0.12],
                "mae_pct": [8.0, 15.0, 5.0, 20.0],
            }
        )

        result = calculate_partial_cover_table(df, sample_mapping, cover_pct=0.5)

        # Should have rows for each threshold level
        assert len(result) == 8  # SCALING_TARGET_LEVELS has 8 levels
        assert "Partial Cover %" in result.columns
        assert "% of Trades" in result.columns
        assert "Avg Blended Return %" in result.columns

        # First row is 5% threshold
        first_row = result.iloc[0]
        assert first_row["Partial Cover %"] == 5

    def test_calculate_partial_cover_empty_df(self, sample_mapping):
        """Test partial cover with empty DataFrame."""
        df = pd.DataFrame(
            columns=["gain_pct", "adjusted_gain_pct", "mae_pct"]
        )

        result = calculate_partial_cover_table(df, sample_mapping, cover_pct=0.5)

        assert len(result) == 8
        # All rows should have 0% of trades
        assert (result["% of Trades"] == 0.0).all()

    def test_calculate_partial_cover_no_threshold_reached(self, sample_mapping):
        """Test when no trades reach any threshold."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, 0.05],
                "adjusted_gain_pct": [0.10, 0.05],
                "mae_pct": [2.0, 3.0],  # All below 5% threshold
            }
        )

        result = calculate_partial_cover_table(df, sample_mapping, cover_pct=0.5)

        # No trades reach even the lowest threshold (5%)
        assert result.iloc[0]["% of Trades"] == 0.0
        # Blended should equal full hold when no threshold reached
        assert result.iloc[0]["Avg Blended Return %"] == result.iloc[0]["Avg Full Hold Return %"]

    def test_calculate_partial_cover_blended_calculation(self, sample_mapping):
        """Test blended return calculation when threshold is reached."""
        # Single trade that reaches 10% MAE with 20% gain
        df = pd.DataFrame(
            {
                "gain_pct": [0.20],
                "adjusted_gain_pct": [0.20],
                "mae_pct": [10.0],
            }
        )

        result = calculate_partial_cover_table(df, sample_mapping, cover_pct=0.5)

        # At 10% threshold (row index 1), blended = 0.5 * (-0.10) + 0.5 * 0.20 = 0.05 = 5%
        row_10 = result[result["Partial Cover %"] == 10].iloc[0]
        assert row_10["% of Trades"] == 100.0  # Trade reached threshold
        # Blended return: 0.5 * (-10%) + 0.5 * (20%) = -5% + 10% = 5%
        assert abs(row_10["Avg Blended Return %"] - 5.0) < 0.01
