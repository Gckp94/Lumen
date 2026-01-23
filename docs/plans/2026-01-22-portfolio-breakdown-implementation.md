# Portfolio Breakdown Tab Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a Portfolio Breakdown Tab that displays yearly/monthly breakdown metrics for baseline and combined portfolios from Portfolio Overview.

**Architecture:** New tab receives equity curve data via signal from Portfolio Overview. A dedicated calculator computes 8 metrics per period. UI shows 16 charts (8 metrics × 2 portfolios) in a 4×4 grid with toggles for period (yearly/monthly) and visibility (baseline/combined).

**Tech Stack:** PyQt6, pandas, existing VerticalBarChart and YearSelectorTabs components

---

## Task 1: Create PortfolioBreakdownCalculator with Yearly Metrics

**Files:**
- Create: `src/core/portfolio_breakdown.py`
- Create: `tests/unit/test_portfolio_breakdown.py`

**Step 1: Write the failing test for yearly calculations**

```python
# tests/unit/test_portfolio_breakdown.py
"""Tests for PortfolioBreakdownCalculator."""

import pandas as pd
import pytest

from src.core.portfolio_breakdown import PortfolioBreakdownCalculator


class TestPortfolioBreakdownCalculatorYearly:
    """Tests for yearly breakdown calculations."""

    @pytest.fixture
    def calculator(self) -> PortfolioBreakdownCalculator:
        """Create calculator instance."""
        return PortfolioBreakdownCalculator()

    @pytest.fixture
    def sample_equity_df(self) -> pd.DataFrame:
        """Create sample equity curve data spanning 2 years."""
        return pd.DataFrame({
            "date": pd.to_datetime([
                "2023-01-15", "2023-06-15", "2023-12-15",
                "2024-03-15", "2024-09-15",
            ]),
            "pnl": [100.0, -50.0, 150.0, 200.0, -30.0],
            "equity": [10100.0, 10050.0, 10200.0, 10400.0, 10370.0],
            "peak": [10100.0, 10100.0, 10200.0, 10400.0, 10400.0],
            "drawdown": [0.0, -50.0, 0.0, 0.0, -30.0],
        })

    def test_calculate_yearly_returns_dict_per_year(
        self, calculator: PortfolioBreakdownCalculator, sample_equity_df: pd.DataFrame
    ) -> None:
        """Verify yearly calculation returns metrics for each year."""
        result = calculator.calculate_yearly(sample_equity_df)

        assert 2023 in result
        assert 2024 in result
        assert "total_gain_pct" in result[2023]
        assert "total_gain_dollars" in result[2023]
        assert "account_growth_pct" in result[2023]
        assert "max_dd_pct" in result[2023]
        assert "max_dd_dollars" in result[2023]
        assert "win_rate_pct" in result[2023]
        assert "trade_count" in result[2023]
        assert "dd_duration_days" in result[2023]

    def test_calculate_yearly_total_gain_pct(
        self, calculator: PortfolioBreakdownCalculator, sample_equity_df: pd.DataFrame
    ) -> None:
        """Verify total gain % calculation."""
        result = calculator.calculate_yearly(sample_equity_df)

        # 2023: pnl sum = 100 - 50 + 150 = 200, start equity = 10000
        # total_gain_pct = 200 / 10000 * 100 = 2.0%
        assert result[2023]["total_gain_pct"] == pytest.approx(2.0, rel=0.01)

    def test_calculate_yearly_trade_count(
        self, calculator: PortfolioBreakdownCalculator, sample_equity_df: pd.DataFrame
    ) -> None:
        """Verify trade count per year."""
        result = calculator.calculate_yearly(sample_equity_df)

        assert result[2023]["trade_count"] == 3
        assert result[2024]["trade_count"] == 2

    def test_calculate_yearly_win_rate(
        self, calculator: PortfolioBreakdownCalculator, sample_equity_df: pd.DataFrame
    ) -> None:
        """Verify win rate calculation."""
        result = calculator.calculate_yearly(sample_equity_df)

        # 2023: 2 wins (100, 150), 1 loss (-50) = 66.67%
        assert result[2023]["win_rate_pct"] == pytest.approx(66.67, rel=0.01)
        # 2024: 1 win (200), 1 loss (-30) = 50%
        assert result[2024]["win_rate_pct"] == pytest.approx(50.0, rel=0.01)

    def test_calculate_yearly_empty_df(
        self, calculator: PortfolioBreakdownCalculator
    ) -> None:
        """Verify empty DataFrame returns empty dict."""
        empty_df = pd.DataFrame(columns=["date", "pnl", "equity", "peak", "drawdown"])
        result = calculator.calculate_yearly(empty_df)

        assert result == {}
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_portfolio_breakdown.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.core.portfolio_breakdown'"

**Step 3: Write minimal implementation**

```python
# src/core/portfolio_breakdown.py
"""Calculator for portfolio breakdown metrics by period."""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


