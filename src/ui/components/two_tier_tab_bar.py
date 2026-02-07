"""Two-tier tab navigation bar with category and tab rows."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.ui.constants import Colors, Fonts, FontSizes, Spacing
from src.ui.tab_categories import TAB_CATEGORIES, get_tabs_in_category


class TwoTierTabBar(QFrame):
    """Two-tier navigation with category row and tab row."""

    tab_activated = pyqtSignal(str)
    category_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._active_category: str = "ANALYZE"
        self._active_tab: str | None = None
        self._category_buttons: dict[str, QPushButton] = {}
        self._tab_buttons: dict[str, QPushButton] = {}

        self._setup_ui()
        self._apply_styling()
        self._on_category_clicked("ANALYZE")

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Row 1: Category buttons
        category_row = QWidget()
        category_row.setObjectName("category_row")
        category_layout = QHBoxLayout(category_row)
        category_layout.setContentsMargins(Spacing.LG, Spacing.SM, Spacing.LG, 0)
        category_layout.setSpacing(Spacing.SM)

        for category in TAB_CATEGORIES.keys():
            btn = QPushButton(category)
            btn.setObjectName("category_button")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, c=category: self._on_category_clicked(c))
            category_layout.addWidget(btn)
            self._category_buttons[category] = btn

        category_layout.addStretch()
        layout.addWidget(category_row)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("tier_separator")
        layout.addWidget(separator)

        # Row 2: Tab buttons (scrollable)
        tab_scroll = QScrollArea()
        tab_scroll.setWidgetResizable(True)
        tab_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tab_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        tab_scroll.setFrameShape(QFrame.Shape.NoFrame)
        tab_scroll.setObjectName("tab_scroll")

        tab_row = QWidget()
        tab_row.setObjectName("tab_row")
        self._tab_layout = QHBoxLayout(tab_row)
        self._tab_layout.setContentsMargins(Spacing.LG, Spacing.SM, Spacing.LG, Spacing.SM)
        self._tab_layout.setSpacing(Spacing.XS)

        for category, tabs in TAB_CATEGORIES.items():
            for tab_name in tabs:
                btn = QPushButton(tab_name)
                btn.setObjectName("tab_button")
                btn.setCheckable(True)
                btn.clicked.connect(lambda checked, t=tab_name: self._on_tab_clicked(t))
                self._tab_layout.addWidget(btn)
                self._tab_buttons[tab_name] = btn

        self._tab_layout.addStretch()
        tab_scroll.setWidget(tab_row)
        layout.addWidget(tab_scroll)

    def _apply_styling(self) -> None:
        """Apply styling with animations."""
        self.setStyleSheet(f"""
            TwoTierTabBar {{
                background-color: {Colors.BG_BASE};
                border-bottom: 1px solid {Colors.BG_BORDER};
            }}

            #category_row {{
                background-color: {Colors.BG_BASE};
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

            #tier_separator {{
                background-color: {Colors.BG_BORDER};
                max-height: 1px;
            }}

            #tab_scroll {{
                background-color: {Colors.BG_BASE};
            }}

            #tab_row {{
                background-color: {Colors.BG_BASE};
            }}

            #tab_button {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                font-family: "{Fonts.UI}";
                font-size: {FontSizes.BODY}px;
                padding: {Spacing.SM}px {Spacing.LG}px;
                border: none;
                border-bottom: 2px solid transparent;
                min-width: 80px;
            }}

            #tab_button:hover {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
            }}

            #tab_button:checked {{
                color: {Colors.TEXT_PRIMARY};
                border-bottom: 2px solid {Colors.SIGNAL_CYAN};
                font-weight: 500;
            }}

            /* Scrollbar styling */
            #tab_scroll QScrollBar:horizontal {{
                height: 4px;
                background-color: transparent;
            }}

            #tab_scroll QScrollBar::handle:horizontal {{
                background-color: {Colors.BG_BORDER};
                border-radius: 2px;
                min-width: 30px;
            }}

            #tab_scroll QScrollBar::handle:horizontal:hover {{
                background-color: {Colors.SIGNAL_CYAN};
            }}

            #tab_scroll QScrollBar::add-line:horizontal,
            #tab_scroll QScrollBar::sub-line:horizontal {{
                width: 0;
            }}
        """)

    def _on_category_clicked(self, category: str) -> None:
        self._active_category = category
        for cat, btn in self._category_buttons.items():
            btn.setChecked(cat == category)

        category_tabs = get_tabs_in_category(category)
        for tab_name, btn in self._tab_buttons.items():
            btn.setVisible(tab_name in category_tabs)

        if category_tabs and (self._active_tab not in category_tabs):
            self._on_tab_clicked(category_tabs[0])

        self.category_changed.emit(category)

    def _on_tab_clicked(self, tab_name: str) -> None:
        self._active_tab = tab_name
        for name, btn in self._tab_buttons.items():
            btn.setChecked(name == tab_name)
        self.tab_activated.emit(tab_name)

    @property
    def active_category(self) -> str:
        return self._active_category

    @property
    def active_tab(self) -> str | None:
        return self._active_tab

    def set_active_tab(self, tab_name: str) -> None:
        from src.ui.tab_categories import get_category_for_tab
        category = get_category_for_tab(tab_name)
        if category and category != self._active_category:
            self._on_category_clicked(category)
        self._on_tab_clicked(tab_name)

    def keyPressEvent(self, event) -> None:
        """Handle keyboard navigation."""
        from src.ui.tab_categories import get_all_categories

        modifiers = event.modifiers()
        key = event.key()

        # Ctrl+1-5: Switch category
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            if Qt.Key.Key_1 <= key <= Qt.Key.Key_5:
                index = key - Qt.Key.Key_1
                categories = get_all_categories()
                if index < len(categories):
                    self._on_category_clicked(categories[index])
                    return

            # Ctrl+Tab: Next tab in category
            if key == Qt.Key.Key_Tab:
                self._cycle_tab(forward=True)
                return

        # Ctrl+Shift+Tab: Previous tab in category
        if modifiers == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
            if key == Qt.Key.Key_Tab:
                self._cycle_tab(forward=False)
                return

        super().keyPressEvent(event)

    def _cycle_tab(self, forward: bool = True) -> None:
        """Cycle to next/previous tab in current category."""
        tabs = get_tabs_in_category(self._active_category)
        if not tabs or self._active_tab not in tabs:
            return

        current_index = tabs.index(self._active_tab)
        if forward:
            next_index = (current_index + 1) % len(tabs)
        else:
            next_index = (current_index - 1) % len(tabs)

        self._on_tab_clicked(tabs[next_index])
