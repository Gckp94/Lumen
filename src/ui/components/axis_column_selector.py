"""Axis column selector for choosing X and Y plot columns.

Provides two dropdowns for selecting which DataFrame columns to plot
on the X and Y axes of a scatter chart.
"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.ui.components.no_scroll_widgets import NoScrollComboBox
from src.ui.constants import Colors, Spacing

# Sentinel value for index-based X axis
INDEX_OPTION = "(Index)"


class AxisColumnSelector(QWidget):
    """Dropdown selectors for X and Y axis columns.

    Provides two combo boxes: one for X-axis (with Index option) and one
    for Y-axis. Emits selection_changed when either selection changes.

    Signals:
        selection_changed: Emitted when X or Y selection changes.

    Properties:
        x_column: Selected X column name, or None if Index selected.
        y_column: Selected Y column name.
    """

    selection_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the AxisColumnSelector.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._setup_ui()
        self._apply_style()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the selector layout with X and Y dropdowns."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, Spacing.SM)
        layout.setSpacing(Spacing.SM)

        # Section label
        section_label = QLabel("Plot Columns")
        section_label.setObjectName("section_label")
        layout.addWidget(section_label)

        # X-axis row
        x_row = QHBoxLayout()
        x_row.setSpacing(Spacing.SM)

        x_label = QLabel("X:")
        x_label.setFixedWidth(20)
        x_label.setObjectName("axis_label")
        x_row.addWidget(x_label)

        self._x_combo = NoScrollComboBox()
        self._x_combo.addItem(INDEX_OPTION)
        self._x_combo.setEnabled(False)
        x_row.addWidget(self._x_combo, stretch=1)

        layout.addLayout(x_row)

        # Y-axis row
        y_row = QHBoxLayout()
        y_row.setSpacing(Spacing.SM)

        y_label = QLabel("Y:")
        y_label.setFixedWidth(20)
        y_label.setObjectName("axis_label")
        y_row.addWidget(y_label)

        self._y_combo = NoScrollComboBox()
        self._y_combo.setEnabled(False)
        y_row.addWidget(self._y_combo, stretch=1)

        layout.addLayout(y_row)

    def _apply_style(self) -> None:
        """Apply Observatory theme styling."""
        # Section label style
        section_style = f"""
            QLabel#section_label {{
                color: {Colors.TEXT_PRIMARY};
                font-size: 12px;
                font-weight: bold;
            }}
        """
        self.setStyleSheet(section_style)

        # Axis label style
        for label in self.findChildren(QLabel):
            if label.objectName() == "axis_label":
                label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")

        # Combo box style (matching existing column_selector)
        combo_style = f"""
            QComboBox {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 13px;
            }}
            QComboBox:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                selection-background-color: {Colors.BG_BORDER};
                selection-color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
            }}
        """
        self._x_combo.setStyleSheet(combo_style)
        self._y_combo.setStyleSheet(combo_style)

    def _connect_signals(self) -> None:
        """Connect combo box signals to emit selection_changed."""
        self._x_combo.currentTextChanged.connect(self._on_selection_changed)
        self._y_combo.currentTextChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self, _text: str) -> None:
        """Handle combo selection change."""
        self.selection_changed.emit()

    def set_columns(self, columns: list[str]) -> None:
        """Populate dropdowns with available columns.

        Args:
            columns: List of column names to add to dropdowns.
        """
        # Block signals during population
        self._x_combo.blockSignals(True)
        self._y_combo.blockSignals(True)

        # Clear and repopulate X combo (keep Index option)
        self._x_combo.clear()
        self._x_combo.addItem(INDEX_OPTION)
        self._x_combo.addItems(columns)

        # Clear and repopulate Y combo
        self._y_combo.clear()
        self._y_combo.addItems(columns)

        # Enable if columns available
        has_columns = len(columns) > 0
        self._x_combo.setEnabled(has_columns)
        self._y_combo.setEnabled(has_columns)

        self._x_combo.blockSignals(False)
        self._y_combo.blockSignals(False)

    @property
    def x_column(self) -> str | None:
        """Get selected X column, or None if Index is selected."""
        text = self._x_combo.currentText()
        return None if text == INDEX_OPTION else text

    @property
    def y_column(self) -> str:
        """Get selected Y column name."""
        return self._y_combo.currentText()

    def set_y_column(self, column: str) -> None:
        """Set the Y column selection.

        Args:
            column: Column name to select.
        """
        index = self._y_combo.findText(column)
        if index >= 0:
            self._y_combo.setCurrentIndex(index)