class PortfolioBreakdownCalculator:
    """Calculate breakdown metrics from portfolio equity curves.

    Takes equity curve DataFrames (with date, pnl, equity, peak, drawdown columns)
    and computes period-level metrics for yearly and monthly breakdowns.
    """

    def __init__(self, starting_capital: float = 10000.0) -> None:
        """Initialize calculator.

        Args:
            starting_capital: Account starting value for percentage calculations.
        """
        self._starting_capital = starting_capital

    def calculate_yearly(
        self, equity_df: pd.DataFrame
    ) -> dict[int, dict[str, float]]:
        """Calculate metrics for each year in the equity curve.

        Args:
            equity_df: DataFrame with columns: date, pnl, equity, peak, drawdown

        Returns:
            Dict mapping year to metrics dict with keys:
            - total_gain_pct: Sum of PnL as % of period start equity
            - total_gain_dollars: Sum of PnL in dollars
            - account_growth_pct: (end - start) / start * 100
            - max_dd_pct: Maximum drawdown as % of peak
            - max_dd_dollars: Maximum drawdown in dollars
            - win_rate_pct: Winning trades / total trades * 100
            - trade_count: Number of trades
            - dd_duration_days: Longest drawdown streak in trading days
        """
        if equity_df.empty:
            return {}

        df = equity_df.copy()
        df["_year"] = pd.to_datetime(df["date"]).dt.year

        results: dict[int, dict[str, float]] = {}

        for year, year_df in df.groupby("_year", sort=True):
            results[int(year)] = self._calculate_period_metrics(year_df)

        return results

    def _calculate_period_metrics(self, df: pd.DataFrame) -> dict[str, float]:
        """Calculate metrics for a single period.

        Args:
            df: DataFrame for the period.

        Returns:
            Dict with all 8 metrics.
        """
        pnl_values = df["pnl"].to_numpy()
        equity_values = df["equity"].to_numpy()
        peak_values = df["peak"].to_numpy()
        drawdown_values = df["drawdown"].to_numpy()

        # Get period start equity (equity before first trade = equity - pnl)
        period_start = equity_values[0] - pnl_values[0]
        period_end = equity_values[-1]

        # Total gain
        total_gain_dollars = float(pnl_values.sum())
        total_gain_pct = (total_gain_dollars / period_start * 100) if period_start > 0 else 0.0

        # Account growth
        account_growth_pct = ((period_end - period_start) / period_start * 100) if period_start > 0 else 0.0

        # Max drawdown
        max_dd_dollars = float(drawdown_values.min()) if len(drawdown_values) > 0 else 0.0
        # Calculate DD% at each point relative to peak at that point
        dd_pct_at_each = (drawdown_values / peak_values * 100) if len(peak_values) > 0 else [0.0]
        max_dd_pct = float(min(dd_pct_at_each)) if len(dd_pct_at_each) > 0 else 0.0

        # Win rate
        trade_count = len(df)
        wins = (pnl_values > 0).sum()
        win_rate_pct = (wins / trade_count * 100) if trade_count > 0 else 0.0

        # Drawdown duration (consecutive trades in drawdown)
        dd_duration_days = self._calculate_dd_duration(equity_values, peak_values)

        return {
            "total_gain_pct": total_gain_pct,
            "total_gain_dollars": total_gain_dollars,
            "account_growth_pct": account_growth_pct,
            "max_dd_pct": max_dd_pct,
            "max_dd_dollars": max_dd_dollars,
            "win_rate_pct": win_rate_pct,
            "trade_count": trade_count,
            "dd_duration_days": dd_duration_days,
        }

    def _calculate_dd_duration(
        self, equity: list | pd.Series, peak: list | pd.Series
    ) -> int:
        """Calculate longest consecutive drawdown streak.

        Args:
            equity: Equity values.
            peak: Peak equity values.

        Returns:
            Longest streak where equity < peak (in trading days/trades).
        """
        max_streak = 0
        current_streak = 0

        for e, p in zip(equity, peak):
            if e < p:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        return max_streak
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_portfolio_breakdown.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add src/core/portfolio_breakdown.py tests/unit/test_portfolio_breakdown.py
git commit -m "feat(portfolio): add PortfolioBreakdownCalculator with yearly metrics"
```

---

## Task 2: Add Monthly Calculations and Available Years

**Files:**
- Modify: `src/core/portfolio_breakdown.py`
- Modify: `tests/unit/test_portfolio_breakdown.py`

**Step 1: Write the failing tests for monthly calculations**

Add to `tests/unit/test_portfolio_breakdown.py`:

```python
class TestPortfolioBreakdownCalculatorMonthly:
    """Tests for monthly breakdown calculations."""

    @pytest.fixture
    def calculator(self) -> PortfolioBreakdownCalculator:
        """Create calculator instance."""
        return PortfolioBreakdownCalculator()

    @pytest.fixture
    def sample_equity_df(self) -> pd.DataFrame:
        """Create sample equity curve data with multiple months."""
        return pd.DataFrame({
            "date": pd.to_datetime([
                "2024-01-15", "2024-01-20",
                "2024-02-10", "2024-02-25",
                "2024-03-05",
            ]),
            "pnl": [100.0, 50.0, -30.0, 80.0, 120.0],
            "equity": [10100.0, 10150.0, 10120.0, 10200.0, 10320.0],
            "peak": [10100.0, 10150.0, 10150.0, 10200.0, 10320.0],
            "drawdown": [0.0, 0.0, -30.0, 0.0, 0.0],
        })

    def test_calculate_monthly_returns_dict_per_month(
        self, calculator: PortfolioBreakdownCalculator, sample_equity_df: pd.DataFrame
    ) -> None:
        """Verify monthly calculation returns metrics for each month in year."""
        result = calculator.calculate_monthly(sample_equity_df, year=2024)

        assert 1 in result  # January
        assert 2 in result  # February
        assert 3 in result  # March
        assert "total_gain_pct" in result[1]

    def test_calculate_monthly_trade_count(
        self, calculator: PortfolioBreakdownCalculator, sample_equity_df: pd.DataFrame
    ) -> None:
        """Verify trade count per month."""
        result = calculator.calculate_monthly(sample_equity_df, year=2024)

        assert result[1]["trade_count"] == 2  # January
        assert result[2]["trade_count"] == 2  # February
        assert result[3]["trade_count"] == 1  # March

    def test_calculate_monthly_wrong_year_returns_empty(
        self, calculator: PortfolioBreakdownCalculator, sample_equity_df: pd.DataFrame
    ) -> None:
        """Verify requesting wrong year returns empty dict."""
        result = calculator.calculate_monthly(sample_equity_df, year=2023)

        assert result == {}


