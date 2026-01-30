"""Unit tests for statistics calculations."""

import pandas as pd
import pytest

from src.core.models import ColumnMapping
from src.core.statistics import (
    calculate_mae_before_win,
    calculate_mfe_before_loss,
    calculate_offset_table,
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


class TestCalculateStopLossTable:
    """Tests for the calculate_stop_loss_table function."""

    def test_basic_data(self, sample_mapping):
        """Test stop loss table with basic data."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, -0.05, 0.20, -0.15],  # 2 win, 2 loss
                "mae_pct": [5.0, 25.0, 8.0, 35.0],  # 2 would be stopped at 20%
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, efficiency=1.0)

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

    def test_stop_levels(self, sample_mapping):
        """Test that correct stop levels are present."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, 0.20],
                "mae_pct": [5.0, 8.0],
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, efficiency=1.0)

        expected_stops = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        assert list(result["Stop %"]) == expected_stops

    def test_stop_loss_applied_correctly(self, sample_mapping):
        """Test that stop loss modifies returns."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.50, 0.50],  # Both would win 50%
                "mae_pct": [15.0, 25.0],  # One stopped at 20%, one not
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, efficiency=1.0)

        row_20 = result[result["Stop %"] == 20].iloc[0]
        assert row_20["Max Loss %"] == 50.0  # 1 of 2 stopped

    def test_stop_loss_return_calculation(self, sample_mapping):
        """Test that stopped out trades use correct return."""
        # Trade with mae_pct=25% will be stopped at 20% stop level
        # Return should be -0.20 (stop level / 100 * efficiency)
        df = pd.DataFrame(
            {
                "gain_pct": [0.30],  # Would have won 30%
                "mae_pct": [25.0],  # MAE >= 20%, so stopped at 20%
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, efficiency=1.0)

        row_20 = result[result["Stop %"] == 20].iloc[0]
        # Trade was stopped, so Win % should be 0
        assert row_20["Win %"] == 0.0
        assert row_20["Max Loss %"] == 100.0  # 1 of 1 stopped

        row_30 = result[result["Stop %"] == 30].iloc[0]
        # At 30% stop, mae_pct 25% < 30%, so not stopped - original gain used
        assert row_30["Win %"] == 100.0  # Trade wins with original 30% gain
        assert row_30["Max Loss %"] == 0.0  # Not stopped

    def test_efficiency_applied(self, sample_mapping):
        """Test that efficiency reduces stop loss magnitude."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10],
                "mae_pct": [25.0],  # Will be stopped at 20%
            }
        )
        result_100 = calculate_stop_loss_table(df, sample_mapping, efficiency=1.0)
        result_80 = calculate_stop_loss_table(df, sample_mapping, efficiency=0.8)

        # At 20% stop with 100% efficiency: loss = -20%
        # At 20% stop with 80% efficiency: loss = -20% * 0.8 = -16%
        # Both should show same stopped count
        row_100 = result_100[result_100["Stop %"] == 20].iloc[0]
        row_80 = result_80[result_80["Stop %"] == 20].iloc[0]

        assert row_100["Max Loss %"] == row_80["Max Loss %"]  # Both stopped
        # Win % should be the same (both are losses)
        assert row_100["Win %"] == row_80["Win %"]

    def test_win_percentage_calculation(self, sample_mapping):
        """Test Win % calculation: winners / total × 100."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, 0.20, -0.05, -0.10],  # 2 winners, 2 losers
                "mae_pct": [5.0, 8.0, 3.0, 4.0],  # None stopped at any level
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, efficiency=1.0)

        # At any stop level where no trades are stopped, Win % = 50%
        row_10 = result[result["Stop %"] == 10].iloc[0]
        assert row_10["Win %"] == pytest.approx(50.0, rel=0.01)

    def test_profit_ratio_calculation(self, sample_mapping):
        """Test Profit Ratio calculation: avg_win / abs(avg_loss)."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.20, 0.10, -0.05, -0.05],  # avg_win=0.15, avg_loss=-0.05
                "mae_pct": [5.0, 5.0, 3.0, 3.0],  # None stopped
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, efficiency=1.0)

        row_10 = result[result["Stop %"] == 10].iloc[0]
        # Profit Ratio = 0.15 / 0.05 = 3.0
        assert row_10["Profit Ratio"] == pytest.approx(3.0, rel=0.01)

    def test_edge_percentage_calculation(self, sample_mapping):
        """Test Edge % calculation: (profit_ratio + 1) × win_rate - 1."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.20, 0.20, -0.10, -0.10],  # 50% win rate
                "mae_pct": [5.0, 5.0, 3.0, 3.0],  # None stopped
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, efficiency=1.0)

        row_10 = result[result["Stop %"] == 10].iloc[0]
        # win_rate = 0.5
        # avg_win = 0.20, avg_loss = -0.10
        # profit_ratio = 0.20 / 0.10 = 2.0
        # edge = (2.0 + 1) * 0.5 - 1 = 0.5 = 50%
        assert row_10["Edge %"] == pytest.approx(50.0, rel=0.01)

    def test_max_loss_percentage(self, sample_mapping):
        """Test Max Loss % calculation: stopped / total × 100."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, 0.10, 0.10, 0.10],
                "mae_pct": [15.0, 25.0, 35.0, 45.0],  # Different MAE levels
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, efficiency=1.0)

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

    def test_kelly_calculations(self, sample_mapping):
        """Test Kelly position sizing calculations."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.20, 0.20, -0.10, -0.10],  # 50% win rate
                "mae_pct": [5.0, 5.0, 3.0, 3.0],  # None stopped
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, efficiency=1.0)

        row_20 = result[result["Stop %"] == 20].iloc[0]
        # win_rate = 0.5, profit_ratio = 2.0
        # edge = (2.0 + 1) * 0.5 - 1 = 0.5 (as decimal)
        # Full Kelly (Stop Adj) = edge / profit_ratio / (stop_level/100)
        # Full Kelly = 0.5 / 2.0 / 0.20 = 1.25
        full_kelly = row_20["Full Kelly (Stop Adj)"]
        assert full_kelly == pytest.approx(1.25, rel=0.01)
        assert row_20["Half Kelly (Stop Adj)"] == pytest.approx(full_kelly / 2, rel=0.01)
        assert row_20["Quarter Kelly (Stop Adj)"] == pytest.approx(full_kelly / 4, rel=0.01)

    def test_empty_dataframe(self, sample_mapping):
        """Test with empty dataframe."""
        df = pd.DataFrame(
            {
                "gain_pct": [],
                "mae_pct": [],
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, efficiency=1.0)

        assert len(result) == 10  # Should still have 10 rows
        # All metrics should be 0 or None
        assert result["Win %"].iloc[0] == 0.0 or pd.isna(result["Win %"].iloc[0])

    def test_all_winners(self, sample_mapping):
        """Test with only winning trades."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, 0.20, 0.30],
                "mae_pct": [5.0, 5.0, 5.0],  # None stopped at 10%+
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, efficiency=1.0)

        row_10 = result[result["Stop %"] == 10].iloc[0]
        assert row_10["Win %"] == 100.0

    def test_all_losers(self, sample_mapping):
        """Test with only losing trades."""
        df = pd.DataFrame(
            {
                "gain_pct": [-0.10, -0.20, -0.30],
                "mae_pct": [5.0, 5.0, 5.0],  # None stopped
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, efficiency=1.0)

        row_10 = result[result["Stop %"] == 10].iloc[0]
        assert row_10["Win %"] == 0.0

    def test_eg_formula(self, sample_mapping):
        """Test EG % (Expected Growth) formula calculation."""
        # Create a dataset with known expected values
        df = pd.DataFrame(
            {
                "gain_pct": [0.20, 0.20, -0.10, -0.10],  # 50% win rate
                "mae_pct": [5.0, 5.0, 3.0, 3.0],  # None stopped
            }
        )
        result = calculate_stop_loss_table(df, sample_mapping, efficiency=1.0)

        # Verify EG % column exists and has expected value
        assert "EG %" in result.columns
        row_10 = result[result["Stop %"] == 10].iloc[0]
        # EG formula: win_rate - (1 - win_rate) / profit_ratio
        # With 50% win rate, PR=2: EG = 0.5 - 0.5 / 2 = 0.5 - 0.25 = 0.25 = 25%
        assert row_10["EG %"] == pytest.approx(25.0, rel=0.01)


# =============================================================================
# Tests for calculate_offset_table
# =============================================================================


class TestCalculateOffsetTable:
    """Tests for the calculate_offset_table function."""

    def test_basic_data(self, sample_mapping):
        """Test offset table with basic data."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, -0.05, 0.15],
                "mae_pct": [5.0, 30.0, 10.0],
                "mfe_pct": [15.0, 8.0, 25.0],
            }
        )
        result = calculate_offset_table(df, sample_mapping, stop_loss=20.0, efficiency=1.0)

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

    def test_offset_levels(self, sample_mapping):
        """Test that correct offset levels are present."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10],
                "mae_pct": [50.0],
                "mfe_pct": [50.0],
            }
        )
        result = calculate_offset_table(df, sample_mapping, stop_loss=20.0, efficiency=1.0)

        expected_offsets = [-20, -10, 0, 10, 20, 30, 40]
        assert list(result["Offset %"]) == expected_offsets

    def test_zero_offset_includes_all(self, sample_mapping):
        """Test that 0% offset includes all trades."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10, -0.05],
                "mae_pct": [5.0, 30.0],
                "mfe_pct": [15.0, 8.0],
            }
        )
        result = calculate_offset_table(df, sample_mapping, stop_loss=20.0, efficiency=1.0)
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
        result = calculate_offset_table(df, sample_mapping, stop_loss=30.0, efficiency=1.0)
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
        result = calculate_offset_table(df, sample_mapping, stop_loss=30.0, efficiency=1.0)
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
        result = calculate_offset_table(df, sample_mapping, stop_loss=50.0, efficiency=1.0)

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
        result = calculate_offset_table(df, sample_mapping, stop_loss=50.0, efficiency=1.0)

        # At -10% offset, should have 1 trade
        row_minus10 = result[result["Offset %"] == -10].iloc[0]
        assert row_minus10["# of Trades"] == 1

    def test_stop_loss_applied_to_adjusted_mae(self, sample_mapping):
        """Test that stop loss is applied to recalculated MAE."""
        # After offset, if new_mae >= stop_loss, trade is stopped
        df = pd.DataFrame(
            {
                "gain_pct": [0.10],
                "mae_pct": [50.0],  # qualifies for all positive offsets
                "mfe_pct": [50.0],  # qualifies for all negative offsets
            }
        )
        result = calculate_offset_table(df, sample_mapping, stop_loss=20.0, efficiency=1.0)

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
        result = calculate_offset_table(df, sample_mapping, stop_loss=50.0, efficiency=1.0)

        # At 0% offset (no filtering), Win % = 2/3 * 100 = 66.67%
        row_0 = result[result["Offset %"] == 0].iloc[0]
        assert row_0["Win %"] == pytest.approx(66.67, rel=0.01)

    def test_empty_qualifying_trades(self, sample_mapping):
        """Test handling when no trades qualify for an offset."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10],
                "mae_pct": [5.0],  # Doesn't qualify for +20% offset
                "mfe_pct": [5.0],  # Doesn't qualify for -10% offset
            }
        )
        result = calculate_offset_table(df, sample_mapping, stop_loss=20.0, efficiency=1.0)

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
        result = calculate_offset_table(df, sample_mapping, stop_loss=50.0, efficiency=1.0)

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
        result = calculate_offset_table(df, sample_mapping, stop_loss=50.0, efficiency=1.0)

        # Profit Ratio = 0.20 / 0.10 = 2.0
        row_0 = result[result["Offset %"] == 0].iloc[0]
        assert row_0["Profit Ratio"] == pytest.approx(2.0, rel=0.01)

    def test_efficiency_applied(self, sample_mapping):
        """Test efficiency is applied to stopped trades."""
        df = pd.DataFrame(
            {
                "gain_pct": [0.10],
                "mae_pct": [25.0],  # Will be stopped at 20%
                "mfe_pct": [10.0],
            }
        )
        # At 0% offset, mae=25% >= 20% stop, so stopped
        # With 80% efficiency, loss = -20% * 0.8 = -16%
        result = calculate_offset_table(df, sample_mapping, stop_loss=20.0, efficiency=0.8)

        row_0 = result[result["Offset %"] == 0].iloc[0]
        # Trade is stopped, so Win % = 0
        assert row_0["Win %"] == 0.0
        # Avg Gain should be -16%
        assert row_0["Avg. Gain %"] == pytest.approx(-16.0, rel=0.01)


