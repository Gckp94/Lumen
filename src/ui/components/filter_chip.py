"""FilterChip component for displaying active filters."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

from src.core.models import FilterCriteria
from src.ui.constants import Colors, Spacing


class FilterChip(QFrame):
    """Display active filter with remove action.

    Attributes:
        removed: Signal emitted when remove button clicked, passes FilterCriteria.
    """

    removed = pyqtSignal(object)  # FilterCriteria

    def __init__(
        self,
        criteria: FilterCriteria,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize FilterChip.

        Args:
            criteria: The filter criteria to display.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._criteria = criteria
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        """Set up the chip UI layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.XS, Spacing.SM, Spacing.XS)
        layout.setSpacing(Spacing.XS)

        # Filter summary label
        op_text = "between" if self._criteria.operator == "between" else "not between"
        text = (
            f"{self._criteria.column} {op_text} "
            f"{self._criteria.min_val}-{self._criteria.max_val}"
        )
        self._label = QLabel(text)
        layout.addWidget(self._label)

        # Remove button
        self._remove_btn = QPushButton("\u2715")  # ✕
        self._remove_btn.setFixedSize(16, 16)
        self._remove_btn.clicked.connect(self._on_remove)
        layout.addWidget(self._remove_btn)

    def _apply_style(self) -> None:
        """Apply Observatory theme styling."""
        self.setStyleSheet(f"""
            FilterChip {{
                background-color: {Colors.SIGNAL_AMBER};
                border-radius: 4px;
            }}
            QLabel {{
                color: {Colors.BG_BASE};
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton {{
                background: transparent;
                border: none;
                color: {Colors.BG_BASE};
                padding: 0;
                font-size: 10px;
            }}
            QPushButton:hover {{
                color: {Colors.SIGNAL_CORAL};
            }}
        """)

    def _on_remove(self) -> None:
        """Handle remove button click."""
        self.removed.emit(self._criteria)
