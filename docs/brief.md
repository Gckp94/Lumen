# Project Brief: Lumen

**Version:** 1.0
**Date:** 2026-01-09
**Status:** Draft

---

## Executive Summary

**Product Concept:** Lumen is a high-performance desktop application for trading data analysis, replacing Excel-based workflows that struggle with 83k+ row datasets.

**Primary Problem:** Excel-based trading analysis is prohibitively slow with large datasets, lacks specialized filtering logic (first trigger analysis), and cannot efficiently compare filtered results against baselines.

**Target Market:** Individual traders and trading analysts who perform quantitative analysis on historical trade data and need rapid iteration on filtering criteria.

**Key Value Proposition:** 10-100x performance improvement over Excel through Pandas + Parquet architecture, with specialized "First Trigger" filtering logic and always-on baseline comparison that no existing tool provides. All 25 trading metrics calculated instantly.

---

## Problem Statement

### Current State & Pain Points

- Trading analysts currently use Excel for analyzing historical trade data
- Datasets of 83,000+ rows cause significant performance degradation
- Simple filtering operations take seconds to minutes instead of milliseconds
- No native support for "first trigger" logic - analysts must manually implement complex formulas
- Comparing filtered subsets against baseline requires duplicating worksheets and manual synchronization

### Impact of the Problem

- Analysis that should take minutes stretches into hours
- Iteration speed is crippled - testing multiple filter combinations becomes tedious
- Analysts avoid exploring edge cases due to time cost
- Decision quality suffers from limited exploration of the data
- Competitive disadvantage vs. traders with proper tooling

### Why Existing Solutions Fall Short

- **Excel:** Too slow, no first-trigger logic, poor charting for large datasets
- **Python scripts:** Require programming knowledge, no interactive UI, hard to iterate
- **Trading platforms:** Focus on execution, not historical analysis; expensive; inflexible
- **BI tools (Tableau, PowerBI):** Not optimized for trading metrics, lack domain-specific calculations like Kelly criterion, risk of ruin

### Urgency

- Every trading day generates more data, compounding the problem
- Manual analysis delays mean missed pattern identification
- The 25 specialized trading metrics are not available in any off-the-shelf tool

---

## Proposed Solution

### Core Concept & Approach

Lumen is a native desktop application built on a high-performance data stack (Pandas + Parquet) with GPU-accelerated visualization (PyQtGraph). It provides a 4-tab workflow designed specifically for trading data analysis:

1. **Data Input** - Load Excel/CSV files with automatic Parquet conversion, establish baseline (all first triggers)
2. **Feature Explorer** - Interactive charting with bounds-based filtering and binning; first-trigger filter toggle available
3. **PnL & Trading Stats** - All 25 trading metrics with baseline vs. filtered comparison
4. **Monte Carlo** - Simulation engine for robustness testing (reshuffling, resampling, risk metrics)

### Key Differentiators

- **First Trigger Logic:** Native support for identifying the first signal per ticker-date meeting user criteria - impossible to replicate efficiently in Excel
- **Flexible First-Trigger Toggle:** In Feature Explorer, users can toggle first-trigger filtering on/off to explore raw data vs. filtered data
- **Always-On Baseline Comparison:** Baseline is ALWAYS the first-trigger filtered dataset; all comparisons measure against this reference point
- **Sub-second Performance:** 83k+ rows filter and chart in milliseconds, not minutes
- **Domain-Specific Metrics:** All 25 trading metrics built-in (Kelly criterion, risk of ruin, win rate, expectancy, etc.)
- **Flexible Schema:** Add columns without breaking the application - no rigid data validation

### Why This Solution Will Succeed

- Addresses exact pain points with purpose-built architecture
- Uses proven, battle-tested libraries (Pandas is reliable and well-documented)
- Desktop app = no latency, works offline, no subscription fees
- User's domain expertise shapes every feature - not a generic tool

### High-Level Vision

Transform trading analysis from a slow, tedious Excel slog into a fast, exploratory experience where testing a hypothesis takes seconds instead of minutes, enabling deeper insights and better trading decisions.

---

## Target Users

### Primary User Segment: Quantitative Day Traders

**Demographic/Firmographic Profile:**
- Individual traders or small trading teams (1-5 people)
- Self-directed, not working for large institutions
- Technically comfortable but not necessarily programmers
- Use systematic/rules-based trading strategies
- Generate significant historical trade data (thousands to hundreds of thousands of rows)

