# Statistics Tab Design

## Overview

A new Statistics tab that displays 5 analytical tables for trade analysis. Tables use the baseline dataframe by default, switching to filtered dataframe when filters are applied.

## Architecture

### New Files

```
src/
  tabs/
    statistics_tab.py      # Main tab with 5 sub-tabs
  core/
    statistics.py          # Pure calculation functions
```

### Modified Files

- `src/core/models.py` - Add `mfe_pct: str` as required field in `ColumnMapping`

### Data Flow

1. User loads data → baseline_df set
2. User applies filters → filtered_df set
3. Statistics tab detects change → calls calculation functions with appropriate df
4. Results displayed in styled QTableWidget for each sub-tab

## Data Format Notes

| Column | Format | Example |
|--------|--------|---------|
| `mae_pct` | Percentage points | 10.5 = 10.5% |
| `mfe_pct` | Percentage points | 10.5 = 10.5% |
| `adjusted_gain_pct` | Decimal | 0.105 = 10.5% |
| `gain_pct` | Decimal | 0.105 = 10.5% |

All calculations must handle these unit conversions correctly.

## Table Specifications

### Table 1: MAE % Before Win

Analyzes maximum adverse excursion for winning trades grouped by gain magnitude.

**Input:** Winning trades only (`adjusted_gain_pct > 0`)

**Row Buckets (fixed):**

| Row | Filter |
|-----|--------|
| Overall | All winners |
| >0% | 0% < gain ≤ 10% |
| >10% | 10% < gain ≤ 20% |
| >20% | 20% < gain ≤ 30% |
| >30% | 30% < gain ≤ 40% |
| >40% | 40% < gain ≤ 50% |
| >50% | gain > 50% |

**Columns:**

| Column | Calculation |
|--------|-------------|
| % Gain per Trade | Row bucket label |
| # of Plays | Count of trades in bucket |
| % of Total | Bucket count / total winners × 100 |
| Avg % | Mean of `adjusted_gain_pct` in bucket (converted to %) |
| Median % | Median of `adjusted_gain_pct` in bucket (converted to %) |
| >5% MAE Probability | Count where `mae_pct > 5` / total winners × 100 |
| >10% MAE Probability | Count where `mae_pct > 10` / total winners × 100 |
| >15% MAE Probability | Count where `mae_pct > 15` / total winners × 100 |
| >20% MAE Probability | Count where `mae_pct > 20` / total winners × 100 |

### Table 2: MFE Before Loss

Analyzes maximum favorable excursion for losing trades grouped by loss magnitude.

**Input:** Losing trades only (`adjusted_gain_pct < 0`)

**Row Buckets (fixed):** Same structure as Table 1, but filtering by loss magnitude (absolute value)

**Columns:** Same structure as Table 1, but using `mfe_pct` for probability columns

### Table 3: Stop Loss Table

Simulates applying different stop loss levels to all trades.

**Stop Loss Levels (fixed):** 10%, 20%, 30%, 40%, 50%, 60%, 70%, 80%, 90%, 100%

**Logic Per Row:**

For each stop level:
1. Classify trades: If `mae_pct >= stop_level`, trade is stopped out (loss = -stop_level)
2. Otherwise, use original `gain_pct`
3. Apply efficiency % to stopped trades
4. Derive all metrics from adjusted returns

**Columns:**

| Column | Calculation |
|--------|-------------|
| Stop % | The stop level |
| Win % | Winners / total × 100 |
| Profit Ratio | avg_win / abs(avg_loss) |
| Edge % | (profit_ratio + 1) × win_rate - 1 |
| EG % | Kelly growth formula |
| Max Loss % | Count stopped out / total × 100 |
| Full Kelly (Stop Adj) | edge / profit_ratio / stop_level |
| Half Kelly (Stop Adj) | Full Kelly / 2 |
| Quarter Kelly (Stop Adj) | Full Kelly / 4 |

### Table 4: Offset Table

