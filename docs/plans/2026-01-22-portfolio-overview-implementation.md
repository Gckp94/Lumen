# Portfolio Overview Tab Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a tab that analyzes multiple trading strategies together, comparing baseline portfolio vs adding candidate strategies.

**Architecture:** Core calculator processes multiple strategy CSVs with daily compounding. Strategy table manages configurations. Dual charts (equity + drawdown) with shared legend for visibility toggles. Import dialog handles column mapping.

**Tech Stack:** PyQt6, pyqtgraph, pandas, dataclasses for models

---

## Task 1: Strategy Data Model

**Files:**
- Create: `src/core/portfolio_models.py`
- Test: `tests/unit/test_portfolio_models.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_portfolio_models.py
import pytest
from src.core.portfolio_models import (
    PositionSizeType,
    StrategyConfig,
    ColumnMapping,
)


class TestStrategyConfig:
    def test_create_strategy_config_with_defaults(self):
        config = StrategyConfig(
            name="Test Strategy",
            file_path="/path/to/file.csv",
            column_mapping=ColumnMapping(
                date_col="date",
                gain_pct_col="gain_pct",
                win_loss_col="wl",
            ),
        )
        assert config.name == "Test Strategy"
        assert config.stop_pct == 2.0  # default
        assert config.efficiency == 1.0  # default
        assert config.size_type == PositionSizeType.CUSTOM_PCT
        assert config.size_value == 10.0  # default 10%
        assert config.max_compound is None
        assert config.is_baseline is False
        assert config.is_candidate is False

    def test_position_size_type_enum(self):
        assert PositionSizeType.FRAC_KELLY.value == "frac_kelly"
        assert PositionSizeType.CUSTOM_PCT.value == "custom_pct"
        assert PositionSizeType.FLAT_DOLLAR.value == "flat_dollar"

    def test_column_mapping_validation(self):
        mapping = ColumnMapping(
            date_col="trade_date",
            gain_pct_col="return_pct",
            win_loss_col="outcome",
        )
        assert mapping.date_col == "trade_date"
        assert mapping.gain_pct_col == "return_pct"
        assert mapping.win_loss_col == "outcome"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_portfolio_models.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.core.portfolio_models'"

**Step 3: Write minimal implementation**

```python
# src/core/portfolio_models.py
"""Data models for Portfolio Overview feature."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PositionSizeType(Enum):
    """Position sizing method."""
    FRAC_KELLY = "frac_kelly"
    CUSTOM_PCT = "custom_pct"
    FLAT_DOLLAR = "flat_dollar"


@dataclass
class ColumnMapping:
    """Maps CSV columns to required fields."""
    date_col: str
    gain_pct_col: str
    win_loss_col: str


@dataclass
class StrategyConfig:
    """Configuration for a single strategy."""
    name: str
    file_path: str
    column_mapping: ColumnMapping
    stop_pct: float = 2.0
    efficiency: float = 1.0
    size_type: PositionSizeType = PositionSizeType.CUSTOM_PCT
    size_value: float = 10.0  # 10% default
    max_compound: Optional[float] = None
    is_baseline: bool = False
    is_candidate: bool = False
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_portfolio_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/portfolio_models.py tests/unit/test_portfolio_models.py
git commit -m "feat(portfolio): add strategy data models"
```

---

## Task 2: Portfolio Calculator - Single Strategy Equity

**Files:**
- Create: `src/core/portfolio_calculator.py`
- Test: `tests/unit/test_portfolio_calculator.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_portfolio_calculator.py
import pytest
import pandas as pd
import numpy as np
from src.core.portfolio_calculator import PortfolioCalculator
from src.core.portfolio_models import (
    StrategyConfig,
    ColumnMapping,
    PositionSizeType,
)


class TestPortfolioCalculatorSingleStrategy:
    @pytest.fixture
    def sample_trades(self):
        """Sample trade data with 5 trades."""
        return pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-02", "2024-01-03", "2024-01-04"]),
            "gain_pct": [5.0, -2.0, 3.0, 4.0, -1.0],
            "wl": ["W", "L", "W", "W", "L"],
        })

    @pytest.fixture
    def strategy_config(self):
        return StrategyConfig(
            name="Test",
            file_path="test.csv",
            column_mapping=ColumnMapping("date", "gain_pct", "wl"),
            size_type=PositionSizeType.CUSTOM_PCT,
            size_value=10.0,  # 10% of account
            stop_pct=2.0,
            efficiency=1.0,
        )

    def test_calculate_single_strategy_equity(self, sample_trades, strategy_config):
        calc = PortfolioCalculator(starting_capital=100_000)
        result = calc.calculate_single_strategy(sample_trades, strategy_config)

        assert "equity" in result.columns
        assert "drawdown" in result.columns
        assert "date" in result.columns
        assert len(result) == 5

    def test_daily_compounding(self, sample_trades, strategy_config):
        """All trades on same day use same opening account value."""
        calc = PortfolioCalculator(starting_capital=100_000)
        result = calc.calculate_single_strategy(sample_trades, strategy_config)

        # Day 1: 1 trade, 5% gain on 10% position = 0.5% account gain
        # Account ends at 100,500
        # Day 2: 2 trades, both use 100,500 opening value
        #   Trade 1: -2% on 10,050 position = -201
        #   Trade 2: +3% on 10,050 position = +301.50
        # Account ends at 100,500 + 100.50 = 100,600.50
        assert result.iloc[0]["equity"] == pytest.approx(100_500, rel=0.01)
        # After day 2 trades (indices 1 and 2)
        assert result.iloc[2]["equity"] == pytest.approx(100_600.50, rel=0.01)

    def test_max_compound_limits_position_size(self, sample_trades, strategy_config):
        """Max compound caps position size."""
        strategy_config.max_compound = 5_000  # Cap at $5k position
        calc = PortfolioCalculator(starting_capital=100_000)
        result = calc.calculate_single_strategy(sample_trades, strategy_config)

        # 10% of 100k = 10k, but capped at 5k
        # Day 1: 5% of 5k = 250 gain
        assert result.iloc[0]["equity"] == pytest.approx(100_250, rel=0.01)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_portfolio_calculator.py::TestPortfolioCalculatorSingleStrategy -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# src/core/portfolio_calculator.py
"""Portfolio equity and drawdown calculation."""
import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from src.core.portfolio_models import StrategyConfig, PositionSizeType

logger = logging.getLogger(__name__)


class PortfolioCalculator:
    """Calculates equity curves for single or multiple strategies."""

    def __init__(self, starting_capital: float = 100_000):
        self.starting_capital = starting_capital

    def calculate_single_strategy(
        self,
        trades_df: pd.DataFrame,
        config: StrategyConfig,
    ) -> pd.DataFrame:
        """Calculate equity curve for a single strategy with daily compounding.

        Args:
            trades_df: DataFrame with trade data (must have columns from config.column_mapping)
            config: Strategy configuration

        Returns:
            DataFrame with columns: date, trade_num, pnl, equity, peak, drawdown
        """
        if trades_df.empty:
            return pd.DataFrame(columns=["date", "trade_num", "pnl", "equity", "peak", "drawdown"])

        mapping = config.column_mapping
        df = trades_df.copy()
        df = df.sort_values(mapping.date_col).reset_index(drop=True)

        # Group by date for daily compounding
        df["_date"] = pd.to_datetime(df[mapping.date_col]).dt.date

        results = []
        account_value = self.starting_capital
        peak = self.starting_capital
        trade_num = 0

        for date, day_trades in df.groupby("_date", sort=True):
            day_opening = account_value

            for _, trade in day_trades.iterrows():
                trade_num += 1
                gain_pct = float(trade[mapping.gain_pct_col])

                # Calculate position size
                position_size = self._calculate_position_size(
                    day_opening, config
                )

                # Apply efficiency and stop adjustment
                adjusted_gain = gain_pct * config.efficiency
                pnl = position_size * (adjusted_gain / 100.0)

                account_value += pnl
                peak = max(peak, account_value)
                drawdown = account_value - peak

                results.append({
                    "date": trade[mapping.date_col],
                    "trade_num": trade_num,
                    "pnl": pnl,
                    "equity": account_value,
                    "peak": peak,
                    "drawdown": drawdown,
                })

        return pd.DataFrame(results)

    def _calculate_position_size(
        self,
        account_value: float,
        config: StrategyConfig,
    ) -> float:
        """Calculate position size based on config."""
        if config.size_type == PositionSizeType.FLAT_DOLLAR:
            size = config.size_value
        elif config.size_type == PositionSizeType.CUSTOM_PCT:
            size = account_value * (config.size_value / 100.0)
        elif config.size_type == PositionSizeType.FRAC_KELLY:
            # For frac kelly, size_value is the fraction (e.g., 0.25 for quarter kelly)
            # Simplified: treat as percentage for now
            size = account_value * (config.size_value / 100.0)
        else:
            size = account_value * 0.10  # fallback 10%

        # Apply max compound limit
        if config.max_compound is not None:
            size = min(size, config.max_compound)

        return size
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_portfolio_calculator.py::TestPortfolioCalculatorSingleStrategy -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/portfolio_calculator.py tests/unit/test_portfolio_calculator.py
git commit -m "feat(portfolio): add single strategy equity calculation"
```

---

## Task 3: Portfolio Calculator - Multi-Strategy Merge

**Files:**
- Modify: `src/core/portfolio_calculator.py`
- Modify: `tests/unit/test_portfolio_calculator.py`

**Step 1: Write the failing test**

```python
# Add to tests/unit/test_portfolio_calculator.py

class TestPortfolioCalculatorMultiStrategy:
    @pytest.fixture
    def strategy_a_trades(self):
        return pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-01-03"]),
            "gain_pct": [5.0, 3.0],
            "wl": ["W", "W"],
        })

    @pytest.fixture
    def strategy_b_trades(self):
        return pd.DataFrame({
            "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "gain_pct": [2.0, -1.0],
            "wl": ["W", "L"],
        })

    @pytest.fixture
    def config_a(self):
        return StrategyConfig(
            name="Strategy A",
            file_path="a.csv",
            column_mapping=ColumnMapping("date", "gain_pct", "wl"),
            size_type=PositionSizeType.CUSTOM_PCT,
            size_value=10.0,
        )

    @pytest.fixture
    def config_b(self):
        return StrategyConfig(
            name="Strategy B",
            file_path="b.csv",
            column_mapping=ColumnMapping("date", "gain_pct", "wl"),
            size_type=PositionSizeType.CUSTOM_PCT,
            size_value=5.0,
        )

    def test_merge_strategies_chronologically(
        self, strategy_a_trades, strategy_b_trades, config_a, config_b
    ):
        calc = PortfolioCalculator(starting_capital=100_000)
        result = calc.calculate_portfolio(
            strategies=[
                (strategy_a_trades, config_a),
                (strategy_b_trades, config_b),
            ]
        )

        # Should have 4 trades total
        assert len(result) == 4
        # First trade is from strategy A on 2024-01-01
        assert result.iloc[0]["strategy"] == "Strategy A"
        # Second trade is from strategy B on 2024-01-02
        assert result.iloc[1]["strategy"] == "Strategy B"

    def test_same_day_trades_use_same_opening_value(
        self, strategy_a_trades, strategy_b_trades, config_a, config_b
    ):
        """Both strategies trading on 2024-01-03 use that day's opening value."""
        calc = PortfolioCalculator(starting_capital=100_000)
        result = calc.calculate_portfolio(
            strategies=[
                (strategy_a_trades, config_a),
                (strategy_b_trades, config_b),
            ]
        )

        # Trades on 2024-01-03 are indices 2 and 3
        day3_trades = result[result["date"].dt.date == pd.Timestamp("2024-01-03").date()]
        assert len(day3_trades) == 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_portfolio_calculator.py::TestPortfolioCalculatorMultiStrategy -v`
Expected: FAIL with "AttributeError: 'PortfolioCalculator' object has no attribute 'calculate_portfolio'"

**Step 3: Add multi-strategy calculation to PortfolioCalculator**

```python
# Add to src/core/portfolio_calculator.py (in PortfolioCalculator class)

    def calculate_portfolio(
        self,
        strategies: list[tuple[pd.DataFrame, StrategyConfig]],
    ) -> pd.DataFrame:
        """Calculate combined equity curve for multiple strategies.

        Trades are merged chronologically. All trades on the same day use
        that day's opening account value for position sizing.

        Args:
            strategies: List of (trades_df, config) tuples

        Returns:
            DataFrame with columns: date, trade_num, strategy, pnl, equity, peak, drawdown
        """
        if not strategies:
            return pd.DataFrame(
                columns=["date", "trade_num", "strategy", "pnl", "equity", "peak", "drawdown"]
            )

        # Merge all trades with strategy info
        all_trades = []
        for trades_df, config in strategies:
            if trades_df.empty:
                continue
            df = trades_df.copy()
            mapping = config.column_mapping
            df["_strategy_name"] = config.name
            df["_gain_pct"] = df[mapping.gain_pct_col]
            df["_date"] = pd.to_datetime(df[mapping.date_col])
            df["_config"] = [config] * len(df)  # Store config reference
            all_trades.append(df[["_date", "_gain_pct", "_strategy_name", "_config"]])

        if not all_trades:
            return pd.DataFrame(
                columns=["date", "trade_num", "strategy", "pnl", "equity", "peak", "drawdown"]
            )

        merged = pd.concat(all_trades, ignore_index=True)
        merged = merged.sort_values("_date").reset_index(drop=True)
        merged["_date_only"] = merged["_date"].dt.date

        results = []
        account_value = self.starting_capital
        peak = self.starting_capital
        trade_num = 0

        for date, day_trades in merged.groupby("_date_only", sort=True):
            day_opening = account_value

            for _, trade in day_trades.iterrows():
                trade_num += 1
                config: StrategyConfig = trade["_config"]
                gain_pct = float(trade["_gain_pct"])

                position_size = self._calculate_position_size(day_opening, config)
                adjusted_gain = gain_pct * config.efficiency
                pnl = position_size * (adjusted_gain / 100.0)

                account_value += pnl
                peak = max(peak, account_value)
                drawdown = account_value - peak

                results.append({
                    "date": trade["_date"],
                    "trade_num": trade_num,
                    "strategy": trade["_strategy_name"],
                    "pnl": pnl,
                    "equity": account_value,
                    "peak": peak,
                    "drawdown": drawdown,
                })

        return pd.DataFrame(results)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_portfolio_calculator.py::TestPortfolioCalculatorMultiStrategy -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/portfolio_calculator.py tests/unit/test_portfolio_calculator.py
