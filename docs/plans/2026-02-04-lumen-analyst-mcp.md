# Lumen Analyst MCP Server

## Overview

An MCP (Model Context Protocol) server that gives Claude Code direct access to Lumen's trade data and analytics engine, enabling Claude to act as a data analyst and quant advisor during analysis sessions.

The server lives inside the Lumen repo at `mcp_server/` and imports Lumen's core modules directly. It loads Excel/CSV trade data files, applies column mappings, and exposes tools for raw pandas analysis and Lumen's full metrics suite. No modifications to Lumen's existing codebase are required.

## Architecture

- **Location:** `mcp_server/` in Lumen repo root
- **Transport:** stdio (standard MCP pattern for Claude Code)
- **SDK:** `mcp` Python SDK with `@server.tool()` decorators
- **Entry point:** `python -m mcp_server` via `mcp_server/__main__.py`
- **State:** In-memory `SessionState` holding loaded datasets, persists for the MCP session duration
- **Imports:** Lumen's `MetricsCalculator`, `TradingMetrics`, `ColumnMapping`, `FilterCriteria`, `AdjustmentParams`, and portfolio calculators

## Tools

### Data Loading & Inspection

**`load_data(file_path, alias?, sheet?, column_mapping?)`**
- Load an Excel/CSV file into memory
- Auto-detects column mapping using heuristic matching (e.g. "gain"/"return" → `gain_pct`, "symbol" → `ticker`)
- Falls back to asking Claude to specify mapping if auto-detection fails
- Returns: column names, row count, detected mapping, date range
- Optional `alias` (defaults to filename stem) for referencing in other tools
- Optional `sheet` for multi-sheet Excel files
- Optional explicit `column_mapping` override

**`describe_data(alias)`**
- Summary statistics for a loaded dataset
- Returns: row count, date range, column dtypes, value distributions for key columns, active column mapping

### Raw Analysis

**`query_data(alias, expression)`**
- Execute a pandas expression against the loaded DataFrame
- Expression is a string evaluated with `df` (the DataFrame), `pd` (pandas), and `np` (numpy) in scope
- Column names are mapped to Lumen names (`gain_pct`, `ticker`, `date`, etc.); original columns preserved as additional columns
- Results truncated to 50,000 characters with head/tail for large DataFrames
- No access to `os`, `subprocess`, `open`, or other system modules

### Lumen Metrics

**`compute_metrics(alias, filters?, first_trigger_only?, adjustment_params?)`**
- Run Lumen's `MetricsCalculator` on the loaded data
- Returns the full `TradingMetrics` output: win rate, Kelly, EV, RR ratio, drawdowns, equity curves, streaks, expected growth, etc.
- Optional `filters`: list of `{column, operator, value}` dicts matching Lumen's `FilterCriteria` format (operators: `>=`, `<=`, `==`, `!=`, `in`)
- Optional `first_trigger_only`: boolean, filter to first triggers per ticker/date
- Optional `adjustment_params`: `{stop_loss_pct, position_size, starting_capital}` for PnL and Kelly calculations

### Comparison

**`compare_datasets(alias_a, alias_b, filters_a?, filters_b?)`**
- Compute metrics for two datasets (or two filter views of the same dataset)
- Returns side-by-side comparison table of all TradingMetrics fields
- Useful for A/B comparisons: before/after filter, strategy A vs B, different time periods

### Utility

**`list_loaded()`**
- Show all currently loaded datasets
- Returns: alias, file path, row count, date range, column mapping for each

## Data Handling

### Column Mapping
- Auto-detection uses heuristic name matching plus Lumen's `ColumnMapping.validate()`
- Required fields: `date`, `gain_pct`
- Optional fields: `time`, `ticker`, `trigger_number`, `mae`, `mfe`, plus any extra feature columns
- If auto-detection fails, returns available columns so Claude can call `load_data` again with explicit mapping
- Ambiguous mappings (two source columns matching one Lumen field) pick best match and note the ambiguity

### Filter Format
Filters use the same structure as Lumen's `FilterCriteria`:
```json
[
  {"column": "ticker", "operator": "==", "value": "AAPL"},
  {"column": "gain_pct", "operator": ">=", "value": -5},
  {"column": "date", "operator": ">=", "value": "2024-01-01"}
]
```

## File Structure

```
mcp_server/
  __init__.py
  __main__.py        # Entry point: python -m mcp_server
  server.py          # MCP server with tool definitions
```

## Configuration

Add to `.mcp.json` at repo root:
```json
{
  "mcpServers": {
    "lumen-analyst": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "<repo_root>"
    }
  }
}
```

## Error Handling

- **File not found / corrupt:** Clear error with available columns for retry with explicit mapping
- **Empty filter results:** Returns `TradingMetrics.empty()` with note that filter was too restrictive
- **Query syntax errors:** Error message returned directly so Claude can self-correct
- **Large results:** Truncated to 50,000 chars with head/tail and full row count noted
- **Alias conflicts:** Second load appends numeric suffix; `list_loaded` shows current state
- **Column mapping ambiguity:** Best match selected, ambiguity noted in response

## Dependencies

Only existing Lumen dependencies plus the MCP SDK:
- `pandas`, `openpyxl` (already in Lumen)
- `mcp` (new — the MCP Python SDK)
