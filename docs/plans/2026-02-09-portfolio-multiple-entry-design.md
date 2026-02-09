# Portfolio Multiple Entry Feature - Design Document

## Overview

Add the ability to control whether duplicate ticker-date pairs across multiple strategies should take multiple trades or defer to higher-priority strategies.

## Requirements

1. **Multiple Entry checkbox** per strategy (default: checked)
2. When unchecked, skip trades if same ticker-date exists in a higher-priority strategy
3. **Drag-and-drop reordering** to set strategy priority (top = highest priority)
4. Settings persist with portfolio config

## Data Model

### StrategyConfig (`src/core/portfolio_models.py`)

Add new field:

```python
@dataclass
class StrategyConfig:
    # ... existing fields ...
    allow_multiple_entry: bool = True  # Default: checked
```

Priority is implicit - the order in `_strategies` list determines priority. No separate field needed.

## UI Changes

### StrategyTableWidget (`src/ui/components/strategy_table.py`)

**New column "Multi":**
- Position: After CND (index 4, shifting subsequent columns right)
- Width: 60px
- Centered checkbox, same style as BL/CND

**Column order after change:**
Name, File, BL, CND, Multi, Stop%, Efficiency, Size Type, Size Value, Max Compound, Menu

**Drag-and-drop reordering:**
- Enable `setDragDropMode(QAbstractItemView.InternalMove)`
- Enable `setDragEnabled(True)` and `setAcceptDrops(True)`
- Override `dropEvent` to reorder internal `_strategies` list
- Emit `strategy_changed` signal after reorder

## Calculation Logic

### PortfolioCalculator (`src/core/portfolio_calculator.py`)

Add filtering step in `calculate_portfolio()` after merging and sorting trades:

```python
def _filter_duplicate_entries(
    self,
    merged: pd.DataFrame,
    strategies: list[tuple[pd.DataFrame, StrategyConfig]]
) -> pd.DataFrame:
    """Remove duplicate ticker-date pairs based on priority and multi-entry settings.
    
    Args:
        merged: DataFrame with all trades, sorted by date
        strategies: List in priority order (first = highest priority)
    
    Returns:
        Filtered DataFrame with duplicates removed per multi-entry settings
    """
    # Build priority map: strategy_name -> priority (0 = highest)
    priority_map = {config.name: i for i, (_, config) in enumerate(strategies)}
    
    seen_ticker_dates = set()  # (ticker, date) pairs already claimed
    keep_mask = []
    
    for _, row in merged.iterrows():
        ticker = row["_ticker"]
        config = row["_config"]
        
        # Skip deduplication if no ticker mapped
        if ticker is None:
            keep_mask.append(True)
            continue
        
        ticker_date = (ticker, row["_date_only"])
        
        if ticker_date in seen_ticker_dates and not config.allow_multiple_entry:
            keep_mask.append(False)  # Skip: duplicate and multi-entry disabled
        else:
            keep_mask.append(True)
            seen_ticker_dates.add(ticker_date)
    
    return merged[keep_mask].reset_index(drop=True)
```

**Key logic:**
- Trades are processed in chronological order (already sorted by date)
- Within same date, strategy priority determines which "claims" first
- First strategy to claim a ticker-date adds it to `seen_ticker_dates`
- Later strategies with `allow_multiple_entry=False` skip if already seen
- Strategies with `allow_multiple_entry=True` always take the trade
- No ticker mapped = always take the trade (skip deduplication)

## Config Persistence

### PortfolioConfigManager (`src/core/portfolio_config_manager.py`)

**Backwards compatibility:**
```python
# When deserializing old configs without the field:
allow_multiple_entry = config_dict.get("allow_multiple_entry", True)
```

**Order preservation:**
- Strategy list order in saved config = priority order
- Drag-and-drop updates list order
- Save/load preserves order naturally

## Edge Cases

1. **No ticker column mapped:** Skip deduplication for that strategy - always take trades
2. **Same strategy, same ticker-date:** Within-strategy duplicates always kept (checkbox only affects cross-strategy)
3. **Empty strategies list:** Returns empty DataFrame (existing behavior)

## Testing

- Unit test: `_filter_duplicate_entries` with various checkbox combinations
- Unit test: drag-drop reordering updates `_strategies` order correctly
- Unit test: backwards compatibility loading old configs
- Integration test: portfolio calculation respects multi-entry settings