git commit -m "feat(portfolio): add multi-strategy portfolio calculation"
```

---

## Task 4: Import Strategy Dialog

**Files:**
- Create: `src/ui/dialogs/import_strategy_dialog.py`
- Test: `tests/unit/test_import_strategy_dialog.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_import_strategy_dialog.py
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from PyQt6.QtWidgets import QApplication
from src.ui.dialogs.import_strategy_dialog import ImportStrategyDialog
from src.core.portfolio_models import ColumnMapping


@pytest.fixture(scope="module")
def app():
    """Create QApplication for Qt tests."""
    app = QApplication.instance() or QApplication([])
    yield app


class TestImportStrategyDialog:
    def test_dialog_creates_successfully(self, app, qtbot):
        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        assert dialog is not None

    def test_dialog_populates_columns_from_dataframe(self, app, qtbot):
        df = pd.DataFrame({
            "trade_date": ["2024-01-01"],
            "return_pct": [5.0],
            "outcome": ["W"],
        })
        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        dialog.set_preview_data(df)

        # Dropdowns should have the column names
        date_items = [dialog._date_combo.itemText(i) for i in range(dialog._date_combo.count())]
        assert "trade_date" in date_items
        assert "return_pct" in date_items
        assert "outcome" in date_items

    def test_get_column_mapping_returns_selected_values(self, app, qtbot):
        df = pd.DataFrame({
            "trade_date": ["2024-01-01"],
            "return_pct": [5.0],
            "outcome": ["W"],
        })
        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        dialog.set_preview_data(df)

        # Simulate user selections
        dialog._date_combo.setCurrentText("trade_date")
        dialog._gain_combo.setCurrentText("return_pct")
        dialog._wl_combo.setCurrentText("outcome")

        mapping = dialog.get_column_mapping()
        assert mapping.date_col == "trade_date"
        assert mapping.gain_pct_col == "return_pct"
        assert mapping.win_loss_col == "outcome"

    def test_import_button_disabled_until_all_mapped(self, app, qtbot):
        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)

        # Initially disabled
        assert not dialog._import_btn.isEnabled()

        # Set data and map all columns
        df = pd.DataFrame({
            "date": ["2024-01-01"],
            "gain": [5.0],
            "wl": ["W"],
        })
        dialog.set_preview_data(df)
        dialog._date_combo.setCurrentText("date")
        dialog._gain_combo.setCurrentText("gain")
        dialog._wl_combo.setCurrentText("wl")

        # Now enabled
        assert dialog._import_btn.isEnabled()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_import_strategy_dialog.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write the dialog implementation**

