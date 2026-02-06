"""Lumen Analyst MCP Server.

Provides Claude Code with tools for loading trade data, running pandas queries,
computing Lumen trading metrics, and comparing datasets/filters side-by-side.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

# Add Lumen src to path so we can import core modules
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from core.breakdown import BreakdownCalculator  # noqa: E402
from core.metrics import MetricsCalculator  # noqa: E402
from core.models import (
    AdjustmentParams,
    ColumnMapping,
    FilterCriteria,
    TradingMetrics,
)  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP("lumen_analyst")

# ---------------------------------------------------------------------------
# Session State
# ---------------------------------------------------------------------------

MAX_RESULT_CHARS = 50_000

# Common heuristic aliases for auto-detecting column mappings
_COLUMN_ALIASES: dict[str, list[str]] = {
    "ticker": ["ticker", "symbol", "sym", "stock", "instrument", "asset"],
    "date": ["date", "trade_date", "entry_date", "dt"],
    "time": ["time", "trade_time", "entry_time", "tm"],
    "gain_pct": [
        "gain_pct",
        "gain",
        "gain%",
        "return",
        "return_pct",
        "returns",
        "pnl_pct",
        "profit",
        "profit_pct",
        "result",
    ],
    "mae_pct": ["mae_pct", "mae", "mae%", "max_adverse", "adverse"],
    "mfe_pct": ["mfe_pct", "mfe", "mfe%", "max_favorable", "favorable"],
    "trigger_number": ["trigger_number", "trigger", "trigger_num", "trig"],
}


class LoadedDataset:
    """In-memory representation of a loaded trade data file."""

    def __init__(
        self,
        df: pd.DataFrame,
        mapping: ColumnMapping,
        file_path: str,
        alias: str,
    ) -> None:
        self.df = df
        self.mapping = mapping
        self.file_path = file_path
        self.alias = alias

    @property
    def row_count(self) -> int:
        return len(self.df)

    @property
    def date_range(self) -> str:
        date_col = self.mapping.date
        if date_col in self.df.columns:
            dates = pd.to_datetime(self.df[date_col], errors="coerce").dropna()
            if not dates.empty:
                return f"{dates.min().date()} to {dates.max().date()}"
        return "unknown"


# Global session state — persists for the MCP session lifetime
_datasets: dict[str, LoadedDataset] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auto_detect_mapping(columns: list[str]) -> ColumnMapping | None:
    """Try to auto-detect column mapping from DataFrame column names."""
    found: dict[str, str] = {}
    lower_cols = {c.lower().strip(): c for c in columns}

    for field, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_cols:
                found[field] = lower_cols[alias]
                break

    # Minimum required: date and gain_pct
    if "date" not in found or "gain_pct" not in found:
        return None

    return ColumnMapping(
        ticker=found.get("ticker", ""),
        date=found["date"],
        time=found.get("time", ""),
        gain_pct=found["gain_pct"],
        mae_pct=found.get("mae_pct", ""),
        mfe_pct=found.get("mfe_pct", ""),
        win_loss_derived=True,
        breakeven_is_win=False,
    )


def _get_dataset(alias: str) -> LoadedDataset:
    """Retrieve a loaded dataset by alias, raising a clear error if not found."""
    if alias not in _datasets:
        available = ", ".join(_datasets.keys()) if _datasets else "(none)"
        msg = f"No dataset loaded with alias '{alias}'. Available: {available}"
        raise ValueError(msg)
    return _datasets[alias]


def _truncate(text: str, limit: int = MAX_RESULT_CHARS) -> str:
    """Truncate text with a note if it exceeds the limit."""
    if len(text) <= limit:
        return text
    return text[: limit - 200] + f"\n\n... (truncated at {limit} chars, full length: {len(text)})"


def _metrics_to_dict(metrics: TradingMetrics) -> dict[str, Any]:
    """Convert TradingMetrics to a serializable dict, dropping list fields."""
    d = asdict(metrics)
    # Drop large list fields to keep output concise
    d.pop("winner_gains", None)
    d.pop("loser_gains", None)
    return d


def _apply_filters(
    df: pd.DataFrame,
    filters: list[dict[str, Any]],
) -> pd.DataFrame:
    """Apply a list of filter dicts to a DataFrame using Lumen's FilterCriteria."""
    mask = pd.Series(True, index=df.index)
    for f in filters:
        col = f.get("column", "")
        op = f.get("operator", "between")
        min_val = f.get("min_val")
        max_val = f.get("max_val")
        # Simple equality / comparison shortcuts
        if op in ("==", "!=", ">=", "<=", ">", "<"):
            value = f.get("value")
            if value is None:
                continue
            if op == "==":
                mask &= df[col] == value
            elif op == "!=":
                mask &= df[col] != value
            elif op == ">=":
                mask &= df[col] >= value
            elif op == "<=":
                mask &= df[col] <= value
            elif op == ">":
                mask &= df[col] > value
            elif op == "<":
                mask &= df[col] < value
        elif op == "in":
            values = f.get("values", f.get("value", []))
            if isinstance(values, list):
                mask &= df[col].isin(values)
        else:
            # Use Lumen's FilterCriteria for range-based operators
            fc = FilterCriteria(column=col, operator=op, min_val=min_val, max_val=max_val)
            err = fc.validate()
            if err:
                raise ValueError(f"Invalid filter on '{col}': {err}")
            mask &= fc.apply(df)
    return df[mask].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Pydantic Input Models
