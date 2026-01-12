# 9. Epic 4: Comparison & Export

## Epic Goal

Deliver the always-on baseline comparison that is Lumen's core differentiator. Upon completion, users see filtered metrics alongside baseline metrics with clear delta indicators, visualize equity curves and distributions via charts, and can export their analysis in multiple formats.

## Stories

### Story 4.1: Filtered Metrics Calculation

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

### Story 4.2: Comparison Ribbon (Validation Checkpoint)

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

### Story 4.3: Baseline vs Filtered Metrics Grid

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

### Story 4.4: PnL Equity Charts

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

### Story 4.5: Distribution Histograms

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

### Story 4.6: Full Export Functionality

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

## Epic 4 Definition of Done

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
