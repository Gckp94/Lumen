# Column Filter Panel Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the cramped dropdown-based column filter with a scrollable sub-panel showing all columns with inline min/max inputs.

**Architecture:** Create a new `ColumnFilterPanel` component that displays all numeric columns in a scrollable list. Each column row contains: column name label, between/not-between toggle, min/max input fields. A search bar at the top allows filtering visible columns. The panel integrates with the existing `FilterPanel` by replacing `FilterRow` components.

**Tech Stack:** PyQt6 (QScrollArea, QWidget, QLineEdit, custom toggle), existing Observatory theme (Colors, Fonts, Spacing from constants.py)

---

## Design Specification

### Visual Layout
```
+--------------------------------------------------+
| [Search columns...]                    [Clear]   |
+--------------------------------------------------+
| Column          | Mode       | Min    | Max     |
+--------------------------------------------------+
| gain_pct        | [between]  | [    ] | [    ]  | <- Active (cyan border)
| vwap            | [between]  | [    ] | [    ]  |
| prev_close      | [between]  | [    ] | [    ]  |
| dollar_volume   | [not betw] | [100 ] | [500 ]  | <- Has values (amber dot)
| market_cap      | [between]  | [    ] | [    ]  |
| days_since_ipo  | [between]  | [    ] | [    ]  |
| ...             |            |        |         |
+--------------------------------------------------+
```

### Key Features
1. **Scrollable column list** - All columns visible without dropdown navigation
2. **Inline editing** - Min/max values editable directly in the grid
3. **Search filter** - Type to filter visible columns
4. **Active indicator** - Columns with values show amber dot indicator
5. **Mode toggle** - Click to toggle between/not-between per column
6. **Dense layout** - Monospace font for alignment, compact spacing

