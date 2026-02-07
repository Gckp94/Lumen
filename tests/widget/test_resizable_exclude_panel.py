"""Tests for ResizableExcludePanel widget."""

import pytest
from pytestqt.qtbot import QtBot
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.ui.components.resizable_exclude_panel import ResizableExcludePanel


class TestResizableExcludePanelCreation:
    """Test panel creation and basic properties."""

    def test_panel_creates_with_default_width(self, qtbot: QtBot) -> None:
        """Panel should create with 280px default width."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        assert panel.width() >= 180  # Minimum width
        assert panel.minimumWidth() == 180

    def test_panel_has_search_input(self, qtbot: QtBot) -> None:
        """Panel should have a search input field."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        assert panel._search_input is not None
        assert panel._search_input.placeholderText() == "Search columns..."

    def test_panel_has_checkbox_list(self, qtbot: QtBot) -> None:
        """Panel should have a scrollable checkbox list."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        assert panel._checkbox_list is not None


class TestResizableExcludePanelWidthConstraints:
    """Test width constraint properties."""

    def test_minimum_width_constant(self, qtbot: QtBot) -> None:
        """MIN_WIDTH should be 180."""
        assert ResizableExcludePanel.MIN_WIDTH == 180

    def test_default_width_constant(self, qtbot: QtBot) -> None:
        """DEFAULT_WIDTH should be 280."""
        assert ResizableExcludePanel.DEFAULT_WIDTH == 280

    def test_maximum_width_constant(self, qtbot: QtBot) -> None:
        """MAX_WIDTH should be 400."""
        assert ResizableExcludePanel.MAX_WIDTH == 400

    def test_panel_respects_minimum_width(self, qtbot: QtBot) -> None:
        """Panel should enforce minimum width."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        assert panel.minimumWidth() == ResizableExcludePanel.MIN_WIDTH

    def test_panel_respects_maximum_width(self, qtbot: QtBot) -> None:
        """Panel should enforce maximum width."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        assert panel.maximumWidth() == ResizableExcludePanel.MAX_WIDTH

    def test_size_hint_uses_default_width(self, qtbot: QtBot) -> None:
        """sizeHint should return DEFAULT_WIDTH."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        assert panel.sizeHint().width() == ResizableExcludePanel.DEFAULT_WIDTH


class TestResizableExcludePanelColumns:
    """Test column management."""

    def test_set_columns_creates_checkboxes(self, qtbot: QtBot) -> None:
        """set_columns should create checkbox for each column."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        columns = ["alpha", "beta", "gamma"]
        panel.set_columns(columns)

        assert len(panel._checkboxes) == 3
        assert "alpha" in panel._checkboxes
        assert "beta" in panel._checkboxes
        assert "gamma" in panel._checkboxes

    def test_set_columns_sorts_alphabetically(self, qtbot: QtBot) -> None:
        """Columns should be sorted alphabetically."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        columns = ["zebra", "apple", "mango"]
        panel.set_columns(columns)

        assert panel._columns == ["apple", "mango", "zebra"]

    def test_checkboxes_have_tooltips(self, qtbot: QtBot) -> None:
        """Each checkbox should have tooltip with full column name."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        columns = ["very_long_column_name"]
        panel.set_columns(columns)

        checkbox = panel._checkboxes["very_long_column_name"]
        assert checkbox.toolTip() == "very_long_column_name"

    def test_set_columns_clears_previous(self, qtbot: QtBot) -> None:
        """set_columns should clear previous checkboxes."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        panel.set_columns(["a", "b"])
        assert len(panel._checkboxes) == 2

        panel.set_columns(["x", "y", "z"])
        assert len(panel._checkboxes) == 3
        assert "a" not in panel._checkboxes
        assert "x" in panel._checkboxes


