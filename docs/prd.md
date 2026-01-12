# Lumen Product Requirements Document (PRD)

**Version:** 1.0
**Date:** 2026-01-09
**Status:** Draft
**Author:** John (PM Agent)

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-01-09 | 1.0 | Initial PRD draft | John (PM) |

---

## Table of Contents

1. [Goals and Background Context](#1-goals-and-background-context)
2. [Requirements](#2-requirements)
3. [User Interface Design Goals](#3-user-interface-design-goals)
4. [Technical Assumptions](#4-technical-assumptions)
5. [Epic Overview](#5-epic-overview)
6. [Epic 1: Foundation & Data Pipeline](#6-epic-1-foundation--data-pipeline)
7. [Epic 2: Feature Explorer & Filtering](#7-epic-2-feature-explorer--filtering)
8. [Epic 3: Metrics Engine](#8-epic-3-metrics-engine)
9. [Epic 4: Comparison & Export](#9-epic-4-comparison--export)
10. [Checklist Results](#10-checklist-results)
11. [Next Steps](#11-next-steps)

---

## 1. Goals and Background Context

### Goals

- Deliver sub-second performance for trading data analysis on 83k+ row datasets, replacing slow Excel workflows
- Implement native "First Trigger" filtering logic that identifies the first signal per ticker-date meeting user criteria
- Provide all 25 trading metrics calculated instantly with always-on baseline comparison
- Enable rapid hypothesis testing through interactive charts and bounds-based filtering
- Create a professional dark-mode desktop application with 4-tab workflow (Data Input → Feature Explorer → PnL Stats → Monte Carlo placeholder)

### Background Context

Trading analysts currently struggle with Excel-based workflows that become prohibitively slow with large datasets. Operations that should take milliseconds stretch into seconds or minutes, crippling iteration speed and limiting data exploration. Existing alternatives (Python scripts, BI tools, trading platforms) either require programming expertise, lack domain-specific metrics, or aren't optimized for historical trade analysis.

Lumen addresses these pain points with a purpose-built architecture using Pandas + Parquet for data processing and PyQtGraph for GPU-accelerated visualization. The application's core differentiator is the "First Trigger" logic—impossible to replicate efficiently in Excel—combined with an always-on baseline comparison that measures every filtered result against the first-trigger baseline.

---

## 2. Requirements

### Functional Requirements

**FR1:** The system shall load Excel (.xlsx, .xls) and CSV files and automatically convert them to Parquet format for optimized performance.

**FR2:** The system shall provide a sheet selector dropdown when loading multi-sheet Excel files.

**FR3:** The system shall display clear, plain English error messages when file loading fails.

**FR4:** The system shall provide a column configuration panel for mapping required columns (Ticker, Date, Time, Gain %) with auto-detection and manual override.

**FR5:** The system shall support an optional Win/Loss column with fallback to deriving win/loss from Gain % values.

**FR6:** The system shall implement "First Trigger" logic that identifies the first row per ticker-date combination, sorted chronologically by time.

**FR7:** The system shall implement "Filtered First Trigger" logic that finds the first row per ticker-date meeting ALL user-defined filter criteria.

**FR8:** The system shall display baseline statistics (all 25 trading metrics) for the first-trigger dataset immediately upon data load.

**FR9:** The system shall provide bounds-based filtering with BETWEEN and NOT BETWEEN operators for numerical columns.

**FR10:** The system shall support multi-feature AND logic, combining up to 10 filter criteria.

**FR11:** The system shall provide a first-trigger toggle in Feature Explorer to switch between first-trigger filtered and raw data views.

**FR12:** The system shall provide date range selection to filter data by date.

**FR13:** The system shall render interactive charts with pan, zoom, and crosshair functionality using PyQtGraph.

**FR14:** The system shall calculate all 25 trading metrics as defined in the Project Brief Appendix D (Core Statistics, Streak & Loss, Flat Stake, Compounded Kelly, Distribution Visuals).

**FR15:** The system shall accept user inputs for: Stop Loss %, Flat Stake $, Compounded Start Capital $, and Fractional Kelly %.

**FR16:** The system shall display Flat Stake PnL chart (cumulative PnL over time by date).

**FR17:** The system shall display Compounded Kelly PnL chart with Kelly-based position sizing.

**FR18:** The system shall display Winner and Loser distribution histograms.

**FR19:** The system shall show side-by-side Baseline vs. Filtered comparison for all metrics with delta indicators.

**FR20:** The system shall display a Comparison Ribbon showing 4 key metrics (Trades, Win Rate, EV, Kelly) with baseline comparison.

**FR21:** The system shall export filtered datasets to CSV and Parquet formats.

**FR22:** The system shall export chart images to PNG format.

**FR23:** The system shall export metrics summary to CSV (baseline, filtered, delta).

**FR24:** The system shall display a 4-tab interface: Data Input, Feature Explorer, PnL & Trading Stats, Monte Carlo.

**FR25:** The system shall display Monte Carlo tab as disabled with "Coming in Phase 3" placeholder message.

**FR26:** The system shall persist column mappings for subsequent loads of the same file.

**FR27:** The system shall cache loaded data as Parquet for faster subsequent loads.

### Non-Functional Requirements

**NFR1:** Data load time shall be < 3 seconds for datasets up to 100,000 rows.

**NFR2:** Filter response time (metrics + chart update) shall be < 500ms.

**NFR3:** Chart render time for 83k+ data points shall be < 200ms.

**NFR4:** Memory footprint shall remain < 500MB with a 100k row dataset loaded.

**NFR5:** Application crash rate shall be 0 per 100 normal operation sessions.

**NFR6:** The application shall run on Windows 10/11 as a native desktop application.

**NFR7:** The application shall function fully offline with no network dependencies.

**NFR8:** The application shall use a professional dark mode UI theme throughout (Observatory palette).

**NFR9:** The application shall handle flexible column schemas without breaking when users add/remove columns between datasets.

**NFR10:** The system shall use Python 3.10+ with Pandas, PyQt6, PyQtGraph, and PyArrow libraries.

**NFR11:** The system shall use uv for dependency management with pyproject.toml configuration.

---

## 3. User Interface Design Goals

### Overall UX Vision

**"Observatory Control"** — Lumen's interface evokes the precision of a mission control room or astronomical observatory. Dark, data-dense, and technically sophisticated, with moments of visual clarity that guide the analyst's eye to what matters. The trader is a scientist; the UI is their instrument.

**Core UX Principles:**
- **Speed as UX** — Every interaction yields sub-500ms feedback; perceived performance builds trust
- **Always-on comparison** — Baseline metrics persist as reference; no context-switching required
- **Explore, don't configure** — Sensible defaults minimize setup; progressive disclosure for power users
- **Data as hero** — Chrome fades to background; numbers and charts dominate

### Typography

| Role | Font | Weight | Size | Color |
|------|------|--------|------|-------|
| Display/KPIs | Space Grotesk | Bold | 32-48px | #F0F0F5 |
| Headers | Space Grotesk | Medium | 18-24px | #F0F0F5 |
| Body/Labels | IBM Plex Sans | Regular | 13-16px | #A0A0B0 |
| Secondary | IBM Plex Sans | Light | 12-14px | #606070 |
| Data/Tables | JetBrains Mono | Regular | 13-14px | #F0F0F5 |
| Code/Filters | JetBrains Mono | Light | 12-13px | #FFB347 |

### Color System — "Observatory Palette"

```css
/* Background Layers */
--void-black:     #0D0D12;  /* App frame, deepest */
--space-dark:     #14141F;  /* Panel backgrounds */
--nebula-gray:    #1E1E2E;  /* Card surfaces */
--dust-gray:      #2A2A3C;  /* Elevated elements */

/* Accent Spectrum */
--plasma-cyan:    #00E5CC;  /* Positive, gains, success */
--solar-coral:    #FF6B6B;  /* Negative, losses, warnings */
--nova-amber:     #FFB347;  /* Highlights, active states */
--stellar-blue:   #4A90D9;  /* Baseline reference */
--comet-purple:   #9D6EFF;  /* Secondary accent */

/* Text Hierarchy */
--star-white:     #F0F0F5;  /* Primary text */
--moon-gray:      #A0A0B0;  /* Secondary text */
--asteroid-gray:  #606070;  /* Disabled, muted */
```

### Key Interaction Paradigms

| Paradigm | Description |
|----------|-------------|
| Tab-based workflow | Linear 4-tab progression guides analysis flow |
| Immediate feedback | All changes render in < 500ms |
| Persistent baseline | Reference metrics always visible |
| Direct manipulation | Charts support pan, zoom, crosshair |
| Bounds-based filtering | Slider/input ranges instead of query builders |

### Core Screens and Views

| Tab | Primary Elements |
|-----|------------------|
| **Data Input** | File picker, sheet selector, column configuration, load progress, baseline metrics summary |
| **Feature Explorer** | Column selector, bounds filters, first-trigger toggle, date range, interactive chart (60% width), filter summary |
| **PnL & Trading Stats** | Comparison Ribbon (signature element), 25-metric comparison grid, Flat Stake chart, Kelly chart, histograms |
| **Monte Carlo** | Disabled placeholder with "Coming in Phase 3" message |

### Signature Element: The Comparison Ribbon

A horizontal ribbon at the top of PnL Stats showing 4 key metrics with large numbers, delta indicators, and baseline comparison — Lumen's visual signature.

```
┌──────────────────────────────────────────────────────────────────┐
│   TRADES           WIN RATE          EV %            KELLY %    │
│    423              67.1%            3.21%           15.4%      │
│   ▼ 824 fewer      ▲ +8.9pp         ▲ +0.87pp       ▲ +3.3pp   │
│   vs 1,247         vs 58.2%         vs 2.34%        vs 12.1%   │
└──────────────────────────────────────────────────────────────────┘
```

### Motion & Micro-interactions

| Interaction | Animation | Duration |
|-------------|-----------|----------|
| Tab switch | Crossfade + slide | 200ms |
| Data load | Shimmer → fade in | 300ms |
| Filter apply | Metric value "tick" animation | 150ms |
| Chart update | Smooth point transitions | 250ms |
| Delta change | Brief pulse highlight | 400ms |

### Accessibility

**None (MVP)** — Personal-use tool; formal compliance deferred to commercial release.

### Target Platform

**Windows 10/11 Desktop Only**
- Minimum: 1920×1080 (1080p)
- Native PyQt6 application
- Dark mode exclusively (no light theme)

---

## 4. Technical Assumptions

### Repository Structure

**Structure: Monorepo**

```
Lumen/
├── src/                    # Application source code
│   ├── __init__.py
│   ├── main.py             # Entry point
│   ├── core/               # Shared utilities, data models, metrics engine
│   ├── ui/                 # Common UI components, themes
│   ├── data_input/         # Tab 1: File loading, column config, first trigger
│   ├── feature_explorer/   # Tab 2: Filtering, charting
│   ├── pnl_stats/          # Tab 3: Metrics display, comparison, charts
│   └── monte_carlo/        # Tab 4: Placeholder (Phase 3)
├── tests/                  # Unit and integration tests
├── assets/
│   └── fonts/              # Space Grotesk, IBM Plex Sans, JetBrains Mono
├── docs/                   # Documentation (PRD, architecture)
├── .lumen_cache/           # Parquet cache, column mappings
├── pyproject.toml          # Project configuration
└── uv.lock                 # Dependency lock file
```

### Service Architecture

**Architecture: Monolithic Desktop Application**

- Single-process application with in-memory data storage
- Tab-based UI with shared DataFrame context
- Event-driven architecture for UI updates (Qt signals/slots)
- No microservices, no backend server, no API layer
- All processing happens locally on user's machine

### Testing Requirements

**Level: Unit + Integration Testing**

| Test Type | Scope | Tools |
|-----------|-------|-------|
| Unit Tests | Metrics calculations, first trigger logic, filters | pytest |
| Integration Tests | Tab workflows, data flow between components | pytest + pytest-qt |
| Manual Testing | UI interactions, visual verification | Developer testing |

### Additional Technical Assumptions

- **Python 3.10+** — Required for modern type hints and performance
- **uv for dependency management** — Fast Rust-based package manager
- **pyproject.toml for project config** — Modern Python project standard
- **Pandas for data processing** — Chosen for reliability and documentation
- **Parquet for storage** — 10-20x faster than CSV; automatic conversion on load
- **PyQt6 for UI** — Native desktop look, professional widgets
- **PyQtGraph for charting** — GPU-accelerated, handles 83k+ points smoothly
- **PyArrow for Parquet I/O** — Standard library for Parquet read/write
- **openpyxl for Excel reading** — Handles .xlsx files
- **No external APIs** — Fully offline operation
- **No database** — In-memory DataFrame is sufficient for single-file analysis
- **No authentication** — Single-user desktop application
- **qdarkstyle or custom QSS** — For dark mode theming

---

## 5. Epic Overview

| Epic | Title | Goal | Stories | Effort |
|------|-------|------|---------|--------|
| 1 | Foundation & Data Pipeline | Establish infrastructure, data loading, first-trigger baseline, core metrics | 7 | 13-20 hrs |
| 2 | Feature Explorer & Filtering | Interactive exploration, bounds filtering, charting, CSV export | 6 | 14-20 hrs |
| 3 | Metrics Engine | All 25 trading metrics, user inputs, equity calculations | 6 | 11-17 hrs |
| 4 | Comparison & Export | Comparison Ribbon, metrics grid, PnL charts, histograms, full export | 6 | 14-20 hrs |
| **Total** | **MVP** | **Complete trading analysis replacement for Excel** | **25** | **52-77 hrs** |

### Epic Flow

```
Epic 1: Foundation & Data Pipeline
├── Project setup, themed UI, file loading
├── Column configuration with auto-detect
├── First trigger baseline algorithm
├── Core metrics (7) display
└── Parquet caching

     │
     ▼

Epic 2: Feature Explorer & Filtering
├── Column selector, basic chart
├── Bounds filtering
├── First-trigger toggle
├── CSV export (validation)
├── Multi-filter + date range
└── Interactive chart controls

     │
     ▼

Epic 3: Metrics Engine
├── Tab layout, user inputs
├── Core stats (1-12) + distribution prep
├── Streak & loss metrics (13-15)
├── Flat stake metrics (16-19)
├── Kelly compound metrics (20-23)
└── Distribution statistics display

     │
     ▼

Epic 4: Comparison & Export
├── Filtered metrics calculation
├── Comparison Ribbon (signature)
├── Baseline vs filtered grid
├── PnL equity charts
├── Distribution histograms
└── Full export (Parquet, PNG)
```

---

## 6. Epic 1: Foundation & Data Pipeline

### Epic Goal

Establish the complete project infrastructure and prove the core data pipeline end-to-end. Upon completion, users can load a trading data file, configure column mappings, see it automatically converted to Parquet for performance, and view baseline first-trigger statistics with 7 key metrics.

### Stories

#### Story 1.1: Project Scaffolding

**As a** developer,
**I want** a properly configured Python project with all dependencies,
**so that** I have a solid foundation for building Lumen.

**Acceptance Criteria:**

1. Project initialized with `uv` and `pyproject.toml` configuration
2. Directory structure created per Technical Assumptions
3. Core dependencies installed: PyQt6, pandas, pyarrow, pyqtgraph, openpyxl
4. `main.py` entry point creates basic `QApplication` and `QMainWindow`
5. Application runs without errors via `uv run python src/main.py`
6. Window appears with title "Lumen" and minimum size 1280x720
7. `.gitignore` configured for Python, PyQt, and `.lumen_cache/`

---

#### Story 1.2: Themed Application Shell

**As a** user,
**I want** a professional dark-themed interface with clear navigation,
**so that** I understand the application workflow and feel confident in the tool.

**Acceptance Criteria:**

1. `QTabWidget` with 4 tabs: "Data Input", "Feature Explorer", "PnL & Trading Stats", "Monte Carlo"
2. Tab order matches workflow; tabs not closable or movable
3. Monte Carlo tab displays centered message: "Monte Carlo simulations coming in Phase 3" with dimmed/disabled appearance
4. Observatory color palette implemented as QSS stylesheet
5. Fonts loaded from `assets/fonts/`: Space Grotesk, IBM Plex Sans, JetBrains Mono
6. Main window background uses void-black (#0D0D12)
7. Tab content areas use space-dark (#14141F)
8. Tab bar styled with nebula-gray background, star-white text
9. Active tab visually distinguished with accent border
10. Theme loading extracted to `src/ui/theme.py` for reuse

---

#### Story 1.3: File Selection & Data Loading

**As a** user,
**I want** to select and load my trading data file,
**so that** I can begin analyzing my trades.

**Acceptance Criteria:**

1. Data Input tab contains file loading section with styled controls
2. "Select File" button opens native file dialog (Excel, CSV filters)
3. File path display shows selected file
4. Sheet selector dropdown for Excel files (populated with sheet names)
5. "Load Data" button triggers loading with progress indicator
6. Success message: "✓ Loaded {n:,} rows from {filename}"
7. Error handling with plain English messages
8. Load completes in < 3 seconds for 100k rows
9. After successful load, trigger column auto-detection

---

#### Story 1.4: Column Configuration Panel

**As a** user,
**I want** to verify and adjust column mappings,
**so that** the analysis uses the correct data even if auto-detection fails.

**Acceptance Criteria:**

1. Auto-detection for required columns (Ticker, Date, Time, Gain %) with case-insensitive pattern matching
2. Auto-detection for optional Win/Loss column
3. If ALL required columns detected: show success summary with "Edit Mappings" option
4. If ANY required column missing: show blocking configuration panel
5. Column configuration panel shows dropdowns with status indicators (✓ detected, ⚠ guessed, ✗ missing)
6. Preview shows first 3 values from selected column
7. Win/Loss can be explicit column OR derived from Gain % with breakeven handling option
8. Validation: all required fields mapped, no duplicates
9. Persist mappings to `.lumen_cache/{file_hash}_mappings.json`
10. On "Continue", store mappings in app state and proceed

---

#### Story 1.5: First Trigger Baseline

**As a** user,
**I want** the first trigger per ticker-date automatically identified,
**so that** I have a clean baseline dataset for analysis.

**Acceptance Criteria:**

1. Apply first trigger algorithm using mapped column names:
   - Group by ticker + date
   - Sort by time within groups
   - Keep first row per group
2. Baseline DataFrame stored in app state
3. Display: "Baseline: {n:,} first triggers from {total:,} total rows"
4. Styled info card with stellar-blue left border
5. Edge case handling (single row, missing time, duplicates)
6. Algorithm completes in < 500ms for 100k rows

---

#### Story 1.6: Core Metrics Calculation & Display

**As a** user,
**I want** to see key trading metrics for my baseline data,
**so that** I can assess my overall trading performance.

**Acceptance Criteria:**

1. Calculate 7 core metrics: Number of Trades, Win Rate, Avg Winner, Avg Loser, R:R Ratio, EV, Kelly
2. Win Rate uses mapped Win/Loss column or derives from Gain % per configuration
3. Prepare distribution data (winner/loser arrays with statistics)
4. Display metrics in styled cards with appropriate formatting
5. Color coding: positive (plasma-cyan), negative (solar-coral)
6. Edge case handling (no winners, no losers, empty dataset)
7. Calculation completes in < 100ms for 100k rows

---

#### Story 1.7: Parquet Caching

**As a** user,
**I want** faster load times when reopening the same file,
**so that** I can iterate quickly on my analysis.

**Acceptance Criteria:**

1. After successful load, save DataFrame to `.lumen_cache/` as Parquet
2. Filename: MD5 hash of file path + sheet name
3. On file selection, check for valid cache (exists and newer than source)
4. Cache hit: load from Parquet, show "Loaded from cache"
5. Cache miss: load from source, save to cache
6. Performance: cache load < 500ms vs source load 2-3s
7. Handle corrupt cache by deleting and reloading
8. Cache excluded from git

---

### Epic 1 Definition of Done

- [ ] Application launches with professional Observatory dark theme
- [ ] 4-tab structure visible with Monte Carlo placeholder
- [ ] User can select Excel/CSV file and choose sheet
- [ ] Column mappings auto-detected or manually configured
- [ ] Win/Loss column supported (explicit or derived)
- [ ] First trigger baseline calculated using mapped columns
- [ ] 7 core metrics displayed in styled cards
- [ ] Subsequent file loads use Parquet cache
- [ ] Column mappings persisted for repeat file loads

---

## 7. Epic 2: Feature Explorer & Filtering

### Epic Goal

Enable interactive data exploration with bounds-based filtering, filtered first-trigger logic, and GPU-accelerated charting. Upon completion, users can select columns to analyze, apply range filters, toggle between raw and first-trigger views, and see instant visual feedback.

### Stories

#### Story 2.1: Feature Explorer Layout & Basic Chart

**As a** user,
**I want** to see my data visualized by column,
**so that** I can explore patterns and distributions.

**Acceptance Criteria:**

1. Tab layout: left sidebar (25%), main chart area (75%), bottom bar
2. Column selector dropdown with all numeric columns
3. PyQtGraph scatter plot showing selected column values
4. Chart styled with Observatory theme (space-dark background, plasma-cyan points)
5. Chart renders baseline first-trigger data by default
6. Bottom bar: "Showing {n:,} data points"
7. Chart updates < 200ms on column change
8. Handles 83k+ points without lag

---

#### Story 2.2: Bounds Filtering

**As a** user,
**I want** to filter data by value ranges,
**so that** I can focus on specific subsets of my trades.

**Acceptance Criteria:**

1. "Add Filter" button with filter row (column, operator, min, max, remove)
2. Operators: "between", "not between"
3. Filter validation (min ≤ max, numeric values)
4. "Apply Filters" updates chart and row count
5. Applied filters shown as styled chips (nova-amber)
6. "Clear All Filters" resets to baseline
7. Filter applied in < 500ms for 100k rows

---

#### Story 2.3: First-Trigger Toggle

**As a** user,
**I want** to apply first-trigger logic to my filtered data,
**so that** I see only the first qualifying signal per ticker-date.

**Acceptance Criteria:**

1. "First Trigger Only" toggle switch in filter controls
2. Toggle ON: apply filtered first trigger algorithm, show first trigger count
3. Toggle OFF: show all rows matching filters
4. Chart updates immediately on toggle (< 200ms)
5. Visual indicator when toggle ON (stellar-blue highlight)
6. Edge cases handled (no matches, no first triggers)

---

#### Story 2.4: Filtered Data Export (Validation Checkpoint)

**As a** user,
**I want** to export my filtered dataset,
**so that** I can validate results and continue analysis elsewhere.

**Acceptance Criteria:**

1. "Export Filtered Data" button in bottom bar
2. Save dialog with suggested filename
3. Export all columns, only filtered rows, CSV format
4. Include metadata comment with filter summary
5. Success toast notification
6. Export completes in < 2 seconds for 100k rows

---

#### Story 2.5: Multi-Filter Logic & Date Range

**As a** user,
**I want** to combine multiple filters and restrict by date,
**so that** I can test complex hypotheses.

**Acceptance Criteria:**

1. Support up to 10 simultaneous filters with AND logic
2. No duplicate columns (replace existing)
3. Active filters displayed as chips with remove button
4. Date range filter: start/end date pickers, "All Dates" checkbox
5. Filter summary in bottom bar
6. Filter chain applied in < 500ms for 100k rows

---

#### Story 2.6: Interactive Chart Controls

**As a** user,
**I want** to pan, zoom, and inspect my chart,
**so that** I can examine data points in detail.

**Acceptance Criteria:**

1. Scroll wheel zoom, left-click drag pan, right-click drag zoom selection
2. Double-click to reset view
3. Crosshair with coordinate display (moon-gray dashed lines)
4. Axis controls: Y/X min/max inputs, "Auto Fit" button
5. "Show Grid" toggle
6. Pan/zoom at 60fps for 83k points

---

### Epic 2 Definition of Done

- [ ] Feature Explorer tab displays interactive scatter chart
- [ ] User can select any numeric column to visualize
- [ ] Bounds filters (BETWEEN/NOT BETWEEN) work correctly
- [ ] First-trigger toggle switches between all matches and first triggers only
- [ ] Export confirms filter results match expectations
- [ ] Multiple filters combine with AND logic
- [ ] Date range filter restricts data by date
- [ ] Chart supports pan, zoom, and crosshair inspection
- [ ] All operations complete in < 500ms for 100k rows

---

## 8. Epic 3: Metrics Engine

### Epic Goal

Implement the complete 25-metric trading statistics engine with user input controls. Upon completion, the PnL & Trading Stats tab displays all metrics defined in the Project Brief Appendix D, accepts user inputs for position sizing parameters, and prepares data structures for comparison and charts.

### Stories

#### Story 3.1: PnL Stats Tab Layout & User Inputs Panel

**As a** user,
**I want** to configure analysis parameters,
**so that** I can customize metrics to my trading approach.

**Acceptance Criteria:**

1. Tab layout: top (user inputs), middle (metrics grid), bottom (charts placeholder)
2. User inputs: Flat Stake ($), Starting Capital ($), Fractional Kelly (%), Stop Loss (%)
3. Input validation with feedback
4. Inputs persist across tab switches
5. "Apply" button or auto-apply with debounce

---

#### Story 3.2: Core Statistics & Distribution Data (Metrics 1-12, 24-25 prep)

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

#### Story 3.3: Streak & Loss Metrics (13-15)

**As a** user,
**I want** to see streak and risk metrics,
**so that** I understand my drawdown risk.

**Acceptance Criteria:**

1. Calculate: Max Consecutive Wins, Max Consecutive Losses, Max Loss %
2. Streak detection on chronologically sorted data
3. Max Loss % uses stop_loss user input
4. Recalculate on stop_loss change

---

#### Story 3.4: Flat Stake Metrics (16-19)

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

#### Story 3.5: Compounded Kelly Metrics (20-23)

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

#### Story 3.6: Distribution Statistics Display (24-25)

**As a** user,
**I want** to see summary statistics for winners and losers,
**so that** I understand the spread of outcomes.

**Acceptance Criteria:**

1. Display winner/loser distribution statistics (count, range, mean, median, std)
2. Winner card with plasma-cyan border, loser card with solar-coral border
3. "View Histogram" link (histograms in Epic 4)
4. Calculate suggested bin size

---

### Epic 3 Definition of Done

- [ ] PnL & Trading Stats tab displays professional layout
- [ ] User can configure all 4 input parameters
- [ ] All 25 metrics calculated correctly per Appendix D
- [ ] Metrics update when user inputs change
- [ ] Reusable equity calculation module created
- [ ] Equity curves stored for chart rendering
- [ ] Distribution data prepared with statistics
- [ ] All calculations < 200ms for 100k rows

---

## 9. Epic 4: Comparison & Export

### Epic Goal

Deliver the always-on baseline comparison that is Lumen's core differentiator. Upon completion, users see filtered metrics alongside baseline metrics with clear delta indicators, visualize equity curves and distributions via charts, and can export their analysis in multiple formats.

### Stories

#### Story 4.1: Filtered Metrics Calculation

**As a** user,
**I want** metrics recalculated when I apply filters,
**so that** I can compare filtered results to baseline.

**Acceptance Criteria:**

1. Trigger on filter change or tab navigation
2. Reuse Epic 3 metrics engine
3. Store filtered metrics and equity curves in app state
4. Performance: core stats < 100ms, equity curves with 300ms debounce
5. Handle edge cases (no matches, single row)
6. Calculation status indicator

---

#### Story 4.2: Comparison Ribbon (Validation Checkpoint)

**As a** user,
**I want** to see key metrics with baseline comparison at a glance,
**so that** I can quickly assess my filter's impact.

**Acceptance Criteria:**

1. Fixed ribbon at top of PnL Stats tab
2. Display 4 metrics: Trades, Win Rate, EV, Kelly
3. Large filtered value, delta indicator, baseline reference
4. Delta colors: plasma-cyan (improvement), solar-coral (decline), moon-gray (neutral)
5. Empty state: "— (no filter applied)"
6. **Validation:** verify calculation logic before building full grid

---

#### Story 4.3: Baseline vs Filtered Metrics Grid

**As a** user,
**I want** to compare all 25 metrics,
**so that** I can analyze the full impact of my filters.

**Acceptance Criteria:**

1. Four-column grid: Metric | Baseline | Filtered | Delta
2. Collapsible sections by metric group
3. Delta formatting by type (pp, $, ratio, days)
4. Color coding based on improvement definitions
5. JetBrains Mono for numeric values

---

#### Story 4.4: PnL Equity Charts

**As a** user,
**I want** to visualize my equity curves,
**so that** I can see portfolio growth over time.

**Acceptance Criteria:**

1. Two charts: Flat Stake PnL, Compounded Kelly
2. Each shows baseline (stellar-blue) and filtered (plasma-cyan) curves
3. Interactive: pan, zoom, crosshair
4. Optional drawdown visualization
5. Consistent Observatory styling
6. Render 10k+ points < 500ms

---

#### Story 4.5: Distribution Histograms

**As a** user,
**I want** to see winner/loser distributions,
**so that** I can understand outcome spread.

**Acceptance Criteria:**

1. Two histograms: Winner, Loser
2. Baseline bars (stellar-blue 50%) overlaid with filtered bars
3. Binning controls (auto, 0.5%, 1%, 2%, 5%)
4. Mean/median reference lines
5. Hover tooltips with bin counts
6. "Show Baseline" toggle

---

#### Story 4.6: Full Export Functionality

**As a** user,
**I want** to export my analysis in multiple formats,
**so that** I can share or continue elsewhere.

**Acceptance Criteria:**

1. Export dropdown: Data, Charts, Report
2. Data: CSV, Parquet (with metadata), Metrics CSV
3. Charts: Individual PNG or All Charts ZIP
4. Chart resolution options (1080p, 4K)
5. Progress indicator, success toast
6. Error handling for permissions, disk space

---

### Epic 4 Definition of Done

- [ ] Filtered metrics calculate automatically on filter change
- [ ] Comparison Ribbon displays 4 key metrics with deltas
- [ ] Full 25-metric grid shows baseline vs filtered
- [ ] Flat Stake PnL chart renders both curves
- [ ] Kelly PnL chart renders both curves
- [ ] Winner/Loser histograms display correctly
- [ ] Export to CSV, Parquet, PNG all functional
- [ ] Improvement logic correct throughout
- [ ] Performance targets met

---

## 10. Checklist Results

**Validation Date:** 2026-01-09
**Validator:** John (PM Agent)
**Overall Status:** READY FOR ARCHITECT

### Category Analysis

| Category | Status | Notes |
|----------|--------|-------|
| 1. Problem Definition & Context | PASS | Clear problem, target users, success metrics |
| 2. MVP Scope Definition | PASS | Well-bounded with explicit out-of-scope |
| 3. User Experience Requirements | PASS | Detailed UI spec, flows documented |
| 4. Functional Requirements | PASS | 27 FRs, all testable |
| 5. Non-Functional Requirements | PASS | 11 NFRs; Security N/A (offline desktop) |
| 6. Epic & Story Structure | PASS | 25 stories, proper sequencing |
| 7. Technical Guidance | PASS | Stack defined, architecture direction clear |
| 8. Cross-Functional Requirements | PARTIAL | No external integrations (by design) |
| 9. Clarity & Communication | PASS | Well-structured, consistent terminology |

### Summary Metrics

| Metric | Assessment |
|--------|------------|
| Overall PRD Completeness | 92% |
| MVP Scope Appropriateness | Just Right |
| Readiness for Architecture | Ready |

### Recommendations

1. **Technical spike** - Recommend PyQtGraph prototype early to validate charting approach
2. **Sample dataset** - Create 1000-row sample for testing/validation
3. **Distribution histograms** - Could defer to Phase 2 if timeline tight (Story 4.5)

---

## 11. Next Steps

### UX Expert Prompt

> Review the Lumen PRD (docs/prd.md), focusing on the User Interface Design Goals section. Create wireframes or mockups for the 4-tab interface, paying special attention to:
> - The Comparison Ribbon signature element
> - The Observatory dark theme color palette
> - Data Input tab with column configuration panel
> - Feature Explorer tab layout (sidebar + chart)
> - PnL Stats tab with metrics grid and charts

### Architect Prompt

> Review the Lumen PRD (docs/prd.md) and Project Brief (docs/brief.md). Create a technical architecture document that includes:
> - Module structure and dependencies
> - Data flow between tabs/components
> - App state management approach
> - Metrics calculation engine design
> - PyQtGraph integration patterns
> - Testing strategy

---

## Appendix: Story Summary

| Epic | Story | Title | Effort |
|------|-------|-------|--------|
| 1 | 1.1 | Project Scaffolding | 1-2 hrs |
| 1 | 1.2 | Themed Application Shell | 3-4 hrs |
| 1 | 1.3 | File Selection & Data Loading | 2-3 hrs |
| 1 | 1.4 | Column Configuration Panel | 2-3 hrs |
| 1 | 1.5 | First Trigger Baseline | 2-3 hrs |
| 1 | 1.6 | Core Metrics Calculation & Display | 2-3 hrs |
| 1 | 1.7 | Parquet Caching | 1-2 hrs |
| 2 | 2.1 | Feature Explorer Layout & Basic Chart | 3-4 hrs |
| 2 | 2.2 | Bounds Filtering | 3-4 hrs |
| 2 | 2.3 | First-Trigger Toggle | 2-3 hrs |
| 2 | 2.4 | Filtered Data Export | 1-2 hrs |
| 2 | 2.5 | Multi-Filter Logic & Date Range | 3-4 hrs |
| 2 | 2.6 | Interactive Chart Controls | 2-3 hrs |
| 3 | 3.1 | PnL Stats Tab Layout & User Inputs | 2-3 hrs |
| 3 | 3.2 | Core Statistics & Distribution Data | 3-4 hrs |
| 3 | 3.3 | Streak & Loss Metrics | 1-2 hrs |
| 3 | 3.4 | Flat Stake Metrics | 2-3 hrs |
| 3 | 3.5 | Compounded Kelly Metrics | 2-3 hrs |
| 3 | 3.6 | Distribution Statistics Display | 1-2 hrs |
| 4 | 4.1 | Filtered Metrics Calculation | 2-3 hrs |
| 4 | 4.2 | Comparison Ribbon | 2-3 hrs |
| 4 | 4.3 | Baseline vs Filtered Metrics Grid | 3-4 hrs |
| 4 | 4.4 | PnL Equity Charts | 3-4 hrs |
| 4 | 4.5 | Distribution Histograms | 2-3 hrs |
| 4 | 4.6 | Full Export Functionality | 2-3 hrs |
| **Total** | **25 stories** | | **52-77 hrs** |

---

*Generated with BMAD-METHOD PRD Template v2.0*
