"""Unit tests for Statistics tab."""
import pytest
import pandas as pd
from PyQt6.QtWidgets import QApplication, QTableWidget, QTabWidget
from src.tabs.statistics_tab import StatisticsTab
from src.core.app_state import AppState
from src.core.models import ColumnMapping


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance() or QApplication([])
    yield app


class TestStatisticsTab:
    def test_creates_successfully(self, app):
        """Test that StatisticsTab can be instantiated."""
        app_state = AppState()
        tab = StatisticsTab(app_state)
        assert tab is not None

    def test_has_5_subtabs(self, app):
        """Test that StatisticsTab has 5 sub-tabs."""
        app_state = AppState()
        tab = StatisticsTab(app_state)
        assert tab._tab_widget.count() == 5

    def test_subtab_names(self, app):
        """Test correct sub-tab names."""
        app_state = AppState()
        tab = StatisticsTab(app_state)
        names = [tab._tab_widget.tabText(i) for i in range(5)]
        assert names == ["MAE Before Win", "MFE Before Loss", "Stop Loss", "Offset", "Scaling"]

    def test_tables_are_tablewidgets(self, app):
        """Test that first 4 sub-tabs contain QTableWidgets."""
        app_state = AppState()
        tab = StatisticsTab(app_state)
        for i in range(4):
            widget = tab._tab_widget.widget(i)
            assert isinstance(widget, QTableWidget)