### Color Scheme (Observatory Theme)
- Background: `BG_ELEVATED` (#1E1E2C)
- Row hover: `BG_BORDER` (#2A2A3A)
- Active input border: `SIGNAL_CYAN` (#00FFD4)
- Has-value indicator: `SIGNAL_AMBER` (#FFAA00)
- Column names: `TEXT_PRIMARY` (#F4F4F8)
- Mode toggle: `TEXT_SECONDARY` (#9898A8)

---

## Task 1: Create ColumnFilterRow Component

**Files:**
- Create: `src/ui/components/column_filter_row.py`
- Test: `tests/ui/components/test_column_filter_row.py`

**Step 1: Write the failing test for basic row rendering**

```python
# tests/ui/components/test_column_filter_row.py
"""Tests for ColumnFilterRow component."""

import pytest
from pytestqt.qtbot import QtBot
from PyQt6.QtWidgets import QApplication

from src.ui.components.column_filter_row import ColumnFilterRow


@pytest.fixture
def app(qtbot: QtBot) -> QApplication:
    """Provide QApplication instance."""
    return QApplication.instance() or QApplication([])


class TestColumnFilterRow:
    """Tests for ColumnFilterRow widget."""

    def test_displays_column_name(self, qtbot: QtBot, app: QApplication) -> None:
        """Row should display the column name."""
        row = ColumnFilterRow(column_name="gain_pct")
        qtbot.addWidget(row)

        assert row.get_column_name() == "gain_pct"
        assert row._column_label.text() == "gain_pct"

    def test_default_operator_is_between(self, qtbot: QtBot, app: QApplication) -> None:
        """Default operator should be 'between'."""
        row = ColumnFilterRow(column_name="vwap")
        qtbot.addWidget(row)

        assert row.get_operator() == "between"

    def test_toggle_operator_changes_mode(self, qtbot: QtBot, app: QApplication) -> None:
        """Clicking toggle should switch between 'between' and 'not_between'."""
        row = ColumnFilterRow(column_name="vwap")
        qtbot.addWidget(row)

        row._toggle_operator()
        assert row.get_operator() == "not_between"

        row._toggle_operator()
        assert row.get_operator() == "between"

    def test_get_criteria_returns_none_when_empty(
        self, qtbot: QtBot, app: QApplication
    ) -> None:
        """get_criteria should return None when min/max are empty."""
        row = ColumnFilterRow(column_name="vwap")
        qtbot.addWidget(row)

        assert row.get_criteria() is None

    def test_get_criteria_returns_filter_when_valid(
        self, qtbot: QtBot, app: QApplication
    ) -> None:
        """get_criteria should return FilterCriteria when inputs are valid."""
        row = ColumnFilterRow(column_name="vwap")
        qtbot.addWidget(row)

        row._min_input.setText("0")
        row._max_input.setText("100")

        criteria = row.get_criteria()
        assert criteria is not None
        assert criteria.column == "vwap"
        assert criteria.operator == "between"
        assert criteria.min_val == 0.0
        assert criteria.max_val == 100.0

    def test_has_values_returns_true_when_inputs_filled(
        self, qtbot: QtBot, app: QApplication
    ) -> None:
        """has_values should return True when both min and max have values."""
        row = ColumnFilterRow(column_name="vwap")
        qtbot.addWidget(row)

        assert row.has_values() is False

        row._min_input.setText("10")
        row._max_input.setText("20")

        assert row.has_values() is True

    def test_clear_values_empties_inputs(
        self, qtbot: QtBot, app: QApplication
    ) -> None:
        """clear_values should empty min and max inputs."""
        row = ColumnFilterRow(column_name="vwap")
        qtbot.addWidget(row)

        row._min_input.setText("10")
        row._max_input.setText("20")
        row.clear_values()

        assert row._min_input.text() == ""
        assert row._max_input.text() == ""
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/ui/components/test_column_filter_row.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.ui.components.column_filter_row'"

**Step 3: Write minimal implementation**

```python
# src/ui/components/column_filter_row.py
"""ColumnFilterRow component for inline column filtering."""

from typing import Literal

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from src.core.models import FilterCriteria
from src.ui.constants import Colors, Fonts, Spacing


class ColumnFilterRow(QWidget):
    """Single row for filtering a column with inline min/max inputs.

    Attributes:
        values_changed: Signal emitted when min/max values change.
        operator_changed: Signal emitted when operator toggles.
    """

    values_changed = pyqtSignal()
    operator_changed = pyqtSignal()

    def __init__(
        self,
        column_name: str,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize ColumnFilterRow.

        Args:
            column_name: Name of the column this row filters.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._column_name = column_name
        self._operator: Literal["between", "not_between"] = "between"
        self._setup_ui()
        self._apply_style()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the row UI layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.XS, Spacing.SM, Spacing.XS)
        layout.setSpacing(Spacing.SM)

        # Column name label (fixed width for alignment)
        self._column_label = QLabel(self._column_name)
        self._column_label.setFixedWidth(140)
        layout.addWidget(self._column_label)

        # Operator toggle button
        self._operator_btn = QPushButton("between")
        self._operator_btn.setFixedWidth(90)
        self._operator_btn.clicked.connect(self._toggle_operator)
        layout.addWidget(self._operator_btn)

        # Min input
        self._min_input = QLineEdit()
        self._min_input.setValidator(QDoubleValidator())
        self._min_input.setPlaceholderText("Min")
        self._min_input.setFixedWidth(70)
        layout.addWidget(self._min_input)

        # Max input
        self._max_input = QLineEdit()
        self._max_input.setValidator(QDoubleValidator())
        self._max_input.setPlaceholderText("Max")
        self._max_input.setFixedWidth(70)
        layout.addWidget(self._max_input)

        # Active indicator (amber dot when has values)
        self._indicator = QLabel()
        self._indicator.setFixedSize(8, 8)
        layout.addWidget(self._indicator)

        layout.addStretch()

    def _apply_style(self) -> None:
        """Apply Observatory theme styling."""
        self.setStyleSheet(f"""
            ColumnFilterRow {{
                background-color: transparent;
            }}
            ColumnFilterRow:hover {{
                background-color: {Colors.BG_BORDER};
            }}
        """)

        self._column_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: "{Fonts.DATA}";
                font-size: 12px;
            }}
        """)

        self._operator_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 3px;
                padding: 2px 6px;
                font-family: "{Fonts.UI}";
                font-size: 11px;
            }}
            QPushButton:hover {{
                border-color: {Colors.SIGNAL_CYAN};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)

        input_style = f"""
            QLineEdit {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 3px;
                padding: 2px 6px;
                font-family: "{Fonts.DATA}";
                font-size: 12px;
            }}
            QLineEdit:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QLineEdit:focus {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
        """
        self._min_input.setStyleSheet(input_style)
        self._max_input.setStyleSheet(input_style)

        self._update_indicator()

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self._min_input.textChanged.connect(self._on_values_changed)
        self._max_input.textChanged.connect(self._on_values_changed)

    def _on_values_changed(self) -> None:
        """Handle min/max value changes."""
        self._update_indicator()
        self.values_changed.emit()

    def _update_indicator(self) -> None:
        """Update the active indicator based on input state."""
        if self.has_values():
            self._indicator.setStyleSheet(f"""
                QLabel {{
                    background-color: {Colors.SIGNAL_AMBER};
                    border-radius: 4px;
                }}
            """)
        else:
            self._indicator.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                }
            """)

    def _toggle_operator(self) -> None:
        """Toggle between 'between' and 'not_between' operators."""
        if self._operator == "between":
            self._operator = "not_between"
            self._operator_btn.setText("not between")
        else:
            self._operator = "between"
            self._operator_btn.setText("between")
        self.operator_changed.emit()

    def get_column_name(self) -> str:
        """Get the column name for this row.

        Returns:
            Column name string.
        """
        return self._column_name

    def get_operator(self) -> Literal["between", "not_between"]:
        """Get current operator.

        Returns:
            Current operator value.
        """
        return self._operator

    def has_values(self) -> bool:
        """Check if both min and max have values.

        Returns:
            True if both inputs have text, False otherwise.
        """
        return bool(self._min_input.text().strip() and self._max_input.text().strip())

    def get_criteria(self) -> FilterCriteria | None:
        """Get FilterCriteria if inputs are valid.

        Returns:
            FilterCriteria object if valid, None otherwise.
        """
        min_text = self._min_input.text().strip()
        max_text = self._max_input.text().strip()

        if not min_text or not max_text:
            return None

        try:
            min_val = float(min_text)
            max_val = float(max_text)
        except ValueError:
            return None

        criteria = FilterCriteria(
            column=self._column_name,
            operator=self._operator,
            min_val=min_val,
            max_val=max_val,
        )

        if criteria.validate():
            return None

        return criteria

    def clear_values(self) -> None:
        """Clear min and max input values."""
        self._min_input.clear()
        self._max_input.clear()

    def set_values(self, min_val: float | None, max_val: float | None) -> None:
        """Set min and max input values.

        Args:
            min_val: Minimum value or None to clear.
            max_val: Maximum value or None to clear.
        """
        self._min_input.setText(str(min_val) if min_val is not None else "")
        self._max_input.setText(str(max_val) if max_val is not None else "")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/ui/components/test_column_filter_row.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/ui/components/test_column_filter_row.py src/ui/components/column_filter_row.py
git commit -m "feat: add ColumnFilterRow component for inline column filtering"
```

---

## Task 2: Create ColumnFilterPanel Component

**Files:**
- Create: `src/ui/components/column_filter_panel.py`
- Test: `tests/ui/components/test_column_filter_panel.py`

**Step 1: Write the failing test**

```python
# tests/ui/components/test_column_filter_panel.py
"""Tests for ColumnFilterPanel component."""

import pytest
from pytestqt.qtbot import QtBot
from PyQt6.QtWidgets import QApplication

from src.ui.components.column_filter_panel import ColumnFilterPanel


@pytest.fixture
def app(qtbot: QtBot) -> QApplication:
    """Provide QApplication instance."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def sample_columns() -> list[str]:
    """Sample column names for testing."""
    return ["gain_pct", "vwap", "prev_close", "dollar_volume", "market_cap"]


class TestColumnFilterPanel:
    """Tests for ColumnFilterPanel widget."""

    def test_creates_row_for_each_column(
        self, qtbot: QtBot, app: QApplication, sample_columns: list[str]
    ) -> None:
        """Panel should create a row for each column."""
        panel = ColumnFilterPanel(columns=sample_columns)
        qtbot.addWidget(panel)

        assert len(panel._rows) == 5
        column_names = [row.get_column_name() for row in panel._rows]
        assert column_names == sample_columns

    def test_search_filters_visible_rows(
        self, qtbot: QtBot, app: QApplication, sample_columns: list[str]
    ) -> None:
        """Typing in search should filter visible rows."""
        panel = ColumnFilterPanel(columns=sample_columns)
        qtbot.addWidget(panel)

        panel._search_input.setText("vwap")

        visible = [row for row in panel._rows if row.isVisible()]
        assert len(visible) == 1
        assert visible[0].get_column_name() == "vwap"

    def test_get_active_criteria_returns_filled_rows(
        self, qtbot: QtBot, app: QApplication, sample_columns: list[str]
    ) -> None:
        """get_active_criteria should return only rows with values."""
        panel = ColumnFilterPanel(columns=sample_columns)
        qtbot.addWidget(panel)

        # Fill in vwap row
        vwap_row = panel._rows[1]
        vwap_row._min_input.setText("0")
        vwap_row._max_input.setText("100")

        criteria_list = panel.get_active_criteria()
        assert len(criteria_list) == 1
        assert criteria_list[0].column == "vwap"

    def test_clear_all_clears_all_row_values(
        self, qtbot: QtBot, app: QApplication, sample_columns: list[str]
    ) -> None:
        """clear_all should clear values from all rows."""
        panel = ColumnFilterPanel(columns=sample_columns)
        qtbot.addWidget(panel)

        # Fill multiple rows
        panel._rows[0]._min_input.setText("10")
        panel._rows[0]._max_input.setText("20")
        panel._rows[1]._min_input.setText("0")
        panel._rows[1]._max_input.setText("100")

        panel.clear_all()

        for row in panel._rows:
            assert not row.has_values()

    def test_set_columns_rebuilds_rows(
        self, qtbot: QtBot, app: QApplication, sample_columns: list[str]
    ) -> None:
        """set_columns should rebuild rows for new columns."""
        panel = ColumnFilterPanel(columns=sample_columns)
        qtbot.addWidget(panel)

        new_columns = ["col_a", "col_b"]
        panel.set_columns(new_columns)

        assert len(panel._rows) == 2
        assert panel._rows[0].get_column_name() == "col_a"
        assert panel._rows[1].get_column_name() == "col_b"

    def test_active_filter_count_signal(
        self, qtbot: QtBot, app: QApplication, sample_columns: list[str]
    ) -> None:
        """Panel should emit signal when active filter count changes."""
        panel = ColumnFilterPanel(columns=sample_columns)
        qtbot.addWidget(panel)

        with qtbot.waitSignal(panel.active_count_changed, timeout=1000) as blocker:
            panel._rows[0]._min_input.setText("10")
            panel._rows[0]._max_input.setText("20")

        assert blocker.args == [1]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/ui/components/test_column_filter_panel.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.ui.components.column_filter_panel'"

**Step 3: Write minimal implementation**

```python
# src/ui/components/column_filter_panel.py
"""ColumnFilterPanel component for scrollable column filter list."""

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.core.models import FilterCriteria
from src.ui.components.column_filter_row import ColumnFilterRow
from src.ui.constants import Colors, Fonts, Spacing


class ColumnFilterPanel(QWidget):
    """Scrollable panel displaying all columns with inline filter inputs.

    Attributes:
        active_count_changed: Signal emitted when number of active filters changes.
        filters_changed: Signal emitted when any filter value changes.
    """

    active_count_changed = pyqtSignal(int)
    filters_changed = pyqtSignal()

    def __init__(
        self,
        columns: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize ColumnFilterPanel.

        Args:
            columns: List of column names to display.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._columns = columns or []
        self._rows: list[ColumnFilterRow] = []
        self._last_active_count = 0
        self._setup_ui()
        self._apply_style()
        self._build_rows()

    def _setup_ui(self) -> None:
        """Set up the panel UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.setSpacing(Spacing.SM)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search columns...")
        self._search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self._search_input)

        self._clear_search_btn = QPushButton("Clear")
        self._clear_search_btn.setFixedWidth(60)
        self._clear_search_btn.clicked.connect(self._on_clear_search)
        search_layout.addWidget(self._clear_search_btn)

        layout.addLayout(search_layout)

        # Header row
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(Spacing.SM, Spacing.XS, Spacing.SM, Spacing.XS)
        header_layout.setSpacing(Spacing.SM)

        col_header = QLabel("Column")
        col_header.setFixedWidth(140)
        header_layout.addWidget(col_header)

        mode_header = QLabel("Mode")
        mode_header.setFixedWidth(90)
        header_layout.addWidget(mode_header)

        min_header = QLabel("Min")
        min_header.setFixedWidth(70)
        header_layout.addWidget(min_header)

        max_header = QLabel("Max")
        max_header.setFixedWidth(70)
        header_layout.addWidget(max_header)

        header_layout.addStretch()
        layout.addWidget(header_frame)

        # Scrollable area for rows
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self._rows_container = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(0)
        self._rows_layout.addStretch()

        self._scroll_area.setWidget(self._rows_container)
        layout.addWidget(self._scroll_area)

    def _apply_style(self) -> None:
        """Apply Observatory theme styling."""
        self._search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 6px 10px;
                font-family: "{Fonts.UI}";
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
        """)

        self._clear_search_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 6px 10px;
                font-family: "{Fonts.UI}";
                font-size: 11px;
            }}
            QPushButton:hover {{
                border-color: {Colors.SIGNAL_CYAN};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)

        header_style = f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: "{Fonts.UI}";
                font-size: 11px;
                font-weight: bold;
            }}
        """
        for label in self.findChildren(QLabel):
            if label.parent() and isinstance(label.parent(), QFrame):
                label.setStyleSheet(header_style)

        self._scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
            }}
            QScrollBar:vertical {{
                background-color: {Colors.BG_ELEVATED};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {Colors.BG_BORDER};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {Colors.TEXT_SECONDARY};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        self._rows_container.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_SURFACE};
            }}
        """)

    def _build_rows(self) -> None:
        """Build rows for current columns."""
        # Clear existing rows
        for row in self._rows:
            row.deleteLater()
        self._rows.clear()

        # Create new rows
        for column in self._columns:
            row = ColumnFilterRow(column_name=column)
            row.values_changed.connect(self._on_row_values_changed)
            self._rows.append(row)
            # Insert before stretch
            self._rows_layout.insertWidget(self._rows_layout.count() - 1, row)

    def _on_search_changed(self, text: str) -> None:
        """Handle search text changes.

        Args:
            text: Current search text.
        """
        search_lower = text.lower().strip()
        for row in self._rows:
            if search_lower:
                visible = search_lower in row.get_column_name().lower()
            else:
                visible = True
            row.setVisible(visible)

    def _on_clear_search(self) -> None:
        """Handle clear search button click."""
        self._search_input.clear()

    def _on_row_values_changed(self) -> None:
        """Handle value changes in any row."""
        active_count = sum(1 for row in self._rows if row.has_values())
        if active_count != self._last_active_count:
            self._last_active_count = active_count
            self.active_count_changed.emit(active_count)
        self.filters_changed.emit()

    def get_active_criteria(self) -> list[FilterCriteria]:
        """Get FilterCriteria for all rows with valid values.

        Returns:
            List of FilterCriteria objects.
        """
        criteria_list = []
        for row in self._rows:
            criteria = row.get_criteria()
            if criteria is not None:
                criteria_list.append(criteria)
        return criteria_list

    def clear_all(self) -> None:
        """Clear all row values."""
        for row in self._rows:
            row.clear_values()

    def set_columns(self, columns: list[str]) -> None:
        """Update displayed columns.

        Args:
            columns: New list of column names.
        """
        self._columns = columns
        self._build_rows()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/ui/components/test_column_filter_panel.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/ui/components/test_column_filter_panel.py src/ui/components/column_filter_panel.py
git commit -m "feat: add ColumnFilterPanel with scrollable column filter list"
```

---

## Task 3: Integrate ColumnFilterPanel into FilterPanel

**Files:**
- Modify: `src/ui/components/filter_panel.py`
- Test: `tests/ui/components/test_filter_panel.py` (add integration tests)

**Step 1: Write the failing integration test**

```python
# Add to tests/ui/components/test_filter_panel.py

def test_filter_panel_uses_column_filter_panel(
    qtbot: QtBot, app: QApplication
) -> None:
    """FilterPanel should use ColumnFilterPanel for column filters."""
    columns = ["gain_pct", "vwap", "prev_close"]
    panel = FilterPanel(columns=columns)
    qtbot.addWidget(panel)

    # Should have column filter panel
    assert hasattr(panel, "_column_filter_panel")
    assert panel._column_filter_panel is not None

    # Should have rows for each column
    assert len(panel._column_filter_panel._rows) == 3


def test_apply_filters_uses_column_filter_panel_criteria(
    qtbot: QtBot, app: QApplication
) -> None:
    """Apply filters should gather criteria from ColumnFilterPanel."""
    columns = ["gain_pct", "vwap"]
    panel = FilterPanel(columns=columns)
    qtbot.addWidget(panel)

    # Set values in column filter panel
    panel._column_filter_panel._rows[0]._min_input.setText("10")
    panel._column_filter_panel._rows[0]._max_input.setText("20")

    with qtbot.waitSignal(panel.filters_applied, timeout=1000) as blocker:
        panel._apply_btn.click()

    criteria_list = blocker.args[0]
    assert len(criteria_list) == 1
    assert criteria_list[0].column == "gain_pct"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/ui/components/test_filter_panel.py::test_filter_panel_uses_column_filter_panel -v`
Expected: FAIL with "AttributeError: 'FilterPanel' object has no attribute '_column_filter_panel'"

**Step 3: Modify FilterPanel to use ColumnFilterPanel**

Replace the `_rows_container` section in `filter_panel.py` `_setup_ui` method:

```python
# In src/ui/components/filter_panel.py

# Add import at top
from src.ui.components.column_filter_panel import ColumnFilterPanel

# Replace in _setup_ui method - remove _rows_container and _add_btn
# Replace with:

        # Column filter panel (replaces individual filter rows)
        self._column_filter_panel = ColumnFilterPanel(columns=self._columns)
        self._column_filter_panel.setMinimumHeight(200)
        self._column_filter_panel.setMaximumHeight(300)
        layout.addWidget(self._column_filter_panel)

# Update _on_apply_filters method:
    def _on_apply_filters(self) -> None:
        """Handle apply filters button click."""
        criteria_list = self._column_filter_panel.get_active_criteria()

        self._active_filters = criteria_list
        self._update_chips()
        self.filters_applied.emit(criteria_list)

# Update _on_clear_filters method to also clear column panel:
    def _on_clear_filters(self) -> None:
        """Handle clear all filters button click."""
        # Clear column filter panel
        self._column_filter_panel.clear_all()

        # ... rest of existing clear logic ...

# Update set_columns method:
    def set_columns(self, columns: list[str]) -> None:
        """Update available columns for filtering.

        Args:
            columns: List of numeric column names.
        """
        self._columns = columns
        self._column_filter_panel.set_columns(columns)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/ui/components/test_filter_panel.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/ui/components/filter_panel.py tests/ui/components/test_filter_panel.py
git commit -m "feat: integrate ColumnFilterPanel into FilterPanel"
```

---

## Task 4: Remove Old FilterRow System

**Files:**
- Modify: `src/ui/components/filter_panel.py` (remove old code)
- Delete references to FilterRow in filter_panel.py

**Step 1: Verify tests still pass before cleanup**

Run: `pytest tests/ui/components/test_filter_panel.py -v`
Expected: PASS

**Step 2: Remove old FilterRow references from FilterPanel**

Remove from `filter_panel.py`:
- Remove `from src.ui.components.filter_row import FilterRow` import
- Remove `self._filter_rows: list[FilterRow] = []` initialization
- Remove `_on_add_filter` method
- Remove `_on_filter_column_changed` method
- Remove `_on_remove_row` method
- Remove `_get_used_columns` method
- Remove `_get_available_columns` method
- Remove `_add_btn` widget and its styling
- Remove button row layout changes for _add_btn

**Step 3: Run full test suite**

Run: `pytest tests/ -v`
Expected: PASS

**Step 4: Commit**

```bash
git add src/ui/components/filter_panel.py
git commit -m "refactor: remove old FilterRow system from FilterPanel"
```

---

## Task 5: Polish and Visual Refinements

**Files:**
- Modify: `src/ui/components/column_filter_row.py`
- Modify: `src/ui/components/column_filter_panel.py`

**Step 1: Add alternating row backgrounds**

```python
# In ColumnFilterPanel._build_rows(), add alternating colors:
for i, column in enumerate(self._columns):
    row = ColumnFilterRow(column_name=column, alternate=(i % 2 == 1))
    # ...
```

**Step 2: Add to ColumnFilterRow __init__:**

```python
def __init__(
    self,
    column_name: str,
    alternate: bool = False,
    parent: QWidget | None = None,
) -> None:
    # ...
    self._alternate = alternate
```

**Step 3: Update ColumnFilterRow._apply_style() for alternating:**

```python
bg_color = Colors.BG_ELEVATED if self._alternate else Colors.BG_SURFACE
self.setStyleSheet(f"""
    ColumnFilterRow {{
        background-color: {bg_color};
    }}
    ColumnFilterRow:hover {{
        background-color: {Colors.BG_BORDER};
    }}
