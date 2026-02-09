# Portfolio Multiple Entry Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add multiple entry control per strategy to filter duplicate ticker-date pairs based on priority order.

**Architecture:** Add `allow_multiple_entry` field to StrategyConfig, add "Multi" checkbox column to StrategyTableWidget with drag-drop reordering, filter duplicates in PortfolioCalculator before processing trades.

**Tech Stack:** Python, PyQt6, pandas, dataclasses

---

### Task 1: Add allow_multiple_entry Field to StrategyConfig

**Files:**
- Modify: `src/core/portfolio_models.py:25-38`
- Test: `tests/unit/test_portfolio_models.py`

**Step 1: Write the failing test**

Add to `tests/unit/test_portfolio_models.py`:

```python
class TestStrategyConfigMultipleEntry:
    """Tests for allow_multiple_entry field."""

    def test_allow_multiple_entry_defaults_to_true(self) -> None:
        """Default is True (allow multiple entries)."""
        config = StrategyConfig(
            name="Test",
            file_path="/path/to/file.xlsx",
            column_mapping=PortfolioColumnMapping(
                ticker_col="ticker",
                date_col="date",
                gain_pct_col="gain_pct",
            ),
        )
        assert config.allow_multiple_entry is True

    def test_allow_multiple_entry_can_be_set_false(self) -> None:
        """Can explicitly set to False."""
        config = StrategyConfig(
            name="Test",
            file_path="/path/to/file.xlsx",
            column_mapping=PortfolioColumnMapping(
                ticker_col="ticker",
                date_col="date",
                gain_pct_col="gain_pct",
            ),
            allow_multiple_entry=False,
        )
        assert config.allow_multiple_entry is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_portfolio_models.py::TestStrategyConfigMultipleEntry -v`
Expected: FAIL with "unexpected keyword argument 'allow_multiple_entry'"

**Step 3: Write minimal implementation**

In `src/core/portfolio_models.py`, add field to StrategyConfig dataclass:

