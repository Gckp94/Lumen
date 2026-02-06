# Feature Impact Tab & Tab Overflow Navigation Design

**Date:** 2026-02-07
**Status:** Approved

---

## Overview

Two related features to enhance Lumen's analytics workflow:

1. **Feature Impact Tab** - A scorecard ranking all features by their predictive power using interpretable metrics (no ML black boxes)
2. **Tab Overflow Menu** - Solution for displaying 14+ tabs without horizontal crowding

---

## Feature 1: Feature Impact Tab

### Purpose

Help traders quickly identify which features in their dataset have the most impact on trade outcomes, using simple, interpretable metrics rather than machine learning.

### Key Decisions

| Decision | Choice |
|----------|--------|
| Metrics displayed | Both correlation AND lift metrics |
| Lift calculation | Optimal threshold (auto-find best split point) |
| Tab location | New dedicated tab |
| Column selection | All numeric columns with exclusion checkboxes |
| Filter handling | Show both baseline AND filtered columns |
| First Trigger toggle | Respect global toggle (consistent with other tabs) |
| Row click behavior | Inline expansion with mini chart |
| Sorting | Composite Impact Score (default) + clickable headers |
| Impact Score weighting | 50% Expectancy Lift, 25% Win Rate Lift, 25% Correlation |
| Color coding | Gradient shading (coral → neutral → cyan) |
| Export | Not needed |

---

### Layout Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────┐ ┌─────────────────────┐ │
│ │          HEADER BAR                 │ │   COLUMN TOGGLES    │ │
│ │  "Feature Impact" + summary stats   │ │   ☑ gap_pct         │ │
│ │  Sorted by: Impact Score ▼          │ │   ☑ volume_ratio    │ │
│ └─────────────────────────────────────┘ └─────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                   SCORECARD TABLE                       │   │
│   │  Feature │ Impact │ Corr │ WR Lift │ EV Lift │ Trades   │   │
│   │  ────────┼────────┼──────┼─────────┼─────────┼────────  │   │
│   │  feat_a  │  0.82  │ +.15 │  +12.3% │  +0.45  │  2,341   │   │
│   │    └── [EXPANDED: Mini histogram + threshold info]      │   │
│   │  feat_b  │  0.71  │ +.08 │   +8.1% │  +0.22  │  2,341   │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### Table Columns

Each metric has **two sub-columns**: Baseline and Filtered.

| Column | Description | Gradient |
|--------|-------------|----------|
| **Feature** | Column name from dataset | None |
| **Impact Score** | Composite: 50% EV + 25% WR + 25% Corr | Cyan intensity |
| **Correlation** | Pearson correlation with gain_pct | Coral ↔ Neutral ↔ Cyan |
| **Win Rate Lift** | % improvement at optimal threshold | Coral ↔ Neutral ↔ Cyan |
| **Expectancy Lift** | EV improvement at optimal threshold | Coral ↔ Neutral ↔ Cyan |
| **Trades** | Count (Baseline / Filtered) | None |

