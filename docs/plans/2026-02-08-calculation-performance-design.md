# Calculation Performance Optimization Design

## Problem

When experimenting with filters, all tabs recalculate simultaneously, causing UI lag. This is especially painful during:
1. Rapid filter experimentation - cumulative lag slows workflow
2. Initial data load - slow first calculation

## Solution Overview

Two complementary optimizations:

**Option A: Visible Tab Lazy Updates**
- Only visible tabs recalculate immediately
- Hidden tabs mark as stale, recalculate when user switches to them
- Works across floating windows and multiple monitors

**Option B: Background Threading**
- Heavy calculations run on background threads
- UI stays responsive with subtle loading overlay
- Results update when ready

## Architecture

```
Filter Changed
     │
     ▼
Visibility Check ← Only queue visible tabs
     │
     ▼
Background Worker ← Calculate off main thread
     │
     ▼
UI Update (with overlay during calculation)
```

### Signal Flow Change

**Current:**
```
filtered_data_updated → ALL tabs recalculate immediately (UI freezes)
```

**New:**
```
filtered_data_updated → VisibilityTracker checks each tab
  → Visible tabs: queue calculation on worker thread, show overlay
  → Hidden tabs: mark as stale, do nothing
  → When stale tab becomes visible: queue calculation
```

## Component Details

### 1. Visibility Detection

Detects which tabs are visible across all windows (main + floating docks):

```python
def is_tab_visible(dock_widget: CDockWidget) -> bool:
    # Is the dock widget itself visible?
    if not dock_widget.isVisible():
        return False

    # If in a tab group, is it the active tab?
    area = dock_widget.dockAreaWidget()
    if area and area.currentDockWidget() != dock_widget:
        return False  # Hidden behind another tab

    # Is the containing window visible (not minimized)?
    container = dock_widget.dockContainer()
    if container and container.isFloating():
        if container.isMinimized():
            return False

    return True
```

Visibility is checked:
- When `filtered_data_updated` fires
- When user switches tabs in a tab group
- When user restores a minimized floating window

### 2. Background Threading

Uses QThreadPool with a worker pattern:

```python
class CalculationWorker(QRunnable):
    """Runs a calculation function on a background thread."""

    class Signals(QObject):
        finished = pyqtSignal(object)
        error = pyqtSignal(str)

    def __init__(self, calc_fn, data):
        self.calc_fn = calc_fn
        self.data = data
        self.signals = Signals()

    def run(self):
        try:
            result = self.calc_fn(self.data)
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))
```

Tab integration:
```python
def _on_filtered_data_updated(self, df):
    if not visibility_tracker.is_visible(self):
        self._mark_stale()
        return

    self._show_loading_overlay()

    worker = CalculationWorker(self._calculate_metrics, df.copy())
    worker.signals.finished.connect(self._on_calculation_complete)
    QThreadPool.globalInstance().start(worker)

def _on_calculation_complete(self, result):
    self._hide_loading_overlay()
    self._update_display(result)
```

Data is copied (`df.copy()`) to avoid race conditions.

### 3. Loading Overlay

Semi-transparent overlay that dims content with centered spinner:

```python
class LoadingOverlay(QWidget):
    """Semi-transparent overlay with spinner."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: rgba(0, 0, 0, 0.3);")

        self._spinner = QLabel("...", self)  # Or animated spinner
        self._spinner.setAlignment(Qt.AlignCenter)

        self.hide()

    def showEvent(self, event):
        self.setGeometry(self.parent().rect())
```

Previous content remains visible underneath, giving context.

### 4. Initial Load Optimization

**Pre-compute columns on load:**
```python
# In file_loader.py, after loading DataFrame:
df['_time_minutes'] = parse_time_to_minutes(df['time'])
df['_is_first_trigger'] = compute_first_triggers(df)
```

**Parallel initial calculations:**
```python
workers = [
    CalculationWorker(compute_baseline_metrics, baseline_df),
    CalculationWorker(compute_statistics_tables, baseline_df),
    CalculationWorker(compute_breakdown_data, baseline_df),
]
for w in workers:
    QThreadPool.globalInstance().start(w)
```

**Progressive UI:** Show Feature Explorer immediately while other tabs show loading overlays.

## File Structure

**New Files:**
```
src/core/
├── visibility_tracker.py   # Tab visibility detection
├── calculation_worker.py   # Background thread worker
└── stale_manager.py        # Tracks which tabs need recalc

src/ui/
└── loading_overlay.py      # Overlay widget
```

**Modified Files:**
- `src/core/app_state.py` - Visibility tracker integration
- `src/core/file_loader.py` - Pre-compute columns on load
- `src/tabs/*.py` - Each tab uses visibility check, worker, overlay

## Implementation Phases

### Phase 1: Infrastructure
- Create CalculationWorker class
- Create LoadingOverlay widget
- Create VisibilityTracker class
- Create StaleManager class

### Phase 2: Heaviest Tabs First
- Update Statistics tab (biggest bottleneck)
- Update PnL Stats tab
- Update Breakdown tab

### Phase 3: Remaining Tabs
- Update Data Binning tab
- Update Feature Insights tab
- Update other visualization tabs

### Phase 4: Initial Load
- Pre-compute time_minutes and first_trigger columns
- Parallelize startup calculations
- Implement progressive UI loading

## Testing Strategy

- Unit tests for visibility detection logic
- Unit tests for CalculationWorker
- Integration test: filter change triggers only visible tab calculation
- Manual testing with large dataset (500K+ rows) to verify UI responsiveness
