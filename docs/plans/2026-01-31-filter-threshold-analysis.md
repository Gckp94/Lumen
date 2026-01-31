# Filter Threshold Analysis Tab Design

## Overview

Repurpose the Parameter Sensitivity tab to show how trading metrics change when varying a single filter threshold. This enables "what-if" analysis for filter values.

## User Story

As a trader, I want to see how my metrics change when I adjust a filter threshold up or down, so I can understand the sensitivity of my strategy to filter parameters.

## UI Layout

### Sidebar (Left Panel, ~280px)

1. **Filter Selector** - Dropdown listing only currently-applied filters
   - Format: "Column > Value" or "Column < Value" or "Column: Min - Max"
   - Only shows filters from Feature Explorer

2. **Bound Toggle** - Radio buttons, only visible when selected filter has both min AND max
   - Options: "Vary Min" / "Vary Max"

3. **Step Size** - Numeric spin box
   - Auto-calculated default based on current value magnitude:
     - Value < 1: step = 0.1
     - Value 1-10: step = 1
     - Value 10-100: step = 5
     - Value 100-1000: step = 50
     - Value > 1000: step = 100
   - User can override manually

4. **Current Value Display** - Read-only field showing the threshold being varied

### Main Area (Right Panel)

Single table with 11 rows showing metrics at varied threshold values.

## Table Structure

### Columns

| Column | Description | Format |
|--------|-------------|--------|
| Threshold | The varied filter value | Number with appropriate precision |
| # Trades | Count of trades passing all filters | Integer |
| EV % | Expected value per trade | X.XX% |
| Win % | Winners / total trades | X.X% |
| Median Winner % | Median winning trade return | X.XX% |
| Profit Ratio | Avg winner / abs(avg loser) | X.XX |
| Edge % | (Profit Ratio + 1) × Win Rate - 1 | X.XX% |
| EG % | Expected geometric growth at full Kelly | X.XX% |
| Full Kelly % | Edge % / Profit Ratio | X.XX% |
| Max Loss % | % of trades hitting stop loss | X.X% |

### Row Structure

- 11 rows total: 5 steps below current, current value, 5 steps above current
- Ordered ascending by threshold value
- Current threshold row highlighted with distinct background
- Thresholds can go negative (no floor at 0)

### Delta Display

- Each cell shows: `value (Δ+X.X%)` or `value (Δ-X.X%)`
- Delta is difference from the current (highlighted) row
- Green text for improvements, red for degradations
- Current row shows no delta

## Calculation Logic

### Threshold Generation

1. Get current filter value as center point
2. Generate 5 values below: `[center - 5*step, center - 4*step, ..., center - step]`
3. Center value (current)
4. Generate 5 values above: `[center + step, ..., center + 5*step]`

### Per-Threshold Calculation

For each threshold value:

1. Clone the current filter set
2. Replace the selected filter's min or max bound with the new threshold
3. Apply all filters to baseline data using `FilterEngine.apply_filters()`
4. Calculate metrics using `MetricsCalculator.calculate()` with:
   - Stop loss from adjustment params
   - Efficiency from adjustment params  
   - MAE column for max loss % calculation

### Metric Formulas

All calculations use stop-loss and efficiency adjusted gains:

- **EV %**: `(win_rate × avg_winner) + ((1 - win_rate) × avg_loser)`
- **Win %**: `winner_count / total_trades × 100`
- **Median Winner %**: Median of winning trade returns
- **Profit Ratio**: `avg_winner / abs(avg_loser)`
- **Edge %**: `((profit_ratio + 1) × win_rate - 1) × 100`
- **EG %**: `((1 + R × S)^p × (1 - S)^(1-p) - 1) × 100` where R=profit_ratio, S=kelly_stake, p=win_rate
- **Full Kelly %**: `edge / profit_ratio × 100`
- **Max Loss %**: `count(MAE > stop_loss) / total_trades × 100`

## Edge Cases

### Empty States

- **No filters applied**: Show message "Add filters in Feature Explorer to analyze thresholds"
- **No data after filtering**: Row shows "0" for # Trades, dashes for other metrics
- **Single trade remaining**: Metrics calculated, shown in italic as low confidence

### Filter Updates

- Filter dropdown auto-refreshes when filters change in Feature Explorer
- If selected filter is removed, reset to "Select a filter..." placeholder
- Table clears until new filter selected

### Adjustment Params

- Stop loss and efficiency values come from Data Input / PnL Trading tab
- If not configured, use defaults (stop_loss=100%, efficiency=100%)
- Recalculate when adjustment params change

## File Changes

### Files to Modify

| File | Changes |
|------|---------|
| `src/tabs/parameter_sensitivity.py` | Replace UI with new sidebar + table layout |
| `src/core/parameter_sensitivity.py` | Replace engine with threshold analysis calculation logic |

### Dependencies (Reuse Existing)

- `src/core/metrics.py` - `MetricsCalculator.calculate()`
- `src/core/statistics.py` - `_calculate_return_metrics()`, `calculate_expected_growth()`
- `src/core/filter_engine.py` - `FilterEngine.apply_filters()`
- `src/core/models.py` - `FilterCriteria`, `TradingMetrics`

## Performance

- Calculations run in background `QThread` worker
- Progress indicator shown during computation
- Cancel button available for long-running analysis
- Results cached until filters or params change
