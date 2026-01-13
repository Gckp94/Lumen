"""Unit tests for PnLStatsTab filtered metrics calculations."""

import pandas as pd
import pytest

from src.core.app_state import AppState
from src.core.models import ColumnMapping
from src.tabs.pnl_stats import PnLStatsTab


class TestFilteredFlatStakeMetrics:
    """Tests for filtered flat stake metrics being populated after debounced calculation."""

    @pytest.fixture
    def sample_df(self) -> pd.DataFrame:
        """Create a sample DataFrame with enough trades for meaningful metrics."""
        return pd.DataFrame({
            "ticker": ["AAPL"] * 100,
            "date": pd.date_range("2024-01-01", periods=100).strftime("%Y-%m-%d").tolist(),
            "time": ["09:30:00"] * 100,
            "gain_pct": [2.0, -1.0] * 50,  # Alternating wins and losses
            "mae_pct": [0.5] * 100,
        })

    @pytest.fixture
    def sample_mapping(self) -> ColumnMapping:
        """Create a standard column mapping."""
        return ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            win_loss_derived=True,
        )

    def test_filtered_flat_stake_metrics_populated_after_debounce(
        self, qtbot, sample_df, sample_mapping
    ):
        """Filtered flat stake metrics should be populated after debounced calculation."""
        app_state = AppState()
        app_state.baseline_df = sample_df
        app_state.column_mapping = sample_mapping

        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        # Apply a filter to trigger filtered calculation
        filtered_data = sample_df.head(50)
        app_state.filtered_df = filtered_data
        # Emit signal to trigger calculation (as filter engine would)
        app_state.filtered_data_updated.emit(filtered_data)

        # Wait for debounced equity calculation (Animation.DEBOUNCE_METRICS + buffer)
        qtbot.wait(500)

        # Filtered metrics should have flat stake data
        filtered = app_state.filtered_metrics
        assert filtered is not None, "Filtered metrics should not be None"
        assert filtered.flat_stake_pnl is not None, "flat_stake_pnl should be populated"
        assert filtered.flat_stake_max_dd is not None, "flat_stake_max_dd should be populated"

        tab.cleanup()

    def test_filtered_kelly_metrics_populated_after_debounce(
        self, qtbot, sample_df, sample_mapping
    ):
        """Filtered Kelly metrics should be populated after debounced calculation."""
        app_state = AppState()
        app_state.baseline_df = sample_df
        app_state.column_mapping = sample_mapping

        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        # Apply a filter to trigger filtered calculation
        filtered_data = sample_df.head(50)
        app_state.filtered_df = filtered_data
        # Emit signal to trigger calculation (as filter engine would)
        app_state.filtered_data_updated.emit(filtered_data)

        # Wait for debounced equity calculation
        qtbot.wait(500)

        # Filtered metrics should have Kelly data
        filtered = app_state.filtered_metrics
        assert filtered is not None, "Filtered metrics should not be None"
        assert filtered.kelly_pnl is not None, "kelly_pnl should be populated"
        assert filtered.kelly_max_dd is not None, "kelly_max_dd should be populated"

        tab.cleanup()
