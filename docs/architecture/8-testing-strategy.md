# 8. Testing Strategy

## Test Pyramid

```
                    ┌─────────┐
                   ╱           ╲
                  ╱   Manual    ╲     5%  - Visual verification
                 ╱   Testing     ╲         - Exploratory testing
                ╱─────────────────╲
               ╱                   ╲
              ╱    Integration      ╲   15%  - Tab workflows
             ╱      Tests           ╲        - File → Metrics flow
            ╱─────────────────────────╲
           ╱                           ╲
          ╱       Widget Tests          ╲  20%  - Component behavior
         ╱         (pytest-qt)           ╲       - Signal emission
        ╱─────────────────────────────────╲
       ╱                                   ╲
      ╱           Unit Tests                ╲  60%  - Core logic
     ╱            (pytest)                   ╲       - Calculations
    ╱─────────────────────────────────────────╲
```

## Fixtures (conftest.py)

```python
# tests/conftest.py
import pytest
import pandas as pd
from pathlib import Path

@pytest.fixture
def sample_trades() -> pd.DataFrame:
    """Standard 1000-row trade dataset."""
    return pd.DataFrame({
        "ticker": ["AAPL"] * 500 + ["GOOGL"] * 500,
        "date": pd.date_range("2024-01-01", periods=1000, freq="h").date,
        "time": pd.date_range("2024-01-01", periods=1000, freq="h").time,
        "gain_pct": np.random.normal(0.5, 3, 1000),
    })

@pytest.fixture
def column_mapping() -> ColumnMapping:
    """Default column mapping."""
    return ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        win_loss_derived=True,
    )

@pytest.fixture
def sample_filters() -> list[FilterCriteria]:
    """Sample filter set."""
    return [
        FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10),
    ]

@pytest.fixture(scope="session")
def large_dataset_path(tmp_path_factory) -> Path:
    """Generate 100k row dataset for performance tests."""
    path = tmp_path_factory.mktemp("data") / "large.parquet"
    df = generate_sample_trades(n_rows=100_000)
    df.to_parquet(path)
    return path
```

## Unit Tests

```python
# tests/unit/test_first_trigger.py
def test_first_trigger_basic(sample_trades, column_mapping):
    """First trigger returns one row per ticker-date."""
    engine = FirstTriggerEngine()
    result = engine.apply(
        sample_trades,
        ticker_col=column_mapping.ticker,
        date_col=column_mapping.date,
        time_col=column_mapping.time,
    )
    # Verify uniqueness
    groups = result.groupby([column_mapping.ticker, column_mapping.date]).size()
    assert (groups == 1).all()

def test_first_trigger_empty_input():
    """Empty DataFrame returns empty DataFrame."""
    engine = FirstTriggerEngine()
    empty = pd.DataFrame(columns=["ticker", "date", "time", "gain_pct"])
    result = engine.apply(empty, "ticker", "date", "time")
    assert len(result) == 0

def test_first_trigger_null_times(sample_trades):
    """Null times are sorted first within groups."""
    sample_trades.loc[0, "time"] = None
    engine = FirstTriggerEngine()
    result = engine.apply(sample_trades, "ticker", "date", "time")
    # Row with null time should be first for its group
    ...
```

```python
# tests/unit/test_filter_engine.py
def test_filter_between(sample_trades):
    """BETWEEN filter includes boundary values."""
    engine = FilterEngine()
    criteria = FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=5)
    result = engine.apply_filters(sample_trades, [criteria])
    assert (result["gain_pct"] >= 0).all()
    assert (result["gain_pct"] <= 5).all()

def test_filter_not_between(sample_trades):
    """NOT BETWEEN filter excludes range."""
    engine = FilterEngine()
    criteria = FilterCriteria(column="gain_pct", operator="not_between", min_val=0, max_val=5)
    result = engine.apply_filters(sample_trades, [criteria])
    assert ((result["gain_pct"] < 0) | (result["gain_pct"] > 5)).all()

def test_filter_invalid_range_raises():
    """Min > max raises FilterValidationError."""
    criteria = FilterCriteria(column="gain_pct", operator="between", min_val=10, max_val=5)
    assert criteria.validate() is not None

def test_date_range_filter(sample_trades):
    """Date range selection filters data by date."""
    engine = FilterEngine()
    filtered = engine.apply_date_range(
        sample_trades,
        date_col="date",
        start="2024-01-15",
        end="2024-01-20",
    )
    assert all(filtered["date"] >= pd.Timestamp("2024-01-15").date())
    assert all(filtered["date"] <= pd.Timestamp("2024-01-20").date())
```

```python
# tests/unit/test_metrics.py
def test_metrics_basic(sample_trades, column_mapping):
    """Basic metrics calculation."""
    calc = MetricsCalculator()
    metrics = calc.calculate(sample_trades, column_mapping.gain_pct)
    assert metrics.num_trades == len(sample_trades)
    assert 0 <= metrics.win_rate <= 100

def test_metrics_empty_df():
    """Empty DataFrame returns empty metrics."""
    calc = MetricsCalculator()
    empty = pd.DataFrame(columns=["gain_pct"])
    metrics = calc.calculate(empty, "gain_pct")
    assert metrics.num_trades == 0
    assert metrics.win_rate is None

def test_metrics_no_winners(sample_trades):
    """All losers handled gracefully."""
    sample_trades["gain_pct"] = -abs(sample_trades["gain_pct"])
    calc = MetricsCalculator()
    metrics = calc.calculate(sample_trades, "gain_pct")
    assert metrics.win_rate == 0
    assert metrics.avg_winner is None
```

