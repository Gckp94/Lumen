# 3. User Interface Design Goals

## Overall UX Vision

**"Observatory Control"** — Lumen's interface evokes the precision of a mission control room or astronomical observatory. Dark, data-dense, and technically sophisticated, with moments of visual clarity that guide the analyst's eye to what matters. The trader is a scientist; the UI is their instrument.

**Core UX Principles:**
- **Speed as UX** — Every interaction yields sub-500ms feedback; perceived performance builds trust
- **Always-on comparison** — Baseline metrics persist as reference; no context-switching required
- **Explore, don't configure** — Sensible defaults minimize setup; progressive disclosure for power users
- **Data as hero** — Chrome fades to background; numbers and charts dominate

## Typography

| Role | Font | Weight | Size | Color |
|------|------|--------|------|-------|
| Display/KPIs | Space Grotesk | Bold | 32-48px | #F0F0F5 |
| Headers | Space Grotesk | Medium | 18-24px | #F0F0F5 |
| Body/Labels | IBM Plex Sans | Regular | 13-16px | #A0A0B0 |
| Secondary | IBM Plex Sans | Light | 12-14px | #606070 |
| Data/Tables | JetBrains Mono | Regular | 13-14px | #F0F0F5 |
| Code/Filters | JetBrains Mono | Light | 12-13px | #FFB347 |

## Color System — "Observatory Palette"

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

## Key Interaction Paradigms

| Paradigm | Description |
|----------|-------------|
| Tab-based workflow | Linear 4-tab progression guides analysis flow |
| Immediate feedback | All changes render in < 500ms |
| Persistent baseline | Reference metrics always visible |
| Direct manipulation | Charts support pan, zoom, crosshair |
| Bounds-based filtering | Slider/input ranges instead of query builders |

## Core Screens and Views

| Tab | Primary Elements |
|-----|------------------|
| **Data Input** | File picker, sheet selector, column configuration, load progress, baseline metrics summary |
| **Feature Explorer** | Column selector, bounds filters, first-trigger toggle, date range, interactive chart (60% width), filter summary |
| **PnL & Trading Stats** | Comparison Ribbon (signature element), 25-metric comparison grid, Flat Stake chart, Kelly chart, histograms |
| **Monte Carlo** | Disabled placeholder with "Coming in Phase 3" message |

## Signature Element: The Comparison Ribbon

A horizontal ribbon at the top of PnL Stats showing 4 key metrics with large numbers, delta indicators, and baseline comparison — Lumen's visual signature.

```
┌──────────────────────────────────────────────────────────────────┐
│   TRADES           WIN RATE          EV %            KELLY %    │
│    423              67.1%            3.21%           15.4%      │
│   ▼ 824 fewer      ▲ +8.9pp         ▲ +0.87pp       ▲ +3.3pp   │
│   vs 1,247         vs 58.2%         vs 2.34%        vs 12.1%   │
└──────────────────────────────────────────────────────────────────┘
```

## Motion & Micro-interactions

| Interaction | Animation | Duration |
|-------------|-----------|----------|
| Tab switch | Crossfade + slide | 200ms |
| Data load | Shimmer → fade in | 300ms |
| Filter apply | Metric value "tick" animation | 150ms |
| Chart update | Smooth point transitions | 250ms |
| Delta change | Brief pulse highlight | 400ms |

## Accessibility

**None (MVP)** — Personal-use tool; formal compliance deferred to commercial release.

## Target Platform

**Windows 10/11 Desktop Only**
- Minimum: 1920×1080 (1080p)
- Native PyQt6 application
- Dark mode exclusively (no light theme)

---
