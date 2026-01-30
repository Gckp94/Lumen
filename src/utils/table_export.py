"""Utilities for exporting table data to various formats."""

from PyQt6.QtWidgets import QTableWidget


def table_to_markdown(table: QTableWidget, title: str | None = None) -> str:
    """Convert a QTableWidget to markdown table format.

    Args:
        table: The QTableWidget to convert.
        title: Optional title to include as a header.

    Returns:
        Markdown-formatted string representation of the table.
    """
    if table.rowCount() == 0 or table.columnCount() == 0:
        return ""

    lines = []

    # Add title if provided
    if title:
        lines.append(f"## {title}")
        lines.append("")

    # Get column headers
    headers = []
    for col in range(table.columnCount()):
        header_item = table.horizontalHeaderItem(col)
        headers.append(header_item.text() if header_item else f"Col {col}")

    # Header row
    lines.append("| " + " | ".join(headers) + " |")

    # Separator row
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    # Data rows
    for row in range(table.rowCount()):
        cells = []
        for col in range(table.columnCount()):
            item = table.item(row, col)
            cells.append(item.text() if item else "")
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines)
