"""Widget tests for FilterPanel component."""

from PyQt6.QtCore import Qt
from pytestqt.qtbot import QtBot

from src.ui.components.filter_panel import FilterPanel


class TestFilterPanelApplyFilters:
    """Tests for applying filters."""

    def test_apply_filters_emits_signal(self, qtbot: QtBot) -> None:
        """'Apply Filters' button emits filters_applied signal."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        # Set values in column filter panel
        row = panel._column_filter_panel._rows[0]
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

        # Set values in column filter panel
        row = panel._column_filter_panel._rows[0]
        row._min_input.setText("0")
        row._max_input.setText("10")

        panel._apply_btn.click()

        assert len(panel._filter_chips) == 1


class TestFilterPanelClearFilters:
    """Tests for clearing filters."""

    def test_clear_filters_clears_column_filter_panel(self, qtbot: QtBot) -> None:
        """'Clear All' clears column filter panel values."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        # Set values in column filter panel
        panel._column_filter_panel._rows[0]._min_input.setText("10")
        panel._column_filter_panel._rows[0]._max_input.setText("20")

        panel._clear_btn.click()

        # All rows should be cleared
        for row in panel._column_filter_panel._rows:
            assert not row.has_values()

    def test_clear_filters_emits_signal(self, qtbot: QtBot) -> None:
        """'Clear All' emits filters_cleared signal."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        # Set some values first
        panel._column_filter_panel._rows[0]._min_input.setText("10")
        panel._column_filter_panel._rows[0]._max_input.setText("20")

        with qtbot.waitSignal(panel.filters_cleared, timeout=1000):
            panel._clear_btn.click()

    def test_clear_filters_removes_chips(self, qtbot: QtBot) -> None:
        """'Clear All' removes all FilterChip widgets."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        # Set values and apply to create chips
        row = panel._column_filter_panel._rows[0]
        row._min_input.setText("0")
        row._max_input.setText("10")
        panel._apply_btn.click()

        assert len(panel._filter_chips) == 1

        panel._clear_btn.click()

        assert len(panel._filter_chips) == 0


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

    def test_set_columns_updates_column_filter_panel(self, qtbot: QtBot) -> None:
        """set_columns updates column filter panel rows."""
        panel = FilterPanel(columns=["gain_pct"])
        qtbot.addWidget(panel)

        assert len(panel._column_filter_panel._rows) == 1

        panel.set_columns(["gain_pct", "volume", "price"])

        assert len(panel._column_filter_panel._rows) == 3


class TestFilterPanelColumnFilterPanelIntegration:
    """Tests for ColumnFilterPanel integration."""

    def test_filter_panel_uses_column_filter_panel(self, qtbot: QtBot) -> None:
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
        self, qtbot: QtBot
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

    def test_multiple_filters_can_be_applied(self, qtbot: QtBot) -> None:
        """Multiple column filters can be applied simultaneously."""
        columns = ["gain_pct", "volume", "price"]
        panel = FilterPanel(columns=columns)
        qtbot.addWidget(panel)

        # Set values for multiple columns
        panel._column_filter_panel._rows[0]._min_input.setText("0")
        panel._column_filter_panel._rows[0]._max_input.setText("10")
        panel._column_filter_panel._rows[1]._min_input.setText("100")
        panel._column_filter_panel._rows[1]._max_input.setText("1000")

        with qtbot.waitSignal(panel.filters_applied, timeout=1000) as blocker:
            panel._apply_btn.click()

        criteria_list = blocker.args[0]
        assert len(criteria_list) == 2
        columns_filtered = {c.column for c in criteria_list}
        assert columns_filtered == {"gain_pct", "volume"}