```python
# src/ui/dialogs/import_strategy_dialog.py
"""Dialog for importing strategy CSV with column mapping."""
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QGroupBox,
    QFormLayout,
    QHeaderView,
)

from src.core.portfolio_models import ColumnMapping
from src.ui.theme import Colors, Fonts, FontSizes, Spacing

logger = logging.getLogger(__name__)


class ImportStrategyDialog(QDialog):
    """Dialog for importing a strategy file and mapping columns."""

    PLACEHOLDER = "-- Select Column --"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Strategy")
        self.setMinimumSize(500, 500)
        self._preview_df: Optional[pd.DataFrame] = None
        self._file_path: Optional[str] = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.MD)

        # File selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("File:"))
        self._file_label = QLineEdit()
        self._file_label.setReadOnly(True)
        self._file_label.setPlaceholderText("No file selected")
        file_layout.addWidget(self._file_label, stretch=1)
        self._browse_btn = QPushButton("Browse...")
        file_layout.addWidget(self._browse_btn)
        layout.addLayout(file_layout)

        # Column mapping group
        mapping_group = QGroupBox("Column Mapping")
        mapping_layout = QFormLayout(mapping_group)

        self._date_combo = QComboBox()
        self._gain_combo = QComboBox()
        self._wl_combo = QComboBox()

        for combo in [self._date_combo, self._gain_combo, self._wl_combo]:
            combo.addItem(self.PLACEHOLDER)

        mapping_layout.addRow("Date Column:", self._date_combo)
        mapping_layout.addRow("Gain % Column:", self._gain_combo)
        mapping_layout.addRow("Win/Loss Column:", self._wl_combo)
        layout.addWidget(mapping_group)

        # Preview table
        preview_group = QGroupBox("Preview (first 5 rows)")
        preview_layout = QVBoxLayout(preview_group)
        self._preview_table = QTableWidget()
        self._preview_table.setMaximumHeight(150)
        preview_layout.addWidget(self._preview_table)
        layout.addWidget(preview_group)

        # Strategy name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Strategy Name:"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Enter strategy name")
        name_layout.addWidget(self._name_edit, stretch=1)
        layout.addLayout(name_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._cancel_btn = QPushButton("Cancel")
        self._import_btn = QPushButton("Import Strategy")
        self._import_btn.setEnabled(False)
        btn_layout.addWidget(self._cancel_btn)
        btn_layout.addWidget(self._import_btn)
        layout.addLayout(btn_layout)

    def _connect_signals(self):
        self._browse_btn.clicked.connect(self._on_browse)
        self._cancel_btn.clicked.connect(self.reject)
        self._import_btn.clicked.connect(self.accept)

        for combo in [self._date_combo, self._gain_combo, self._wl_combo]:
            combo.currentTextChanged.connect(self._validate_mapping)

    def _on_browse(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Strategy File",
            "",
            "Data Files (*.csv *.xlsx *.xls);;CSV Files (*.csv);;Excel Files (*.xlsx *.xls)",
        )
        if file_path:
            self._load_file(file_path)

    def _load_file(self, file_path: str):
        try:
            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

            self._file_path = file_path
            self._file_label.setText(Path(file_path).name)
            self._name_edit.setText(Path(file_path).stem)
            self.set_preview_data(df)
        except Exception as e:
            logger.error(f"Failed to load file: {e}")

    def set_preview_data(self, df: pd.DataFrame):
        """Set the preview data and populate column dropdowns."""
        self._preview_df = df
        columns = list(df.columns)

        # Update dropdowns
        for combo in [self._date_combo, self._gain_combo, self._wl_combo]:
            combo.clear()
            combo.addItem(self.PLACEHOLDER)
            combo.addItems(columns)

        # Update preview table
        preview = df.head(5)
        self._preview_table.setRowCount(len(preview))
        self._preview_table.setColumnCount(len(columns))
        self._preview_table.setHorizontalHeaderLabels(columns)

        for i, row in enumerate(preview.itertuples(index=False)):
            for j, val in enumerate(row):
                self._preview_table.setItem(i, j, QTableWidgetItem(str(val)))

        self._preview_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._validate_mapping()

    def _validate_mapping(self):
        """Enable import button only when all columns are mapped."""
        all_mapped = (
            self._date_combo.currentText() != self.PLACEHOLDER
            and self._gain_combo.currentText() != self.PLACEHOLDER
            and self._wl_combo.currentText() != self.PLACEHOLDER
        )
        self._import_btn.setEnabled(all_mapped)

    def get_column_mapping(self) -> ColumnMapping:
        """Get the selected column mapping."""
        return ColumnMapping(
            date_col=self._date_combo.currentText(),
            gain_pct_col=self._gain_combo.currentText(),
            win_loss_col=self._wl_combo.currentText(),
        )

    def get_strategy_name(self) -> str:
        """Get the entered strategy name."""
        return self._name_edit.text() or "Unnamed Strategy"

    def get_file_path(self) -> Optional[str]:
        """Get the selected file path."""
        return self._file_path

    def get_dataframe(self) -> Optional[pd.DataFrame]:
        """Get the loaded DataFrame."""
        return self._preview_df
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_import_strategy_dialog.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/ui/dialogs/import_strategy_dialog.py tests/unit/test_import_strategy_dialog.py
git commit -m "feat(portfolio): add import strategy dialog with column mapping"
```

---

## Task 5: Strategy Table Widget

