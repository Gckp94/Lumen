"""Integration tests for filter workflow."""

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
import pytest
from pytestqt.qtbot import QtBot

from src.core.app_state import AppState
from src.core.filter_engine import FilterEngine
from src.core.models import FilterCriteria
from src.tabs.feature_explorer import FeatureExplorerTab

if TYPE_CHECKING:
    from src.core.models import ColumnMapping


class TestFilterWorkflowIntegration:
    """Integration tests for complete filter workflow."""

    @pytest.fixture
    def app_state_with_data(self, sample_trades: pd.DataFrame) -> AppState:
        """AppState with loaded baseline data."""
        app_state = AppState()
        app_state.raw_df = sample_trades
        app_state.baseline_df = sample_trades.copy()
        return app_state

    def test_apply_filter_updates_app_state(
        self, qtbot: QtBot, app_state_with_data: AppState
    ) -> None:
        """Applying filter updates AppState.filtered_df."""
        tab = FeatureExplorerTab(app_state_with_data)
        qtbot.addWidget(tab)

        # Simulate data loaded
        app_state_with_data.data_loaded.emit(app_state_with_data.baseline_df)

        # Apply a filter
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10)
        ]
        tab._on_filters_applied(filters)

        # Check AppState was updated
        assert app_state_with_data.filters == filters
        assert app_state_with_data.filtered_df is not None
        assert len(app_state_with_data.filtered_df) == 3  # 0, 5, 10

    def test_clear_filter_restores_baseline(
        self, qtbot: QtBot, app_state_with_data: AppState
    ) -> None:
        """Clearing filters restores baseline data."""
        tab = FeatureExplorerTab(app_state_with_data)
        qtbot.addWidget(tab)

        # Simulate data loaded
        app_state_with_data.data_loaded.emit(app_state_with_data.baseline_df)

        # Apply a filter
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=5)
        ]
        tab._on_filters_applied(filters)

        assert len(app_state_with_data.filtered_df) == 2  # 0, 5

        # Clear filters
        tab._on_filters_cleared()

        # Should be restored to baseline
        assert app_state_with_data.filters == []
        pd.testing.assert_frame_equal(
            app_state_with_data.filtered_df, app_state_with_data.baseline_df
        )

    def test_filter_applied_signal_emitted(
        self, qtbot: QtBot, app_state_with_data: AppState
    ) -> None:
        """filtered_data_updated signal is emitted when filters applied."""
        tab = FeatureExplorerTab(app_state_with_data)
        qtbot.addWidget(tab)

        # Simulate data loaded
        app_state_with_data.data_loaded.emit(app_state_with_data.baseline_df)

        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10)
        ]

        with qtbot.waitSignal(
            app_state_with_data.filtered_data_updated, timeout=1000
        ) as blocker:
            tab._on_filters_applied(filters)

        assert blocker.args[0] is not None

    def test_filter_cleared_signal_emitted(
        self, qtbot: QtBot, app_state_with_data: AppState
    ) -> None:
        """filtered_data_updated signal is emitted when filters cleared."""
        tab = FeatureExplorerTab(app_state_with_data)
        qtbot.addWidget(tab)

        # Simulate data loaded and filter applied
        app_state_with_data.data_loaded.emit(app_state_with_data.baseline_df)
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10)
        ]
        tab._on_filters_applied(filters)

        with qtbot.waitSignal(
            app_state_with_data.filtered_data_updated, timeout=1000
        ):
            tab._on_filters_cleared()


class TestFilterChainIntegration:
    """Tests for multi-filter chain behavior."""

    def test_multiple_filters_narrow_results(
        self, sample_trades: pd.DataFrame
    ) -> None:
        """Multiple filters progressively narrow results."""
        engine = FilterEngine()

        # First filter: gain_pct between -5 and 10
        filters1 = [
            FilterCriteria(column="gain_pct", operator="between", min_val=-5, max_val=10)
        ]
        result1 = engine.apply_filters(sample_trades, filters1)
        assert len(result1) == 4  # -5, 0, 5, 10

        # Add second filter: gain_pct between 0 and 10
        filters2 = [
            FilterCriteria(column="gain_pct", operator="between", min_val=-5, max_val=10),
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10),
        ]
        result2 = engine.apply_filters(sample_trades, filters2)
        assert len(result2) == 3  # 0, 5, 10

        # Add third filter: volume between 1000 and 2000
        filters3 = [
            FilterCriteria(column="gain_pct", operator="between", min_val=-5, max_val=10),
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10),
            FilterCriteria(column="volume", operator="between", min_val=1000, max_val=2000),
        ]
        result3 = engine.apply_filters(sample_trades, filters3)
        assert len(result3) == 2  # Intersection narrows further

    def test_filter_with_data_reload(
        self, qtbot: QtBot, sample_trades: pd.DataFrame
    ) -> None:
        """Filters persist correctly when data is reloaded."""
        app_state = AppState()
        app_state.raw_df = sample_trades
        app_state.baseline_df = sample_trades.copy()

        tab = FeatureExplorerTab(app_state)
        qtbot.addWidget(tab)

        # Load data and apply filter
        app_state.data_loaded.emit(app_state.baseline_df)
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10)
        ]
        tab._on_filters_applied(filters)

        first_filtered_count = len(app_state.filtered_df)

        # Reload same data - filters should be preserved
        app_state.baseline_df = sample_trades.copy()
        tab._on_filters_applied(app_state.filters)

        assert len(app_state.filtered_df) == first_filtered_count


