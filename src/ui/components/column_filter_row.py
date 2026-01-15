# src/ui/components/column_filter_row.py
"""ColumnFilterRow component for inline column filtering."""

from typing import Literal, TypeAlias

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from src.core.models import FilterCriteria
from src.ui.constants import Colors, Fonts, Spacing

# Type alias for filter operator to avoid long lines
FilterOp: TypeAlias = Literal[
    "between", "not_between", "between_blanks", "not_between_blanks"
]


class ColumnFilterRow(QWidget):
    """Single row for filtering a column with inline min/max inputs.

    Attributes:
        values_changed: Signal emitted when min/max values change.
        operator_changed: Signal emitted when operator toggles.
        apply_clicked: Signal emitted with column name when apply button clicked.
    """

    values_changed = pyqtSignal()
    operator_changed = pyqtSignal()
    apply_clicked = pyqtSignal(str)  # Emits column name when clicked

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
        self._operator: FilterOp = "between"
        self._setup_ui()
        self._apply_style()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the row UI layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.XS, Spacing.SM, Spacing.XS)
        layout.setSpacing(Spacing.SM)

        # Column name label (responsive width with minimum)
        self._column_label = QLabel(self._column_name)
        self._column_label.setMinimumWidth(80)
        self._column_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        # Enable text elision for long names
        self._column_label.setWordWrap(False)
        self._column_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self._column_label, stretch=1)

        # Operator toggle button
        self._operator_btn = QPushButton("between")
        # Width sized to fit "not between + blanks"
        self._operator_btn.setMinimumWidth(130)
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

        # Apply button (for applying this single filter)
        self._apply_btn = QPushButton("+")
        self._apply_btn.setFixedSize(22, 22)
        self._apply_btn.setToolTip("Apply this filter")
        self._apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
                font-family: "{Fonts.UI}";
                color: {Colors.TEXT_SECONDARY};
            }}
            QPushButton:hover {{
                background: {Colors.BG_BORDER};
                border-color: {Colors.SIGNAL_AMBER};
                color: {Colors.SIGNAL_AMBER};
            }}
            QPushButton:pressed {{
                background: {Colors.BG_ELEVATED};
            }}
            QPushButton:disabled {{
                color: {Colors.TEXT_DISABLED};
                border-color: transparent;
            }}
        """)
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._on_apply_clicked)
        layout.addWidget(self._apply_btn)

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
        """Update the active indicator and apply button based on input state."""
        has_vals = self.has_values()
        if has_vals:
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
        # Enable/disable apply button based on whether filter has values
        self._apply_btn.setEnabled(has_vals)

    def _on_apply_clicked(self) -> None:
        """Emit apply signal with column name."""
        self.apply_clicked.emit(self._column_name)

    def _toggle_operator(self) -> None:
        """Cycle through filter operators: between, not between, +blanks variants."""
        operators: list[tuple[FilterOp, str]] = [
            ("between", "between"),
            ("not_between", "not between"),
            ("between_blanks", "between + blanks"),
            ("not_between_blanks", "not between + blanks"),
        ]

        # Find current index and advance to next
        current_idx = next(
            (i for i, (op, _) in enumerate(operators) if op == self._operator), 0
        )
        next_idx = (current_idx + 1) % len(operators)

        self._operator, display_text = operators[next_idx]
        self._operator_btn.setText(display_text)
        self.operator_changed.emit()

    def get_column_name(self) -> str:
        """Get the column name for this row.

        Returns:
            Column name string.
        """
        return self._column_name

    def get_operator(self) -> FilterOp:
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
