# Partial Cover % Table Design

## Overview

Add a "Partial Cover %" table to the Statistics Tab's Scaling section. This table simulates covering a portion of a short position when price moves against you (MAE reaches threshold), helping analyze defensive scaling strategies.

## Requirements

- Works like Partial Target %, but uses `mae_pct` instead of `mfe_pct`
- Separate "Cover %" spinbox (0-100%, default 50%)
- Vertically stacked below the existing Partial Target % table
- Same metrics columns as Partial Target % for consistency

## Calculation Logic

For each threshold level (1%, 2%, 3%, etc. from `SCALING_TARGET_LEVELS`):

1. **% of Trades** - Percentage where `mae_pct >= threshold`
2. **Blended Return** calculation:
   - Trades reaching threshold: `cover_pct × (-threshold/100) + (1-cover_pct) × full_hold`
   - Trades not reaching threshold: `full_hold` unchanged
3. **Metrics** (same as Partial Target %):
   - Avg Blended Return %, Avg Full Hold Return %
   - Total Blended Return %, Total Full Hold Return %
   - Blended Win %, Full Hold Win %
   - Blended Profit Ratio, Full Hold Profit Ratio
   - Blended Edge %, Full Hold Edge %
   - Blended EG %, Full Hold EG %

First column named "Partial Cover %" (instead of "Partial Target %").

## Files to Modify

### `src/core/statistics.py`

Add new function:

```python
def calculate_partial_cover_analysis(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    cover_pct: float = 0.5,
) -> pd.DataFrame:
```

Add helper function:

```python
def _calculate_cover_row(
    df: pd.DataFrame,
    mae_col: str,
    threshold: float,
    cover_pct: float,
) -> dict:
```

### `src/tabs/statistics_tab.py`

Modify `_create_scaling_widget()`:

1. Change existing Scale Out spinbox range from 10-90% to 0-100%
2. Add spacer after Partial Target % table
3. Add "Cover:" label + `self._cover_spin` spinbox (0-100%, default 50%)
4. Add `self._cover_table` for Partial Cover % results
5. Connect `self._cover_spin.valueChanged` to refresh cover table

Update `_update_tables()` and related methods:
- Calculate and populate Partial Cover % table
- Handle missing `mae_pct` column (disable cover section)

## UI Layout

```
┌─────────────────────────────────────┐
│ Scale Out: [___50___%]              │
├─────────────────────────────────────┤
│ Partial Target % Table              │
│ ...                                 │
├─────────────────────────────────────┤
│ (spacer)                            │
├─────────────────────────────────────┤
│ Cover: [___50___%]                  │
├─────────────────────────────────────┤
│ Partial Cover % Table               │
│ ...                                 │
└─────────────────────────────────────┘
```

## Testing

### Unit tests (`tests/unit/test_statistics.py`)

- `test_calculate_partial_cover_analysis_basic` - Verify calculation with known data
- `test_calculate_partial_cover_analysis_empty_df` - Handle empty DataFrame
- `test_calculate_partial_cover_analysis_no_mae_reached` - All trades below threshold

### Integration tests (`tests/integration/test_statistics_tab.py`)

- Verify Cover spinbox exists and has correct range (0-100%)
- Verify Scale Out spinbox range updated to 0-100%
- Verify Partial Cover % table populates when data has `mae_pct`
- Verify spinbox value change triggers table refresh

## Edge Cases

- Empty DataFrame → Return empty table with column headers
- No trades reach threshold → Show 0% of trades, metrics as None/0
- Missing `mae_pct` column → Cover section disabled/hidden

## Implementation Steps

1. Add `_calculate_cover_row()` helper in `statistics.py`
2. Add `calculate_partial_cover_analysis()` function in `statistics.py`
3. Update `_create_scaling_widget()` to add Cover spinbox and table
4. Update Scale Out spinbox range to 0-100%
5. Wire up Cover spinbox to refresh cover table
6. Update `_update_tables()` to populate cover table
7. Handle tab enablement for missing `mae_pct`
8. Add unit tests
9. Add integration tests