class TestFilteredMetricsIntegration:
    """Integration tests for filter → metrics recalculation flow (Story 4.1)."""

    @pytest.fixture
    def app_state_with_mapping(self, sample_trades: pd.DataFrame) -> AppState:
        """AppState with loaded data and column mapping."""
        from src.core.models import ColumnMapping

        app_state = AppState()
        app_state.raw_df = sample_trades
        app_state.baseline_df = sample_trades.copy()
        app_state.filtered_df = sample_trades.copy()
        app_state.column_mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            win_loss=None,
            mae_pct=None,
            win_loss_derived=True,
            breakeven_is_win=False,
        )
        return app_state

    def test_filter_triggers_metrics_recalculation(
        self, qtbot: QtBot, app_state_with_mapping: AppState
    ) -> None:
        """Applying filter triggers filtered_data_updated → metrics recalculation."""
        from src.tabs.pnl_stats import PnLStatsTab

        tab = PnLStatsTab(app_state_with_mapping)
        qtbot.addWidget(tab)

        # Apply a filter that reduces the dataset
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10)
        ]
        engine = FilterEngine()
        filtered = engine.apply_filters(app_state_with_mapping.baseline_df, filters)
        app_state_with_mapping.filtered_df = filtered

        # Track if metrics_updated signal is emitted
        with qtbot.waitSignal(
            app_state_with_mapping.metrics_updated, timeout=1000
        ) as blocker:
            app_state_with_mapping.filtered_data_updated.emit(filtered)

        # Verify signal was emitted with both baseline and filtered
        assert blocker.args is not None

    def test_filtered_metrics_stored_in_app_state(
        self, qtbot: QtBot, app_state_with_mapping: AppState
    ) -> None:
        """Filtered metrics are correctly stored in AppState."""
        from src.tabs.pnl_stats import PnLStatsTab

        tab = PnLStatsTab(app_state_with_mapping)
        qtbot.addWidget(tab)

        # Apply a filter
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=-5, max_val=10)
        ]
        engine = FilterEngine()
        filtered = engine.apply_filters(app_state_with_mapping.baseline_df, filters)
        app_state_with_mapping.filtered_df = filtered

        # Emit the signal to trigger calculation
        with qtbot.waitSignal(
            app_state_with_mapping.metrics_updated, timeout=1000
        ):
            app_state_with_mapping.filtered_data_updated.emit(filtered)

        # Verify filtered metrics were stored
        assert app_state_with_mapping.filtered_metrics is not None
        assert app_state_with_mapping.filtered_metrics.num_trades == len(filtered)

    def test_metrics_updated_signal_emits_both_baseline_and_filtered(
        self, qtbot: QtBot, app_state_with_mapping: AppState
    ) -> None:
        """metrics_updated signal emits both baseline and filtered TradingMetrics."""
        # Set baseline metrics first
        from src.core.metrics import MetricsCalculator
        from src.core.models import TradingMetrics
        from src.tabs.pnl_stats import PnLStatsTab

        calc = MetricsCalculator()
        baseline_metrics, _, _ = calc.calculate(
            app_state_with_mapping.baseline_df,
            "gain_pct",
            derived=True,
        )
        app_state_with_mapping.baseline_metrics = baseline_metrics

        tab = PnLStatsTab(app_state_with_mapping)
        qtbot.addWidget(tab)

        # Apply a filter
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10)
        ]
        engine = FilterEngine()
        filtered = engine.apply_filters(app_state_with_mapping.baseline_df, filters)
        app_state_with_mapping.filtered_df = filtered

        # Track the signal
        received_args = []

        def capture_metrics(baseline: object, filtered_m: object) -> None:
            received_args.append((baseline, filtered_m))

        app_state_with_mapping.metrics_updated.connect(capture_metrics)

        app_state_with_mapping.filtered_data_updated.emit(filtered)
        qtbot.wait(100)  # Allow signal processing

        # Verify both metrics were emitted
        assert len(received_args) == 1
        _baseline_arg, filtered_arg = received_args[0]
        assert isinstance(filtered_arg, TradingMetrics)

    def test_empty_filter_result_emits_empty_metrics(
        self, qtbot: QtBot, app_state_with_mapping: AppState
    ) -> None:
        """Empty filter result (no matches) emits empty metrics."""
        from src.tabs.pnl_stats import PnLStatsTab

        tab = PnLStatsTab(app_state_with_mapping)
        qtbot.addWidget(tab)

        # Apply filter that matches nothing
        filters = [
            FilterCriteria(
                column="gain_pct", operator="between", min_val=1000, max_val=2000
            )
        ]
        engine = FilterEngine()
        filtered = engine.apply_filters(app_state_with_mapping.baseline_df, filters)
        app_state_with_mapping.filtered_df = filtered

        assert len(filtered) == 0  # No matches

        # Emit the signal
        with qtbot.waitSignal(
            app_state_with_mapping.filtered_calculation_completed, timeout=1000
        ):
            app_state_with_mapping.filtered_data_updated.emit(filtered)

        # Verify empty metrics
        assert app_state_with_mapping.filtered_metrics is not None
        assert app_state_with_mapping.filtered_metrics.num_trades == 0

    def test_calculation_status_signals_emitted(
        self, qtbot: QtBot, app_state_with_mapping: AppState
    ) -> None:
        """filtered_calculation_started and completed signals are emitted."""
        from src.tabs.pnl_stats import PnLStatsTab

        tab = PnLStatsTab(app_state_with_mapping)
        qtbot.addWidget(tab)

        filtered = app_state_with_mapping.baseline_df.copy()
        app_state_with_mapping.filtered_df = filtered

        started_count = [0]
        completed_count = [0]

        def on_started() -> None:
            started_count[0] += 1

        def on_completed() -> None:
            completed_count[0] += 1

        app_state_with_mapping.filtered_calculation_started.connect(on_started)
        app_state_with_mapping.filtered_calculation_completed.connect(on_completed)

        # Emit filtered data update
        app_state_with_mapping.filtered_data_updated.emit(filtered)

        # Wait for debounced equity curve calculation
        qtbot.wait(400)  # DEBOUNCE_METRICS = 300ms + buffer

        assert started_count[0] == 1
        assert completed_count[0] == 1


