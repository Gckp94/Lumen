# Chart Viewer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Chart Viewer tab that displays candlestick charts for filtered trades with dynamically calculated exit markers based on user-configured scaling rules.

**Architecture:** New dockable tab with left panel (trade browser + scaling config) and right area (candlestick chart). Price data loaded from local parquet files, exits simulated on-the-fly based on entry price, stop level, and scaling config.

**Tech Stack:** PyQt6, pyqtgraph (candlestick rendering), pandas/pyarrow (parquet loading), PyQt6Ads (docking)

---

## Task 1: Price Data Loader Core

**Files:**
- Create: `src/core/price_data.py`
- Test: `tests/unit/test_price_data.py`

**Step 1: Write the failing test for loading minute data**

```python
# tests/unit/test_price_data.py
"""Tests for price data loading and aggregation."""

import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.price_data import PriceDataLoader, Resolution


class TestPriceDataLoader:
    """Tests for PriceDataLoader class."""

    def test_load_minute_data_returns_dataframe(self, tmp_path: Path) -> None:
        """Load minute data for a ticker and date."""
        # Create test parquet file
        df = pd.DataFrame({
            "ticker": ["AAPL", "AAPL", "MSFT"],
            "datetime": pd.to_datetime(["2024-01-15 09:30", "2024-01-15 09:31", "2024-01-15 09:30"]),
            "open": [185.0, 185.5, 400.0],
            "high": [186.0, 186.0, 401.0],
            "low": [184.5, 185.0, 399.0],
            "close": [185.5, 185.8, 400.5],
            "volume": [1000, 1100, 2000],
        })
        parquet_path = tmp_path / "2024-01-15.parquet"
        df.to_parquet(parquet_path)

        loader = PriceDataLoader(minute_path=tmp_path)
        result = loader.load("AAPL", "2024-01-15", Resolution.MINUTE_1)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == ["datetime", "open", "high", "low", "close", "volume"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_price_data.py::TestPriceDataLoader::test_load_minute_data_returns_dataframe -v`
Expected: FAIL with "No module named 'src.core.price_data'"

**Step 3: Write minimal implementation**

```python
# src/core/price_data.py
"""Price data loading and aggregation for Chart Viewer.

Loads OHLCV data from local parquet files and aggregates to different resolutions.
"""

import logging
from enum import Enum
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class Resolution(Enum):
    """Chart resolution options."""

    SECOND_1 = ("1s", 1, "second")
    SECOND_5 = ("5s", 5, "second")
    SECOND_15 = ("15s", 15, "second")
    SECOND_30 = ("30s", 30, "second")
    MINUTE_1 = ("1m", 1, "minute")
    MINUTE_2 = ("2m", 2, "minute")
    MINUTE_5 = ("5m", 5, "minute")
    MINUTE_15 = ("15m", 15, "minute")
    MINUTE_30 = ("30m", 30, "minute")
    MINUTE_60 = ("60m", 60, "minute")
    DAILY = ("D", 1, "day")

    def __init__(self, label: str, value: int, unit: str) -> None:
        """Initialize resolution with label, value, and unit."""
        self.label = label
        self.value = value
        self.unit = unit


class PriceDataLoader:
    """Loads and aggregates price data from parquet files.

    Attributes:
        second_path: Path to second-level parquet files.
        minute_path: Path to minute-level parquet files.
        daily_path: Path to daily-level parquet files.
    """

    def __init__(
        self,
        second_path: Path | None = None,
        minute_path: Path | None = None,
        daily_path: Path | None = None,
    ) -> None:
        """Initialize loader with data paths.

        Args:
            second_path: Path to second-level data directory.
            minute_path: Path to minute-level data directory.
            daily_path: Path to daily-level data directory.
        """
        self.second_path = second_path or Path(r"d:\Second-Level")
        self.minute_path = minute_path or Path(r"d:\Minute-Level")
        self.daily_path = daily_path or Path(r"d:\Daily-Level")

    def load(
        self,
        ticker: str,
        date: str,
        resolution: Resolution,
    ) -> pd.DataFrame | None:
        """Load price data for a ticker and date at specified resolution.

        Args:
            ticker: Stock ticker symbol.
            date: Date string in YYYY-MM-DD format.
            resolution: Desired chart resolution.

        Returns:
            DataFrame with columns [datetime, open, high, low, close, volume],
            or None if data not available.
        """
        # Determine source file based on resolution
        if resolution.unit == "second":
            base_path = self.second_path
            source_resolution = Resolution.SECOND_1
        elif resolution.unit == "minute":
            base_path = self.minute_path
            source_resolution = Resolution.MINUTE_1
        else:  # daily
            base_path = self.daily_path
            source_resolution = Resolution.DAILY

        file_path = base_path / f"{date}.parquet"

        if not file_path.exists():
            logger.warning("Price data file not found: %s", file_path)
            return None

        try:
            df = pd.read_parquet(file_path)
        except Exception as e:
            logger.error("Failed to load price data: %s", e)
            return None

        # Filter to ticker
        ticker_col = self._find_ticker_column(df)
        if ticker_col is None:
            logger.warning("No ticker column found in %s", file_path)
            return None

        df = df[df[ticker_col] == ticker].copy()

        if df.empty:
            logger.warning("No data for ticker %s in %s", ticker, file_path)
            return None

        # Normalize column names
        df = self._normalize_columns(df)

        # Aggregate if needed
        if resolution != source_resolution and resolution.unit != "day":
            df = self._aggregate(df, resolution)

        return df[["datetime", "open", "high", "low", "close", "volume"]].reset_index(drop=True)

    def _find_ticker_column(self, df: pd.DataFrame) -> str | None:
        """Find the ticker column in the DataFrame."""
        for col in ["ticker", "Ticker", "symbol", "Symbol", "TICKER", "SYMBOL"]:
            if col in df.columns:
                return col
        return None

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to lowercase standard names."""
        column_map = {}
        for col in df.columns:
            lower = col.lower()
            if lower in ["datetime", "date", "time", "timestamp"]:
                column_map[col] = "datetime"
            elif lower in ["open", "o"]:
                column_map[col] = "open"
            elif lower in ["high", "h"]:
                column_map[col] = "high"
            elif lower in ["low", "l"]:
                column_map[col] = "low"
            elif lower in ["close", "c"]:
                column_map[col] = "close"
            elif lower in ["volume", "vol", "v"]:
                column_map[col] = "volume"

        df = df.rename(columns=column_map)

        # Ensure datetime is datetime type
        if "datetime" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["datetime"]):
            df["datetime"] = pd.to_datetime(df["datetime"])

        return df

    def _aggregate(self, df: pd.DataFrame, resolution: Resolution) -> pd.DataFrame:
        """Aggregate data to the specified resolution.

        Args:
            df: Source DataFrame with 1-second or 1-minute bars.
            resolution: Target resolution.

        Returns:
            Aggregated DataFrame.
        """
        # Set datetime as index for resampling
        df = df.set_index("datetime").sort_index()

        # Determine resample rule
        if resolution.unit == "second":
            rule = f"{resolution.value}s"
        else:  # minute
            rule = f"{resolution.value}min"

        # Resample OHLCV
        agg_dict = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }

        df = df.resample(rule).agg(agg_dict).dropna()
        df = df.reset_index()

        return df
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_price_data.py::TestPriceDataLoader::test_load_minute_data_returns_dataframe -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/price_data.py tests/unit/test_price_data.py
git commit -m "feat(chart-viewer): add PriceDataLoader with minute data support"
```

