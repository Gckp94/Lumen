# 10. Error Handling & Resilience

## Philosophy

| Principle | Implementation |
|-----------|----------------|
| Fail gracefully | Show user-friendly message, never crash |
| Preserve data | Never lose user's loaded data on error |
| Enable recovery | Provide clear path forward after error |
| Log for debugging | Capture details for troubleshooting |

## Exception Layers

```
┌─────────────────────────────────────────────────────────────┐
│  UI Layer (Tabs, Widgets)                                   │
│  • Catch LumenError → Show toast/dialog                     │
│  • Catch Exception → Log + generic error message            │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│  Core Layer (Engines, Calculators)                          │
│  • Validate inputs → Raise specific LumenError              │
│  • Catch pandas/numpy errors → Wrap in LumenError           │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│  I/O Layer (File, Cache, Export)                            │
│  • Catch OSError → Wrap in FileLoadError/ExportError        │
│  • Catch format errors → Wrap with context                  │
└─────────────────────────────────────────────────────────────┘
```

## Error Messages

| Error Case | User Message |
|------------|--------------|
| File not found | "File not found: {filename}" |
| Permission denied | "Cannot access file. Check permissions." |
| Corrupt file | "Unable to read file. The file may be corrupted." |
| Column missing | "Required column not mapped: {column}" |
| Invalid range | "Min value must be less than max value." |
| No matches | "No rows match your filter criteria." |
| Export failed | "Cannot write to selected location." |

## Graceful Degradation

```python
class MetricsCalculator:
    def calculate(self, df: pd.DataFrame) -> TradingMetrics:
        if len(df) == 0:
            logger.warning("Empty DataFrame, returning default metrics")
            return TradingMetrics.empty()

        winners = df[df["gain_pct"] > 0]
        losers = df[df["gain_pct"] < 0]

        if len(winners) == 0:
            logger.warning("No winners in dataset")
            avg_winner = None
            rr_ratio = None
        else:
            avg_winner = winners["gain_pct"].mean()
            rr_ratio = self._calculate_rr(winners, losers)

        return TradingMetrics(
            num_trades=len(df),
            avg_winner=avg_winner,
            rr_ratio=rr_ratio,
            # ...
        )
```

## State Recovery

```python
class AppState(QObject):
    def apply_filter(self, criteria: FilterCriteria) -> None:
        if not self._validate_state():
            self.state_corrupted.emit("State invalid. Please reload data.")
            return

        self._take_snapshot()

        try:
            self._do_apply_filter(criteria)
        except Exception as e:
            logger.error("Filter failed: %s", e)
            self._rollback()
            raise

    def _take_snapshot(self) -> None:
        self._snapshot = StateSnapshot(
            filters=deepcopy(self.filters),
            filtered_df=self.filtered_df.copy() if self.filtered_df is not None else None,
            first_trigger_enabled=self.first_trigger_enabled,
        )

    def _rollback(self) -> None:
        if self._snapshot:
            self.filters = self._snapshot.filters
            self.filtered_df = self._snapshot.filtered_df
            self.state_recovered.emit()
```

## Tab Navigation Guards

```python
class FeatureExplorerTab(QWidget):
    requires_data = True

    def show_empty_state(self) -> None:
        self._content_stack.setCurrentWidget(self._empty_state)
        self._empty_state.set_message(
            icon="📁",
            title="No Data Loaded",
            description="Load a trading data file in the Data Input tab.",
            action_text="Go to Data Input",
            action_callback=lambda: self._app_state.request_tab_change.emit(0),
        )
```

## Global Exception Handler

```python
# src/main.py
import sys
from PyQt6.QtWidgets import QApplication, QMessageBox

def exception_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    QMessageBox.critical(
        None,
        "Unexpected Error",
        "An unexpected error occurred. Please save your work and restart.",
    )

def main():
    sys.excepthook = exception_handler
    app = QApplication(sys.argv)
    # ...
```

## Font Loading with Fallback

```python
# src/ui/theme.py
class FontLoader:
    FALLBACKS = {
        "Azeret Mono": ["SF Mono", "Consolas", "Courier New"],
        "Geist": ["SF Pro Text", "Segoe UI", "Arial"],
    }

    def load_fonts(self) -> tuple[bool, list[str]]:
        """Load fonts, return (success, warnings)."""
        warnings = []

        for family, weights in self.REQUIRED_FONTS.items():
            if family not in self._loaded_fonts:
                fallback = self._find_fallback(family)
                if fallback:
                    self._using_fallbacks[family] = fallback
                    warnings.append(f"Using {fallback} instead of {family}")

        return len(self._using_fallbacks) == 0, warnings
```

---