# ---------------------------------------------------------------------------


class LoadDataInput(BaseModel):
    """Input for loading a trade data file."""

    model_config = ConfigDict(str_strip_whitespace=True)

    file_path: str = Field(
        ...,
        description="Absolute path to an Excel (.xlsx/.xls) or CSV file containing trade data.",
    )
    alias: Optional[str] = Field(
        default=None,
        description="Short alias to reference this dataset later. Defaults to filename stem.",
    )
    sheet: Optional[str] = Field(
        default=None,
        description="Sheet name for Excel files. If omitted, reads the first sheet.",
    )
    column_mapping: Optional[dict[str, str]] = Field(
        default=None,
        description=(
            "Explicit column mapping: keys are Lumen field names "
            "(ticker, date, time, gain_pct, mae_pct, mfe_pct), values are source column names. "
            "If omitted, auto-detection is attempted."
        ),
    )


class DescribeDataInput(BaseModel):
    """Input for describing a loaded dataset."""

    model_config = ConfigDict(str_strip_whitespace=True)

    alias: str = Field(..., description="Alias of the loaded dataset to describe.")


class QueryDataInput(BaseModel):
    """Input for running a pandas expression on a loaded dataset."""

    model_config = ConfigDict(str_strip_whitespace=True)

    alias: str = Field(..., description="Alias of the loaded dataset to query.")
    expression: str = Field(
        ...,
        description=(
            "A Python/pandas expression evaluated with `df` (the DataFrame), "
            "`pd` (pandas), and `np` (numpy) in scope. "
            "Example: `df.groupby('ticker')['gain_pct'].mean()` or "
            "`df[df['gain_pct'] > 0.02].shape[0]`"
        ),
    )


class ComputeMetricsInput(BaseModel):
    """Input for computing Lumen trading metrics on a loaded dataset."""

    model_config = ConfigDict(str_strip_whitespace=True)

    alias: str = Field(..., description="Alias of the loaded dataset.")
    filters: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description=(
            "Optional list of filter dicts. Each dict has: "
            "'column' (str), 'operator' (str: ==, !=, >=, <=, >, <, in, between, not_between), "
            "and 'value' / 'min_val' / 'max_val' as appropriate."
        ),
    )
    first_trigger_only: bool = Field(
        default=False,
        description="If True, keep only trigger_number == 1 rows.",
    )
    stop_loss_pct: Optional[float] = Field(
        default=None,
        description="Stop loss percentage (e.g. 8 for 8%). Enables stop-adjusted metrics.",
    )
    efficiency_pct: Optional[float] = Field(
        default=None,
        description="Efficiency/slippage percentage (e.g. 5 for 5%). Default 5 when stop_loss set.",
    )
    fractional_kelly_pct: float = Field(
        default=25.0,
        description="Fractional Kelly percentage (default 25%).",
    )
    flat_stake: Optional[float] = Field(
        default=None,
        description="Fixed stake amount in dollars for flat-stake equity curve.",
    )
    start_capital: Optional[float] = Field(
        default=None,
        description="Starting capital in dollars for Kelly equity curve.",
    )