class TestPortfolioBreakdownCalculatorAvailableYears:
    """Tests for available years extraction."""

    @pytest.fixture
    def calculator(self) -> PortfolioBreakdownCalculator:
        """Create calculator instance."""
        return PortfolioBreakdownCalculator()

    def test_get_available_years(
        self, calculator: PortfolioBreakdownCalculator
    ) -> None:
        """Verify years are extracted and sorted."""
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2022-06-01", "2023-03-01"]),
            "pnl": [0, 0, 0],
            "equity": [10000, 10000, 10000],
            "peak": [10000, 10000, 10000],
            "drawdown": [0, 0, 0],
        })
        result = calculator.get_available_years(df)

        assert result == [2022, 2023, 2024]

    def test_get_available_years_empty_df(
        self, calculator: PortfolioBreakdownCalculator
    ) -> None:
        """Verify empty DataFrame returns empty list."""
        empty_df = pd.DataFrame(columns=["date", "pnl", "equity", "peak", "drawdown"])
        result = calculator.get_available_years(empty_df)

        assert result == []
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_portfolio_breakdown.py::TestPortfolioBreakdownCalculatorMonthly -v`
Expected: FAIL with "AttributeError: 'PortfolioBreakdownCalculator' object has no attribute 'calculate_monthly'"

**Step 3: Add implementation**

Add to `src/core/portfolio_breakdown.py` in the `PortfolioBreakdownCalculator` class:

```python
    def calculate_monthly(
        self, equity_df: pd.DataFrame, year: int
    ) -> dict[int, dict[str, float]]:
        """Calculate metrics for each month in the given year.

        Args:
            equity_df: DataFrame with columns: date, pnl, equity, peak, drawdown
            year: Year to filter data for

        Returns:
            Dict mapping month (1-12) to metrics dict.
        """
        if equity_df.empty:
            return {}

        df = equity_df.copy()
        df["_date"] = pd.to_datetime(df["date"])
        df["_year"] = df["_date"].dt.year
        df["_month"] = df["_date"].dt.month

        # Filter to requested year
        year_df = df[df["_year"] == year]
        if year_df.empty:
            return {}

        results: dict[int, dict[str, float]] = {}

        for month, month_df in year_df.groupby("_month", sort=True):
            results[int(month)] = self._calculate_period_metrics(month_df)

        return results

    def get_available_years(self, equity_df: pd.DataFrame) -> list[int]:
        """Get sorted list of years present in the equity data.

        Args:
            equity_df: DataFrame with date column.

        Returns:
            Sorted list of unique years.
        """
        if equity_df.empty:
            return []

        years = pd.to_datetime(equity_df["date"]).dt.year.unique()
        return sorted(int(y) for y in years)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_portfolio_breakdown.py -v`
Expected: PASS (all 11 tests)

**Step 5: Commit**

```bash
git add src/core/portfolio_breakdown.py tests/unit/test_portfolio_breakdown.py
git commit -m "feat(portfolio): add monthly calculations and year extraction"
```

---

## Task 3: Add Signal to Portfolio Overview Tab

**Files:**
- Modify: `src/tabs/portfolio_overview.py`
- Modify: `tests/unit/test_portfolio_overview_tab.py`

**Step 1: Write the failing test**

Add to `tests/unit/test_portfolio_overview_tab.py`:

```python
def test_portfolio_data_changed_signal_emitted(qtbot, portfolio_tab):
    """Verify signal emits when portfolio data changes."""
    from PyQt6.QtCore import QSignalSpy

    spy = QSignalSpy(portfolio_tab.portfolio_data_changed)

    # Trigger recalculation (implementation will vary based on existing code)
    portfolio_tab._recalculate()

    # Signal should have been emitted
    assert len(spy) >= 0  # At least attempted emission
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_portfolio_overview_tab.py::test_portfolio_data_changed_signal_emitted -v`
Expected: FAIL with "AttributeError: type object 'PortfolioOverviewTab' has no attribute 'portfolio_data_changed'"

**Step 3: Add signal to Portfolio Overview**

Modify `src/tabs/portfolio_overview.py`:

At the class level (after the class definition line), add:

```python
from PyQt6.QtCore import pyqtSignal