---

## Task 2: Price Data Aggregation

**Files:**
- Modify: `src/core/price_data.py`
- Modify: `tests/unit/test_price_data.py`

**Step 1: Write the failing test for aggregation**

```python
# Add to tests/unit/test_price_data.py

    def test_aggregate_to_5_minute_bars(self, tmp_path: Path) -> None:
        """Aggregate 1-minute data to 5-minute bars."""
        # Create 10 minutes of data
        times = pd.date_range("2024-01-15 09:30", periods=10, freq="1min")
        df = pd.DataFrame({
            "ticker": ["AAPL"] * 10,
            "datetime": times,
            "open": [100.0 + i for i in range(10)],
            "high": [101.0 + i for i in range(10)],
            "low": [99.0 + i for i in range(10)],
            "close": [100.5 + i for i in range(10)],
            "volume": [1000] * 10,
        })
        parquet_path = tmp_path / "2024-01-15.parquet"
        df.to_parquet(parquet_path)

        loader = PriceDataLoader(minute_path=tmp_path)
        result = loader.load("AAPL", "2024-01-15", Resolution.MINUTE_5)

        assert len(result) == 2  # 10 minutes -> 2 five-minute bars
        # First bar: 09:30-09:34
        assert result.iloc[0]["open"] == 100.0  # First open
        assert result.iloc[0]["high"] == 105.0  # Max high of first 5 bars
        assert result.iloc[0]["low"] == 99.0  # Min low of first 5 bars
        assert result.iloc[0]["close"] == 104.5  # Last close
        assert result.iloc[0]["volume"] == 5000  # Sum of volumes
```

**Step 2: Run test to verify it fails or passes**

Run: `pytest tests/unit/test_price_data.py::TestPriceDataLoader::test_aggregate_to_5_minute_bars -v`
Expected: Should PASS if implementation is correct, otherwise fix aggregation logic

**Step 3: Commit if passing**

```bash
git add tests/unit/test_price_data.py
git commit -m "test(chart-viewer): add aggregation test for 5-minute bars"
```

---

## Task 3: Exit Simulator Core

**Files:**
- Create: `src/core/exit_simulator.py`
- Test: `tests/unit/test_exit_simulator.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_exit_simulator.py
"""Tests for exit simulation logic."""

import pandas as pd
import pytest
from datetime import datetime

from src.core.exit_simulator import ExitSimulator, ExitEvent, ScalingConfig


class TestExitSimulator:
    """Tests for ExitSimulator class."""

    def test_profit_target_hit_scales_out(self) -> None:
        """When price hits profit target, scale out configured percentage."""
        # Price bars: entry at 100, then rises to hit 135% target
        bars = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",
                "2024-01-15 09:34",
            ]),
            "open": [100.0, 110.0, 130.0],
            "high": [105.0, 120.0, 140.0],  # 140 hits 35% target
            "low": [98.0, 108.0, 125.0],
            "close": [102.0, 115.0, 138.0],
        })

        config = ScalingConfig(scale_pct=50, profit_target_pct=35)
        simulator = ExitSimulator(
            entry_price=100.0,
            entry_time=datetime(2024, 1, 15, 9, 32),
            stop_level=95.0,
            scaling_config=config,
            session_close_time="16:00",
        )

        exits = simulator.simulate(bars)

        assert len(exits) == 1
        assert exits[0].reason == "profit_target"
        assert exits[0].price == 135.0  # Exactly at target
        assert exits[0].pct == 50
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_exit_simulator.py::TestExitSimulator::test_profit_target_hit_scales_out -v`
Expected: FAIL with "No module named 'src.core.exit_simulator'"

**Step 3: Write minimal implementation**

```python
# src/core/exit_simulator.py
"""Exit simulation logic for Chart Viewer.

Calculates exit points based on entry price, stop level, and scaling configuration.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, time

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ScalingConfig:
    """Configuration for trade scaling/exit rules.

    Attributes:
        scale_pct: Percentage of position to exit at profit target.
        profit_target_pct: Profit percentage to trigger scale-out.
    """

    scale_pct: float = 50.0
    profit_target_pct: float = 35.0


@dataclass
class ExitEvent:
    """Represents a single exit event.

    Attributes:
        time: Datetime of the exit.
        price: Exit price.
        pct: Percentage of original position exited.
        reason: Reason for exit (profit_target, stop_hit, session_close).
    """

    time: datetime
    price: float
    pct: float
    reason: str


class ExitSimulator:
    """Simulates trade exits based on price action and scaling rules.

    Attributes:
        entry_price: Entry price of the trade.
        entry_time: Entry time of the trade.
        stop_level: Stop loss price level.
        scaling_config: Configuration for scaling exits.
        session_close_time: Time when session closes (HH:MM format).
    """

    def __init__(
        self,
        entry_price: float,
        entry_time: datetime,
        stop_level: float,
        scaling_config: ScalingConfig,
        session_close_time: str = "16:00",
    ) -> None:
        """Initialize the exit simulator.

        Args:
            entry_price: Entry price of the trade.
            entry_time: Entry time of the trade.
            stop_level: Stop loss price level.
            scaling_config: Configuration for scaling exits.
            session_close_time: Session close time in HH:MM format.
        """
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.stop_level = stop_level
        self.scaling_config = scaling_config

        # Parse session close time
        close_parts = session_close_time.split(":")
        self.session_close = time(int(close_parts[0]), int(close_parts[1]))

        # Calculate profit target price
        self.profit_target_price = entry_price * (1 + scaling_config.profit_target_pct / 100)

        # Determine if long or short based on stop level
        self.is_long = stop_level < entry_price

    def simulate(self, bars: pd.DataFrame) -> list[ExitEvent]:
        """Simulate exits based on price bars.

        Args:
            bars: DataFrame with columns [datetime, open, high, low, close].

        Returns:
            List of ExitEvent objects representing each exit.
        """
        exits: list[ExitEvent] = []
        remaining_pct = 100.0
        scaled_out = False

        for _, bar in bars.iterrows():
            bar_time = bar["datetime"]
            if isinstance(bar_time, pd.Timestamp):
                bar_time = bar_time.to_pydatetime()

            # Skip bars before entry
            if bar_time < self.entry_time:
                continue

            # Check for stop hit
            if self.is_long and bar["low"] <= self.stop_level:
                exits.append(ExitEvent(
                    time=bar_time,
                    price=self.stop_level,
                    pct=remaining_pct,
                    reason="stop_hit",
                ))
                return exits

            if not self.is_long and bar["high"] >= self.stop_level:
                exits.append(ExitEvent(
                    time=bar_time,
                    price=self.stop_level,
                    pct=remaining_pct,
                    reason="stop_hit",
                ))
                return exits

            # Check for profit target (only if not already scaled out)
            if not scaled_out:
                if self.is_long and bar["high"] >= self.profit_target_price:
                    exits.append(ExitEvent(
                        time=bar_time,
                        price=self.profit_target_price,
                        pct=self.scaling_config.scale_pct,
                        reason="profit_target",
                    ))
                    remaining_pct -= self.scaling_config.scale_pct
                    scaled_out = True

                if not self.is_long and bar["low"] <= self.profit_target_price:
                    exits.append(ExitEvent(
                        time=bar_time,
                        price=self.profit_target_price,
                        pct=self.scaling_config.scale_pct,
                        reason="profit_target",
                    ))
                    remaining_pct -= self.scaling_config.scale_pct
                    scaled_out = True

            # Check for session close
            if bar_time.time() >= self.session_close:
                if remaining_pct > 0:
                    exits.append(ExitEvent(
                        time=bar_time,
                        price=bar["close"],
                        pct=remaining_pct,
                        reason="session_close",
                    ))
                return exits

        return exits
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_exit_simulator.py::TestExitSimulator::test_profit_target_hit_scales_out -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/core/exit_simulator.py tests/unit/test_exit_simulator.py
git commit -m "feat(chart-viewer): add ExitSimulator with profit target scaling"
```

