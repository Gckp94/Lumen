"""Table displaying range analysis results for a feature."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from src.core.feature_analyzer import FeatureAnalysisResult, RangeClassification


class RangeAnalysisTable(QWidget):
    """Table showing range breakdown for a selected feature."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "Range", "Trades", "EV", "Win Rate", "Total PnL", "Classification"
        ])

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self._table.setStyleSheet("""
            QTableWidget {
                background-color: #2a2a2a;
                gridline-color: #444;
            }
            QHeaderView::section {
                background-color: #333;
                padding: 8px;
                border: none;
            }
        """)

        layout.addWidget(self._table)

    def update_data(self, feature: FeatureAnalysisResult) -> None:
        """Update table with feature range data."""
        from src.core.feature_analyzer import RangeClassification

        self._table.setRowCount(len(feature.ranges))

        for row, range_result in enumerate(feature.ranges):
            # Range
            self._table.setItem(row, 0, QTableWidgetItem(range_result.range_label))

            # Trades
            self._table.setItem(row, 1, QTableWidgetItem(str(range_result.trade_count)))

            # EV
            ev_text = f"{range_result.ev * 100:.2f}%" if range_result.ev else "N/A"
            self._table.setItem(row, 2, QTableWidgetItem(ev_text))

            # Win Rate
            wr_text = f"{range_result.win_rate:.1f}%" if range_result.win_rate else "N/A"
            self._table.setItem(row, 3, QTableWidgetItem(wr_text))

            # Total PnL
            pnl_text = f"{range_result.total_pnl * 100:.2f}%"
            self._table.setItem(row, 4, QTableWidgetItem(pnl_text))

            # Classification with color
            class_item = QTableWidgetItem(range_result.classification.value.upper())
            if range_result.classification == RangeClassification.FAVORABLE:
                class_item.setForeground(Qt.GlobalColor.green)
            elif range_result.classification == RangeClassification.UNFAVORABLE:
                class_item.setForeground(Qt.GlobalColor.red)
            elif range_result.classification == RangeClassification.INSUFFICIENT:
                class_item.setForeground(Qt.GlobalColor.gray)
            self._table.setItem(row, 5, class_item)