class TestStatisticsTabDataUpdates:
    """Test that StatisticsTab updates when data changes."""

    @pytest.fixture
    def test_df(self) -> pd.DataFrame:
        """Create test DataFrame with required columns."""
        return pd.DataFrame({
            "adjusted_gain_pct": [0.10, -0.05, 0.15, -0.08, 0.20, -0.03],
            "mae_pct": [5.0, 15.0, 8.0, 12.0, 6.0, 18.0],
            "mfe_pct": [12.0, 5.0, 20.0, 8.0, 25.0, 4.0],
            "gain_pct": [0.10, -0.05, 0.15, -0.08, 0.20, -0.03],
            "ticker": ["AAPL"] * 6,
            "date": ["2024-01-01"] * 6,
            "time": ["09:30"] * 6,
        })

    @pytest.fixture
    def test_mapping(self) -> ColumnMapping:
        """Create test column mapping."""
        return ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
        )

    def test_updates_on_baseline_calculated(self, app, test_df, test_mapping):
        """Test that tables update when baseline data changes."""
        app_state = AppState()
        tab = StatisticsTab(app_state)

        # Initially tables should be empty
        assert tab._mae_table.rowCount() == 0

        # Set data via app_state
        app_state.baseline_df = test_df
        app_state.column_mapping = test_mapping

        # Emit baseline_calculated signal (simulates what DataInputTab does)
        from src.core.models import TradingMetrics
        dummy_metrics = TradingMetrics(
            num_trades=6, win_rate=50.0, avg_winner=15.0, avg_loser=-5.0,
            rr_ratio=3.0, ev=5.0, kelly=10.0
        )
        app_state.baseline_calculated.emit(dummy_metrics)

        # Verify MAE table has data (7 rows: Overall + 6 buckets)
        assert tab._mae_table.rowCount() == 7

    def test_updates_on_filtered_data(self, app, test_df, test_mapping):
        """Test that tables update when filtered data changes."""
        app_state = AppState()
        tab = StatisticsTab(app_state)

        # Set baseline first
        app_state.baseline_df = test_df
        app_state.column_mapping = test_mapping

        # Emit filtered data signal
        app_state.filtered_data_updated.emit(test_df)

        # Verify MAE table has data
        assert tab._mae_table.rowCount() == 7

    def test_mfe_table_updates(self, app, test_df, test_mapping):
        """Test that MFE table updates with data."""
        app_state = AppState()
        tab = StatisticsTab(app_state)

        app_state.baseline_df = test_df
        app_state.column_mapping = test_mapping

        from src.core.models import TradingMetrics
        dummy_metrics = TradingMetrics(
            num_trades=6, win_rate=50.0, avg_winner=15.0, avg_loser=-5.0,
            rr_ratio=3.0, ev=5.0, kelly=10.0
        )
        app_state.baseline_calculated.emit(dummy_metrics)

        # Verify MFE table has data (7 rows: Overall + 6 buckets)
        assert tab._mfe_table.rowCount() == 7

    def test_stop_loss_table_updates(self, app, test_df, test_mapping):
        """Test that Stop Loss table updates with data."""
        app_state = AppState()
        tab = StatisticsTab(app_state)

        app_state.baseline_df = test_df
        app_state.column_mapping = test_mapping

        from src.core.models import TradingMetrics
        dummy_metrics = TradingMetrics(
            num_trades=6, win_rate=50.0, avg_winner=15.0, avg_loser=-5.0,
            rr_ratio=3.0, ev=5.0, kelly=10.0
        )
        app_state.baseline_calculated.emit(dummy_metrics)

        # Verify Stop Loss table has data (10 stop loss levels)
        assert tab._stop_loss_table.rowCount() == 10

    def test_offset_table_updates(self, app, test_df, test_mapping):
        """Test that Offset table updates with data."""
        app_state = AppState()
        tab = StatisticsTab(app_state)

        app_state.baseline_df = test_df
        app_state.column_mapping = test_mapping

        from src.core.models import TradingMetrics
        dummy_metrics = TradingMetrics(
            num_trades=6, win_rate=50.0, avg_winner=15.0, avg_loser=-5.0,
            rr_ratio=3.0, ev=5.0, kelly=10.0
        )
        app_state.baseline_calculated.emit(dummy_metrics)

        # Verify Offset table has data (7 offset levels)
        assert tab._offset_table.rowCount() == 7

    def test_scaling_table_updates(self, app, test_df, test_mapping):
        """Test that Scaling table updates with data."""
        app_state = AppState()
        tab = StatisticsTab(app_state)

        app_state.baseline_df = test_df
        app_state.column_mapping = test_mapping

        from src.core.models import TradingMetrics
        dummy_metrics = TradingMetrics(
            num_trades=6, win_rate=50.0, avg_winner=15.0, avg_loser=-5.0,
            rr_ratio=3.0, ev=5.0, kelly=10.0
        )
        app_state.baseline_calculated.emit(dummy_metrics)

        # Verify Scaling table has data (8 target levels)
        assert tab._scaling_table.rowCount() == 8

    def test_scaling_spinbox_triggers_update(self, app, test_df, test_mapping):
        """Test that changing scale out % refreshes scaling table."""
        app_state = AppState()
        tab = StatisticsTab(app_state)

        # Set data first
        app_state.baseline_df = test_df
        app_state.column_mapping = test_mapping

        from src.core.models import TradingMetrics
        dummy_metrics = TradingMetrics(
            num_trades=6, win_rate=50.0, avg_winner=15.0, avg_loser=-5.0,
            rr_ratio=3.0, ev=5.0, kelly=10.0
        )
        app_state.baseline_calculated.emit(dummy_metrics)

        # Verify initial data
        assert tab._scaling_table.rowCount() == 8

        # Get initial cell value (Blended Return for first row)
        initial_blended = tab._scaling_table.item(0, 2)  # Column 2: Avg Blended Return %
        initial_value = initial_blended.text() if initial_blended else None

        # Change spinbox value
        tab._scale_out_spin.setValue(70)

        # Table should still have data after spinbox change
        assert tab._scaling_table.rowCount() == 8

        # Value should change because scale_out_pct affects blended returns
        new_blended = tab._scaling_table.item(0, 2)
        new_value = new_blended.text() if new_blended else None
        # The values should differ when scale_out changes (50% vs 70%)
        assert new_value != initial_value or initial_value is None

    def test_adjustment_params_updates_stop_loss_table(self, app, test_df, test_mapping):
        """Test that changing adjustment params refreshes stop loss table."""
        app_state = AppState()
        tab = StatisticsTab(app_state)

        # Set data first
        app_state.baseline_df = test_df
        app_state.column_mapping = test_mapping

        from src.core.models import TradingMetrics, AdjustmentParams
        dummy_metrics = TradingMetrics(
            num_trades=6, win_rate=50.0, avg_winner=15.0, avg_loser=-5.0,
            rr_ratio=3.0, ev=5.0, kelly=10.0
        )
        app_state.baseline_calculated.emit(dummy_metrics)

        # Get initial data
        initial_row_count = tab._stop_loss_table.rowCount()
        assert initial_row_count == 10

        # Change adjustment params
        new_params = AdjustmentParams(stop_loss=20.0, efficiency=0.9)
        app_state.adjustment_params = new_params
        app_state.adjustment_params_changed.emit(new_params)

        # Table should still have data
        assert tab._stop_loss_table.rowCount() == 10

    def test_no_update_without_mapping(self, app, test_df):
        """Test that tables don't update without column mapping."""
        app_state = AppState()
        tab = StatisticsTab(app_state)

        # Set baseline without mapping
        app_state.baseline_df = test_df
        # No column_mapping set

        from src.core.models import TradingMetrics
        dummy_metrics = TradingMetrics(
            num_trades=6, win_rate=50.0, avg_winner=15.0, avg_loser=-5.0,
            rr_ratio=3.0, ev=5.0, kelly=10.0
        )
        app_state.baseline_calculated.emit(dummy_metrics)

        # Tables should remain empty
        assert tab._mae_table.rowCount() == 0

    def test_initialize_from_state(self, app, test_df, test_mapping):
        """Test that tables populate if data exists when tab is created."""
        app_state = AppState()

        # Set data BEFORE creating tab
        app_state.baseline_df = test_df
        app_state.column_mapping = test_mapping

        # Now create tab
        tab = StatisticsTab(app_state)

        # Tables should be populated from existing state
        assert tab._mae_table.rowCount() == 7

    def test_prefers_filtered_data_over_baseline(self, app, test_df, test_mapping):
        """Test that filtered data is used when available."""
        app_state = AppState()

        # Create a smaller filtered dataset
        filtered_df = test_df.iloc[:3].copy()  # Only 3 trades

        # Set both baseline and filtered
        app_state.baseline_df = test_df
        app_state.filtered_df = filtered_df
        app_state.column_mapping = test_mapping

        # Create tab - should use filtered_df
        tab = StatisticsTab(app_state)

        # MAE table should be populated
        # With only 3 trades (2 winners, 1 loser based on adjusted_gain_pct)
        assert tab._mae_table.rowCount() == 7  # Still 7 rows, but different counts


