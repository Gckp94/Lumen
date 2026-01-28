"""Save filter preset dialog."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.constants import Colors, Spacing


class SavePresetDialog(QDialog):
    """Dialog for entering a preset name when saving filters.

    Attributes:
        existing_names: List of existing preset names for duplicate detection.
    """

    def __init__(
        self,
        existing_names: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize SavePresetDialog.

        Args:
            existing_names: Existing preset names for duplicate warning.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._existing_names = [n.lower() for n in (existing_names or [])]
        self._setup_ui()
        self._apply_style()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up dialog UI."""
        self.setWindowTitle("Save Filter Preset")
        self.setMinimumWidth(350)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.MD)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)

        # Name input row
        name_layout = QHBoxLayout()
        name_label = QLabel("Name:")
        name_layout.addWidget(name_label)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Enter preset name")
        name_layout.addWidget(self._name_input, stretch=1)
        layout.addLayout(name_layout)

        # Warning label (hidden by default)
        self._warning_label = QLabel("A preset with this name already exists")
        self._warning_label.setVisible(False)
        layout.addWidget(self._warning_label)

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)

        self._save_btn = QPushButton("Save")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self.accept)
        self._save_btn.setDefault(True)
        btn_layout.addWidget(self._save_btn)

        layout.addLayout(btn_layout)

    def _apply_style(self) -> None:
        """Apply Observatory theme styling."""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_SURFACE};
            }}
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-size: 13px;
            }}
            QLineEdit {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
        """)

        # Primary button (Save)
        self._save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SIGNAL_CYAN};
                color: {Colors.BG_BASE};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {Colors.SIGNAL_BLUE};
            }}
            QPushButton:disabled {{
                background-color: {Colors.BG_BORDER};
                color: {Colors.TEXT_DISABLED};
            }}
        """)

        # Secondary button (Cancel)
        self._cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                border-color: {Colors.SIGNAL_CYAN};
                color: {Colors.SIGNAL_CYAN};
            }}
        """)

        # Warning label
        self._warning_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.SIGNAL_AMBER};
                font-size: 12px;
            }}
        """)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self._name_input.textChanged.connect(self._on_name_changed)

    def _on_name_changed(self, text: str) -> None:
        """Handle name input changes.

        Args:
            text: Current input text.
        """
        name = text.strip()
        has_name = bool(name)
        is_duplicate = name.lower() in self._existing_names

        self._save_btn.setEnabled(has_name)
        self._warning_label.setVisible(has_name and is_duplicate)

    def get_preset_name(self) -> str:
        """Get the entered preset name.

        Returns:
            Trimmed preset name.
        """
        return self._name_input.text().strip()