---

## Task 4: Exit Simulator - Stop Hit and Session Close

**Files:**
- Modify: `tests/unit/test_exit_simulator.py`

**Step 1: Write failing tests for stop hit and session close**

```python
# Add to tests/unit/test_exit_simulator.py

    def test_stop_hit_exits_full_position(self) -> None:
        """When price hits stop, exit entire remaining position."""
        bars = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 09:33",
            ]),
            "open": [100.0, 98.0],
            "high": [102.0, 99.0],
            "low": [99.0, 94.0],  # 94 hits stop at 95
            "close": [98.0, 95.0],
        })

        config = ScalingConfig(scale_pct=50, profit_target_pct=35)
        simulator = ExitSimulator(
            entry_price=100.0,
            entry_time=datetime(2024, 1, 15, 9, 32),
            stop_level=95.0,
            scaling_config=config,
            session_close_time="16:00",
        )

        exits = simulator.simulate(bars)

        assert len(exits) == 1
        assert exits[0].reason == "stop_hit"
        assert exits[0].price == 95.0
        assert exits[0].pct == 100

    def test_session_close_exits_remaining(self) -> None:
        """At session close, exit remaining position."""
        bars = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 15:59",
                "2024-01-15 16:00",
            ]),
            "open": [100.0, 105.0, 106.0],
            "high": [102.0, 107.0, 108.0],
            "low": [99.0, 104.0, 105.0],
            "close": [101.0, 106.0, 107.0],
        })

        config = ScalingConfig(scale_pct=50, profit_target_pct=35)
        simulator = ExitSimulator(
            entry_price=100.0,
            entry_time=datetime(2024, 1, 15, 9, 32),
            stop_level=95.0,
            scaling_config=config,
            session_close_time="16:00",
        )

        exits = simulator.simulate(bars)

        assert len(exits) == 1
        assert exits[0].reason == "session_close"
        assert exits[0].price == 107.0  # Close price at 16:00
        assert exits[0].pct == 100

    def test_profit_target_then_session_close(self) -> None:
        """Profit target hit, then remainder at session close."""
        bars = pd.DataFrame({
            "datetime": pd.to_datetime([
                "2024-01-15 09:32",
                "2024-01-15 10:00",  # Hits 35% target (135)
                "2024-01-15 16:00",
            ]),
            "open": [100.0, 130.0, 132.0],
            "high": [102.0, 140.0, 134.0],  # 140 > 135 target
            "low": [99.0, 128.0, 130.0],
            "close": [101.0, 138.0, 133.0],
        })

        config = ScalingConfig(scale_pct=50, profit_target_pct=35)
        simulator = ExitSimulator(
            entry_price=100.0,
            entry_time=datetime(2024, 1, 15, 9, 32),
            stop_level=95.0,
            scaling_config=config,
            session_close_time="16:00",
        )

        exits = simulator.simulate(bars)

        assert len(exits) == 2
        assert exits[0].reason == "profit_target"
        assert exits[0].pct == 50
        assert exits[1].reason == "session_close"
        assert exits[1].pct == 50
        assert exits[1].price == 133.0
```

**Step 2: Run tests**

Run: `pytest tests/unit/test_exit_simulator.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add tests/unit/test_exit_simulator.py
git commit -m "test(chart-viewer): add stop hit and session close tests"
```

---

## Task 5: Trade Browser Widget

**Files:**
- Create: `src/ui/components/trade_browser.py`
- Test: `tests/unit/test_trade_browser.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_trade_browser.py
"""Tests for Trade Browser widget."""

import pandas as pd
import pytest
from datetime import datetime
from unittest.mock import MagicMock

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.ui.components.trade_browser import TradeBrowser


@pytest.fixture
def qapp():
    """Create QApplication for widget tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def sample_trades() -> pd.DataFrame:
    """Sample filtered trades DataFrame."""
    return pd.DataFrame({
        "ticker": ["AAPL", "MSFT", "TSLA"],
        "entry_time": pd.to_datetime(["2024-01-15 09:32", "2024-01-15 09:45", "2024-01-15 10:00"]),
        "entry_price": [185.0, 400.0, 250.0],
        "date": ["2024-01-15", "2024-01-15", "2024-01-15"],
        "pnl_pct": [2.3, -1.5, 3.1],
    })


class TestTradeBrowser:
    """Tests for TradeBrowser widget."""

    def test_set_trades_populates_list(self, qapp, sample_trades: pd.DataFrame) -> None:
        """Setting trades populates the list widget."""
        browser = TradeBrowser()
        browser.set_trades(sample_trades)

        assert browser.trade_list.count() == 3

    def test_trade_selected_signal_emitted(self, qapp, sample_trades: pd.DataFrame) -> None:
        """Selecting a trade emits signal with trade data."""
        browser = TradeBrowser()
        browser.set_trades(sample_trades)

        signal_received = []
        browser.trade_selected.connect(lambda data: signal_received.append(data))

        # Select first item
        browser.trade_list.setCurrentRow(0)

        assert len(signal_received) == 1
        assert signal_received[0]["ticker"] == "AAPL"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_trade_browser.py::TestTradeBrowser::test_set_trades_populates_list -v`
Expected: FAIL with "No module named 'src.ui.components.trade_browser'"

**Step 3: Write minimal implementation**