class CompareDatasetsInput(BaseModel):
    """Input for comparing metrics between two datasets or filter views."""

    model_config = ConfigDict(str_strip_whitespace=True)

    alias_a: str = Field(..., description="Alias of dataset A.")
    alias_b: Optional[str] = Field(
        default=None,
        description="Alias of dataset B. If omitted, uses alias_a for both (filter comparison).",
    )
    filters_a: Optional[list[dict[str, Any]]] = Field(
        default=None, description="Filters for dataset A."
    )
    filters_b: Optional[list[dict[str, Any]]] = Field(
        default=None, description="Filters for dataset B."
    )


class GetBreakdownInput(BaseModel):
    """Input for retrieving breakdown metrics."""

    model_config = ConfigDict(str_strip_whitespace=True)

    alias: str = Field(..., description="Alias of the loaded dataset.")
    period: str = Field(
        default="yearly",
        description="Period type: 'yearly' for all years, 'monthly' for a specific year.",
    )
    year: Optional[int] = Field(
        default=None,
        description="Year for monthly breakdown (required if period='monthly').",
    )
    filters: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Optional list of filter dicts to narrow the data.",
    )
    first_trigger_only: bool = Field(
        default=False,
        description="If True, keep only trigger_number == 1 rows.",
    )
    stake: float = Field(
        default=1000.0,
        description="Fixed stake amount for flat stake calculations.",
    )
    start_capital: float = Field(
        default=10000.0,
        description="Starting capital for equity curves.",
    )
    stop_loss_pct: Optional[float] = Field(
        default=None,
        description="Stop loss percentage (e.g., 8 for 8%). Enables stop-adjusted metrics.",
    )
    efficiency_pct: Optional[float] = Field(
        default=None,
        description="Efficiency/slippage percentage (e.g., 5 for 5%).",
    )


# ---------------------------------------------------------------------------
# Tool Implementations
# ---------------------------------------------------------------------------