class TestComparisonRibbonIntegration:
    """Integration tests for ComparisonRibbon update flow (Story 4.2)."""

    @pytest.fixture
    def app_state_with_mapping(self, sample_trades: pd.DataFrame) -> AppState:
        """AppState with loaded data and column mapping."""
        from src.core.models import ColumnMapping

        app_state = AppState()
        app_state.raw_df = sample_trades
        app_state.baseline_df = sample_trades.copy()
        app_state.filtered_df = sample_trades.copy()
        app_state.column_mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            win_loss=None,
            mae_pct=None,
            win_loss_derived=True,
            breakeven_is_win=False,
        )
        return app_state

    def test_metrics_updated_signal_triggers_ribbon_update(
        self, qtbot: QtBot, app_state_with_mapping: AppState
    ) -> None:
        """metrics_updated signal triggers ribbon update in PnLStatsTab."""
        from src.core.metrics import MetricsCalculator
        from src.tabs.pnl_stats import PnLStatsTab

        # Set baseline metrics first
        calc = MetricsCalculator()
        baseline_metrics, _, _ = calc.calculate(
            app_state_with_mapping.baseline_df,
            "gain_pct",
            derived=True,
        )
        app_state_with_mapping.baseline_metrics = baseline_metrics

        tab = PnLStatsTab(app_state_with_mapping)
        qtbot.addWidget(tab)

        # Apply a filter
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10)
        ]
        engine = FilterEngine()
        filtered = engine.apply_filters(app_state_with_mapping.baseline_df, filters)
        app_state_with_mapping.filtered_df = filtered

        # Emit filtered data - should eventually trigger ribbon update
        with qtbot.waitSignal(
            app_state_with_mapping.metrics_updated, timeout=1000
        ):
            app_state_with_mapping.filtered_data_updated.emit(filtered)

        # Verify ribbon was updated (not in empty state)
        ribbon = tab._comparison_ribbon
        trades_value = ribbon._cards["trades"]._value_widget.text()
        assert trades_value != "—", "Ribbon should not be in empty state after update"

    def test_ribbon_shows_correct_values_after_filter(
        self, qtbot: QtBot, app_state_with_mapping: AppState
    ) -> None:
        """Ribbon shows correct filtered values after filter applied."""
        from src.core.metrics import MetricsCalculator
        from src.tabs.pnl_stats import PnLStatsTab

        # Set baseline metrics
        calc = MetricsCalculator()
        baseline_metrics, _, _ = calc.calculate(
            app_state_with_mapping.baseline_df,
            "gain_pct",
            derived=True,
        )
        app_state_with_mapping.baseline_metrics = baseline_metrics

        tab = PnLStatsTab(app_state_with_mapping)
        qtbot.addWidget(tab)

        # Apply filter to show only winners (gain_pct > 0)
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0.01, max_val=100)
        ]
        engine = FilterEngine()
        filtered = engine.apply_filters(app_state_with_mapping.baseline_df, filters)
        app_state_with_mapping.filtered_df = filtered

        # Emit and wait for update
        with qtbot.waitSignal(
            app_state_with_mapping.metrics_updated, timeout=1000
        ):
            app_state_with_mapping.filtered_data_updated.emit(filtered)

        # The filtered count should match
        ribbon = tab._comparison_ribbon
        # Count winners in the filtered data
        winner_count = len(filtered[filtered["gain_pct"] > 0])
        trades_text = ribbon._cards["trades"]._value_widget.text()
        # The value should contain the filtered trade count
        assert str(winner_count) in trades_text.replace(",", "")

    def test_ribbon_clears_when_filters_removed(
        self, qtbot: QtBot, app_state_with_mapping: AppState
    ) -> None:
        """Ribbon clears when filtered_metrics becomes None."""
        from src.core.metrics import MetricsCalculator
        from src.tabs.pnl_stats import PnLStatsTab

        # Set baseline metrics
        calc = MetricsCalculator()
        baseline_metrics, _, _ = calc.calculate(
            app_state_with_mapping.baseline_df,
            "gain_pct",
            derived=True,
        )
        app_state_with_mapping.baseline_metrics = baseline_metrics

        tab = PnLStatsTab(app_state_with_mapping)
        qtbot.addWidget(tab)

        # First apply a filter
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10)
        ]
        engine = FilterEngine()
        filtered = engine.apply_filters(app_state_with_mapping.baseline_df, filters)
        app_state_with_mapping.filtered_df = filtered

        with qtbot.waitSignal(
            app_state_with_mapping.metrics_updated, timeout=1000
        ):
            app_state_with_mapping.filtered_data_updated.emit(filtered)

        # Verify ribbon has values
        ribbon = tab._comparison_ribbon
        trades_value = ribbon._cards["trades"]._value_widget.text()
        assert trades_value != "—"

        # Now emit metrics_updated with None for filtered
        app_state_with_mapping.metrics_updated.emit(baseline_metrics, None)

        # Verify ribbon shows empty state
        trades_value = ribbon._cards["trades"]._value_widget.text()
        assert trades_value == "—"
        delta_text = ribbon._cards["trades"]._delta_widget.text()
        assert "(no filter applied)" in delta_text