```python
# src/ui/components/trade_browser.py
"""Trade Browser widget for Chart Viewer.

Displays a list of filtered trades with navigation controls.
"""

import logging
from typing import Any

import pandas as pd
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.constants import Colors, Fonts, Spacing

logger = logging.getLogger(__name__)


class TradeBrowser(QWidget):
    """Widget for browsing filtered trades.

    Signals:
        trade_selected: Emitted when a trade is selected, with trade data dict.
    """

    trade_selected = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the trade browser widget.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._trades_df: pd.DataFrame | None = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_TERTIARY};
                border-bottom: 1px solid {Colors.BORDER_SUBTLE};
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)

        title = QLabel("Trade Browser")
        title.setStyleSheet(f"""
            QLabel {{
                font-family: {Fonts.UI};
                font-size: 11px;
                font-weight: 600;
                color: {Colors.TEXT_SECONDARY};
                text-transform: uppercase;
                letter-spacing: 0.8px;
            }}
        """)
        header_layout.addWidget(title)

        self._count_label = QLabel("0 trades")
        self._count_label.setStyleSheet(f"""
            QLabel {{
                font-family: {Fonts.DATA};
                font-size: 10px;
                font-weight: 600;
                color: {Colors.TEXT_TERTIARY};
                background-color: {Colors.BG_PRIMARY};
                padding: 2px 6px;
                border-radius: 3px;
            }}
        """)
        header_layout.addWidget(self._count_label)

        layout.addWidget(header)

        # Trade list
        self.trade_list = QListWidget()
        self.trade_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {Colors.BG_SECONDARY};
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                padding: {Spacing.SM}px {Spacing.MD}px;
                border: 1px solid transparent;
                border-radius: 4px;
                margin: 2px {Spacing.SM}px;
            }}
            QListWidget::item:hover {{
                background-color: {Colors.HOVER_OVERLAY};
            }}
            QListWidget::item:selected {{
                background-color: {Colors.SELECTED_BG};
                border-color: {Colors.SELECTED_BORDER};
            }}
        """)
        layout.addWidget(self.trade_list, 1)

        # Navigation buttons
        nav = QWidget()
        nav.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_TERTIARY};
                border-top: 1px solid {Colors.BORDER_SUBTLE};
            }}
        """)
        nav_layout = QHBoxLayout(nav)
        nav_layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        nav_layout.setSpacing(Spacing.SM)

        self._prev_btn = QPushButton("< Prev")
        self._next_btn = QPushButton("Next >")

        for btn in [self._prev_btn, self._next_btn]:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.BG_ELEVATED};
                    border: 1px solid {Colors.BORDER_SUBTLE};
                    border-radius: 4px;
                    color: {Colors.TEXT_SECONDARY};
                    font-family: {Fonts.UI};
                    font-size: 12px;
                    font-weight: 500;
                    padding: {Spacing.SM}px {Spacing.MD}px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.BG_PRIMARY};
                    border-color: {Colors.BORDER_MEDIUM};
                    color: {Colors.TEXT_PRIMARY};
                }}
            """)
            nav_layout.addWidget(btn)

        layout.addWidget(nav)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.trade_list.currentRowChanged.connect(self._on_selection_changed)
        self._prev_btn.clicked.connect(self._on_prev_clicked)
        self._next_btn.clicked.connect(self._on_next_clicked)

    def set_trades(self, df: pd.DataFrame) -> None:
        """Set the trades to display.

        Args:
            df: DataFrame with trade data. Expected columns: ticker, entry_time,
                entry_price, date, pnl_pct.
        """
        self._trades_df = df.copy()
        self.trade_list.clear()

        for _, row in df.iterrows():
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, row.to_dict())

            # Format display text
            ticker = row.get("ticker", "???")
            time_str = ""
            if "entry_time" in row:
                entry_time = row["entry_time"]
                if hasattr(entry_time, "strftime"):
                    time_str = entry_time.strftime("%H:%M")
            pnl = row.get("pnl_pct", 0)
            pnl_str = f"+{pnl:.1f}%" if pnl >= 0 else f"{pnl:.1f}%"

            item.setText(f"{ticker}  {time_str}  {pnl_str}")
            self.trade_list.addItem(item)

        self._count_label.setText(f"{len(df)} trades")

    def _on_selection_changed(self, row: int) -> None:
        """Handle trade selection change."""
        if row < 0:
            return
        item = self.trade_list.item(row)
        if item:
            trade_data = item.data(Qt.ItemDataRole.UserRole)
            self.trade_selected.emit(trade_data)

    def _on_prev_clicked(self) -> None:
        """Navigate to previous trade."""
        current = self.trade_list.currentRow()
        if current > 0:
            self.trade_list.setCurrentRow(current - 1)

    def _on_next_clicked(self) -> None:
        """Navigate to next trade."""
        current = self.trade_list.currentRow()
        if current < self.trade_list.count() - 1:
            self.trade_list.setCurrentRow(current + 1)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_trade_browser.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/ui/components/trade_browser.py tests/unit/test_trade_browser.py
git commit -m "feat(chart-viewer): add TradeBrowser widget"
```

---

## Task 6: Candlestick Chart Widget

**Files:**
- Create: `src/ui/components/candlestick_chart.py`
- Test: `tests/unit/test_candlestick_chart.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_candlestick_chart.py
"""Tests for Candlestick Chart widget."""

import pandas as pd
import pytest
from datetime import datetime

from PyQt6.QtWidgets import QApplication

from src.ui.components.candlestick_chart import CandlestickChart
from src.core.exit_simulator import ExitEvent


@pytest.fixture
def qapp():
    """Create QApplication for widget tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def sample_bars() -> pd.DataFrame:
    """Sample price bars."""
    return pd.DataFrame({
        "datetime": pd.to_datetime([
            "2024-01-15 09:30",
            "2024-01-15 09:31",
            "2024-01-15 09:32",
        ]),
        "open": [100.0, 101.0, 102.0],
        "high": [102.0, 103.0, 104.0],
        "low": [99.0, 100.0, 101.0],
        "close": [101.0, 102.0, 103.0],
        "volume": [1000, 1100, 1200],
    })


class TestCandlestickChart:
    """Tests for CandlestickChart widget."""

    def test_set_data_renders_candles(self, qapp, sample_bars: pd.DataFrame) -> None:
        """Setting data renders candlesticks on the chart."""
        chart = CandlestickChart()
        chart.set_data(sample_bars)

        # Verify candle items exist
        assert chart._candle_item is not None

    def test_set_markers_adds_entry_exit(self, qapp, sample_bars: pd.DataFrame) -> None:
        """Setting markers adds entry and exit points."""
        chart = CandlestickChart()
        chart.set_data(sample_bars)

        exits = [
            ExitEvent(
                time=datetime(2024, 1, 15, 9, 32),
                price=103.0,
                pct=100,
                reason="session_close",
            )
        ]

        chart.set_markers(
            entry_time=datetime(2024, 1, 15, 9, 30),
            entry_price=100.0,
            exits=exits,
            stop_level=95.0,
            profit_target=135.0,
        )

        # Verify marker items exist
        assert len(chart._marker_items) > 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_candlestick_chart.py -v`
Expected: FAIL with "No module named 'src.ui.components.candlestick_chart'"

**Step 3: Write minimal implementation**

