# 1. Goals and Background Context

## Goals

- Deliver sub-second performance for trading data analysis on 83k+ row datasets, replacing slow Excel workflows
- Implement native "First Trigger" filtering logic that identifies the first signal per ticker-date meeting user criteria
- Provide all 25 trading metrics calculated instantly with always-on baseline comparison
- Enable rapid hypothesis testing through interactive charts and bounds-based filtering
- Create a professional dark-mode desktop application with 4-tab workflow (Data Input → Feature Explorer → PnL Stats → Monte Carlo placeholder)

## Background Context

Trading analysts currently struggle with Excel-based workflows that become prohibitively slow with large datasets. Operations that should take milliseconds stretch into seconds or minutes, crippling iteration speed and limiting data exploration. Existing alternatives (Python scripts, BI tools, trading platforms) either require programming expertise, lack domain-specific metrics, or aren't optimized for historical trade analysis.

Lumen addresses these pain points with a purpose-built architecture using Pandas + Parquet for data processing and PyQtGraph for GPU-accelerated visualization. The application's core differentiator is the "First Trigger" logic—impossible to replicate efficiently in Excel—combined with an always-on baseline comparison that measures every filtered result against the first-trigger baseline.

---
