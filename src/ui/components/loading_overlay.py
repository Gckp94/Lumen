"""Semi-transparent loading overlay with spinner."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QHideEvent, QShowEvent
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.ui.constants import Colors


class LoadingOverlay(QWidget):
    """Semi-transparent overlay that dims content with a centered spinner.

    Usage:
        self._overlay = LoadingOverlay(self)
        # When starting calculation:
        self._overlay.show()
        # When calculation completes:
        self._overlay.hide()
    """

    def __init__(self, parent: QWidget) -> None:
        """Initialize overlay as child of parent widget.

        Args:
            parent: Widget to overlay. Overlay will match its geometry.
        """
        super().__init__(parent)

        # Make overlay non-interactive (clicks pass through to parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Semi-transparent dark background
        self.setStyleSheet("""
            QWidget {
                background: rgba(0, 0, 0, 0.35);
            }
        """)

        # Layout with centered spinner
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._spinner = QLabel("Calculating...", self)
        self._spinner.setStyleSheet(f"""
            QLabel {{
                color: {Colors.SIGNAL_CYAN};
                font-size: 14px;
                font-weight: 500;
                background: transparent;
                padding: 12px 20px;
                border-radius: 6px;
            }}
        """)
        self._spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._spinner)

        # Animation for pulsing effect
        self._opacity = 1.0
        self._pulse_direction = -1
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(50)
        self._pulse_timer.timeout.connect(self._pulse)

        self.hide()

    def showEvent(self, event: QShowEvent | None) -> None:
        """Match parent geometry when shown."""
        super().showEvent(event)
        parent_widget = self.parentWidget()
        if parent_widget is not None:
            self.setGeometry(parent_widget.rect())
        self._pulse_timer.start()

    def hideEvent(self, event: QHideEvent | None) -> None:
        """Stop animation when hidden."""
        super().hideEvent(event)
        self._pulse_timer.stop()

    def _pulse(self) -> None:
        """Animate opacity pulse."""
        self._opacity += self._pulse_direction * 0.04
        if self._opacity <= 0.5:
            self._opacity = 0.5
            self._pulse_direction = 1
        elif self._opacity >= 1.0:
            self._opacity = 1.0
            self._pulse_direction = -1

        self._spinner.setStyleSheet(f"""
            QLabel {{
                color: rgba(0, 255, 255, {self._opacity});
                font-size: 14px;
                font-weight: 500;
                background: transparent;
                padding: 12px 20px;
                border-radius: 6px;
            }}
        """)
