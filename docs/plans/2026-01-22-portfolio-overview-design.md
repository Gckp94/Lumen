# Portfolio Overview Tab Design

## Overview

A new tab for analyzing multiple trading strategies together. Compare a baseline portfolio against adding new candidate strategies to evaluate if they're worth including in the playbook.

## Core Concepts

### Strategy
A single trading system represented by a CSV/XLSX file containing trade history (date, gain_pct, win/loss). Each strategy has configurable position sizing and risk parameters.

### Baseline vs Candidate
- **Baseline**: Your current playbook of strategies (one or more)
- **Candidate**: Strategy being evaluated for inclusion
- A strategy can be marked as baseline, candidate, both, or excluded

### Position Sizing Modes
- **Frac Kelly**: Fractional Kelly criterion (e.g., 0.25 = quarter Kelly)
- **Custom %**: Fixed percentage of account (e.g., 10%)
- **Flat $**: Fixed dollar amount per trade (e.g., $5,000)

### Max Compound
Limits maximum position size regardless of account growth. Example: Account at $600k with 10% position size would normally be $60k, but max compound of $50k caps it at $50k.

### Daily Compounding
All trades on the same day use that day's opening account value for position sizing. Account value updates at the start of each new trading day.

### Simultaneous Allocation
Multiple strategies trading on the same day each calculate position size independently from the same opening account value. No interaction or capping between them.

---

## Layout Structure

```
+-------------------------------------------------------------+
|  TOOLBAR: [+ Add Strategy]              Account: $________  |
+-------------------------------------------------------------+
|                                                             |
|  STRATEGY TABLE (collapsible, ~200px height)                |
|  +-----+--------+----+-----+------+----+------+------+-----+|
|  |Name | File   | BL | CND |Stop% |Eff | Type |Value |MaxC ||
|  +-----+--------+----+-----+------+----+------+------+-----+|
|                                                             |
+-------------------------------------------------------------+
|                                                             |
|  CHARTS (fills remaining space, side-by-side)               |
|  +---------------------------+  +---------------------------+|
|  |   EQUITY CURVE            |  |   DRAWDOWN                ||
|  |   [Trades | Date]         |  |   [Trades | Date]         ||
|  |                           |  |                           ||
|  +---------------------------+  +---------------------------+|
|                                                             |
|  LEGEND: [ ] Strategy A  [ ] Strategy B  | [ ] Baseline  [ ] Combined |
+-------------------------------------------------------------+
```

---

## Component Details

### 1. Toolbar

| Element | Description |
|---------|-------------|
| **+ Add Strategy** | Opens import dialog to add new strategy from file |
| **Account Start** | Global starting account value (e.g., $100,000) |

### 2. Strategy Table

| Column | Width | Type | Description |
|--------|-------|------|-------------|
| **Name** | 120px | Editable text | Custom strategy label |
| **File** | 140px | Button/label | Filename (click to change), tooltip shows full path |
| **BL** | 40px | Checkbox | Include in baseline (cyan highlight when checked) |
| **CND** | 40px | Checkbox | Mark as candidate (amber highlight when checked) |
| **Stop %** | 70px | Spin box | Stop loss percentage (e.g., 2.5) |
| **Efficiency** | 70px | Spin box | Trade efficiency multiplier (e.g., 0.85) |
| **Size Type** | 100px | Dropdown | Frac Kelly / Custom % / Flat $ |
| **Size Value** | 80px | Spin box | Value for selected size type |
| **Max Compound** | 100px | Spin box | Maximum position size limit (e.g., $50,000) |
| **Menu (three dots)** | 30px | Button | Delete, Duplicate, Reset to defaults |

**Behaviors:**
- Row hover shows subtle highlight
- All numeric fields edit in-place
- Right-click row for context menu
- Empty state: "Drop CSV/XLSX files here or click + Add Strategy"

### 3. Import Dialog

Triggered when adding a new strategy or dropping a file.