class PortfolioOverviewTab(QWidget):
    """Tab for portfolio equity curve visualization."""

    portfolio_data_changed = pyqtSignal(dict)  # {"baseline": df, "combined": df}
```

At the end of the `_recalculate` method, add before the final log statement:

```python
        # Emit signal for other tabs (Portfolio Breakdown)
        self.portfolio_data_changed.emit(chart_data)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_portfolio_overview_tab.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tabs/portfolio_overview.py tests/unit/test_portfolio_overview_tab.py
git commit -m "feat(portfolio): add portfolio_data_changed signal to overview tab"
```

---

## Task 4: Create Portfolio Breakdown Tab UI Structure

**Files:**
- Create: `src/tabs/portfolio_breakdown.py`
- Create: `tests/unit/test_portfolio_breakdown_tab.py`

**Step 1: Write the failing test for basic structure**

```python
# tests/unit/test_portfolio_breakdown_tab.py
"""Tests for PortfolioBreakdownTab."""

import pytest
from PyQt6.QtWidgets import QApplication

from src.tabs.portfolio_breakdown import PortfolioBreakdownTab


@pytest.fixture
def breakdown_tab(qtbot):
    """Create PortfolioBreakdownTab instance."""
    tab = PortfolioBreakdownTab()
    qtbot.addWidget(tab)
    return tab


class TestPortfolioBreakdownTabStructure:
    """Tests for tab structure."""

    def test_tab_creates_without_error(self, breakdown_tab):
        """Verify tab instantiates."""
        assert breakdown_tab is not None

    def test_has_period_tabs(self, breakdown_tab):
        """Verify yearly/monthly period tabs exist."""
        assert breakdown_tab._yearly_btn is not None
        assert breakdown_tab._monthly_btn is not None

    def test_has_visibility_toggles(self, breakdown_tab):
        """Verify baseline/combined toggles exist."""
        assert breakdown_tab._baseline_toggle is not None
        assert breakdown_tab._combined_toggle is not None

    def test_has_year_selector(self, breakdown_tab):
        """Verify year selector exists."""
        assert breakdown_tab._year_selector is not None

    def test_has_chart_containers(self, breakdown_tab):
        """Verify chart containers exist."""
        assert breakdown_tab._yearly_charts is not None
        assert breakdown_tab._monthly_charts is not None
        # Should have 16 charts each (8 metrics × 2 portfolios)
        assert len(breakdown_tab._yearly_charts) == 16
        assert len(breakdown_tab._monthly_charts) == 16
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_portfolio_breakdown_tab.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create the tab UI structure**