**Files:**
- Create: `src/ui/components/strategy_table.py`
- Test: `tests/unit/test_strategy_table.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_strategy_table.py
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from src.ui.components.strategy_table import StrategyTableWidget
from src.core.portfolio_models import (
    StrategyConfig,
    ColumnMapping,
    PositionSizeType,
)


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance() or QApplication([])
    yield app


class TestStrategyTableWidget:
    def test_table_creates_successfully(self, app, qtbot):
        table = StrategyTableWidget()
        qtbot.addWidget(table)
        assert table is not None

    def test_add_strategy_adds_row(self, app, qtbot):
        table = StrategyTableWidget()
        qtbot.addWidget(table)

        config = StrategyConfig(
            name="Test Strategy",
            file_path="/path/test.csv",
            column_mapping=ColumnMapping("date", "gain_pct", "wl"),
        )
        table.add_strategy(config)

        assert table.rowCount() == 1

    def test_get_strategies_returns_all_configs(self, app, qtbot):
        table = StrategyTableWidget()
        qtbot.addWidget(table)

        config1 = StrategyConfig(
            name="Strategy A",
            file_path="a.csv",
            column_mapping=ColumnMapping("date", "gain", "wl"),
        )
        config2 = StrategyConfig(
            name="Strategy B",
            file_path="b.csv",
            column_mapping=ColumnMapping("date", "gain", "wl"),
        )
        table.add_strategy(config1)
        table.add_strategy(config2)

        strategies = table.get_strategies()
        assert len(strategies) == 2
        assert strategies[0].name == "Strategy A"
        assert strategies[1].name == "Strategy B"

    def test_baseline_checkbox_updates_config(self, app, qtbot):
        table = StrategyTableWidget()
        qtbot.addWidget(table)

        config = StrategyConfig(
            name="Test",
            file_path="test.csv",
            column_mapping=ColumnMapping("date", "gain", "wl"),
        )
        table.add_strategy(config)

        # Simulate checking baseline checkbox (column index 2)
        table.set_baseline(0, True)

        strategies = table.get_strategies()
        assert strategies[0].is_baseline is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_strategy_table.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write the table widget implementation**

```python
# src/ui/components/strategy_table.py
"""Strategy configuration table widget."""
import logging
from typing import Optional
from dataclasses import replace

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QMenu,
)

from src.core.portfolio_models import StrategyConfig, PositionSizeType, ColumnMapping
from src.ui.theme import Colors

logger = logging.getLogger(__name__)