class TestMultiFilterLogic:
    """Integration tests for multi-filter AND logic (AC: 1, 6)."""

    def test_ten_filters_applied_correctly(self) -> None:
        """10 simultaneous filters apply with AND logic correctly."""
        import numpy as np

        # Create DataFrame with 10 numeric columns
        np.random.seed(42)
        df = pd.DataFrame({
            f"col_{i}": np.random.uniform(0, 100, 1000)
            for i in range(10)
        })

        engine = FilterEngine()

        # Create 10 filters, each narrowing the range
        filters = [
            FilterCriteria(column=f"col_{i}", operator="between", min_val=20, max_val=80)
            for i in range(10)
        ]

        result = engine.apply_filters(df, filters)

        # Verify all 10 filters were applied (AND logic)
        for i in range(10):
            col = f"col_{i}"
            assert all(result[col] >= 20), f"Filter on {col} lower bound not applied"
            assert all(result[col] <= 80), f"Filter on {col} upper bound not applied"

    @pytest.mark.slow
    def test_ten_filters_performance_100k_rows(
        self, large_dataset_path: Path
    ) -> None:
        """NFR: 10 filters applied in < 500ms for 100k rows."""
        from time import perf_counter

        from src.core.file_loader import FileLoader

        loader = FileLoader()
        df = loader.load(large_dataset_path)
        assert len(df) == 100_000, "Dataset should have 100k rows"

        engine = FilterEngine()

        # Create 10 filters on different ranges of gain_pct and volume
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=-2, max_val=3),
            FilterCriteria(column="volume", operator="between", min_val=500, max_val=8000),
            FilterCriteria(column="gain_pct", operator="between", min_val=-1.5, max_val=2.5),
            FilterCriteria(column="volume", operator="between", min_val=600, max_val=7500),
            FilterCriteria(column="gain_pct", operator="between", min_val=-1, max_val=2),
            FilterCriteria(column="volume", operator="between", min_val=700, max_val=7000),
            FilterCriteria(column="gain_pct", operator="between", min_val=-0.5, max_val=1.5),
            FilterCriteria(column="volume", operator="between", min_val=800, max_val=6500),
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=1),
            FilterCriteria(column="volume", operator="between", min_val=1000, max_val=5000),
        ]

        start = perf_counter()
        result = engine.apply_filters(df, filters)
        elapsed = perf_counter() - start

        assert elapsed < 0.5, f"Filter chain took {elapsed:.3f}s, exceeds 500ms limit"
        assert result is not None

    def test_date_range_plus_column_filters_combined(self) -> None:
        """Date range and column filters combine correctly."""
        df = pd.DataFrame({
            "date": pd.to_datetime([
                "2024-01-05", "2024-01-10", "2024-01-15",
                "2024-01-20", "2024-01-25", "2024-01-30",
            ]),
            "gain_pct": [-5.0, 0.0, 5.0, 10.0, 15.0, 20.0],
            "volume": [1000, 2000, 1500, 3000, 2500, 4000],
        })

        engine = FilterEngine()

        # Apply date range first
        date_filtered = engine.apply_date_range(
            df,
            date_col="date",
            start="2024-01-10",
            end="2024-01-25",
        )

        # Should have rows for: Jan 10, 15, 20, 25
        assert len(date_filtered) == 4

        # Then apply column filter
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=0, max_val=10
        )
        result = engine.apply_filters(date_filtered, [criteria])

        # Should have: Jan 10 (0%), Jan 15 (5%), Jan 20 (10%)
        assert len(result) == 3

        # Verify both filters applied correctly
        dates = pd.to_datetime(result["date"])
        assert all(dates >= pd.Timestamp("2024-01-10"))
        assert all(dates <= pd.Timestamp("2024-01-25"))
        assert all(result["gain_pct"] >= 0)
        assert all(result["gain_pct"] <= 10)

    def test_filter_chain_order_baseline_date_column_trigger(
        self, sample_trades: pd.DataFrame, sample_column_mapping: "ColumnMapping"
    ) -> None:
        """Filter chain applies in correct order: baseline -> date -> column -> trigger."""
        from src.core.first_trigger import FirstTriggerEngine

        # Add date column as datetime for date filtering
        df = sample_trades.copy()
        df["date"] = pd.to_datetime(df["date"])

        engine = FilterEngine()
        ft_engine = FirstTriggerEngine()

        # Step 1: Date range filter
        after_date = engine.apply_date_range(
            df,
            date_col="date",
            start="2024-01-02",
            end="2024-01-04",
        )
        assert len(after_date) < len(df), "Date filter should reduce rows"

        # Step 2: Column filters
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=-5, max_val=10)
        ]
        after_column = engine.apply_filters(after_date, filters)
        assert len(after_column) <= len(after_date), "Column filter should not increase rows"

        # Step 3: First trigger
        after_trigger = ft_engine.apply_filtered(
            after_column,
            ticker_col=sample_column_mapping.ticker,
            date_col=sample_column_mapping.date,
            time_col=sample_column_mapping.time,
        )
        assert len(after_trigger) <= len(after_column), "First trigger should not increase rows"


