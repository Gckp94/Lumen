# Chart Viewer Design

## Overview

A Chart Viewer tab inside Lumen that displays candlestick charts for filtered trades, with entry/exit markers calculated dynamically based on user-configured scaling rules.

## Components

1. **Chart Viewer Tab** - New dockable panel with candlestick chart and controls
2. **Trade Browser Panel** - List of filtered trades with navigation (prev/next)
3. **Price Data Loader** - Service to load and aggregate parquet files
4. **Exit Simulator** - Logic to calculate exits based on entry, stop, and scaling config

## Data Flow

```
User selects trade → Load price data for ticker/date →
Apply resolution/aggregation → Simulate exits using scaling config →
Render chart with markers
```

## Data Sources

### Trade Data (from filtered trades)
- Entry time
- Entry price
- Ticker
- Date

### Stop Level
- Read from existing config (Data Input / PnL Trading Stats)
- No duplicate configuration in Chart Viewer

### Price Data (all unadjusted)

| Path | Resolution |
|------|------------|
| `d:\Daily-Level\YYYY-MM-DD.parquet` | Daily bars |
| `d:\Minute-Level\YYYY-MM-DD.parquet` | 1-minute bars |
| `d:\Second-Level\YYYY-MM-DD.parquet` | 1-second bars |

Each file contains all tickers for that date.

## UI Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ [Resolution: ▼ 1-Min] [Zoom: ▼ Trade ± 30min]  Trade Info Box  │
├─────────────────┬───────────────────────────────────────────────┤
│ Trade Browser   │                                               │
│ ┌─────────────┐ │                                               │
│ │ AAPL 09:32  │ │          Candlestick Chart                    │
│ │ MSFT 10:15  │◄│          (pyqtgraph)                          │
│ │ TSLA 11:02  │ │                                               │
│ │ ...         │ │     ────────── stop level ──────────          │
│ └─────────────┘ │     ────────── profit target ────────         │
│ [◄ Prev][Next ►]│          ▲ entry    ▼ exit₁  ▼ exit₂          │
├─────────────────┤                                               │
│ Scaling Config  │                                               │
│ [50]% at [35]%  │                                               │
│ profit, rest at │                                               │
│ close           │                                               │
└─────────────────┴───────────────────────────────────────────────┘
```

### Controls

- **Resolution dropdown**: 1s, 5s, 15s, 30s, 1m, 2m, 5m, 15m, 30m, 60m, Daily
- **Zoom dropdown**: Trade only, ±15min, ±30min, ±60min, Full session
- **Trade info box**: Ticker, date, entry price/time, PnL, direction
- **Trade browser**: Scrollable list + prev/next buttons
- **Scaling config**: Simple preset (X% at Y% profit, rest at close)

### UI Mockup

See `docs/designs/chart-viewer-ui.html` for high-fidelity visual design.

## Resolution & Aggregation

### Resolution to Source Mapping

| Resolution | Source File |
|------------|-------------|
| 1s, 5s, 15s, 30s | Second-Level |
| 1m, 2m, 5m, 15m, 30m, 60m | Minute-Level |
| Daily | Daily-Level |

### Aggregation Logic

For aggregated resolutions (2m, 5m, etc. from 1-minute; 5s, 15s, etc. from 1-second):

- Group bars into time buckets (floor timestamp to nearest N)
- Open = first bar's open
- High = max of all highs
- Low = min of all lows
- Close = last bar's close
- Volume = sum of volumes (if present)

## Exit Simulation

### Inputs

- Entry time and price (from trade data)
- Stop level (from existing config)
- Scaling config: X% of position at Y% profit, rest at close
- Price bars (loaded from parquet)
- Session close time: 4:00 PM

### Simulation Flow

```
For each bar after entry:
  1. Check if low ≤ stop level → Stop hit, exit remaining position
  2. Check if high ≥ profit target (entry × (1 + Y%)) → Scale out X%
  3. Check if time = session close → Exit remaining position

Track: exit_time, exit_price, position_% for each exit event
```

### Output

```python
[
  {"time": "10:45", "price": 152.30, "pct": 50, "reason": "profit_target"},
  {"time": "16:00", "price": 151.80, "pct": 50, "reason": "session_close"}
]
```

## Chart Markers & Overlays

1. **Entry point** - Blue marker with price/time label
2. **Exit points** - Green markers showing scaled exits with % and price
3. **Stop level** - Red dashed horizontal line
4. **Profit target** - Orange dashed horizontal line
5. **Trade info overlay** - PnL, duration, size
6. **VWAP** - Purple line (limited indicators to start)

## Integration Points

### "View Chart" Action

Add to existing tables:
- Statistics tab trade tables
- Feature Explorer filtered trade list
- PnL Stats trade breakdown tables

Implementation:
- Right-click context menu with "View Chart"
- Double-click row also opens chart
- Both select the trade and switch focus to Chart Viewer tab

### Filtered Trades Source

Trade Browser pulls from same filtered dataset used by other tabs:
- Updates automatically when filters change
- Maintains consistency across application

## Error Handling

### Missing Price Data

If parquet file doesn't exist for trade's date:
- Show message: "Price data not available for [date]"
- Trade Browser shows trade grayed out
- User can navigate to other trades

### Ticker Not in File

If ticker not found in parquet file:
- Show message: "No data for [TICKER] on [date]"

### Partial Session Data

If price data doesn't cover full session:
- Display what's available
- Show warning if entry time falls outside available data

### Stop Hit Before Scale-out

- Single exit marker at stop price
- All position exits at once
- PnL shows the loss

### Multi-day Trades

- For now: only show entry day's data
- Future enhancement: stitch multiple days together

## File Structure

### New Files

```
src/
├── tabs/
│   └── chart_viewer.py       # Main Chart Viewer tab widget
├── core/
│   └── price_data.py         # Price data loader & aggregation
│   └── exit_simulator.py     # Exit calculation logic
└── ui/
    └── trade_browser.py      # Trade Browser panel component
```

### Modified Files

- `src/tabs/statistics_tab.py` - Add "View Chart" context menu
- `src/tabs/feature_explorer.py` - Add "View Chart" context menu
- `src/core/app_state.py` - Expose filtered trades for Chart Viewer
- `src/main.py` - Register Chart Viewer tab with docking system

## Dependencies

No new dependencies required:
- `pyqtgraph` - Already used, for candlestick rendering
- `pandas` / `pyarrow` - Already used, for parquet loading

## Future Enhancements (Out of Scope)

- Adjusted price data toggle (when data becomes available)
- Additional indicators beyond VWAP
- Multi-scale exit configuration (2-3 levels)
- Multi-day trade visualization
- Configurable session close time