**Gradient Logic:**
- Negative values: interpolate toward `SIGNAL_CORAL` (#FF4757)
- Neutral (zero): `BG_ELEVATED` (#1E1E2C)
- Positive values: interpolate toward `SIGNAL_CYAN` (#00FFD4)
- Text color adjusts for contrast

---

### Expanded Row Detail

Clicking a row reveals:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│   ┌─ OPTIMAL THRESHOLD ──────────────────────────────────────────────────┐   │
│   │                                                                      │   │
│   │   Threshold: gap_pct > 2.35%                                         │   │
│   │                                                                      │   │
│   │   ▂▃▄▅▆▇█▇▆▅▄▃▂▁    ← Win Rate by Percentile (spark line)           │   │
│   │   0%            100%                                                 │   │
│   │            ↑ threshold                                               │   │
│   │                                                                      │   │
│   │   BELOW THRESHOLD        ABOVE THRESHOLD                             │   │
│   │   ─────────────────      ─────────────────                           │   │
│   │   Trades: 1,402          Trades: 939                                 │   │
│   │   Win Rate: 54.2%        Win Rate: 66.5%  ← +12.3%                   │   │
│   │   Avg Gain: +1.82%       Avg Gain: +2.91%                            │   │
│   │   Expectancy: 0.32       Expectancy: 0.77  ← +0.45                   │   │
│   │                                                                      │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Components:**
- Spark line: 50-bar mini histogram using pyqtgraph
- Threshold marker: Vertical cyan line at optimal split
- Comparison cards: Below vs Above threshold stats
- Animation: 150ms ease-out expand, chart fades in

---

### Header Bar

```
┌─────────────────────────────────────────────────────────────────────────────┐
│   FEATURE IMPACT                                    ┌─ EXCLUDE COLUMNS ───┐ │
│   ━━━━━━━━━━━━━━━                                   │ ☑ gap_pct           │ │
│                                                     │ ☑ volume_ratio      │ │
│   Analyzing 47 features across 2,341 trades        │ ☐ ticker  (excluded) │ │
│   Baseline: 2,341  │  Filtered: 1,204              │ ☐ date    (excluded) │ │
│                                                     │ ☑ float_pct         │ │
│   Sorted by: Impact Score ▼                         └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Auto-excluded columns:** `date`, `ticker`, `gain_pct`, `trigger_number`, `time`, and any non-numeric columns.

---

### Calculations

**Optimal Threshold Algorithm:**
1. Sort trades by feature value
2. For each unique value as potential threshold:
   - Calculate win rate above vs below
   - Track the split that maximizes win rate difference
3. Return threshold value and resulting lift metrics

**Impact Score Formula:**
```
impact_score = (0.50 * normalized_ev_lift) +
               (0.25 * normalized_wr_lift) +
               (0.25 * abs(normalized_correlation))
```

Where normalization scales each metric to 0-1 range across all features.

---

## Feature 2: Tab Overflow Menu

### Purpose

Handle 14+ tabs gracefully without horizontal scrolling or cramped tabs.

### Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ┌──────────┐┌─────────────────┐┌───────────┐┌────────────┐┌─────────┐ ┌─┐  │
│  │Data Input││Feature Explorer ││ Breakdown ││Data Binning││PnL Stats│ │⋯│  │
│  └──────────┘└─────────────────┘└───────────┘└────────────┘└─────────┘ └─┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                                                          │
         OVERFLOW MENU ───────────────────────────────────────────────────┘
         ┌────────────────────────────┐
         │  Monte Carlo               │
         │  Parameter Sensitivity     │
         │  Feature Insights          │
         │  Feature Impact         ●  │  ← new tab indicator
         │ ─────────────────────────  │
         │  Portfolio Overview        │
         │  Portfolio Breakdown       │
         │  Portfolio Metrics         │
         │ ─────────────────────────  │
         │  Chart Viewer              │
         │  Statistics                │
         └────────────────────────────┘
```

### Visual Specs

| Element | Specification |
|---------|---------------|
| Overflow button | `⋯` or `»`, 28x28px, `BG_ELEVATED` background |
| Button visibility | Only when tabs exceed available width |
| Menu background | `BG_ELEVATED` (#1E1E2C) |
| Menu border | 1px `BG_BORDER` (#2A2A3A) |
| Group separators | 1px `BG_BORDER` with 8px margin |
| Hover state | `rgba(0, 255, 212, 0.15)` |
| Active tab badge | Cyan dot on overflow button if hidden tab is active |

### Behavior

1. **Dynamic visibility**: Overflow button appears/disappears based on available width
2. **Tab promotion**: Clicking a hidden tab moves it to visible area (swaps with rightmost)
3. **Grouping**: Menu items grouped by category with subtle separators:
   - Analysis: Monte Carlo, Param Sensitivity, Feature Insights, Feature Impact
   - Portfolio: Overview, Breakdown, Metrics
   - Tools: Chart Viewer, Statistics

### Implementation Note

PyQt6Ads already supports `DockAreaHasTabsMenuButton` config flag which provides similar functionality. May need customization for:
- Tab promotion behavior
- Grouped menu with separators
- New tab indicator badge

---

## Technical Notes

### New Files
- `src/tabs/feature_impact.py` - Main tab implementation
- `src/core/feature_impact_calculator.py` - Optimal threshold and scoring logic

### Modified Files
- `src/ui/main_window.py` - Add Feature Impact tab to dock setup
- `src/ui/dock_manager.py` - Customize overflow menu behavior

### Dependencies
- Uses existing: `pyqtgraph` (spark charts), `pandas` (calculations)
- No new dependencies required

---

## Aesthetic Guidelines

Follows Lumen Observatory Palette:
- Background: `BG_SURFACE` (#141420)
- Elevated: `BG_ELEVATED` (#1E1E2C)
- Positive: `SIGNAL_CYAN` (#00FFD4)
- Negative: `SIGNAL_CORAL` (#FF4757)
- Fonts: Azeret Mono (data), Geist (UI)