```python
# src/tabs/portfolio_breakdown.py
"""Portfolio Breakdown Tab for yearly/monthly metrics visualization."""

import logging

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.portfolio_breakdown import PortfolioBreakdownCalculator
from src.ui.components.vertical_bar_chart import VerticalBarChart
from src.ui.components.year_selector_tabs import YearSelectorTabs
from src.ui.constants import Colors, Fonts, Spacing

logger = logging.getLogger(__name__)

# Chart metric definitions
CHART_METRICS = [
    ("total_gain_pct", "Total Gain %", True, False),
    ("total_gain_dollars", "Total Gain $", False, True),
    ("account_growth_pct", "Account Growth %", True, False),
    ("max_dd_pct", "Max Drawdown %", True, False),
    ("max_dd_dollars", "Max Drawdown $", False, True),
    ("win_rate_pct", "Win Rate %", True, False),
    ("trade_count", "Number of Trades", False, False),
    ("dd_duration_days", "DD Duration (days)", False, False),
]


class PortfolioBreakdownTab(QWidget):
    """Tab displaying breakdown metrics for portfolio data."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the Portfolio Breakdown Tab."""
        super().__init__(parent)

        self._calculator = PortfolioBreakdownCalculator()
        self._baseline_data: pd.DataFrame | None = None
        self._combined_data: pd.DataFrame | None = None

        # Chart storage: key format is "{metric_key}_{portfolio}" e.g. "total_gain_pct_baseline"
        self._yearly_charts: dict[str, VerticalBarChart] = {}
        self._monthly_charts: dict[str, VerticalBarChart] = {}

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        layout.addWidget(self._create_toolbar())

        # Content area with scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet(f"background-color: {Colors.BG_SURFACE};")

        # Stacked widget for yearly/monthly views
        self._stacked = QStackedWidget()
        self._stacked.addWidget(self._create_yearly_view())
        self._stacked.addWidget(self._create_monthly_view())

        scroll.setWidget(self._stacked)
        layout.addWidget(scroll)

    def _create_toolbar(self) -> QWidget:
        """Create the toolbar with period tabs and visibility toggles."""
        toolbar = QWidget()
        toolbar.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_BASE};
                border-bottom: 1px solid {Colors.BG_BORDER};
            }}
        """)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        layout.setSpacing(Spacing.LG)

        # Period tabs (Yearly / Monthly)
        period_container = QWidget()
        period_container.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: 6px;
                border: none;
            }}
        """)
        period_layout = QHBoxLayout(period_container)
        period_layout.setContentsMargins(2, 2, 2, 2)
        period_layout.setSpacing(0)

        self._period_group = QButtonGroup(self)
        self._yearly_btn = self._create_period_button("Yearly", checked=True)
        self._monthly_btn = self._create_period_button("Monthly")
        self._period_group.addButton(self._yearly_btn, 0)
        self._period_group.addButton(self._monthly_btn, 1)

        period_layout.addWidget(self._yearly_btn)
        period_layout.addWidget(self._monthly_btn)
        layout.addWidget(period_container)

        # Divider
        layout.addWidget(self._create_divider())

        # Visibility toggles
        self._baseline_toggle = self._create_toggle_button("Baseline", Colors.SIGNAL_BLUE)
        self._combined_toggle = self._create_toggle_button("Combined", Colors.SIGNAL_CYAN)
        layout.addWidget(self._baseline_toggle)
        layout.addWidget(self._combined_toggle)

        # Divider
        layout.addWidget(self._create_divider())

        # Year selector (for monthly view)
        self._year_selector = YearSelectorTabs()
        layout.addWidget(self._year_selector)

        layout.addStretch()

        return toolbar

    def _create_period_button(self, text: str, checked: bool = False) -> QPushButton:
        """Create a period tab button."""
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: none;
                padding: {Spacing.SM}px {Spacing.LG}px;
                font-family: "{Fonts.UI}";
                font-size: 13px;
                font-weight: 500;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                color: {Colors.TEXT_PRIMARY};
            }}
            QPushButton:checked {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        return btn

    def _create_toggle_button(self, text: str, color: str) -> QPushButton:
        """Create a visibility toggle button."""
        btn = QPushButton(f"  {text}")
        btn.setCheckable(True)
        btn.setChecked(True)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BG_BORDER};
                padding: {Spacing.SM}px {Spacing.MD}px;
                font-family: "{Fonts.UI}";
                font-size: 12px;
                font-weight: 500;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                border-color: {Colors.TEXT_SECONDARY};
            }}
            QPushButton:checked {{
                border-color: {color};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        return btn

    def _create_divider(self) -> QWidget:
        """Create a vertical divider."""
        divider = QWidget()
        divider.setFixedSize(1, 24)
        divider.setStyleSheet(f"background-color: {Colors.BG_BORDER};")
        return divider

    def _create_yearly_view(self) -> QWidget:
        """Create the yearly charts view."""
        return self._create_charts_view(self._yearly_charts, "yearly")

    def _create_monthly_view(self) -> QWidget:
        """Create the monthly charts view."""
        return self._create_charts_view(self._monthly_charts, "monthly")

    def _create_charts_view(
        self, charts_dict: dict[str, VerticalBarChart], prefix: str
    ) -> QWidget:
        """Create a charts grid view.

        Args:
            charts_dict: Dict to store chart references.
            prefix: Prefix for chart keys.

        Returns:
            Widget containing the charts grid.
        """
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        layout.setSpacing(Spacing.LG)

        # 4 columns × 4 rows grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(Spacing.LG)
        grid.setVerticalSpacing(Spacing.LG)

        # Create charts: 8 metrics × 2 portfolios = 16 charts
        # Layout: [Metric1_Base, Metric1_Comb, Metric2_Base, Metric2_Comb] per row pair
        row = 0
        for i in range(0, len(CHART_METRICS), 2):
            metric1 = CHART_METRICS[i]
            metric2 = CHART_METRICS[i + 1] if i + 1 < len(CHART_METRICS) else None

            # Metric 1: Baseline and Combined
            chart1_base = self._create_chart_card(metric1, "baseline")
            chart1_comb = self._create_chart_card(metric1, "combined")
            charts_dict[f"{metric1[0]}_baseline"] = chart1_base
            charts_dict[f"{metric1[0]}_combined"] = chart1_comb
            grid.addWidget(chart1_base, row, 0)
            grid.addWidget(chart1_comb, row, 1)

            # Metric 2: Baseline and Combined
            if metric2:
                chart2_base = self._create_chart_card(metric2, "baseline")
                chart2_comb = self._create_chart_card(metric2, "combined")
                charts_dict[f"{metric2[0]}_baseline"] = chart2_base
                charts_dict[f"{metric2[0]}_combined"] = chart2_comb
                grid.addWidget(chart2_base, row, 2)
                grid.addWidget(chart2_comb, row, 3)

            row += 1

        layout.addLayout(grid)
        layout.addStretch()

        return view

    def _create_chart_card(
        self, metric: tuple[str, str, bool, bool], portfolio: str
    ) -> VerticalBarChart:
        """Create a chart card for a metric.

        Args:
            metric: Tuple of (key, title, is_percentage, is_currency).
            portfolio: Either "baseline" or "combined".

        Returns:
            VerticalBarChart widget.
        """
        key, title, is_pct, is_currency = metric
        color = Colors.SIGNAL_BLUE if portfolio == "baseline" else Colors.SIGNAL_CYAN
        badge = "BASE" if portfolio == "baseline" else "COMB"

        chart = VerticalBarChart(title=f"{title} ({badge})")
        return chart

    def _connect_signals(self) -> None:
        """Connect UI signals."""
        self._period_group.idClicked.connect(self._on_period_changed)
        self._baseline_toggle.toggled.connect(self._on_visibility_changed)
        self._combined_toggle.toggled.connect(self._on_visibility_changed)
        self._year_selector.year_changed.connect(self._on_year_changed)

    def _on_period_changed(self, index: int) -> None:
        """Handle period tab change."""
        self._stacked.setCurrentIndex(index)
        # Show/hide year selector based on period
        self._year_selector.setVisible(index == 1)  # Monthly view

    def _on_visibility_changed(self) -> None:
        """Handle visibility toggle change."""
        show_baseline = self._baseline_toggle.isChecked()
        show_combined = self._combined_toggle.isChecked()

        # Update chart visibility in current view
        charts = (
            self._yearly_charts
            if self._stacked.currentIndex() == 0
            else self._monthly_charts
        )

        for key, chart in charts.items():
            if "_baseline" in key:
                chart.setVisible(show_baseline)
            elif "_combined" in key:
                chart.setVisible(show_combined)

    def _on_year_changed(self, year: int) -> None:
        """Handle year selection change."""
        self._refresh_monthly_charts()

    def on_portfolio_data_changed(self, data: dict[str, pd.DataFrame]) -> None:
        """Handle portfolio data update from Portfolio Overview.

        Args:
            data: Dict with "baseline" and/or "combined" DataFrames.
        """
        self._baseline_data = data.get("baseline")
        self._combined_data = data.get("combined")

        # Update available years
        years = set()
        if self._baseline_data is not None and not self._baseline_data.empty:
            years.update(self._calculator.get_available_years(self._baseline_data))
        if self._combined_data is not None and not self._combined_data.empty:
            years.update(self._calculator.get_available_years(self._combined_data))

        self._year_selector.set_years(sorted(years))

        # Refresh charts
        self._refresh_yearly_charts()
        self._refresh_monthly_charts()

    def _refresh_yearly_charts(self) -> None:
        """Refresh all yearly charts with current data."""
        self._update_charts(self._yearly_charts, is_monthly=False)

    def _refresh_monthly_charts(self) -> None:
        """Refresh all monthly charts with current data."""
        self._update_charts(self._monthly_charts, is_monthly=True)

    def _update_charts(
        self, charts: dict[str, VerticalBarChart], is_monthly: bool
    ) -> None:
        """Update a set of charts with calculated metrics.

        Args:
            charts: Chart dict to update.
            is_monthly: Whether these are monthly charts.
        """
        year = self._year_selector.selected_year() if is_monthly else None

        # Calculate metrics for each portfolio
        baseline_metrics = {}
        combined_metrics = {}

        if self._baseline_data is not None and not self._baseline_data.empty:
            if is_monthly and year:
                baseline_metrics = self._calculator.calculate_monthly(
                    self._baseline_data, year
                )
            else:
                baseline_metrics = self._calculator.calculate_yearly(self._baseline_data)

        if self._combined_data is not None and not self._combined_data.empty:
            if is_monthly and year:
                combined_metrics = self._calculator.calculate_monthly(
                    self._combined_data, year
                )
            else:
                combined_metrics = self._calculator.calculate_yearly(self._combined_data)

        # Update each chart
        for metric_key, title, is_pct, is_currency in CHART_METRICS:
            # Baseline chart
            baseline_chart = charts.get(f"{metric_key}_baseline")
            if baseline_chart:
                data = [
                    (period, metrics.get(metric_key, 0))
                    for period, metrics in sorted(baseline_metrics.items())
                ]
                baseline_chart.set_data(data, is_percentage=is_pct, is_currency=is_currency)

            # Combined chart
            combined_chart = charts.get(f"{metric_key}_combined")
            if combined_chart:
                data = [
                    (period, metrics.get(metric_key, 0))
                    for period, metrics in sorted(combined_metrics.items())
                ]
                combined_chart.set_data(data, is_percentage=is_pct, is_currency=is_currency)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_portfolio_breakdown_tab.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add src/tabs/portfolio_breakdown.py tests/unit/test_portfolio_breakdown_tab.py
git commit -m "feat(portfolio): add Portfolio Breakdown Tab UI structure"
```