```python
# src/ui/components/candlestick_chart.py
"""Candlestick chart widget for Chart Viewer.

Displays OHLC candlesticks with trade markers using pyqtgraph.
"""

import logging
from datetime import datetime

import numpy as np
import pandas as pd
import pyqtgraph as pg  # type: ignore[import-untyped]
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from src.core.exit_simulator import ExitEvent
from src.ui.constants import Colors

logger = logging.getLogger(__name__)


class CandlestickItem(pg.GraphicsObject):
    """Custom pyqtgraph item for rendering candlesticks."""

    def __init__(self) -> None:
        """Initialize the candlestick item."""
        super().__init__()
        self._data: np.ndarray | None = None
        self._picture: pg.QtGui.QPicture | None = None

    def set_data(self, data: np.ndarray) -> None:
        """Set candlestick data.

        Args:
            data: Array with columns [time_idx, open, high, low, close].
        """
        self._data = data
        self._picture = None
        self.prepareGeometryChange()
        self.update()

    def paint(self, painter, option, widget) -> None:
        """Paint the candlesticks."""
        if self._data is None or len(self._data) == 0:
            return

        if self._picture is None:
            self._generate_picture()

        if self._picture is not None:
            self._picture.play(painter)

    def _generate_picture(self) -> None:
        """Generate the picture for painting."""
        self._picture = pg.QtGui.QPicture()
        painter = pg.QtGui.QPainter(self._picture)

        green = QColor(Colors.ACCENT_PROFIT)
        red = QColor(Colors.ACCENT_LOSS)

        width = 0.6

        for row in self._data:
            t, o, h, l, c = row[:5]

            if c >= o:
                color = green
            else:
                color = red

            painter.setPen(pg.mkPen(color))
            painter.setBrush(pg.mkBrush(color))

            # Draw wick
            painter.drawLine(
                pg.QtCore.QPointF(t, l),
                pg.QtCore.QPointF(t, h),
            )

            # Draw body
            body_top = max(o, c)
            body_bottom = min(o, c)
            body_height = max(body_top - body_bottom, 0.001)

            painter.drawRect(
                pg.QtCore.QRectF(
                    t - width / 2,
                    body_bottom,
                    width,
                    body_height,
                )
            )

        painter.end()

    def boundingRect(self):
        """Return the bounding rectangle."""
        if self._data is None or len(self._data) == 0:
            return pg.QtCore.QRectF()

        t = self._data[:, 0]
        h = self._data[:, 2]
        l = self._data[:, 3]

        return pg.QtCore.QRectF(
            t.min() - 1,
            l.min(),
            t.max() - t.min() + 2,
            h.max() - l.min(),
        )


class CandlestickChart(QWidget):
    """Widget displaying candlestick chart with trade markers.

    Attributes:
        _plot_widget: The pyqtgraph PlotWidget.
        _candle_item: The candlestick graphics item.
        _marker_items: List of marker graphics items.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the candlestick chart.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._bars_df: pd.DataFrame | None = None
        self._time_index: dict[datetime, int] = {}
        self._candle_item: CandlestickItem | None = None
        self._marker_items: list = []
        self._level_items: list = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create plot widget
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setBackground(Colors.BG_PRIMARY)
        self._plot_widget.showGrid(x=True, y=True, alpha=0.2)

        # Configure axes
        self._plot_widget.setLabel("left", "Price")
        self._plot_widget.setLabel("bottom", "Time")

        layout.addWidget(self._plot_widget)

        # Create candlestick item
        self._candle_item = CandlestickItem()
        self._plot_widget.addItem(self._candle_item)

    def set_data(self, df: pd.DataFrame) -> None:
        """Set the price data to display.

        Args:
            df: DataFrame with columns [datetime, open, high, low, close, volume].
        """
        self._bars_df = df.copy()
        self._clear_markers()

        # Build time index mapping
        self._time_index = {
            dt: idx for idx, dt in enumerate(df["datetime"])
        }

        # Convert to numpy array for candlestick item
        data = np.column_stack([
            np.arange(len(df)),
            df["open"].values,
            df["high"].values,
            df["low"].values,
            df["close"].values,
        ])

        self._candle_item.set_data(data)
        self._plot_widget.autoRange()

    def set_markers(
        self,
        entry_time: datetime,
        entry_price: float,
        exits: list[ExitEvent],
        stop_level: float,
        profit_target: float,
    ) -> None:
        """Set trade markers on the chart.

        Args:
            entry_time: Entry time.
            entry_price: Entry price.
            exits: List of exit events.
            stop_level: Stop loss level.
            profit_target: Profit target level.
        """
        self._clear_markers()

        # Get time indices
        entry_idx = self._get_time_index(entry_time)

        # Entry marker
        entry_marker = pg.ScatterPlotItem(
            [entry_idx],
            [entry_price],
            symbol="t",  # Triangle up
            size=15,
            brush=pg.mkBrush(Colors.ACCENT_ENTRY),
            pen=pg.mkPen(None),
        )
        self._plot_widget.addItem(entry_marker)
        self._marker_items.append(entry_marker)

        # Exit markers
        for exit_event in exits:
            exit_idx = self._get_time_index(exit_event.time)
            exit_marker = pg.ScatterPlotItem(
                [exit_idx],
                [exit_event.price],
                symbol="t1",  # Triangle down
                size=15,
                brush=pg.mkBrush(Colors.ACCENT_PROFIT),
                pen=pg.mkPen(None),
            )
            self._plot_widget.addItem(exit_marker)
            self._marker_items.append(exit_marker)

        # Stop level line
        stop_line = pg.InfiniteLine(
            pos=stop_level,
            angle=0,
            pen=pg.mkPen(Colors.ACCENT_LOSS, width=1, style=Qt.PenStyle.DashLine),
        )
        self._plot_widget.addItem(stop_line)
        self._level_items.append(stop_line)

        # Profit target line
        target_line = pg.InfiniteLine(
            pos=profit_target,
            angle=0,
            pen=pg.mkPen(Colors.ACCENT_TARGET, width=1, style=Qt.PenStyle.DashLine),
        )
        self._plot_widget.addItem(target_line)
        self._level_items.append(target_line)

    def _get_time_index(self, dt: datetime) -> int:
        """Get the time index for a datetime.

        Args:
            dt: Datetime to look up.

        Returns:
            Index in the data array.
        """
        if dt in self._time_index:
            return self._time_index[dt]

        # Find closest time
        if isinstance(dt, pd.Timestamp):
            dt = dt.to_pydatetime()

        for key_dt, idx in self._time_index.items():
            if isinstance(key_dt, pd.Timestamp):
                key_dt = key_dt.to_pydatetime()
            if key_dt >= dt:
                return idx

        return len(self._time_index) - 1

    def _clear_markers(self) -> None:
        """Clear all markers from the chart."""
        for item in self._marker_items:
            self._plot_widget.removeItem(item)
        self._marker_items.clear()

        for item in self._level_items:
            self._plot_widget.removeItem(item)
        self._level_items.clear()

    def clear(self) -> None:
        """Clear all data from the chart."""
        self._clear_markers()
        self._candle_item.set_data(np.array([]))
        self._bars_df = None
        self._time_index.clear()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_candlestick_chart.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/ui/components/candlestick_chart.py tests/unit/test_candlestick_chart.py
git commit -m "feat(chart-viewer): add CandlestickChart widget with markers"
```

---

## Task 7: Chart Viewer Tab - Basic Structure

**Files:**
- Create: `src/tabs/chart_viewer.py`
- Test: `tests/unit/test_chart_viewer_tab.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_chart_viewer_tab.py
"""Tests for Chart Viewer tab."""

import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication

from src.core.app_state import AppState
from src.tabs.chart_viewer import ChartViewerTab


@pytest.fixture
def qapp():
    """Create QApplication for widget tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def mock_app_state() -> AppState:
    """Create mock app state."""
    state = AppState()
    state.filtered_df = pd.DataFrame({
        "ticker": ["AAPL", "MSFT"],
        "entry_time": pd.to_datetime(["2024-01-15 09:32", "2024-01-15 09:45"]),
        "entry_price": [185.0, 400.0],
        "date": ["2024-01-15", "2024-01-15"],
        "pnl_pct": [2.3, -1.5],
    })
    state.adjustment_params.stop_loss_percent = 1.5
    return state


class TestChartViewerTab:
    """Tests for ChartViewerTab."""

    def test_tab_initializes(self, qapp, mock_app_state: AppState) -> None:
        """Tab initializes without error."""
        tab = ChartViewerTab(mock_app_state)
        assert tab is not None

    def test_trade_browser_shows_filtered_trades(self, qapp, mock_app_state: AppState) -> None:
        """Trade browser shows trades from filtered_df."""
        tab = ChartViewerTab(mock_app_state)

        # Trigger state update
        mock_app_state.filtered_data_updated.emit(mock_app_state.filtered_df)

        assert tab._trade_browser.trade_list.count() == 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_chart_viewer_tab.py -v`
