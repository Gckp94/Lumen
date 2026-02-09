"""Export GUI state to filesystem for MCP server bridge.

Writes state files to ~/.lumen/state/ so the MCP server can read
the current GUI state (loaded file, filters, metrics) and sync
DataFrames without manual user intervention.
"""

from __future__ import annotations

import contextlib
import json
import logging
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd
from PyQt6.QtCore import QObject, QTimer

if TYPE_CHECKING:
    from src.core.app_state import AppState

logger = logging.getLogger(__name__)

STATE_DIR = Path.home() / ".lumen" / "state"


class StateExporter(QObject):
    """Debounced exporter that writes GUI state to filesystem.

    Connects to AppState signals and writes state files after a 500ms
    debounce period. Files are written atomically via tmp + rename.

    State files written to ~/.lumen/state/:
        gui_state.json  — metadata, filters, adjustment params, metrics summary
        baseline_data.parquet — baseline DataFrame
        filtered_data.parquet — filtered DataFrame
    """

    _DEBOUNCE_MS = 500

    def __init__(self, app_state: AppState, parent: QObject | None = None) -> None:
        """Initialize the state exporter.

        Args:
            app_state: The centralized application state to export.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self._app_state = app_state

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(self._DEBOUNCE_MS)
        self._timer.timeout.connect(self._export)

        self._connect_signals()

    def _connect_signals(self) -> None:
        """Connect to AppState signals that should trigger an export."""
        s = self._app_state
        s.data_loaded.connect(self._schedule)
        s.filtered_data_updated.connect(self._schedule)
        s.metrics_updated.connect(self._schedule)
        s.adjustment_params_changed.connect(self._schedule)
        s.filters_changed.connect(self._schedule)
        s.first_trigger_toggled.connect(self._schedule)

    def _schedule(self, *_args: object) -> None:
        """Restart the debounce timer."""
        self._timer.start()

    def _export(self) -> None:
        """Write all state files atomically."""
        state = self._app_state
        if state.baseline_df is None:
            return

        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            self._write_json(state)
            self._write_parquet(state.baseline_df, STATE_DIR / "baseline_data.parquet")
            if state.filtered_df is not None:
                self._write_parquet(state.filtered_df, STATE_DIR / "filtered_data.parquet")
            else:
                # Remove stale filtered file when no filters are active
                filtered_path = STATE_DIR / "filtered_data.parquet"
                if filtered_path.exists():
                    filtered_path.unlink()
            logger.debug("State exported to %s", STATE_DIR)
        except Exception:
            logger.exception("Failed to export GUI state")

    def _write_json(self, state: AppState) -> None:
        """Write gui_state.json atomically."""
        mapping_dict: dict[str, Any] | None = None
        if state.column_mapping is not None:
            mapping_dict = {
                "ticker": state.column_mapping.ticker,
                "date": state.column_mapping.date,
                "time": state.column_mapping.time,
                "gain_pct": state.column_mapping.gain_pct,
                "mae_pct": state.column_mapping.mae_pct,
                "mfe_pct": state.column_mapping.mfe_pct,
            }

        filters_list: list[dict[str, Any]] = []
        for f in state.filters:
            filters_list.append(
                {
                    "column": f.column,
                    "operator": f.operator,
                    "min_val": f.min_val,
                    "max_val": f.max_val,
                }
            )

        def _metrics_summary(m: Any) -> dict[str, Any] | None:
            if m is None:
                return None
            d = asdict(m)
            d.pop("winner_gains", None)
            d.pop("loser_gains", None)
            return d

        payload: dict[str, Any] = {
            "source_file": state.source_file_path,
            "source_sheet": state.source_sheet,
            "column_mapping": mapping_dict,
            "filters": filters_list,
            "adjustment_params": {
                "stop_loss": state.adjustment_params.stop_loss,
                "efficiency": state.adjustment_params.efficiency,
                "is_short": state.adjustment_params.is_short,
            },
            "first_trigger_enabled": state.first_trigger_enabled,
            "date_range": {
                "start": state.date_start,
                "end": state.date_end,
                "all_dates": state.all_dates,
            },
            "time_range": {
                "start": state.time_start,
                "end": state.time_end,
                "all_times": state.all_times,
            },
            "baseline_rows": len(state.baseline_df) if state.baseline_df is not None else 0,
            "filtered_rows": len(state.filtered_df) if state.filtered_df is not None else 0,
            "baseline_metrics": _metrics_summary(state.baseline_metrics),
            "filtered_metrics": _metrics_summary(state.filtered_metrics),
            "exported_at": datetime.now(UTC).isoformat(),
        }

        target = STATE_DIR / "gui_state.json"
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        tmp.replace(target)

    @staticmethod
    def _write_parquet(df: pd.DataFrame, target: Path) -> None:
        """Write a DataFrame to parquet atomically."""
        tmp = target.with_suffix(".parquet.tmp")
        # Convert object columns to strings to avoid pyarrow type errors
        # (mixed types or complex objects cause conversion failures)
        df_clean = df.copy()
        for col in df_clean.select_dtypes(include=["object"]).columns:
            df_clean[col] = df_clean[col].astype(str)
        df_clean.to_parquet(tmp, index=False)
        tmp.replace(target)

    def cleanup(self) -> None:
        """Remove all state files (called on application close)."""
        self._timer.stop()
        for name in ("gui_state.json", "baseline_data.parquet", "filtered_data.parquet"):
            p = STATE_DIR / name
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    logger.warning("Could not remove state file %s", p)
        # Remove .tmp files too
        for tmp in STATE_DIR.glob("*.tmp"):
            with contextlib.suppress(OSError):
                tmp.unlink()
        # Remove directory if empty
        try:
            if STATE_DIR.exists() and not any(STATE_DIR.iterdir()):
                STATE_DIR.rmdir()
        except OSError:
            pass
