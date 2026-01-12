"""Toast notification component for Lumen application.

Provides transient feedback messages with auto-dismiss functionality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from src.ui.constants import Animation, Colors, Spacing

if TYPE_CHECKING:
    pass


class Toast(QFrame):
    """Transient notification for feedback messages.

    Displays a styled message with an icon that auto-dismisses after
    a configurable duration with a fade-out animation.

    Attributes:
        VARIANTS: Mapping of variant names to (color, icon) tuples.
    """

    VARIANTS: dict[str, tuple[str, str]] = {
        "success": (Colors.SIGNAL_CYAN, "✓"),
        "error": (Colors.SIGNAL_CORAL, "✗"),
        "warning": (Colors.SIGNAL_AMBER, "⚠"),
        "info": (Colors.SIGNAL_BLUE, "ℹ"),
    }

    def __init__(
        self,
        message: str,
        variant: str = "info",
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the Toast.

        Args:
            message: The message to display.
            variant: One of "success", "error", "warning", "info".
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._message = message
        self._variant = variant
        self._animation: QPropertyAnimation | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up toast appearance."""
        color, icon = self.VARIANTS.get(self._variant, self.VARIANTS["info"])

        self.setStyleSheet(f"""
            Toast {{
                background-color: {Colors.BG_ELEVATED};
                border: 1px solid {color};
                border-radius: 4px;
                padding: {Spacing.SM}px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"color: {color};")
        layout.addWidget(icon_label)

        message_label = QLabel(self._message)
        message_label.setObjectName("toast_message")
        message_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(message_label)

    @classmethod
    def display(
        cls,
        parent: QWidget,
        message: str,
        variant: str = "info",
        duration: int = 3000,
    ) -> Toast:
        """Display toast notification.

        Args:
            parent: Parent widget for positioning.
            message: Message to display.
            variant: One of "success", "error", "warning", "info".
            duration: Auto-dismiss duration in ms (0 = persistent).

        Returns:
            Toast instance.
        """
        toast = cls(message, variant, parent)
        toast.setWindowFlags(Qt.WindowType.ToolTip)

        # Position at bottom-center of parent
        toast.adjustSize()
        parent_rect = parent.rect()
        x = parent_rect.center().x() - toast.width() // 2
        y = parent_rect.bottom() - toast.height() - Spacing.LG
        toast.move(parent.mapToGlobal(QPoint(x, y)))

        toast.show()

        if duration > 0:
            QTimer.singleShot(duration, toast._fade_out)

        return toast

    def _fade_out(self) -> None:
        """Animate fade out and close."""
        self._animation = QPropertyAnimation(self, b"windowOpacity")
        self._animation.setDuration(Animation.TAB_SWITCH)
        self._animation.setStartValue(1.0)
        self._animation.setEndValue(0.0)
        self._animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._animation.finished.connect(self.close)
        self._animation.start()