Simulates entering trades at different price offsets from the original entry. This is for **short trades**.

**Offset Levels (fixed):** -20%, -10%, 0%, +10%, +20%, +30%, +40%

**Logic Per Row:**

For each offset:

1. **Filter qualifying trades:**
   - Negative offset (e.g., -10%): Include if `mfe_pct >= abs(offset)` (price dropped enough to reach lower entry)
   - Positive offset (e.g., +20%): Include if `mae_pct >= offset` (price rose enough to reach higher entry)
   - 0% offset: All trades qualify

2. **Recalculate MAE/MFE from new entry point:**
   ```python
   original_entry = 1.0  # normalized
   new_entry = 1.0 * (1 + offset)

   # Derive price levels from original percentages
   highest_price = 1.0 * (1 + mae_pct / 100)
   lowest_price = 1.0 * (1 - mfe_pct / 100)

   # Recalculate from new entry
   new_mae_pct = (highest_price - new_entry) / new_entry * 100
   new_mfe_pct = (new_entry - lowest_price) / new_entry * 100
   ```

3. **Recalculate returns:**
   - New gain based on offset entry price to same exit
   - Apply stop-loss using `new_mae_pct`
   - Apply efficiency %

4. **Max Loss %** = Trades where `new_mae_pct >= stop_level` / total qualifying trades × 100

**Columns:**

| Column | Calculation |
|--------|-------------|
| Offset % | The offset level |
| # of Trades | Qualifying trades count |
| Win % | Winners / qualifying × 100 |
| Avg. Gain % | Mean adjusted return (as %) |
| Median Gain % | Median adjusted return (as %) |
| EV % | Expected value |
| Profit Ratio | avg_win / abs(avg_loss) |
| Edge % | (PR + 1) × WR - 1 |
| EG % | Kelly growth |
| Max Loss % | Stop-hit rate after offset adjustment |
| Total Gain % | Sum of all adjusted returns (as %) |

### Table 5: Scaling Table

Analyzes taking partial profits at various MFE targets vs. holding to close.

**User Input:** Scale Out % - Spinbox above the table (default: 50%, range: 10%-90%, step: 10%)

**Partial Target Levels (fixed):** 5%, 10%, 15%, 20%, 25%, 30%, 35%, 40%

**Logic Per Row:**

For each target with user-specified scale_out %:

1. For each trade:
   - If `mfe_pct >= target`: `blended = (scale_out × target/100) + ((1 - scale_out) × full_hold_return)`
   - If `mfe_pct < target`: `blended = full_hold_return`

2. Calculate metrics for both blended and full hold returns

**Columns:**

| Column | Description |
|--------|-------------|
| Partial Target % | The MFE target level |
| % of Trades | Trades where `mfe_pct >= target` / total × 100 |
| Avg Blended Return % | Mean of blended returns |
| Avg Full Hold Return % | Mean of full hold returns |
| Total Blended Return % | Sum of blended returns |
| Total Full Hold Return % | Sum of full hold returns |
| Blended Win % | Win rate using blended |
| Full Hold Win % | Win rate using full hold |
| Blended Profit Ratio | PR using blended |
| Full Hold Profit Ratio | PR using full hold |
| Blended Edge % | Edge using blended |
| Full Hold Edge % | Edge using full hold |
| Blended EG % | EG using blended |
| Full Hold EG % | EG using full hold |

## UI Design

### Tab Structure

```
Statistics Tab
├── QTabWidget (sub-tabs)
│   ├── "MAE Before Win" → QTableWidget
│   ├── "MFE Before Loss" → QTableWidget
│   ├── "Stop Loss" → QTableWidget
│   ├── "Offset" → QTableWidget
│   └── "Scaling" → QWidget
│       ├── Scale Out control (QSpinBox + label)
│       └── QTableWidget
```

### Styling (Observatory Theme)

Uses existing theme from `src/ui/constants.py` and `src/ui/theme.py`.

