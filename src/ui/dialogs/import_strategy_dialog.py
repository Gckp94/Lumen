"""Dialog for importing strategy CSV with column mapping."""
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QGroupBox,
    QFormLayout,
    QHeaderView,
)

from src.core.file_loader import FileLoader
from src.core.portfolio_models import PortfolioColumnMapping
from src.ui.constants import Colors, Fonts, FontSizes, Spacing

logger = logging.getLogger(__name__)


class ImportStrategyDialog(QDialog):
    """Dialog for importing a strategy file and mapping columns."""

    PLACEHOLDER = "-- Select Column --"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Strategy")
        self.setMinimumSize(500, 500)
        self._preview_df: Optional[pd.DataFrame] = None
        self._file_path: Optional[str] = None
        self._file_loader = FileLoader()
        self._selected_sheet: Optional[str] = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.MD)

        # File selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("File:"))
        self._file_label = QLineEdit()
        self._file_label.setReadOnly(True)
        self._file_label.setPlaceholderText("No file selected")
        file_layout.addWidget(self._file_label, stretch=1)
        self._browse_btn = QPushButton("Browse...")
        file_layout.addWidget(self._browse_btn)
        layout.addLayout(file_layout)

        # Sheet selection (hidden by default, shown for Excel files)
        sheet_layout = QHBoxLayout()
        self._sheet_label = QLabel("Sheet:")
        self._sheet_label.setVisible(False)
        sheet_layout.addWidget(self._sheet_label)
        self._sheet_selector = QComboBox()
        self._sheet_selector.setVisible(False)
        self._sheet_selector.setMinimumWidth(150)
        sheet_layout.addWidget(self._sheet_selector, stretch=1)
        sheet_layout.addStretch()
        layout.addLayout(sheet_layout)

        # Column mapping group
        mapping_group = QGroupBox("Column Mapping")
        mapping_layout = QFormLayout(mapping_group)

        self._date_combo = QComboBox()
        self._gain_combo = QComboBox()
        self._wl_combo = QComboBox()

        for combo in [self._date_combo, self._gain_combo, self._wl_combo]:
            combo.addItem(self.PLACEHOLDER)

        mapping_layout.addRow("Date Column:", self._date_combo)
        mapping_layout.addRow("Gain % Column:", self._gain_combo)
        mapping_layout.addRow("Win/Loss Column:", self._wl_combo)
        layout.addWidget(mapping_group)

        # Preview table
        preview_group = QGroupBox("Preview (first 5 rows)")
        preview_layout = QVBoxLayout(preview_group)
        self._preview_table = QTableWidget()
        self._preview_table.setMaximumHeight(150)
        preview_layout.addWidget(self._preview_table)
        layout.addWidget(preview_group)

        # Strategy name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Strategy Name:"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Enter strategy name")
        name_layout.addWidget(self._name_edit, stretch=1)
        layout.addLayout(name_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._cancel_btn = QPushButton("Cancel")
        self._import_btn = QPushButton("Import Strategy")
        self._import_btn.setEnabled(False)
        btn_layout.addWidget(self._cancel_btn)
        btn_layout.addWidget(self._import_btn)
        layout.addLayout(btn_layout)

    def _connect_signals(self):
        self._browse_btn.clicked.connect(self._on_browse)
        self._cancel_btn.clicked.connect(self.reject)
        self._import_btn.clicked.connect(self.accept)
        self._sheet_selector.currentTextChanged.connect(self._on_sheet_changed)

        for combo in [self._date_combo, self._gain_combo, self._wl_combo]:
            combo.currentTextChanged.connect(self._validate_mapping)

    def _on_browse(self):
        # Use home directory as starting point to avoid slow network drive resolution
        start_dir = str(Path.home())
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Strategy File",
            start_dir,
            "Data Files (*.csv *.xlsx *.xls);;CSV Files (*.csv);;Excel Files (*.xlsx *.xls)",
        )
        if file_path:
            self._load_file(file_path)

    def _load_file(self, file_path: str):
        """Load a file and populate the preview."""
        try:
            self._file_path = file_path
            suffix = Path(file_path).suffix.lower()

            # Handle Excel files - show sheet selector
            if suffix in {".xlsx", ".xls"}:
                sheet_names = self._file_loader.get_sheet_names(Path(file_path))
                self._sheet_selector.clear()
                self._sheet_selector.addItems(sheet_names)
                self._sheet_label.setVisible(True)
                self._sheet_selector.setVisible(True)
                # Load first sheet by default
                df = self._file_loader.load(Path(file_path), sheet_names[0])
            else:
                # CSV file - hide sheet selector
                self._sheet_label.setVisible(False)
                self._sheet_selector.setVisible(False)
                df = pd.read_csv(file_path)

            self._file_label.setText(Path(file_path).name)
            self._name_edit.setText(Path(file_path).stem)
            self.set_preview_data(df)
        except Exception as e:
            logger.error(f"Failed to load file: {e}")

    def _on_sheet_changed(self, sheet_name: str):
        """Handle sheet selection change - reload data from selected sheet."""
        if not self._file_path or not sheet_name:
            return
        try:
            df = self._file_loader.load(Path(self._file_path), sheet_name)
            self.set_preview_data(df)
        except Exception as e:
            logger.error(f"Failed to load sheet {sheet_name}: {e}")

    def set_preview_data(self, df: pd.DataFrame):
        """Set the preview data and populate column dropdowns."""
        self._preview_df = df
        columns = list(df.columns)

        for combo in [self._date_combo, self._gain_combo, self._wl_combo]:
            combo.clear()
            combo.addItem(self.PLACEHOLDER)
            combo.addItems(columns)

        preview = df.head(5)
        self._preview_table.setRowCount(len(preview))
        self._preview_table.setColumnCount(len(columns))
        self._preview_table.setHorizontalHeaderLabels(columns)

        for i, row in enumerate(preview.itertuples(index=False)):
            for j, val in enumerate(row):
                self._preview_table.setItem(i, j, QTableWidgetItem(str(val)))

        self._preview_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._validate_mapping()

    def _validate_mapping(self):
        """Enable import button only when all columns are mapped."""
        all_mapped = (
            self._date_combo.currentText() != self.PLACEHOLDER
            and self._gain_combo.currentText() != self.PLACEHOLDER
            and self._wl_combo.currentText() != self.PLACEHOLDER
        )
        self._import_btn.setEnabled(all_mapped)

    def get_column_mapping(self) -> PortfolioColumnMapping:
        """Get the selected column mapping."""
        return PortfolioColumnMapping(
            date_col=self._date_combo.currentText(),
            gain_pct_col=self._gain_combo.currentText(),
            win_loss_col=self._wl_combo.currentText(),
        )

    def get_strategy_name(self) -> str:
        """Get the entered strategy name."""
        return self._name_edit.text() or "Unnamed Strategy"

    def get_file_path(self) -> Optional[str]:
        """Get the selected file path."""
        return self._file_path

    def get_dataframe(self) -> Optional[pd.DataFrame]:
        """Get the loaded DataFrame."""
        return self._preview_df

    def get_selected_sheet(self) -> Optional[str]:
        """Get the selected sheet name, or None if not applicable."""
        # Check if sheet selector has items (indicating an Excel file was loaded)
        # Note: Use count() > 0 instead of isVisible() since isVisible() returns False
        # when the dialog itself is not shown (e.g., during unit tests)
        if self._sheet_selector.count() > 0 and self._sheet_selector.currentText():
            return self._sheet_selector.currentText()
        return None