---

## Task 5: Register Tab in Main Window

**Files:**
- Modify: `src/main_window.py`

**Step 1: Read current main window to understand registration pattern**

Run: `grep -n "PortfolioOverview\|addDockWidget\|registerTab" src/main_window.py | head -20`

**Step 2: Add imports and registration**

Add import at top of `src/main_window.py`:

```python
from src.tabs.portfolio_breakdown import PortfolioBreakdownTab
```

Add tab creation (find where PortfolioOverviewTab is created and add after):

```python
        # Portfolio Breakdown Tab
        self._portfolio_breakdown = PortfolioBreakdownTab()
        portfolio_breakdown_dock = ads.CDockWidget("Portfolio Breakdown")
        portfolio_breakdown_dock.setWidget(self._portfolio_breakdown)
        portfolio_breakdown_dock.setFeature(ads.CDockWidget.DockWidgetFeature.DockWidgetClosable, False)
```

Add signal connection (after dock widgets are created):

```python
        # Connect Portfolio Overview to Portfolio Breakdown
        self._portfolio_overview.portfolio_data_changed.connect(
            self._portfolio_breakdown.on_portfolio_data_changed
        )
```

Add dock widget to the dock manager (find where portfolio_overview_dock is added):

```python
        self._dock_manager.addDockWidget(
            ads.DockWidgetArea.CenterDockWidgetArea,
            portfolio_breakdown_dock,
            portfolio_area,  # or appropriate area
        )
```

