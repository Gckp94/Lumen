"""Year selector tab buttons for monthly breakdown navigation."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from src.ui.constants import Colors, Fonts, Spacing


class YearSelectorTabs(QWidget):
    """Horizontal tab buttons for selecting years.

    Displays year buttons that auto-detect from dataset.
    Emits signal when year selection changes.
    """

    year_changed = pyqtSignal(int)  # selected year

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize year selector tabs.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._years: list[int] = []
        self._selected_year: int | None = None
        self._buttons: dict[int, QPushButton] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(Spacing.XS)
        self._layout.addStretch()

    def set_years(self, years: list[int]) -> None:
        """Set available years and create tab buttons.

        Args:
            years: Sorted list of years.
        """
        # Clear existing buttons
        for btn in self._buttons.values():
            btn.deleteLater()
        self._buttons.clear()

        self._years = years

        # Remove stretch
        while self._layout.count() > 0:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create buttons for each year
        for year in years:
            btn = QPushButton(str(year))
            btn.setFont(QFont(Fonts.UI, 10))
            btn.setFixedHeight(32)
            btn.setMinimumWidth(60)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, y=year: self._on_year_clicked(y))
            self._buttons[year] = btn
            self._layout.addWidget(btn)

        self._layout.addStretch()

        # Select most recent year by default
        if years:
            self._select_year(years[-1])

    def _on_year_clicked(self, year: int) -> None:
        """Handle year button click.

        Args:
            year: Clicked year.
        """
        if year != self._selected_year:
            self._select_year(year)
            self.year_changed.emit(year)

    def _select_year(self, year: int) -> None:
        """Update selection state and button styles.

        Args:
            year: Year to select.
        """
        self._selected_year = year
        self._update_button_styles()

    def _update_button_styles(self) -> None:
        """Update button styles based on selection."""
        for year, btn in self._buttons.items():
            if year == self._selected_year:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {Colors.SIGNAL_CYAN};
                        color: {Colors.BG_BASE};
                        border: none;
                        border-radius: 4px;
                        padding: 0 12px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background-color: {Colors.SIGNAL_CYAN};
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {Colors.BG_ELEVATED};
                        color: {Colors.TEXT_PRIMARY};
                        border: 1px solid {Colors.BG_BORDER};
                        border-radius: 4px;
                        padding: 0 12px;
                    }}
                    QPushButton:hover {{
                        background-color: {Colors.BG_BORDER};
                        border-color: {Colors.TEXT_SECONDARY};
                    }}
                """)

    def selected_year(self) -> int | None:
        """Get currently selected year.

        Returns:
            Selected year or None if no selection.
        """
        return self._selected_year
