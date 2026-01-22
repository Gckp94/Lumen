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

        for combo in [self._date_combo, self._gain_combo, self._wl_combo]:
            combo.currentTextChanged.connect(self._validate_mapping)

    def _on_browse(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Strategy File",
            "",
            "Data Files (*.csv *.xlsx *.xls);;CSV Files (*.csv);;Excel Files (*.xlsx *.xls)",
        )
        if file_path:
            self._load_file(file_path)

    def _load_file(self, file_path: str):
        try:
            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

            self._file_path = file_path
            self._file_label.setText(Path(file_path).name)
            self._name_edit.setText(Path(file_path).stem)
            self.set_preview_data(df)
        except Exception as e:
            logger.error(f"Failed to load file: {e}")

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
