"""Category bar component for two-tier tab navigation."""

import logging

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QWidget

from src.ui.constants import Colors, Fonts, Spacing
from src.ui.tab_categories import get_all_categories

logger = logging.getLogger(__name__)


class CategoryBar(QFrame):
    """Horizontal bar with category toggle buttons.

    Emits category_changed when user clicks a category.
    Does NOT control tab visibility directly - that's handled by MainWindow.
    """

    category_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._active_category: str = "ANALYZE"
        self._category_buttons: dict[str, QPushButton] = {}

        self._setup_ui()
        self._apply_styling()

        # Set initial checked state
        self._category_buttons["ANALYZE"].setChecked(True)

    def _setup_ui(self) -> None:
        """Set up the category button row."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.SM, Spacing.LG, Spacing.SM)
        layout.setSpacing(Spacing.SM)

        for category in get_all_categories():
            btn = QPushButton(category)
            btn.setObjectName("category_button")
            btn.setCheckable(True)
            # `checked` param is required by QPushButton.clicked signal signature
            btn.clicked.connect(lambda checked, c=category: self._on_category_clicked(c))
            layout.addWidget(btn)
            self._category_buttons[category] = btn

        layout.addStretch()

    def _apply_styling(self) -> None:
        """Apply category bar styling."""
        self.setStyleSheet(f"""
            CategoryBar {{
                background-color: {Colors.BG_BASE};
                border-bottom: 1px solid {Colors.BG_BORDER};
                min-height: 40px;
                max-height: 40px;
            }}

            #category_button {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                font-family: "{Fonts.UI}";
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 0.5px;
                padding: {Spacing.SM}px {Spacing.LG}px;
                border: none;
                border-left: 3px solid transparent;
                border-radius: 4px;
            }}

            #category_button:hover {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
            }}

            #category_button:checked {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border-left: 3px solid {Colors.SIGNAL_CYAN};
            }}
        """)

    def _on_category_clicked(self, category: str) -> None:
        """Handle category button click."""
        self._active_category = category
        for cat, btn in self._category_buttons.items():
            btn.setChecked(cat == category)
        self.category_changed.emit(category)

    @property
    def active_category(self) -> str:
        """Get the currently active category."""
        return self._active_category

    def set_active_category(self, category: str) -> None:
        """Set active category programmatically without emitting signal.

        This method intentionally does NOT emit category_changed to prevent
        infinite loops when called from signal handlers that respond to
        category changes.

        Args:
            category: The category name to activate. Must be a valid category.
        """
        if category not in self._category_buttons:
            logger.warning("Invalid category '%s' passed to set_active_category", category)
            return
        self._active_category = category
        for cat, btn in self._category_buttons.items():
            btn.setChecked(cat == category)