**Current Behaviors & Workflows:**
- Export trade data from broker platforms to Excel/CSV
- Spend hours filtering and analyzing data manually in Excel
- Create complex formulas to identify patterns and calculate metrics
- Manually build comparison views between different filter criteria
- Struggle to iterate quickly due to Excel performance limitations

**Specific Needs & Pain Points:**
- Need to identify "first trigger" signals per ticker-date quickly
- Require all 25 trading metrics calculated consistently
- Must compare filtered results against baseline to measure edge
- Want to test multiple filter hypotheses rapidly
- Need Monte Carlo simulation to validate strategy robustness

**Goals They're Trying to Achieve:**
- Discover profitable filtering criteria that improve trading edge
- Validate that observed patterns are statistically significant
- Optimize position sizing using Kelly criterion
- Understand risk of ruin before deploying capital
- Reduce time spent on analysis to focus on trading

### Secondary User Segment: Trading Strategy Researchers

**Demographic/Firmographic Profile:**
- Hobbyist quants developing trading systems
- Students/academics studying market microstructure
- Traders transitioning from discretionary to systematic approaches

**Current Behaviors & Workflows:**
- Similar to primary segment but may have smaller datasets
- More exploratory, less production-focused
- May use Python/R but want faster iteration than coding allows

**Specific Needs & Pain Points:**
- Need intuitive UI without programming requirement
- Want to explore "what if" scenarios quickly
- Require export capabilities to continue analysis in other tools

**Goals:**
- Learn what factors influence trading outcomes
- Build intuition about their trading data
- Prototype filtering strategies before coding them

---

## Goals & Success Metrics

### Business Objectives

- **Replace Excel workflow entirely** - Lumen becomes the primary tool for all trading data analysis, eliminating Excel dependency
- **Enable rapid hypothesis testing** - User can test a new filter hypothesis in under 10 seconds end-to-end
- **Provide complete metrics visibility** - All 25 trading metrics available instantly for any filtered dataset
- **Support data-driven trading decisions** - Monte Carlo simulations validate strategy robustness before capital deployment

### User Success Metrics

- **Time to first insight:** Load data and see baseline stats in < 5 seconds
- **Filter iteration speed:** Apply new filter criteria and see updated metrics in < 1 second
- **Analysis sessions completed:** User completes full analysis workflow without returning to Excel
- **Hypothesis throughput:** Number of filter combinations tested per session increases 10x vs. Excel
- **Confidence in decisions:** Monte Carlo results inform position sizing and risk management

### Key Performance Indicators (KPIs)

| KPI | Definition | Target |
|-----|------------|--------|
| **Data load time** | Time from file selection to baseline stats displayed | < 3 seconds for 100k rows |
| **Filter response time** | Time from filter change to metrics + chart update | < 500ms |
| **Chart render time** | Time to render 83k+ data points | < 200ms |
| **Memory footprint** | RAM usage with large dataset loaded | < 500MB |
| **Crash rate** | Application crashes per 100 sessions | 0 |
| **Feature completeness** | MVP features implemented and working | 100% |

---

## MVP Scope

### Core Features (Must Have)

#### Tab 1: Data Input
- **File loader:** Excel/CSV import with automatic Parquet conversion for performance
- **Sheet selector:** Dropdown to choose which sheet to load from Excel files
- **Column validation:** Flexible validation (no strict schema), warn on missing expected columns
- **Load status indicator:** Clear success/failure feedback with plain English error messages
- **First trigger logic:** Apply user-defined criteria to identify first trigger per ticker-date
- **Baseline stats display:** Show metrics for all first triggers immediately on load

#### Tab 2: Feature Explorer
- **Feature (column) selection:** Choose which column to analyze
- **Bounds filtering:** BETWEEN and NOT BETWEEN range filters
- **Multi-feature AND logic:** Combine multiple filter criteria
- **First-trigger toggle:** Switch between first-trigger filtered and raw data views
- **Date range selection:** Filter by date range
- **Chart type selection:** Basic chart types for visualization
- **Min/Max chart bounds:** User-defined axis limits
- **Interactive charts:** Pan, zoom, crosshair with PyQtGraph