```
+-----------------------------------------------------------+
|  Import Strategy                                      X   |
+-----------------------------------------------------------+
|                                                           |
|  File: [strategy_trades.csv]               [Browse...]    |
|                                                           |
|  --------------- Column Mapping ---------------           |
|                                                           |
|  Date Column        [ trade_date        v ]               |
|  Gain % Column      [ gain_pct          v ]               |
|  Win/Loss Column    [ outcome           v ]               |
|                                                           |
|  --------------- Preview (first 5 rows) ---------------   |
|  +--------------+-----------+---------+                   |
|  | trade_date   | gain_pct  | outcome |                   |
|  +--------------+-----------+---------+                   |
|  | 2024-01-15   | 2.34      | W       |                   |
|  | 2024-01-16   | -1.20     | L       |                   |
|  | 2024-01-18   | 1.85      | W       |                   |
|  +--------------+-----------+---------+                   |
|                                                           |
|  Strategy Name: [Strategy_trades      ]                   |
|                                                           |
|                           [Cancel]  [Import Strategy]     |
+-----------------------------------------------------------+
```

**Behaviors:**
- Dropdowns populated with all column headers from file
- Preview table updates live as mappings change
- Strategy name auto-filled from filename, editable
- Import button disabled until all three columns mapped
- Win/Loss accepts: W/L, Win/Loss, 1/0, TRUE/FALSE (auto-detected)

### 4. Charts

Two side-by-side charts filling the remaining vertical space.

**Equity Curve (left):**
- Y-axis: Account value ($)
- X-axis: Toggle between "Trades" (sequential) or "Date"
- Shows growth of account over time

**Drawdown (right):**
- Y-axis: Drawdown percentage (0% to -X%)
- X-axis: Toggle between "Trades" or "Date" (synced with equity curve optional)
- Shows peak-to-trough declines

**Both charts:**
- Hover crosshair with tooltip (date, value, % change)
- Zoom/pan synchronized between charts

### 5. Shared Legend

Spans bottom of chart area, controls visibility for both charts.

| Element | Color | Description |
|---------|-------|-------------|
| Individual strategies | Distinct palette (cyan, amber, magenta, lime, etc.) | Toggle to show/hide that strategy's line |
| **Baseline** | White/light gray, dashed | Aggregate equity curve of all baseline strategies |
| **Combined** | Bright green, solid | Aggregate of baseline + candidate strategies |

**Behaviors:**
- Checkbox toggles visibility on both charts
- Double-click to "solo" (hide all others)

---

## Color Scheme

| Element | Color |
|---------|-------|
| Baseline checkbox (checked) | Cyan background |
| Candidate checkbox (checked) | Amber background |
| Baseline aggregate line | White/light gray, dashed |
| Combined aggregate line | Bright green, solid |
| Individual strategy lines | Rotating palette: cyan, amber, magenta, lime, coral, violet |

---

## Interaction Patterns

### Real-time Updates
Charts recalculate and redraw when:
- Strategy settings change (stop%, position size, etc.)
- Baseline/Candidate checkboxes toggle
- Account start amount changes
- Debounced ~300ms to prevent flickering

### Empty/Partial States
- **No strategies**: Charts show empty axes with message "Add strategies to see equity curves"
- **No baseline selected**: Baseline line hidden, Combined shows only candidates
- **No candidates selected**: Only baseline lines visible, no Combined line
- **Single strategy**: Shows individual equity curve with configured position sizing

### Edge Cases
- **Same date across strategies**: All use day's opening account value (simultaneous allocation)
- **Date gaps**: Line connects across gaps; Date mode shows actual dates (not evenly spaced)
- **Negative account**: Stop at $0, show warning badge on strategy row

---

## Persistence

Strategy configurations saved to JSON config file:
- Strategy name, file path, column mappings
- All parameter values (stop%, efficiency, position sizing, max compound)
- Baseline/Candidate checkbox states
- Account start value

On app reopen:
- Restore all strategies and settings
- If file missing, show warning icon in File column

---

## File Structure

```
src/
  tabs/
    portfolio_overview.py      # Main tab widget
  core/
    portfolio_calculator.py    # Equity/drawdown calculation logic
  ui/
    import_strategy_dialog.py  # Column mapping dialog
    strategy_table.py          # Table widget with inline editing
```

---

## Data Flow

1. User imports CSV -> Column mapping dialog -> Strategy added to table
2. User configures strategy parameters in table
3. On any change:
   - Gather all strategies marked baseline/candidate
   - Load trade data from CSV files
   - Merge trades chronologically by date
   - For each day:
     - Calculate position sizes using day's opening account value
     - Apply all trades, update account value
   - Calculate drawdown series from equity curve
4. Update both charts with new data
5. Persist configuration to JSON