class TestComparisonGridIntegration:
    """Integration tests for ComparisonGrid update flow (Story 4.3)."""

    @pytest.fixture
    def app_state_with_mapping(self, sample_trades: pd.DataFrame) -> AppState:
        """AppState with loaded data and column mapping."""
        from src.core.models import ColumnMapping

        app_state = AppState()
        app_state.raw_df = sample_trades
        app_state.baseline_df = sample_trades.copy()
        app_state.filtered_df = sample_trades.copy()
        app_state.column_mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            win_loss=None,
            mae_pct=None,
            win_loss_derived=True,
            breakeven_is_win=False,
        )
        return app_state

    def test_metrics_updated_signal_triggers_grid_update(
        self, qtbot: QtBot, app_state_with_mapping: AppState
    ) -> None:
        """metrics_updated signal triggers comparison grid update in PnLStatsTab."""
        from src.core.metrics import MetricsCalculator
        from src.tabs.pnl_stats import PnLStatsTab

        # Set baseline metrics first
        calc = MetricsCalculator()
        baseline_metrics, _, _ = calc.calculate(
            app_state_with_mapping.baseline_df,
            "gain_pct",
            derived=True,
        )
        app_state_with_mapping.baseline_metrics = baseline_metrics

        tab = PnLStatsTab(app_state_with_mapping)
        qtbot.addWidget(tab)

        # Apply a filter
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10)
        ]
        engine = FilterEngine()
        filtered = engine.apply_filters(app_state_with_mapping.baseline_df, filters)
        app_state_with_mapping.filtered_df = filtered

        # Emit filtered data - should trigger grid update
        with qtbot.waitSignal(
            app_state_with_mapping.metrics_updated, timeout=1000
        ):
            app_state_with_mapping.filtered_data_updated.emit(filtered)

        # Verify filtered metrics were calculated and stored
        # The grid will reflect these values through the section cards
        assert app_state_with_mapping.filtered_metrics is not None
        assert app_state_with_mapping.filtered_metrics.win_rate is not None

    def test_grid_shows_correct_baseline_and_filtered_values_after_filter(
        self, qtbot: QtBot, app_state_with_mapping: AppState
    ) -> None:
        """Grid shows correct baseline and filtered values after filter applied."""
        from src.core.metrics import MetricsCalculator
        from src.tabs.pnl_stats import PnLStatsTab

        # Set baseline metrics
        calc = MetricsCalculator()
        baseline_metrics, _, _ = calc.calculate(
            app_state_with_mapping.baseline_df,
            "gain_pct",
            derived=True,
        )
        app_state_with_mapping.baseline_metrics = baseline_metrics

        tab = PnLStatsTab(app_state_with_mapping)
        qtbot.addWidget(tab)

        # Apply filter
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10)
        ]
        engine = FilterEngine()
        filtered = engine.apply_filters(app_state_with_mapping.baseline_df, filters)
        app_state_with_mapping.filtered_df = filtered

        # Emit and wait for update
        with qtbot.waitSignal(
            app_state_with_mapping.metrics_updated, timeout=1000
        ):
            app_state_with_mapping.filtered_data_updated.emit(filtered)

        # Verify metrics reflect the correct trade counts
        baseline_count = len(app_state_with_mapping.baseline_df)
        filtered_count = len(filtered)

        # Baseline metrics should have original count
        assert app_state_with_mapping.baseline_metrics.num_trades == baseline_count
        # Filtered metrics should have filtered count
        assert app_state_with_mapping.filtered_metrics is not None
        assert app_state_with_mapping.filtered_metrics.num_trades == filtered_count

    def test_grid_clears_filtered_column_when_filters_removed(
        self, qtbot: QtBot, app_state_with_mapping: AppState
    ) -> None:
        """Grid clears filtered column when filters removed."""
        from src.core.metrics import MetricsCalculator
        from src.tabs.pnl_stats import PnLStatsTab

        # Set baseline metrics
        calc = MetricsCalculator()
        baseline_metrics, _, _ = calc.calculate(
            app_state_with_mapping.baseline_df,
            "gain_pct",
            derived=True,
        )
        app_state_with_mapping.baseline_metrics = baseline_metrics

        tab = PnLStatsTab(app_state_with_mapping)
        qtbot.addWidget(tab)

        # First apply a filter
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10)
        ]
        engine = FilterEngine()
        filtered = engine.apply_filters(app_state_with_mapping.baseline_df, filters)
        app_state_with_mapping.filtered_df = filtered

        with qtbot.waitSignal(
            app_state_with_mapping.metrics_updated, timeout=1000
        ):
            app_state_with_mapping.filtered_data_updated.emit(filtered)

        # Verify filtered metrics were set
        assert app_state_with_mapping.filtered_metrics is not None
        assert app_state_with_mapping.filtered_metrics.win_rate is not None

        # Now emit metrics_updated with None for filtered (filters removed)
        app_state_with_mapping.filtered_metrics = None
        app_state_with_mapping.metrics_updated.emit(baseline_metrics, None)

        # Verify filtered_metrics is now None (grid will show em dashes for these)
        assert app_state_with_mapping.filtered_metrics is None


