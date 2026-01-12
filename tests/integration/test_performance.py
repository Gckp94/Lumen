"""Performance tests for Lumen application."""

import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from PyQt6.QtCore import QElapsedTimer

from src.core.app_state import AppState
from src.core.export_manager import ExportManager
from src.core.file_loader import FileLoader
from src.core.filter_engine import FilterEngine
from src.core.first_trigger import FirstTriggerEngine
from src.core.models import FilterCriteria
from src.tabs.feature_explorer import FeatureExplorerTab
from src.ui.components.chart_canvas import ChartCanvas
from src.ui.components.equity_chart import EquityChart


class TestFeatureExplorerPerformance:
    """Performance tests for Feature Explorer tab."""

    @pytest.mark.slow
    def test_chart_update_under_200ms_for_100k_rows(self, qtbot):
        """Chart update completes within 200ms for 100k rows.

        Note: Test environment threshold is set to 400ms to account for CI overhead.
        Production target remains 200ms.
        """
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        # Create large dataset
        np.random.seed(42)
        df = pd.DataFrame({
            "gain_pct": np.random.normal(0.5, 3, 100_000),
            "volume": np.random.randint(100, 10000, 100_000),
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)

        # Warm up (first render includes initialization overhead)
        tab._update_chart()

        # Measure chart update time (subsequent render)
        start_time = time.perf_counter()
        tab._update_chart()
        elapsed_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

        # Test environment threshold: 400ms (production target: 200ms)
        assert elapsed_time < 400, f"Chart update took {elapsed_time:.1f}ms, expected < 400ms"

    @pytest.mark.slow
    def test_column_change_under_200ms_for_100k_rows(self, qtbot):
        """Column change (without debounce) completes within 200ms for 100k rows.

        Note: Test environment threshold is set to 400ms to account for CI overhead.
        Production target remains 200ms.
        """
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        # Create large dataset
        np.random.seed(42)
        df = pd.DataFrame({
            "gain_pct": np.random.normal(0.5, 3, 100_000),
            "volume": np.random.randint(100, 10000, 100_000).astype(float),
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)

        # Warm up (initial render includes overhead)
        tab._update_chart()

        # Change column and measure direct update time (bypass debounce)
        tab._column_selector.setCurrentText("volume")

        start_time = time.perf_counter()
        tab._update_chart()  # Direct call, bypassing debounce
        elapsed_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

        # Test environment threshold: 400ms (production target: 200ms)
        assert elapsed_time < 400, f"Column change took {elapsed_time:.1f}ms, expected < 400ms"

    @pytest.mark.slow
    def test_handles_83k_points_without_lag(self, qtbot):
        """Chart handles 83k+ points (typical dataset size) without lag."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        # Create 83k dataset (typical first-trigger filtered size)
        np.random.seed(42)
        df = pd.DataFrame({
            "gain_pct": np.random.normal(0.5, 3, 83_000),
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)

        # Should complete without hanging
        start_time = time.perf_counter()
        tab._update_chart()
        elapsed_time = (time.perf_counter() - start_time) * 1000

        # Verify it completed in reasonable time (< 500ms including all overhead)
        assert elapsed_time < 500, f"83k points took {elapsed_time:.1f}ms, expected < 500ms"

        # Verify data was actually loaded
        assert len(tab._chart_canvas._scatter.data) == 83_000


class TestFilterPerformance:
    """Performance tests for filter operations."""

    @pytest.mark.slow
    def test_filter_application_under_500ms_for_100k_rows(self) -> None:
        """NFR2: Filter application completes within 500ms for 100k rows.

        This tests AC7 from Story 2.2: Filter applied in < 500ms for 100k rows.
        """
        # Create large dataset
        np.random.seed(42)
        df = pd.DataFrame({
            "gain_pct": np.random.normal(0.5, 3, 100_000),
            "volume": np.random.randint(100, 10000, 100_000),
        })

        engine = FilterEngine()
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=0, max_val=10
        )

        # Warm up (first run may include JIT compilation overhead)
        _ = engine.apply_filters(df, [criteria])

        # Measure filter application time
        start_time = time.perf_counter()
        result = engine.apply_filters(df, [criteria])
        elapsed_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

        assert elapsed_time < 500, (
            f"Filter application took {elapsed_time:.1f}ms, expected < 500ms"
        )

        # Verify filter actually worked
        assert len(result) > 0
        assert len(result) < len(df)

    @pytest.mark.slow
    def test_multiple_filters_under_500ms_for_100k_rows(self) -> None:
        """Multiple filters combined complete within 500ms for 100k rows."""
        # Create large dataset
        np.random.seed(42)
        df = pd.DataFrame({
            "gain_pct": np.random.normal(0.5, 3, 100_000),
            "volume": np.random.randint(100, 10000, 100_000),
            "price": np.random.uniform(10, 500, 100_000),
        })

        engine = FilterEngine()
        filters = [
            FilterCriteria(
                column="gain_pct", operator="between", min_val=-5, max_val=10
            ),
            FilterCriteria(
                column="volume", operator="between", min_val=1000, max_val=8000
            ),
            FilterCriteria(
                column="price", operator="between", min_val=50, max_val=400
            ),
        ]

        # Warm up
        _ = engine.apply_filters(df, filters)

        # Measure filter application time
        start_time = time.perf_counter()
        result = engine.apply_filters(df, filters)
        elapsed_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

        assert elapsed_time < 500, (
            f"Multiple filters took {elapsed_time:.1f}ms, expected < 500ms"
        )

        # Verify filters actually worked
        assert len(result) > 0
        assert len(result) < len(df)


class TestFirstTriggerTogglePerformance:
    """Performance tests for first trigger toggle operations."""

    @pytest.mark.slow
    def test_first_trigger_toggle_under_200ms(self) -> None:
        """NFR: Toggle response < 200ms for 100k rows.

        This tests AC4 from Story 2.3: Chart updates immediately on toggle (< 200ms).
        """
        # Create large dataset with multiple triggers per ticker-date
        np.random.seed(42)
        n_rows = 100_000

        # Generate data with ~50 tickers, ~250 dates, multiple triggers per combo
        df = pd.DataFrame({
            "ticker": np.random.choice([f"TICK{i}" for i in range(50)], n_rows),
            "date": np.random.choice(
                pd.date_range("2024-01-01", periods=250).strftime("%Y-%m-%d"),
                n_rows,
            ),
            "time": pd.to_datetime(
                np.random.randint(0, 86400, n_rows), unit="s"
            ).strftime("%H:%M:%S"),
            "gain_pct": np.random.normal(0.5, 3, n_rows),
        })

        engine = FirstTriggerEngine()

        # Warm up (first run may include overhead)
        _ = engine.apply_filtered(df, "ticker", "date", "time")

        # Measure first trigger application time
        start_time = time.perf_counter()
        result = engine.apply_filtered(df, "ticker", "date", "time")
        elapsed_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

        assert elapsed_time < 200, (
            f"First trigger toggle took {elapsed_time:.1f}ms, expected < 200ms"
        )

        # Verify first trigger actually worked
        assert len(result) <= n_rows
        assert len(result) > 0

        # Verify uniqueness per ticker-date
        groups = result.groupby(["ticker", "date"]).size()
        assert (groups == 1).all()

    @pytest.mark.slow
    def test_first_trigger_on_filtered_data_under_200ms(self) -> None:
        """NFR: First trigger application on filtered data < 200ms.

        Tests the typical workflow: filter first, then apply first trigger.
        """
        # Create large dataset
        np.random.seed(42)
        n_rows = 100_000

        df = pd.DataFrame({
            "ticker": np.random.choice([f"TICK{i}" for i in range(50)], n_rows),
            "date": np.random.choice(
                pd.date_range("2024-01-01", periods=250).strftime("%Y-%m-%d"),
                n_rows,
            ),
            "time": pd.to_datetime(
                np.random.randint(0, 86400, n_rows), unit="s"
            ).strftime("%H:%M:%S"),
            "gain_pct": np.random.normal(0.5, 3, n_rows),
        })

        # First apply a filter to reduce dataset
        filter_engine = FilterEngine()
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=0, max_val=5
        )
        filtered = filter_engine.apply_filters(df, [criteria])

        # Now apply first trigger on filtered data
        ft_engine = FirstTriggerEngine()

        # Warm up
        _ = ft_engine.apply_filtered(filtered, "ticker", "date", "time")

        # Measure first trigger on filtered data
        start_time = time.perf_counter()
        result = ft_engine.apply_filtered(filtered, "ticker", "date", "time")
        elapsed_time = (time.perf_counter() - start_time) * 1000

        assert elapsed_time < 200, (
            f"First trigger on filtered took {elapsed_time:.1f}ms, expected < 200ms"
        )

        # Verify result
        assert len(result) <= len(filtered)
        groups = result.groupby(["ticker", "date"]).size()
        assert (groups == 1).all()


class TestExportPerformance:
    """Performance tests for export operations."""

    @pytest.mark.slow
    def test_export_csv_under_2_seconds(
        self, large_dataset_path: Path, tmp_path: Path
    ) -> None:
        """NFR: Export completes < 2 seconds for 100k rows."""
        loader = FileLoader()
        df = loader.load(large_dataset_path)

        exporter = ExportManager()
        output_path = tmp_path / "large_export.csv"

        start = time.perf_counter()
        exporter.to_csv(df, output_path)
        elapsed = time.perf_counter() - start

        assert elapsed < 2.0, f"Export took {elapsed:.3f}s, exceeds 2s limit"
        assert output_path.exists()

    @pytest.mark.slow
    def test_export_csv_with_filters_under_2_seconds(
        self, large_dataset_path: Path, tmp_path: Path
    ) -> None:
        """NFR: Export with filter metadata completes < 2 seconds for 100k rows."""
        loader = FileLoader()
        df = loader.load(large_dataset_path)

        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=-5, max_val=5),
            FilterCriteria(column="volume", operator="between", min_val=1000, max_val=8000),
        ]

        exporter = ExportManager()
        output_path = tmp_path / "filtered_export.csv"

        start = time.perf_counter()
        exporter.to_csv(
            df,
            output_path,
            filters=filters,
            first_trigger_enabled=True,
            total_rows=len(df),
        )
        elapsed = time.perf_counter() - start

        assert elapsed < 2.0, f"Export with filters took {elapsed:.3f}s, exceeds 2s limit"
        assert output_path.exists()


class TestFilteredMetricsPerformance:
    """Performance tests for filtered metrics calculation (Story 4.1)."""

    @pytest.mark.slow
    def test_filtered_core_stats_under_100ms_for_10k_rows(self) -> None:
        """NFR: Filtered core stats complete < 100ms for 10k rows."""
        from src.core.metrics import MetricsCalculator

        np.random.seed(42)
        df = pd.DataFrame({
            "gain_pct": np.random.normal(0.5, 3, 10_000),
        })

        calc = MetricsCalculator()

        # Warm up
        _, _, _ = calc.calculate(df, "gain_pct", derived=True, flat_stake=None, start_capital=None)

        # Measure core stats only (no equity curves)
        start = time.perf_counter()
        metrics, flat_eq, kelly_eq = calc.calculate(
            df, "gain_pct", derived=True, flat_stake=None, start_capital=None
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, (
            f"Core stats calculation took {elapsed_ms:.1f}ms, expected < 100ms"
        )
        assert metrics.num_trades == 10_000
        assert flat_eq is None  # No equity curve when flat_stake=None
        assert kelly_eq is None  # No equity curve when start_capital=None

    @pytest.mark.slow
    def test_filtered_core_stats_under_100ms_for_100k_rows(self) -> None:
        """NFR: Filtered core stats complete < 100ms for 100k rows."""
        from src.core.metrics import MetricsCalculator

        np.random.seed(42)
        df = pd.DataFrame({
            "gain_pct": np.random.normal(0.5, 3, 100_000),
        })

        calc = MetricsCalculator()

        # Warm up
        _, _, _ = calc.calculate(df, "gain_pct", derived=True, flat_stake=None, start_capital=None)

        # Measure core stats only (no equity curves)
        start = time.perf_counter()
        metrics, flat_eq, kelly_eq = calc.calculate(
            df, "gain_pct", derived=True, flat_stake=None, start_capital=None
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, (
            f"Core stats calculation took {elapsed_ms:.1f}ms for 100k rows, expected < 100ms"
        )
        assert metrics.num_trades == 100_000
        assert flat_eq is None
        assert kelly_eq is None

    def test_debounce_timer_is_300ms(self) -> None:
        """Verify debounce timer uses Animation.DEBOUNCE_METRICS = 300ms."""
        from src.ui.constants import Animation

        assert Animation.DEBOUNCE_METRICS == 300, (
            f"DEBOUNCE_METRICS is {Animation.DEBOUNCE_METRICS}ms, expected 300ms"
        )


class TestChartInteractionPerformance:
    """Performance tests for chart pan/zoom with large datasets."""

    @pytest.mark.slow
    def test_chart_pan_zoom_60fps_with_83k_points(self, qtbot):
        """NFR: Chart maintains 60fps during pan/zoom with 83k points.

        Uses QElapsedTimer for accurate Qt timing and simulates
        realistic pan interactions with mouse events.
        """
        # Create 83k dataset (typical first-trigger filtered size)
        np.random.seed(42)
        df = pd.DataFrame({
            "gain_pct": np.random.normal(0.5, 3, 83_000),
        })
        assert len(df) >= 83000

        canvas = ChartCanvas()
        qtbot.addWidget(canvas)
        canvas.update_data(df, "gain_pct")
        canvas.show()
        qtbot.waitExposed(canvas)

        # Use QElapsedTimer for Qt-accurate timing
        timer = QElapsedTimer()
        viewbox = canvas._plot_widget.getViewBox()

        # Warm up - first few renders include initialization overhead
        for _ in range(5):
            viewbox.setRange(xRange=(0, 10000), yRange=(-5, 5))
            qtbot.wait(10)

        # Measure frame times during pan simulation
        frames = []
        canvas.rect().center()

        for i in range(30):
            timer.start()

            # Simulate pan by changing range (approximates left-drag behavior)
            offset = i * 100
            viewbox.setRange(
                xRange=(offset, offset + 10000),
                yRange=(-5, 5),
                padding=0,
            )

            # Allow Qt event processing
            qtbot.wait(1)

            elapsed_ms = timer.elapsed()
            frames.append(elapsed_ms)

        # Calculate average frame time and FPS
        avg_frame_time_ms = sum(frames) / len(frames)
        fps = 1000.0 / avg_frame_time_ms if avg_frame_time_ms > 0 else 0

        # 60fps = 16.67ms per frame
        # Use 30fps threshold for CI environments (33.3ms per frame)
        # Production target remains 60fps
        assert fps >= 30, (
            f"Chart renders at {fps:.1f}fps (avg {avg_frame_time_ms:.1f}ms/frame), "
            f"expected >= 30fps in test environment"
        )

        # Verify data was actually loaded
        assert len(canvas._scatter.data) == 83_000

    @pytest.mark.slow
    def test_chart_zoom_performance_83k_points(self, qtbot):
        """Test zoom performance with 83k points."""
        np.random.seed(42)
        df = pd.DataFrame({
            "gain_pct": np.random.normal(0.5, 3, 83_000),
        })

        canvas = ChartCanvas()
        qtbot.addWidget(canvas)
        canvas.update_data(df, "gain_pct")
        canvas.show()
        qtbot.waitExposed(canvas)

        timer = QElapsedTimer()
        viewbox = canvas._plot_widget.getViewBox()

        # Warm up
        for _ in range(3):
            viewbox.setRange(xRange=(0, 83000), yRange=(-10, 10))
            qtbot.wait(10)

        # Measure zoom operations
        zoom_times = []
        for scale in [1.0, 0.5, 0.25, 0.1, 0.25, 0.5, 1.0]:
            timer.start()

            x_range = 83000 * scale
            viewbox.setRange(
                xRange=(0, x_range),
                yRange=(-10 * scale, 10 * scale),
                padding=0,
            )
            qtbot.wait(1)

            zoom_times.append(timer.elapsed())

        avg_zoom_time_ms = sum(zoom_times) / len(zoom_times)

        # Zoom should complete in < 50ms average
        assert avg_zoom_time_ms < 50, (
            f"Zoom took {avg_zoom_time_ms:.1f}ms average, expected < 50ms"
        )

    @pytest.mark.slow
    def test_chart_auto_range_performance_83k_points(self, qtbot):
        """Test auto-range reset performance with 83k points."""
        np.random.seed(42)
        df = pd.DataFrame({
            "gain_pct": np.random.normal(0.5, 3, 83_000),
        })

        canvas = ChartCanvas()
        qtbot.addWidget(canvas)
        canvas.update_data(df, "gain_pct")
        canvas.show()
        qtbot.waitExposed(canvas)

        # Zoom in first
        viewbox = canvas._plot_widget.getViewBox()
        viewbox.setRange(xRange=(0, 100), yRange=(0, 1))
        qtbot.wait(10)

        timer = QElapsedTimer()

        # Measure auto-range time
        timer.start()
        canvas.auto_range()
        qtbot.wait(1)
        elapsed_ms = timer.elapsed()

        # Auto-range should complete in < 100ms
        assert elapsed_ms < 100, (
            f"Auto-range took {elapsed_ms}ms, expected < 100ms"
        )


class TestEquityChartPerformance:
    """Performance tests for EquityChart component (Story 4.4)."""

    @pytest.mark.slow
    def test_equity_chart_10k_points_under_500ms(self, qtbot):
        """EquityChart renders 10k points in < 500ms (AC6)."""
        np.random.seed(42)
        n_points = 10_000

        # Create equity curve data
        pnl = np.random.normal(50, 100, n_points)
        equity = 10000 + np.cumsum(pnl)
        peak = np.maximum.accumulate(equity)

        df = pd.DataFrame({
            "trade_num": np.arange(1, n_points + 1),
            "pnl": pnl,
            "equity": equity,
            "peak": peak,
            "drawdown": equity - peak,
        })

        chart = EquityChart()
        qtbot.addWidget(chart)
        chart.show()
        qtbot.waitExposed(chart)

        # Warm up
        chart.set_baseline(df)
        chart.clear()
        qtbot.wait(50)

        # Measure render time
        start = time.perf_counter()
        chart.set_baseline(df)
        qtbot.wait(10)  # Allow Qt to process
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 500, (
            f"10k points rendered in {elapsed_ms:.1f}ms, expected < 500ms"
        )

        # Verify data was actually rendered
        x_data, _y_data = chart._baseline_curve.getData()
        assert len(x_data) == n_points

    @pytest.mark.slow
    def test_equity_chart_83k_points_under_1000ms(self, qtbot):
        """EquityChart renders 83k points in < 1000ms (stretch goal)."""
        np.random.seed(42)
        n_points = 83_000

        pnl = np.random.normal(50, 100, n_points)
        equity = 10000 + np.cumsum(pnl)
        peak = np.maximum.accumulate(equity)

        df = pd.DataFrame({
            "trade_num": np.arange(1, n_points + 1),
            "pnl": pnl,
            "equity": equity,
            "peak": peak,
            "drawdown": equity - peak,
        })

        chart = EquityChart()
        qtbot.addWidget(chart)
        chart.show()
        qtbot.waitExposed(chart)

        # Warm up
        chart.set_baseline(df)
        chart.clear()
        qtbot.wait(50)

        # Measure render time
        start = time.perf_counter()
        chart.set_baseline(df)
        qtbot.wait(10)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 1000, (
            f"83k points rendered in {elapsed_ms:.1f}ms, expected < 1000ms"
        )

        x_data, _y_data = chart._baseline_curve.getData()
        assert len(x_data) == n_points

    @pytest.mark.slow
    def test_equity_chart_filtered_curve_performance(self, qtbot):
        """Filtered curve also renders 10k points in < 500ms."""
        np.random.seed(42)
        n_points = 10_000

        pnl = np.random.normal(50, 100, n_points)
        equity = 10000 + np.cumsum(pnl)
        peak = np.maximum.accumulate(equity)

        df = pd.DataFrame({
            "trade_num": np.arange(1, n_points + 1),
            "pnl": pnl,
            "equity": equity,
            "peak": peak,
            "drawdown": equity - peak,
        })

        chart = EquityChart()
        qtbot.addWidget(chart)
        chart.show()
        qtbot.waitExposed(chart)

        # Warm up
        chart.set_filtered(df)
        chart.clear()
        qtbot.wait(50)

        # Measure render time
        start = time.perf_counter()
        chart.set_filtered(df)
        qtbot.wait(10)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 500, (
            f"Filtered 10k points rendered in {elapsed_ms:.1f}ms, expected < 500ms"
        )

    @pytest.mark.slow
    def test_equity_chart_both_curves_performance(self, qtbot):
        """Both curves render together in < 800ms for 10k points each."""
        np.random.seed(42)
        n_points = 10_000

        pnl = np.random.normal(50, 100, n_points)
        equity = 10000 + np.cumsum(pnl)
        peak = np.maximum.accumulate(equity)

        baseline_df = pd.DataFrame({
            "trade_num": np.arange(1, n_points + 1),
            "pnl": pnl,
            "equity": equity,
            "peak": peak,
            "drawdown": equity - peak,
        })

        # Filtered has different values
        pnl2 = np.random.normal(60, 90, n_points)
        equity2 = 10000 + np.cumsum(pnl2)

        filtered_df = pd.DataFrame({
            "trade_num": np.arange(1, n_points + 1),
            "equity": equity2,
        })

        chart = EquityChart()
        qtbot.addWidget(chart)
        chart.show()
        qtbot.waitExposed(chart)

        # Warm up
        chart.set_baseline(baseline_df)
        chart.set_filtered(filtered_df)
        chart.clear()
        qtbot.wait(50)

        # Measure render time for both
        start = time.perf_counter()
        chart.set_baseline(baseline_df)
        chart.set_filtered(filtered_df)
        qtbot.wait(10)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 800, (
            f"Both curves rendered in {elapsed_ms:.1f}ms, expected < 800ms"
        )