Expected: FAIL with "No module named 'src.tabs.chart_viewer'"

**Step 3: Write minimal implementation**

```python
# src/tabs/chart_viewer.py
"""Chart Viewer tab for displaying candlestick charts of filtered trades.

Displays price action with entry/exit markers calculated dynamically
based on scaling configuration.
"""

import logging
from datetime import datetime

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.core.app_state import AppState
from src.core.exit_simulator import ExitSimulator, ScalingConfig
from src.core.price_data import PriceDataLoader, Resolution
from src.ui.components.candlestick_chart import CandlestickChart
from src.ui.components.trade_browser import TradeBrowser
from src.ui.constants import Colors, Fonts, Spacing

logger = logging.getLogger(__name__)


class ChartViewerTab(QWidget):
    """Tab for viewing candlestick charts of filtered trades.

    Attributes:
        _app_state: Reference to the centralized application state.
    """

    RESOLUTIONS = [
        ("1 Second", Resolution.SECOND_1),
        ("5 Second", Resolution.SECOND_5),
        ("15 Second", Resolution.SECOND_15),
        ("30 Second", Resolution.SECOND_30),
        ("1 Minute", Resolution.MINUTE_1),
        ("2 Minute", Resolution.MINUTE_2),
        ("5 Minute", Resolution.MINUTE_5),
        ("15 Minute", Resolution.MINUTE_15),
        ("30 Minute", Resolution.MINUTE_30),
        ("60 Minute", Resolution.MINUTE_60),
        ("Daily", Resolution.DAILY),
    ]

    ZOOM_PRESETS = [
        ("Trade Only", 0),
        ("± 15 min", 15),
        ("± 30 min", 30),
        ("± 60 min", 60),
        ("Full Session", -1),
    ]

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        """Initialize the Chart Viewer tab.

        Args:
            app_state: Reference to the centralized application state.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._app_state = app_state
        self._price_loader = PriceDataLoader()
        self._current_trade: dict | None = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # Main content with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {Colors.BORDER_SUBTLE};
                width: 1px;
            }}
        """)

        # Left panel
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)

        # Chart area
        self._chart = CandlestickChart()
        splitter.addWidget(self._chart)

        # Set initial sizes (280px for left panel)
        splitter.setSizes([280, 1000])

        layout.addWidget(splitter, 1)

    def _create_toolbar(self) -> QWidget:
        """Create the toolbar widget."""
        toolbar = QWidget()
        toolbar.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_SECONDARY};
                border-bottom: 1px solid {Colors.BORDER_SUBTLE};
            }}
        """)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        layout.setSpacing(Spacing.XL)

        # Resolution selector
        res_layout = QHBoxLayout()
        res_layout.setSpacing(Spacing.MD)
        res_label = QLabel("Resolution")
        res_label.setStyleSheet(f"""
            QLabel {{
                font-family: {Fonts.UI};
                font-size: 11px;
                font-weight: 500;
                color: {Colors.TEXT_TERTIARY};
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
        """)
        res_layout.addWidget(res_label)

        self._resolution_combo = QComboBox()
        for label, _ in self.RESOLUTIONS:
            self._resolution_combo.addItem(label)
        self._resolution_combo.setCurrentIndex(4)  # Default to 1 Minute
        self._style_combo(self._resolution_combo)
        res_layout.addWidget(self._resolution_combo)
        layout.addLayout(res_layout)

        # Zoom selector
        zoom_layout = QHBoxLayout()
        zoom_layout.setSpacing(Spacing.MD)
        zoom_label = QLabel("Zoom")
        zoom_label.setStyleSheet(res_label.styleSheet())
        zoom_layout.addWidget(zoom_label)

        self._zoom_combo = QComboBox()
        for label, _ in self.ZOOM_PRESETS:
            self._zoom_combo.addItem(label)
        self._zoom_combo.setCurrentIndex(2)  # Default to ± 30 min
        self._style_combo(self._zoom_combo)
        zoom_layout.addWidget(self._zoom_combo)
        layout.addLayout(zoom_layout)

        # Trade info box (right side)
        layout.addStretch()
        self._trade_info = self._create_trade_info()
        layout.addWidget(self._trade_info)

        return toolbar

    def _create_trade_info(self) -> QWidget:
        """Create the trade info box."""
        box = QWidget()
        box.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_SUBTLE};
                border-radius: 4px;
            }}
        """)

        layout = QHBoxLayout(box)
        layout.setContentsMargins(Spacing.LG, Spacing.SM, Spacing.LG, Spacing.SM)
        layout.setSpacing(Spacing.LG)

        self._ticker_label = QLabel("---")
        self._date_label = QLabel("---")
        self._entry_label = QLabel("---")
        self._pnl_label = QLabel("---")

        for label in [self._ticker_label, self._date_label, self._entry_label, self._pnl_label]:
            label.setStyleSheet(f"""
                QLabel {{
                    font-family: {Fonts.DATA};
                    font-size: 12px;
                    color: {Colors.TEXT_PRIMARY};
                }}
            """)
            layout.addWidget(label)

        return box

    def _create_left_panel(self) -> QWidget:
        """Create the left panel with trade browser and scaling config."""
        panel = QWidget()
        panel.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_SECONDARY};
            }}
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Trade browser
        self._trade_browser = TradeBrowser()
        layout.addWidget(self._trade_browser, 1)

        # Scaling config
        scaling = self._create_scaling_config()
        layout.addWidget(scaling)

        return panel

    def _create_scaling_config(self) -> QWidget:
        """Create the scaling configuration panel."""
        panel = QWidget()
        panel.setStyleSheet(f"""
            QWidget {{
                border-top: 1px solid {Colors.BORDER_SUBTLE};
            }}
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_TERTIARY};
                border-bottom: 1px solid {Colors.BORDER_SUBTLE};
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        title = QLabel("Scaling Config")
        title.setStyleSheet(f"""
            QLabel {{
                font-family: {Fonts.UI};
                font-size: 11px;
                font-weight: 600;
                color: {Colors.TEXT_SECONDARY};
                text-transform: uppercase;
                letter-spacing: 0.8px;
            }}
        """)
        header_layout.addWidget(title)
        layout.addWidget(header)

        # Config inputs
        config = QWidget()
        config_layout = QHBoxLayout(config)
        config_layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        config_layout.setSpacing(Spacing.SM)

        label_style = f"""
            QLabel {{
                font-family: {Fonts.UI};
                font-size: 12px;
                color: {Colors.TEXT_SECONDARY};
            }}
        """

        config_layout.addWidget(QLabel("Exit"))
        config_layout.itemAt(0).widget().setStyleSheet(label_style)

        self._scale_pct_spin = QDoubleSpinBox()
        self._scale_pct_spin.setRange(0, 100)
        self._scale_pct_spin.setValue(50)
        self._scale_pct_spin.setSuffix("%")
        self._style_spin(self._scale_pct_spin)
        config_layout.addWidget(self._scale_pct_spin)

        at_label = QLabel("at")
        at_label.setStyleSheet(label_style)
        config_layout.addWidget(at_label)

        self._profit_target_spin = QDoubleSpinBox()
        self._profit_target_spin.setRange(0, 100)
        self._profit_target_spin.setValue(35)
        self._profit_target_spin.setSuffix("%")
        self._style_spin(self._profit_target_spin)
        config_layout.addWidget(self._profit_target_spin)

        profit_label = QLabel("profit")
        profit_label.setStyleSheet(label_style)
        config_layout.addWidget(profit_label)

        config_layout.addStretch()
        layout.addWidget(config)

        return panel

    def _style_combo(self, combo: QComboBox) -> None:
        """Apply standard styling to a combo box."""
        combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {Colors.BG_TERTIARY};
                border: 1px solid {Colors.BORDER_SUBTLE};
                border-radius: 4px;
                padding: {Spacing.SM}px {Spacing.MD}px;
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.DATA};
                font-size: 12px;
                min-width: 100px;
            }}
            QComboBox:hover {{
                border-color: {Colors.BORDER_MEDIUM};
                background-color: {Colors.BG_ELEVATED};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
        """)

    def _style_spin(self, spin: QDoubleSpinBox) -> None:
        """Apply standard styling to a spin box."""
        spin.setStyleSheet(f"""
            QDoubleSpinBox {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER_SUBTLE};
                border-radius: 3px;
                padding: {Spacing.XS}px {Spacing.SM}px;
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.DATA};
                font-size: 12px;
                min-width: 60px;
            }}
            QDoubleSpinBox:hover {{
                border-color: {Colors.BORDER_MEDIUM};
            }}
        """)

    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        # App state signals
        self._app_state.filtered_data_updated.connect(self._on_filtered_data_updated)

        # Trade browser signals
        self._trade_browser.trade_selected.connect(self._on_trade_selected)

        # Control signals
        self._resolution_combo.currentIndexChanged.connect(self._on_settings_changed)
        self._zoom_combo.currentIndexChanged.connect(self._on_settings_changed)
        self._scale_pct_spin.valueChanged.connect(self._on_settings_changed)
        self._profit_target_spin.valueChanged.connect(self._on_settings_changed)

    def _on_filtered_data_updated(self, df: pd.DataFrame) -> None:
        """Handle filtered data update."""
        if df is None or df.empty:
            return

        self._trade_browser.set_trades(df)

    def _on_trade_selected(self, trade_data: dict) -> None:
        """Handle trade selection."""
        self._current_trade = trade_data
        self._update_trade_info(trade_data)
        self._load_and_display_chart()

    def _update_trade_info(self, trade_data: dict) -> None:
        """Update the trade info display."""
        self._ticker_label.setText(trade_data.get("ticker", "---"))
        self._date_label.setText(str(trade_data.get("date", "---")))

        entry_price = trade_data.get("entry_price", 0)
        entry_time = trade_data.get("entry_time", "")
        if hasattr(entry_time, "strftime"):
            entry_time = entry_time.strftime("%H:%M")
        self._entry_label.setText(f"${entry_price:.2f} @ {entry_time}")

        pnl = trade_data.get("pnl_pct", 0)
        pnl_str = f"+{pnl:.1f}%" if pnl >= 0 else f"{pnl:.1f}%"
        color = Colors.ACCENT_PROFIT if pnl >= 0 else Colors.ACCENT_LOSS
        self._pnl_label.setText(pnl_str)
        self._pnl_label.setStyleSheet(f"""
            QLabel {{
                font-family: {Fonts.DATA};
                font-size: 12px;
                color: {color};
                font-weight: 600;
            }}
        """)

    def _load_and_display_chart(self) -> None:
        """Load price data and display the chart."""
        if self._current_trade is None:
            return

        ticker = self._current_trade.get("ticker")
        date = str(self._current_trade.get("date", ""))
        entry_time = self._current_trade.get("entry_time")
        entry_price = self._current_trade.get("entry_price", 0)

        if not ticker or not date:
            return

        # Get resolution
        res_idx = self._resolution_combo.currentIndex()
        resolution = self.RESOLUTIONS[res_idx][1]

        # Load price data
        bars = self._price_loader.load(ticker, date, resolution)

        if bars is None or bars.empty:
            logger.warning("No price data for %s on %s", ticker, date)
            return

        # Apply zoom
        zoom_idx = self._zoom_combo.currentIndex()
        zoom_minutes = self.ZOOM_PRESETS[zoom_idx][1]
        if zoom_minutes > 0 and entry_time is not None:
            bars = self._apply_zoom(bars, entry_time, zoom_minutes)

        # Set chart data
        self._chart.set_data(bars)

        # Simulate exits
        if entry_time is not None and entry_price > 0:
            self._simulate_and_display_exits(bars, entry_time, entry_price)

    def _apply_zoom(
        self, bars: pd.DataFrame, entry_time: datetime, minutes: int
    ) -> pd.DataFrame:
        """Apply zoom to price data around entry time.

        Args:
            bars: Full price bars DataFrame.
            entry_time: Trade entry time.
            minutes: Minutes of padding before and after.

        Returns:
            Filtered DataFrame.
        """
        if isinstance(entry_time, pd.Timestamp):
            entry_time = entry_time.to_pydatetime()

        start = pd.Timestamp(entry_time) - pd.Timedelta(minutes=minutes)
        end = pd.Timestamp(entry_time) + pd.Timedelta(minutes=minutes)

        mask = (bars["datetime"] >= start) & (bars["datetime"] <= end)
        return bars[mask].copy()

    def _simulate_and_display_exits(
        self, bars: pd.DataFrame, entry_time: datetime, entry_price: float
    ) -> None:
        """Simulate exits and display markers."""
        # Get stop level from app state
        stop_pct = self._app_state.adjustment_params.stop_loss_percent
        stop_level = entry_price * (1 - stop_pct / 100)

        # Get scaling config
        config = ScalingConfig(
            scale_pct=self._scale_pct_spin.value(),
            profit_target_pct=self._profit_target_spin.value(),
        )

        # Calculate profit target price
        profit_target = entry_price * (1 + config.profit_target_pct / 100)

        # Simulate
        simulator = ExitSimulator(
            entry_price=entry_price,
            entry_time=entry_time if isinstance(entry_time, datetime) else entry_time.to_pydatetime(),
            stop_level=stop_level,
            scaling_config=config,
        )

        exits = simulator.simulate(bars)

        # Display markers
        self._chart.set_markers(
            entry_time=entry_time,
            entry_price=entry_price,
            exits=exits,
            stop_level=stop_level,
            profit_target=profit_target,
        )

    def _on_settings_changed(self) -> None:
        """Handle settings change - reload chart."""
        self._load_and_display_chart()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_chart_viewer_tab.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tabs/chart_viewer.py tests/unit/test_chart_viewer_tab.py
git commit -m "feat(chart-viewer): add ChartViewerTab with core functionality"
```