**Conditional Cell Colors:**

```python
# Positive metrics (EG%, Edge%, positive returns)
CELL_POSITIVE = "rgba(0, 255, 212, 0.12)"  # Cyan tint
CELL_POSITIVE_TEXT = "#00FFD4"  # Plasma-cyan

# Negative metrics (losses, negative edge)
CELL_NEGATIVE = "rgba(255, 71, 87, 0.12)"  # Coral tint
CELL_NEGATIVE_TEXT = "#FF4757"  # Solar-coral

# Best row highlight (highest EG% per table)
ROW_OPTIMAL = "rgba(0, 255, 212, 0.08)"  # Subtle cyan glow
ROW_OPTIMAL_BORDER = "#00FFD4"  # Left border accent
```

**Column Formatting:**
- First column (bucket/level): Bold, left-aligned
- Metric columns: Right-aligned, Azeret Mono font
- Percentages: 2 decimal places with % symbol
- Ratios: 3 decimal places
- Counts: Integer with thousands separator

**Scale Out Control:**
- Positioned above the Scaling table
- Label: "Scale Out:" in Geist font
- Spinbox: Value in Azeret Mono, 10-90% range, 10% step

## Edge Cases & Error Handling

### Empty States

- **No data loaded:** Display "Load trade data to view statistics" centered, TEXT_SECONDARY color
- **No qualifying trades for row:** Show "—" for all cells, row dimmed
- **Filter results in zero trades:** Show empty table with "No trades match current filters"

### Data Validation

- **Missing `mfe_pct`:** Warning banner, disable MFE-dependent tables (MFE Before Loss, Scaling)
- **Missing `mae_pct`:** Disable MAE-dependent tables (MAE Before Win, Stop Loss, Offset)
- **NaN/inf values:** Exclude from calculations silently
- **Negative percentages:** Log warning, continue

### Performance

- **Large datasets (>100k trades):** Run calculations in QThread
- **Loading indicator:** Subtle spinner during recalculation
- **Debounce:** 300ms delay after filter changes before recalculating

### Calculation Precision

- Percentages: 2 decimal places
- Ratios: 3 decimal places
- Counts: Integer with thousands separator (e.g., 1,234)

## Implementation Notes

### ColumnMapping Update

Add `mfe_pct` as required field:

```python
@dataclass
class ColumnMapping:
    ticker: str
    date: str
    time: str
    gain_pct: str
    mae_pct: str
    mfe_pct: str  # NEW - required
    win_loss: str | None = None
    win_loss_derived: bool = False
    breakeven_is_win: bool = False
```

Update `validate()` method to check for `mfe_pct` column.

### Calculation Functions

All in `src/core/statistics.py`:

```python
def calculate_mae_before_win(df: pd.DataFrame, mapping: ColumnMapping) -> pd.DataFrame:
    """Calculate MAE probabilities for winning trades by gain bucket."""
    ...

def calculate_mfe_before_loss(df: pd.DataFrame, mapping: ColumnMapping) -> pd.DataFrame:
    """Calculate MFE probabilities for losing trades by loss bucket."""
    ...

def calculate_stop_loss_table(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    efficiency: float
) -> pd.DataFrame:
    """Simulate stop loss levels and calculate metrics."""
    ...

def calculate_offset_table(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    stop_loss: float,
    efficiency: float
) -> pd.DataFrame:
    """Simulate entry offsets with recalculated MAE/MFE and returns."""
    ...

def calculate_scaling_table(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    scale_out_pct: float
) -> pd.DataFrame:
    """Compare blended partial-profit returns vs full hold."""
    ...
```

### Signal Connections

Statistics tab subscribes to:
- `app_state.baseline_df_changed` - Recalculate with baseline
- `app_state.filtered_df_changed` - Recalculate with filtered (if filters active)
- `app_state.stop_loss_changed` - Recalculate Offset table
- `app_state.efficiency_changed` - Recalculate Stop Loss and Offset tables
