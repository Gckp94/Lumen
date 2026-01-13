"""FilterRow component for filter input."""

from typing import Literal

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from src.core.models import FilterCriteria
from src.ui.components.no_scroll_widgets import NoScrollComboBox
from src.ui.constants import Colors, Spacing


class FilterRow(QWidget):
    """Input row for defining a single filter criterion.

    Attributes:
        filter_changed: Signal emitted when filter value changes (FilterCriteria or None).
        validation_failed: Signal emitted when validation fails with error message.
        remove_requested: Signal emitted when remove button is clicked.
        column_changed: Signal emitted when column selection changes (old_col, new_col).
    """

    filter_changed = pyqtSignal(object)  # FilterCriteria | None
    validation_failed = pyqtSignal(str)
    remove_requested = pyqtSignal()
    column_changed = pyqtSignal(str, str)  # old_column, new_column

    def __init__(
        self,
        columns: list[str],
        parent: QWidget | None = None,
    ) -> None:
        """Initialize FilterRow.

        Args:
            columns: List of numeric column names for dropdown.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._columns = columns
        self._previous_column = columns[0] if columns else ""
        self._setup_ui()
        self._apply_style()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the row UI layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, Spacing.XS, 0, Spacing.XS)
        layout.setSpacing(Spacing.SM)

        # Column dropdown
        self._column_combo = NoScrollComboBox()
        self._column_combo.addItems(self._columns)
        self._column_combo.setMinimumWidth(100)
        layout.addWidget(self._column_combo)

        # Operator dropdown
        self._operator_combo = NoScrollComboBox()
        self._operator_combo.addItems(["between", "not between"])
        self._operator_combo.setMinimumWidth(100)
        layout.addWidget(self._operator_combo)

        # Min input
        self._min_label = QLabel("Min:")
        layout.addWidget(self._min_label)

        self._min_input = QLineEdit()
        self._min_input.setValidator(QDoubleValidator())
        self._min_input.setPlaceholderText("0.0")
        self._min_input.setFixedWidth(80)
        layout.addWidget(self._min_input)

        # Max input
        self._max_label = QLabel("Max:")
        layout.addWidget(self._max_label)

        self._max_input = QLineEdit()
        self._max_input.setValidator(QDoubleValidator())
        self._max_input.setPlaceholderText("100.0")
        self._max_input.setFixedWidth(80)
        layout.addWidget(self._max_input)

        # Remove button
        self._remove_btn = QPushButton("\u2715")  # ✕
        self._remove_btn.setFixedSize(24, 24)
        layout.addWidget(self._remove_btn)

        layout.addStretch()

    def _apply_style(self) -> None:
        """Apply Observatory theme styling."""
        combo_style = f"""
            QComboBox {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QComboBox:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                selection-background-color: {Colors.BG_BORDER};
                selection-color: {Colors.TEXT_PRIMARY};
            }}
        """
        self._column_combo.setStyleSheet(combo_style)
        self._operator_combo.setStyleSheet(combo_style)

        input_style = f"""
            QLineEdit {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QLineEdit:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QLineEdit:focus {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
        """
        self._min_input.setStyleSheet(input_style)
        self._max_input.setStyleSheet(input_style)

        label_style = f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
            }}
        """
        self._min_label.setStyleSheet(label_style)
        self._max_label.setStyleSheet(label_style)

        self._remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                color: {Colors.SIGNAL_CORAL};
                border-color: {Colors.SIGNAL_CORAL};
            }}
        """)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self._remove_btn.clicked.connect(self.remove_requested.emit)
        self._column_combo.currentTextChanged.connect(self._on_column_changed)

    def _on_column_changed(self, new_column: str) -> None:
        """Handle column selection change.

        Args:
            new_column: Newly selected column name.
        """
        old_column = self._previous_column
        self._previous_column = new_column
        self.column_changed.emit(old_column, new_column)

    def get_column(self) -> str:
        """Get currently selected column name.

        Returns:
            Current column name or empty string if none selected.
        """
        return self._column_combo.currentText()

    def set_column(self, column: str) -> None:
        """Set the selected column.

        Args:
            column: Column name to select.
        """
        if column in self._columns:
            self._column_combo.setCurrentText(column)

    def get_available_columns(self) -> list[str]:
        """Get list of columns available in dropdown.

        Returns:
            List of column names in the dropdown.
        """
        return self._columns.copy()

    def get_criteria(self) -> FilterCriteria | None:
        """Get current filter criteria from inputs.

        Returns:
            FilterCriteria if inputs are valid, None otherwise.
        """
        column = self._column_combo.currentText()
        operator_text = self._operator_combo.currentText()
        operator: Literal["between", "not_between"] = (
            "between" if operator_text == "between" else "not_between"
        )

        min_text = self._min_input.text().strip()
        max_text = self._max_input.text().strip()

        if not min_text or not max_text:
            self.validation_failed.emit("Min and max values are required")
            return None

        try:
            min_val = float(min_text)
            max_val = float(max_text)
        except ValueError:
            self.validation_failed.emit("Min and max must be numeric values")
            return None

        criteria = FilterCriteria(
            column=column,
            operator=operator,
            min_val=min_val,
            max_val=max_val,
        )

        error = criteria.validate()
        if error:
            self.validation_failed.emit(error)
            return None

        return criteria

    def set_columns(self, columns: list[str]) -> None:
        """Update available columns.

        Args:
            columns: New list of column names.
        """
        current = self._column_combo.currentText()
        self._column_combo.blockSignals(True)
        self._column_combo.clear()
        self._column_combo.addItems(columns)
        if current in columns:
            self._column_combo.setCurrentText(current)
        self._column_combo.blockSignals(False)
        self._columns = columns
        self._previous_column = self._column_combo.currentText()
