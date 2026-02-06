# Time Stop Tab Design

## Overview

Add a new "Time Stop" sub-tab to the Statistics Tab that analyzes trade performance at fixed time intervals after entry. This enables time-based stop-out strategies where losing trades are partially exited at specific time points.

## Requirements Summary

- **New sub-tab**: "Time Stop" as 4th tab in Statistics Tab
- **Two tables**: Time Statistics and Time Stop
- **Fixed time intervals**: 10, 20, 30, 60, 90, 120, 150, 180, 240 minutes
- **Scale Out control**: Spinbox (0-100%, default 50%, step 10%)
- **Export functionality**: CSV export for both tables
- **Color coding**: Same gradient system as existing Statistics tables

---

## Data Architecture

### New Column Mappings

Add 9 new optional fields to `ColumnMapping` in `src/core/models.py`:

```python
price_10_min_after: str | None = None
price_20_min_after: str | None = None
price_30_min_after: str | None = None
price_60_min_after: str | None = None
price_90_min_after: str | None = None
price_120_min_after: str | None = None
price_150_min_after: str | None = None
price_180_min_after: str | None = None
price_240_min_after: str | None = None
```

### Computed Columns

During file loading/processing, compute percentage change columns for each mapped time interval:

```python
change_X_min = (trigger_price_unadjusted - price_X_min_after) / trigger_price_unadjusted
```

These columns (`change_10_min`, `change_20_min`, etc.) are added to the DataFrame, similar to `adjusted_gain_pct`.

### Time Intervals Constant

```python
TIME_STOP_INTERVALS = [10, 20, 30, 60, 90, 120, 150, 180, 240]
```

Tables dynamically show only rows for intervals that have mapped columns.

---

## Time Statistics Table

### Purpose

Show gain/loss statistics and recovery probabilities at each time interval.

### Columns

| Column | Calculation |
|--------|-------------|
| Minutes After Entry | Fixed label: "10 Mins", "20 Mins", etc. |
| Avg. Gain % | Mean of `change_X_min` where `change_X_min > 0` |
| Median Gain % | Median of `change_X_min` where `change_X_min > 0` |
| Avg. Loss % | Mean of `change_X_min` where `change_X_min <= 0` |
| Median Loss % | Median of `change_X_min` where `change_X_min <= 0` |
| Prob. of Profit (Red) % | Of trades RED at time X, % that end profitable at final close |
| Prob. of Profit (Green) % | Of trades GREEN at time X, % that end profitable at final close |

### Calculation Details

```python
def calculate_time_statistics_row(df, change_col, final_gain_col, interval):
    changes = df[change_col]
    final_gains = df[final_gain_col]

    # Split into winners and losers at this time
    winners_mask = changes > 0
    losers_mask = changes <= 0

    # Gain/Loss stats
    avg_gain = changes[winners_mask].mean() * 100 if winners_mask.any() else None
    median_gain = changes[winners_mask].median() * 100 if winners_mask.any() else None
    avg_loss = changes[losers_mask].mean() * 100 if losers_mask.any() else None
    median_loss = changes[losers_mask].median() * 100 if losers_mask.any() else None

    # Recovery probabilities
    red_trades = df[losers_mask]
    green_trades = df[winners_mask]

    prob_profit_red = (red_trades[final_gain_col] > 0).mean() * 100 if len(red_trades) > 0 else None
    prob_profit_green = (green_trades[final_gain_col] > 0).mean() * 100 if len(green_trades) > 0 else None

    return {
        "Minutes After Entry": f"{interval} Mins",
        "Avg. Gain %": avg_gain,
        "Median Gain %": median_gain,
        "Avg. Loss %": avg_loss,
        "Median Loss %": median_loss,
        "Prob. of Profit (Red) %": prob_profit_red,
        "Prob. of Profit (Green) %": prob_profit_green,
    }
```

---

## Time Stop Table

### Purpose

Compare "exit partial position if RED at time X" strategy vs full hold.

### Blending Logic

```python
if change_X_min <= 0:  # RED at time X
    blended_return = scale_out_pct * change_X_min + (1 - scale_out_pct) * final_gain
else:  # GREEN at time X
    blended_return = final_gain  # No scaling, hold full position
```

### Columns

| Column | Description |
|--------|-------------|
| Minutes After Entry | Fixed label |
| Blended Win % | % of trades with positive blended return |
| Full Hold Win % | % of trades with positive final return |
| Blended EV % | Average blended return per trade |
| Full Hold EV % | Average final return per trade |
| Blended Profit Ratio | Avg blended winner / Avg blended loser |
| Full Hold Profit Ratio | Avg final winner / Avg final loser |
| Blended Edge % | `(Profit Ratio + 1) * Win Rate - 1` |
| Full Hold Edge % | Same formula for full hold |
| Blended EG % | Expected Growth via Kelly formula |
| Full Hold EG % | Same formula for full hold |
| Blended Kelly Stake % | `Edge % / Profit Ratio` |
| Full Hold Kelly Stake % | Same formula for full hold |

