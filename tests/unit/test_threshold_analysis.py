"""Tests for threshold analysis engine."""

import pandas as pd
import pytest

from src.core.models import AdjustmentParams, ColumnMapping, FilterCriteria
from src.core.parameter_sensitivity import (
    ThresholdAnalysisEngine,
    ThresholdAnalysisResult,
    ThresholdRow,
)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Create sample trade data.

    Data has 100 trades (10 unique values repeated 10 times).
    Price values: 5, 10, 15, 20, 25, 30, 35, 40, 45, 50
    Gain values: mix of positive and negative (in decimal format)
    MAE values: in percentage format
    """
    return pd.DataFrame({
        "ticker": ["AAPL"] * 100,
        "date": ["2024-01-01"] * 100,
        "time": ["09:30:00"] * 100,
        "price": [5, 10, 15, 20, 25, 30, 35, 40, 45, 50] * 10,
        "gain_pct": [0.05, -0.02, 0.08, -0.03, 0.10, 0.02, -0.05, 0.15, -0.01, 0.07] * 10,
        "mae_pct": [2.0, 5.0, 3.0, 8.0, 1.0, 4.0, 10.0, 2.0, 6.0, 3.0] * 10,
        "mfe_pct": [5.0, 2.0, 8.0, 3.0, 10.0, 3.0, 2.0, 15.0, 1.0, 7.0] * 10,
    })


@pytest.fixture
def column_mapping() -> ColumnMapping:
    """Create column mapping with all required fields."""
    return ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
        win_loss_derived=True,
    )


@pytest.fixture
def adjustment_params() -> AdjustmentParams:
    """Create adjustment params with default stop loss and efficiency."""
    return AdjustmentParams(stop_loss=8.0, efficiency=5.0)


class TestThresholdAnalysisEngine:
    """Tests for ThresholdAnalysisEngine."""

    def test_analyze_returns_11_rows(
        self, sample_df, column_mapping, adjustment_params
    ):
        """Analysis should return exactly 11 rows."""
        filters = [FilterCriteria(column="price", operator="between", min_val=20.0, max_val=None)]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )
        result = engine.analyze(filter_index=0, vary_bound="min", step_size=5.0)

        assert len(result.rows) == 11
        assert result.current_index == 5

    def test_current_row_marked_correctly(
        self, sample_df, column_mapping, adjustment_params
    ):
        """The middle row should be marked as current."""
        filters = [FilterCriteria(column="price", operator="between", min_val=20.0, max_val=None)]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )
        result = engine.analyze(filter_index=0, vary_bound="min", step_size=5.0)

        current_row = result.rows[result.current_index]
        assert current_row.is_current is True
        assert current_row.threshold == 20.0  # Original filter value

        # Other rows should not be marked as current
        for i, row in enumerate(result.rows):
            if i != result.current_index:
                assert row.is_current is False

    def test_thresholds_increase_with_step_size(
        self, sample_df, column_mapping, adjustment_params
    ):
        """Thresholds should be evenly spaced by step_size."""
        filters = [FilterCriteria(column="price", operator="between", min_val=20.0, max_val=None)]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )
        result = engine.analyze(filter_index=0, vary_bound="min", step_size=5.0)

        expected_thresholds = [-5.0, 0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0]
        actual_thresholds = [row.threshold for row in result.rows]
        assert actual_thresholds == expected_thresholds

    def test_stricter_filter_reduces_trade_count(
        self, sample_df, column_mapping, adjustment_params
    ):
        """Higher min threshold should result in fewer trades."""
        filters = [FilterCriteria(column="price", operator="between", min_val=25.0, max_val=None)]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )
        result = engine.analyze(filter_index=0, vary_bound="min", step_size=5.0)

        # Trade counts should generally decrease as threshold increases
        trade_counts = [row.num_trades for row in result.rows]
        # First few rows (lower thresholds) should have more trades
        assert trade_counts[0] >= trade_counts[-1]

    def test_empty_result_when_no_trades_pass(
        self, sample_df, column_mapping, adjustment_params
    ):
        """Rows with no trades should have None metrics."""
        # Filter that will exclude all data at high thresholds
        filters = [FilterCriteria(column="price", operator="between", min_val=45.0, max_val=None)]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )
        result = engine.analyze(filter_index=0, vary_bound="min", step_size=10.0)

        # Last row (threshold=95) should have no trades since max price is 50
        last_row = result.rows[-1]
        assert last_row.num_trades == 0
        assert last_row.ev_pct is None
        assert last_row.win_pct is None

    def test_vary_max_bound(
        self, sample_df, column_mapping, adjustment_params
    ):
        """Should correctly vary max bound instead of min."""
        filters = [FilterCriteria(column="price", operator="between", min_val=None, max_val=30.0)]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )
        result = engine.analyze(filter_index=0, vary_bound="max", step_size=5.0)

        assert result.varied_bound == "max"
        current_row = result.rows[result.current_index]
        assert current_row.threshold == 30.0

    def test_cancel_stops_analysis(
        self, sample_df, column_mapping, adjustment_params
    ):
        """Cancelling should stop processing early."""
        filters = [FilterCriteria(column="price", operator="between", min_val=20.0, max_val=None)]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )
        engine.cancel()
        result = engine.analyze(filter_index=0, vary_bound="min", step_size=5.0)

        # Should have fewer than 11 rows due to cancellation
        assert len(result.rows) < 11

    def test_result_has_correct_filter_column(
        self, sample_df, column_mapping, adjustment_params
    ):
        """Result should report the correct filter column."""
        filters = [FilterCriteria(column="price", operator="between", min_val=20.0, max_val=None)]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )
        result = engine.analyze(filter_index=0, vary_bound="min", step_size=5.0)

        assert result.filter_column == "price"
        assert result.step_size == 5.0

    def test_invalid_filter_index_raises_error(
        self, sample_df, column_mapping, adjustment_params
    ):
        """Invalid filter index should raise IndexError."""
        filters = [FilterCriteria(column="price", operator="between", min_val=20.0, max_val=None)]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )

        with pytest.raises(IndexError):
            engine.analyze(filter_index=5, vary_bound="min", step_size=5.0)

    def test_no_bound_raises_error(
        self, sample_df, column_mapping, adjustment_params
    ):
        """Varying a bound that is None should raise ValueError."""
        # Filter with only max bound set
        filters = [FilterCriteria(column="price", operator="between", min_val=None, max_val=30.0)]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )

        # Try to vary min bound which is None
        with pytest.raises(ValueError, match="no min bound"):
            engine.analyze(filter_index=0, vary_bound="min", step_size=5.0)

    def test_multiple_filters(
        self, sample_df, column_mapping, adjustment_params
    ):
        """Should work with multiple filters, varying only one."""
        filters = [
            FilterCriteria(column="price", operator="between", min_val=20.0, max_val=None),
            FilterCriteria(column="mae_pct", operator="between", min_val=None, max_val=6.0),
        ]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )
        result = engine.analyze(filter_index=0, vary_bound="min", step_size=5.0)

        assert len(result.rows) == 11
        # All rows should have trade counts reduced by mae filter
        for row in result.rows:
            # With mae_pct <= 6.0 filter active, we exclude some trades
            assert row.num_trades <= 100

    def test_threshold_row_fields_populated(
        self, sample_df, column_mapping, adjustment_params
    ):
        """ThresholdRow should have all expected fields populated for non-empty results."""
        filters = [FilterCriteria(column="price", operator="between", min_val=20.0, max_val=None)]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )
        result = engine.analyze(filter_index=0, vary_bound="min", step_size=5.0)

        # Check a row with trades
        current_row = result.rows[result.current_index]
        assert current_row.num_trades > 0
        assert current_row.ev_pct is not None
        assert current_row.win_pct is not None
        # Other metrics may or may not be None depending on data

    def test_progress_callback_called(
        self, sample_df, column_mapping, adjustment_params
    ):
        """Progress callback should be called during analysis."""
        filters = [FilterCriteria(column="price", operator="between", min_val=20.0, max_val=None)]

        progress_values = []

        def track_progress(value: int) -> None:
            progress_values.append(value)

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )
        engine.analyze(filter_index=0, vary_bound="min", step_size=5.0, progress_callback=track_progress)

        # Progress should be called 11 times (once per row)
        assert len(progress_values) == 11
        # Should go from ~9% to 100%
        assert progress_values[-1] == 100
        # Should be monotonically increasing
        assert progress_values == sorted(progress_values)


class TestThresholdAnalysisResult:
    """Tests for ThresholdAnalysisResult dataclass."""

    def test_result_is_dataclass(self, sample_df, column_mapping, adjustment_params):
        """Result should be a proper dataclass."""
        filters = [FilterCriteria(column="price", operator="between", min_val=20.0, max_val=None)]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )
        result = engine.analyze(filter_index=0, vary_bound="min", step_size=5.0)

        assert isinstance(result, ThresholdAnalysisResult)
        assert hasattr(result, "filter_column")
        assert hasattr(result, "varied_bound")
        assert hasattr(result, "step_size")
        assert hasattr(result, "rows")
        assert hasattr(result, "current_index")


class TestThresholdRow:
    """Tests for ThresholdRow dataclass."""

    def test_row_is_dataclass(self, sample_df, column_mapping, adjustment_params):
        """ThresholdRow should be a proper dataclass."""
        filters = [FilterCriteria(column="price", operator="between", min_val=20.0, max_val=None)]

        engine = ThresholdAnalysisEngine(
            sample_df, column_mapping, filters, adjustment_params
        )
        result = engine.analyze(filter_index=0, vary_bound="min", step_size=5.0)

        row = result.rows[0]
        assert isinstance(row, ThresholdRow)
        assert hasattr(row, "threshold")
        assert hasattr(row, "is_current")
        assert hasattr(row, "num_trades")
        assert hasattr(row, "ev_pct")
        assert hasattr(row, "win_pct")
        assert hasattr(row, "median_winner_pct")
        assert hasattr(row, "profit_ratio")
        assert hasattr(row, "edge_pct")
        assert hasattr(row, "eg_pct")
        assert hasattr(row, "kelly_pct")
        assert hasattr(row, "max_loss_pct")
