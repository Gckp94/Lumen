# 6. Epic 1: Foundation & Data Pipeline

## Epic Goal

Establish the complete project infrastructure and prove the core data pipeline end-to-end. Upon completion, users can load a trading data file, configure column mappings, see it automatically converted to Parquet for performance, and view baseline first-trigger statistics with 7 key metrics.

## Stories

### Story 1.1: Project Scaffolding

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

### Story 1.2: Themed Application Shell

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

### Story 1.3: File Selection & Data Loading

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

### Story 1.4: Column Configuration Panel

**As a** user,
**I want** to verify and adjust column mappings,
**so that** the analysis uses the correct data even if auto-detection fails.

**Acceptance Criteria:**

1. Auto-detection for required columns (Ticker, Date, Time, Gain %, MAE %) with case-insensitive pattern matching
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

### Story 1.5: First Trigger Baseline

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

### Story 1.6: Core Metrics Calculation & Display

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
8. User inputs panel with Stop Loss % (default 8%) and Efficiency % (default 5%)
9. Calculate stop_adjusted_gain_pct: if mae_pct > stop_loss then -stop_loss, else gain_pct
10. Calculate efficiency_adjusted_gain_pct = stop_adjusted_gain_pct - efficiency
11. All metrics calculated using efficiency_adjusted_gain_pct
12. User input changes trigger metric recalculation with 300ms debounce

---

### Story 1.7: Parquet Caching

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

## Epic 1 Definition of Done

- [ ] Application launches with professional Observatory dark theme
- [ ] 4-tab structure visible with Monte Carlo placeholder
- [ ] User can select Excel/CSV file and choose sheet
- [ ] Column mappings auto-detected or manually configured (including MAE %)
- [ ] Win/Loss column supported (explicit or derived)
- [ ] First trigger baseline calculated using mapped columns
- [ ] User inputs panel for Stop Loss % and Efficiency % with defaults
- [ ] Trade adjustments calculated (stop loss + efficiency)
- [ ] 7 core metrics displayed in styled cards using adjusted gains
- [ ] Metrics recalculate when user inputs change
- [ ] Subsequent file loads use Parquet cache
- [ ] Column mappings persisted for repeat file loads

---