#### Tab 3: PnL & Trading Stats
- **All 25 trading metrics:** Complete metrics calculation engine
- **User inputs:** Stop loss %, efficiency value, flat stake $, fractional Kelly %
- **Flat Stake PnL chart:** Cumulative PnL over time (by date)
- **Compounded Kelly PnL chart:** Kelly-based position sizing results
- **Baseline vs. Filtered comparison:** Side-by-side metrics comparison (always against first-trigger baseline)

#### Tab 4: Monte Carlo (Placeholder only in MVP)
- **Tab visible but disabled:** Shows "Coming in Phase 3" message
- **No functionality in MVP**

#### Global Features
- **Dark mode UI:** Professional dark theme throughout
- **Export filtered dataset:** CSV and Parquet export of current filter results
- **Export chart images:** PNG export of charts

### Out of Scope for MVP

- Monte Carlo simulation (Phase 3)
- Binning for exploration (Phase 2)
- Winner/Loser histograms (Phase 2)
- Filter A vs. B comparison (Phase 4)
- Time period comparison (Phase 4)
- Save/load filter configurations (Phase 4)
- PDF report generation (Phase 4)
- Session history / audit trail (Phase 4)
- Stop-loss adjusted toggle (Phase 2)
- Multi-file analysis (Moonshot)
- Real-time data integration (Moonshot)

### MVP Success Criteria

The MVP is successful when:

1. **Complete workflow replacement:** User can load data, apply filters, view all 25 metrics, and export results without touching Excel
2. **Performance targets met:** All KPIs achieved (< 3s load, < 500ms filter, < 200ms chart)
3. **First trigger logic works:** Correctly identifies first trigger per ticker-date based on user criteria
4. **Baseline comparison functional:** Every filtered view shows delta from baseline
5. **Stability:** Zero crashes during normal operation
6. **Usability:** Dark mode UI is intuitive, no training required

---

## Post-MVP Vision

### Phase 2 Features: Full Analysis

Building on the MVP foundation to enhance data exploration:

- **Binning for exploration:** User-defined bin sizes for distribution analysis
- **Winner/Loser histograms:** Separate distribution views for winning vs. losing trades
- **All chart types:** Expand beyond basic charts (scatter, histogram, line, etc.)
- **Stop-loss adjusted toggle:** View metrics with/without stop-loss adjustment applied

### Phase 3 Features: Monte Carlo

Simulation engine for strategy robustness validation:

- **Reshuffling simulation:** Randomize trade order to test sequence dependency
- **Resampling (bootstrap):** Sample with replacement to test statistical significance
- **10,000 simulation runs:** High-volume simulation for confidence intervals
- **Average PnL trend:** Expected value trajectory across simulations
- **Worst case scenario:** Identify tail risk from simulations
- **Equity curve bands:** 5th / 50th / 95th percentile visualization
- **Probability of target:** User-defined profit target probability
- **Risk of ruin %:** Calculate probability of account drawdown to specified level
- **User-defined inputs:** Target amount, ruin threshold, simulation count

### Phase 4 Features: Advanced Features

Power user capabilities and workflow enhancements:

- **Filter A vs. B comparison:** Compare two different filter configurations side-by-side
- **Time period comparison:** Compare same filter across different date ranges
- **Bin breakdown comparison:** See metrics breakdown by bin
- **Save/load filter configurations:** Persist and reload filter setups
- **PDF report generation:** Export formatted reports with stats, charts, and filter configs
- **Session history / audit trail:** Track analysis sessions and decisions

### Long-term Vision

**1-2 Year Horizon:**

Lumen becomes the complete trading analysis workbench:

- **Multi-file analysis:** Combine multiple years of data for long-term pattern analysis
- **Strategy backtesting:** Move beyond analysis to actual backtesting with entry/exit rules
- **Custom metrics engine:** User-defined calculated columns and metrics
- **Template library:** Pre-built analysis templates for common trading strategies

### Expansion Opportunities

| Opportunity | Description | Prerequisites |
|-------------|-------------|---------------|
| **Multi-file support** | Load and analyze multiple datasets simultaneously | Stable single-file performance |
| **Plugin architecture** | Allow custom metrics and chart types | Well-defined API boundaries |
| **Cloud sync** | Sync filter configurations across machines | Save/load feature complete |
| **Real-time integration** | Connect to broker APIs for live data | Core analysis engine mature |
| **Commercial release** | Package for other traders | Full feature set, polish, documentation |

---

## Technical Considerations

