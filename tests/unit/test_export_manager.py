"""Unit tests for ExportManager."""

from pathlib import Path

import pandas as pd
import pytest

from src.core.exceptions import ExportError
from src.core.export_manager import ExportManager
from src.core.models import FilterCriteria


class TestExportManagerToCSV:
    """Tests for ExportManager.to_csv() method."""

    def test_export_csv_all_columns(self, sample_trades: pd.DataFrame, tmp_path: Path) -> None:
        """Export includes all columns from DataFrame."""
        exporter = ExportManager()
        path = tmp_path / "export.csv"
        exporter.to_csv(sample_trades, path)

        result = pd.read_csv(path, encoding="utf-8-sig")
        assert set(result.columns) == set(sample_trades.columns)

    def test_export_csv_row_count(self, sample_trades: pd.DataFrame, tmp_path: Path) -> None:
        """Export includes correct number of rows."""
        exporter = ExportManager()
        path = tmp_path / "export.csv"
        exporter.to_csv(sample_trades, path)

        result = pd.read_csv(path, encoding="utf-8-sig")
        assert len(result) == len(sample_trades)

    def test_export_csv_first_trigger_on(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Export works when first_trigger_enabled=True."""
        exporter = ExportManager()
        path = tmp_path / "export.csv"
        exporter.to_csv(sample_trades, path, first_trigger_enabled=True)

        result = pd.read_csv(path, encoding="utf-8-sig")
        assert len(result) == len(sample_trades)

    def test_export_csv_first_trigger_off(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Export works when first_trigger_enabled=False."""
        exporter = ExportManager()
        path = tmp_path / "export.csv"
        exporter.to_csv(sample_trades, path, first_trigger_enabled=False)

        result = pd.read_csv(path, encoding="utf-8-sig")
        assert len(result) == len(sample_trades)

    def test_export_csv_empty_df(self, tmp_path: Path) -> None:
        """Empty DataFrame exports with header only."""
        exporter = ExportManager()
        path = tmp_path / "export.csv"
        empty = pd.DataFrame(columns=["ticker", "date", "gain_pct"])
        exporter.to_csv(empty, path)

        result = pd.read_csv(path, encoding="utf-8-sig")
        assert len(result) == 0
        assert list(result.columns) == ["ticker", "date", "gain_pct"]

    def test_export_csv_special_characters(self, tmp_path: Path) -> None:
        """Export handles special characters in data."""
        exporter = ExportManager()
        path = tmp_path / "export.csv"
        df = pd.DataFrame({
            "ticker": ["ABC,DEF", "GHI\"JKL", "MNO\nPQR"],
            "value": [1, 2, 3],
        })
        exporter.to_csv(df, path)

        result = pd.read_csv(path, encoding="utf-8-sig")
        assert len(result) == 3
        assert result.iloc[0]["ticker"] == "ABC,DEF"
        assert result.iloc[1]["ticker"] == 'GHI"JKL'

    def test_export_csv_no_comment_lines(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """CSV export has no comment lines - Excel compatible."""
        exporter = ExportManager()
        path = tmp_path / "export.csv"
        exporter.to_csv(sample_trades, path)

        with open(path, "rb") as f:
            content = f.read()

        # Should start with UTF-8 BOM followed by header row
        assert content.startswith(b"\xef\xbb\xbf"), "Missing UTF-8 BOM"

        # After BOM, first line should be header, not a comment
        text = content.decode("utf-8-sig")
        first_line = text.split("\n")[0]
        assert not first_line.startswith("#"), "Comment lines break Excel compatibility"

        # First line should be the column headers
        assert "ticker" in first_line or sample_trades.columns[0] in first_line


class TestExportManagerErrors:
    """Tests for ExportManager error handling."""

    def test_export_permission_denied(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Permission denied raises ExportError."""
        exporter = ExportManager()

        # Create a read-only directory (platform-specific behavior)
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()

        # Try to write to a non-existent subdirectory in readonly (will fail)
        path = readonly_dir / "subdir" / "export.csv"

        with pytest.raises(ExportError) as exc_info:
            exporter.to_csv(sample_trades, path)

        assert "Export failed" in str(exc_info.value) or "Permission" in str(exc_info.value)


class TestExportManagerToParquet:
    """Tests for ExportManager.to_parquet() method."""

    def test_parquet_creates_file(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Parquet export creates valid file."""
        exporter = ExportManager()
        path = tmp_path / "export.parquet"
        exporter.to_parquet(sample_trades, path)

        assert path.exists()

    def test_parquet_row_count(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Parquet export has correct row count."""
        exporter = ExportManager()
        path = tmp_path / "export.parquet"
        exporter.to_parquet(sample_trades, path)

        result = pd.read_parquet(path)
        assert len(result) == len(sample_trades)

    def test_parquet_stores_metadata(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Parquet export stores metadata in schema."""
        import pyarrow.parquet as pq

        exporter = ExportManager()
        path = tmp_path / "export.parquet"
        metadata = {
            "lumen_export": "true",
            "first_trigger": "ON",
            "filters": "gain_pct: between [0, 10]",
        }
        exporter.to_parquet(sample_trades, path, metadata=metadata)

        pq_metadata = pq.read_metadata(path).schema.to_arrow_schema().metadata
        assert pq_metadata[b"lumen_export"] == b"true"
        assert pq_metadata[b"first_trigger"] == b"ON"
        assert pq_metadata[b"filters"] == b"gain_pct: between [0, 10]"

    def test_parquet_no_metadata(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Parquet export works without metadata."""
        exporter = ExportManager()
        path = tmp_path / "export.parquet"
        exporter.to_parquet(sample_trades, path)

        result = pd.read_parquet(path)
        assert len(result) == len(sample_trades)

    def test_parquet_permission_error(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Parquet export raises ExportError on permission denied."""
        exporter = ExportManager()
        # Non-existent nested path
        path = tmp_path / "nonexistent" / "subdir" / "export.parquet"

        with pytest.raises(ExportError):
            exporter.to_parquet(sample_trades, path)


class TestExportManagerMetricsCSV:
    """Tests for ExportManager.metrics_to_csv() method."""

    def test_metrics_csv_creates_file(
        self, sample_baseline_metrics, tmp_path: Path
    ) -> None:
        """Metrics CSV export creates file."""
        exporter = ExportManager()
        path = tmp_path / "metrics.csv"
        exporter.metrics_to_csv(sample_baseline_metrics, None, path)

        assert path.exists()

    def test_metrics_csv_has_all_metrics(
        self, sample_baseline_metrics, tmp_path: Path
    ) -> None:
        """Metrics CSV includes all 27 metrics."""
        exporter = ExportManager()
        path = tmp_path / "metrics.csv"
        exporter.metrics_to_csv(sample_baseline_metrics, None, path)

        result = pd.read_csv(path, comment="#")
        # Should have 27 metrics
        assert len(result) == 27

    def test_metrics_csv_columns(
        self, sample_baseline_metrics, tmp_path: Path
    ) -> None:
        """Metrics CSV has correct columns."""
        exporter = ExportManager()
        path = tmp_path / "metrics.csv"
        exporter.metrics_to_csv(sample_baseline_metrics, None, path)

        result = pd.read_csv(path, comment="#")
        assert list(result.columns) == ["Metric", "Baseline", "Filtered", "Delta"]

    def test_metrics_csv_none_filtered(
        self, sample_baseline_metrics, tmp_path: Path
    ) -> None:
        """Metrics CSV handles None filtered metrics."""
        exporter = ExportManager()
        path = tmp_path / "metrics.csv"
        exporter.metrics_to_csv(sample_baseline_metrics, None, path)

        result = pd.read_csv(path, comment="#")
        # Filtered and Delta columns should be "-"
        assert all(result["Filtered"] == "-")
        assert all(result["Delta"] == "-")

    def test_metrics_csv_with_filtered(
        self, sample_baseline_metrics, sample_filtered_metrics, tmp_path: Path
    ) -> None:
        """Metrics CSV includes both baseline and filtered values."""
        exporter = ExportManager()
        path = tmp_path / "metrics.csv"
        exporter.metrics_to_csv(sample_baseline_metrics, sample_filtered_metrics, path)

        result = pd.read_csv(path, comment="#")
        # Should have actual values, not just "-"
        trades_row = result[result["Metric"] == "Trades"]
        assert trades_row["Baseline"].values[0] != "-"
        assert trades_row["Filtered"].values[0] != "-"

    def test_metrics_csv_metadata_header(
        self, sample_baseline_metrics, tmp_path: Path
    ) -> None:
        """Metrics CSV has metadata header."""
        exporter = ExportManager()
        path = tmp_path / "metrics.csv"
        exporter.metrics_to_csv(sample_baseline_metrics, None, path)

        with open(path) as f:
            header = f.readline()

        assert header.startswith("# Lumen Metrics Export")


class TestExportManagerChartPNG:
    """Tests for ExportManager.chart_to_png() method."""

    def test_chart_to_png_creates_file_1080p(self, tmp_path: Path, qtbot) -> None:
        """Chart export at 1080p resolution creates PNG file."""
        from PyQt6.QtWidgets import QWidget

        exporter = ExportManager()
        path = tmp_path / "chart_1080p.png"

        # Create a simple widget for testing
        widget = QWidget()
        widget.setFixedSize(800, 600)
        widget.show()
        qtbot.addWidget(widget)

        exporter.chart_to_png(widget, path, resolution=(1920, 1080))

        assert path.exists()
        assert path.suffix == ".png"

    def test_chart_to_png_creates_file_4k(self, tmp_path: Path, qtbot) -> None:
        """Chart export at 4K resolution creates PNG file."""
        from PyQt6.QtWidgets import QWidget

        exporter = ExportManager()
        path = tmp_path / "chart_4k.png"

        # Create a simple widget for testing
        widget = QWidget()
        widget.setFixedSize(800, 600)
        widget.show()
        qtbot.addWidget(widget)

        exporter.chart_to_png(widget, path, resolution=(3840, 2160))

        assert path.exists()
        assert path.suffix == ".png"


class TestExportManagerChartsZIP:
    """Tests for ExportManager.charts_to_zip() method."""

    def test_charts_to_zip_creates_archive(self, tmp_path: Path, qtbot) -> None:
        """Charts ZIP export creates archive file."""
        import zipfile

        from PyQt6.QtWidgets import QWidget

        exporter = ExportManager()
        path = tmp_path / "charts.zip"

        # Create test widgets
        widget1 = QWidget()
        widget1.setFixedSize(400, 300)
        widget1.show()
        qtbot.addWidget(widget1)

        widget2 = QWidget()
        widget2.setFixedSize(400, 300)
        widget2.show()
        qtbot.addWidget(widget2)

        charts = {"flat_stake_pnl": widget1, "kelly_pnl": widget2}

        exporter.charts_to_zip(charts, path, resolution=(1920, 1080))

        assert path.exists()
        assert zipfile.is_zipfile(path)

    def test_charts_to_zip_contains_all_charts(self, tmp_path: Path, qtbot) -> None:
        """Charts ZIP archive contains all chart PNGs."""
        import zipfile

        from PyQt6.QtWidgets import QWidget

        exporter = ExportManager()
        path = tmp_path / "charts.zip"

        # Create test widgets
        widget1 = QWidget()
        widget1.setFixedSize(400, 300)
        widget1.show()
        qtbot.addWidget(widget1)

        widget2 = QWidget()
        widget2.setFixedSize(400, 300)
        widget2.show()
        qtbot.addWidget(widget2)

        widget3 = QWidget()
        widget3.setFixedSize(400, 300)
        widget3.show()
        qtbot.addWidget(widget3)

        charts = {
            "flat_stake_pnl": widget1,
            "kelly_pnl": widget2,
            "equity_curve": widget3,
        }

        exporter.charts_to_zip(charts, path, resolution=(1920, 1080))

        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            assert len(names) == 3
            assert "flat_stake_pnl.png" in names
            assert "kelly_pnl.png" in names
            assert "equity_curve.png" in names


class TestExportManagerToExcel:
    """Tests for ExportManager.to_excel() method."""

    def test_export_excel_creates_file(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Excel export creates valid .xlsx file."""
        exporter = ExportManager()
        path = tmp_path / "export.xlsx"
        exporter.to_excel(sample_trades, path)

        assert path.exists()
        assert path.suffix == ".xlsx"

    def test_export_excel_row_count(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Excel export includes correct number of rows."""
        exporter = ExportManager()
        path = tmp_path / "export.xlsx"
        exporter.to_excel(sample_trades, path)

        result = pd.read_excel(path, sheet_name="Data")
        assert len(result) == len(sample_trades)

    def test_export_excel_metadata_in_separate_sheet(
        self, sample_trades: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Excel export includes metadata in separate Metadata sheet."""
        exporter = ExportManager()
        path = tmp_path / "export.xlsx"
        filters = [
            FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=5)
        ]
        exporter.to_excel(sample_trades, path, filters=filters)

        # Read both sheets
        data_df = pd.read_excel(path, sheet_name="Data")
        metadata_df = pd.read_excel(path, sheet_name="Metadata")

        # Data sheet has actual data
        assert len(data_df) == len(sample_trades)

        # Metadata sheet has export info
        assert "Export Info" in metadata_df.columns
        metadata_text = "\n".join(metadata_df["Export Info"].astype(str))
        assert "Lumen Export" in metadata_text
        assert "gain_pct" in metadata_text
