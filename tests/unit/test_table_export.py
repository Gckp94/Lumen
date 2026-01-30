"""Tests for table export utilities."""

import pytest
from PyQt6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for widget tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestTableToMarkdown:
    """Tests for QTableWidget to markdown conversion."""

    def test_converts_simple_table(self, qapp):
        """Should convert a simple table to markdown."""
        from src.utils.table_export import table_to_markdown

        table = QTableWidget(2, 2)
        table.setHorizontalHeaderLabels(["Col A", "Col B"])
        table.setItem(0, 0, QTableWidgetItem("a1"))
        table.setItem(0, 1, QTableWidgetItem("b1"))
        table.setItem(1, 0, QTableWidgetItem("a2"))
        table.setItem(1, 1, QTableWidgetItem("b2"))

        result = table_to_markdown(table)

        assert "| Col A | Col B |" in result
        assert "| a1 | b1 |" in result
        assert "| a2 | b2 |" in result
        assert "| --- | --- |" in result

    def test_handles_empty_table(self, qapp):
        """Should return empty string for empty table."""
        from src.utils.table_export import table_to_markdown

        table = QTableWidget(0, 0)

        result = table_to_markdown(table)

        assert result == ""

    def test_handles_none_items(self, qapp):
        """Should handle cells with no QTableWidgetItem."""
        from src.utils.table_export import table_to_markdown

        table = QTableWidget(1, 2)
        table.setHorizontalHeaderLabels(["A", "B"])
        table.setItem(0, 0, QTableWidgetItem("value"))
        # Item at (0, 1) is None

        result = table_to_markdown(table)

        assert "| value |" in result

    def test_includes_title_when_provided(self, qapp):
        """Should include title as header when provided."""
        from src.utils.table_export import table_to_markdown

        table = QTableWidget(1, 1)
        table.setHorizontalHeaderLabels(["Col"])
        table.setItem(0, 0, QTableWidgetItem("val"))

        result = table_to_markdown(table, title="My Table")

        assert "## My Table" in result