```python
# tests/unit/test_export_manager.py
def test_export_csv(sample_trades, tmp_path):
    """Export filtered dataset to CSV."""
    exporter = ExportManager()
    path = tmp_path / "export.csv"
    exporter.to_csv(sample_trades, path)
    assert path.exists()
    reloaded = pd.read_csv(path)
    assert len(reloaded) == len(sample_trades)

def test_export_parquet_with_metadata(sample_trades, tmp_path):
    """Export to Parquet with filter metadata."""
    exporter = ExportManager()
    path = tmp_path / "export.parquet"
    exporter.to_parquet(sample_trades, path, metadata={"filters": "gain_pct: 0-5"})
    assert path.exists()
```

## Widget Tests

```python
# tests/widget/test_metric_card.py
def test_metric_card_display(qtbot):
    """MetricCard displays value correctly."""
    card = MetricCard(label="Win Rate", variant=MetricCard.STANDARD)
    qtbot.addWidget(card)
    card.update_value(67.5, format_spec=".1f")
    assert "67.5" in card._value_label.text()

def test_metric_card_delta_colors(qtbot):
    """Delta indicator uses correct colors."""
    card = MetricCard(label="EV", variant=MetricCard.STANDARD)
    qtbot.addWidget(card)
    card.update_value(3.2, delta=1.5, baseline=1.7)
    # Positive delta should use cyan
    assert Colors.SIGNAL_CYAN in card._delta_label.styleSheet()
```

```python
# tests/widget/test_comparison_ribbon.py
def test_ribbon_displays_four_metrics(qtbot):
    """Ribbon shows Trades, Win Rate, EV, Kelly."""
    ribbon = ComparisonRibbon()
    qtbot.addWidget(ribbon)
    baseline = TradingMetrics(num_trades=12847, win_rate=58.2, ev=1.87, kelly=12.1)
    filtered = TradingMetrics(num_trades=4231, win_rate=67.1, ev=3.21, kelly=15.4)
    ribbon.update(baseline, filtered)
    assert "4,231" in ribbon._trades_card._value_label.text()
    assert "67.1" in ribbon._win_rate_card._value_label.text()

def test_ribbon_empty_state(qtbot):
    """Empty state when no filters applied."""
    ribbon = ComparisonRibbon()
    qtbot.addWidget(ribbon)
    ribbon.clear()
    assert "—" in ribbon._trades_card._value_label.text()
```

## Integration Tests

```python
# tests/integration/test_file_load_workflow.py
def test_full_load_workflow(qtbot, tmp_path):
    """Complete file load → first trigger → baseline flow."""
    # Create test file
    test_file = tmp_path / "trades.csv"
    sample_df = generate_sample_trades(100)
    sample_df.to_csv(test_file, index=False)

    # Create app state
    app_state = AppState()

    # Track signal emissions
    signals = []
    app_state.data_loaded.connect(lambda df: signals.append("data_loaded"))
    app_state.baseline_calculated.connect(lambda m: signals.append("baseline_calculated"))

    # Load file
    loader = FileLoader()
    df = loader.load(test_file)

    # Auto-detect columns
    mapper = ColumnMapper()
    mapping = mapper.auto_detect(df.columns.tolist())
    assert mapping is not None

    # Set data in app state
    app_state.set_data(df, mapping)

    # Verify signals
    assert "data_loaded" in signals
    assert "baseline_calculated" in signals
    assert app_state.baseline_df is not None
    assert app_state.baseline_metrics is not None
```

```python
# tests/integration/test_performance.py
import pytest
from time import perf_counter
import tracemalloc

@pytest.mark.slow
def test_data_load_performance(large_dataset_path):
    """NFR1: Data load < 3 seconds for 100k rows."""
    start = perf_counter()
    loader = FileLoader()
    df = loader.load(large_dataset_path)
    elapsed = perf_counter() - start
    assert elapsed < 3.0, f"Load took {elapsed:.2f}s, exceeds 3s limit"
    assert len(df) >= 100_000

@pytest.mark.slow
def test_filter_response_time(large_dataset_path):
    """NFR2: Filter response < 500ms."""
    loader = FileLoader()
    df = loader.load(large_dataset_path)

    engine = FilterEngine()
    criteria = FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10)

    start = perf_counter()
    result = engine.apply_filters(df, [criteria])
    elapsed = perf_counter() - start
    assert elapsed < 0.5, f"Filter took {elapsed:.3f}s, exceeds 500ms limit"

@pytest.mark.slow
def test_memory_footprint_nfr4(large_dataset_path):
    """NFR4: Memory footprint < 500MB with 100k row dataset."""
    tracemalloc.start()

    # Simulate full application load
    app_state = AppState()
    loader = FileLoader()
    df = loader.load(large_dataset_path)

    mapping = ColumnMapping(
        ticker="ticker", date="date", time="time", gain_pct="gain_pct"
    )
    app_state.set_data(df, mapping)

    # Calculate metrics
    metrics_calc = MetricsCalculator()
    baseline_metrics = metrics_calc.calculate(app_state.baseline_df, "gain_pct")

    # Measure peak memory
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak / (1024 * 1024)
    assert peak_mb < 500, f"Memory peak {peak_mb:.1f}MB exceeds 500MB limit"
```

## Manual Testing Checklist

| Test | Steps | Expected |
|------|-------|----------|
| File Load | Load 100k row Excel file | < 3s, no errors |
| Column Detection | Load file with standard column names | All 4 required columns auto-detected |
| Filter Apply | Add 3 filters, click Apply | Chart updates < 500ms |
| First Trigger Toggle | Toggle switch ON/OFF | Row count changes, chart updates |
| Export CSV | Export filtered data | File saved, openable in Excel |
| Chart Pan/Zoom | Mouse wheel, drag | 60fps, no lag |
| Window Resize | Resize to 1920x1080 | Layout adapts, no clipping |
| Session Restore | Close and reopen | Window position/size restored |

---