---

## Task 8: Register Chart Viewer Tab

**Files:**
- Modify: `src/ui/main_window.py:14-26` (imports)
- Modify: `src/ui/main_window.py:66-84` (tabs list)

**Step 1: Add import**

Add to imports in `src/ui/main_window.py`:

```python
from src.tabs.chart_viewer import ChartViewerTab
```

**Step 2: Add tab to dock manager**

In `_setup_docks`, add to the `tabs` list before "Statistics":

```python
("Chart Viewer", ChartViewerTab(self._app_state)),
```

**Step 3: Test manually**

Run: `python -m src.main`
Expected: Chart Viewer tab appears in the dock manager

**Step 4: Commit**

```bash
git add src/ui/main_window.py
git commit -m "feat(chart-viewer): register ChartViewerTab in main window"
```

---

## Task 9: Add "View Chart" Context Menu to Statistics Tab

**Files:**
- Modify: `src/tabs/statistics_tab.py`

**Step 1: Add context menu to tables**

In `_create_table` method, add context menu policy:

```python
table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
table.customContextMenuRequested.connect(
    lambda pos, t=table: self._show_table_context_menu(pos, t)
)
```

**Step 2: Add context menu handler**

Add new method to `StatisticsTab`:

```python
def _show_table_context_menu(self, pos, table: QTableWidget) -> None:
    """Show context menu for table row."""
    item = table.itemAt(pos)
    if item is None:
        return

    row = item.row()
    menu = QMenu(self)

    view_chart_action = menu.addAction("View Chart")
    view_chart_action.triggered.connect(lambda: self._on_view_chart(table, row))

    menu.exec(table.mapToGlobal(pos))

def _on_view_chart(self, table: QTableWidget, row: int) -> None:
    """Handle View Chart action."""
    # Get trade data from row and emit signal to switch to Chart Viewer
    # Implementation depends on how trade data is stored in table
    self._app_state.request_tab_change.emit(-1)  # Signal to switch to Chart Viewer
```

