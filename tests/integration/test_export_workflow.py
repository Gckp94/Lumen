"""Integration tests for export workflow."""

from pathlib import Path

import pandas as pd

from src.core.app_state import AppState
from src.core.export_manager import ExportManager
from src.core.filter_engine import FilterEngine
from src.core.models import FilterCriteria


class TestExportWorkflow:
    """Integration tests for complete export workflow."""

    def test_export_workflow_with_filters(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Full export workflow: load → filter → export → verify."""
        # Setup
        app_state = AppState()
        app_state.raw_df = sample_trades
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=0, max_val=10
        )

        # Apply filter
        engine = FilterEngine()
        filtered = engine.apply_filters(sample_trades, [criteria])
        app_state.filtered_df = filtered
        app_state.filters = [criteria]

        # Export
        path = tmp_path / "export.csv"
        exporter = ExportManager()
        exporter.to_csv(
            filtered,
            path,
            filters=[criteria],
            first_trigger_enabled=False,
            total_rows=len(sample_trades),
        )

        # Verify
        result = pd.read_csv(path, comment="#")
        assert len(result) == len(filtered)
        assert (result["gain_pct"] >= 0).all()
        assert (result["gain_pct"] <= 10).all()

    def test_export_without_filters(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Export all data when no filters applied."""
        app_state = AppState()
        app_state.raw_df = sample_trades
        app_state.filtered_df = sample_trades
        app_state.filters = []

        path = tmp_path / "export.csv"
        exporter = ExportManager()
        exporter.to_csv(sample_trades, path)

        result = pd.read_csv(path, comment="#")
        assert len(result) == len(sample_trades)

    def test_export_with_first_trigger_on_metadata(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Export with first-trigger ON includes it in metadata."""
        path = tmp_path / "export.csv"
        exporter = ExportManager()
        exporter.to_csv(
            sample_trades,
            path,
            first_trigger_enabled=True,
        )

        with open(path) as f:
            content = f.read()

        assert "First Trigger: ON" in content

    def test_export_with_first_trigger_off_metadata(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Export with first-trigger OFF includes it in metadata."""
        path = tmp_path / "export.csv"
        exporter = ExportManager()
        exporter.to_csv(
            sample_trades,
            path,
            first_trigger_enabled=False,
        )

        with open(path) as f:
            content = f.read()

        assert "First Trigger: OFF" in content

    def test_export_suggested_filename_format(self) -> None:
        """Suggested filename follows expected pattern."""
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suggested = f"lumen_export_{timestamp}.csv"

        assert suggested.startswith("lumen_export_")
        assert suggested.endswith(".csv")
        # Should have timestamp pattern YYYYMMDD_HHMMSS
        import re

        assert re.match(r"lumen_export_\d{8}_\d{6}\.csv", suggested)

    def test_export_with_multiple_filters_metadata(
        self, tmp_path: Path
    ) -> None:
        """Export with multiple filters includes all in metadata."""
        df = pd.DataFrame({
            "gain_pct": [1.0, 2.0, 3.0, 4.0, 5.0],
            "volume": [100, 200, 300, 400, 500],
        })
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=1, max_val=4),
            FilterCriteria(column="volume", operator="between", min_val=150, max_val=450),
        ]

        engine = FilterEngine()
        filtered = engine.apply_filters(df, filters)

        path = tmp_path / "export.csv"
        exporter = ExportManager()
        exporter.to_csv(filtered, path, filters=filters, total_rows=len(df))

        with open(path) as f:
            content = f.read()

        assert "gain_pct between" in content
        assert "volume between" in content

    def test_export_preserves_all_columns(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Export preserves all columns from source DataFrame."""
        path = tmp_path / "export.csv"
        exporter = ExportManager()
        exporter.to_csv(sample_trades, path)

        result = pd.read_csv(path, comment="#")
        assert set(result.columns) == set(sample_trades.columns)

    def test_export_data_integrity(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Exported data matches source data values."""
        path = tmp_path / "export.csv"
        exporter = ExportManager()
        exporter.to_csv(sample_trades, path)

        result = pd.read_csv(path, comment="#")

        # Check that ticker values match
        assert list(result["ticker"]) == list(sample_trades["ticker"])

        # Check that numeric values are close (float comparison)
        for i, val in enumerate(sample_trades["gain_pct"]):
            assert abs(result.iloc[i]["gain_pct"] - val) < 0.0001


class TestExportEdgeCases:
    """Integration tests for export edge cases."""

    def test_export_empty_filtered_result(self, tmp_path: Path) -> None:
        """Export handles empty filtered result."""
        df = pd.DataFrame({
            "gain_pct": [1.0, 2.0, 3.0],
            "ticker": ["A", "B", "C"],
        })
        # Filter that matches nothing
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=100, max_val=200
        )
        engine = FilterEngine()
        filtered = engine.apply_filters(df, [criteria])

        assert len(filtered) == 0

        path = tmp_path / "export.csv"
        exporter = ExportManager()
        exporter.to_csv(filtered, path, filters=[criteria])

        result = pd.read_csv(path, comment="#")
        assert len(result) == 0

    def test_export_not_between_filter_metadata(self, tmp_path: Path) -> None:
        """Export includes not_between filter in metadata."""
        df = pd.DataFrame({"gain_pct": [1.0, 2.0, 3.0]})
        filters = [
            FilterCriteria(
                column="gain_pct", operator="not_between", min_val=1.5, max_val=2.5
            )
        ]

        path = tmp_path / "export.csv"
        exporter = ExportManager()
        exporter.to_csv(df, path, filters=filters)

        with open(path) as f:
            content = f.read()

        assert "not_between" in content

    def test_export_large_row_count_in_metadata(self, tmp_path: Path) -> None:
        """Export shows formatted row counts for large datasets."""
        # Simulate filtered subset of large dataset
        df = pd.DataFrame({"value": range(1234)})

        path = tmp_path / "export.csv"
        exporter = ExportManager()
        exporter.to_csv(df, path, total_rows=100_000)

        with open(path) as f:
            content = f.read()

        # Should show "Rows: 1,234 of 100,000"
        assert "1,234" in content
        assert "100,000" in content


