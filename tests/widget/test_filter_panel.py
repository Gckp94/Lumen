"""Widget tests for FilterPanel component."""

from PyQt6.QtCore import Qt
from pytestqt.qtbot import QtBot

from src.ui.components.filter_panel import FilterPanel
from src.ui.constants import Limits


class TestFilterPanelAddFilter:
    """Tests for adding filters."""

    def test_add_filter_creates_filter_row(self, qtbot: QtBot) -> None:
        """'Add Filter' button creates new FilterRow."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        assert len(panel._filter_rows) == 0

        panel._add_btn.click()

        assert len(panel._filter_rows) == 1

    def test_add_multiple_filter_rows(self, qtbot: QtBot) -> None:
        """Multiple filter rows can be added."""
        panel = FilterPanel(columns=["gain_pct", "volume", "price"])
        qtbot.addWidget(panel)

        panel._add_btn.click()
        panel._add_btn.click()
        panel._add_btn.click()

        assert len(panel._filter_rows) == 3

    def test_max_filters_disables_add_button(self, qtbot: QtBot) -> None:
        """Add button is disabled when max filters reached."""
        # Need at least MAX_FILTERS columns to test max filters
        columns = [f"col_{i}" for i in range(Limits.MAX_FILTERS)]
        panel = FilterPanel(columns=columns)
        qtbot.addWidget(panel)

        for _ in range(Limits.MAX_FILTERS):
            panel._add_btn.click()

        assert not panel._add_btn.isEnabled()
        assert len(panel._filter_rows) == Limits.MAX_FILTERS


class TestFilterPanelApplyFilters:
    """Tests for applying filters."""

    def test_apply_filters_emits_signal(self, qtbot: QtBot) -> None:
        """'Apply Filters' button emits filters_applied signal."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        # Add a filter row and set values
        panel._add_btn.click()
        row = panel._filter_rows[0]
        row._column_combo.setCurrentText("gain_pct")
        row._operator_combo.setCurrentIndex(0)  # "between"
        row._min_input.setText("0")
        row._max_input.setText("10")

        with qtbot.waitSignal(panel.filters_applied, timeout=1000) as blocker:
            panel._apply_btn.click()

        assert len(blocker.args[0]) == 1
        criteria = blocker.args[0][0]
        assert criteria.column == "gain_pct"
        assert criteria.operator == "between"
        assert criteria.min_val == 0.0
        assert criteria.max_val == 10.0

    def test_apply_filters_creates_chips(self, qtbot: QtBot) -> None:
        """Applying filters creates FilterChip widgets."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        # Add and configure a filter row
        panel._add_btn.click()
        row = panel._filter_rows[0]
        row._min_input.setText("0")
        row._max_input.setText("10")

        panel._apply_btn.click()

        assert len(panel._filter_chips) == 1


class TestFilterPanelClearFilters:
    """Tests for clearing filters."""

    def test_clear_filters_removes_all_rows(self, qtbot: QtBot) -> None:
        """'Clear All Filters' removes all filter rows."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        panel._add_btn.click()
        panel._add_btn.click()
        assert len(panel._filter_rows) == 2

        panel._clear_btn.click()

        assert len(panel._filter_rows) == 0

    def test_clear_filters_emits_signal(self, qtbot: QtBot) -> None:
        """'Clear All Filters' emits filters_cleared signal."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        panel._add_btn.click()

        with qtbot.waitSignal(panel.filters_cleared, timeout=1000):
            panel._clear_btn.click()

    def test_clear_filters_removes_chips(self, qtbot: QtBot) -> None:
        """'Clear All Filters' removes all FilterChip widgets."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        # Add, configure, and apply a filter
        panel._add_btn.click()
        row = panel._filter_rows[0]
        row._min_input.setText("0")
        row._max_input.setText("10")
        panel._apply_btn.click()

        assert len(panel._filter_chips) == 1

        panel._clear_btn.click()

        assert len(panel._filter_chips) == 0

    def test_clear_re_enables_add_button(self, qtbot: QtBot) -> None:
        """'Clear All Filters' re-enables add button."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        # Add max filters
        for _ in range(Limits.MAX_FILTERS):
            panel._add_btn.click()

        assert not panel._add_btn.isEnabled()

        panel._clear_btn.click()

        assert panel._add_btn.isEnabled()


class TestFilterPanelRemoveRow:
    """Tests for removing individual filter rows."""

    def test_remove_button_removes_row(self, qtbot: QtBot) -> None:
        """Remove button on FilterRow removes that row."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        panel._add_btn.click()
        assert len(panel._filter_rows) == 1

        row = panel._filter_rows[0]
        row._remove_btn.click()

        # Process events to let deleteLater work
        qtbot.wait(10)

        assert len(panel._filter_rows) == 0

    def test_remove_row_re_enables_add_button(self, qtbot: QtBot) -> None:
        """Removing a row re-enables add button if below max."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        # Add max filters
        for _ in range(Limits.MAX_FILTERS):
            panel._add_btn.click()

        assert not panel._add_btn.isEnabled()

        # Remove one
        panel._filter_rows[0]._remove_btn.click()
        qtbot.wait(10)

        assert panel._add_btn.isEnabled()


class TestFilterPanelFirstTriggerToggle:
    """Tests for first trigger toggle integration."""

    def test_filter_panel_has_first_trigger_toggle(self, qtbot: QtBot) -> None:
        """FilterPanel has first_trigger_toggle widget."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        assert hasattr(panel, "_first_trigger_toggle")
        assert panel._first_trigger_toggle is not None

    def test_toggle_emits_first_trigger_toggled_signal(self, qtbot: QtBot) -> None:
        """Toggle emits first_trigger_toggled signal."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        with qtbot.waitSignal(panel.first_trigger_toggled, timeout=1000) as blocker:
            # Toggle is initially True, clicking should emit False
            qtbot.mouseClick(panel._first_trigger_toggle, Qt.MouseButton.LeftButton)

        assert blocker.args[0] is False

    def test_toggle_initial_state_is_on(self, qtbot: QtBot) -> None:
        """Toggle initial state matches default (ON/True)."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        assert panel._first_trigger_toggle.isChecked() is True

    def test_toggle_label_is_correct(self, qtbot: QtBot) -> None:
        """Toggle displays 'First Trigger Only' label."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        assert panel._first_trigger_toggle._label == "First Trigger Only"


class TestFilterPanelSetColumns:
    """Tests for setting columns."""

    def test_set_columns_updates_existing_rows(self, qtbot: QtBot) -> None:
        """set_columns updates column options in existing rows."""
        panel = FilterPanel(columns=["gain_pct"])
        qtbot.addWidget(panel)

        panel._add_btn.click()
        row = panel._filter_rows[0]
        assert row._column_combo.count() == 1

        panel.set_columns(["gain_pct", "volume", "price"])

        assert row._column_combo.count() == 3


class TestFilterPanelDuplicatePrevention:
    """Tests for duplicate column prevention (AC: 2)."""

    def test_add_filter_excludes_used_columns(self, qtbot: QtBot) -> None:
        """Adding filter excludes columns already in use."""
        panel = FilterPanel(columns=["gain_pct", "volume", "price"])
        qtbot.addWidget(panel)

        # Add first filter for gain_pct (first column by default)
        panel._add_btn.click()
        assert panel._filter_rows[0].get_column() == "gain_pct"

        # Add second filter - gain_pct should not be available
        panel._add_btn.click()
        available = panel._filter_rows[1].get_available_columns()
        assert "gain_pct" not in available
        assert "volume" in available
        assert "price" in available

    def test_remove_filter_makes_column_available(self, qtbot: QtBot) -> None:
        """Removing filter makes column available again."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        # Add filter for gain_pct
        panel._add_btn.click()
        assert panel._filter_rows[0].get_column() == "gain_pct"

        # Remove the filter row
        panel._filter_rows[0]._remove_btn.click()
        qtbot.wait(10)

        # Add new filter - gain_pct should be available
        panel._add_btn.click()
        available = panel._filter_rows[0].get_available_columns()
        assert "gain_pct" in available

    def test_add_disabled_when_all_columns_used(self, qtbot: QtBot) -> None:
        """Add button disabled when all columns are in use."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        # Use all columns
        panel._add_btn.click()  # gain_pct
        panel._add_btn.click()  # volume

        assert not panel._add_btn.isEnabled()
        assert len(panel._filter_rows) == 2

    def test_add_re_enabled_when_column_freed(self, qtbot: QtBot) -> None:
        """Add button re-enabled when a column becomes available."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        # Use all columns
        panel._add_btn.click()
        panel._add_btn.click()
        assert not panel._add_btn.isEnabled()

        # Remove one row
        panel._filter_rows[0]._remove_btn.click()
        qtbot.wait(10)

        assert panel._add_btn.isEnabled()

    def test_get_used_columns_returns_correct_set(self, qtbot: QtBot) -> None:
        """_get_used_columns returns set of columns in use."""
        panel = FilterPanel(columns=["gain_pct", "volume", "price"])
        qtbot.addWidget(panel)

        panel._add_btn.click()  # gain_pct
        panel._add_btn.click()  # volume

        used = panel._get_used_columns()
        assert used == {"gain_pct", "volume"}

    def test_no_duplicate_columns_across_filters(self, qtbot: QtBot) -> None:
        """Cannot have duplicate columns across multiple filter rows."""
        panel = FilterPanel(columns=["gain_pct", "volume", "price"])
        qtbot.addWidget(panel)

        # Add three filters - should get different columns
        panel._add_btn.click()
        panel._add_btn.click()
        panel._add_btn.click()

        columns = [row.get_column() for row in panel._filter_rows]
        assert len(columns) == len(set(columns)), "Duplicate columns found"