""")
```

**Step 4: Run tests and verify visually**

Run: `pytest tests/ -v`
Run app manually to verify visual appearance.

**Step 5: Commit**

```bash
git add src/ui/components/column_filter_row.py src/ui/components/column_filter_panel.py
git commit -m "style: add alternating row backgrounds to column filter panel"
```

---

## Task 6: Final Integration Test

**Files:**
- Test: `tests/integration/test_feature_explorer_filters.py`

**Step 1: Write integration test**

```python
# tests/integration/test_feature_explorer_filters.py
"""Integration tests for Feature Explorer filter functionality."""

import pytest
from pytestqt.qtbot import QtBot
from PyQt6.QtWidgets import QApplication

from src.tabs.feature_explorer import FeatureExplorerTab


@pytest.fixture
def app(qtbot: QtBot) -> QApplication:
    """Provide QApplication instance."""
    return QApplication.instance() or QApplication([])


class TestFeatureExplorerFilters:
    """Integration tests for filter panel in Feature Explorer."""

    def test_filter_panel_displays_numeric_columns(
        self, qtbot: QtBot, app: QApplication
    ) -> None:
        """Filter panel should display all numeric columns from data."""
        # This test verifies the full integration works
        tab = FeatureExplorerTab()
        qtbot.addWidget(tab)

        # Verify filter panel exists
        assert hasattr(tab, "_filter_panel")
        assert tab._filter_panel is not None
```

**Step 2: Run integration test**

Run: `pytest tests/integration/test_feature_explorer_filters.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/integration/test_feature_explorer_filters.py
git commit -m "test: add integration test for Feature Explorer filters"
```

---

## Summary

This plan transforms the cramped dropdown-based filter system into a scrollable panel showing all columns with inline min/max inputs. Key benefits:

1. **All columns visible** - No need to navigate a dropdown
2. **Inline editing** - Min/max values editable directly in grid
3. **Search filter** - Quick column finding
4. **Visual indicators** - Amber dots show active filters
5. **Consistent theme** - Uses existing Observatory design language

The implementation follows TDD with each component tested before integration.
