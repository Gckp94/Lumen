"""X-axis mode toggle for equity charts.

Provides a segmented control to switch between trade number and date
display on the chart X-axis.
"""

from enum import Enum, auto

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from src.ui.constants import Colors, Fonts, FontSizes, Spacing


class AxisMode(Enum):
    """X-axis display mode."""

    TRADES = auto()
    DATE = auto()


class AxisModeToggle(QWidget):
    """Segmented toggle control for chart X-axis mode.

    Observatory-themed toggle with subtle glow effects and crisp typography.
    Designed to complement the equity chart controls.

    Signals:
        mode_changed: Emitted when mode changes, with new AxisMode value.

    Attributes:
        mode: Current axis mode (TRADES or DATE).
    """

    mode_changed = pyqtSignal(object)  # AxisMode

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the toggle.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._mode = AxisMode.TRADES
        self._setup_ui()

    @property
    def mode(self) -> AxisMode:
        """Current axis mode."""
        return self._mode

    def set_mode(self, mode: AxisMode) -> None:
        """Set the axis mode.

        Args:
            mode: New axis mode to set.
        """
        if mode != self._mode:
            self._mode = mode
            self._update_button_states()
            self.mode_changed.emit(mode)

    def _setup_ui(self) -> None:
        """Set up the toggle layout and styling."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Container styling - pill-shaped with subtle border
        self.setStyleSheet(f"""
            AxisModeToggle {{
                background: {Colors.BG_ELEVATED};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
            }}
        """)

        # Base button style
        base_style = f"""
            QPushButton {{
                background: transparent;
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
                font-weight: 500;
                padding: {Spacing.XS}px {Spacing.MD}px;
                border: none;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                color: {Colors.TEXT_PRIMARY};
                background: rgba(255, 255, 255, 0.05);
            }}
        """

        # Active button style with cyan glow
        active_style = f"""
            QPushButton {{
                background: rgba(0, 255, 212, 0.12);
                color: {Colors.SIGNAL_CYAN};
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
                font-weight: 600;
                padding: {Spacing.XS}px {Spacing.MD}px;
                border: 1px solid rgba(0, 255, 212, 0.3);
                border-radius: 3px;
            }}
        """

        # Trades button
        self._trades_btn = QPushButton("Trades")
        self._trades_btn.setStyleSheet(active_style)  # Default active
        self._trades_btn.clicked.connect(lambda: self.set_mode(AxisMode.TRADES))
        self._trades_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._trades_btn)

        # Date button
        self._date_btn = QPushButton("Date")
        self._date_btn.setStyleSheet(base_style)
        self._date_btn.clicked.connect(lambda: self.set_mode(AxisMode.DATE))
        self._date_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._date_btn)

        # Store styles for updates
        self._base_style = base_style
        self._active_style = active_style

    def _update_button_states(self) -> None:
        """Update button styling based on current mode."""
        if self._mode == AxisMode.TRADES:
            self._trades_btn.setStyleSheet(self._active_style)
            self._date_btn.setStyleSheet(self._base_style)
        else:
            self._trades_btn.setStyleSheet(self._base_style)
            self._date_btn.setStyleSheet(self._active_style)