# =============================================================================
# Tests for calculate_scaling_table
# =============================================================================


class TestCalculateScalingTable:
    """Tests for the calculate_scaling_table function."""

    def test_basic_data(self, sample_mapping):
        """Test scaling table with basic data."""
        df = pd.DataFrame({
            "adjusted_gain_pct": [0.10, 0.20, -0.05],
            "mfe_pct": [15.0, 8.0, 3.0],
        })
        result = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.5)

        assert len(result) == 8  # 8 target levels
        assert "Partial Target %" in result.columns
        assert "% of Trades" in result.columns

    def test_target_levels(self, sample_mapping):
        """Test correct target levels."""
        df = pd.DataFrame({
            "adjusted_gain_pct": [0.10],
            "mfe_pct": [50.0],
        })
        result = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.5)

        targets = result["Partial Target %"].tolist()
        assert targets == [5, 10, 15, 20, 25, 30, 35, 40]

    def test_percent_of_trades(self, sample_mapping):
        """Test % of trades reaching target."""
        df = pd.DataFrame({
            "adjusted_gain_pct": [0.10, 0.10, 0.10],
            "mfe_pct": [8.0, 12.0, 22.0],  # 1 at 10%, 2 at 10+%, 3 total
        })
        result = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.5)

        row_10 = result[result["Partial Target %"] == 10].iloc[0]
        assert row_10["% of Trades"] == pytest.approx(66.67, rel=0.01)  # 2/3

    def test_blended_return_calculation(self, sample_mapping):
        """Test blended return formula."""
        df = pd.DataFrame({
            "adjusted_gain_pct": [0.20],  # 20% full hold return
            "mfe_pct": [15.0],  # Reaches 10% target
        })
        result = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.5)

        row_10 = result[result["Partial Target %"] == 10].iloc[0]
        # blended = 0.5 * 0.10 + 0.5 * 0.20 = 0.05 + 0.10 = 0.15 = 15%
        assert row_10["Avg Blended Return %"] == pytest.approx(15.0, rel=0.01)

    def test_no_target_reached_uses_full_hold(self, sample_mapping):
        """Test that trades not reaching target use full hold."""
        df = pd.DataFrame({
            "adjusted_gain_pct": [0.20],  # 20% return
            "mfe_pct": [8.0],  # Only reaches 8%, not 10%
        })
        result = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.5)

        row_10 = result[result["Partial Target %"] == 10].iloc[0]
        # Trade didn't reach 10% target, so blended = full hold
        assert row_10["Avg Blended Return %"] == pytest.approx(20.0, rel=0.01)

    def test_all_columns_present(self, sample_mapping):
        """Test that all required columns are present."""
        df = pd.DataFrame({
            "adjusted_gain_pct": [0.10, -0.05],
            "mfe_pct": [15.0, 5.0],
        })
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
        df = pd.DataFrame({
            "adjusted_gain_pct": [0.15, 0.25],  # 15% and 25% returns
            "mfe_pct": [50.0, 50.0],  # Both reach all targets
        })
        result = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.5)

        # Full hold average should always be (15 + 25) / 2 = 20%
        for _, row in result.iterrows():
            assert row["Avg Full Hold Return %"] == pytest.approx(20.0, rel=0.01)

    def test_total_returns(self, sample_mapping):
        """Test total return calculations."""
        df = pd.DataFrame({
            "adjusted_gain_pct": [0.10, 0.20],  # 10% and 20% returns
            "mfe_pct": [15.0, 15.0],  # Both reach 10% target
        })
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
        df = pd.DataFrame({
            "adjusted_gain_pct": [0.05, -0.15],  # 1 win, 1 loss (full hold)
            "mfe_pct": [20.0, 20.0],  # Both reach 10% target
        })
        result = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.5)

        row_10 = result[result["Partial Target %"] == 10].iloc[0]
        # Full hold: 1 win (5%), 1 loss (-15%) -> 50% win rate
        assert row_10["Full Hold Win %"] == pytest.approx(50.0, rel=0.01)
        # Blended trade 1: 0.5*10 + 0.5*5 = 7.5% (win)
        # Blended trade 2: 0.5*10 + 0.5*(-15) = 5 - 7.5 = -2.5% (loss)
        assert row_10["Blended Win %"] == pytest.approx(50.0, rel=0.01)

    def test_different_scale_out_percentages(self, sample_mapping):
        """Test different scale out percentages."""
        df = pd.DataFrame({
            "adjusted_gain_pct": [0.30],  # 30% full hold return
            "mfe_pct": [20.0],  # Reaches 10% target
        })

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
        df = pd.DataFrame({
            "adjusted_gain_pct": [],
            "mfe_pct": [],
        })
        result = calculate_scaling_table(df, sample_mapping, scale_out_pct=0.5)

        # Should still have 8 rows (one for each target level)
        assert len(result) == 8
        # % of Trades should be 0 for all
        assert all(result["% of Trades"] == 0.0)

    def test_mixed_reaching_targets(self, sample_mapping):
        """Test with trades that reach different target levels."""
        df = pd.DataFrame({
            "adjusted_gain_pct": [0.10, 0.10, 0.10],
            "mfe_pct": [7.0, 12.0, 25.0],  # MFE values for each trade
        })
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
