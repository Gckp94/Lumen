"""Toggle switch component with animated transition."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from src.ui.constants import Animation, Colors

if TYPE_CHECKING:
    from PyQt6.QtGui import QPaintEvent


def _make_qt_property(type_: type, getter: Any, setter: Any) -> Any:
    """Create a Qt property, working around mypy stub issues."""
    from PyQt6 import QtCore
    # Use getattr to avoid mypy error about missing attribute in stubs
    prop_factory = getattr(QtCore, "pyqt" + "Property")  # noqa: B009
    return prop_factory(type_, getter, setter)


class ToggleSwitch(QWidget):
    """Binary toggle with animated transition.

    Emits a signal when the toggle state changes via user click.
    The toggle uses stellar-blue when ON and neutral background when OFF.

    Attributes:
        toggled: Signal emitted with boolean value when toggle state changes.
    """

    toggled = pyqtSignal(bool)

    # Toggle dimensions
    _TRACK_WIDTH = 40
    _TRACK_HEIGHT = 20
    _THUMB_RADIUS = 8
    _THUMB_MARGIN = 2

    def __init__(
        self,
        label: str = "",
        initial: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize ToggleSwitch.

        Args:
            label: Text label displayed next to the toggle.
            initial: Initial state (True = ON, False = OFF).
            parent: Parent widget.
        """
        super().__init__(parent)
        self._checked = initial
        self._label = label
        self._thumb_position = 1.0 if initial else 0.0  # 0.0 = left, 1.0 = right
        self._setup_ui()
        self._setup_animation()

    def _setup_ui(self) -> None:
        """Set up the toggle UI with label."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Track widget (the toggle itself)
        self._track = _ToggleTrack(self)
        self._track.setFixedSize(self._TRACK_WIDTH, self._TRACK_HEIGHT)
        layout.addWidget(self._track)

        # Label
        if self._label:
            self._label_widget = QLabel(self._label)
            self._label_widget.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.TEXT_PRIMARY};
                    font-size: 13px;
                }}
            """)
            layout.addWidget(self._label_widget)

        layout.addStretch()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _setup_animation(self) -> None:
        """Set up the thumb position animation."""
        self._animation = QPropertyAnimation(self, b"thumbPosition")
        self._animation.setDuration(Animation.DEBOUNCE_INPUT)  # 150ms
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def isChecked(self) -> bool:
        """Return current toggle state.

        Returns:
            True if toggle is ON, False otherwise.
        """
        return self._checked

    def setChecked(self, checked: bool) -> None:
        """Set toggle state without emitting signal.

        Args:
            checked: New toggle state.
        """
        if self._checked != checked:
            self._checked = checked
            self._animate_to(1.0 if checked else 0.0)

    def _on_click(self) -> None:
        """Handle click to toggle state."""
        self._checked = not self._checked
        self._animate_to(1.0 if self._checked else 0.0)
        self.toggled.emit(self._checked)

    def _animate_to(self, target: float) -> None:
        """Animate thumb to target position.

        Args:
            target: Target position (0.0 = left, 1.0 = right).
        """
        self._animation.stop()
        self._animation.setStartValue(self._thumb_position)
        self._animation.setEndValue(target)
        self._animation.start()

    # Qt property getter/setter for animation
    def _get_thumb_position(self) -> float:
        """Get current thumb position (0.0 to 1.0)."""
        return self._thumb_position

    def _set_thumb_position(self, value: float) -> None:
        """Set thumb position and trigger repaint.

        Args:
            value: Position value (0.0 = left, 1.0 = right).
        """
        self._thumb_position = value
        self._track.update()

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        """Handle mouse press to toggle state.

        Args:
            event: Mouse event.
        """
        if event is not None and event.button() == Qt.MouseButton.LeftButton:
            self._on_click()
        super().mousePressEvent(event)


# Register Qt property for animation - done at module level to avoid mypy stub issues
ToggleSwitch.thumbPosition = _make_qt_property(  # type: ignore[attr-defined]
    float,
    ToggleSwitch._get_thumb_position,
    ToggleSwitch._set_thumb_position,
)


class _ToggleTrack(QWidget):
    """Internal widget for rendering the toggle track and thumb."""

    def __init__(self, parent: ToggleSwitch) -> None:
        """Initialize track widget.

        Args:
            parent: Parent ToggleSwitch.
        """
        super().__init__(parent)
        self._toggle = parent

    def paintEvent(self, _event: QPaintEvent | None) -> None:
        """Custom paint for toggle appearance.

        Draws track (rounded rectangle) and thumb (circle) based on state.
        Uses Colors.SIGNAL_BLUE when ON, Colors.BG_BORDER when OFF.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Interpolate track color based on thumb position
        position = self._toggle._thumb_position
        off_color = QColor(Colors.BG_BORDER)
        on_color = QColor(Colors.SIGNAL_BLUE)

        r = int(off_color.red() + (on_color.red() - off_color.red()) * position)
        g = int(off_color.green() + (on_color.green() - off_color.green()) * position)
        b = int(off_color.blue() + (on_color.blue() - off_color.blue()) * position)
        track_color = QColor(r, g, b)

        # Draw track (rounded rectangle)
        track_rect = QRectF(0, 0, width, height)
        track_path = QPainterPath()
        track_path.addRoundedRect(track_rect, height / 2, height / 2)

        painter.setBrush(track_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(track_path)

        # Draw thumb (circle)
        thumb_radius = ToggleSwitch._THUMB_RADIUS
        margin = ToggleSwitch._THUMB_MARGIN

        # Calculate thumb center position based on animation position
        left_x = margin + thumb_radius
        right_x = width - margin - thumb_radius
        thumb_x = left_x + (right_x - left_x) * position
        thumb_y = height / 2

        painter.setBrush(QColor(Colors.TEXT_PRIMARY))
        painter.drawEllipse(
            QRectF(
                thumb_x - thumb_radius,
                thumb_y - thumb_radius,
                thumb_radius * 2,
                thumb_radius * 2,
            )
        )

        painter.end()
