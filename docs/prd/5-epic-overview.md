# 5. Epic Overview

| Epic | Title | Goal | Stories | Effort |
|------|-------|------|---------|--------|
| 1 | Foundation & Data Pipeline | Establish infrastructure, data loading, first-trigger baseline, core metrics | 7 | 13-20 hrs |
| 2 | Feature Explorer & Filtering | Interactive exploration, bounds filtering, charting, CSV export | 6 | 14-20 hrs |
| 3 | Metrics Engine | All 25 trading metrics, user inputs, equity calculations | 6 | 11-17 hrs |
| 4 | Comparison & Export | Comparison Ribbon, metrics grid, PnL charts, histograms, full export | 6 | 14-20 hrs |
| **Total** | **MVP** | **Complete trading analysis replacement for Excel** | **25** | **52-77 hrs** |

## Epic Flow

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