### Platform Requirements

| Requirement | Specification |
|-------------|---------------|
| **Target Platform** | Windows desktop (primary) |
| **OS Support** | Windows 10/11 |
| **Python Version** | Python 3.10+ |
| **Display** | 1920x1080 minimum resolution recommended |
| **Performance Requirements** | < 3s data load, < 500ms filter response, < 200ms chart render |
| **Memory** | < 500MB RAM with 100k row dataset |

### Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Data Processing** | Pandas | Reliable, forgiving with messy data, sufficient speed for 83k rows |
| **Data Storage** | Parquet | 10-20x faster than CSV, columnar format optimized for analytics |
| **UI Framework** | PyQt6 | Native desktop look, professional widgets, mature ecosystem |
| **Charting** | PyQtGraph | GPU-accelerated, handles 83k+ points smoothly, interactive |
| **File I/O** | PyArrow + openpyxl | Parquet read/write + Excel import support |
| **PDF Generation** | ReportLab or WeasyPrint | PDF export for trading stats and reports (Phase 4) |

### Architecture Considerations

**Repository Structure:**
- Single repository, monolithic application
- Clear separation: `src/` for code, `tests/` for tests, `docs/` for documentation
- Feature-based module organization (data_input, feature_explorer, pnl_stats, monte_carlo)

**Application Architecture:**
- Single-process desktop application
- Tab-based UI with shared data context
- In-memory data storage (Pandas DataFrame)
- Event-driven UI updates

**Integration Requirements:**
- File system only (no external APIs in MVP)
- Import: Excel (.xlsx, .xls), CSV
- Export: Parquet, CSV, PNG, PDF (trading stats & reports - Phase 4)

**Security/Compliance:**
- Local data only - no network transmission
- No authentication required (single-user desktop app)
- User data never leaves the machine

---

## Constraints & Assumptions

### Constraints

**Budget:**
- Personal project - no external budget
- Open-source libraries only (PyQt6 is GPL/commercial dual-licensed - GPL is free for personal use)
- No paid APIs or services

**Resources:**
- Solo developer
- Development alongside other commitments
- No dedicated QA or design resources

**Technical:**
- Windows desktop only (MVP)
- Python ecosystem only
- Must work offline (no cloud dependencies)
- Dataset size: optimized for ~100k rows (Pandas handles comfortably)
- Single-user, single-file at a time

**Dependencies:**
- PyQt6 (UI framework)
- Pandas (data processing)
- PyArrow (Parquet support)
- PyQtGraph (charting)
- openpyxl (Excel reading)
- ReportLab or similar (PDF export - Phase 4)

### Key Assumptions

- **Data format:** Input files are Excel (.xlsx) or CSV with trading data
- **Data structure:** Each row represents a trade/signal with date, ticker, and numerical features
- **Column flexibility:** User may add/remove columns between datasets - app should not break
- **First trigger definition:** User will define criteria; app provides the filtering mechanism
- **Metric formulas:** User will provide exact formulas for all 25 trading metrics
- **Single user:** No need for authentication, multi-user access, or data sharing
- **Local data:** All data stays on user's machine; no privacy/compliance concerns
- **Screen resolution:** User has 1080p or higher display
- **Performance baseline:** Sub-second response is acceptable; real-time (<16ms) not required

---

## Risks & Open Questions

### Key Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| ~~**Metric formulas undefined**~~ | ~~Can't complete metrics engine without all 25 formulas~~ | ~~High~~ | **MITIGATED** - All 25 metrics defined in Appendix D |
| ~~**First trigger logic ambiguity**~~ | ~~Core feature may not match user expectations~~ | ~~Medium~~ | **MITIGATED** - Algorithm defined in Appendix C |
| **PyQtGraph learning curve** | Interactive charting may take longer than expected | Medium | Build charting prototype early (technical spike) |
| **Pandas performance edge cases** | Large filters or complex aggregations may be slow | Low | Profile early; optimize or cache if needed |
| **PyQt6 dark mode styling** | Custom styling may be time-consuming | Medium | Use existing dark theme libraries (qdarkstyle) |
| **Excel file variations** | Different Excel formats/structures may cause load failures | Medium | Robust error handling + clear user feedback |
| **Scope creep** | Feature requests during development delay MVP | Medium | Strict phase boundaries; defer to post-MVP |
| **Solo developer burnout** | Project stalls due to competing priorities | Medium | Keep MVP minimal; celebrate incremental progress |