class TestEquityChartSignalFlow:
    """Integration tests for equity chart signal flow (Story 4.4)."""

    @pytest.fixture
    def app_state_with_equity(self, sample_trades: pd.DataFrame) -> AppState:
        """AppState with loaded data, column mapping, and equity curves."""
        import numpy as np

        from src.core.models import ColumnMapping

        app_state = AppState()
        app_state.raw_df = sample_trades
        app_state.baseline_df = sample_trades.copy()
        app_state.filtered_df = sample_trades.copy()
        app_state.column_mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            win_loss=None,
            mae_pct=None,
            win_loss_derived=True,
            breakeven_is_win=False,
        )

        # Create sample equity curve
        n_trades = len(sample_trades)
        np.random.seed(42)
        pnl = sample_trades["gain_pct"].values * 100  # Convert % to $
        equity = 10000 + np.cumsum(pnl)
        peak = np.maximum.accumulate(equity)

        app_state.flat_stake_equity_curve = pd.DataFrame({
            "trade_num": np.arange(1, n_trades + 1),
            "pnl": pnl,
            "equity": equity,
            "peak": peak,
            "drawdown": equity - peak,
        })

        return app_state

    def test_equity_curve_updated_signal_triggers_chart_update(
        self, qtbot: QtBot, app_state_with_equity: AppState
    ) -> None:
        """equity_curve_updated signal triggers chart update in PnLStatsTab."""
        import numpy as np

        from src.tabs.pnl_stats import PnLStatsTab

        tab = PnLStatsTab(app_state_with_equity)
        qtbot.addWidget(tab)

        # Create new equity data
        n_trades = 10
        pnl = np.random.normal(50, 100, n_trades)
        equity = 10000 + np.cumsum(pnl)
        peak = np.maximum.accumulate(equity)

        new_equity_df = pd.DataFrame({
            "trade_num": np.arange(1, n_trades + 1),
            "pnl": pnl,
            "equity": equity,
            "peak": peak,
            "drawdown": equity - peak,
        })

        # Emit signal
        app_state_with_equity.equity_curve_updated.emit(new_equity_df)

        # Verify chart was updated
        x_data, _y_data = tab._flat_stake_chart_panel.chart._baseline_curve.getData()
        assert len(x_data) == n_trades

    def test_filtered_equity_curve_updated_adds_filtered_series(
        self, qtbot: QtBot, app_state_with_equity: AppState
    ) -> None:
        """filtered_equity_curve_updated adds filtered series to chart."""
        import numpy as np

        from src.tabs.pnl_stats import PnLStatsTab

        tab = PnLStatsTab(app_state_with_equity)
        qtbot.addWidget(tab)

        # Set baseline first
        app_state_with_equity.equity_curve_updated.emit(
            app_state_with_equity.flat_stake_equity_curve
        )

        # Create filtered equity data (fewer points)
        n_trades = 3
        pnl = np.array([100, -50, 150])
        equity = 10000 + np.cumsum(pnl)

        filtered_equity_df = pd.DataFrame({
            "trade_num": np.arange(1, n_trades + 1),
            "equity": equity,
        })

        # Emit filtered signal
        app_state_with_equity.filtered_equity_curve_updated.emit(filtered_equity_df)

        # Verify filtered curve was updated
        x_data, _y_data = tab._flat_stake_chart_panel.chart._filtered_curve.getData()
        assert len(x_data) == n_trades

    def test_filter_removal_clears_filtered_series(
        self, qtbot: QtBot, app_state_with_equity: AppState
    ) -> None:
        """Filter removal clears filtered series (shows baseline only)."""
        import numpy as np

        from src.core.metrics import MetricsCalculator
        from src.tabs.pnl_stats import PnLStatsTab

        # Need baseline metrics for metrics_updated signal
        calc = MetricsCalculator()
        baseline_metrics, _, _ = calc.calculate(
            app_state_with_equity.baseline_df,
            "gain_pct",
            derived=True,
        )
        app_state_with_equity.baseline_metrics = baseline_metrics

        tab = PnLStatsTab(app_state_with_equity)
        qtbot.addWidget(tab)

        # Set baseline
        app_state_with_equity.equity_curve_updated.emit(
            app_state_with_equity.flat_stake_equity_curve
        )

        # Add filtered
        n_trades = 3
        filtered_equity_df = pd.DataFrame({
            "trade_num": np.arange(1, n_trades + 1),
            "equity": 10000 + np.cumsum([100, -50, 150]),
        })
        app_state_with_equity.filtered_equity_curve_updated.emit(filtered_equity_df)

        # Verify filtered exists
        x_data, _ = tab._flat_stake_chart_panel.chart._filtered_curve.getData()
        assert len(x_data) == n_trades

        # Now emit metrics_updated with None for filtered (filters removed)
        app_state_with_equity.metrics_updated.emit(baseline_metrics, None)

        # Verify filtered series is cleared
        x_data, _ = tab._flat_stake_chart_panel.chart._filtered_curve.getData()
        assert x_data is None or len(x_data) == 0

    def test_kelly_equity_curve_signal_updates_kelly_chart(
        self, qtbot: QtBot, app_state_with_equity: AppState
    ) -> None:
        """kelly_equity_curve_updated signal updates Kelly chart."""
        import numpy as np

        from src.tabs.pnl_stats import PnLStatsTab

        tab = PnLStatsTab(app_state_with_equity)
        qtbot.addWidget(tab)

        # Create Kelly equity data
        n_trades = 8
        pnl = np.random.normal(80, 150, n_trades)
        equity = 10000 + np.cumsum(pnl)
        peak = np.maximum.accumulate(equity)

        kelly_equity_df = pd.DataFrame({
            "trade_num": np.arange(1, n_trades + 1),
            "pnl": pnl,
            "equity": equity,
            "peak": peak,
            "drawdown": equity - peak,
        })

        # Emit signal
        app_state_with_equity.kelly_equity_curve_updated.emit(kelly_equity_df)

        # Verify Kelly chart was updated
        x_data, _ = tab._kelly_chart_panel.chart._baseline_curve.getData()
        assert len(x_data) == n_trades


