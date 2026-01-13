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

    def test_apply_button_disabled_by_default(
        self, qtbot: QtBot, app: QApplication
    ) -> None:
        """Apply button should be disabled when inputs are empty."""
        row = ColumnFilterRow(column_name="vwap")
        qtbot.addWidget(row)

        assert row._apply_btn.isEnabled() is False

    def test_apply_button_enabled_when_values_present(
        self, qtbot: QtBot, app: QApplication
    ) -> None:
        """Apply button should be enabled when both min and max have values."""
        row = ColumnFilterRow(column_name="vwap")
        qtbot.addWidget(row)

        row._min_input.setText("10")
        row._max_input.setText("20")

        assert row._apply_btn.isEnabled() is True

    def test_apply_clicked_emits_column_name(
        self, qtbot: QtBot, app: QApplication
    ) -> None:
        """apply_clicked signal should emit column name."""
        row = ColumnFilterRow(column_name="gain_pct")
        qtbot.addWidget(row)

        row._min_input.setText("0")
        row._max_input.setText("100")

        with qtbot.waitSignal(row.apply_clicked, timeout=1000) as blocker:
            row._apply_btn.click()

        assert blocker.args == ["gain_pct"]