### Open Questions

**Data & Logic:**
- ~~What is the exact algorithm for "first trigger" identification?~~ **RESOLVED** - See Appendix C
- ~~What are the formulas for all 25 trading metrics?~~ **RESOLVED** - See Appendix D
- What date format(s) are used in the datasets?
- Which columns are required vs. optional?
- How should the app handle missing values in critical columns?

**UX & Design:**
- What should the default dark mode color scheme be?
- How should baseline vs. filtered comparison be visually presented?
- What chart types are needed in MVP vs. later phases?

**Technical:**
- Should filter configurations auto-save, or only on explicit user action?
- How should the app behave if Parquet conversion fails?
- What's the maximum expected dataset size (for future-proofing)?

### Areas Needing Further Research

- ~~**First trigger algorithm:** Need concrete examples with sample data to validate logic~~ **RESOLVED** - See Appendix C
- ~~**25 trading metrics:** Complete list with formulas required before development~~ **RESOLVED** - See Appendix D
- **UI/UX mockups:** Visual design for dark mode interface across all 4 tabs
- **PyQtGraph capabilities:** Confirm all required chart types and interactions are supported
- **PDF report layout:** What should the exported report look like?

---

## Appendices

### A. Research Summary

**Source: Brainstorming Session (2026-01-09)**

Key findings from the brainstorming session:

| Finding | Implication |
|---------|-------------|
| Speed is #1 priority | Architecture decisions favor performance |
| "First trigger" is core differentiator | Must be clearly defined before development |
| Comparison against baseline is essential | Every view shows delta from first-trigger baseline |
| Flexibility over rigidity | No strict schema validation; columns can change |
| 25 trading metrics required | Formulas needed as input to development |
| 4-tab structure emerged naturally | Data Input → Feature Explorer → PnL Stats → Monte Carlo |

**Technology decisions confirmed:**
- Pandas + Parquet for data (reliable, fast enough for 83k rows)
- PyQt6 + PyQtGraph for UI (native desktop, GPU-accelerated charts)
- Dark mode UI throughout

### B. References

| Document | Location | Purpose |
|----------|----------|---------|
| Brainstorming Results | `docs/brainstorming-session-results.md` | Full ideation session output |
| Project Brief | `docs/brief.md` | This document |
| PRD (to be created) | `docs/prd.md` | Detailed product requirements |
| Architecture (to be created) | `docs/architecture.md` | Technical design |

### C. First Trigger Algorithm Definition

The "first trigger" algorithm is the core filtering logic that differentiates Lumen from generic analysis tools.

#### Baseline First Trigger (No Filters Applied)

**Purpose:** Establish the baseline dataset for comparison. Used whenever baseline metrics are displayed.

**Algorithm:**
1. Group all rows by **ticker + date** (unique ticker-date pairs)
2. Within each group, sort chronologically by **time**
3. Keep only the **first row** (earliest time) per ticker-date
4. Discard all subsequent triggers for the same ticker-date

**Example:**

| Ticker | Date | Time | % from VWAP | Included in Baseline? |
|--------|------|------|-------------|----------------------|
| AAPL | 2020-01-01 | 8:45 AM | 9% | **Yes** (first for this ticker-date) |
| AAPL | 2020-01-01 | 9:15 AM | 11% | No (same ticker-date, later time) |
| AAPL | 2020-01-01 | 10:20 AM | 15% | No (same ticker-date, later time) |
| AAPL | 2020-01-02 | 9:00 AM | 8% | **Yes** (new date = new first trigger) |
| MSFT | 2020-01-01 | 8:50 AM | 12% | **Yes** (different ticker) |

**Result:** 3 rows in baseline (one per unique ticker-date)

---

#### Filtered First Trigger (With Feature Selection)

**Purpose:** Find the first trigger per ticker-date that meets ALL user-defined filter criteria.

**Algorithm:**
1. Group all rows by **ticker + date**
2. Within each group, sort chronologically by **time**
3. Iterate through rows in chronological order
4. Find the **first row that meets ALL filter criteria**
5. If found, include that row; discard all others for that ticker-date
6. If NO rows meet criteria, **exclude that ticker-date entirely** (Option A)

**Example (Filter: % from VWAP >= 10%):**