```python
@dataclass
class StrategyConfig:
    """Configuration for a single strategy."""
    name: str
    file_path: str
    column_mapping: PortfolioColumnMapping
    sheet_name: str | None = None
    stop_pct: float = 2.0
    efficiency: float = 5.0
    size_type: PositionSizeType = PositionSizeType.CUSTOM_PCT
    size_value: float = 10.0
    max_compound: float | None = 50000.0
    is_baseline: bool = False
    is_candidate: bool = False
    allow_multiple_entry: bool = True  # NEW: Default allows multiple entries
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_portfolio_models.py::TestStrategyConfigMultipleEntry -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/portfolio_models.py tests/unit/test_portfolio_models.py
git commit -m "feat(portfolio): add allow_multiple_entry field to StrategyConfig

Default True allows taking duplicate ticker-date trades across strategies.
When False, strategy defers to higher-priority strategies.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 2: Add Multi Checkbox Column to StrategyTableWidget

**Files:**
- Modify: `src/ui/components/strategy_table.py:31-55`
- Test: `tests/unit/test_strategy_table.py`

**Step 1: Write the failing test**

Add to `tests/unit/test_strategy_table.py`:

```python
class TestStrategyTableMultipleEntry:
    """Tests for Multiple Entry checkbox column."""

    def test_multi_column_exists(self, qtbot: QtBot) -> None:
        """Table has Multi column after CND."""
        table = StrategyTableWidget()
        qtbot.addWidget(table)
        headers = [
            table.horizontalHeaderItem(i).text()
            for i in range(table.columnCount())
        ]
        assert "Multi" in headers
        # Should be after CND (index 3), so at index 4
        assert headers.index("Multi") == 4

    def test_multi_checkbox_defaults_checked(self, qtbot: QtBot) -> None:
        """Multi checkbox defaults to checked (allow multiple entry)."""
        table = StrategyTableWidget()
        qtbot.addWidget(table)
        config = StrategyConfig(
            name="Test",
            file_path="/path/to/file.xlsx",
            column_mapping=PortfolioColumnMapping(
                ticker_col="ticker",
                date_col="date",
                gain_pct_col="gain_pct",
            ),
        )
        table.add_strategy(config)
        # Get checkbox from Multi column (index 4)
        checkbox = table.cellWidget(0, 4).findChild(QCheckBox)
        assert checkbox.isChecked() is True

    def test_multi_checkbox_updates_config(self, qtbot: QtBot) -> None:
        """Unchecking Multi updates strategy config."""
        table = StrategyTableWidget()
        qtbot.addWidget(table)
        config = StrategyConfig(
            name="Test",
            file_path="/path/to/file.xlsx",
            column_mapping=PortfolioColumnMapping(
                ticker_col="ticker",
                date_col="date",
                gain_pct_col="gain_pct",
            ),
        )
        table.add_strategy(config)
        checkbox = table.cellWidget(0, 4).findChild(QCheckBox)
        checkbox.setChecked(False)
        strategies = table.get_strategies()
        assert strategies[0].allow_multiple_entry is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_strategy_table.py::TestStrategyTableMultipleEntry -v`
Expected: FAIL with assertion errors about missing column

**Step 3: Write minimal implementation**

In `src/ui/components/strategy_table.py`:

1. Update COLUMNS list (insert after CND):
```python
COLUMNS = [
    ("Name", 120),
    ("File", 30),
    ("BL", 53),
    ("CND", 60),
    ("Multi", 60),  # NEW
    ("Stop%", 170),
    ("Efficiency", 180),
    ("Size Type", 200),
    ("Size Value", 150),
    ("Max Compound", 173),
    ("Menu", 80),
]
```

2. Update column indices:
```python
COL_NAME = 0
COL_FILE = 1
COL_BL = 2
COL_CND = 3
COL_MULTI = 4  # NEW
COL_STOP = 5   # Was 4
COL_EFFICIENCY = 6  # Was 5
COL_SIZE_TYPE = 7   # Was 6
COL_SIZE_VALUE = 8  # Was 7
COL_MAX_COMPOUND = 9  # Was 8
COL_MENU = 10  # Was 9
```

3. In `_populate_row`, add Multi checkbox after CND:
```python
# Multi checkbox
multi_cb = self._create_centered_checkbox(config.allow_multiple_entry)
multi_cb.findChild(QCheckBox).stateChanged.connect(
    lambda state, r=row: self._on_multi_changed(r, state)
)
self.setCellWidget(row, self.COL_MULTI, multi_cb)
```

4. Add handler method:
```python
def _on_multi_changed(self, row: int, state: int) -> None:
    """Handle multi entry checkbox change."""
    if 0 <= row < len(self._strategies):
        self._strategies[row].allow_multiple_entry = state == Qt.CheckState.Checked.value
        self.strategy_changed.emit()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_strategy_table.py::TestStrategyTableMultipleEntry -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/ui/components/strategy_table.py tests/unit/test_strategy_table.py
git commit -m "feat(ui): add Multi checkbox column to strategy table

- New column after CND for multiple entry control
- Defaults to checked (allow multiple entries)
- Updates StrategyConfig.allow_multiple_entry on change

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 3: Enable Drag-and-Drop Row Reordering

**Files:**
- Modify: `src/ui/components/strategy_table.py`
- Test: `tests/unit/test_strategy_table.py`

**Step 1: Write the failing test**

Add to `tests/unit/test_strategy_table.py`:

