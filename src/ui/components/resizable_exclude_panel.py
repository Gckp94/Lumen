"""Resizable panel for excluding columns from analysis."""

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.ui.constants import Colors, Fonts, FontSizes, Spacing


class ResizableExcludePanel(QFrame):
    """Resizable sidebar panel for column exclusion.

    Features:
    - Draggable width via parent QSplitter
    - Search/filter input
    - Scrollable checkbox list with tooltips
    - Collapsible header
    """

    # Emitted when exclusion set changes: (column_name, is_excluded)
    exclusion_changed = pyqtSignal(str, bool)

    # Emitted when all exclusions change (for bulk updates)
    exclusions_updated = pyqtSignal(set)

    # Width constraints
    MIN_WIDTH = 180
    DEFAULT_WIDTH = 280
    MAX_WIDTH = 400

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the resizable exclude panel."""
        super().__init__(parent)
        self._columns: list[str] = []
        self._excluded: set[str] = set()
        self._checkboxes: dict[str, QCheckBox] = {}

        self._setup_ui()
        self._apply_styling()

    def _setup_ui(self) -> None:
        """Set up the panel UI."""
        self.setMinimumWidth(self.MIN_WIDTH)
        self.setMaximumWidth(self.MAX_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(Spacing.SM)

        # Header
        header = QLabel("EXCLUDE COLUMNS")
        header.setObjectName("exclude_header")
        layout.addWidget(header)

        # Search input
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search columns...")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.textChanged.connect(self._filter_checkboxes)
        layout.addWidget(self._search_input)

        # Scrollable checkbox area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._checkbox_container = QWidget()
        self._checkbox_layout = QVBoxLayout(self._checkbox_container)
        self._checkbox_layout.setContentsMargins(0, 0, 0, 0)
        self._checkbox_layout.setSpacing(2)
        self._checkbox_layout.addStretch()

        scroll.setWidget(self._checkbox_container)
        self._checkbox_list = scroll
        layout.addWidget(scroll, 1)  # Stretch factor 1

    def _apply_styling(self) -> None:
        """Apply styling to the panel."""
        self.setStyleSheet(f"""
            ResizableExcludePanel {{
                background-color: {Colors.BG_ELEVATED};
                border-right: 1px solid {Colors.BG_BORDER};
            }}

            #exclude_header {{
                color: {Colors.TEXT_PRIMARY};
                font-family: "{Fonts.UI}";
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 0.5px;
                padding-bottom: {Spacing.XS}px;
                border-bottom: 2px solid {Colors.SIGNAL_CYAN};
            }}

            QLineEdit {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: {Spacing.SM}px;
                color: {Colors.TEXT_PRIMARY};
                font-family: "{Fonts.UI}";
                font-size: {FontSizes.BODY}px;
            }}

            QLineEdit:focus {{
                border-color: {Colors.SIGNAL_CYAN};
            }}

            QScrollArea {{
                background-color: transparent;
            }}

            QCheckBox {{
                color: {Colors.TEXT_PRIMARY};
                font-family: "{Fonts.DATA}";
                font-size: {FontSizes.BODY}px;
                padding: {Spacing.XS}px 0;
            }}

            QCheckBox:hover {{
                background-color: {Colors.BG_SURFACE};
            }}

            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {Colors.TEXT_SECONDARY};
                border-radius: 3px;
                background-color: {Colors.BG_SURFACE};
            }}

            QCheckBox::indicator:checked {{
                background-color: {Colors.SIGNAL_CYAN};
                border-color: {Colors.SIGNAL_CYAN};
            }}

            QCheckBox::indicator:unchecked {{
                background-color: {Colors.BG_SURFACE};
            }}
        """)

    def set_columns(self, columns: list[str]) -> None:
        """Set the available columns.

        Args:
            columns: List of column names to display.
        """
        self._columns = sorted(columns)
        self._rebuild_checkboxes()

    def _rebuild_checkboxes(self) -> None:
        """Rebuild checkbox list from current columns."""
        # Clear existing
        for checkbox in self._checkboxes.values():
            checkbox.deleteLater()
        self._checkboxes.clear()

        # Remove stretch and clear layout
        while self._checkbox_layout.count():
            item = self._checkbox_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create checkboxes
        for col in self._columns:
            checkbox = QCheckBox(col)
            checkbox.setToolTip(col)  # Full name on hover
            checkbox.setChecked(col not in self._excluded)
            checkbox.stateChanged.connect(
                lambda state, c=col: self._on_checkbox_changed(c, state)
            )
            self._checkbox_layout.addWidget(checkbox)
            self._checkboxes[col] = checkbox

        self._checkbox_layout.addStretch()

    def _on_checkbox_changed(self, column: str, state: int) -> None:
        """Handle checkbox state change."""
        is_excluded = state != Qt.CheckState.Checked.value
        if is_excluded:
            self._excluded.add(column)
        else:
            self._excluded.discard(column)
        self.exclusion_changed.emit(column, is_excluded)

    def _filter_checkboxes(self, text: str) -> None:
        """Filter visible checkboxes by search text."""
        search = text.lower()
        for col, checkbox in self._checkboxes.items():
            checkbox.setVisible(search in col.lower())

    def get_excluded(self) -> set[str]:
        """Get the set of excluded column names."""
        return self._excluded.copy()

    def set_excluded(self, excluded: set[str]) -> None:
        """Set the excluded columns.

        Args:
            excluded: Set of column names to exclude.
        """
        self._excluded = excluded.copy()
        for col, checkbox in self._checkboxes.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(col not in self._excluded)
            checkbox.blockSignals(False)
        self.exclusions_updated.emit(self._excluded)

    def sizeHint(self) -> QSize:
        """Return default size hint."""
        return QSize(self.DEFAULT_WIDTH, 400)