| Ticker | Date | Time | % from VWAP | Meets Filter? | Included? |
|--------|------|------|-------------|---------------|-----------|
| AAPL | 2020-01-01 | 8:45 AM | 9% | No | No |
| AAPL | 2020-01-01 | 9:15 AM | 11% | Yes | **Yes** (first meeting criteria) |
| AAPL | 2020-01-01 | 10:20 AM | 15% | Yes | No (already found first) |
| AAPL | 2020-01-02 | 9:00 AM | 8% | No | No |
| AAPL | 2020-01-02 | 10:00 AM | 7% | No | No |
| MSFT | 2020-01-01 | 8:50 AM | 12% | Yes | **Yes** (first for MSFT on this date) |

**Result:**
- AAPL 2020-01-01: Trigger at 9:15 AM included (first meeting >= 10%)
- AAPL 2020-01-02: **Excluded entirely** (no triggers met criteria)
- MSFT 2020-01-01: Trigger at 8:50 AM included

---

#### Key Rules Summary

| Rule | Description |
|------|-------------|
| **Grouping** | Always group by ticker + date |
| **Ordering** | Always sort chronologically within group |
| **Baseline** | First trigger per ticker-date, no filters |
| **Filtered** | First trigger per ticker-date meeting ALL criteria |
| **No match** | If no triggers meet criteria, ticker-date is excluded |
| **Comparison** | Filtered results always compared against baseline |

### D. Trading Metrics Definition (25 Total)

Complete specification of all trading metrics calculated by Lumen.

#### Data Requirements

- **gain_pct column:** Required column in dataset containing trade gain/loss as percentage
- **mae_pct column:** Required column containing Maximum Adverse Excursion percentage for each trade (used for stop loss calculations)
- **date column:** Required for chronological ordering and DD Duration calculation

**Note:** All percentage values are stored as whole numbers (e.g., 20 = 20%, not 0.20).

#### User Inputs

| Input | Default | Used By |
|-------|---------|---------|
| Stop Loss % | 8% | Trade-level stop adjustment, Max Loss % (15) |
| Efficiency % | 5% | Trade-level efficiency adjustment (applied to all trades) |
| Flat Stake $ | $10,000 | Flat Stake metrics (16-19) |
| Compounded Start Capital $ | User input | Compounded Kelly metrics (20-23) |
| Fractional Kelly Y% | User input | Metrics 9, 10, 20-23 |

---

#### Trade-Level Adjustments

Before any metric calculation, each trade's gain is adjusted using the following two-step process:

**Step 1: Stop Loss Adjustment**

If the trade's Maximum Adverse Excursion (MAE) exceeded the stop loss threshold, the trade is considered "stopped out" and the gain is capped at the stop loss:

```
IF mae_pct > stop_loss:
    stop_adjusted_gain_pct = -stop_loss
ELSE:
    stop_adjusted_gain_pct = gain_pct
```

**Step 2: Efficiency Adjustment**

Transaction costs and slippage are simulated by subtracting the efficiency percentage from every trade:

```
efficiency_adjusted_gain_pct = stop_adjusted_gain_pct - efficiency
```

**Example (stop_loss = 8, efficiency = 5):**

| gain_pct | mae_pct | Stop Hit? | stop_adjusted | efficiency_adjusted |
|----------|---------|-----------|---------------|---------------------|
| 20 | 3 | No | 20 | **15** |
| 10 | 10 | Yes (10 > 8) | -8 | **-13** |
| -2 | 5 | No | -2 | **-7** |
| 5 | 12 | Yes (12 > 8) | -8 | **-13** |

**Important:** All 25 trading metrics use `efficiency_adjusted_gain_pct` as the basis for calculations.

---

#### Core Statistics (12 metrics)

| # | Metric | Formula | Output |
|---|--------|---------|--------|
| 1 | Number of Trades | `COUNT(rows)` | Integer |
| 2 | Win Rate % | `COUNT(gain_pct > 0) / COUNT(all) × 100` | % |
| 3 | Average Winner % | `MEAN(gain_pct WHERE gain_pct > 0)` | % |
| 4 | Average Loser % | `MEAN(gain_pct WHERE gain_pct < 0)` | % |
| 5 | R:R Ratio | `ABS(Average Winner / Average Loser)` | Ratio |
| 6 | EV % | `(WinRate × AvgWinner) - ((1 - WinRate) × ABS(AvgLoser))` | % |
| 7 | Edge % | `((R:R + 1) × WinRate) - 1` | % |
| 8 | Kelly Criterion % | `Edge % / R:R` | % |
| 9 | Fractional Kelly % | `UserInput_Y% × Kelly Criterion %` | % |
| 10 | EG % | `((1 + R:R × Kelly × FracKelly)^WinRate) × ((1 - Kelly × FracKelly)^(1 - WinRate)) - 1` | % |
| 11 | Median Winner % | `MEDIAN(gain_pct WHERE gain_pct > 0)` | % |
| 12 | Median Loser % | `MEDIAN(gain_pct WHERE gain_pct < 0)` | % |

