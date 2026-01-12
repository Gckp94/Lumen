# 2. High-Level Architecture

## System Overview

Lumen is a **monolithic desktop application** built with Python and PyQt6. All processing occurs locally on the user's machine with no network dependencies.

```
┌─────────────────────────────────────────────────────────────┐
│                    Lumen Application                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    UI Layer                          │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │    │
│  │  │Data Input│ │ Feature  │ │PnL Stats │ │ Monte  │  │    │
│  │  │   Tab    │ │ Explorer │ │   Tab    │ │ Carlo  │  │    │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────────┘  │    │
│  └───────┼────────────┼────────────┼───────────────────┘    │
│          │            │            │                         │
│          ▼            ▼            ▼                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                  AppState (QObject)                  │    │
│  │         Centralized State + Signal Emission          │    │
│  └─────────────────────────────────────────────────────┘    │
│          │            │            │                         │
│          ▼            ▼            ▼                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   Core Layer                         │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │    │
│  │  │  File    │ │  Filter  │ │ Metrics  │ │ Equity │  │    │
│  │  │ Loader   │ │  Engine  │ │Calculator│ │  Calc  │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
│          │                                                   │
│          ▼                                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   I/O Layer                          │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐             │    │
│  │  │  Cache   │ │  Export  │ │  Config  │             │    │
│  │  │ Manager  │ │ Manager  │ │ Manager  │             │    │
│  │  └──────────┘ └──────────┘ └──────────┘             │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Repository Structure

```
Lumen/
├── src/
│   ├── __init__.py
│   ├── __version__.py          # Version string
│   ├── main.py                 # Entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── app_state.py        # Centralized state (QObject)
│   │   ├── models.py           # Data models (dataclasses)
│   │   ├── constants.py        # Application constants
│   │   ├── exceptions.py       # Custom exceptions
│   │   ├── file_loader.py      # Excel/CSV/Parquet loading
│   │   ├── column_mapper.py    # Auto-detection + manual mapping
│   │   ├── first_trigger.py    # First trigger algorithm
│   │   ├── filter_engine.py    # Bounds filtering logic
│   │   ├── metrics.py          # 25 trading metrics
│   │   ├── equity.py           # Equity curve calculations
│   │   ├── cache_manager.py    # Parquet caching
│   │   └── export_manager.py   # CSV/Parquet/PNG export
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── theme.py            # QSS stylesheet, font loading
│   │   ├── constants.py        # Colors, fonts, spacing, animation
│   │   ├── main_window.py      # QMainWindow + tab container
│   │   └── components/
│   │       ├── __init__.py
│   │       ├── metric_card.py
│   │       ├── comparison_ribbon.py
│   │       ├── filter_chip.py
│   │       ├── toggle_switch.py
│   │       ├── data_grid.py
│   │       ├── chart_canvas.py
│   │       ├── toast.py
│   │       └── empty_state.py
│   └── tabs/
│       ├── __init__.py
│       ├── data_input.py       # Tab 1: File loading, column config
│       ├── feature_explorer.py # Tab 2: Filtering, charting
│       ├── pnl_stats.py        # Tab 3: Metrics, comparison, charts
│       └── monte_carlo.py      # Tab 4: Placeholder
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Shared fixtures
│   ├── unit/
│   │   ├── test_first_trigger.py
│   │   ├── test_filter_engine.py
│   │   ├── test_metrics.py
│   │   ├── test_equity.py
│   │   ├── test_cache_manager.py
│   │   └── test_export_manager.py
│   ├── widget/
│   │   ├── test_metric_card.py
│   │   ├── test_filter_chip.py
│   │   ├── test_comparison_ribbon.py
│   │   └── test_data_grid.py
│   └── integration/
│       ├── test_file_load_workflow.py
│       ├── test_filter_workflow.py
│       ├── test_session.py
│       └── test_performance.py
├── assets/
│   └── fonts/
│       ├── AzeretMono-Regular.ttf
│       ├── AzeretMono-Bold.ttf
│       ├── AzeretMono-Medium.ttf
│       ├── Geist-Regular.otf
│       ├── Geist-Bold.otf
│       ├── Geist-Medium.otf
│       └── Geist-Light.otf
├── docs/
│   ├── prd.md
│   ├── front-end-spec.md
│   └── architecture.md         # This document
├── .lumen_cache/               # Git-ignored cache directory
├── pyproject.toml
├── uv.lock
├── Makefile
├── lumen.spec                  # PyInstaller config
├── .pre-commit-config.yaml
└── .gitignore
```

## AppState Critical Path

AppState is the single source of truth for application data. All components communicate through its signals.

```
┌─────────────────────────────────────────────────────────────┐
│                        AppState                              │
├─────────────────────────────────────────────────────────────┤
│ Properties:                                                  │
│   raw_df: pd.DataFrame | None                               │
│   baseline_df: pd.DataFrame | None                          │
│   filtered_df: pd.DataFrame | None                          │
│   column_mapping: ColumnMapping | None                      │
│   filters: list[FilterCriteria]                             │
│   first_trigger_enabled: bool                               │
│   baseline_metrics: TradingMetrics | None                   │
│   filtered_metrics: TradingMetrics | None                   │
├─────────────────────────────────────────────────────────────┤
│ Signals:                                                     │
│   data_loaded(pd.DataFrame)                                 │
│   column_mapping_changed(ColumnMapping)                     │
│   baseline_calculated(TradingMetrics)                       │
│   filters_changed(list[FilterCriteria])                     │
│   filtered_data_updated(pd.DataFrame)                       │
│   metrics_updated(TradingMetrics, TradingMetrics)           │
│   first_trigger_toggled(bool)                               │
│   request_tab_change(int)                                   │
│   state_corrupted(str)                                      │
│   state_recovered()                                         │
└─────────────────────────────────────────────────────────────┘
```

## Signal Flow

```
User loads file
       │
       ▼
┌─────────────┐    data_loaded    ┌─────────────┐
│ DataInputTab│ ───────────────▶  │  AppState   │
└─────────────┘                   └──────┬──────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
           baseline_calculated   column_mapping_changed  filters_changed
                    │                    │                    │
                    ▼                    ▼                    ▼
            ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
            │  PnLStats   │      │   Feature   │      │   Feature   │
            │    Tab      │      │  Explorer   │      │  Explorer   │
            └─────────────┘      └─────────────┘      └─────────────┘
```

---
