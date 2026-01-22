# Portfolio Breakdown Tab Design

## Overview

Create a new tab called Portfolio Breakdown that displays yearly and monthly breakdown charts for the portfolio data from Portfolio Overview Tab. It shows metrics for both baseline and combined (candidate) portfolios side-by-side, using the position sizing already calculated by Portfolio Overview.

## Requirements

### Data Source
- Uses equity curve data from Portfolio Overview Tab
- Shows both "baseline" and "combined" portfolios
- Data already incorporates user's position sizing choices

### Views
- **Yearly view**: Each bar represents one year of data
- **Monthly view**: Each bar represents one month, with year selector to filter

### Metrics (8 charts per portfolio × 2 portfolios = 16 charts)
1. Total Gain %
2. Total Gain $
3. Account Growth %
4. Max Drawdown %
5. Max Drawdown $
6. Win Rate %
7. Number of Trades
8. Drawdown Duration (days)

## UI Design

### Toolbar Layout

Horizontal toolbar with three control groups separated by dividers:

```
[Yearly | Monthly]  |  [● Baseline] [● Combined]  |  [2021] [2022] [2023] [2024]
```

1. **Period Tabs** - Pill-style segmented control, active tab has cyan underline
2. **Visibility Toggles** - Toggle buttons with glowing indicators
   - Baseline: stellar-blue (#4A9EFF)
   - Combined: plasma-cyan (#00FFD4)
3. **Year Selector** - Only visible in Monthly view, reuses `YearSelectorTabs`

### Chart Grid Layout

4 columns × 4 rows = 16 charts, grouped by metric pairs:

| Row | Columns 1-2 | Columns 3-4 |
|-----|-------------|-------------|
| 1 | Total Gain % (Base, Comb) | Total Gain $ (Base, Comb) |
| 2 | Account Growth % (Base, Comb) | Max Drawdown % (Base, Comb) |
| 3 | Max Drawdown $ (Base, Comb) | Win Rate % (Base, Comb) |
| 4 | Number of Trades (Base, Comb) | DD Duration (Base, Comb) |

### Chart Card Design

- Dark elevated background (#1E1E2C) with subtle border
- Colored top border: Blue for Baseline, Cyan for Combined
- Header: Metric title (left) + Badge "BASE" or "COMB" (right)
- Badge has semi-transparent background matching the color
- Positive bars: Blue gradient (baseline) or Cyan gradient (combined)
- Negative bars (drawdowns): Coral red (#FF4757) for both

## Architecture

### New Files

```
src/
├── core/
│   └── portfolio_breakdown.py      # PortfolioBreakdownCalculator
├── tabs/
│   └── portfolio_breakdown.py      # PortfolioBreakdownTab widget
```

### Component Structure

```
PortfolioBreakdownTab
├── _toolbar
│   ├── _period_tabs (QButtonGroup for Yearly/Monthly)
│   ├── _baseline_toggle (QPushButton, checkable)
│   ├── _combined_toggle (QPushButton, checkable)
│   └── _year_selector (YearSelectorTabs)
├── _stacked_widget (QStackedWidget)
│   ├── _yearly_view (QWidget)
│   │   └── _yearly_charts: dict[str, VerticalBarChart]
│   └── _monthly_view (QWidget)
│       └── _monthly_charts: dict[str, VerticalBarChart]
└── _calculator: PortfolioBreakdownCalculator
```

### Data Flow

1. Portfolio Overview calculates equity curves for baseline and combined portfolios
2. Emits `portfolio_data_changed` signal with dict: `{"baseline": df, "combined": df}`
3. Portfolio Breakdown receives signal, stores data
4. Calculator computes 8 metrics per period (year/month) for each portfolio
5. Charts update with calculated data

### Signal Wiring

**Portfolio Overview Tab** (modify existing):
```python
class PortfolioOverviewTab(QWidget):
    portfolio_data_changed = pyqtSignal(dict)  # {"baseline": df, "combined": df}
```

**Main Window** (add connection):
```python
self._portfolio_overview.portfolio_data_changed.connect(
    self._portfolio_breakdown.on_portfolio_data_changed
)
```

## Calculations

### Input Data Format

Equity curve DataFrame columns:
- `date`: Trade date
- `trade_num`: Sequential trade number
- `strategy`: Strategy name (for combined)
- `pnl`: Profit/loss in dollars
- `equity`: Account value after trade
- `peak`: Running peak equity
- `drawdown`: Current drawdown (negative or zero)

### Metric Calculations

For each period (year or month):

| Metric | Formula |
|--------|---------|
| Total Gain % | `sum(pnl) / period_start_equity * 100` |
| Total Gain $ | `sum(pnl)` |
| Account Growth % | `(period_end_equity - period_start_equity) / period_start_equity * 100` |
| Max Drawdown % | `min(drawdown / peak) * 100` at each point |
| Max Drawdown $ | `min(drawdown)` |
| Win Rate % | `count(pnl > 0) / count(all) * 100` |
| Number of Trades | `count(all)` |
| DD Duration | Longest consecutive streak where `equity < peak` (trading days) |

### PortfolioBreakdownCalculator Interface

```python
class PortfolioBreakdownCalculator:
    def calculate_yearly(
        self,
        equity_df: pd.DataFrame
    ) -> dict[int, dict[str, float]]:
        """Calculate metrics for each year.

        Returns:
            {2024: {"total_gain_pct": 15.2, "total_gain_dollars": 1520, ...}, ...}
        """

    def calculate_monthly(
        self,
        equity_df: pd.DataFrame,
        year: int
    ) -> dict[int, dict[str, float]]:
        """Calculate metrics for each month in the given year.

        Returns:
            {1: {"total_gain_pct": 3.1, ...}, 2: {...}, ...}
        """

    def get_available_years(self, equity_df: pd.DataFrame) -> list[int]:
        """Return sorted list of years in the data."""
```

## Reused Components

- `VerticalBarChart` - Existing bar chart widget from `src/ui/components/vertical_bar_chart.py`
- `YearSelectorTabs` - Existing year selector from `src/ui/components/year_selector_tabs.py`
- `Colors`, `Fonts`, `Spacing` - Constants from `src/ui/constants.py`

## Edge Cases

- **No data**: Show empty charts with "No data" message
- **Single portfolio**: If only baseline or combined exists, show only those charts
- **Partial year**: Monthly view handles incomplete years gracefully
- **Zero trades in period**: Show zero bars, avoid division by zero

## Testing

- Unit tests for `PortfolioBreakdownCalculator` metric calculations
- Integration test for signal connection between tabs
- Visual verification of chart rendering
