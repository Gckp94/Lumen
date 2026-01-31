# Profit/Loss Chance Tables Design

## Overview

Add a new "Profit/Loss Chance" sub-tab to the Statistics tab with two tables analyzing trade probabilities based on MFE (Maximum Favorable Excursion) and MAE (Maximum Adverse Excursion) thresholds.

## Data Model & Calculations

### Bucket Definition

- Fixed buckets at 5%, 10%, 15%, 20%, 25%, 30%, 35%, 40%
- A trade appears in all buckets it reached (e.g., 25% MFE trade appears in 5%, 10%, 15%, 20%, 25% buckets)

### Chance of Profit Table (MFE-based)

For each bucket, calculate metrics on trades where `mfe_pct >= bucket_threshold`:

| Column | Formula |
|--------|---------|
| Profit Reached % | Bucket threshold (5%, 10%, etc.) |
| Chance of Next Profit % | count(mfe_pct >= next_bucket) / count(mfe_pct >= current_bucket) |
| Chance of Max Loss % | count(mae_pct > stop_loss) / count(mfe_pct >= current_bucket) |
| Win % | count(gain_pct > 0) / total_in_bucket |
| Profit Ratio | mean(gain_pct where gain_pct > 0) / abs(mean(gain_pct where gain_pct < 0)) |
| Edge % | (Profit Ratio + 1) × Win% - 1 |
| EG % | ((1 + Profit_Ratio × Kelly) ^ Win%) × ((1 - Kelly) ^ (1 - Win%)) - 1 |

Where Kelly = Edge% / Profit Ratio (calculated internally, not displayed).

### Chance of Loss Table (MAE-based)

For each bucket, calculate metrics on trades where `mae_pct >= bucket_threshold`:

| Column | Formula |
|--------|---------|
| Loss Reached % | Bucket threshold (5%, 10%, etc.) |
| Chance of Next Loss % | count(mae_pct >= next_bucket) / count(mae_pct >= current_bucket) |
| Chance of Profit % | count(gain_pct > 0) / count(mae_pct >= current_bucket) |
| Win % | count(gain_pct > 0) / total_in_bucket |
| Profit Ratio | mean(gain_pct where gain_pct > 0) / abs(mean(gain_pct where gain_pct < 0)) |
| Edge % | (Profit Ratio + 1) × Win% - 1 |
| EG % | Same formula as Profit table |

### Edge Cases

- 40% row: "Chance of Next %" displays "—" (no 45% bucket)
- No losing trades in bucket: Profit Ratio = "—"
- No winning trades in bucket: Profit Ratio = 0
- Empty bucket: entire row displays "—"

## UI Structure

### New Sub-Tab: "Profit/Loss Chance"

- Added to Statistics tab's tab widget
- Position: After existing tabs (Scaling, MAE/MFE, Stop Loss/Offset)

### Layout (Stacked Vertically)

```
┌─────────────────────────────────────────┐
│  Chance of Profit                       │
│  ┌───────────────────────────────────┐  │
│  │ [Table with 8 rows × 7 columns]   │  │
│  └───────────────────────────────────┘  │
│                                         │
│  Chance of Loss                         │
│  ┌───────────────────────────────────┐  │
│  │ [Table with 8 rows × 7 columns]   │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### Table Styling

- Uses existing `_create_table()` method for consistency
- Gradient coloring via existing `GradientStyler`
- Export button for markdown export (existing pattern)

### Column Headers

**Profit Table:**
Profit Reached %, Chance of Next %, Chance of Max Loss %, Win %, Profit Ratio, Edge %, EG %

**Loss Table:**
Loss Reached %, Chance of Next %, Chance of Profit %, Win %, Profit Ratio, Edge %, EG %

## Implementation Structure

### New Functions in `src/core/statistics.py`

```python
def calculate_profit_chance_table(df, mapping, params) -> pd.DataFrame
def calculate_loss_chance_table(df, mapping, params) -> pd.DataFrame
def _calculate_bucket_metrics(df, bucket_col, bucket_threshold, next_threshold, mapping, params) -> dict
```

### Changes to `src/tabs/statistics_tab.py`

1. Add `_create_profit_loss_chance_widget()` method (follows `_create_stop_loss_offset_widget()` pattern)
2. Add `self._profit_chance_table` and `self._loss_chance_table` attributes
3. Register new tab in `_setup_ui()`
4. Add table population logic in `_update_all_tables()`
5. Add to export list in `_on_export_clicked()`

### Required Columns Check

- `mfe_pct` and `mae_pct` columns required
- Tab disabled if columns missing (existing pattern)

### Data Flow

1. `_on_baseline_calculated` or `_on_filtered_data_updated` triggers refresh
2. `_update_all_tables()` calls new calculation functions
3. `_populate_table()` renders with gradient styling

## Testing

### Unit Tests (`tests/unit/test_statistics.py`)

- Test `calculate_profit_chance_table()` with sample data
- Test `calculate_loss_chance_table()` with sample data
- Test edge cases: empty buckets, no winners, no losers, single trade

### Test Scenarios

- Trade with 30% MFE appears in 5%, 10%, 15%, 20%, 25%, 30% buckets
- "Chance of Next %" correctly calculates conditional probability
- "Chance of Max Loss %" uses stop_loss from AdjustmentParams
- Profit Ratio handles division by zero (no losers → "—")
- EG% formula produces expected values

### Integration Test

- Verify tables populate when data loaded
- Verify tables update on filtered data change
- Verify gradient styling applies correctly

## Dependencies

No new dependencies required - uses existing pandas, PyQt6, and Statistics tab infrastructure.
