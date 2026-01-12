# 2. Requirements

## Functional Requirements

**FR1:** The system shall load Excel (.xlsx, .xls) and CSV files and automatically convert them to Parquet format for optimized performance.

**FR2:** The system shall provide a sheet selector dropdown when loading multi-sheet Excel files.

**FR3:** The system shall display clear, plain English error messages when file loading fails.

**FR4:** The system shall provide a column configuration panel for mapping required columns (Ticker, Date, Time, Gain %) with auto-detection and manual override.

**FR4a:** The system shall require a MAE % (Maximum Adverse Excursion) column for stop loss calculations, with auto-detection support.

**FR5:** The system shall support an optional Win/Loss column for data reference. For metric calculations, win/loss classification shall always be determined by the sign of the efficiency_adjusted_gain (positive = win, zero or negative = loss per breakeven setting), ensuring Avg Winner is always positive and Avg Loser is always negative.

**FR6:** The system shall implement "First Trigger" logic that identifies the first row per ticker-date combination, sorted chronologically by time.

**FR7:** The system shall implement "Filtered First Trigger" logic that finds the first row per ticker-date meeting ALL user-defined filter criteria.

**FR8:** The system shall display baseline statistics (all 25 trading metrics) for the first-trigger dataset immediately upon data load.

**FR9:** The system shall provide bounds-based filtering with BETWEEN and NOT BETWEEN operators for numerical columns.

**FR10:** The system shall support multi-feature AND logic, combining up to 10 filter criteria.

**FR11:** The system shall provide a first-trigger toggle in Feature Explorer to switch between first-trigger filtered and raw data views.

**FR12:** The system shall provide date range selection to filter data by date.

**FR13:** The system shall render interactive charts with pan, zoom, and crosshair functionality using PyQtGraph.

**FR14:** The system shall calculate all 25 trading metrics as defined in the Project Brief Appendix D (Core Statistics, Streak & Loss, Flat Stake, Compounded Kelly, Distribution Visuals).

**FR15:** The system shall accept user inputs for: Stop Loss %, Efficiency % (default 5%), Flat Stake $, Compounded Start Capital $, and Fractional Kelly %.

**FR15a:** The system shall calculate stop-adjusted gain where: if MAE % > Stop Loss %, then stop_adjusted_gain = -Stop Loss %, otherwise stop_adjusted_gain = Gain %.

**FR15b:** The system shall calculate efficiency-adjusted gain as: efficiency_adjusted_gain = stop_adjusted_gain - Efficiency %.

**FR15c:** All 25 trading metrics shall use efficiency_adjusted_gain as the basis for calculations.

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

## Non-Functional Requirements

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