class StrategyTableWidget(QTableWidget):
    """Table widget for managing strategy configurations."""

    strategy_changed = pyqtSignal()  # Emitted when any strategy config changes

    COLUMNS = [
        ("Name", 120),
        ("File", 140),
        ("BL", 40),
        ("CND", 40),
        ("Stop %", 70),
        ("Efficiency", 70),
        ("Size Type", 100),
        ("Size Value", 80),
        ("Max Compound", 100),
        ("", 30),  # Menu column
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._strategies: list[StrategyConfig] = []
        self._setup_table()

    def _setup_table(self):
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels([col[0] for col in self.COLUMNS])

        header = self.horizontalHeader()
        for i, (_, width) in enumerate(self.COLUMNS):
            if width > 0:
                self.setColumnWidth(i, width)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # File column stretches

        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)

    def add_strategy(self, config: StrategyConfig):
        """Add a strategy to the table."""
        self._strategies.append(config)
        row = self.rowCount()
        self.insertRow(row)
        self._populate_row(row, config)

    def _populate_row(self, row: int, config: StrategyConfig):
        """Populate a row with strategy data."""
        # Name (editable)
        name_item = QTableWidgetItem(config.name)
        self.setItem(row, 0, name_item)

        # File (display only)
        file_item = QTableWidgetItem(config.file_path.split("/")[-1].split("\\")[-1])
        file_item.setToolTip(config.file_path)
        file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.setItem(row, 1, file_item)

        # Baseline checkbox
        bl_checkbox = self._create_centered_checkbox(config.is_baseline)
        bl_checkbox.stateChanged.connect(lambda state, r=row: self._on_baseline_changed(r, state))
        self.setCellWidget(row, 2, bl_checkbox)

        # Candidate checkbox
        cnd_checkbox = self._create_centered_checkbox(config.is_candidate)
        cnd_checkbox.stateChanged.connect(lambda state, r=row: self._on_candidate_changed(r, state))
        self.setCellWidget(row, 3, cnd_checkbox)

        # Stop %
        stop_spin = QDoubleSpinBox()
        stop_spin.setRange(0.1, 100.0)
        stop_spin.setValue(config.stop_pct)
        stop_spin.setSuffix("%")
        stop_spin.valueChanged.connect(lambda v, r=row: self._on_stop_changed(r, v))
        self.setCellWidget(row, 4, stop_spin)

        # Efficiency
        eff_spin = QDoubleSpinBox()
        eff_spin.setRange(0.01, 2.0)
        eff_spin.setValue(config.efficiency)
        eff_spin.setSingleStep(0.05)
        eff_spin.valueChanged.connect(lambda v, r=row: self._on_efficiency_changed(r, v))
        self.setCellWidget(row, 5, eff_spin)

        # Size Type
        size_type_combo = QComboBox()
        size_type_combo.addItems(["Frac Kelly", "Custom %", "Flat $"])
        type_map = {
            PositionSizeType.FRAC_KELLY: 0,
            PositionSizeType.CUSTOM_PCT: 1,
            PositionSizeType.FLAT_DOLLAR: 2,
        }
        size_type_combo.setCurrentIndex(type_map.get(config.size_type, 1))
        size_type_combo.currentIndexChanged.connect(lambda i, r=row: self._on_size_type_changed(r, i))
        self.setCellWidget(row, 6, size_type_combo)

        # Size Value
        size_spin = QDoubleSpinBox()
        size_spin.setRange(0.01, 1_000_000)
        size_spin.setValue(config.size_value)
        size_spin.valueChanged.connect(lambda v, r=row: self._on_size_value_changed(r, v))
        self.setCellWidget(row, 7, size_spin)

        # Max Compound
        max_spin = QDoubleSpinBox()
        max_spin.setRange(0, 10_000_000)
        max_spin.setSpecialValueText("None")
        max_spin.setValue(config.max_compound or 0)
        max_spin.setPrefix("$")
        max_spin.valueChanged.connect(lambda v, r=row: self._on_max_compound_changed(r, v))
        self.setCellWidget(row, 8, max_spin)

        # Menu button
        menu_btn = QPushButton("⋮")
        menu_btn.setFixedWidth(30)
        menu_btn.clicked.connect(lambda _, r=row: self._show_row_menu(r))
        self.setCellWidget(row, 9, menu_btn)

    def _create_centered_checkbox(self, checked: bool) -> QWidget:
        """Create a centered checkbox widget."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        layout.addWidget(checkbox)
        return widget

    def _get_checkbox(self, row: int, col: int) -> Optional[QCheckBox]:
        """Get checkbox from cell widget."""
        widget = self.cellWidget(row, col)
        if widget:
            checkbox = widget.findChild(QCheckBox)
            return checkbox
        return None

    def set_baseline(self, row: int, checked: bool):
        """Set baseline state for a row."""
        checkbox = self._get_checkbox(row, 2)
        if checkbox:
            checkbox.setChecked(checked)

    def set_candidate(self, row: int, checked: bool):
        """Set candidate state for a row."""
        checkbox = self._get_checkbox(row, 3)
        if checkbox:
            checkbox.setChecked(checked)

    def _on_baseline_changed(self, row: int, state: int):
        self._strategies[row] = replace(
            self._strategies[row], is_baseline=(state == Qt.CheckState.Checked.value)
        )
        self.strategy_changed.emit()

    def _on_candidate_changed(self, row: int, state: int):
        self._strategies[row] = replace(
            self._strategies[row], is_candidate=(state == Qt.CheckState.Checked.value)
        )
        self.strategy_changed.emit()

    def _on_stop_changed(self, row: int, value: float):
        self._strategies[row] = replace(self._strategies[row], stop_pct=value)
        self.strategy_changed.emit()

    def _on_efficiency_changed(self, row: int, value: float):
        self._strategies[row] = replace(self._strategies[row], efficiency=value)
        self.strategy_changed.emit()

    def _on_size_type_changed(self, row: int, index: int):
        type_map = {0: PositionSizeType.FRAC_KELLY, 1: PositionSizeType.CUSTOM_PCT, 2: PositionSizeType.FLAT_DOLLAR}
        self._strategies[row] = replace(self._strategies[row], size_type=type_map[index])
        self.strategy_changed.emit()

    def _on_size_value_changed(self, row: int, value: float):
        self._strategies[row] = replace(self._strategies[row], size_value=value)
        self.strategy_changed.emit()

    def _on_max_compound_changed(self, row: int, value: float):
        self._strategies[row] = replace(
            self._strategies[row], max_compound=value if value > 0 else None
        )
        self.strategy_changed.emit()

    def _show_row_menu(self, row: int):
        """Show context menu for row."""
        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self.remove_strategy(row))
        menu.exec(self.cursor().pos())

    def remove_strategy(self, row: int):
        """Remove a strategy from the table."""
        if 0 <= row < len(self._strategies):
            self._strategies.pop(row)
            self.removeRow(row)
            self.strategy_changed.emit()

    def get_strategies(self) -> list[StrategyConfig]:
        """Get all strategy configurations."""
        # Update names from editable cells
        for row in range(self.rowCount()):
            name_item = self.item(row, 0)
            if name_item:
                self._strategies[row] = replace(self._strategies[row], name=name_item.text())
        return self._strategies.copy()

    def clear_all(self):
        """Remove all strategies."""
        self._strategies.clear()
        self.setRowCount(0)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_strategy_table.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/ui/components/strategy_table.py tests/unit/test_strategy_table.py
git commit -m "feat(portfolio): add strategy table widget"
```

---

## Task 6: Portfolio Charts Component

**Files:**
- Create: `src/ui/components/portfolio_charts.py`
- Test: `tests/unit/test_portfolio_charts.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_portfolio_charts.py
import pytest
import pandas as pd
import numpy as np
from PyQt6.QtWidgets import QApplication
from src.ui.components.portfolio_charts import PortfolioChartsWidget


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance() or QApplication([])
    yield app


class TestPortfolioChartsWidget:
    def test_widget_creates_successfully(self, app, qtbot):
        widget = PortfolioChartsWidget()
        qtbot.addWidget(widget)
        assert widget is not None

    def test_set_data_updates_charts(self, app, qtbot):
        widget = PortfolioChartsWidget()
        qtbot.addWidget(widget)

        # Create sample equity data
        data = {
            "Strategy A": pd.DataFrame({
                "trade_num": [1, 2, 3],
                "equity": [100000, 101000, 102000],
                "drawdown": [0, 0, 0],
                "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            }),
            "baseline": pd.DataFrame({
                "trade_num": [1, 2],
                "equity": [100000, 100500],
                "drawdown": [0, 0],
                "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            }),
        }
        widget.set_data(data)
        # Should not raise

    def test_toggle_series_visibility(self, app, qtbot):
        widget = PortfolioChartsWidget()
        qtbot.addWidget(widget)

        widget.set_series_visible("Strategy A", False)
        assert widget.is_series_visible("Strategy A") is False

        widget.set_series_visible("Strategy A", True)
        assert widget.is_series_visible("Strategy A") is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_portfolio_charts.py -v`
Expected: FAIL

**Step 3: Write the portfolio charts widget**

```python
# src/ui/components/portfolio_charts.py
"""Portfolio equity and drawdown charts with shared legend."""
import logging
from typing import Optional

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QPushButton,
    QButtonGroup,
    QFrame,
)

from src.ui.theme import Colors, Fonts, FontSizes, Spacing
from src.ui.components.axis_mode_toggle import AxisMode, AxisModeToggle

logger = logging.getLogger(__name__)

# Color palette for strategies
STRATEGY_COLORS = [
    "#00D9FF",  # cyan
    "#FFB800",  # amber
    "#FF00FF",  # magenta
    "#00FF88",  # lime
    "#FF6B6B",  # coral
    "#A855F7",  # violet
]

BASELINE_COLOR = "#AAAAAA"
COMBINED_COLOR = "#00FF00"


class PortfolioChartsWidget(QWidget):
    """Widget containing equity and drawdown charts with shared legend."""

    axis_mode_changed = pyqtSignal(AxisMode)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: dict[str, pd.DataFrame] = {}
        self._series_visible: dict[str, bool] = {}
        self._curves: dict[str, dict] = {}  # {name: {"equity": curve, "drawdown": curve}}
        self._axis_mode = AxisMode.TRADES
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        # Charts container (side by side)
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(Spacing.MD)

        # Equity chart
        equity_container = QVBoxLayout()
        equity_header = QHBoxLayout()
        equity_header.addWidget(QLabel("Equity Curve"))
        equity_header.addStretch()
        self._equity_toggle = AxisModeToggle()
        self._equity_toggle.mode_changed.connect(self._on_axis_mode_changed)
        equity_header.addWidget(self._equity_toggle)
        equity_container.addLayout(equity_header)

        self._equity_plot = pg.PlotWidget()
        self._equity_plot.setBackground(Colors.BG_SURFACE)
        self._equity_plot.showGrid(x=True, y=True, alpha=0.3)
        self._equity_plot.setLabel("left", "Account Value ($)")
        equity_container.addWidget(self._equity_plot)
        charts_layout.addLayout(equity_container)

        # Drawdown chart
        dd_container = QVBoxLayout()
        dd_header = QHBoxLayout()
        dd_header.addWidget(QLabel("Drawdown"))
        dd_header.addStretch()
        self._dd_toggle = AxisModeToggle()
        self._dd_toggle.mode_changed.connect(self._on_axis_mode_changed)
        dd_header.addWidget(self._dd_toggle)
        dd_container.addLayout(dd_header)

        self._dd_plot = pg.PlotWidget()
        self._dd_plot.setBackground(Colors.BG_SURFACE)
        self._dd_plot.showGrid(x=True, y=True, alpha=0.3)
        self._dd_plot.setLabel("left", "Drawdown (%)")
        dd_container.addWidget(self._dd_plot)
        charts_layout.addLayout(dd_container)

        layout.addLayout(charts_layout, stretch=1)

        # Legend bar
        self._legend_frame = QFrame()
        self._legend_frame.setStyleSheet(f"background-color: {Colors.BG_ELEVATED};")
        self._legend_layout = QHBoxLayout(self._legend_frame)
        self._legend_layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        self._legend_layout.addStretch()
        layout.addWidget(self._legend_frame)

        self._legend_checkboxes: dict[str, QCheckBox] = {}

    def _on_axis_mode_changed(self, mode: AxisMode):
        self._axis_mode = mode
        # Sync both toggles
        self._equity_toggle.set_mode(mode)
        self._dd_toggle.set_mode(mode)
        self._update_charts()
        self.axis_mode_changed.emit(mode)

    def set_data(self, data: dict[str, pd.DataFrame]):
        """Set chart data.

        Args:
            data: Dict mapping series name to DataFrame with columns:
                  trade_num, equity, drawdown, date
        """
        self._data = data
        self._update_legend()
        self._update_charts()

    def _update_legend(self):
        """Update legend checkboxes."""
        # Clear existing
        for cb in self._legend_checkboxes.values():
            self._legend_layout.removeWidget(cb)
            cb.deleteLater()
        self._legend_checkboxes.clear()

        # Add new
        for i, name in enumerate(self._data.keys()):
            if name not in self._series_visible:
                self._series_visible[name] = True

            cb = QCheckBox(name)
            cb.setChecked(self._series_visible[name])

            # Set color indicator
            if name == "baseline":
                color = BASELINE_COLOR
            elif name == "combined":
                color = COMBINED_COLOR
            else:
                color = STRATEGY_COLORS[i % len(STRATEGY_COLORS)]

            cb.setStyleSheet(f"QCheckBox {{ color: {color}; }}")
            cb.stateChanged.connect(lambda state, n=name: self._on_legend_toggled(n, state))

            self._legend_layout.insertWidget(self._legend_layout.count() - 1, cb)
            self._legend_checkboxes[name] = cb

    def _on_legend_toggled(self, name: str, state: int):
        self._series_visible[name] = state == Qt.CheckState.Checked.value
        self._update_charts()

    def _update_charts(self):
        """Redraw all chart curves."""
        self._equity_plot.clear()
        self._dd_plot.clear()

        for i, (name, df) in enumerate(self._data.items()):
            if not self._series_visible.get(name, True):
                continue

            if df.empty:
                continue

            # Determine x-axis data
            if self._axis_mode == AxisMode.DATE and "date" in df.columns:
                x = df["date"].astype(np.int64) / 1e9  # Convert to timestamp
            else:
                x = df["trade_num"].values

            # Determine color and style
            if name == "baseline":
                color = BASELINE_COLOR
                style = Qt.PenStyle.DashLine
            elif name == "combined":
                color = COMBINED_COLOR
                style = Qt.PenStyle.SolidLine
            else:
                color = STRATEGY_COLORS[i % len(STRATEGY_COLORS)]
                style = Qt.PenStyle.SolidLine

            pen = pg.mkPen(color=color, width=2, style=style)

            # Equity curve
            self._equity_plot.plot(x, df["equity"].values, pen=pen, name=name)

            # Drawdown curve (as percentage)
            dd_pct = (df["drawdown"].values / df["peak"].values) * 100 if "peak" in df.columns else df["drawdown"].values
            self._dd_plot.plot(x, dd_pct, pen=pen, name=name)

    def set_series_visible(self, name: str, visible: bool):
        """Set visibility of a series."""
        self._series_visible[name] = visible
        if name in self._legend_checkboxes:
            self._legend_checkboxes[name].setChecked(visible)
        self._update_charts()

    def is_series_visible(self, name: str) -> bool:
        """Check if a series is visible."""
        return self._series_visible.get(name, True)

    def clear(self):
        """Clear all data."""
        self._data.clear()
        self._equity_plot.clear()
        self._dd_plot.clear()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_portfolio_charts.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/ui/components/portfolio_charts.py tests/unit/test_portfolio_charts.py
git commit -m "feat(portfolio): add portfolio charts widget with legend"
```

---

## Task 7: Portfolio Overview Tab - Main Widget

**Files:**
- Create: `src/tabs/portfolio_overview.py`
- Test: `tests/unit/test_portfolio_overview_tab.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_portfolio_overview_tab.py
import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
from src.tabs.portfolio_overview import PortfolioOverviewTab
from src.core.app_state import AppState


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def mock_app_state():
    state = MagicMock(spec=AppState)
    return state


class TestPortfolioOverviewTab:
    def test_tab_creates_successfully(self, app, qtbot, mock_app_state):
        tab = PortfolioOverviewTab(mock_app_state)
        qtbot.addWidget(tab)
        assert tab is not None

    def test_tab_has_add_strategy_button(self, app, qtbot, mock_app_state):
        tab = PortfolioOverviewTab(mock_app_state)
        qtbot.addWidget(tab)
        assert tab._add_strategy_btn is not None

    def test_tab_has_account_start_input(self, app, qtbot, mock_app_state):
        tab = PortfolioOverviewTab(mock_app_state)
        qtbot.addWidget(tab)
        assert tab._account_start_spin is not None
        assert tab._account_start_spin.value() == 100_000  # default

    def test_tab_has_strategy_table(self, app, qtbot, mock_app_state):
        tab = PortfolioOverviewTab(mock_app_state)
        qtbot.addWidget(tab)
        assert tab._strategy_table is not None

    def test_tab_has_charts(self, app, qtbot, mock_app_state):
        tab = PortfolioOverviewTab(mock_app_state)
        qtbot.addWidget(tab)
        assert tab._charts is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_portfolio_overview_tab.py -v`
Expected: FAIL

**Step 3: Write the Portfolio Overview tab**

```python
# src/tabs/portfolio_overview.py
"""Portfolio Overview tab for multi-strategy analysis."""
import logging
from typing import Optional

import pandas as pd
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QDoubleSpinBox,
    QScrollArea,
    QSplitter,
)

from src.core.app_state import AppState
from src.core.portfolio_models import StrategyConfig, ColumnMapping
from src.core.portfolio_calculator import PortfolioCalculator
from src.ui.components.strategy_table import StrategyTableWidget
from src.ui.components.portfolio_charts import PortfolioChartsWidget
from src.ui.components.empty_state import EmptyState
from src.ui.dialogs.import_strategy_dialog import ImportStrategyDialog
from src.ui.theme import Colors, Fonts, FontSizes, Spacing

logger = logging.getLogger(__name__)


class PortfolioOverviewTab(QWidget):
    """Tab for analyzing multiple trading strategies together."""

    def __init__(self, app_state: AppState, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._app_state = app_state
        self._calculator = PortfolioCalculator()
        self._strategy_data: dict[str, pd.DataFrame] = {}  # Loaded CSV data per strategy
        self._recalc_timer = QTimer(self)
        self._recalc_timer.setSingleShot(True)
        self._recalc_timer.setInterval(300)
        self._recalc_timer.timeout.connect(self._recalculate)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        self.setObjectName("portfolioOverviewTab")
        self.setStyleSheet(f"""
            QWidget#portfolioOverviewTab {{
                background-color: {Colors.BG_SURFACE};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # Toolbar
        toolbar = QHBoxLayout()
        self._add_strategy_btn = QPushButton("+ Add Strategy")
        self._add_strategy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ACCENT_PRIMARY};
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.ACCENT_SECONDARY};
            }}
        """)
        toolbar.addWidget(self._add_strategy_btn)
        toolbar.addStretch()

        toolbar.addWidget(QLabel("Account Start:"))
        self._account_start_spin = QDoubleSpinBox()
        self._account_start_spin.setRange(1_000, 100_000_000)
        self._account_start_spin.setValue(100_000)
        self._account_start_spin.setPrefix("$")
        self._account_start_spin.setSingleStep(10_000)
        self._account_start_spin.setMinimumWidth(150)
        toolbar.addWidget(self._account_start_spin)

        layout.addLayout(toolbar)

        # Main splitter (table on top, charts on bottom)
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Strategy table
        self._strategy_table = StrategyTableWidget()
        self._strategy_table.setMinimumHeight(150)
        self._strategy_table.setMaximumHeight(250)
        splitter.addWidget(self._strategy_table)

        # Charts
        self._charts = PortfolioChartsWidget()
        splitter.addWidget(self._charts)

        # Set initial sizes
        splitter.setSizes([200, 400])

        layout.addWidget(splitter, stretch=1)

    def _connect_signals(self):
        self._add_strategy_btn.clicked.connect(self._on_add_strategy)
        self._strategy_table.strategy_changed.connect(self._schedule_recalculation)
        self._account_start_spin.valueChanged.connect(self._schedule_recalculation)

    def _on_add_strategy(self):
        """Open import dialog to add a new strategy."""
        dialog = ImportStrategyDialog(self)
        if dialog.exec():
            config = StrategyConfig(
                name=dialog.get_strategy_name(),
                file_path=dialog.get_file_path() or "",
                column_mapping=dialog.get_column_mapping(),
            )
            df = dialog.get_dataframe()
            if df is not None:
                self._strategy_data[config.name] = df
                self._strategy_table.add_strategy(config)
                self._schedule_recalculation()

    def _schedule_recalculation(self):
        """Debounce recalculation."""
        self._recalc_timer.start()

    def _recalculate(self):
        """Recalculate and update charts."""
        strategies = self._strategy_table.get_strategies()
        if not strategies:
            self._charts.clear()
            return

        self._calculator.starting_capital = self._account_start_spin.value()

        chart_data = {}
        baseline_strategies = []
        candidate_strategies = []

        # Calculate individual strategy curves
        for config in strategies:
            if config.name not in self._strategy_data:
                continue

            df = self._strategy_data[config.name]
            equity_df = self._calculator.calculate_single_strategy(df, config)
            chart_data[config.name] = equity_df

            if config.is_baseline:
                baseline_strategies.append((df, config))
            if config.is_candidate:
                candidate_strategies.append((df, config))

        # Calculate baseline aggregate
        if baseline_strategies:
            baseline_df = self._calculator.calculate_portfolio(baseline_strategies)
            if not baseline_df.empty:
                chart_data["baseline"] = baseline_df

        # Calculate combined (baseline + candidates)
        if baseline_strategies and candidate_strategies:
            combined = baseline_strategies + candidate_strategies
            combined_df = self._calculator.calculate_portfolio(combined)
            if not combined_df.empty:
                chart_data["combined"] = combined_df

        self._charts.set_data(chart_data)

    def get_strategies(self) -> list[StrategyConfig]:
        """Get all configured strategies."""
        return self._strategy_table.get_strategies()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_portfolio_overview_tab.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tabs/portfolio_overview.py tests/unit/test_portfolio_overview_tab.py
git commit -m "feat(portfolio): add Portfolio Overview tab widget"
```

---

## Task 8: Register Tab in Main Window

**Files:**
- Modify: `src/ui/main_window.py`

**Step 1: Add import**

At the top of `src/ui/main_window.py`, add:

```python
from src.tabs.portfolio_overview import PortfolioOverviewTab
```

**Step 2: Add tab to tabs list**

In the `_create_tabs` section (around line 53-61), add the new tab:

```python
tabs = [
    ("Data Input", DataInputTab(self._app_state)),
    ("Feature Explorer", FeatureExplorerTab(self._app_state)),
    ("Breakdown", BreakdownTab(self._app_state)),
    ("Data Binning", DataBinningTab(self._app_state)),
    ("PnL & Trading Stats", PnLStatsTab(self._app_state)),
    ("Monte Carlo", MonteCarloTab(self._app_state)),
    ("Parameter Sensitivity", ParameterSensitivityTab(self._app_state)),
    ("Feature Insights", FeatureInsightsTab(self._app_state)),
    ("Portfolio Overview", PortfolioOverviewTab(self._app_state)),  # NEW
]
```

**Step 3: Verify app launches**

Run: `python -m src.main`
Expected: App launches with "Portfolio Overview" tab visible

**Step 4: Commit**

```bash
git add src/ui/main_window.py
git commit -m "feat(portfolio): register Portfolio Overview tab in main window"
```

---

## Task 9: Add Persistence (Save/Load Configurations)

**Files:**
- Create: `src/core/portfolio_config_manager.py`
- Modify: `src/tabs/portfolio_overview.py`
- Test: `tests/unit/test_portfolio_config_manager.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_portfolio_config_manager.py
import pytest
import json
from pathlib import Path
from src.core.portfolio_config_manager import PortfolioConfigManager
from src.core.portfolio_models import StrategyConfig, ColumnMapping, PositionSizeType


class TestPortfolioConfigManager:
    def test_save_and_load_config(self, tmp_path):
        config_file = tmp_path / "portfolio_config.json"
        manager = PortfolioConfigManager(config_file)

        strategies = [
            StrategyConfig(
                name="Strategy A",
                file_path="/path/to/a.csv",
                column_mapping=ColumnMapping("date", "gain", "wl"),
                is_baseline=True,
                size_value=15.0,
            ),
            StrategyConfig(
                name="Strategy B",
                file_path="/path/to/b.csv",
                column_mapping=ColumnMapping("dt", "pct", "outcome"),
                is_candidate=True,
            ),
        ]

        manager.save(strategies, account_start=150_000)

        loaded_strategies, account_start = manager.load()

        assert len(loaded_strategies) == 2
        assert loaded_strategies[0].name == "Strategy A"
        assert loaded_strategies[0].is_baseline is True
        assert loaded_strategies[0].size_value == 15.0
        assert loaded_strategies[1].is_candidate is True
        assert account_start == 150_000

    def test_load_missing_file_returns_empty(self, tmp_path):
        config_file = tmp_path / "nonexistent.json"
        manager = PortfolioConfigManager(config_file)

        strategies, account_start = manager.load()

        assert strategies == []
        assert account_start == 100_000  # default
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_portfolio_config_manager.py -v`
Expected: FAIL

**Step 3: Write the config manager**

```python
# src/core/portfolio_config_manager.py
"""Persistence for portfolio configurations."""
import json
import logging
from pathlib import Path
from typing import Optional

from src.core.portfolio_models import StrategyConfig, ColumnMapping, PositionSizeType

logger = logging.getLogger(__name__)


class PortfolioConfigManager:
    """Manages saving and loading portfolio configurations."""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path.home() / ".lumen" / "portfolio_config.json"
        self._config_path = Path(config_path)

    def save(self, strategies: list[StrategyConfig], account_start: float = 100_000):
        """Save strategies and account start to JSON file."""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "account_start": account_start,
            "strategies": [self._strategy_to_dict(s) for s in strategies],
        }

        with open(self._config_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved portfolio config to {self._config_path}")

    def load(self) -> tuple[list[StrategyConfig], float]:
        """Load strategies and account start from JSON file.

        Returns:
            Tuple of (strategies list, account_start value)
        """
        if not self._config_path.exists():
            return [], 100_000

        try:
            with open(self._config_path) as f:
                data = json.load(f)

            account_start = data.get("account_start", 100_000)
            strategies = [self._dict_to_strategy(s) for s in data.get("strategies", [])]

            logger.info(f"Loaded {len(strategies)} strategies from {self._config_path}")
            return strategies, account_start

        except Exception as e:
            logger.error(f"Failed to load portfolio config: {e}")
            return [], 100_000

    def _strategy_to_dict(self, config: StrategyConfig) -> dict:
        return {
            "name": config.name,
            "file_path": config.file_path,
            "column_mapping": {
                "date_col": config.column_mapping.date_col,
                "gain_pct_col": config.column_mapping.gain_pct_col,
                "win_loss_col": config.column_mapping.win_loss_col,
            },
            "stop_pct": config.stop_pct,
            "efficiency": config.efficiency,
            "size_type": config.size_type.value,
            "size_value": config.size_value,
            "max_compound": config.max_compound,
            "is_baseline": config.is_baseline,
            "is_candidate": config.is_candidate,
        }

    def _dict_to_strategy(self, data: dict) -> StrategyConfig:
        mapping = ColumnMapping(
            date_col=data["column_mapping"]["date_col"],
            gain_pct_col=data["column_mapping"]["gain_pct_col"],
            win_loss_col=data["column_mapping"]["win_loss_col"],
        )
        return StrategyConfig(
            name=data["name"],
            file_path=data["file_path"],
            column_mapping=mapping,
            stop_pct=data.get("stop_pct", 2.0),
            efficiency=data.get("efficiency", 1.0),
            size_type=PositionSizeType(data.get("size_type", "custom_pct")),
            size_value=data.get("size_value", 10.0),
            max_compound=data.get("max_compound"),
            is_baseline=data.get("is_baseline", False),
            is_candidate=data.get("is_candidate", False),
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_portfolio_config_manager.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/portfolio_config_manager.py tests/unit/test_portfolio_config_manager.py
git commit -m "feat(portfolio): add config persistence for strategies"
```

---

## Task 10: Integration - Wire Persistence to Tab

**Files:**
- Modify: `src/tabs/portfolio_overview.py`

**Step 1: Add imports and initialization**

Add to top of file:

```python
from src.core.portfolio_config_manager import PortfolioConfigManager
```

In `__init__`, add:

```python
self._config_manager = PortfolioConfigManager()
self._load_saved_config()
```

**Step 2: Add load method**

```python
def _load_saved_config(self):
    """Load saved strategies on startup."""
    strategies, account_start = self._config_manager.load()
    self._account_start_spin.setValue(account_start)

    for config in strategies:
        # Try to reload the CSV data
        try:
            if config.file_path.endswith(".csv"):
                df = pd.read_csv(config.file_path)
            else:
                df = pd.read_excel(config.file_path)
            self._strategy_data[config.name] = df
            self._strategy_table.add_strategy(config)
        except Exception as e:
            logger.warning(f"Could not load file for {config.name}: {e}")
            # Still add strategy but mark file as missing
            self._strategy_table.add_strategy(config)

    if strategies:
        self._schedule_recalculation()
```

**Step 3: Add save on change**

In `_recalculate`, add at the end:

```python
# Save configuration
self._config_manager.save(strategies, self._account_start_spin.value())
```

**Step 4: Test manually**

Run: `python -m src.main`
- Add a strategy
- Close app
- Reopen app
- Strategy should be restored

**Step 5: Commit**

```bash
git add src/tabs/portfolio_overview.py
git commit -m "feat(portfolio): wire persistence to tab for auto-save/restore"
```

---

## Task 11: Final Integration Test

**Files:**
- Create: `tests/integration/test_portfolio_overview.py`

**Step 1: Write integration test**

```python
# tests/integration/test_portfolio_overview.py
import pytest
import pandas as pd
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from src.tabs.portfolio_overview import PortfolioOverviewTab
from src.core.app_state import AppState
from src.core.portfolio_models import StrategyConfig, ColumnMapping


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def sample_csv(tmp_path):
    """Create a sample CSV file for testing."""
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=10),
        "gain_pct": [2.5, -1.0, 3.0, -0.5, 4.0, 1.5, -2.0, 2.0, -1.5, 3.5],
        "wl": ["W", "L", "W", "L", "W", "W", "L", "W", "L", "W"],
    })
    csv_path = tmp_path / "test_strategy.csv"
    df.to_csv(csv_path, index=False)
    return csv_path


class TestPortfolioOverviewIntegration:
    def test_full_workflow(self, app, qtbot, sample_csv, tmp_path):
        """Test adding strategy, configuring, and seeing charts update."""
        app_state = AppState()
        tab = PortfolioOverviewTab(app_state)
        qtbot.addWidget(tab)

        # Load CSV data directly (simulating import dialog)
        df = pd.read_csv(sample_csv)
        config = StrategyConfig(
            name="Test Strategy",
            file_path=str(sample_csv),
            column_mapping=ColumnMapping("date", "gain_pct", "wl"),
            is_baseline=True,
        )
        tab._strategy_data[config.name] = df
        tab._strategy_table.add_strategy(config)

        # Trigger recalculation
        tab._recalculate()

        # Verify charts have data
        assert "Test Strategy" in tab._charts._data
        assert len(tab._charts._data["Test Strategy"]) == 10

    def test_baseline_vs_combined_calculation(self, app, qtbot, tmp_path):
        """Test that baseline and combined are calculated correctly."""
        # Create two CSV files
        df1 = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=5),
            "gain_pct": [5.0, 3.0, -2.0, 4.0, 1.0],
            "wl": ["W", "W", "L", "W", "W"],
        })
        df2 = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=5),
            "gain_pct": [2.0, -1.0, 3.0, 2.0, -1.0],
            "wl": ["W", "L", "W", "W", "L"],
        })

        csv1 = tmp_path / "strategy1.csv"
        csv2 = tmp_path / "strategy2.csv"
        df1.to_csv(csv1, index=False)
        df2.to_csv(csv2, index=False)

        app_state = AppState()
        tab = PortfolioOverviewTab(app_state)
        qtbot.addWidget(tab)

        # Add baseline strategy
        config1 = StrategyConfig(
            name="Baseline Strategy",
            file_path=str(csv1),
            column_mapping=ColumnMapping("date", "gain_pct", "wl"),
            is_baseline=True,
        )
        tab._strategy_data[config1.name] = df1
        tab._strategy_table.add_strategy(config1)

        # Add candidate strategy
        config2 = StrategyConfig(
            name="Candidate Strategy",
            file_path=str(csv2),
            column_mapping=ColumnMapping("date", "gain_pct", "wl"),
            is_candidate=True,
        )
        tab._strategy_data[config2.name] = df2
        tab._strategy_table.add_strategy(config2)

        # Trigger recalculation
        tab._recalculate()

        # Verify all expected series exist
        assert "Baseline Strategy" in tab._charts._data
        assert "Candidate Strategy" in tab._charts._data
        assert "baseline" in tab._charts._data
        assert "combined" in tab._charts._data
```

**Step 2: Run integration tests**

Run: `pytest tests/integration/test_portfolio_overview.py -v`
Expected: PASS

**Step 3: Run all tests**

Run: `pytest tests/ -v --ignore=tests/visual`
Expected: All tests pass

**Step 4: Final commit**

```bash
git add tests/integration/test_portfolio_overview.py
git commit -m "test(portfolio): add integration tests for portfolio overview"
```

---

## Summary

The implementation is broken into 11 tasks:

1. **Strategy Data Model** - Data classes for strategy configuration
2. **Portfolio Calculator - Single Strategy** - Equity calculation with daily compounding
3. **Portfolio Calculator - Multi-Strategy** - Merging multiple strategies chronologically
4. **Import Strategy Dialog** - Column mapping UI
5. **Strategy Table Widget** - Inline editing table for configurations
6. **Portfolio Charts Component** - Equity and drawdown charts with legend
7. **Portfolio Overview Tab** - Main tab widget bringing it together
8. **Register Tab in Main Window** - Wire into app
9. **Config Persistence** - Save/load to JSON
10. **Wire Persistence** - Auto-save on changes
11. **Integration Tests** - End-to-end testing

Each task follows TDD: write failing test → implement → verify → commit.