```python
class TestStrategyTableDragDrop:
    """Tests for drag-drop row reordering."""

    def test_drag_drop_enabled(self, qtbot: QtBot) -> None:
        """Table supports internal drag-drop."""
        table = StrategyTableWidget()
        qtbot.addWidget(table)
        assert table.dragDropMode() == QAbstractItemView.DragDropMode.InternalMove
        assert table.dragEnabled() is True

    def test_reorder_strategies_updates_list(self, qtbot: QtBot) -> None:
        """Reordering rows updates internal strategies list."""
        table = StrategyTableWidget()
        qtbot.addWidget(table)
        config1 = StrategyConfig(
            name="Alpha",
            file_path="/path/to/alpha.xlsx",
            column_mapping=PortfolioColumnMapping(
                ticker_col="ticker", date_col="date", gain_pct_col="gain_pct"
            ),
        )
        config2 = StrategyConfig(
            name="Beta",
            file_path="/path/to/beta.xlsx",
            column_mapping=PortfolioColumnMapping(
                ticker_col="ticker", date_col="date", gain_pct_col="gain_pct"
            ),
        )
        table.add_strategy(config1)
        table.add_strategy(config2)
        # Simulate reorder: move Beta to top
        table.move_strategy(1, 0)
        strategies = table.get_strategies()
        assert strategies[0].name == "Beta"
        assert strategies[1].name == "Alpha"

    def test_reorder_emits_strategy_changed(self, qtbot: QtBot) -> None:
        """Reordering emits strategy_changed signal."""
        table = StrategyTableWidget()
        qtbot.addWidget(table)
        config1 = StrategyConfig(
            name="Alpha",
            file_path="/path/to/alpha.xlsx",
            column_mapping=PortfolioColumnMapping(
                ticker_col="ticker", date_col="date", gain_pct_col="gain_pct"
            ),
        )
        config2 = StrategyConfig(
            name="Beta",
            file_path="/path/to/beta.xlsx",
            column_mapping=PortfolioColumnMapping(
                ticker_col="ticker", date_col="date", gain_pct_col="gain_pct"
            ),
        )
        table.add_strategy(config1)
        table.add_strategy(config2)
        with qtbot.waitSignal(table.strategy_changed, timeout=1000):
            table.move_strategy(1, 0)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_strategy_table.py::TestStrategyTableDragDrop -v`
Expected: FAIL with "no attribute 'move_strategy'" or drag mode assertion

**Step 3: Write minimal implementation**

In `src/ui/components/strategy_table.py`:

1. In `__init__`, enable drag-drop:
```python
self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
self.setDragEnabled(True)
self.setAcceptDrops(True)
self.setDropIndicatorShown(True)
self.setDefaultDropAction(Qt.DropAction.MoveAction)
```

2. Add move_strategy method:
```python
def move_strategy(self, from_row: int, to_row: int) -> None:
    """Move a strategy from one position to another.

    Args:
        from_row: Source row index.
        to_row: Destination row index.
    """
    if from_row == to_row:
        return
    if not (0 <= from_row < len(self._strategies)):
        return
    if not (0 <= to_row <= len(self._strategies)):
        return

    # Move in internal list
    strategy = self._strategies.pop(from_row)
    self._strategies.insert(to_row, strategy)

    # Rebuild table rows
    self._rebuild_table()
    self.strategy_changed.emit()

def _rebuild_table(self) -> None:
    """Rebuild all table rows from strategies list."""
    self.setRowCount(0)
    for config in self._strategies:
        row = self.rowCount()
        self.insertRow(row)
        self._populate_row(row, config)
```