### Calculation Details

```python
def calculate_time_stop_row(df, change_col, final_gain_col, interval, scale_out_pct):
    changes = df[change_col]
    final_gains = df[final_gain_col]

    # Calculate blended returns
    red_mask = changes <= 0
    blended_returns = final_gains.copy()
    blended_returns[red_mask] = (
        scale_out_pct * changes[red_mask] +
        (1 - scale_out_pct) * final_gains[red_mask]
    )

    # Calculate metrics for both
    blended_metrics = _calculate_return_metrics(blended_returns)
    full_hold_metrics = _calculate_return_metrics(final_gains)

    return {
        "Minutes After Entry": f"{interval} Mins",
        "Blended Win %": blended_metrics["win_pct"],
        "Full Hold Win %": full_hold_metrics["win_pct"],
        "Blended EV %": blended_returns.mean() * 100,
        "Full Hold EV %": final_gains.mean() * 100,
        "Blended Profit Ratio": blended_metrics["profit_ratio"],
        "Full Hold Profit Ratio": full_hold_metrics["profit_ratio"],
        "Blended Edge %": blended_metrics["edge_pct"],
        "Full Hold Edge %": full_hold_metrics["edge_pct"],
        "Blended EG %": blended_metrics["eg_pct"],
        "Full Hold EG %": full_hold_metrics["eg_pct"],
        "Blended Kelly Stake %": blended_metrics["kelly_pct"],
        "Full Hold Kelly Stake %": full_hold_metrics["kelly_pct"],
    }
```

---

## UI Layout

```
Statistics Tab
├── MAE/MFE (existing)
├── Stop Loss/Offset (existing)
├── Scaling (existing)
└── Time Stop (NEW)
    ├── Control Bar
    │   ├── Scale Out: [50%] spinbox
    │   └── Export CSV button (right-aligned)
    ├── Time Statistics Table
    ├── Time Stop Table
    └── Legend (gradient color key)
```

### Controls

- **Scale Out Spinbox**: 0-100%, default 50%, step 10%
- **Export Button**: Exports both tables to single CSV with section headers

### Color Coding

Uses existing `GradientStyler` from Statistics Tab:
- `GRADIENT_LOW` (coral-red) for low values
- `GRADIENT_MID` (neutral gray) for middle values
- `GRADIENT_HIGH` (teal-green) for high values
- Optimal row (best EG%) gets gold/amber border highlight

### Column Exclusions from Gradient

- "Minutes After Entry" column excluded (label column)

---

## File Changes

### New/Modified Files

1. **`src/core/models.py`** - Add 9 optional column mapping fields
2. **`src/core/statistics.py`** - Add calculation functions:
   - `calculate_time_statistics_table()`
   - `calculate_time_stop_table()`
   - `_calculate_time_statistics_row()`
   - `_calculate_time_stop_row()`
3. **`src/tabs/statistics_tab.py`** - Add UI:
   - `_create_time_stop_widget()` method
   - Time Stop tab to tab widget
   - Signal connections for spinbox
   - Export handler
4. **`src/tabs/data_input.py`** - Add column mapping UI fields
5. **`src/core/file_loader.py`** - Compute `change_X_min` columns during load

### Constants

```python
# In src/core/statistics.py
TIME_STOP_INTERVALS = [10, 20, 30, 60, 90, 120, 150, 180, 240]
```

---

## Visual Design

See mockup: `docs/designs/time-stop-tab-design.html`

Key design elements:
- Follows Lumen Observatory theme
- Azeret Mono for data, Geist for UI labels
- Dark theme with gradient color coding
- Optimal row highlighted with gold border
- Responsive table scrolling

---

## Signal Flow

```
User changes Scale Out spinbox
    ↓
_on_scale_out_changed()
    ↓
_refresh_time_stop_table()
    ↓
calculate_time_stop_table(df, scale_out_pct)
    ↓
_populate_table() updates UI
```

Data updates flow through existing signals:
- `baseline_calculated` → refresh all tables
- `filtered_data_updated` → refresh all tables
- `adjustment_params_changed` → refresh all tables

---

## Export Format

Single CSV file with both tables:

```csv
# Time Statistics
Minutes After Entry,Avg. Gain %,Median Gain %,Avg. Loss %,Median Loss %,Prob. of Profit (Red) %,Prob. of Profit (Green) %
10 Mins,2.45,1.82,-1.85,-1.24,42.30,78.50
...

# Time Stop (Scale Out: 50%)
Minutes After Entry,Blended Win %,Full Hold Win %,Blended EV %,Full Hold EV %,...
10 Mins,68.50,66.20,2.85,2.42,...
...
```
