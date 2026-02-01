"""Export manager for Lumen application.

Handles exporting filtered data to various formats with metadata.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.core.exceptions import ExportError

if TYPE_CHECKING:
    from collections.abc import Callable

    from PyQt6.QtWidgets import QWidget

    from src.core.models import FilterCriteria, TradingMetrics

logger = logging.getLogger(__name__)


class ExportManager:
    """Export data in various formats.

    Provides methods to export DataFrames to CSV with metadata headers
    including filter summaries and timestamps.
    """

    def to_csv(
        self,
        df: pd.DataFrame,
        path: Path,
        filters: list[FilterCriteria] | None = None,
        first_trigger_enabled: bool = False,
        total_rows: int | None = None,
    ) -> None:
        """Export to CSV with UTF-8 BOM for Excel compatibility.

        Args:
            df: DataFrame to export
            path: Output file path
            filters: Active filters (unused, kept for API compatibility)
            first_trigger_enabled: First trigger toggle state (unused)
            total_rows: Total rows before filtering (unused)

        Note:
            Metadata is not included in CSV exports for Excel compatibility.
            Use XLSX export if metadata is needed.

        Raises:
            ExportError: If export fails
        """
        try:
            # Write with UTF-8 BOM for Excel compatibility
            with open(path, "wb") as f:
                # Write UTF-8 BOM
                f.write(b"\xef\xbb\xbf")
                # Write DataFrame as CSV
                csv_bytes = df.to_csv(index=False).encode("utf-8")
                f.write(csv_bytes)

            logger.info("Exported %d rows to %s", len(df), path)

        except PermissionError as e:
            raise ExportError(f"Permission denied: {path}") from e
        except OSError as e:
            raise ExportError(f"Export failed: {e}") from e

    def to_excel(
        self,
        df: pd.DataFrame,
        path: Path,
        sheet_name: str = "Data",
        filters: list[FilterCriteria] | None = None,
        first_trigger_enabled: bool = False,
        total_rows: int | None = None,
    ) -> None:
        """Export to Excel (.xlsx) format.

        Args:
            df: DataFrame to export
            path: Output file path
            sheet_name: Name of the worksheet
            filters: Active filters for metadata (optional)
            first_trigger_enabled: First trigger toggle state
            total_rows: Total rows before filtering (for metadata)

        Raises:
            ExportError: If export fails
        """
        try:
            # Build metadata for a separate sheet
            metadata = self._build_metadata(
                df, filters, first_trigger_enabled, total_rows
            )

            # Write to Excel with openpyxl engine
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                # Write main data
                df.to_excel(writer, sheet_name=sheet_name, index=False)

                # Write metadata to a separate sheet
                metadata_df = pd.DataFrame({"Export Info": metadata})
                metadata_df.to_excel(writer, sheet_name="Metadata", index=False)

            logger.info("Exported %d rows to Excel: %s", len(df), path)

        except PermissionError as e:
            raise ExportError(f"Permission denied: {path}") from e
        except OSError as e:
            raise ExportError(f"Export failed: {e}") from e

    def _build_metadata(
        self,
        df: pd.DataFrame,
        filters: list[FilterCriteria] | None,
        first_trigger_enabled: bool,
        total_rows: int | None,
    ) -> list[str]:
        """Build metadata comment lines.

        Args:
            df: DataFrame being exported
            filters: Active filters
            first_trigger_enabled: Whether first trigger is enabled
            total_rows: Total rows before filtering

        Returns:
            List of metadata strings to write as comments
        """
        lines = [
            f"Lumen Export - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Rows: {len(df):,}" + (f" of {total_rows:,}" if total_rows else ""),
            f"First Trigger: {'ON' if first_trigger_enabled else 'OFF'}",
        ]

        if filters:
            lines.append("Filters:")
            for f in filters:
                lines.append(f"  {f.column} {f.operator} [{f.min_val}, {f.max_val}]")
        else:
            lines.append("Filters: None")

        return lines

    def to_parquet(
        self,
        df: pd.DataFrame,
        path: Path,
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Export to Parquet with embedded metadata.

        Args:
            df: DataFrame to export
            path: Output file path
            metadata: Optional metadata dict to embed in Parquet schema

        Raises:
            ExportError: If export fails
        """
        try:
            # Create table from DataFrame
            table = pa.Table.from_pandas(df)

            # Build metadata if provided
            if metadata:
                custom_metadata = {
                    k.encode("utf-8"): v.encode("utf-8") for k, v in metadata.items()
                }
                # Merge with existing metadata
                existing = table.schema.metadata or {}
                merged = {**existing, **custom_metadata}
                table = table.replace_schema_metadata(merged)

            # Write to file
            pq.write_table(table, path)
            logger.info("Exported %d rows to Parquet: %s", len(df), path)

        except PermissionError as e:
            raise ExportError(f"Permission denied: {path}") from e
        except OSError as e:
            raise ExportError(f"Disk full or write error: {e}") from e

    def metrics_to_csv(
        self,
        baseline: TradingMetrics,
        filtered: TradingMetrics | None,
        path: Path,
    ) -> None:
        """Export metrics comparison to CSV.

        Args:
            baseline: Baseline metrics (unfiltered)
            filtered: Filtered metrics (or None for baseline-only export)
            path: Output file path

        Raises:
            ExportError: If export fails
        """
        try:
            rows = self._build_metrics_rows(baseline, filtered)
            df = pd.DataFrame(rows, columns=["Metric", "Baseline", "Filtered", "Delta"])

            # Write with metadata header
            with open(path, "w", encoding="utf-8", newline="") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"# Lumen Metrics Export - {timestamp}\n")
                df.to_csv(f, index=False)

            logger.info("Exported %d metrics to %s", len(rows), path)

        except PermissionError as e:
            raise ExportError(f"Permission denied: {path}") from e
        except OSError as e:
            raise ExportError(f"Export failed: {e}") from e

    def _build_metrics_rows(
        self,
        baseline: TradingMetrics,
        filtered: TradingMetrics | None,
    ) -> list[list[str]]:
        """Build metrics rows for CSV export.

        Args:
            baseline: Baseline metrics
            filtered: Filtered metrics (or None)

        Returns:
            List of [Metric, Baseline, Filtered, Delta] rows
        """
        rows: list[list[str]] = []

        # Define metric groups with (name, attr, format_type)
        # format_type: "count", "pct", "ratio", "dollar", "duration"
        metric_defs = [
            # Core Statistics (1-7)
            ("Trades", "num_trades", "count"),
            ("Win Rate", "win_rate", "pct"),
            ("Avg Winner", "avg_winner", "pct"),
            ("Avg Loser", "avg_loser", "pct"),
            ("R:R Ratio", "rr_ratio", "ratio"),
            ("EV", "ev", "pct"),
            ("Kelly", "kelly", "pct"),
            # Extended Core (8-14)
            ("Edge", "edge", "pct"),
            ("Fractional Kelly", "fractional_kelly", "pct"),
            ("EG Full Kelly", "eg_full_kelly", "pct"),
            ("EG Frac Kelly", "eg_frac_kelly", "pct"),
            ("EG Flat Stake", "eg_flat_stake", "pct"),
            ("Median Winner", "median_winner", "pct"),
            ("Median Loser", "median_loser", "pct"),
            # Streak & Loss (15-17)
            ("Max Consecutive Wins", "max_consecutive_wins", "count"),
            ("Max Consecutive Losses", "max_consecutive_losses", "count"),
            ("Max Loss %", "max_loss_pct", "pct"),
            # Flat Stake (18-21)
            ("Flat Stake PnL", "flat_stake_pnl", "dollar"),
            ("Flat Stake Max DD", "flat_stake_max_dd", "dollar"),
            ("Flat Stake Max DD %", "flat_stake_max_dd_pct", "pct"),
            ("Flat Stake DD Duration", "flat_stake_dd_duration", "duration"),
            # Kelly (22-25)
            ("Kelly PnL", "kelly_pnl", "dollar"),
            ("Kelly Max DD", "kelly_max_dd", "dollar"),
            ("Kelly Max DD %", "kelly_max_dd_pct", "pct"),
            ("Kelly DD Duration", "kelly_dd_duration", "duration"),
            # Distribution (26-27)
            ("Winner Count", "winner_count", "count"),
            ("Loser Count", "loser_count", "count"),
        ]

        for name, attr, fmt_type in metric_defs:
            base_val = getattr(baseline, attr, None)
            filt_val = getattr(filtered, attr, None) if filtered else None

            base_str = self._format_metric(base_val, fmt_type)
            filt_str = self._format_metric(filt_val, fmt_type) if filtered else "-"
            delta_str = self._format_delta(base_val, filt_val, fmt_type) if filtered else "-"

            rows.append([name, base_str, filt_str, delta_str])

        return rows

    def _format_metric(self, value: float | int | str | None, fmt_type: str) -> str:
        """Format a metric value for display.

        Args:
            value: The metric value
            fmt_type: One of "count", "pct", "ratio", "dollar", "duration"

        Returns:
            Formatted string
        """
        if value is None:
            return "-"

        if fmt_type == "count":
            return f"{int(value):,}"
        elif fmt_type == "pct":
            return f"{value:.2f}%"
        elif fmt_type == "ratio":
            return f"{value:.2f}"
        elif fmt_type == "dollar":
            return f"${value:,.2f}"
        elif fmt_type == "duration":
            if isinstance(value, str):
                return value
            return f"{int(value)} days"
        return str(value)

    def _format_delta(
        self,
        base_val: float | int | str | None,
        filt_val: float | int | str | None,
        fmt_type: str,
    ) -> str:
        """Format delta between baseline and filtered values.

        Args:
            base_val: Baseline value
            filt_val: Filtered value
            fmt_type: Format type

        Returns:
            Formatted delta string
        """
        if base_val is None or filt_val is None:
            return "-"

        # Handle string values (duration special cases)
        if isinstance(base_val, str) or isinstance(filt_val, str):
            return "-"

        delta = filt_val - base_val

        if fmt_type == "count":
            sign = "+" if delta >= 0 else ""
            return f"{sign}{int(delta):,}"
        elif fmt_type == "pct":
            sign = "+" if delta >= 0 else ""
            return f"{sign}{delta:.2f}pp"
        elif fmt_type == "ratio":
            sign = "+" if delta >= 0 else ""
            return f"{sign}{delta:.2f}"
        elif fmt_type == "dollar":
            sign = "+" if delta >= 0 else ""
            return f"{sign}${delta:,.2f}"
        elif fmt_type == "duration":
            sign = "+" if delta >= 0 else ""
            return f"{sign}{int(delta)} days"
        return "-"

    def chart_to_png(
        self,
        widget: QWidget,
        path: Path,
        resolution: tuple[int, int],
    ) -> None:
        """Export a chart widget to PNG.

        Uses PyQtGraph's ImageExporter for PlotWidget-based charts,
        or QWidget.grab() for other widgets.

        Args:
            widget: The chart widget to export
            path: Output file path
            resolution: Target resolution as (width, height)

        Raises:
            ExportError: If export fails
        """
        try:
            width, height = resolution

            # Try PyQtGraph export for PlotWidget
            if hasattr(widget, "plotItem"):
                self._export_pyqtgraph_widget(widget, path, width)
            else:
                self._export_qwidget(widget, path, width, height)

            logger.info("Exported chart to PNG: %s (%dx%d)", path, width, height)

        except PermissionError as e:
            raise ExportError(f"Permission denied: {path}") from e
        except OSError as e:
            raise ExportError(f"Chart export failed: {e}") from e
        except Exception as e:
            raise ExportError(f"Chart export failed: {e}") from e

    def _export_pyqtgraph_widget(
        self,
        widget: QWidget,
        path: Path,
        width: int,
    ) -> None:
        """Export PyQtGraph PlotWidget using ImageExporter.

        Args:
            widget: PlotWidget with plotItem
            path: Output path
            width: Target width (height auto-calculated)
        """
        from pyqtgraph.exporters import ImageExporter

        exporter = ImageExporter(widget.plotItem)
        exporter.parameters()["width"] = width
        exporter.export(str(path))

    def _export_qwidget(
        self,
        widget: QWidget,
        path: Path,
        width: int,
        height: int,
    ) -> None:
        """Export generic QWidget using grab and scale.

        Args:
            widget: Widget to export
            path: Output path
            width: Target width
            height: Target height
        """
        from PyQt6.QtCore import Qt

        pixmap = widget.grab()
        scaled = pixmap.scaled(
            width,
            height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        scaled.save(str(path), "PNG")

    def charts_to_zip(
        self,
        charts: dict[str, QWidget],
        path: Path,
        resolution: tuple[int, int],
        progress_callback: Callable[[int], None] | None = None,
    ) -> None:
        """Export multiple charts to a ZIP archive.

        Args:
            charts: Dict mapping chart names to widgets
            path: Output ZIP file path
            resolution: Target resolution as (width, height)
            progress_callback: Optional callback for progress updates (0-100)

        Raises:
            ExportError: If export fails
        """
        import tempfile
        import zipfile

        try:
            total = len(charts)
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)

                # Export each chart to temp directory
                for i, (name, widget) in enumerate(charts.items(), 1):
                    logger.debug("Exporting chart %d of %d: %s", i, total, name)
                    png_path = tmp_path / f"{name}.png"
                    self.chart_to_png(widget, png_path, resolution)

                    if progress_callback:
                        progress = int((i / total) * 80)  # 80% for chart export
                        progress_callback(progress)

                # Create ZIP archive
                with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for png_file in tmp_path.glob("*.png"):
                        zf.write(png_file, png_file.name)

                if progress_callback:
                    progress_callback(100)

            logger.info("Exported %d charts to ZIP: %s", total, path)

        except PermissionError as e:
            raise ExportError(f"Permission denied: {path}") from e
        except OSError as e:
            raise ExportError(f"ZIP export failed: {e}") from e
        except ExportError:
            raise
        except Exception as e:
            raise ExportError(f"ZIP export failed: {e}") from e