class TestResizableExcludePanelExclusion:
    """Test exclusion state management."""

    def test_get_excluded_returns_empty_initially(self, qtbot: QtBot) -> None:
        """get_excluded should return empty set initially."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        assert panel.get_excluded() == set()

    def test_set_excluded_updates_checkboxes(self, qtbot: QtBot) -> None:
        """set_excluded should uncheck excluded columns."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        panel.set_columns(["a", "b", "c"])
        panel.set_excluded({"b"})

        assert panel._checkboxes["a"].isChecked()
        assert not panel._checkboxes["b"].isChecked()
        assert panel._checkboxes["c"].isChecked()

    def test_get_excluded_reflects_set_excluded(self, qtbot: QtBot) -> None:
        """get_excluded should return what was set."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        panel.set_columns(["a", "b", "c"])
        panel.set_excluded({"a", "c"})

        assert panel.get_excluded() == {"a", "c"}

    def test_unchecking_checkbox_adds_to_excluded(self, qtbot: QtBot) -> None:
        """Unchecking a checkbox should add column to excluded set."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        panel.set_columns(["a", "b"])
        panel._checkboxes["a"].setChecked(False)

        assert "a" in panel.get_excluded()

    def test_checking_checkbox_removes_from_excluded(self, qtbot: QtBot) -> None:
        """Checking a checkbox should remove column from excluded set."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        panel.set_columns(["a", "b"])
        panel.set_excluded({"a", "b"})
        panel._checkboxes["a"].setChecked(True)

        assert "a" not in panel.get_excluded()
        assert "b" in panel.get_excluded()


class TestResizableExcludePanelSignals:
    """Test signal emissions."""

    def test_exclusion_changed_emitted_on_uncheck(self, qtbot: QtBot) -> None:
        """exclusion_changed should emit when checkbox unchecked."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        panel.set_columns(["a", "b"])

        with qtbot.waitSignal(panel.exclusion_changed, timeout=1000) as blocker:
            panel._checkboxes["a"].setChecked(False)

        assert blocker.args == ["a", True]  # column, is_excluded

    def test_exclusion_changed_emitted_on_check(self, qtbot: QtBot) -> None:
        """exclusion_changed should emit when checkbox checked."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        panel.set_columns(["a", "b"])
        panel.set_excluded({"a"})

        with qtbot.waitSignal(panel.exclusion_changed, timeout=1000) as blocker:
            panel._checkboxes["a"].setChecked(True)

        assert blocker.args == ["a", False]  # column, is_excluded

    def test_exclusions_updated_emitted_on_set_excluded(self, qtbot: QtBot) -> None:
        """exclusions_updated should emit when set_excluded called."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        panel.set_columns(["a", "b", "c"])

        with qtbot.waitSignal(panel.exclusions_updated, timeout=1000) as blocker:
            panel.set_excluded({"a", "c"})

        assert blocker.args[0] == {"a", "c"}


class TestResizableExcludePanelSearch:
    """Test search/filter functionality."""

    def test_search_filters_checkboxes(self, qtbot: QtBot) -> None:
        """Search input should filter visible checkboxes."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        panel.set_columns(["alpha", "beta", "gamma"])
        panel._search_input.setText("alpha")

        # Use isHidden() since isVisible() requires widget to be shown
        assert not panel._checkboxes["alpha"].isHidden()
        assert panel._checkboxes["beta"].isHidden()
        assert panel._checkboxes["gamma"].isHidden()

    def test_search_is_case_insensitive(self, qtbot: QtBot) -> None:
        """Search should be case-insensitive."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        panel.set_columns(["Alpha", "Beta"])
        panel._search_input.setText("ALPHA")

        assert not panel._checkboxes["Alpha"].isHidden()
        assert panel._checkboxes["Beta"].isHidden()

    def test_clear_search_shows_all(self, qtbot: QtBot) -> None:
        """Clearing search should show all checkboxes."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        panel.set_columns(["alpha", "beta"])
        panel._search_input.setText("alpha")
        panel._search_input.clear()

        assert not panel._checkboxes["alpha"].isHidden()
        assert not panel._checkboxes["beta"].isHidden()

    def test_search_partial_match(self, qtbot: QtBot) -> None:
        """Search should match partial strings."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        panel.set_columns(["column_one", "column_two", "other"])
        panel._search_input.setText("column")

        assert not panel._checkboxes["column_one"].isHidden()
        assert not panel._checkboxes["column_two"].isHidden()
        assert panel._checkboxes["other"].isHidden()

    def test_search_input_has_clear_button(self, qtbot: QtBot) -> None:
        """Search input should have clear button enabled."""
        panel = ResizableExcludePanel()
        qtbot.addWidget(panel)

        assert panel._search_input.isClearButtonEnabled()