3. Override dropEvent to handle drag-drop:
```python
def dropEvent(self, event: QDropEvent) -> None:
    """Handle drop event to reorder strategies."""
    if event.source() != self:
        event.ignore()
        return

    # Get source row
    source_row = self.currentRow()
    if source_row < 0:
        event.ignore()
        return

    # Get target row from drop position
    target_row = self.rowAt(event.position().toPoint().y())
    if target_row < 0:
        target_row = self.rowCount() - 1

    if source_row != target_row:
        self.move_strategy(source_row, target_row)

    event.accept()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_strategy_table.py::TestStrategyTableDragDrop -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/ui/components/strategy_table.py tests/unit/test_strategy_table.py
git commit -m "feat(ui): enable drag-drop reordering for strategy table

- Strategies can be reordered via drag-drop
- Order determines priority (top = highest)
- Emits strategy_changed on reorder

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 4: Add Duplicate Filtering to PortfolioCalculator

**Files:**
- Modify: `src/core/portfolio_calculator.py`
- Test: `tests/unit/test_portfolio_calculator.py`

**Step 1: Write the failing test**

Add to `tests/unit/test_portfolio_calculator.py`:

```python
class TestPortfolioCalculatorMultipleEntry:
    """Tests for multiple entry filtering."""

    def test_filter_duplicates_when_multi_entry_disabled(self) -> None:
        """Duplicate ticker-date skipped when allow_multiple_entry=False."""
        calc = PortfolioCalculator(starting_capital=10000.0)

        # Two strategies with same ticker-date
        mapping = PortfolioColumnMapping(
            ticker_col="ticker", date_col="date", gain_pct_col="gain_pct"
        )
        config1 = StrategyConfig(
            name="Alpha",
            file_path="/path/alpha.xlsx",
            column_mapping=mapping,
            allow_multiple_entry=True,  # Takes trade
        )
        config2 = StrategyConfig(
            name="Beta",
            file_path="/path/beta.xlsx",
            column_mapping=mapping,
            allow_multiple_entry=False,  # Defers to Alpha
        )

        df1 = pd.DataFrame({
            "ticker": ["AAPL"],
            "date": ["2024-01-15"],
            "gain_pct": [0.05],
        })
        df2 = pd.DataFrame({
            "ticker": ["AAPL"],
            "date": ["2024-01-15"],
            "gain_pct": [0.03],
        })

        result = calc.calculate_portfolio([(df1, config1), (df2, config2)])

        # Only Alpha's trade should be taken
        assert len(result) == 1
        assert result.iloc[0]["strategy"] == "Alpha"

    def test_allow_duplicates_when_multi_entry_enabled(self) -> None:
        """Both trades taken when allow_multiple_entry=True for both."""
        calc = PortfolioCalculator(starting_capital=10000.0)

        mapping = PortfolioColumnMapping(
            ticker_col="ticker", date_col="date", gain_pct_col="gain_pct"
        )
        config1 = StrategyConfig(
            name="Alpha",
            file_path="/path/alpha.xlsx",
            column_mapping=mapping,
            allow_multiple_entry=True,
        )
        config2 = StrategyConfig(
            name="Beta",
            file_path="/path/beta.xlsx",
            column_mapping=mapping,
            allow_multiple_entry=True,
        )

        df1 = pd.DataFrame({
            "ticker": ["AAPL"],
            "date": ["2024-01-15"],
            "gain_pct": [0.05],
        })
        df2 = pd.DataFrame({
            "ticker": ["AAPL"],
            "date": ["2024-01-15"],
            "gain_pct": [0.03],
        })

        result = calc.calculate_portfolio([(df1, config1), (df2, config2)])

        # Both trades taken
        assert len(result) == 2

    def test_no_ticker_skips_deduplication(self) -> None:
        """When ticker is None, deduplication is skipped."""
        calc = PortfolioCalculator(starting_capital=10000.0)

        # No ticker column mapped
        mapping = PortfolioColumnMapping(
            ticker_col=None, date_col="date", gain_pct_col="gain_pct"
        )
        config1 = StrategyConfig(
            name="Alpha",
            file_path="/path/alpha.xlsx",
            column_mapping=mapping,
            allow_multiple_entry=False,
        )
        config2 = StrategyConfig(
            name="Beta",
            file_path="/path/beta.xlsx",
            column_mapping=mapping,
            allow_multiple_entry=False,
        )

        df1 = pd.DataFrame({
            "date": ["2024-01-15"],
            "gain_pct": [0.05],
        })
        df2 = pd.DataFrame({
            "date": ["2024-01-15"],
            "gain_pct": [0.03],
        })

        result = calc.calculate_portfolio([(df1, config1), (df2, config2)])

        # Both trades taken (no ticker = no deduplication)
        assert len(result) == 2

    def test_priority_order_determines_which_trade_kept(self) -> None:
        """First strategy in list has priority."""
        calc = PortfolioCalculator(starting_capital=10000.0)

        mapping = PortfolioColumnMapping(
            ticker_col="ticker", date_col="date", gain_pct_col="gain_pct"
        )
        # Beta first = higher priority
        config_beta = StrategyConfig(
            name="Beta",
            file_path="/path/beta.xlsx",
            column_mapping=mapping,
            allow_multiple_entry=True,
        )
        config_alpha = StrategyConfig(
            name="Alpha",
            file_path="/path/alpha.xlsx",
            column_mapping=mapping,
            allow_multiple_entry=False,  # Defers to Beta
        )

        df_beta = pd.DataFrame({
            "ticker": ["AAPL"],
            "date": ["2024-01-15"],
            "gain_pct": [0.03],
        })
        df_alpha = pd.DataFrame({
            "ticker": ["AAPL"],
            "date": ["2024-01-15"],
            "gain_pct": [0.05],
        })

        result = calc.calculate_portfolio([
            (df_beta, config_beta),
            (df_alpha, config_alpha),
        ])

        # Only Beta's trade (first in list = higher priority)
        assert len(result) == 1
        assert result.iloc[0]["strategy"] == "Beta"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_portfolio_calculator.py::TestPortfolioCalculatorMultipleEntry -v`
Expected: FAIL (both trades taken, no filtering)

**Step 3: Write minimal implementation**

In `src/core/portfolio_calculator.py`:

1. Add helper method:
```python
def _filter_duplicate_entries(
    self,
    merged: pd.DataFrame,
    strategies: list[tuple[pd.DataFrame, StrategyConfig]],
) -> pd.DataFrame:
    """Filter duplicate ticker-date pairs based on multi-entry settings.

    Args:
        merged: DataFrame with all trades, sorted by date.
        strategies: List in priority order (first = highest priority).

    Returns:
        Filtered DataFrame with duplicates removed per settings.
    """
    if merged.empty:
        return merged

    seen_ticker_dates: set[tuple] = set()
    keep_mask = []

    for _, row in merged.iterrows():
        ticker = row["_ticker"]
        config: StrategyConfig = row["_config"]

        # Skip deduplication if no ticker mapped
        if ticker is None:
            keep_mask.append(True)
            continue

        ticker_date = (ticker, row["_date_only"])

        if ticker_date in seen_ticker_dates and not config.allow_multiple_entry:
            keep_mask.append(False)  # Skip: duplicate and multi-entry disabled
        else:
            keep_mask.append(True)
            seen_ticker_dates.add(ticker_date)

    return merged[keep_mask].reset_index(drop=True)
