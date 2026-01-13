# Epic 6: Data Binning - Brownfield Enhancement

**Version:** 1.0  
**Date:** 2026-01-13  
**Author:** Sarah (PO Agent)  
**Status:** Draft

---

## Epic Goal

Enable users to analyze trading data distributions by binning any numeric column into custom ranges and visualizing key metrics (average, median, count, win rate) per bin through an intuitive new tab interface.

---

## Existing System Context

- **Current Functionality:** Lumen is a PyQt6 desktop app with 4 main tabs (Data Input, Feature Explorer, PnL Stats, Monte Carlo)
- **Technology Stack:** Python 3.12+, PyQt6, pandas, matplotlib
- **Integration Points:** 
  - AppState (centralized state with `raw_df`, `baseline_df`, filters)
  - Existing ChartCanvas component for matplotlib integration
  - Stop loss & efficiency filter application from Data Input tab
  - Column mapping system for identifying data columns

---

## Enhancement Details

### What's Being Added

A new **"Data Binning"** tab that allows users to:

1. **Select any numeric column** for binning analysis
2. **Define custom bin ranges** with flexible operators:
   - Less than (`<`)
   - Greater than (`>`)
   - Range (`X-Y`)
   - Nulls (automatically captured in dedicated bin)
3. **Support time format input** (`HHMMSS` → `HH:MM:SS`)
4. **View 4 horizontal bar charts:**
   - Average gain_pct or adjusted_gain_pct per bin
   - Median gain_pct or adjusted_gain_pct per bin  
   - Count per bin (total rows in each bin)
   - Win rate per bin (wins / total in bin)
5. **Toggle between gain_pct and adjusted_gain_pct** for metric calculations
6. **Save/Load bin configurations** for reuse
7. **Visual enhancements:**
   - Gradient colors indicating relative magnitude
   - Tooltips showing exact values
   - Scrollable chart area

### How It Integrates

- Receives data from `AppState.raw_df` with only stop_loss and efficiency applied (not other filters)
- Follows existing tab architecture pattern (QWidget with setup methods)
- Uses existing UI constants (Colors, Fonts, spacing)
- Bin configurations saved to user's local storage (similar to column mappings)

### Success Criteria

- User can create bins for any numeric column including time columns
- Charts accurately reflect data distributions
- Bin configurations persist across sessions
- UI matches existing Lumen design language
- Performance remains acceptable with large datasets (100k+ rows)

---

## Stories

### Story 6.1: Data Binning Tab Foundation
**Goal:** Create the basic tab structure with column selector and bin configuration panel

**Key Deliverables:**
- New `src/tabs/data_binning.py` with `DataBinningTab` class
- Column dropdown populated from numeric columns
- Bin configuration UI (add/remove bins, operator selection, value inputs)
- Time format parsing (`HHMMSS` → `HH:MM:SS`)
- Integration with main window tab bar

**Estimated Effort:** 4-6 hours

---

### Story 6.2: Binning Engine & Chart Visualization
**Goal:** Implement binning logic and render the 4 horizontal bar charts

**Key Deliverables:**
- Bin assignment algorithm supporting <, >, range, and null handling
- Chart rendering for Average, Median, Count, Win Rate
- gain_pct / adjusted_gain_pct toggle
- Gradient coloring based on relative values
- Tooltips with exact values
- Scrollable chart container

**Estimated Effort:** 5-7 hours

---

### Story 6.3: Bin Configuration Persistence
**Goal:** Enable saving and loading of bin configurations

**Key Deliverables:**
- Save bin configuration to JSON file
- Load bin configuration from file
- Configuration includes: column name, bin definitions, metric selection
- File dialog for save/load operations
- Recent configurations quick access (optional)

**Estimated Effort:** 2-3 hours

---

## Compatibility Requirements

- [x] Existing APIs remain unchanged
- [x] No database schema changes required
- [x] UI changes follow existing patterns (sidebar + content area)
- [x] Performance impact is minimal (binning is O(n) operation)
- [x] No changes to existing tabs or components

---

## Risk Mitigation

**Primary Risk:** Large datasets causing slow chart rendering

**Mitigation:** 
- Use pandas vectorized operations for binning
- Limit chart redraw frequency with debouncing
- Consider sampling for datasets > 500k rows (with user notification)

**Rollback Plan:** 
- Tab is isolated and can be removed from main_window.py tab registration
- No changes to core components or existing functionality

---

## Definition of Done

- [ ] All 3 stories completed with acceptance criteria met
- [ ] Existing functionality verified through test suite (no regressions)
- [ ] New unit tests for binning logic (>90% coverage)
- [ ] Widget tests for DataBinningTab
- [ ] Manual QA completed
- [ ] Code follows existing patterns and coding standards

---

## Technical Notes

### Data Flow
```
AppState.raw_df 
    → Apply stop_loss/efficiency only
    → Column selection
    → Bin assignment
    → Metric calculation per bin
    → Chart rendering
```

### UI Layout (Proposed)
```
┌─────────────────────────────────────────────────────────────┐
│                     Data Binning Tab                         │
├──────────────┬──────────────────────────────────────────────┤
│   Sidebar    │              Chart Area (Scrollable)          │
│              │  ┌────────────────────────────────────────┐   │
│ Column:      │  │     Average [gain_pct ▼]               │   │
│ [dropdown]   │  │     ████████████████ 2.45%             │   │
│              │  │     ████████████ 1.89%                 │   │
│ Bins:        │  │     ████████ 1.23%                     │   │
│ [< 1M    ]   │  └────────────────────────────────────────┘   │
│ [1M-10M  ]   │  ┌────────────────────────────────────────┐   │
│ [10M-50M ]   │  │     Median                             │   │
│ [> 50M   ]   │  │     ...                                │   │
│ [Nulls   ]   │  └────────────────────────────────────────┘   │
│              │  ┌────────────────────────────────────────┐   │
│ [+ Add Bin]  │  │     Count                              │   │
│              │  │     ...                                │   │
│ ──────────── │  └────────────────────────────────────────┘   │
│ [Save Config]│  ┌────────────────────────────────────────┐   │
│ [Load Config]│  │     Win Rate                           │   │
│              │  │     ...                                │   │
└──────────────┴──┴────────────────────────────────────────┴───┘
```

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-01-13 | 1.0 | Initial epic creation | Sarah (PO Agent) |