**Step 3: Test manually**

Run: `python -m src.main`
Expected: Right-click on Statistics table shows "View Chart" option

**Step 4: Commit**

```bash
git add src/tabs/statistics_tab.py
git commit -m "feat(chart-viewer): add View Chart context menu to Statistics tab"
```

---

## Task 10: Add VWAP Indicator

**Files:**
- Modify: `src/ui/components/candlestick_chart.py`

**Step 1: Add VWAP calculation method**

```python
def _calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
    """Calculate VWAP from price data.

    Args:
        df: DataFrame with columns [datetime, high, low, close, volume].

    Returns:
        Series with VWAP values.
    """
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    cumulative_tp_vol = (typical_price * df["volume"]).cumsum()
    cumulative_vol = df["volume"].cumsum()
    return cumulative_tp_vol / cumulative_vol
```

**Step 2: Add VWAP line to set_data**

After setting candlestick data:

```python
# Calculate and plot VWAP
if "volume" in df.columns and df["volume"].sum() > 0:
    vwap = self._calculate_vwap(df)
    self._vwap_line = self._plot_widget.plot(
        np.arange(len(df)),
        vwap.values,
        pen=pg.mkPen(Colors.ACCENT_VWAP, width=1.5),
    )
```

**Step 3: Clear VWAP in clear method**

Add to `_clear_markers`:

```python
if hasattr(self, '_vwap_line') and self._vwap_line is not None:
    self._plot_widget.removeItem(self._vwap_line)
    self._vwap_line = None
```

**Step 4: Test manually**

Run: `python -m src.main`
Expected: VWAP line appears on chart

**Step 5: Commit**

```bash
git add src/ui/components/candlestick_chart.py
git commit -m "feat(chart-viewer): add VWAP indicator to candlestick chart"
```

---

## Task 11: Final Integration Test

**Files:**
- Create: `tests/integration/test_chart_viewer_integration.py`

**Step 1: Write integration test**

```python
# tests/integration/test_chart_viewer_integration.py
"""Integration tests for Chart Viewer."""

import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication

from src.core.app_state import AppState
from src.tabs.chart_viewer import ChartViewerTab


@pytest.fixture
def qapp():
    """Create QApplication for widget tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def app_state_with_trades() -> AppState:
    """Create app state with sample trades."""
    state = AppState()
    state.filtered_df = pd.DataFrame({
        "ticker": ["AAPL"],
        "entry_time": pd.to_datetime(["2024-01-15 09:32"]),
        "entry_price": [185.0],
        "date": ["2024-01-15"],
        "pnl_pct": [2.3],
    })
    state.adjustment_params.stop_loss_percent = 1.5
    return state


class TestChartViewerIntegration:
    """Integration tests for Chart Viewer."""

    def test_full_workflow(self, qapp, app_state_with_trades: AppState, tmp_path: Path) -> None:
        """Test full workflow: select trade -> load data -> display chart."""
        # Create mock price data
        bars = pd.DataFrame({
            "ticker": ["AAPL"] * 10,
            "datetime": pd.date_range("2024-01-15 09:30", periods=10, freq="1min"),
            "open": [185.0 + i * 0.1 for i in range(10)],
            "high": [186.0 + i * 0.1 for i in range(10)],
            "low": [184.0 + i * 0.1 for i in range(10)],
            "close": [185.5 + i * 0.1 for i in range(10)],
            "volume": [1000] * 10,
        })
        parquet_path = tmp_path / "2024-01-15.parquet"
        bars.to_parquet(parquet_path)

        # Create tab with mocked price path
        with patch.object(
            ChartViewerTab, "_price_loader"
        ) as mock_loader:
            from src.core.price_data import PriceDataLoader
            mock_loader = PriceDataLoader(minute_path=tmp_path)

            tab = ChartViewerTab(app_state_with_trades)
            tab._price_loader = mock_loader

            # Trigger filtered data update
            app_state_with_trades.filtered_data_updated.emit(
                app_state_with_trades.filtered_df
            )

            # Select the trade
            tab._trade_browser.trade_list.setCurrentRow(0)

            # Verify chart has data
            assert tab._chart._bars_df is not None
```

**Step 2: Run integration test**

Run: `pytest tests/integration/test_chart_viewer_integration.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/integration/test_chart_viewer_integration.py
git commit -m "test(chart-viewer): add integration test for full workflow"
```

---

## Task 12: Final Cleanup and Documentation

**Step 1: Run all tests**

Run: `pytest tests/unit/test_price_data.py tests/unit/test_exit_simulator.py tests/unit/test_trade_browser.py tests/unit/test_candlestick_chart.py tests/unit/test_chart_viewer_tab.py -v`
Expected: All PASS

**Step 2: Run linting**

Run: `ruff check src/core/price_data.py src/core/exit_simulator.py src/ui/components/trade_browser.py src/ui/components/candlestick_chart.py src/tabs/chart_viewer.py --fix`

**Step 3: Run type checking**

Run: `mypy src/core/price_data.py src/core/exit_simulator.py src/ui/components/trade_browser.py src/ui/components/candlestick_chart.py src/tabs/chart_viewer.py`

**Step 4: Final commit**

```bash
git add -A
git commit -m "chore(chart-viewer): lint and type check fixes"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Price Data Loader Core | `src/core/price_data.py` |
| 2 | Price Data Aggregation | tests |
| 3 | Exit Simulator Core | `src/core/exit_simulator.py` |
| 4 | Exit Simulator - Stop/Close | tests |
| 5 | Trade Browser Widget | `src/ui/components/trade_browser.py` |
| 6 | Candlestick Chart Widget | `src/ui/components/candlestick_chart.py` |
| 7 | Chart Viewer Tab | `src/tabs/chart_viewer.py` |
| 8 | Register Tab | `src/ui/main_window.py` |
| 9 | Context Menu | `src/tabs/statistics_tab.py` |
| 10 | VWAP Indicator | `src/ui/components/candlestick_chart.py` |
| 11 | Integration Test | `tests/integration/` |
| 12 | Cleanup | lint/type fixes |