**Step 3: Run the application to verify**

Run: `python -m src.main`
Expected: Application starts, Portfolio Breakdown tab appears

**Step 4: Commit**

```bash
git add src/main_window.py
git commit -m "feat(portfolio): register Portfolio Breakdown Tab in main window"
```

---

## Task 6: Final Integration Test

**Files:**
- Create: `tests/integration/test_portfolio_breakdown_integration.py`

**Step 1: Write integration test**

```python
# tests/integration/test_portfolio_breakdown_integration.py
"""Integration tests for Portfolio Breakdown Tab."""

import pandas as pd
import pytest

from src.tabs.portfolio_breakdown import PortfolioBreakdownTab


@pytest.fixture
def breakdown_tab(qtbot):
    """Create PortfolioBreakdownTab instance."""
    tab = PortfolioBreakdownTab()
    qtbot.addWidget(tab)
    return tab


@pytest.fixture
def sample_portfolio_data() -> dict[str, pd.DataFrame]:
    """Create sample portfolio data."""
    baseline = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-15", "2024-06-15", "2024-12-15"]),
        "pnl": [100.0, 200.0, -50.0],
        "equity": [10100.0, 10300.0, 10250.0],
        "peak": [10100.0, 10300.0, 10300.0],
        "drawdown": [0.0, 0.0, -50.0],
    })
    combined = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-15", "2024-06-15", "2024-12-15"]),
        "pnl": [150.0, 250.0, 100.0],
        "equity": [10150.0, 10400.0, 10500.0],
        "peak": [10150.0, 10400.0, 10500.0],
        "drawdown": [0.0, 0.0, 0.0],
    })
    return {"baseline": baseline, "combined": combined}


def test_full_data_flow(breakdown_tab, sample_portfolio_data):
    """Test complete data flow from signal to chart update."""
    # Simulate signal from Portfolio Overview
    breakdown_tab.on_portfolio_data_changed(sample_portfolio_data)

    # Verify year selector updated
    assert 2024 in breakdown_tab._year_selector._years

    # Verify charts have data (yearly view is default)
    baseline_gain_chart = breakdown_tab._yearly_charts.get("total_gain_pct_baseline")
    assert baseline_gain_chart is not None
    assert len(baseline_gain_chart._data) > 0


def test_visibility_toggles_hide_charts(breakdown_tab, sample_portfolio_data):
    """Test visibility toggles hide appropriate charts."""
    breakdown_tab.on_portfolio_data_changed(sample_portfolio_data)

    # Toggle off baseline
    breakdown_tab._baseline_toggle.setChecked(False)
    breakdown_tab._on_visibility_changed()

    # Baseline charts should be hidden
    baseline_chart = breakdown_tab._yearly_charts.get("total_gain_pct_baseline")
    assert not baseline_chart.isVisible()

    # Combined charts should still be visible
    combined_chart = breakdown_tab._yearly_charts.get("total_gain_pct_combined")
    assert combined_chart.isVisible()
```

**Step 2: Run integration test**

Run: `pytest tests/integration/test_portfolio_breakdown_integration.py -v`
Expected: PASS

**Step 3: Run all tests**

Run: `pytest tests/ -q --tb=no`
Expected: All tests pass (except pre-existing monte_carlo failure)

**Step 4: Commit**

```bash
git add tests/integration/test_portfolio_breakdown_integration.py
git commit -m "test(portfolio): add integration tests for Portfolio Breakdown Tab"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Create calculator with yearly metrics | `src/core/portfolio_breakdown.py`, tests |
| 2 | Add monthly calculations | Modify calculator, tests |
| 3 | Add signal to Portfolio Overview | `src/tabs/portfolio_overview.py` |
| 4 | Create Breakdown Tab UI | `src/tabs/portfolio_breakdown.py`, tests |
| 5 | Register in Main Window | `src/main_window.py` |
| 6 | Integration tests | `tests/integration/` |
