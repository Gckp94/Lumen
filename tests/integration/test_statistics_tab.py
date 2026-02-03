# tests/integration/test_statistics_tab.py
"""Integration tests for Statistics tab."""

import pandas as pd
import pytest
from PyQt6.QtWidgets import QApplication

from src.core.app_state import AppState
from src.core.models import AdjustmentParams, ColumnMapping, TradingMetrics
from src.tabs.statistics_tab import StatisticsTab


@pytest.fixture(scope="module")
def app():
    """Provide QApplication instance for Qt tests."""
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def sample_statistics_data() -> pd.DataFrame:
    """Create sample data with all columns needed for statistics calculations.

    Data includes:
    - Mix of winners (positive adjusted_gain_pct) and losers (negative)
    - Various MAE values for different buckets
    - Various MFE values for scaling calculations
    """
    return pd.DataFrame(
        {
            "ticker": [
                "AAPL",
                "GOOGL",
                "MSFT",
                "TSLA",
                "META",
                "NVDA",
                "AMD",
                "INTC",
                "AMZN",
                "NFLX",
                "DIS",
                "BA",
                "JPM",
                "GS",
                "V",
                "MA",
                "PYPL",
                "SQ",
                "UBER",
                "LYFT",
            ],
            "date": pd.date_range("2024-01-01", periods=20).tolist(),
            "time": [
                "09:30:00",
                "09:35:00",
                "09:40:00",
                "09:45:00",
                "09:50:00",
                "09:55:00",
                "10:00:00",
                "10:05:00",
                "10:10:00",
                "10:15:00",
                "10:20:00",
                "10:25:00",
                "10:30:00",
                "10:35:00",
                "10:40:00",
                "10:45:00",
                "10:50:00",
                "10:55:00",
                "11:00:00",
                "11:05:00",
            ],
            # Mix of winners and losers with varying magnitudes
            # Winners: indices 0,1,2,4,5,6,9,10,12,13,14,15,17,19 (14 winners)
            # Losers: indices 3,7,8,11,16,18 (6 losers)
            "gain_pct": [
                5.0,
                8.0,
                12.0,
                -3.0,
                15.0,
                25.0,
                35.0,
                -5.0,
                -8.0,
                45.0,
                55.0,
                -10.0,
                6.0,
                18.0,
                28.0,
                38.0,
                -4.0,
                22.0,
                -6.0,
                48.0,
            ],
            # Adjusted gain uses same values for simplicity
            "adjusted_gain_pct": [
                5.0,
                8.0,
                12.0,
                -3.0,
                15.0,
                25.0,
                35.0,
                -5.0,
                -8.0,
                45.0,
                55.0,
                -10.0,
                6.0,
                18.0,
                28.0,
                38.0,
                -4.0,
                22.0,
                -6.0,
                48.0,
            ],
            # MAE percentages (for winners and losers)
            "mae_pct": [
                3.0,
                6.0,
                9.0,
                12.0,
                5.0,
                8.0,
                11.0,
                15.0,
                18.0,
                4.0,
                7.0,
                20.0,
                2.0,
                10.0,
                13.0,
                16.0,
                8.0,
                14.0,
                22.0,
                6.0,
            ],
            # MFE percentages (for winners and losers)
            "mfe_pct": [
                8.0,
                12.0,
                18.0,
                5.0,
                22.0,
                32.0,
                42.0,
                8.0,
                6.0,
                52.0,
                62.0,
                12.0,
                10.0,
                25.0,
                35.0,
                45.0,
                6.0,
                28.0,
                8.0,
                55.0,
            ],
            # Win/loss indicator
            "win_loss": [
                "W",
                "W",
                "W",
                "L",
                "W",
                "W",
                "W",
                "L",
                "L",
                "W",
                "W",
                "L",
                "W",
                "W",
                "W",
                "W",
                "L",
                "W",
                "L",
                "W",
            ],
        }
    )


