# tests/ui/components/test_column_filter_panel.py
"""Tests for ColumnFilterPanel component."""

import pytest
from PyQt6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

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
        panel.show()

        panel._search_input.setText("vwap")

        # Use isVisibleTo to check visibility relative to parent
        visible = [row for row in panel._rows if not row.isHidden()]
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