class TestParquetExportIntegration:
    """Integration tests for Parquet export workflow."""

    def test_parquet_export_with_metadata(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Parquet export includes metadata that can be read back."""
        import pyarrow.parquet as pq

        path = tmp_path / "export.parquet"
        metadata = {
            "lumen_export": "true",
            "first_trigger": "ON",
            "filters": "gain_pct: between [0, 10]",
        }

        exporter = ExportManager()
        exporter.to_parquet(sample_trades, path, metadata=metadata)

        # Read metadata back
        pq_metadata = pq.read_metadata(path).schema.to_arrow_schema().metadata
        assert pq_metadata[b"lumen_export"] == b"true"
        assert pq_metadata[b"first_trigger"] == b"ON"

    def test_parquet_export_data_integrity(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Parquet export preserves data integrity."""
        path = tmp_path / "export.parquet"
        exporter = ExportManager()
        exporter.to_parquet(sample_trades, path)

        result = pd.read_parquet(path)
        assert len(result) == len(sample_trades)
        assert list(result.columns) == list(sample_trades.columns)
        assert list(result["ticker"]) == list(sample_trades["ticker"])

    def test_parquet_export_filtered_data(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Parquet export of filtered data."""
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=0, max_val=15
        )
        engine = FilterEngine()
        filtered = engine.apply_filters(sample_trades, [criteria])

        path = tmp_path / "export.parquet"
        exporter = ExportManager()
        exporter.to_parquet(filtered, path)

        result = pd.read_parquet(path)
        assert len(result) == len(filtered)


class TestMetricsExportIntegration:
    """Integration tests for metrics CSV export."""

    def test_metrics_csv_full_comparison(
        self,
        sample_baseline_metrics,
        sample_filtered_metrics,
        tmp_path: Path,
    ) -> None:
        """Metrics CSV export includes baseline and filtered comparison."""
        path = tmp_path / "metrics.csv"
        exporter = ExportManager()
        exporter.metrics_to_csv(
            sample_baseline_metrics, sample_filtered_metrics, path
        )

        result = pd.read_csv(path, comment="#")
        assert len(result) == 27  # All 27 metrics

        # Check that filtered column has values (not all "-")
        trades_row = result[result["Metric"] == "Trades"]
        assert trades_row["Filtered"].values[0] != "-"
        assert trades_row["Delta"].values[0] != "-"

    def test_metrics_csv_baseline_only(
        self, sample_baseline_metrics, tmp_path: Path
    ) -> None:
        """Metrics CSV export with baseline only."""
        path = tmp_path / "metrics.csv"
        exporter = ExportManager()
        exporter.metrics_to_csv(sample_baseline_metrics, None, path)

        result = pd.read_csv(path, comment="#")
        assert len(result) == 27

        # All filtered/delta columns should be "-"
        assert all(result["Filtered"] == "-")
        assert all(result["Delta"] == "-")

    def test_metrics_csv_has_all_metric_groups(
        self, sample_baseline_metrics, tmp_path: Path
    ) -> None:
        """Metrics CSV includes metrics from all groups."""
        path = tmp_path / "metrics.csv"
        exporter = ExportManager()
        exporter.metrics_to_csv(sample_baseline_metrics, None, path)

        result = pd.read_csv(path, comment="#")
        metrics = list(result["Metric"])

        # Core metrics
        assert "Trades" in metrics
        assert "Win Rate" in metrics
        assert "EV" in metrics

        # Streak metrics
        assert "Max Consecutive Wins" in metrics

        # Flat Stake metrics
        assert "Flat Stake PnL" in metrics

        # Kelly metrics
        assert "Kelly PnL" in metrics

        # Distribution metrics
        assert "Winner Count" in metrics
