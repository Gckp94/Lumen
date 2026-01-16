"""Tests for VerticalBarChart component."""

import pytest
from PyQt6.QtWidgets import QApplication

from src.ui.components.vertical_bar_chart import VerticalBarChart


@pytest.fixture(scope="module")
def app():
    """Create QApplication for tests."""
    application = QApplication.instance() or QApplication([])
    yield application


def test_vertical_bar_chart_init(app):
    """Test VerticalBarChart initializes with title."""
    chart = VerticalBarChart(title="Test Chart")
    assert chart._title == "Test Chart"
    assert chart._data == []


def test_vertical_bar_chart_set_data(app):
    """Test VerticalBarChart accepts data."""
    chart = VerticalBarChart(title="Test")
    data = [("2023", 10.5), ("2024", -5.2), ("2025", 15.0)]
    chart.set_data(data, is_percentage=True)
    assert chart._data == data
    assert chart._is_percentage is True
