"""Tests for YearSelectorTabs component."""

import pytest
from PyQt6.QtWidgets import QApplication

from src.ui.components.year_selector_tabs import YearSelectorTabs


@pytest.fixture(scope="module")
def app():
    """Create QApplication for tests."""
    application = QApplication.instance() or QApplication([])
    yield application


def test_year_selector_tabs_init(app):
    """Test YearSelectorTabs initializes."""
    tabs = YearSelectorTabs()
    assert tabs._years == []
    assert tabs._selected_year is None


def test_year_selector_tabs_set_years(app):
    """Test setting available years."""
    tabs = YearSelectorTabs()
    tabs.set_years([2023, 2024, 2025])
    assert tabs._years == [2023, 2024, 2025]
    # Most recent year selected by default
    assert tabs._selected_year == 2025