```

2. In `calculate_portfolio`, call the filter after sorting:
```python
merged = pd.concat(all_trades, ignore_index=True)
merged = merged.sort_values("_date").reset_index(drop=True)
merged["_date_only"] = merged["_date"].dt.date

# Filter duplicates based on multi-entry settings
merged = self._filter_duplicate_entries(merged, strategies)

if merged.empty:
    return pd.DataFrame(...)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_portfolio_calculator.py::TestPortfolioCalculatorMultipleEntry -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/portfolio_calculator.py tests/unit/test_portfolio_calculator.py
git commit -m "feat(portfolio): filter duplicate ticker-date pairs by priority

- Strategies with allow_multiple_entry=False skip duplicates
- Priority order = list order (first = highest)
- No ticker mapped = skip deduplication for that strategy

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 5: Add Backwards Compatibility for Config Loading

**Files:**
- Modify: `src/core/portfolio_config_manager.py`
- Test: `tests/unit/test_portfolio_config_manager.py`

**Step 1: Write the failing test**

Add to `tests/unit/test_portfolio_config_manager.py`:

```python
class TestPortfolioConfigManagerMultipleEntry:
    """Tests for allow_multiple_entry field persistence."""

    def test_saves_allow_multiple_entry(self, tmp_path: Path) -> None:
        """Saves allow_multiple_entry field."""
        config_path = tmp_path / "portfolio.json"
        manager = PortfolioConfigManager(config_path)

        config = StrategyConfig(
            name="Test",
            file_path="/path/to/file.xlsx",
            column_mapping=PortfolioColumnMapping(
                ticker_col="ticker", date_col="date", gain_pct_col="gain_pct"
            ),
            allow_multiple_entry=False,
        )
        manager.save([config])

        loaded = manager.load()
        assert loaded[0].allow_multiple_entry is False

    def test_loads_default_when_field_missing(self, tmp_path: Path) -> None:
        """Old configs without field default to True."""
        config_path = tmp_path / "portfolio.json"
        # Write old-format config without allow_multiple_entry
        old_config = {
            "strategies": [{
                "name": "Test",
                "file_path": "/path/to/file.xlsx",
                "column_mapping": {
                    "ticker_col": "ticker",
                    "date_col": "date",
                    "gain_pct_col": "gain_pct",
                },
                "stop_pct": 2.0,
                "efficiency": 5.0,
                "size_type": "CUSTOM_PCT",
                "size_value": 10.0,
                "max_compound": 50000.0,
                "is_baseline": False,
                "is_candidate": False,
                # NOTE: no allow_multiple_entry field
            }]
        }
        import json
        config_path.write_text(json.dumps(old_config))

        manager = PortfolioConfigManager(config_path)
        loaded = manager.load()

        # Should default to True
        assert loaded[0].allow_multiple_entry is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_portfolio_config_manager.py::TestPortfolioConfigManagerMultipleEntry -v`
