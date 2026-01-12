"""Empty state component for placeholder sections."""

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from src.ui.constants import Colors, Fonts, Spacing


class EmptyState(QFrame):
    """Consistent empty state display for placeholder sections.

    Shows an icon, title, description, and optional action button
    in a centered layout. Used for sections without data or
    placeholders for upcoming features.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize empty state widget.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._action_callback: Callable[[], None] | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the centered layout."""
        self.setObjectName("emptyState")
        self.setStyleSheet(f"""
            QFrame#emptyState {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(Spacing.SM)
        layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)

        self._icon_label = QLabel()
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet("font-size: 48px;")

        self._title_label = QLabel()
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-family: {Fonts.UI};
            font-size: 16px;
            font-weight: bold;
        """)

        self._description_label = QLabel()
        self._description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._description_label.setWordWrap(True)
        self._description_label.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-family: {Fonts.UI};
            font-size: 13px;
        """)

        self._action_button = QPushButton()
        self._action_button.setVisible(False)
        self._action_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._action_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SIGNAL_BLUE};
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.UI};
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: #5EAEFF;
            }}
            QPushButton:pressed {{
                background-color: #3D8EEF;
            }}
        """)
        self._action_button.clicked.connect(self._on_action_clicked)

        layout.addStretch()
        layout.addWidget(self._icon_label)
        layout.addWidget(self._title_label)
        layout.addWidget(self._description_label)
        layout.addSpacing(Spacing.MD)
        layout.addWidget(self._action_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

    def _on_action_clicked(self) -> None:
        """Handle action button click."""
        if self._action_callback:
            self._action_callback()

    def set_message(
        self,
        icon: str,
        title: str,
        description: str,
        action_text: str | None = None,
        action_callback: Callable[[], None] | None = None,
    ) -> None:
        """Configure empty state content.

        Args:
            icon: Emoji or text to display as icon.
            title: Main title text.
            description: Descriptive text.
            action_text: Optional button text.
            action_callback: Optional callback for button click.
        """
        self._icon_label.setText(icon)
        self._title_label.setText(title)
        self._description_label.setText(description)

        if action_text and action_callback:
            self._action_button.setText(action_text)
            self._action_callback = action_callback
            self._action_button.setVisible(True)
        else:
            self._action_callback = None
            self._action_button.setVisible(False)