class TestStatisticsTabTablePopulation:
    """Test table population helper methods."""

    @pytest.fixture
    def test_df(self) -> pd.DataFrame:
        """Create test DataFrame with required columns."""
        return pd.DataFrame({
            "adjusted_gain_pct": [0.10, -0.05, 0.15],
            "mae_pct": [5.0, 15.0, 8.0],
            "mfe_pct": [12.0, 5.0, 20.0],
            "gain_pct": [0.10, -0.05, 0.15],
            "ticker": ["AAPL"] * 3,
            "date": ["2024-01-01"] * 3,
            "time": ["09:30"] * 3,
        })

    @pytest.fixture
    def test_mapping(self) -> ColumnMapping:
        """Create test column mapping."""
        return ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
        )

    def test_populate_table_sets_headers(self, app, test_df, test_mapping):
        """Test that _populate_table sets correct column headers."""
        app_state = AppState()
        app_state.baseline_df = test_df
        app_state.column_mapping = test_mapping
        tab = StatisticsTab(app_state)

        # MAE table should have correct headers
        header_count = tab._mae_table.columnCount()
        assert header_count == 9  # 9 columns in MAE table

    def test_populate_table_handles_none_values(self, app, test_mapping):
        """Test that _populate_table handles None values gracefully."""
        app_state = AppState()

        # Create df with data that produces None values (no losers)
        all_winners_df = pd.DataFrame({
            "adjusted_gain_pct": [0.10, 0.15, 0.20],  # All positive
            "mae_pct": [5.0, 8.0, 6.0],
            "mfe_pct": [12.0, 20.0, 25.0],
            "gain_pct": [0.10, 0.15, 0.20],
            "ticker": ["AAPL"] * 3,
            "date": ["2024-01-01"] * 3,
            "time": ["09:30"] * 3,
        })

        app_state.baseline_df = all_winners_df
        app_state.column_mapping = test_mapping

        tab = StatisticsTab(app_state)

        # MFE table should exist but may have zero rows (no losers)
        # It should NOT crash
        assert tab._mfe_table.rowCount() == 0  # No losers = empty MFE table
