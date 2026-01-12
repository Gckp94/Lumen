"""Monte Carlo tab placeholder for Phase 3 simulations.

This tab displays a placeholder message indicating that Monte Carlo
simulations will be available in Phase 3.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.ui.constants import Colors


class MonteCarloTab(QWidget):
    """Placeholder tab for Monte Carlo simulations (Phase 3)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the Monte Carlo tab with placeholder content.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the placeholder UI with centered message."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel("Monte Carlo simulations coming in Phase 3")
        label.setStyleSheet(f"color: {Colors.TEXT_DISABLED}; font-size: 18px;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(label)