---

#### Streak & Loss Metrics (3 metrics)

| # | Metric | Formula | Output |
|---|--------|---------|--------|
| 13 | Max Consecutive Wins | Longest consecutive streak where gain_pct > 0 | Integer |
| 14 | Max Consecutive Losses | Longest consecutive streak where gain_pct < 0 | Integer |
| 15 | Max Loss % | `COUNT(gain_pct ≤ -StopLoss%) / COUNT(all) × 100` | % |

---

#### Flat Stake Metrics (4 metrics)

Calculated using fixed position size (default $10,000).

| # | Metric | Formula | Output |
|---|--------|---------|--------|
| 16 | Flat Stake PnL | `FlatStake$ × SUM(gain_pct)` | $ |
| 17 | Flat Stake Max DD ($) | `MAX(RunningPeak - CumulativePnL)` | $ |
| 18 | Flat Stake Max DD (%) | `MaxDD$ / PeakEquity × 100` | % |
| 19 | Flat Stake Max DD Duration | Trading days from peak to recovery (or end if not recovered) | Days |

**Calculation Notes:**
- Cumulative PnL: Running sum of `FlatStake$ × gain_pct` for each trade
- Running Peak: Maximum cumulative PnL seen up to that point
- Max DD: Largest difference between running peak and subsequent cumulative PnL

---

#### Compounded Kelly Metrics (4 metrics)

Calculated using Kelly-based position sizing with compounding.

| # | Metric | Formula | Output |
|---|--------|---------|--------|
| 20 | Compounded Kelly PnL | `StartCapital × Π(1 + gain_pct × Kelly% × FracKelly%)` | $ |
| 21 | Compounded Kelly Max DD ($) | `MAX(RunningPeak - CompoundedEquity)` | $ |
| 22 | Compounded Kelly Max DD (%) | `MaxDD$ / PeakEquity × 100` | % |
| 23 | Compounded Kelly Max DD Duration | Trading days from peak to recovery (or end if not recovered) | Days |

**Calculation Notes:**
- Each trade: `Equity_new = Equity_old × (1 + gain_pct × Kelly% × FracKelly%)`
- Running Peak: Maximum compounded equity seen up to that point
- Π denotes product (compounding) across all trades in chronological order

---

#### Distribution Visuals (2 metrics)

| # | Metric | Type | Data |
|---|--------|------|------|
| 24 | Winner Distribution | Histogram | All gain_pct values where gain_pct > 0 |
| 25 | Loser Distribution | Histogram | All gain_pct values where gain_pct < 0 |

**Display Notes:**
- User-configurable bin size
- Show count/frequency per bin
- Overlay with baseline distribution for comparison

---

## Next Steps

### Immediate Actions

1. ~~**Define first trigger algorithm**~~ **DONE** - See Appendix C
2. ~~**Gather all 25 metric formulas**~~ **DONE** - See Appendix D
3. **Create UI wireframes** - Sketch layouts for each of the 4 tabs
4. **Set up development environment** - Python, PyQt6, Pandas, PyQtGraph
5. **Build technical prototype** - Validate Pandas + PyQtGraph integration with sample data
6. **Create PRD** - Expand this brief into detailed product requirements

### PM Handoff

This Project Brief provides the full context for **Lumen**.

**Next step:** Start in 'PRD Generation Mode' to work through detailed requirements section by section, clarifying any open questions and expanding feature specifications.

**Key inputs needed before PRD:**
- ~~First trigger algorithm definition~~ **DONE** - See Appendix C
- ~~Complete list of 25 trading metrics with formulas~~ **DONE** - See Appendix D
- Sample dataset for testing/validation

---

*Generated with BMAD-METHOD Project Brief Template v2.0*
