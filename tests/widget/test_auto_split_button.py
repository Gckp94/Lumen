"""Tests for AutoSplitButton widget."""

import pytest
from PyQt6.QtWidgets import QApplication

from src.tabs.data_binning import AutoSplitButton


@pytest.fixture(scope="module")
def app():
    """Create QApplication for widget tests."""
    return QApplication.instance() or QApplication([])


class TestAutoSplitButton:
    """Tests for AutoSplitButton custom widget."""

    def test_button_creation_quartile(self, app) -> None:
        """AutoSplitButton creates with correct label and segment count."""
        btn = AutoSplitButton("Q4", 4)
        assert btn.label == "Q4"
        assert btn.segments == 4
        assert btn.width() == 68
        assert btn.height() == 44

    def test_button_creation_quintile(self, app) -> None:
        """AutoSplitButton creates for quintile."""
        btn = AutoSplitButton("Q5", 5)
        assert btn.label == "Q5"
        assert btn.segments == 5

    def test_button_creation_decile(self, app) -> None:
        """AutoSplitButton creates for decile."""
        btn = AutoSplitButton("D10", 10)
        assert btn.label == "D10"
        assert btn.segments == 10
