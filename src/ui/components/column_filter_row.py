# src/ui/components/column_filter_row.py
"""ColumnFilterRow component for inline column filtering."""

from typing import Literal

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from src.core.models import FilterCriteria
from src.ui.constants import Colors, Fonts, Spacing


class ColumnFilterRow(QWidget):
    """Single row for filtering a column with inline min/max inputs.

    Attributes:
        values_changed: Signal emitted when min/max values change.
        operator_changed: Signal emitted when operator toggles.
    """

    values_changed = pyqtSignal()
    operator_changed = pyqtSignal()

    def __init__(
        self,
        column_name: str,
        alternate: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize ColumnFilterRow.

        Args:
            column_name: Name of the column this row filters.
            alternate: Whether to use alternate background color.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._column_name = column_name
        self._alternate = alternate
        self._operator: Literal["between", "not_between"] = "between"
        self._setup_ui()
        self._apply_style()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the row UI layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.XS, Spacing.SM, Spacing.XS)
        layout.setSpacing(Spacing.SM)

        # Column name label (fixed width for alignment)
        self._column_label = QLabel(self._column_name)
        self._column_label.setFixedWidth(140)
        layout.addWidget(self._column_label)

        # Operator toggle button
        self._operator_btn = QPushButton("between")
        self._operator_btn.setFixedWidth(90)
        self._operator_btn.clicked.connect(self._toggle_operator)
        layout.addWidget(self._operator_btn)

        # Min input
        self._min_input = QLineEdit()
        self._min_input.setValidator(QDoubleValidator())
        self._min_input.setPlaceholderText("Min")
        self._min_input.setFixedWidth(70)
        layout.addWidget(self._min_input)

        # Max input
        self._max_input = QLineEdit()
        self._max_input.setValidator(QDoubleValidator())
        self._max_input.setPlaceholderText("Max")
        self._max_input.setFixedWidth(70)
        layout.addWidget(self._max_input)

        # Active indicator (amber dot when has values)
        self._indicator = QLabel()
        self._indicator.setFixedSize(8, 8)
        layout.addWidget(self._indicator)

        layout.addStretch()

    def _apply_style(self) -> None:
        """Apply Observatory theme styling."""
        bg_color = Colors.BG_ELEVATED if self._alternate else Colors.BG_SURFACE
        self.setStyleSheet(f"""
            ColumnFilterRow {{
                background-color: {bg_color};
            }}
            ColumnFilterRow:hover {{
                background-color: {Colors.BG_BORDER};
            }}
        """)

        self._column_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: "{Fonts.DATA}";
                font-size: 12px;
            }}
        """)

        self._operator_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 3px;
                padding: 2px 6px;
                font-family: "{Fonts.UI}";
                font-size: 11px;
            }}
            QPushButton:hover {{
                border-color: {Colors.SIGNAL_CYAN};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)

        input_style = f"""
            QLineEdit {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 3px;
                padding: 2px 6px;
                font-family: "{Fonts.DATA}";
                font-size: 12px;
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

        self._update_indicator()

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self._min_input.textChanged.connect(self._on_values_changed)
        self._max_input.textChanged.connect(self._on_values_changed)

    def _on_values_changed(self) -> None:
        """Handle min/max value changes."""
        self._update_indicator()
        self.values_changed.emit()

    def _update_indicator(self) -> None:
        """Update the active indicator based on input state."""
        if self.has_values():
            self._indicator.setStyleSheet(f"""
                QLabel {{
                    background-color: {Colors.SIGNAL_AMBER};
                    border-radius: 4px;
                }}
            """)
        else:
            self._indicator.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                }
            """)

    def _toggle_operator(self) -> None:
        """Toggle between 'between' and 'not_between' operators."""
        if self._operator == "between":
            self._operator = "not_between"
            self._operator_btn.setText("not between")
        else:
            self._operator = "between"
            self._operator_btn.setText("between")
        self.operator_changed.emit()

    def get_column_name(self) -> str:
        """Get the column name for this row.

        Returns:
            Column name string.
        """
        return self._column_name

    def get_operator(self) -> Literal["between", "not_between"]:
        """Get current operator.

        Returns:
            Current operator value.
        """
        return self._operator

    def has_values(self) -> bool:
        """Check if both min and max have values.

        Returns:
            True if both inputs have text, False otherwise.
        """
        return bool(self._min_input.text().strip() and self._max_input.text().strip())

    def get_criteria(self) -> FilterCriteria | None:
        """Get FilterCriteria if inputs are valid.

        Returns:
            FilterCriteria object if valid, None otherwise.
        """
        min_text = self._min_input.text().strip()
        max_text = self._max_input.text().strip()

        if not min_text or not max_text:
            return None

        try:
            min_val = float(min_text)
            max_val = float(max_text)
        except ValueError:
            return None

        criteria = FilterCriteria(
            column=self._column_name,
            operator=self._operator,
            min_val=min_val,
            max_val=max_val,
        )

        # validate() returns None if valid, error message if invalid
        if criteria.validate() is not None:
            return None

        return criteria

    def clear_values(self) -> None:
        """Clear min and max input values."""
        self._min_input.clear()
        self._max_input.clear()

    def set_values(self, min_val: float | None, max_val: float | None) -> None:
        """Set min and max input values.

        Args:
            min_val: Minimum value or None to clear.
            max_val: Maximum value or None to clear.
        """
        self._min_input.setText(str(min_val) if min_val is not None else "")
        self._max_input.setText(str(max_val) if max_val is not None else "")