Expected: FAIL or PASS (may already work if using dataclass defaults)

**Step 3: Write minimal implementation (if needed)**

In `src/core/portfolio_config_manager.py`, ensure the deserialization handles missing field:

```python
def _dict_to_strategy_config(self, data: dict) -> StrategyConfig:
    """Convert dict to StrategyConfig with backwards compatibility."""
    return StrategyConfig(
        name=data["name"],
        file_path=data["file_path"],
        column_mapping=PortfolioColumnMapping(**data["column_mapping"]),
        sheet_name=data.get("sheet_name"),
        stop_pct=data.get("stop_pct", 2.0),
        efficiency=data.get("efficiency", 5.0),
        size_type=PositionSizeType[data.get("size_type", "CUSTOM_PCT")],
        size_value=data.get("size_value", 10.0),
        max_compound=data.get("max_compound", 50000.0),
        is_baseline=data.get("is_baseline", False),
        is_candidate=data.get("is_candidate", False),
        allow_multiple_entry=data.get("allow_multiple_entry", True),  # NEW
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_portfolio_config_manager.py::TestPortfolioConfigManagerMultipleEntry -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/portfolio_config_manager.py tests/unit/test_portfolio_config_manager.py
git commit -m "feat(config): persist allow_multiple_entry with backwards compat

- Saves and loads allow_multiple_entry field
- Old configs without field default to True

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 6: Run Full Test Suite and Verify

**Files:**
- None (verification only)

**Step 1: Run all portfolio-related tests**

Run: `pytest tests/unit/test_strategy_table.py tests/unit/test_portfolio*.py -v`
Expected: All tests pass

**Step 2: Run the application manually**

Run: `python -m src.main`
Expected:
- Strategy table shows "Multi" column after CND
- Checkbox defaults to checked
- Can drag rows to reorder
- Portfolio recalculates when Multi checkbox or order changes

**Step 3: Final commit (if any fixes needed)**

Only if manual testing reveals issues.

---

### Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Add allow_multiple_entry to StrategyConfig | portfolio_models.py |
| 2 | Add Multi checkbox column | strategy_table.py |
| 3 | Enable drag-drop reordering | strategy_table.py |
| 4 | Filter duplicates in calculator | portfolio_calculator.py |
| 5 | Config persistence backwards compat | portfolio_config_manager.py |
| 6 | Full test suite verification | - |