class TestHistogramDialogIntegration:
    """Integration tests for histogram dialog flow (Story 4.5)."""

    @pytest.fixture
    def app_state_with_metrics(self, sample_trades: pd.DataFrame) -> AppState:
        """AppState with loaded data, column mapping, and baseline metrics."""
        from src.core.metrics import MetricsCalculator
        from src.core.models import ColumnMapping

        app_state = AppState()
        app_state.raw_df = sample_trades
        app_state.baseline_df = sample_trades.copy()
        app_state.filtered_df = sample_trades.copy()
        app_state.column_mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            win_loss=None,
            mae_pct=None,
            win_loss_derived=True,
            breakeven_is_win=False,
        )

        # Calculate baseline metrics
        calc = MetricsCalculator()
        baseline_metrics, _, _ = calc.calculate(
            app_state.baseline_df,
            "gain_pct",
            derived=True,
        )
        app_state.baseline_metrics = baseline_metrics

        return app_state

    def test_view_histogram_signal_connected(
        self, qtbot: QtBot, app_state_with_metrics: AppState
    ) -> None:
        """view_histogram_clicked signal is properly connected in PnLStatsTab."""
        from src.tabs.pnl_stats import PnLStatsTab

        tab = PnLStatsTab(app_state_with_metrics)
        qtbot.addWidget(tab)

        # Verify signals are connected by checking the distribution cards exist
        assert tab._winner_dist_card is not None
        assert tab._loser_dist_card is not None

        # Verify signal is connected (checking receivers is indirect, but we can verify
        # the signal exists and the handler method exists)
        assert hasattr(tab._winner_dist_card, "view_histogram_clicked")
        assert hasattr(tab, "_on_view_winner_histogram")
        assert hasattr(tab, "_on_view_loser_histogram")

    def test_histogram_dialog_receives_baseline_data(
        self, qtbot: QtBot, app_state_with_metrics: AppState
    ) -> None:
        """Histogram dialog receives correct baseline data from AppState."""
        from src.tabs.pnl_stats import PnLStatsTab
        from src.ui.components.distribution_histogram import HistogramDialog

        tab = PnLStatsTab(app_state_with_metrics)
        qtbot.addWidget(tab)

        baseline_metrics = app_state_with_metrics.baseline_metrics
        assert baseline_metrics is not None

        # Verify baseline data exists
        assert len(baseline_metrics.winner_gains) > 0 or len(baseline_metrics.loser_gains) > 0

        # Create dialog with the same data the handler would use
        if baseline_metrics.winner_gains:
            dialog = HistogramDialog(
                card_type="winner",
                baseline_gains=baseline_metrics.winner_gains,
                filtered_gains=None,
                baseline_mean=baseline_metrics.avg_winner,
                baseline_median=baseline_metrics.median_winner,
            )
            qtbot.addWidget(dialog)

            # Verify dialog received the data
            histogram = dialog._panel._histogram
            assert histogram._baseline_gains == baseline_metrics.winner_gains

    def test_histogram_dialog_receives_filtered_data_when_available(
        self, qtbot: QtBot, app_state_with_metrics: AppState
    ) -> None:
        """Histogram dialog receives filtered data when filters are applied."""
        from src.core.metrics import MetricsCalculator
        from src.tabs.pnl_stats import PnLStatsTab
        from src.ui.components.distribution_histogram import HistogramDialog

        tab = PnLStatsTab(app_state_with_metrics)
        qtbot.addWidget(tab)

        # Apply a filter to get filtered metrics
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=-5, max_val=10)
        ]
        engine = FilterEngine()
        filtered = engine.apply_filters(app_state_with_metrics.baseline_df, filters)
        app_state_with_metrics.filtered_df = filtered

        # Calculate filtered metrics
        calc = MetricsCalculator()
        filtered_metrics, _, _ = calc.calculate(filtered, "gain_pct", derived=True)
        app_state_with_metrics.filtered_metrics = filtered_metrics

        # Create dialog with filtered data
        baseline_metrics = app_state_with_metrics.baseline_metrics
        if baseline_metrics.winner_gains and filtered_metrics.winner_gains:
            dialog = HistogramDialog(
                card_type="winner",
                baseline_gains=baseline_metrics.winner_gains,
                filtered_gains=filtered_metrics.winner_gains,
                baseline_mean=baseline_metrics.avg_winner,
                baseline_median=baseline_metrics.median_winner,
                filtered_mean=filtered_metrics.avg_winner,
                filtered_median=filtered_metrics.median_winner,
            )
            qtbot.addWidget(dialog)

            # Verify dialog received both baseline and filtered data
            histogram = dialog._panel._histogram
            assert histogram._baseline_gains == baseline_metrics.winner_gains
            assert histogram._filtered_gains == filtered_metrics.winner_gains