@mcp.tool(
    name="lumen_load_data",
    annotations={
        "title": "Load Trade Data",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def lumen_load_data(params: LoadDataInput) -> str:
    """Load an Excel or CSV trade data file into memory for analysis.

    Auto-detects column mapping using heuristic name matching. If auto-detection
    fails, returns the available columns so you can call again with an explicit
    column_mapping parameter.

    Args:
        params (LoadDataInput): Validated input containing:
            - file_path (str): Absolute path to Excel/CSV file
            - alias (Optional[str]): Short name for referencing later
            - sheet (Optional[str]): Sheet name for Excel files
            - column_mapping (Optional[dict]): Explicit field-to-column mapping

    Returns:
        str: JSON with alias, row count, columns, detected mapping, and date range.
    """
    path = Path(params.file_path)
    if not path.exists():
        return f"Error: File not found: {params.file_path}"

    # Read file
    try:
        if path.suffix.lower() in (".xlsx", ".xls"):
            df = pd.read_excel(path, sheet_name=params.sheet)
        elif path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
        else:
            return f"Error: Unsupported file type '{path.suffix}'. Use .xlsx, .xls, or .csv."
    except Exception as e:
        return f"Error reading file: {e}"

    # Determine column mapping
    if params.column_mapping:
        mapping = ColumnMapping(
            ticker=params.column_mapping.get("ticker", ""),
            date=params.column_mapping.get("date", ""),
            time=params.column_mapping.get("time", ""),
            gain_pct=params.column_mapping.get("gain_pct", ""),
            mae_pct=params.column_mapping.get("mae_pct", ""),
            mfe_pct=params.column_mapping.get("mfe_pct", ""),
            win_loss_derived=True,
        )
    else:
        mapping = _auto_detect_mapping(list(df.columns))
        if mapping is None:
            return json.dumps(
                {
                    "error": "Auto-detection failed. Could not find 'date' and 'gain_pct' columns.",
                    "available_columns": list(df.columns),
                    "hint": (
                        "Call load_data again with an explicit column_mapping dict. "
                        "Required keys: 'date', 'gain_pct'. "
                        "Optional: 'ticker', 'time', 'mae_pct', 'mfe_pct'."
                    ),
                },
                indent=2,
            )

    # Resolve alias
    alias = params.alias or path.stem
    if alias in _datasets:
        # Append numeric suffix to avoid collision
        i = 2
        while f"{alias}_{i}" in _datasets:
            i += 1
        alias = f"{alias}_{i}"

    dataset = LoadedDataset(df=df, mapping=mapping, file_path=str(path), alias=alias)
    _datasets[alias] = dataset

    return json.dumps(
        {
            "alias": alias,
            "file": str(path),
            "rows": dataset.row_count,
            "columns": list(df.columns),
            "mapping": {
                "ticker": mapping.ticker,
                "date": mapping.date,
                "time": mapping.time,
                "gain_pct": mapping.gain_pct,
                "mae_pct": mapping.mae_pct,
                "mfe_pct": mapping.mfe_pct,
            },
            "date_range": dataset.date_range,
        },
        indent=2,
    )


@mcp.tool(
    name="lumen_describe_data",
    annotations={
        "title": "Describe Loaded Dataset",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def lumen_describe_data(params: DescribeDataInput) -> str:
    """Return summary statistics for a loaded dataset.

    Provides row count, date range, column dtypes, and descriptive stats
    for numeric columns (count, mean, std, min, max, quartiles).

    Args:
        params (DescribeDataInput): Validated input containing:
            - alias (str): Alias of the loaded dataset

    Returns:
        str: JSON with row count, date range, dtypes, and numeric summary stats.
    """
    try:
        ds = _get_dataset(params.alias)
    except ValueError as e:
        return f"Error: {e}"

    df = ds.df
    describe = df.describe(include="all").to_dict()

    result = {
        "alias": ds.alias,
        "file": ds.file_path,
        "rows": ds.row_count,
        "date_range": ds.date_range,
        "mapping": {
            "ticker": ds.mapping.ticker,
            "date": ds.mapping.date,
            "time": ds.mapping.time,
            "gain_pct": ds.mapping.gain_pct,
            "mae_pct": ds.mapping.mae_pct,
            "mfe_pct": ds.mapping.mfe_pct,
        },
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "summary": describe,
    }
    return _truncate(json.dumps(result, indent=2, default=str))


@mcp.tool(
    name="lumen_query_data",
    annotations={
        "title": "Query Data with Pandas",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def lumen_query_data(params: QueryDataInput) -> str:
    """Execute a pandas expression against a loaded dataset.

    The expression is evaluated in a restricted namespace containing only:
    - df: the loaded DataFrame
    - pd: pandas module
    - np: numpy module

    No access to os, subprocess, open, or other system modules.

    Args:
        params (QueryDataInput): Validated input containing:
            - alias (str): Dataset alias
            - expression (str): Pandas expression (e.g. df.groupby('ticker').gain_pct.mean())

    Returns:
        str: The result of the expression as text. Large DataFrames are truncated.
    """
    try:
        ds = _get_dataset(params.alias)
    except ValueError as e:
        return f"Error: {e}"

    # Restricted eval namespace — no builtins, no system access
    namespace: dict[str, Any] = {
        "df": ds.df,
        "pd": pd,
        "np": np,
        "__builtins__": {},
    }

    try:
        result = eval(params.expression, namespace)  # noqa: S307
    except Exception as e:
        return f"Error evaluating expression: {type(e).__name__}: {e}"

    # Format result
    if isinstance(result, pd.DataFrame):
        text = result.to_string()
        if len(result) > 100:
            text = (
                f"({len(result)} rows x {len(result.columns)} columns)\n\n"
                f"First 50 rows:\n{result.head(50).to_string()}\n\n"
                f"Last 10 rows:\n{result.tail(10).to_string()}"
            )
    elif isinstance(result, pd.Series):
        text = result.to_string()
    else:
        text = str(result)

    return _truncate(text)


@mcp.tool(
    name="lumen_compute_metrics",
    annotations={
        "title": "Compute Trading Metrics",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def lumen_compute_metrics(params: ComputeMetricsInput) -> str:
    """Compute Lumen's full TradingMetrics suite on a loaded dataset.

    Calculates: win rate, avg winner/loser, R:R ratio, expected value, Kelly criterion,
    stop-adjusted Kelly, edge, expected growth, streaks, flat-stake PnL & drawdowns,
    compounded Kelly PnL & drawdowns, and distribution statistics.

    Args:
        params (ComputeMetricsInput): Validated input containing:
            - alias (str): Dataset alias
            - filters (Optional[list]): Filter dicts to narrow the data
            - first_trigger_only (bool): Keep only trigger_number == 1
            - stop_loss_pct (Optional[float]): Stop loss % for adjustments
            - efficiency_pct (Optional[float]): Efficiency/slippage %
            - fractional_kelly_pct (float): Fractional Kelly %
            - flat_stake (Optional[float]): Fixed stake for equity curve
            - start_capital (Optional[float]): Starting capital for Kelly curve

    Returns:
        str: JSON with all TradingMetrics fields plus trade count and filter summary.
    """
    try:
        ds = _get_dataset(params.alias)
    except ValueError as e:
        return f"Error: {e}"

    df = ds.df.copy()
    mapping = ds.mapping
    filter_summary: list[str] = []

    # Apply first-trigger filter
    if params.first_trigger_only:
        trig_col = None
        for alias_name in _COLUMN_ALIASES.get("trigger_number", []):
            lower_cols = {c.lower(): c for c in df.columns}
            if alias_name in lower_cols:
                trig_col = lower_cols[alias_name]
                break
        if trig_col:
            df = df[df[trig_col] == 1].reset_index(drop=True)
            filter_summary.append("first_trigger_only=True")
        else:
            filter_summary.append("first_trigger_only requested but no trigger column found")

    # Apply user filters
    if params.filters:
        try:
            df = _apply_filters(df, params.filters)
            filter_summary.append(f"{len(params.filters)} filter(s) applied")
        except Exception as e:
            return f"Error applying filters: {e}"

    if len(df) == 0:
        return json.dumps(
            {
                "error": "No rows remain after filtering.",
                "filters_applied": filter_summary,
                "hint": "Try loosening your filters or removing first_trigger_only.",
            },
            indent=2,
        )

    # Build adjustment params if stop loss provided
    adjustment_params: AdjustmentParams | None = None
    mae_col: str | None = None
    if params.stop_loss_pct is not None:
        efficiency = params.efficiency_pct if params.efficiency_pct is not None else 5.0
        adjustment_params = AdjustmentParams(
            stop_loss=params.stop_loss_pct,
            efficiency=efficiency,
        )
        mae_col = mapping.mae_pct if mapping.mae_pct else None

    # Compute metrics
    calc = MetricsCalculator()
    try:
        metrics, equity_curve, kelly_curve = calc.calculate(
            df=df,
            gain_col=mapping.gain_pct,
            derived=True,
            breakeven_is_win=mapping.breakeven_is_win,
            adjustment_params=adjustment_params,
            mae_col=mae_col,
            fractional_kelly_pct=params.fractional_kelly_pct,
            date_col=mapping.date if mapping.date else None,
            time_col=mapping.time if mapping.time else None,
            flat_stake=params.flat_stake,
            start_capital=params.start_capital,
        )
    except Exception as e:
        return f"Error computing metrics: {type(e).__name__}: {e}"

    result = {
        "alias": params.alias,
        "trades_analyzed": len(df),
        "filters_applied": filter_summary,
        "metrics": _metrics_to_dict(metrics),
    }

    # Include equity curve summary if computed
    if equity_curve is not None and not equity_curve.empty:
        result["flat_stake_equity_curve_rows"] = len(equity_curve)
    if kelly_curve is not None and not kelly_curve.empty:
        result["kelly_equity_curve_rows"] = len(kelly_curve)

    return _truncate(json.dumps(result, indent=2, default=str))


@mcp.tool(
    name="lumen_get_breakdown",
    annotations={
        "title": "Get Breakdown Metrics",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def lumen_get_breakdown(params: GetBreakdownInput) -> str:
    """Get yearly or monthly breakdown metrics for a loaded dataset.

    Calculates aggregated statistics per period including total gain, flat stake PnL,
    max drawdown, trade count, win rate, and average winner/loser.

    Args:
        params (GetBreakdownInput): Validated input containing:
            - alias (str): Dataset alias
            - period (str): 'yearly' or 'monthly'
            - year (int): Required for monthly breakdown
            - filters (Optional[list]): Filter dicts to narrow the data
            - first_trigger_only (bool): Keep only trigger_number == 1
            - stake (float): Fixed stake amount
            - start_capital (float): Starting capital
            - stop_loss_pct (Optional[float]): Stop loss %
            - efficiency_pct (Optional[float]): Efficiency %

    Returns:
        str: JSON with breakdown metrics per period.
    """
    try:
        ds = _get_dataset(params.alias)
    except ValueError as e:
        return f"Error: {e}"

    df = ds.df.copy()
    mapping = ds.mapping
    filter_summary: list[str] = []

    # Check required columns
    if not mapping.date:
        return json.dumps({"error": "No date column mapped. Breakdown requires a date column."})

    # Apply first-trigger filter
    if params.first_trigger_only:
        trig_col = None
        for alias_name in _COLUMN_ALIASES.get("trigger_number", []):
            lower_cols = {c.lower(): c for c in df.columns}
            if alias_name in lower_cols:
                trig_col = lower_cols[alias_name]
                break
        if trig_col:
            df = df[df[trig_col] == 1].reset_index(drop=True)
            filter_summary.append("first_trigger_only=True")

    # Apply user filters
    if params.filters:
        try:
            df = _apply_filters(df, params.filters)
            filter_summary.append(f"{len(params.filters)} filter(s) applied")
        except Exception as e:
            return f"Error applying filters: {e}"

    if len(df) == 0:
        return json.dumps({
            "error": "No rows remain after filtering.",
            "filters_applied": filter_summary,
        }, indent=2)

    # Build adjustment params if stop loss provided
    adjustment_params: AdjustmentParams | None = None
    mae_col: str | None = None
    if params.stop_loss_pct is not None:
        efficiency = params.efficiency_pct if params.efficiency_pct is not None else 5.0
        adjustment_params = AdjustmentParams(
            stop_loss=params.stop_loss_pct,
            efficiency=efficiency,
        )
        mae_col = mapping.mae_pct if mapping.mae_pct else None

    # Create breakdown calculator
    calc = BreakdownCalculator(
        stake=params.stake,
        start_capital=params.start_capital,
        adjustment_params=adjustment_params,
        mae_col=mae_col,
    )

    # Get win/loss column if available
    win_loss_col = None
    for alias_name in ["win_loss", "w_l", "result"]:
        lower_cols = {c.lower(): c for c in df.columns}
        if alias_name in lower_cols:
            win_loss_col = lower_cols[alias_name]
            break

    try:
        if params.period == "yearly":
            breakdown = calc.calculate_yearly(
                df=df,
                date_col=mapping.date,
                gain_col=mapping.gain_pct,
                win_loss_col=win_loss_col,
            )
            available_years = calc.get_available_years(df, mapping.date)
            result = {
                "alias": params.alias,
                "period": "yearly",
                "trades_analyzed": len(df),
                "filters_applied": filter_summary,
                "available_years": available_years,
                "breakdown": breakdown,
            }
        elif params.period == "monthly":
            if params.year is None:
                available_years = calc.get_available_years(df, mapping.date)
                return json.dumps({
                    "error": "Year is required for monthly breakdown.",
                    "available_years": available_years,
                }, indent=2)
            breakdown = calc.calculate_monthly(
                df=df,
                year=params.year,
                date_col=mapping.date,
                gain_col=mapping.gain_pct,
                win_loss_col=win_loss_col,
            )
            result = {
                "alias": params.alias,
                "period": "monthly",
                "year": params.year,
                "trades_analyzed": len(df),
                "filters_applied": filter_summary,
                "breakdown": breakdown,
            }
        else:
            return json.dumps({"error": f"Invalid period '{params.period}'. Use 'yearly' or 'monthly'."})
    except Exception as e:
        return f"Error computing breakdown: {type(e).__name__}: {e}"

    return _truncate(json.dumps(result, indent=2, default=str))


@mcp.tool(
    name="lumen_compare_datasets",
    annotations={
        "title": "Compare Datasets Side-by-Side",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def lumen_compare_datasets(params: CompareDatasetsInput) -> str:
    """Compute and compare metrics for two datasets or two filtered views.

    Returns a side-by-side comparison table of all TradingMetrics fields,
    plus the delta between A and B for numeric fields.

    Args:
        params (CompareDatasetsInput): Validated input containing:
            - alias_a (str): Dataset A alias
            - alias_b (Optional[str]): Dataset B alias (defaults to alias_a)
            - filters_a (Optional[list]): Filters for dataset A
            - filters_b (Optional[list]): Filters for dataset B

    Returns:
        str: JSON with side_a, side_b, and delta dicts of all metric fields.
    """
    alias_b = params.alias_b or params.alias_a

    try:
        ds_a = _get_dataset(params.alias_a)
        ds_b = _get_dataset(alias_b)
    except ValueError as e:
        return f"Error: {e}"

    # Prepare DataFrames
    df_a = ds_a.df.copy()
    df_b = ds_b.df.copy()

    if params.filters_a:
        try:
            df_a = _apply_filters(df_a, params.filters_a)
        except Exception as e:
            return f"Error applying filters_a: {e}"
    if params.filters_b:
        try:
            df_b = _apply_filters(df_b, params.filters_b)
        except Exception as e:
            return f"Error applying filters_b: {e}"

    # Compute metrics for both sides
    calc = MetricsCalculator()

    def _compute(df: pd.DataFrame, mapping: ColumnMapping) -> TradingMetrics:
        metrics, _, _ = calc.calculate(
            df=df,
            gain_col=mapping.gain_pct,
            derived=True,
            breakeven_is_win=mapping.breakeven_is_win,
            date_col=mapping.date if mapping.date else None,
            time_col=mapping.time if mapping.time else None,
        )
        return metrics

    try:
        metrics_a = _compute(df_a, ds_a.mapping)
        metrics_b = _compute(df_b, ds_b.mapping)
    except Exception as e:
        return f"Error computing metrics: {type(e).__name__}: {e}"

    dict_a = _metrics_to_dict(metrics_a)
    dict_b = _metrics_to_dict(metrics_b)

    # Compute deltas for numeric fields
    delta: dict[str, Any] = {}
    for key in dict_a:
        val_a = dict_a[key]
        val_b = dict_b.get(key)
        if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
            if val_a is not None and val_b is not None:
                delta[key] = round(val_b - val_a, 6)

    result = {
        "side_a": {
            "alias": params.alias_a,
            "trades": len(df_a),
            "metrics": dict_a,
        },
        "side_b": {
            "alias": alias_b,
            "trades": len(df_b),
            "metrics": dict_b,
        },
        "delta_b_minus_a": delta,
    }

    return _truncate(json.dumps(result, indent=2, default=str))


@mcp.tool(
    name="lumen_list_loaded",
    annotations={
        "title": "List Loaded Datasets",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def lumen_list_loaded() -> str:
    """Show all currently loaded datasets with their aliases, file paths, row counts, and date ranges.

    Returns:
        str: JSON array of loaded dataset summaries.
    """
    if not _datasets:
        return "No datasets loaded. Use lumen_load_data to load a trade data file."

    items = []
    for ds in _datasets.values():
        items.append(
            {
                "alias": ds.alias,
                "file": ds.file_path,
                "rows": ds.row_count,
                "date_range": ds.date_range,
                "columns": list(ds.df.columns),
                "mapping": {
                    "ticker": ds.mapping.ticker,
                    "date": ds.mapping.date,
                    "time": ds.mapping.time,
                    "gain_pct": ds.mapping.gain_pct,
                    "mae_pct": ds.mapping.mae_pct,
                    "mfe_pct": ds.mapping.mfe_pct,
                },
            }
        )
    return json.dumps(items, indent=2)


# ---------------------------------------------------------------------------
# GUI State Bridge
# ---------------------------------------------------------------------------


def _get_gui_state_dir() -> Path:
    """Return the directory where the Lumen GUI writes state files."""
    return Path.home() / ".lumen" / "state"


@mcp.tool(
    name="lumen_get_gui_state",
    annotations={
        "title": "Get Lumen GUI State",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def lumen_get_gui_state() -> str:
    """Read the current state of the Lumen GUI application.

    Returns source file, sheet, column mapping, filters, adjustment params,
    metrics summary, row counts, and staleness (seconds since last export).
    The GUI must be running with data loaded for this to work.

    Returns:
        str: JSON with full GUI state metadata, or an error message.
    """
    state_dir = _get_gui_state_dir()
    state_file = state_dir / "gui_state.json"

    if not state_file.exists():
        return json.dumps(
            {
                "error": "GUI state not found.",
                "hint": (
                    "Make sure the Lumen GUI is running and has data loaded. "
                    "State files are written to ~/.lumen/state/ automatically."
                ),
            },
            indent=2,
        )

    try:
        payload = json.loads(state_file.read_text(encoding="utf-8"))
    except Exception as e:
        return f"Error reading GUI state: {e}"

    # Calculate staleness
    exported_at = payload.get("exported_at")
    if exported_at:
        try:
            from datetime import UTC, datetime

            ts = datetime.fromisoformat(exported_at)
            staleness = (datetime.now(UTC) - ts).total_seconds()
            payload["staleness_seconds"] = round(staleness, 1)
        except Exception:
            payload["staleness_seconds"] = None

    # Report available parquet files
    payload["baseline_parquet_available"] = (state_dir / "baseline_data.parquet").exists()
    payload["filtered_parquet_available"] = (state_dir / "filtered_data.parquet").exists()

    return json.dumps(payload, indent=2, default=str)


class SyncFromGuiInput(BaseModel):
    """Input for syncing DataFrames from the Lumen GUI."""

    model_config = ConfigDict(extra="forbid")

    alias_prefix: str = Field(
        default="gui",
        description=(
            "Prefix for dataset aliases. Datasets will be stored as "
            '"{prefix}_baseline" and "{prefix}_filtered". Default: "gui".'
        ),
    )


@mcp.tool(
    name="lumen_sync_from_gui",
    annotations={
        "title": "Sync Data from Lumen GUI",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def lumen_sync_from_gui(params: SyncFromGuiInput) -> str:
    """Load DataFrames from the running Lumen GUI into the MCP dataset store.

    Reads baseline and filtered parquet files exported by the GUI and makes
    them available for lumen_query_data and lumen_compute_metrics.

    Args:
        params (SyncFromGuiInput): Validated input containing:
            - alias_prefix (str): Prefix for dataset aliases (default "gui")

    Returns:
        str: JSON with aliases, row counts, columns, and staleness info.
    """
    state_dir = _get_gui_state_dir()
    state_file = state_dir / "gui_state.json"

    if not state_file.exists():
        return json.dumps(
            {
                "error": "GUI state not found.",
                "hint": (
                    "Make sure the Lumen GUI is running and has data loaded. "
                    "State files are written to ~/.lumen/state/ automatically."
                ),
            },
            indent=2,
        )

    # Read metadata for mapping and staleness
    try:
        meta = json.loads(state_file.read_text(encoding="utf-8"))
    except Exception as e:
        return f"Error reading GUI state: {e}"

    mapping_dict = meta.get("column_mapping")
    if not mapping_dict:
        return json.dumps({"error": "No column mapping in GUI state."}, indent=2)

    mapping = ColumnMapping(
        ticker=mapping_dict.get("ticker", ""),
        date=mapping_dict.get("date", ""),
        time=mapping_dict.get("time", ""),
        gain_pct=mapping_dict.get("gain_pct", ""),
        mae_pct=mapping_dict.get("mae_pct", ""),
        mfe_pct=mapping_dict.get("mfe_pct", ""),
        win_loss_derived=True,
    )

    prefix = params.alias_prefix
    result: dict[str, Any] = {"synced": []}

    # Calculate staleness
    exported_at = meta.get("exported_at")
    staleness: float | None = None
    if exported_at:
        try:
            from datetime import UTC, datetime

            ts = datetime.fromisoformat(exported_at)
            staleness = round((datetime.now(UTC) - ts).total_seconds(), 1)
        except Exception:
            pass
    result["staleness_seconds"] = staleness

    source_file = meta.get("source_file", "gui")

    # Load baseline
    baseline_path = state_dir / "baseline_data.parquet"
    if baseline_path.exists():
        try:
            df_baseline = pd.read_parquet(baseline_path)
            alias_b = f"{prefix}_baseline"
            _datasets[alias_b] = LoadedDataset(
                df=df_baseline,
                mapping=mapping,
                file_path=source_file,
                alias=alias_b,
            )
            result["synced"].append(
                {
                    "alias": alias_b,
                    "rows": len(df_baseline),
                    "columns": list(df_baseline.columns),
                }
            )
        except Exception as e:
            result["baseline_error"] = str(e)

    # Load filtered
    filtered_path = state_dir / "filtered_data.parquet"
    if filtered_path.exists():
        try:
            df_filtered = pd.read_parquet(filtered_path)
            alias_f = f"{prefix}_filtered"
            _datasets[alias_f] = LoadedDataset(
                df=df_filtered,
                mapping=mapping,
                file_path=source_file,
                alias=alias_f,
            )
            result["synced"].append(
                {
                    "alias": alias_f,
                    "rows": len(df_filtered),
                    "columns": list(df_filtered.columns),
                }
            )
        except Exception as e:
            result["filtered_error"] = str(e)

    if not result["synced"]:
        result["error"] = "No parquet files found in GUI state directory."
        result["hint"] = "Load data in the Lumen GUI first."

    return json.dumps(result, indent=2, default=str)