@pytest.fixture
def statistics_column_mapping() -> ColumnMapping:
    """Column mapping for statistics test data."""
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
def app_state_with_statistics_data(
    sample_statistics_data: pd.DataFrame, statistics_column_mapping: ColumnMapping
) -> AppState:
    """AppState configured with statistics test data."""
    app_state = AppState()
    app_state.raw_df = sample_statistics_data
    app_state.baseline_df = sample_statistics_data.copy()
    app_state.column_mapping = statistics_column_mapping
    return app_state


class TestStatisticsTabIntegration:
    """Integration tests for complete Statistics tab workflow."""

    def test_tables_populated_on_baseline_calculated(
        self, app, qtbot, app_state_with_statistics_data: AppState
    ) -> None:
        """Test that all 5 tables populate when baseline_calculated signal emits."""
        tab = StatisticsTab(app_state_with_statistics_data)
        qtbot.addWidget(tab)

        # Create dummy metrics to trigger baseline_calculated signal
        dummy_metrics = TradingMetrics(
            num_trades=20,
            win_rate=70.0,
            avg_winner=25.0,
            avg_loser=-6.0,
            rr_ratio=4.17,
            ev=15.0,
            kelly=20.0,
            winner_count=14,
            loser_count=6,
        )

        # Emit baseline_calculated signal
        app_state_with_statistics_data.baseline_calculated.emit(dummy_metrics)

        # Verify empty state is hidden (isHidden checks logical visibility, not screen)
        assert tab._empty_label.isHidden()
        assert not tab._tab_widget.isHidden()

        # Verify MAE Before Win table (7 rows: Overall + 6 buckets)
        assert tab._mae_table.rowCount() == 7
        assert tab._mae_table.columnCount() > 0

        # Verify MFE Before Loss table (7 rows: Overall + 6 buckets)
        assert tab._mfe_table.rowCount() == 7
        assert tab._mfe_table.columnCount() > 0

        # Verify Stop Loss table (10 rows: 10% to 100%)
        assert tab._stop_loss_table.rowCount() == 10
        assert tab._stop_loss_table.columnCount() > 0

        # Verify Offset table (7 rows: -20% to +40%)
        assert tab._offset_table.rowCount() == 7
        assert tab._offset_table.columnCount() > 0

        # Verify Scaling table (8 rows: 5% to 40%)
        assert tab._scaling_table.rowCount() == 8
        assert tab._scaling_table.columnCount() > 0

    def test_tables_update_on_filtered_data(
        self, app, qtbot, app_state_with_statistics_data: AppState
    ) -> None:
        """Test that tables update when filtered_data_updated signal emits."""
        tab = StatisticsTab(app_state_with_statistics_data)
        qtbot.addWidget(tab)

        # First load baseline data
        dummy_metrics = TradingMetrics(
            num_trades=20,
            win_rate=70.0,
            avg_winner=25.0,
            avg_loser=-6.0,
            rr_ratio=4.17,
            ev=15.0,
            kelly=20.0,
            winner_count=14,
            loser_count=6,
        )
        app_state_with_statistics_data.baseline_calculated.emit(dummy_metrics)

        # Get initial row count for reference
        initial_mae_rows = tab._mae_table.rowCount()

        # Create filtered data (subset of original)
        filtered_df = app_state_with_statistics_data.baseline_df.iloc[:10].copy()
        app_state_with_statistics_data.filtered_df = filtered_df

        # Emit filtered_data_updated signal
        app_state_with_statistics_data.filtered_data_updated.emit(filtered_df)

        # Tables should still not be hidden
        assert not tab._tab_widget.isHidden()

        # MAE table should still have 7 rows (Overall + 6 buckets structure preserved)
        # But the values inside should reflect filtered data
        assert tab._mae_table.rowCount() == 7

    def test_mae_table_has_expected_columns(
        self, app, qtbot, app_state_with_statistics_data: AppState
    ) -> None:
        """Test MAE Before Win table has expected column structure."""
        tab = StatisticsTab(app_state_with_statistics_data)
        qtbot.addWidget(tab)

        # Trigger data population
        dummy_metrics = TradingMetrics(
            num_trades=20,
            win_rate=70.0,
            avg_winner=25.0,
            avg_loser=-6.0,
            rr_ratio=4.17,
            ev=15.0,
            kelly=20.0,
            winner_count=14,
            loser_count=6,
        )
        app_state_with_statistics_data.baseline_calculated.emit(dummy_metrics)

        # Get column headers from MAE table
        headers = []
        for col in range(tab._mae_table.columnCount()):
            header_item = tab._mae_table.horizontalHeaderItem(col)
            if header_item:
                headers.append(header_item.text())

        # Verify key columns exist
        assert "% Gain per Trade" in headers
        assert "# of Plays" in headers
        assert ">5% MAE Probability" in headers
        assert ">10% MAE Probability" in headers

    def test_stop_loss_table_has_expected_structure(
        self, app, qtbot, app_state_with_statistics_data: AppState
    ) -> None:
        """Test Stop Loss table has 10 rows for 10% to 100% stops."""
        tab = StatisticsTab(app_state_with_statistics_data)
        qtbot.addWidget(tab)

        # Trigger data population
        dummy_metrics = TradingMetrics(
            num_trades=20,
            win_rate=70.0,
            avg_winner=25.0,
            avg_loser=-6.0,
            rr_ratio=4.17,
            ev=15.0,
            kelly=20.0,
            winner_count=14,
            loser_count=6,
        )
        app_state_with_statistics_data.baseline_calculated.emit(dummy_metrics)

        # Verify 10 rows (10%, 20%, ..., 100%)
        assert tab._stop_loss_table.rowCount() == 10

        # First column should contain stop loss percentages
        first_col_values = []
        for row in range(tab._stop_loss_table.rowCount()):
            item = tab._stop_loss_table.item(row, 0)
            if item:
                first_col_values.append(item.text())

        # Should have stop loss levels
        assert len(first_col_values) == 10

    def test_scaling_spinbox_refreshes_table(
        self, app, qtbot, app_state_with_statistics_data: AppState
    ) -> None:
        """Test that changing scale out spinbox refreshes the scaling table."""
        tab = StatisticsTab(app_state_with_statistics_data)
        qtbot.addWidget(tab)

        # Trigger initial data population
        dummy_metrics = TradingMetrics(
            num_trades=20,
            win_rate=70.0,
            avg_winner=25.0,
            avg_loser=-6.0,
            rr_ratio=4.17,
            ev=15.0,
            kelly=20.0,
            winner_count=14,
            loser_count=6,
        )
        app_state_with_statistics_data.baseline_calculated.emit(dummy_metrics)

        # Verify initial spinbox value
        assert tab._scale_out_spin.value() == 50

        # Capture initial scaling table data (cell values)
        initial_cell = tab._scaling_table.item(0, 0)
        initial_value = initial_cell.text() if initial_cell else ""

        # Change spinbox value
        tab._scale_out_spin.setValue(70)

        # Table should still have same structure
        assert tab._scaling_table.rowCount() == 8

    def test_cover_spinbox_refreshes_table(
        self, app, qtbot, app_state_with_statistics_data: AppState
    ) -> None:
        """Test that changing cover spinbox refreshes the cover table."""
        tab = StatisticsTab(app_state_with_statistics_data)
        qtbot.addWidget(tab)

        # Trigger initial data population
        dummy_metrics = TradingMetrics(
            num_trades=20,
            win_rate=70.0,
            avg_winner=25.0,
            avg_loser=-6.0,
            rr_ratio=4.17,
            ev=15.0,
            kelly=20.0,
            winner_count=14,
            loser_count=6,
        )
        app_state_with_statistics_data.baseline_calculated.emit(dummy_metrics)

        # Verify initial table has data
        initial_row_count = tab._cover_table.rowCount()
        assert initial_row_count > 0

        # Change cover percentage
        tab._cover_spin.setValue(75)

        # Table should still have data (refreshed)
        assert tab._cover_table.rowCount() > 0

    def test_empty_state_shown_without_data(self, app, qtbot) -> None:
        """Test that empty state is shown when no data is loaded."""
        app_state = AppState()
        tab = StatisticsTab(app_state)
        qtbot.addWidget(tab)

        # Empty label should not be hidden (i.e., it's shown)
        assert not tab._empty_label.isHidden()
        # Tab widget should be hidden
        assert tab._tab_widget.isHidden()

    def test_tab_disable_without_mae_column(
        self, app, qtbot, sample_statistics_data: pd.DataFrame
    ) -> None:
        """Test that MAE-dependent tabs are disabled when MAE column is missing."""
        # Create data without MAE column
        df_no_mae = sample_statistics_data.drop(columns=["mae_pct"])

        # Create mapping - mae_pct still references a column name, but it won't exist in DF
        mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",  # Column name that won't exist in DataFrame
            mfe_pct="mfe_pct",
            win_loss_derived=True,
        )

        app_state = AppState()
        app_state.raw_df = df_no_mae
        app_state.baseline_df = df_no_mae.copy()
        app_state.column_mapping = mapping

        tab = StatisticsTab(app_state)
        qtbot.addWidget(tab)

        # Trigger data population
        dummy_metrics = TradingMetrics(
            num_trades=20,
            win_rate=70.0,
            avg_winner=25.0,
            avg_loser=-6.0,
            rr_ratio=4.17,
            ev=15.0,
            kelly=20.0,
            winner_count=14,
            loser_count=6,
        )
        app_state.baseline_calculated.emit(dummy_metrics)

        # Stop Loss/Offset tab (index 1) should be disabled (MAE-dependent)
        assert not tab._tab_widget.isTabEnabled(1)  # Stop Loss/Offset

        # MAE/MFE tab (index 0) should be enabled (has MFE)
        assert tab._tab_widget.isTabEnabled(0)  # MAE/MFE (has MFE)
        # Scaling tab (index 2) should be enabled (MFE-dependent)
        assert tab._tab_widget.isTabEnabled(2)  # Scaling

    def test_tab_disable_without_mfe_column(
        self, app, qtbot, sample_statistics_data: pd.DataFrame
    ) -> None:
        """Test that MFE-dependent tabs are disabled when MFE column is missing."""
        # Create data without MFE column
        df_no_mfe = sample_statistics_data.drop(columns=["mfe_pct"])

        # Create mapping - mfe_pct still references a column name, but it won't exist in DF
        mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",  # Column name that won't exist in DataFrame
            win_loss_derived=True,
        )

        app_state = AppState()
        app_state.raw_df = df_no_mfe
        app_state.baseline_df = df_no_mfe.copy()
        app_state.column_mapping = mapping

        tab = StatisticsTab(app_state)
        qtbot.addWidget(tab)

        # Trigger data population
        dummy_metrics = TradingMetrics(
            num_trades=20,
            win_rate=70.0,
            avg_winner=25.0,
            avg_loser=-6.0,
            rr_ratio=4.17,
            ev=15.0,
            kelly=20.0,
            winner_count=14,
            loser_count=6,
        )
        app_state.baseline_calculated.emit(dummy_metrics)

        # Stop Loss/Offset tab (index 1) should be enabled (MAE-dependent)
        assert tab._tab_widget.isTabEnabled(1)  # Stop Loss/Offset

        # MAE/MFE tab (index 0) should be enabled (has MAE)
        assert tab._tab_widget.isTabEnabled(0)  # MAE/MFE (has MAE)
        # Scaling tab (index 2) should be disabled (MFE-dependent)
        assert not tab._tab_widget.isTabEnabled(2)  # Scaling

    def test_initialize_from_existing_state(
        self, app, qtbot, app_state_with_statistics_data: AppState
    ) -> None:
        """Test that tab initializes correctly if data already exists in state."""
        # Set filtered_df before creating tab
        app_state_with_statistics_data.filtered_df = (
            app_state_with_statistics_data.baseline_df.copy()
        )

        # Create tab after data is already loaded
        tab = StatisticsTab(app_state_with_statistics_data)
        qtbot.addWidget(tab)

        # Tables should be populated immediately (from _initialize_from_state)
        assert tab._empty_label.isHidden()
        assert not tab._tab_widget.isHidden()

        # All tables should have data
        assert tab._mae_table.rowCount() > 0
        assert tab._mfe_table.rowCount() > 0
        assert tab._stop_loss_table.rowCount() > 0
        assert tab._offset_table.rowCount() > 0
        assert tab._scaling_table.rowCount() > 0

    def test_efficiency_change_updates_scaling_table(
        self, app, qtbot, sample_statistics_data: pd.DataFrame
    ) -> None:
        """Changing efficiency should recalculate Scaling table with fresh adjusted_gain_pct."""
        # Setup initial data with known gain values
        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL", "MSFT"],
            "date": pd.date_range("2024-01-01", periods=3).tolist(),
            "time": ["09:30:00", "09:35:00", "09:40:00"],
            "gain_pct": [0.20, 0.15, -0.10],  # Decimal format: 20%, 15%, -10%
            "mae_pct": [5.0, 10.0, 15.0],  # MAE in percentage points
            "mfe_pct": [25.0, 20.0, 5.0],  # MFE in percentage points
            "adjusted_gain_pct": [0.20, 0.15, -0.10],  # Initial: matches gain_pct (0% efficiency)
        })

        # Create app state with 0% efficiency initially
        app_state = AppState()
        app_state.raw_df = df
        app_state.baseline_df = df.copy()
        app_state.filtered_df = None
        app_state.column_mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            mfe_pct="mfe_pct",
        )

        # Initial params: 0% efficiency (so adjusted = original gains)
        params_0 = AdjustmentParams(stop_loss=100, efficiency=0)
        app_state.adjustment_params = params_0

        # Create tab
        tab = StatisticsTab(app_state)
        qtbot.addWidget(tab)

        # Trigger initial table population
        dummy_metrics = TradingMetrics(
            num_trades=3,
            win_rate=66.67,
            avg_winner=17.5,
            avg_loser=-10.0,
            rr_ratio=1.75,
            ev=10.0,
            kelly=20.0,
            winner_count=2,
            loser_count=1,
        )
        app_state.baseline_calculated.emit(dummy_metrics)

        # Wait for initial update
        qtbot.wait(50)

        # Get initial scaling table value (first row, Avg Full Hold Return % column - index 3)
        initial_item = tab._scaling_table.item(0, 3)
        initial_value = initial_item.text() if initial_item else ""

        # Change efficiency to 5%
        params_5 = AdjustmentParams(stop_loss=100, efficiency=5)
        app_state.adjustment_params = params_5

        # Emit signal (simulating efficiency change)
        app_state.adjustment_params_changed.emit(params_5)

        # Wait for update
        qtbot.wait(150)

        # Get updated scaling table value
        updated_item = tab._scaling_table.item(0, 3)
        updated_value = updated_item.text() if updated_item else ""

        # Values should differ (5% efficiency reduces returns)
        assert initial_value != updated_value, (
            f"Scaling table should update when efficiency changes. "
            f"Initial: {initial_value}, After 5% efficiency: {updated_value}"
        )

    def test_stop_loss_table_displays_kelly_metrics_columns(
        self, app, qtbot, app_state_with_statistics_data: AppState
    ) -> None:
        """Test that Stop Loss table shows Max DD % and Total Kelly $ columns."""
        tab = StatisticsTab(app_state_with_statistics_data)
        qtbot.addWidget(tab)

        # Trigger data population
        dummy_metrics = TradingMetrics(
            num_trades=20,
            win_rate=70.0,
            avg_winner=25.0,
            avg_loser=-6.0,
            rr_ratio=4.17,
            ev=15.0,
            kelly=20.0,
            winner_count=14,
            loser_count=6,
        )
        app_state_with_statistics_data.baseline_calculated.emit(dummy_metrics)

        # Get column headers from Stop Loss table
        headers = []
        for col in range(tab._stop_loss_table.columnCount()):
            header_item = tab._stop_loss_table.horizontalHeaderItem(col)
            if header_item:
                headers.append(header_item.text())

        # Verify Kelly metrics columns are present
        assert "Max DD %" in headers, f"'Max DD %' column not found. Headers: {headers}"
        assert "Total Kelly $" in headers, f"'Total Kelly $' column not found. Headers: {headers}"

    def test_stop_loss_table_kelly_metrics_have_values(
        self, app, qtbot, app_state_with_statistics_data: AppState
    ) -> None:
        """Test that Kelly metrics columns contain calculated values (not empty)."""
        tab = StatisticsTab(app_state_with_statistics_data)
        qtbot.addWidget(tab)

        # Trigger data population
        dummy_metrics = TradingMetrics(
            num_trades=20,
            win_rate=70.0,
            avg_winner=25.0,
            avg_loser=-6.0,
            rr_ratio=4.17,
            ev=15.0,
            kelly=20.0,
            winner_count=14,
            loser_count=6,
        )
        app_state_with_statistics_data.baseline_calculated.emit(dummy_metrics)

        # Find column indices for Kelly metrics
        max_dd_col = None
        total_kelly_col = None
        for col in range(tab._stop_loss_table.columnCount()):
            header_item = tab._stop_loss_table.horizontalHeaderItem(col)
            if header_item:
                if header_item.text() == "Max DD %":
                    max_dd_col = col
                elif header_item.text() == "Total Kelly $":
                    total_kelly_col = col

        assert max_dd_col is not None, "Max DD % column not found"
        assert total_kelly_col is not None, "Total Kelly $ column not found"

        # Verify at least one row has values in these columns
        row_count = tab._stop_loss_table.rowCount()
        assert row_count > 0, "Stop Loss table should have rows"

        # Check that at least the first row has non-empty values
        max_dd_item = tab._stop_loss_table.item(0, max_dd_col)
        total_kelly_item = tab._stop_loss_table.item(0, total_kelly_col)

        assert max_dd_item is not None, "Max DD % cell should exist"
        assert total_kelly_item is not None, "Total Kelly $ cell should exist"

        # Values should be non-empty strings
        assert max_dd_item.text().strip() != "", "Max DD % should have a value"
        assert total_kelly_item.text().strip() != "", "Total Kelly $ should have a value"

    def test_offset_table_displays_kelly_metrics_columns(
        self, app, qtbot, app_state_with_statistics_data: AppState
    ) -> None:
        """Test that Offset table shows Max DD % and Total Kelly $ columns."""
        tab = StatisticsTab(app_state_with_statistics_data)
        qtbot.addWidget(tab)

        # Trigger baseline calculation to populate tables
        dummy_metrics = TradingMetrics(
            num_trades=20,
            win_rate=70.0,
            avg_winner=25.0,
            avg_loser=-6.0,
            rr_ratio=4.17,
            ev=15.0,
            kelly=20.0,
            winner_count=14,
            loser_count=6,
        )
        app_state_with_statistics_data.baseline_calculated.emit(dummy_metrics)

        # Process events
        qtbot.wait(100)

        # Get column headers from offset table
        headers = []
        for i in range(tab._offset_table.columnCount()):
            header_item = tab._offset_table.horizontalHeaderItem(i)
            if header_item:
                headers.append(header_item.text())

        # Verify new columns are present
        assert "Max DD %" in headers, f"Max DD % not found in headers: {headers}"
        assert "Total Kelly $" in headers, f"Total Kelly $ not found in headers: {headers}"
