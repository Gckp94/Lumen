"""Unit tests for statistics calculations."""
import pytest
import pandas as pd

from src.core.statistics import (
    calculate_mae_before_win,
    calculate_mfe_before_loss,
    calculate_stop_loss_table,
    calculate_offset_table,
    calculate_scaling_table,
)
from src.core.models import ColumnMapping


@pytest.fixture
def sample_mapping():
    """Create a sample column mapping for tests."""
    return ColumnMapping(
        ticker="ticker", date="date", time="time",
        gain_pct="gain_pct", mae_pct="mae_pct", mfe_pct="mfe_pct"
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
        df = pd.DataFrame({
            "gain_pct": [0.05, 0.15, 0.25, 0.08, -0.10],  # 4 winners, 1 loser
            "adjusted_gain_pct": [0.05, 0.15, 0.25, 0.08, -0.10],
            "mae_pct": [3.0, 8.0, 12.0, 6.0, 15.0],  # MAE in percentage points
        })

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
        df = pd.DataFrame({
            "gain_pct": [-0.05, -0.10],
            "adjusted_gain_pct": [-0.05, -0.10],
            "mae_pct": [5.0, 10.0],
        })

        result = calculate_mae_before_win(df, sample_mapping)
        # Empty table when no winners
        assert len(result) == 0 or result.iloc[0]["# of Plays"] == 0

    def test_mae_probabilities(self, sample_mapping):
        """Test MAE probability calculations."""
        df = pd.DataFrame({
            "adjusted_gain_pct": [0.05, 0.06, 0.07, 0.08],  # 4 winners in >0% bucket
            "mae_pct": [3.0, 8.0, 12.0, 22.0],  # Various MAE levels
        })

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
        df = pd.DataFrame({
            "adjusted_gain_pct": [
                0.05,   # >0% bucket (0 < gain <= 10%)
                0.15,   # >10% bucket (10 < gain <= 20%)
                0.25,   # >20% bucket (20 < gain <= 30%)
                0.35,   # >30% bucket (30 < gain <= 40%)
                0.45,   # >40% bucket (40 < gain <= 50%)
                0.55,   # >50% bucket (gain > 50%)
            ],
            "mae_pct": [5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
        })

        result = calculate_mae_before_win(df, sample_mapping)

        # Overall row should have 6 trades
        assert result.iloc[0]["# of Plays"] == 6

        # Each bucket row should have 1 trade
        # Bucket order: Overall, >0%, >10%, >20%, >30%, >40%, >50%
        for i in range(1, 7):
            assert result.iloc[i]["# of Plays"] == 1

    def test_avg_and_median_calculations(self, sample_mapping):
        """Test average and median percentage calculations."""
        df = pd.DataFrame({
            "adjusted_gain_pct": [0.05, 0.08, 0.10],  # All in >0% bucket
            "mae_pct": [5.0, 5.0, 5.0],
        })

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
        df = pd.DataFrame({
            "adjusted_gain_pct": [0.05, 0.05, 0.15, 0.25],  # 2 in >0%, 1 in >10%, 1 in >20%
            "mae_pct": [5.0, 5.0, 5.0, 5.0],
        })

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
        df = pd.DataFrame({
            "adjusted_gain_pct": [0.05, 0.15, 0.25, 0.35, 0.45, 0.55],
            "mae_pct": [5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
        })

        result = calculate_mae_before_win(df, sample_mapping)

        expected_labels = ["Overall", ">0%", ">10%", ">20%", ">30%", ">40%", ">50%"]
        assert list(result["% Gain per Trade"]) == expected_labels

    def test_all_columns_present(self, sample_mapping):
        """Test that all required columns are present in output."""
        df = pd.DataFrame({
            "adjusted_gain_pct": [0.05],
            "mae_pct": [5.0],
        })

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
        df = pd.DataFrame({
            # 0.10 = 10% should be in >0% bucket (0 < gain <= 10%)
            # 0.20 = 20% should be in >10% bucket (10 < gain <= 20%)
            "adjusted_gain_pct": [0.10, 0.20, 0.30, 0.40, 0.50],
            "mae_pct": [5.0, 5.0, 5.0, 5.0, 5.0],
        })

        result = calculate_mae_before_win(df, sample_mapping)

        # 10% gain should be in >0% bucket
        bucket_0 = result[result["% Gain per Trade"] == ">0%"].iloc[0]
        assert bucket_0["# of Plays"] == 1

        # 20% gain should be in >10% bucket
        bucket_10 = result[result["% Gain per Trade"] == ">10%"].iloc[0]
        assert bucket_10["# of Plays"] == 1

    def test_empty_buckets_show_zero(self, sample_mapping):
        """Test that empty buckets still appear with zero counts."""
        df = pd.DataFrame({
            "adjusted_gain_pct": [0.05],  # Only in >0% bucket
            "mae_pct": [5.0],
        })

        result = calculate_mae_before_win(df, sample_mapping)

        # Should still have 7 rows (Overall + 6 buckets)
        assert len(result) == 7

        # Empty buckets should have 0 plays
        bucket_50 = result[result["% Gain per Trade"] == ">50%"].iloc[0]
        assert bucket_50["# of Plays"] == 0
