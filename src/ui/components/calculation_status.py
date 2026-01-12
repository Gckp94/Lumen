"""Calculation status indicator widget.

Shows calculation progress status with animated visual feedback.
"""

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from src.core.app_state import AppState
from src.ui.constants import Colors, Fonts, FontSizes


class CalculationStatusIndicator(QWidget):
    """Widget showing calculation status with animated feedback.

    Displays "Calculating..." with pulse animation during calculation,
    and "Ready" with auto-fade after calculation completes.

    Attributes:
        _app_state: Reference to centralized app state.
        _status_label: Label showing status text.
        _opacity: Current opacity for animations.
        _pulse_timer: Timer for pulse animation.
        _fade_timer: Timer for auto-fade after completion.
    """

    def __init__(
        self, app_state: AppState, parent: QWidget | None = None
    ) -> None:
        """Initialize the calculation status indicator.

        Args:
            app_state: Centralized application state.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._app_state = app_state
        self._opacity = 1.0
        self._pulse_direction = -1  # -1 = fading out, 1 = fading in
        self._setup_ui()
        self._setup_timers()
        self._connect_signals()
        # Start hidden
        self.hide()

    def _setup_ui(self) -> None:
        """Set up the indicator UI."""
        self.setObjectName("calculationStatus")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._status_label = QLabel()
        self._status_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
            }}
        """)
        layout.addWidget(self._status_label)

    def _setup_timers(self) -> None:
        """Set up animation timers."""
        # Pulse timer for "Calculating..." state
        self._pulse_timer = QTimer()
        self._pulse_timer.setInterval(50)  # 50ms for smooth animation
        self._pulse_timer.timeout.connect(self._pulse_animation)

        # Fade timer for auto-hide after "Ready"
        self._fade_timer = QTimer()
        self._fade_timer.setSingleShot(True)
        self._fade_timer.timeout.connect(self._start_fade_out)

        # Fade out animation timer
        self._fade_out_timer = QTimer()
        self._fade_out_timer.setInterval(50)
        self._fade_out_timer.timeout.connect(self._fade_out_animation)

    def _connect_signals(self) -> None:
        """Connect to AppState signals."""
        self._app_state.filtered_calculation_started.connect(
            self._on_calculation_started
        )
        self._app_state.filtered_calculation_completed.connect(
            self._on_calculation_completed
        )

    def _on_calculation_started(self) -> None:
        """Handle calculation started signal."""
        self._fade_timer.stop()
        self._fade_out_timer.stop()
        self._opacity = 1.0
        self._update_style_opacity()

        self._status_label.setText("Calculating...")
        self._status_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.SIGNAL_AMBER};
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
            }}
        """)
        self.show()
        self._pulse_timer.start()

    def _on_calculation_completed(self) -> None:
        """Handle calculation completed signal."""
        self._pulse_timer.stop()
        self._opacity = 1.0
        self._update_style_opacity()

        self._status_label.setText("Ready")
        self._status_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.SIGNAL_CYAN};
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
            }}
        """)
        # Auto-fade after 2 seconds
        self._fade_timer.start(2000)

    def _pulse_animation(self) -> None:
        """Animate opacity pulse for calculating state."""
        # Oscillate between 0.4 and 1.0 opacity
        self._opacity += self._pulse_direction * 0.03

        if self._opacity <= 0.4:
            self._opacity = 0.4
            self._pulse_direction = 1
        elif self._opacity >= 1.0:
            self._opacity = 1.0
            self._pulse_direction = -1

        self._update_style_opacity()

    def _start_fade_out(self) -> None:
        """Start fade out animation after Ready display."""
        self._fade_out_timer.start()

    def _fade_out_animation(self) -> None:
        """Animate fade out for Ready state."""
        self._opacity -= 0.05

        if self._opacity <= 0:
            self._opacity = 0
            self._fade_out_timer.stop()
            self.hide()
        else:
            self._update_style_opacity()

    def _update_style_opacity(self) -> None:
        """Update widget opacity via stylesheet."""
        self.setStyleSheet(f"QWidget#calculationStatus {{ opacity: {self._opacity}; }}")
        # Also update the label with opacity in rgba
        current_color = Colors.SIGNAL_AMBER if self._pulse_timer.isActive() else Colors.SIGNAL_CYAN
        # Convert hex to rgba with opacity
        r = int(current_color[1:3], 16)
        g = int(current_color[3:5], 16)
        b = int(current_color[5:7], 16)
        self._status_label.setStyleSheet(f"""
            QLabel {{
                color: rgba({r}, {g}, {b}, {self._opacity});
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
            }}
        """)

    def cleanup(self) -> None:
        """Clean up resources."""
        self._pulse_timer.stop()
        self._fade_timer.stop()
        self._fade_out_timer.stop()
