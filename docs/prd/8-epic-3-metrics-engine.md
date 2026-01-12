# 8. Epic 3: Metrics Engine

## Epic Goal

Implement the complete 25-metric trading statistics engine with user input controls. Upon completion, the PnL & Trading Stats tab displays all metrics defined in the Project Brief Appendix D, accepts user inputs for position sizing parameters, and prepares data structures for comparison and charts.

## Stories

### Story 3.1: PnL Stats Tab Layout & User Inputs Panel

**As a** user,
**I want** to configure analysis parameters,
**so that** I can customize metrics to my trading approach.

**Acceptance Criteria:**

1. Tab layout: top (user inputs), middle (metrics grid), bottom (charts placeholder)
2. User inputs: Flat Stake ($), Starting Capital ($), Fractional Kelly (%), Stop Loss (%), Efficiency (%)
3. Stop Loss and Efficiency inputs sync with Data Input tab values (bidirectional via AppState)
4. Input validation with feedback
5. Inputs persist across tab switches
6. "Apply" button or auto-apply with debounce

**Note:** Stop Loss and Efficiency are already established in Epic 1 Story 1.6. This story exposes them in the PnL Stats tab for convenience, with bidirectional sync via AppState.adjustment_params.

---

### Story 3.2: Core Statistics & Distribution Data (Metrics 1-12, 24-25 prep)

**As a** user,
**I want** to see core trading statistics,
**so that** I understand my win rate, expectancy, and optimal position sizing.

**Acceptance Criteria:**

1. Calculate metrics 1-12: Trades, Win Rate, Avg Winner/Loser, R:R, EV, Edge, Kelly, Fractional Kelly, EG, Median Winner/Loser
2. Prepare distribution data (winner/loser arrays with min, max, mean, median, std)
3. Display in styled metric cards with tooltips
4. Color coding for positive/negative values
5. Recalculate on user input changes
6. Calculation < 100ms for 100k rows

---

### Story 3.3: Streak & Loss Metrics (13-15)

**As a** user,
**I want** to see streak and risk metrics,
**so that** I understand my drawdown risk.

**Acceptance Criteria:**

1. Calculate: Max Consecutive Wins, Max Consecutive Losses, Max Loss %
2. Streak detection on chronologically sorted data
3. Max Loss % uses stop_loss user input
4. Recalculate on stop_loss change

---

### Story 3.4: Flat Stake Metrics (16-19)

**As a** user,
**I want** to see performance with fixed position size,
**so that** I can evaluate my strategy without compounding.

**Acceptance Criteria:**

1. Calculate: Flat Stake PnL, Max DD ($), Max DD (%), DD Duration
2. Create equity calculation module (`src/core/equity.py`)
3. Store equity curve in app state for charts
4. Display "Not recovered" if drawdown ongoing
5. Recalculate on flat_stake change

---

### Story 3.5: Compounded Kelly Metrics (20-23)

**As a** user,
**I want** to see performance with Kelly position sizing,
**so that** I can evaluate optimal growth strategy.

**Acceptance Criteria:**

1. Calculate: Compounded Kelly PnL, Max DD ($), Max DD (%), DD Duration
2. Reuse equity module from Story 3.4
3. Handle negative Kelly (warning), blown account
4. Store equity curve for charts
5. Recalculate on start_capital or fractional_kelly change

---

### Story 3.6: Distribution Statistics Display (24-25)

**As a** user,
**I want** to see summary statistics for winners and losers,
**so that** I understand the spread of outcomes.

**Acceptance Criteria:**

1. Display winner/loser distribution statistics (count, range, mean, median, std)
2. Winner card with plasma-cyan border, loser card with solar-coral border
3. "View Histogram" link (histograms in Epic 4)
4. Calculate suggested bin size

---

## Epic 3 Definition of Done

- [ ] PnL & Trading Stats tab displays professional layout
- [ ] User can configure all 4 input parameters
- [ ] All 25 metrics calculated correctly per Appendix D
- [ ] Metrics update when user inputs change
- [ ] Reusable equity calculation module created
- [ ] Equity curves stored for chart rendering
- [ ] Distribution data prepared with statistics
- [ ] All calculations < 200ms for 100k rows

---
