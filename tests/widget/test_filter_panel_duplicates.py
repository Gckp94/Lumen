"""Widget tests for FilterPanel duplicate column prevention (AC: 2).

These tests verify that:
- Adding a filter excludes already-used columns from the dropdown
- Removing a filter makes the column available again
- No duplicate columns can exist across multiple filter rows
"""

from pytestqt.qtbot import QtBot

from src.ui.components.filter_panel import FilterPanel


class TestAddFilterExcludesUsedColumns:
    """Tests for column exclusion when adding filters."""

    def test_second_filter_excludes_first_column(self, qtbot: QtBot) -> None:
        """Second filter row doesn't have first filter's column."""
        panel = FilterPanel(columns=["gain_pct", "volume", "price"])
        qtbot.addWidget(panel)

        # Add first filter (defaults to first available column)
        panel._add_btn.click()
        assert panel._filter_rows[0].get_column() == "gain_pct"

        # Add second filter
        panel._add_btn.click()
        available = panel._filter_rows[1].get_available_columns()

        assert "gain_pct" not in available
        assert "volume" in available
        assert "price" in available

    def test_third_filter_excludes_first_two_columns(self, qtbot: QtBot) -> None:
        """Third filter excludes both previously used columns."""
        panel = FilterPanel(columns=["gain_pct", "volume", "price"])
        qtbot.addWidget(panel)

        panel._add_btn.click()  # gain_pct
        panel._add_btn.click()  # volume
        panel._add_btn.click()  # price

        # Third row should only have price available (first column not used by others)
        third_available = panel._filter_rows[2].get_available_columns()
        assert len(third_available) == 1
        assert "price" in third_available


class TestRemoveFilterMakesColumnAvailable:
    """Tests for column availability after filter removal."""

    def test_removing_filter_frees_column(self, qtbot: QtBot) -> None:
        """Removing a filter makes its column available again."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        # Add filter for gain_pct
        panel._add_btn.click()
        assert panel._filter_rows[0].get_column() == "gain_pct"

        # Remove the filter
        panel._filter_rows[0]._remove_btn.click()
        qtbot.wait(10)  # Allow deleteLater to process

        # Add new filter - gain_pct should be available again
        panel._add_btn.click()
        available = panel._filter_rows[0].get_available_columns()

        assert "gain_pct" in available
        assert "volume" in available

    def test_removing_middle_filter_frees_column(self, qtbot: QtBot) -> None:
        """Removing a filter from the middle frees its column."""
        panel = FilterPanel(columns=["gain_pct", "volume", "price"])
        qtbot.addWidget(panel)

        panel._add_btn.click()  # gain_pct
        panel._add_btn.click()  # volume
        panel._add_btn.click()  # price

        # Remove middle filter (volume)
        panel._filter_rows[1]._remove_btn.click()
        qtbot.wait(10)

        # Add new filter - volume should be available
        panel._add_btn.click()
        new_row_available = panel._filter_rows[2].get_available_columns()

        assert "volume" in new_row_available
        assert "gain_pct" not in new_row_available
        assert "price" not in new_row_available


class TestAddButtonDisabledWhenAllColumnsUsed:
    """Tests for add button state when all columns are used."""

    def test_add_disabled_when_all_columns_used(self, qtbot: QtBot) -> None:
        """Add button is disabled when all columns have filters."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        panel._add_btn.click()  # gain_pct
        panel._add_btn.click()  # volume

        assert not panel._add_btn.isEnabled()

    def test_add_re_enabled_after_removing_filter(self, qtbot: QtBot) -> None:
        """Add button is re-enabled when a column becomes available."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        panel._add_btn.click()
        panel._add_btn.click()
        assert not panel._add_btn.isEnabled()

        # Remove one filter
        panel._filter_rows[0]._remove_btn.click()
        qtbot.wait(10)

        assert panel._add_btn.isEnabled()


class TestGetUsedColumns:
    """Tests for _get_used_columns helper method."""

    def test_get_used_columns_empty_initially(self, qtbot: QtBot) -> None:
        """No columns used initially."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        used = panel._get_used_columns()
        assert used == set()

    def test_get_used_columns_tracks_filters(self, qtbot: QtBot) -> None:
        """Used columns set matches filter row columns."""
        panel = FilterPanel(columns=["gain_pct", "volume", "price"])
        qtbot.addWidget(panel)

        panel._add_btn.click()  # gain_pct
        panel._add_btn.click()  # volume

        used = panel._get_used_columns()
        assert used == {"gain_pct", "volume"}

    def test_get_used_columns_updates_on_removal(self, qtbot: QtBot) -> None:
        """Used columns set updates when filter is removed."""
        panel = FilterPanel(columns=["gain_pct", "volume"])
        qtbot.addWidget(panel)

        panel._add_btn.click()  # gain_pct
        panel._add_btn.click()  # volume
        assert panel._get_used_columns() == {"gain_pct", "volume"}

        panel._filter_rows[0]._remove_btn.click()
        qtbot.wait(10)

        assert panel._get_used_columns() == {"volume"}


class TestNoDuplicateColumns:
    """Tests to ensure no duplicate columns across filters."""

    def test_all_filter_columns_unique(self, qtbot: QtBot) -> None:
        """All filter rows have unique columns."""
        panel = FilterPanel(columns=["gain_pct", "volume", "price", "delta"])
        qtbot.addWidget(panel)

        # Add multiple filters
        panel._add_btn.click()
        panel._add_btn.click()
        panel._add_btn.click()
        panel._add_btn.click()

        columns = [row.get_column() for row in panel._filter_rows]
        assert len(columns) == len(set(columns)), f"Duplicate columns found: {columns}"

    def test_max_filters_with_unique_columns(self, qtbot: QtBot) -> None:
        """All 10 filters can be added with unique columns."""
        columns = [f"col_{i}" for i in range(10)]
        panel = FilterPanel(columns=columns)
        qtbot.addWidget(panel)

        for _ in range(10):
            panel._add_btn.click()

        assert len(panel._filter_rows) == 10

        used = [row.get_column() for row in panel._filter_rows]
        assert len(used) == len(set(used)), "Duplicate columns found in 10 filters"
