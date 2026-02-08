"""Data Input tab for file loading and column configuration.

This is the first tab in the workflow where users load their data files
and configure column mappings.
"""

import logging
from pathlib import Path

import pandas as pd
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.core.app_state import AppState
from src.core.column_mapper import ColumnMapper
from src.core.file_load_worker import FileLoadWorker
from src.core.file_loader import FileLoader
from src.core.filter_engine import time_to_minutes
from src.core.first_trigger import FirstTriggerEngine
from src.core.mapping_worker import MappingResult, MappingWorker
from src.core.metrics import MetricsCalculator
from src.core.models import AdjustmentParams, ColumnMapping, DetectionResult, TradingMetrics
from src.ui.components.metric_card import MetricCard
from src.ui.components.no_scroll_widgets import NoScrollComboBox, NoScrollDoubleSpinBox
from src.ui.constants import Colors, Fonts, Spacing

logger = logging.getLogger(__name__)


class ColumnConfigPanel(QWidget):
    """Panel for configuring column mappings.

    Displays dropdowns for required and optional column mappings with
    status indicators and preview values.
    """

    mapping_completed = pyqtSignal(object)  # Emits ColumnMapping when valid

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the Column Configuration Panel.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._columns: list[str] = []
        self._df: pd.DataFrame | None = None
        self._detection_result: DetectionResult | None = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the UI layout and widgets."""
        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.MD)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QLabel("Column Mappings")
        header.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-size: 16px;
                font-weight: bold;
            }}
        """
        )
        layout.addWidget(header)

        # Status summary
        self._status_summary = QLabel()
        self._status_summary.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 13px;
            }}
        """
        )
        layout.addWidget(self._status_summary)

        # Grid for dropdowns
        grid = QGridLayout()
        grid.setSpacing(Spacing.SM)
        grid.setColumnStretch(1, 1)  # Make dropdown column stretch

        # Required columns
        self._combos: dict[str, NoScrollComboBox] = {}
        self._status_labels: dict[str, QLabel] = {}
        self._preview_labels: dict[str, QLabel] = {}

        required_fields = [
            ("ticker", "Ticker"),
            ("date", "Date"),
            ("time", "Time"),
            ("gain_pct", "Gain %"),
            ("mae_pct", "MAE %"),
            ("mfe_pct", "MFE %"),
        ]

        row = 0
        for field_name, display_name in required_fields:
            row = self._add_field_row(grid, row, field_name, display_name, required=True)

        # Win/Loss optional field
        row = self._add_field_row(grid, row, "win_loss", "Win/Loss", required=False)

        # MAE/MFE Time optional fields (for timing-aware scaling logic)
        row = self._add_field_row(grid, row, "mae_time", "MAE Time", required=False)
        row = self._add_field_row(grid, row, "mfe_time", "MFE Time", required=False)

        # Time interval price columns (optional, for time stop analysis)
        time_price_fields = [
            ("price_10_min_after", "Price 10 Mins After"),
            ("price_20_min_after", "Price 20 Mins After"),
            ("price_30_min_after", "Price 30 Mins After"),
            ("price_60_min_after", "Price 60 Mins After"),
            ("price_90_min_after", "Price 90 Mins After"),
            ("price_120_min_after", "Price 120 Mins After"),
            ("price_150_min_after", "Price 150 Mins After"),
            ("price_180_min_after", "Price 180 Mins After"),
            ("price_240_min_after", "Price 240 Mins After"),
        ]
        for field_name, display_name in time_price_fields:
            row = self._add_field_row(grid, row, field_name, display_name, required=False)

        layout.addLayout(grid)

        # Derive Win/Loss checkbox
        self._derive_checkbox = QCheckBox("Derive Win/Loss from Gain %")
        self._derive_checkbox.setObjectName("derive_winloss_checkbox")
        self._derive_checkbox.setStyleSheet(
            f"""
            QCheckBox {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 13px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 3px;
                background-color: {Colors.BG_SURFACE};
            }}
            QCheckBox::indicator:checked {{
                background-color: {Colors.SIGNAL_CYAN};
                border-color: {Colors.SIGNAL_CYAN};
            }}
        """
        )
        layout.addWidget(self._derive_checkbox)

        # Breakeven checkbox (only visible when deriving)
        self._breakeven_checkbox = QCheckBox("Count 0% as Win")
        self._breakeven_checkbox.setObjectName("breakeven_checkbox")
        self._breakeven_checkbox.setVisible(False)
        self._breakeven_checkbox.setStyleSheet(
            f"""
            QCheckBox {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 13px;
                spacing: 8px;
                margin-left: 24px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 3px;
                background-color: {Colors.BG_SURFACE};
            }}
            QCheckBox::indicator:checked {{
                background-color: {Colors.SIGNAL_CYAN};
                border-color: {Colors.SIGNAL_CYAN};
            }}
        """
        )
        layout.addWidget(self._breakeven_checkbox)

        # Validation error label
        self._error_label = QLabel()
        self._error_label.setObjectName("error_label")
        self._error_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.SIGNAL_CORAL};
                font-size: 13px;
            }}
        """
        )
        self._error_label.setVisible(False)
        layout.addWidget(self._error_label)

        # Continue button
        button_row = QHBoxLayout()
        self._continue_btn = QPushButton("Continue")
        self._continue_btn.setObjectName("continue_button")
        self._continue_btn.setEnabled(False)
        self._continue_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {Colors.SIGNAL_CYAN};
                color: {Colors.BG_BASE};
                border: none;
                border-radius: 4px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #00E6BF;
            }}
            QPushButton:pressed {{
                background-color: #00CCaa;
            }}
            QPushButton:disabled {{
                background-color: {Colors.BG_BORDER};
                color: {Colors.TEXT_DISABLED};
            }}
        """
        )
        button_row.addWidget(self._continue_btn)
        button_row.addStretch()
        layout.addLayout(button_row)

    def _add_field_row(
        self, grid: QGridLayout, row: int, field_name: str, display_name: str, required: bool
    ) -> int:
        """Add a field row to the grid.

        Args:
            grid: The grid layout to add to.
            row: Current row index.
            field_name: Internal field name.
            display_name: Display label text.
            required: Whether this is a required field.

        Returns:
            Next row index.
        """
        # Label
        label = QLabel(f"{display_name}{'*' if required else ''}:")
        label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 13px;
            }}
        """
        )
        grid.addWidget(label, row, 0)

        # Combo box
        combo = NoScrollComboBox()
        combo.setObjectName(f"{field_name}_combo")
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        combo.setStyleSheet(
            f"""
            QComboBox {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 8px 32px 8px 12px;
                font-size: 13px;
                min-width: 150px;
                min-height: 20px;
            }}
            QComboBox:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 24px;
                border: none;
            }}
            QComboBox::down-arrow {{
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {Colors.TEXT_SECONDARY};
            }}
            QComboBox::down-arrow:hover {{
                border-top-color: {Colors.TEXT_PRIMARY};
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                selection-background-color: {Colors.BG_BORDER};
                selection-color: {Colors.TEXT_PRIMARY};
                padding: 4px;
            }}
        """
        )
        self._combos[field_name] = combo
        grid.addWidget(combo, row, 1)

        # Status indicator
        status_label = QLabel()
        status_label.setFixedWidth(24)
        status_label.setStyleSheet("font-size: 14px;")
        self._status_labels[field_name] = status_label
        grid.addWidget(status_label, row, 2)

        row += 1

        # Preview label
        preview = QLabel()
        preview.setObjectName(f"{field_name}_preview")
        preview.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 12px;
                margin-left: 4px;
            }}
        """
        )
        self._preview_labels[field_name] = preview
        grid.addWidget(preview, row, 1, 1, 2)

        return row + 1

    def _connect_signals(self) -> None:
        """Connect widget signals to slots."""
        for combo in self._combos.values():
            combo.currentTextChanged.connect(self._on_selection_changed)
        self._derive_checkbox.toggled.connect(self._on_derive_toggled)
        self._continue_btn.clicked.connect(self._on_continue_clicked)

    def set_columns(
        self, columns: list[str], df: pd.DataFrame, detection_result: DetectionResult
    ) -> None:
        """Set available columns and detection result.

        Args:
            columns: List of DataFrame column names.
            df: The DataFrame for preview values.
            detection_result: Result from auto-detection.
        """
        self._columns = columns
        self._df = df
        self._detection_result = detection_result

        # Populate combos
        for field_name, combo in self._combos.items():
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("")  # Empty option
            combo.addItems(columns)

            # Set detected value if available
            if detection_result.mapping:
                value = getattr(detection_result.mapping, field_name, None)
                if value:
                    idx = combo.findText(value)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
            combo.blockSignals(False)

        # Update status indicators
        self._update_status_indicators()

        # Update previews
        self._update_all_previews()

        # Update summary
        detected_count = sum(1 for s in detection_result.statuses.values() if s == "detected")
        total = len(detection_result.statuses)
        self._status_summary.setText(f"Auto-detected {detected_count}/{total} columns")

        # Validate
        self._validate()

    def _update_status_indicators(self) -> None:
        """Update status indicator labels based on detection result and current values."""
        for field_name, label in self._status_labels.items():
            combo = self._combos.get(field_name)
            # First check if combo has a value (user selection or auto-detected)
            if combo and combo.currentText():
                label.setText("✓")
                label.setStyleSheet(f"color: {Colors.SIGNAL_CYAN}; font-size: 14px;")
            elif self._detection_result:
                # Fall back to detection result status
                status = self._detection_result.statuses.get(field_name, "missing")
                if status == "detected":
                    label.setText("✓")
                    label.setStyleSheet(f"color: {Colors.SIGNAL_CYAN}; font-size: 14px;")
                elif status == "guessed":
                    label.setText("⚠")
                    label.setStyleSheet(f"color: {Colors.SIGNAL_AMBER}; font-size: 14px;")
                else:
                    label.setText("✗")
                    label.setStyleSheet(f"color: {Colors.SIGNAL_CORAL}; font-size: 14px;")
            else:
                label.setText("✗")
                label.setStyleSheet(f"color: {Colors.SIGNAL_CORAL}; font-size: 14px;")

    def _update_single_status_indicator(self, field_name: str) -> None:
        """Update status indicator for a single field based on current selection.

        Args:
            field_name: The field name (e.g., 'ticker', 'win_loss')
        """
        if field_name not in self._status_labels:
            return

        label = self._status_labels[field_name]
        combo = self._combos.get(field_name)

        if combo and combo.currentText():
            # User has selected a column - show as valid
            label.setText("✓")
            label.setStyleSheet(f"color: {Colors.SIGNAL_CYAN}; font-size: 14px;")
        else:
            # No selection - show as missing
            label.setText("✗")
            label.setStyleSheet(f"color: {Colors.SIGNAL_CORAL}; font-size: 14px;")

    def _update_all_previews(self) -> None:
        """Update all preview labels."""
        for field_name in self._combos:
            self._update_preview(field_name)

    def _update_preview(self, field_name: str) -> None:
        """Update preview for a specific field.

        Args:
            field_name: The field to update preview for.
        """
        combo = self._combos[field_name]
        preview = self._preview_labels[field_name]
        column = combo.currentText()

        if not column or self._df is None or column not in self._df.columns:
            preview.setText("")
            return

        # Get first 3 unique values
        values = self._df[column].dropna().head(3).astype(str).tolist()
        if values:
            preview.setText(f"Values: {', '.join(values)}")
        else:
            preview.setText("No values")

    def _on_selection_changed(self, _text: str) -> None:
        """Handle combo box selection change."""
        # Find which combo changed
        sender = self.sender()
        for field_name, combo in self._combos.items():
            if combo is sender:
                self._update_preview(field_name)
                self._update_single_status_indicator(field_name)
                break
        self._validate()

    def _on_derive_toggled(self, checked: bool) -> None:
        """Handle derive checkbox toggle.

        Args:
            checked: Whether checkbox is checked.
        """
        self._combos["win_loss"].setVisible(not checked)
        self._preview_labels["win_loss"].setVisible(not checked)
        self._status_labels["win_loss"].setVisible(not checked)
        self._breakeven_checkbox.setVisible(checked)
        self._validate()

    def _validate(self) -> bool:
        """Validate current selections.

        Returns:
            True if valid, False otherwise.
        """
        errors: list[str] = []
        selected: list[str] = []

        # Check required fields
        required = ["ticker", "date", "time", "gain_pct", "mae_pct", "mfe_pct"]
        for field in required:
            value = self._combos[field].currentText()
            if not value:
                errors.append(f"Required column not mapped: {field}")
            else:
                selected.append(value)

        # Check win_loss if not deriving
        if not self._derive_checkbox.isChecked():
            win_loss = self._combos["win_loss"].currentText()
            if win_loss:
                selected.append(win_loss)

        # Check for duplicates
        if len(selected) != len(set(selected)):
            errors.append("Duplicate column selections")

        # Update UI
        if errors:
            self._error_label.setText(errors[0])
            self._error_label.setVisible(True)
            self._continue_btn.setEnabled(False)
            return False
        else:
            self._error_label.setVisible(False)
            self._continue_btn.setEnabled(True)
            return True

    def _on_continue_clicked(self) -> None:
        """Handle continue button click."""
        if not self._validate():
            return

        mapping = ColumnMapping(
            ticker=self._combos["ticker"].currentText(),
            date=self._combos["date"].currentText(),
            time=self._combos["time"].currentText(),
            gain_pct=self._combos["gain_pct"].currentText(),
            mae_pct=self._combos["mae_pct"].currentText(),
            mfe_pct=self._combos["mfe_pct"].currentText(),
            win_loss=self._combos["win_loss"].currentText() or None,
            mae_time=self._combos["mae_time"].currentText() or None,
            mfe_time=self._combos["mfe_time"].currentText() or None,
            price_10_min_after=self._combos["price_10_min_after"].currentText() or None,
            price_20_min_after=self._combos["price_20_min_after"].currentText() or None,
            price_30_min_after=self._combos["price_30_min_after"].currentText() or None,
            price_60_min_after=self._combos["price_60_min_after"].currentText() or None,
            price_90_min_after=self._combos["price_90_min_after"].currentText() or None,
            price_120_min_after=self._combos["price_120_min_after"].currentText() or None,
            price_150_min_after=self._combos["price_150_min_after"].currentText() or None,
            price_180_min_after=self._combos["price_180_min_after"].currentText() or None,
            price_240_min_after=self._combos["price_240_min_after"].currentText() or None,
            win_loss_derived=self._derive_checkbox.isChecked(),
            breakeven_is_win=self._breakeven_checkbox.isChecked(),
        )

        logger.info(
            "Column mapping completed: ticker=%s, date=%s, time=%s, gain=%s, mae=%s, mfe=%s, mae_time=%s, mfe_time=%s",
            mapping.ticker,
            mapping.date,
            mapping.time,
            mapping.gain_pct,
            mapping.mae_pct,
            mapping.mfe_pct,
            mapping.mae_time,
            mapping.mfe_time,
        )

        self.mapping_completed.emit(mapping)

    def get_mapping(self) -> ColumnMapping | None:
        """Get current mapping if valid.

        Returns:
            ColumnMapping if valid, None otherwise.
        """
        if not self._validate():
            return None

        return ColumnMapping(
            ticker=self._combos["ticker"].currentText(),
            date=self._combos["date"].currentText(),
            time=self._combos["time"].currentText(),
            gain_pct=self._combos["gain_pct"].currentText(),
            mae_pct=self._combos["mae_pct"].currentText(),
            mfe_pct=self._combos["mfe_pct"].currentText(),
            win_loss=self._combos["win_loss"].currentText() or None,
            mae_time=self._combos["mae_time"].currentText() or None,
            mfe_time=self._combos["mfe_time"].currentText() or None,
            price_10_min_after=self._combos["price_10_min_after"].currentText() or None,
            price_20_min_after=self._combos["price_20_min_after"].currentText() or None,
            price_30_min_after=self._combos["price_30_min_after"].currentText() or None,
            price_60_min_after=self._combos["price_60_min_after"].currentText() or None,
            price_90_min_after=self._combos["price_90_min_after"].currentText() or None,
            price_120_min_after=self._combos["price_120_min_after"].currentText() or None,
            price_150_min_after=self._combos["price_150_min_after"].currentText() or None,
            price_180_min_after=self._combos["price_180_min_after"].currentText() or None,
            price_240_min_after=self._combos["price_240_min_after"].currentText() or None,
            win_loss_derived=self._derive_checkbox.isChecked(),
            breakeven_is_win=self._breakeven_checkbox.isChecked(),
        )


class ColumnMappingSuccessPanel(QWidget):
    """Panel shown when all columns are auto-detected successfully."""

    edit_requested = pyqtSignal()  # Emitted when user wants to edit mappings
    continue_requested = pyqtSignal()  # Emitted when user wants to continue

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the success panel.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._mapping: ColumnMapping | None = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.MD)
        layout.setContentsMargins(0, 0, 0, 0)

        # Success message
        header = QLabel("✓ All columns detected automatically")
        header.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.SIGNAL_CYAN};
                font-size: 16px;
                font-weight: bold;
            }}
        """
        )
        layout.addWidget(header)

        # Mapping summary
        self._summary_label = QLabel()
        self._summary_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 13px;
                line-height: 1.5;
            }}
        """
        )
        layout.addWidget(self._summary_label)

        # Buttons
        button_row = QHBoxLayout()
        button_row.setSpacing(Spacing.SM)

        self._continue_btn = QPushButton("Continue")
        self._continue_btn.setObjectName("continue_button")
        self._continue_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {Colors.SIGNAL_CYAN};
                color: {Colors.BG_BASE};
                border: none;
                border-radius: 4px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #00E6BF;
            }}
            QPushButton:pressed {{
                background-color: #00CCaa;
            }}
        """
        )
        button_row.addWidget(self._continue_btn)

        self._edit_btn = QPushButton("Edit Mappings")
        self._edit_btn.setObjectName("edit_mappings_button")
        self._edit_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 10px 24px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                border-color: {Colors.SIGNAL_CYAN};
                color: {Colors.TEXT_PRIMARY};
            }}
        """
        )
        button_row.addWidget(self._edit_btn)
        button_row.addStretch()

        layout.addLayout(button_row)

    def _connect_signals(self) -> None:
        """Connect widget signals."""
        self._edit_btn.clicked.connect(self.edit_requested.emit)
        self._continue_btn.clicked.connect(self.continue_requested.emit)

    def set_mapping(self, mapping: ColumnMapping) -> None:
        """Set the detected mapping to display.

        Args:
            mapping: The auto-detected column mapping.
        """
        self._mapping = mapping
        summary = (
            f"Ticker: {mapping.ticker}\n"
            f"Date: {mapping.date}\n"
            f"Time: {mapping.time}\n"
            f"Gain %: {mapping.gain_pct}\n"
            f"MAE %: {mapping.mae_pct}\n"
            f"MFE %: {mapping.mfe_pct}"
        )
        if mapping.win_loss:
            summary += f"\nWin/Loss: {mapping.win_loss}"
        if mapping.mae_time:
            summary += f"\nMAE Time: {mapping.mae_time}"
        if mapping.mfe_time:
            summary += f"\nMFE Time: {mapping.mfe_time}"
        # Time interval price columns
        if mapping.price_10_min_after:
            summary += f"\nPrice 10 Mins After: {mapping.price_10_min_after}"
        if mapping.price_20_min_after:
            summary += f"\nPrice 20 Mins After: {mapping.price_20_min_after}"
        if mapping.price_30_min_after:
            summary += f"\nPrice 30 Mins After: {mapping.price_30_min_after}"
        if mapping.price_60_min_after:
            summary += f"\nPrice 60 Mins After: {mapping.price_60_min_after}"
        if mapping.price_90_min_after:
            summary += f"\nPrice 90 Mins After: {mapping.price_90_min_after}"
        if mapping.price_120_min_after:
            summary += f"\nPrice 120 Mins After: {mapping.price_120_min_after}"
        if mapping.price_150_min_after:
            summary += f"\nPrice 150 Mins After: {mapping.price_150_min_after}"
        if mapping.price_180_min_after:
            summary += f"\nPrice 180 Mins After: {mapping.price_180_min_after}"
        if mapping.price_240_min_after:
            summary += f"\nPrice 240 Mins After: {mapping.price_240_min_after}"
        self._summary_label.setText(summary)

    def get_mapping(self) -> ColumnMapping | None:
        """Get the current mapping.

        Returns:
            The column mapping or None.
        """
        return self._mapping


class BaselineInfoCard(QWidget):
    """Info card displaying baseline dataset statistics.

    Shows the count of first triggers extracted from total rows with
    a styled card using stellar-blue left border.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the BaselineInfoCard.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI layout and widgets."""
        self.setObjectName("baselineInfoCard")
        self.setStyleSheet(
            f"""
            QWidget#baselineInfoCard {{
                background-color: {Colors.BG_ELEVATED};
                border-left: 4px solid {Colors.SIGNAL_BLUE};
                border-radius: 4px;
            }}
        """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)

        self._message_label = QLabel()
        self._message_label.setObjectName("message_label")
        self._message_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-size: 14px;
            }}
        """
        )
        layout.addWidget(self._message_label)
        layout.addStretch()

    def update_counts(self, total_rows: int, baseline_rows: int) -> None:
        """Update the displayed row counts.

        Args:
            total_rows: Total number of rows in the raw data.
            baseline_rows: Number of first trigger rows in baseline.
        """
        self._message_label.setText(
            f"Baseline: {baseline_rows:,} first triggers from {total_rows:,} total rows"
        )


class AdjustmentInputsPanel(QWidget):
    """Panel for configuring stop loss and efficiency adjustment parameters.

    Provides input controls for Stop Loss % and Efficiency % with immediate
    feedback via the params_changed signal.
    """

    params_changed = pyqtSignal(object)  # Emits AdjustmentParams

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the AdjustmentInputsPanel.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._params = AdjustmentParams()
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the UI layout and widgets."""
        self.setObjectName("adjustmentInputsPanel")
        self.setStyleSheet(
            f"""
            QWidget#adjustmentInputsPanel {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: 8px;
            }}
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.UI};
                font-size: 12px;
            }}
            QDoubleSpinBox {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                font-family: {Fonts.DATA};
                font-size: 14px;
            }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                background-color: {Colors.BG_BORDER};
                border: none;
                width: 16px;
            }}
        """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        layout.setSpacing(Spacing.SM)

        # Title
        title = QLabel("Trade Adjustments")
        title.setStyleSheet(
            f"""
            color: {Colors.TEXT_PRIMARY};
            font-family: {Fonts.UI};
            font-size: 14px;
            font-weight: bold;
        """
        )
        layout.addWidget(title)

        # Inputs grid
        inputs_layout = QGridLayout()
        inputs_layout.setSpacing(Spacing.SM)
        inputs_layout.setColumnStretch(1, 1)

        # Stop Loss %
        stop_loss_label = QLabel("Stop Loss %")
        self._stop_loss_spin = NoScrollDoubleSpinBox()
        self._stop_loss_spin.setObjectName("stop_loss_spin")
        self._stop_loss_spin.setRange(0.0, 100.0)
        self._stop_loss_spin.setValue(100.0)
        self._stop_loss_spin.setSingleStep(0.5)
        self._stop_loss_spin.setDecimals(1)
        self._stop_loss_spin.setSuffix("%")
        inputs_layout.addWidget(stop_loss_label, 0, 0)
        inputs_layout.addWidget(self._stop_loss_spin, 0, 1)

        # Efficiency %
        efficiency_label = QLabel("Efficiency %")
        self._efficiency_spin = NoScrollDoubleSpinBox()
        self._efficiency_spin.setObjectName("efficiency_spin")
        self._efficiency_spin.setRange(0.0, 100.0)
        self._efficiency_spin.setValue(5.0)
        self._efficiency_spin.setSingleStep(0.5)
        self._efficiency_spin.setDecimals(1)
        self._efficiency_spin.setSuffix("%")
        inputs_layout.addWidget(efficiency_label, 1, 0)
        inputs_layout.addWidget(self._efficiency_spin, 1, 1)

        # Short Strategy checkbox
        self._is_short_checkbox = QCheckBox("Short Strategy")
        self._is_short_checkbox.setObjectName("is_short_checkbox")
        self._is_short_checkbox.setChecked(True)
        self._is_short_checkbox.setToolTip("Check if trading short positions (stop above entry)")
        inputs_layout.addWidget(self._is_short_checkbox, 2, 0, 1, 2)

        layout.addLayout(inputs_layout)

    def _connect_signals(self) -> None:
        """Connect input signals to handlers."""
        self._stop_loss_spin.valueChanged.connect(self._on_value_changed)
        self._efficiency_spin.valueChanged.connect(self._on_value_changed)
        self._is_short_checkbox.stateChanged.connect(self._on_value_changed)

    def _on_value_changed(self) -> None:
        """Handle value changes in spinboxes and checkbox."""
        self._params = AdjustmentParams(
            stop_loss=self._stop_loss_spin.value(),
            efficiency=self._efficiency_spin.value(),
            is_short=self._is_short_checkbox.isChecked(),
        )
        self.params_changed.emit(self._params)
        logger.debug(
            "Adjustment params changed: stop_loss=%.1f%%, efficiency=%.1f%%, is_short=%s",
            self._params.stop_loss,
            self._params.efficiency,
            self._params.is_short,
        )

    def get_params(self) -> AdjustmentParams:
        """Get the current adjustment parameters.

        Returns:
            Current AdjustmentParams values.
        """
        return self._params

    def set_params(self, params: AdjustmentParams) -> None:
        """Set the adjustment parameters.

        Args:
            params: AdjustmentParams to set.
        """
        self._params = params
        # Block signals to prevent triggering params_changed during set
        self._stop_loss_spin.blockSignals(True)
        self._efficiency_spin.blockSignals(True)
        self._is_short_checkbox.blockSignals(True)
        self._stop_loss_spin.setValue(params.stop_loss)
        self._efficiency_spin.setValue(params.efficiency)
        self._is_short_checkbox.setChecked(params.is_short)
        self._stop_loss_spin.blockSignals(False)
        self._efficiency_spin.blockSignals(False)
        self._is_short_checkbox.blockSignals(False)


class MetricsPanel(QWidget):
    """Panel displaying 7 metric cards in a grid layout.

    Shows trading metrics: Trades, Win Rate, Avg Winner, Avg Loser,
    R:R Ratio, EV, and Kelly.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the MetricsPanel.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._cards: dict[str, MetricCard] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI layout and widgets."""
        self.setObjectName("metrics_panel")

        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.MD)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title = QLabel("Baseline Metrics")
        title.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.UI};
                font-size: 18px;
                font-weight: bold;
            }}
        """
        )
        layout.addWidget(title)

        # Grid of metric cards
        grid = QGridLayout()
        grid.setSpacing(Spacing.MD)

        # Define cards with (key, label, row, col)
        card_defs = [
            ("trades", "Trades", 0, 0),
            ("win_rate", "Win Rate", 0, 1),
            ("avg_winner", "Avg Winner", 0, 2),
            ("avg_loser", "Avg Loser", 1, 0),
            ("rr_ratio", "R:R Ratio", 1, 1),
            ("ev", "EV", 1, 2),
            ("kelly", "Kelly", 2, 0),
        ]

        for key, label, row, col in card_defs:
            card = MetricCard(label=label, variant=MetricCard.STANDARD)
            self._cards[key] = card
            grid.addWidget(card, row, col)

        layout.addLayout(grid)

    def update_metrics(self, metrics: TradingMetrics | None) -> None:
        """Update all metric cards with new values.

        Args:
            metrics: TradingMetrics instance or None to clear display.
        """
        if metrics is None:
            for card in self._cards.values():
                card.update_value(None)
            return

        # Debug logging to help diagnose display issues
        logger.debug(
            "MetricsPanel update - win=%.4f, avg_w=%.4f, avg_l=%.4f, ev=%.4f, kelly=%.4f",
            metrics.win_rate if metrics.win_rate else 0,
            metrics.avg_winner if metrics.avg_winner else 0,
            metrics.avg_loser if metrics.avg_loser else 0,
            metrics.ev if metrics.ev else 0,
            metrics.kelly if metrics.kelly else 0,
        )

        # Trades: integer with thousands separator
        self._cards["trades"].update_value(metrics.num_trades)

        # Win Rate: one decimal + percent
        if metrics.win_rate is not None:
            self._cards["win_rate"].update_value(metrics.win_rate, format_spec=".1f")
            # Manually append % to display
            current_text = self._cards["win_rate"]._value_widget.text()
            self._cards["win_rate"]._value_widget.setText(f"{current_text}%")
        else:
            self._cards["win_rate"].update_value(None)

        # Avg Winner: sign + two decimals + percent
        if metrics.avg_winner is not None:
            self._cards["avg_winner"].update_value(metrics.avg_winner, format_spec="+.2f")
            current_text = self._cards["avg_winner"]._value_widget.text()
            self._cards["avg_winner"]._value_widget.setText(f"{current_text}%")
        else:
            self._cards["avg_winner"].update_value(None)

        # Avg Loser: sign + two decimals + percent
        if metrics.avg_loser is not None:
            self._cards["avg_loser"].update_value(metrics.avg_loser, format_spec="+.2f")
            current_text = self._cards["avg_loser"]._value_widget.text()
            self._cards["avg_loser"]._value_widget.setText(f"{current_text}%")
        else:
            self._cards["avg_loser"].update_value(None)

        # R:R Ratio: two decimals
        if metrics.rr_ratio is not None:
            self._cards["rr_ratio"].update_value(metrics.rr_ratio, format_spec=".2f")
        else:
            self._cards["rr_ratio"].update_value(None)

        # EV: sign + two decimals + percent
        if metrics.ev is not None:
            self._cards["ev"].update_value(metrics.ev, format_spec="+.2f")
            current_text = self._cards["ev"]._value_widget.text()
            self._cards["ev"]._value_widget.setText(f"{current_text}%")
        else:
            self._cards["ev"].update_value(None)

        # Kelly: one decimal + percent
        if metrics.kelly is not None:
            self._cards["kelly"].update_value(metrics.kelly, format_spec=".1f")
            current_text = self._cards["kelly"]._value_widget.text()
            self._cards["kelly"]._value_widget.setText(f"{current_text}%")
        else:
            self._cards["kelly"].update_value(None)


class DataInputTab(QWidget):
    """Tab for data file loading and column configuration."""

    data_loaded = pyqtSignal(object)  # Emits DataFrame when data is loaded
    mapping_completed = pyqtSignal(object)  # Emits ColumnMapping when mapping done

    def __init__(self, app_state: AppState | None = None, parent: QWidget | None = None) -> None:
        """Initialize the Data Input tab.

        Args:
            app_state: Shared application state (optional for backwards compatibility).
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._app_state = app_state
        self._selected_path: Path | None = None
        self._selected_sheet: str | None = None
        self._worker: FileLoadWorker | None = None
        self._mapping_worker: MappingWorker | None = None
        self._df: pd.DataFrame | None = None
        self._file_loader = FileLoader()
        self._column_mapper = ColumnMapper()
        self._column_mapping: ColumnMapping | None = None
        self._last_load_from_cache: bool = False
        self._first_trigger_engine = FirstTriggerEngine()
        self._metrics_calculator = MetricsCalculator()
        self._pending_adjustment_params: AdjustmentParams | None = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the UI layout and widgets."""
        # Main layout for scroll area (no margins)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setStyleSheet(f"QScrollArea {{ background-color: {Colors.BG_BASE}; }}")

        # Content widget that will be scrollable
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(Spacing.LG)
        layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)

        # Section header
        header_label = QLabel("Select Data File")
        header_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: "{Fonts.UI}";
                font-size: 18px;
                font-weight: bold;
            }}
        """
        )
        layout.addWidget(header_label)

        # File selection row
        file_row = QHBoxLayout()
        file_row.setSpacing(Spacing.SM)

        self._select_file_btn = QPushButton("Select File")
        self._select_file_btn.setObjectName("select_file_button")
        self._select_file_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 8px 16px;
                font-family: "{Fonts.UI}";
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_BORDER};
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QPushButton:pressed {{
                background-color: {Colors.BG_BASE};
            }}
        """
        )
        file_row.addWidget(self._select_file_btn)

        self._file_path_display = QLineEdit()
        self._file_path_display.setObjectName("file_path_display")
        self._file_path_display.setReadOnly(True)
        self._file_path_display.setPlaceholderText("No file selected")
        self._file_path_display.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-family: "{Fonts.DATA}";
                font-size: 13px;
            }}
        """
        )
        file_row.addWidget(self._file_path_display, 1)

        layout.addLayout(file_row)

        # Sheet selector (hidden by default)
        sheet_row = QHBoxLayout()
        sheet_row.setSpacing(Spacing.SM)

        sheet_label = QLabel("Sheet:")
        sheet_style = f'color: {Colors.TEXT_SECONDARY}; font-family: "{Fonts.UI}"; font-size: 13px;'
        sheet_label.setStyleSheet(sheet_style)
        self._sheet_label = sheet_label

        self._sheet_selector = NoScrollComboBox()
        self._sheet_selector.setObjectName("sheet_selector")
        self._sheet_selector.setStyleSheet(
            f"""
            QComboBox {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-family: "{Fonts.UI}";
                font-size: 13px;
                min-width: 200px;
            }}
            QComboBox:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                selection-background-color: {Colors.BG_BORDER};
                selection-color: {Colors.TEXT_PRIMARY};
                font-family: "{Fonts.UI}";
            }}
        """
        )
        sheet_row.addWidget(sheet_label)
        sheet_row.addWidget(self._sheet_selector)
        sheet_row.addStretch()

        # Initially hidden
        self._sheet_label.setVisible(False)
        self._sheet_selector.setVisible(False)

        layout.addLayout(sheet_row)

        # Load button row
        load_row = QHBoxLayout()
        load_row.setSpacing(Spacing.SM)

        self._load_data_btn = QPushButton("Load Data")
        self._load_data_btn.setObjectName("load_data_button")
        self._load_data_btn.setEnabled(False)
        self._load_data_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {Colors.SIGNAL_CYAN};
                color: {Colors.BG_BASE};
                border: none;
                border-radius: 4px;
                padding: 10px 24px;
                font-family: "{Fonts.UI}";
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #00E6BF;
            }}
            QPushButton:pressed {{
                background-color: #00CCaa;
            }}
            QPushButton:disabled {{
                background-color: {Colors.BG_BORDER};
                color: {Colors.TEXT_DISABLED};
            }}
        """
        )
        load_row.addWidget(self._load_data_btn)

        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("progress_bar")
        self._progress_bar.setVisible(False)
        self._progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                text-align: center;
                color: {Colors.TEXT_PRIMARY};
                font-size: 12px;
            }}
            QProgressBar::chunk {{
                background-color: {Colors.SIGNAL_CYAN};
                border-radius: 3px;
            }}
        """
        )
        load_row.addWidget(self._progress_bar)
        load_row.addStretch()

        layout.addLayout(load_row)

        # Status message label
        self._status_label = QLabel()
        self._status_label.setObjectName("status_label")
        self._status_label.setStyleSheet(
            f"""
            QLabel {{
                font-family: "{Fonts.UI}";
                font-size: 14px;
                padding: 8px 0;
            }}
        """
        )
        layout.addWidget(self._status_label)

        # Column mapping success panel (hidden by default)
        self._success_panel = ColumnMappingSuccessPanel()
        self._success_panel.setVisible(False)
        layout.addWidget(self._success_panel)

        # Column configuration panel (hidden by default)
        self._config_panel = ColumnConfigPanel()
        self._config_panel.setVisible(False)
        layout.addWidget(self._config_panel)

        # Baseline info card (hidden by default)
        self._baseline_card = BaselineInfoCard()
        self._baseline_card.setObjectName("baseline_info_card")
        self._baseline_card.setVisible(False)
        layout.addWidget(self._baseline_card)

        # Adjustment inputs panel (hidden by default)
        self._adjustment_panel = AdjustmentInputsPanel()
        self._adjustment_panel.setObjectName("adjustment_inputs_panel")
        self._adjustment_panel.setVisible(False)
        layout.addWidget(self._adjustment_panel)

        # Debounce timer for adjustment changes (300ms)
        self._adjustment_debounce_timer = QTimer()
        self._adjustment_debounce_timer.setSingleShot(True)
        self._adjustment_debounce_timer.setInterval(300)

        # Metrics panel (hidden by default)
        self._metrics_panel = MetricsPanel()
        self._metrics_panel.setObjectName("metrics_panel")
        self._metrics_panel.setVisible(False)
        layout.addWidget(self._metrics_panel)

        # Add stretch to push everything to the top
        layout.addStretch()

        # Set up scroll area with content
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

    def _connect_signals(self) -> None:
        """Connect widget signals to slots."""
        self._select_file_btn.clicked.connect(self._on_select_file_clicked)
        self._load_data_btn.clicked.connect(self._on_load_data_clicked)
        self.data_loaded.connect(self._on_data_loaded)
        self._success_panel.edit_requested.connect(self._on_edit_mappings_requested)
        self._success_panel.continue_requested.connect(self._on_mapping_continue)
        self._config_panel.mapping_completed.connect(self._on_mapping_continue)
        # Adjustment panel signals with 300ms debounce
        self._adjustment_panel.params_changed.connect(self._on_adjustment_params_changed)
        self._adjustment_debounce_timer.timeout.connect(self._recalculate_metrics)

    def _on_select_file_clicked(self) -> None:
        """Handle Select File button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Data File",
            "",
            "All Supported Files (*.xlsx *.xls *.csv *.parquet);;"
            "Excel Files (*.xlsx *.xls);;"
            "CSV Files (*.csv);;"
            "Parquet Files (*.parquet)",
        )

        if not file_path:
            # User cancelled
            return

        self._selected_path = Path(file_path)
        self._file_path_display.setText(file_path)
        self._file_path_display.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 8px;
                font-family: "{Fonts.DATA}";
                font-size: 13px;
            }}
        """
        )

        # Clear previous status
        self._status_label.clear()

        # Handle Excel files - show sheet selector
        suffix = self._selected_path.suffix.lower()
        if suffix in {".xlsx", ".xls"}:
            try:
                sheet_names = self._file_loader.get_sheet_names(self._selected_path)
                self._sheet_selector.clear()
                self._sheet_selector.addItems(sheet_names)
                self._sheet_label.setVisible(True)
                self._sheet_selector.setVisible(True)
            except Exception as e:
                self._show_error(str(e))
                return
        else:
            self._sheet_label.setVisible(False)
            self._sheet_selector.setVisible(False)

        # Enable load button
        self._load_data_btn.setEnabled(True)

    def _on_load_data_clicked(self) -> None:
        """Handle Load Data button click."""
        if self._selected_path is None:
            return

        # Get selected sheet for Excel files
        sheet: str | None = None
        if self._sheet_selector.isVisible():
            sheet = self._sheet_selector.currentText()
        self._selected_sheet = sheet

        # Disable UI during loading
        self._select_file_btn.setEnabled(False)
        self._load_data_btn.setEnabled(False)
        self._sheet_selector.setEnabled(False)

        # Show progress bar
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._status_label.clear()

        # Create and start worker
        self._worker = FileLoadWorker(self._selected_path, sheet)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_load_complete)
        self._worker.error.connect(self._on_load_error)
        self._worker.cache_hit.connect(self._on_cache_hit)
        self._worker.start()

    def _on_progress(self, value: int) -> None:
        """Handle progress updates from worker."""
        self._progress_bar.setValue(value)

    def _on_cache_hit(self, from_cache: bool) -> None:
        """Handle cache hit signal from worker.

        Args:
            from_cache: True if data was loaded from cache.
        """
        self._last_load_from_cache = from_cache

    def _on_load_complete(self, df: pd.DataFrame) -> None:
        """Handle successful data load.

        Args:
            df: The loaded DataFrame.
        """
        self._df = df
        self._progress_bar.setVisible(False)

        # Re-enable UI
        self._select_file_btn.setEnabled(True)
        self._load_data_btn.setEnabled(True)
        self._sheet_selector.setEnabled(True)

        # Show success message based on cache status
        filename = self._selected_path.name if self._selected_path else "file"
        row_count = len(df)

        if self._last_load_from_cache:
            self._status_label.setText(f"✓ Loaded from cache ({row_count:,} rows)")
            status_color = Colors.SIGNAL_CYAN
            logger.info("Loaded %d rows from cache for %s", row_count, filename)
        else:
            self._status_label.setText(f"✓ Loaded {row_count:,} rows from {filename}")
            status_color = Colors.SIGNAL_BLUE
            logger.info("Loaded %d rows from %s", row_count, filename)

        self._status_label.setStyleSheet(
            f"""
            QLabel {{
                color: {status_color};
                font-family: "{Fonts.UI}";
                font-size: 14px;
                padding: 8px 0;
            }}
        """
        )

        # Emit signal for column auto-detection
        self.data_loaded.emit(df)

    def _on_load_error(self, error_message: str) -> None:
        """Handle load error.

        Args:
            error_message: The error message to display.
        """
        self._progress_bar.setVisible(False)

        # Re-enable UI
        self._select_file_btn.setEnabled(True)
        self._load_data_btn.setEnabled(True)
        self._sheet_selector.setEnabled(True)

        self._show_error(error_message)

    def _show_error(self, message: str) -> None:
        """Display an error message.

        Args:
            message: The error message to display.
        """
        self._status_label.setText(message)
        self._status_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.SIGNAL_CORAL};
                font-family: "{Fonts.UI}";
                font-size: 14px;
                padding: 8px 0;
            }}
        """
        )
        logger.error("File load error: %s", message)

    def _on_data_loaded(self, df: pd.DataFrame) -> None:
        """Handle data loaded signal - trigger column detection.

        Args:
            df: The loaded DataFrame.
        """
        if self._selected_path is None:
            return

        # Check for cached mapping first
        cached_mapping = self._column_mapper.load_mapping(self._selected_path, self._selected_sheet)
        if cached_mapping:
            # Validate cached mapping against current columns
            errors = cached_mapping.validate(list(df.columns))
            if not errors:
                logger.info("Using cached column mapping")
                self._column_mapping = cached_mapping
                self._success_panel.set_mapping(cached_mapping)
                self._success_panel.setVisible(True)
                self._config_panel.setVisible(False)
                return

        # Auto-detect columns
        detection_result = self._column_mapper.auto_detect(list(df.columns))

        if detection_result.all_required_detected and detection_result.mapping:
            # Show success panel
            self._success_panel.set_mapping(detection_result.mapping)
            self._success_panel.setVisible(True)
            self._config_panel.setVisible(False)
        else:
            # Show config panel
            self._config_panel.set_columns(list(df.columns), df, detection_result)
            self._config_panel.setVisible(True)
            self._success_panel.setVisible(False)

    def _on_edit_mappings_requested(self) -> None:
        """Handle edit mappings button click."""
        if self._df is None:
            return

        # Create detection result from current mapping for display
        mapping = self._success_panel.get_mapping()
        statuses = {
            "ticker": "detected",
            "date": "detected",
            "time": "detected",
            "gain_pct": "detected",
            "mae_pct": "detected",
            "mfe_pct": "detected",
            "win_loss": "detected" if mapping and mapping.win_loss else "missing",
            "mae_time": "detected" if mapping and mapping.mae_time else "missing",
            "mfe_time": "detected" if mapping and mapping.mfe_time else "missing",
            "price_10_min_after": "detected" if mapping and mapping.price_10_min_after else "missing",
            "price_20_min_after": "detected" if mapping and mapping.price_20_min_after else "missing",
            "price_30_min_after": "detected" if mapping and mapping.price_30_min_after else "missing",
            "price_60_min_after": "detected" if mapping and mapping.price_60_min_after else "missing",
            "price_90_min_after": "detected" if mapping and mapping.price_90_min_after else "missing",
            "price_120_min_after": "detected" if mapping and mapping.price_120_min_after else "missing",
            "price_150_min_after": "detected" if mapping and mapping.price_150_min_after else "missing",
            "price_180_min_after": "detected" if mapping and mapping.price_180_min_after else "missing",
            "price_240_min_after": "detected" if mapping and mapping.price_240_min_after else "missing",
        }
        detection_result = DetectionResult(
            mapping=mapping,
            statuses=statuses,
            all_required_detected=True,
        )

        self._config_panel.set_columns(list(self._df.columns), self._df, detection_result)
        self._success_panel.setVisible(False)
        self._config_panel.setVisible(True)

    def _on_mapping_continue(self, mapping: ColumnMapping | None = None) -> None:
        """Handle continue after mapping is complete.

        Saves the mapping to cache (fast) and launches the heavy computation
        on a background ``MappingWorker`` thread so the UI stays responsive.

        Args:
            mapping: The column mapping (from config panel signal).
        """
        if mapping is None:
            mapping = self._success_panel.get_mapping()

        if mapping is None or self._selected_path is None or self._df is None:
            return

        self._column_mapping = mapping

        # Persist mapping to cache (fast, stays on main thread)
        self._column_mapper.save_mapping(self._selected_path, mapping, self._selected_sheet)
        logger.info("Column mapping saved to cache")

        # Get current adjustment params
        adjustment_params = self._adjustment_panel.get_params()
        self._pending_adjustment_params = adjustment_params

        # Get flat stake and start capital from AppState or use defaults
        metrics_inputs = self._app_state.metrics_user_inputs if self._app_state else None
        flat_stake = metrics_inputs.flat_stake if metrics_inputs else 10000.0
        start_capital = metrics_inputs.starting_capital if metrics_inputs else 100000.0

        # Disable Continue buttons and show progress bar
        self._success_panel.setVisible(False)
        self._config_panel.setVisible(False)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._status_label.setText("Processing data...")
        self._status_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: "{Fonts.UI}";
                font-size: 14px;
                padding: 8px 0;
            }}
        """
        )

        # Launch background worker
        self._mapping_worker = MappingWorker(
            df=self._df,
            mapping=mapping,
            adjustment_params=adjustment_params,
            flat_stake=flat_stake,
            start_capital=start_capital,
        )
        self._mapping_worker.progress.connect(self._on_progress)
        self._mapping_worker.finished.connect(self._on_mapping_complete)
        self._mapping_worker.error.connect(self._on_mapping_error)
        self._mapping_worker.start()

    def _on_mapping_complete(self, result: MappingResult) -> None:
        """Handle successful completion of the background mapping worker.

        Updates AppState, emits signals, and shows baseline/metrics UI.

        Args:
            result: MappingResult from the worker thread.
        """
        mapping = self._column_mapping
        if mapping is None:
            return

        self._progress_bar.setVisible(False)

        baseline_df = result.baseline_df
        metrics = result.metrics
        flat_equity = result.flat_equity
        kelly_equity = result.kelly_equity
        adjustment_params = self._pending_adjustment_params or self._adjustment_panel.get_params()

        max_trigger = baseline_df["trigger_number"].max() if result.total_rows > 0 else 0
        logger.info(
            "Trigger numbers assigned: %d rows, max trigger_number=%d",
            result.total_rows,
            max_trigger,
        )
        logger.info(
            "data_input._on_mapping_complete: Using %d first triggers (from %d total rows)",
            result.baseline_rows,
            result.total_rows,
        )

        # Update AppState if available
        if self._app_state is not None:
            self._app_state.source_file_path = str(self._selected_path)
            self._app_state.source_sheet = self._selected_sheet or ""
            self._app_state.raw_df = self._df
            self._app_state.baseline_df = baseline_df
            self._app_state.column_mapping = mapping
            self._app_state.baseline_metrics = metrics
            self._app_state.adjustment_params = adjustment_params
            # Store equity curves for chart display
            self._app_state.flat_stake_equity_curve = flat_equity
            self._app_state.kelly_equity_curve = kelly_equity
            self._app_state.data_loaded.emit(baseline_df)
            self._app_state.column_mapping_changed.emit(mapping)
            self._app_state.baseline_calculated.emit(metrics)
            self._app_state.adjustment_params_changed.emit(adjustment_params)
            # Emit equity curve signals for chart updates
            if flat_equity is not None:
                self._app_state.equity_curve_updated.emit(flat_equity)
            # Only emit Kelly equity curve if baseline Kelly is positive
            if kelly_equity is not None and metrics.kelly is not None and metrics.kelly > 0:
                self._app_state.kelly_equity_curve_updated.emit(kelly_equity)
            elif kelly_equity is not None:
                # Clear the Kelly chart when Kelly is negative
                self._app_state.kelly_equity_curve_updated.emit(pd.DataFrame())
                if metrics.kelly is not None:
                    logger.info(
                        "Baseline Kelly is negative (%.2f%%), not plotting Kelly curve",
                        metrics.kelly,
                    )
                else:
                    logger.info("Baseline Kelly is None, not plotting Kelly curve")

        # Display baseline info card
        self._baseline_card.update_counts(result.total_rows, result.baseline_rows)
        self._baseline_card.setVisible(True)

        # Display adjustment inputs panel
        self._adjustment_panel.setVisible(True)

        # Display metrics panel
        self._metrics_panel.update_metrics(metrics)
        self._metrics_panel.setVisible(True)

        # Show success status
        self._status_label.setText(
            f"✓ Processed {result.total_rows:,} rows "
            f"({result.baseline_rows:,} first triggers)"
        )
        self._status_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.SIGNAL_CYAN};
                font-family: "{Fonts.UI}";
                font-size: 14px;
                padding: 8px 0;
            }}
        """
        )

        # Emit signal for next workflow step
        self.mapping_completed.emit(mapping)

    def _on_mapping_error(self, error_message: str) -> None:
        """Handle mapping worker error.

        Args:
            error_message: The error message to display.
        """
        self._progress_bar.setVisible(False)
        self._show_error(f"Processing error: {error_message}")
        logger.error("MappingWorker error: %s", error_message)

    @property
    def dataframe(self) -> pd.DataFrame | None:
        """Get the currently loaded DataFrame."""
        return self._df

    @property
    def column_mapping(self) -> ColumnMapping | None:
        """Get the current column mapping."""
        return self._column_mapping

    def _on_adjustment_params_changed(self, params: AdjustmentParams) -> None:
        """Handle adjustment params change from panel.

        Stores the pending params and restarts the debounce timer.
        Updates AppState immediately for other listeners.

        Args:
            params: The new adjustment parameters.
        """
        self._pending_adjustment_params = params
        self._adjustment_debounce_timer.start()

        # Update AppState immediately (other components may listen)
        if self._app_state is not None:
            self._app_state.adjustment_params = params
            self._app_state.adjustment_params_changed.emit(params)

        logger.debug(
            "Adjustment params changed (debounced): stop_loss=%.1f%%, efficiency=%.1f%%",
            params.stop_loss,
            params.efficiency,
        )

    def _recalculate_metrics(self) -> None:
        """Recalculate metrics with current adjustment parameters.

        Called after debounce timer fires.
        """
        if self._pending_adjustment_params is None:
            return

        if self._app_state is None:
            logger.warning("Cannot recalculate metrics: AppState not available")
            return

        baseline_df = self._app_state.baseline_df
        mapping = self._app_state.column_mapping

        if baseline_df is None or mapping is None:
            logger.warning("Cannot recalculate metrics: baseline data not available")
            return

        # Update adjusted_gain_pct column in baseline_df
        if mapping.mae_pct is not None:
            adjusted_gains = self._pending_adjustment_params.calculate_adjusted_gains(
                baseline_df, mapping.gain_pct, mapping.mae_pct
            )
            baseline_df["adjusted_gain_pct"] = adjusted_gains

            # Also update filtered_df if it exists (it's a copy, so won't auto-update)
            filtered_df = self._app_state.filtered_df
            if filtered_df is not None and not filtered_df.empty:
                # Update adjusted_gain_pct for rows that exist in filtered_df
                # Use index alignment to copy only matching rows
                filtered_df["adjusted_gain_pct"] = baseline_df.loc[
                    filtered_df.index, "adjusted_gain_pct"
                ]
                logger.debug(
                    "Updated adjusted_gain_pct in filtered_df (%d rows)",
                    len(filtered_df),
                )
                # Emit filtered_data_updated so tabs like Statistics refresh with new values
                # This is critical because Statistics ignores baseline_calculated when
                # filtered_df exists, so it needs this signal to see updated adjusted_gain_pct
                self._app_state.filtered_data_updated.emit(filtered_df)

        # Ensure time_minutes column exists for time-based analysis
        has_time_col = mapping.time and mapping.time in baseline_df.columns
        if has_time_col and "time_minutes" not in baseline_df.columns:
            baseline_df["time_minutes"] = time_to_minutes(baseline_df[mapping.time])
            logger.debug("Added time_minutes column derived from '%s'", mapping.time)

        # Get flat stake and start capital from AppState or use defaults
        metrics_inputs = self._app_state.metrics_user_inputs
        flat_stake = metrics_inputs.flat_stake if metrics_inputs else 10000.0
        start_capital = metrics_inputs.starting_capital if metrics_inputs else 100000.0

        # Filter to first triggers only for baseline metrics recalculation
        first_triggers_df = baseline_df[baseline_df["trigger_number"] == 1].copy()
        logger.info(
            "data_input._recalculate_metrics: Using %d first triggers (from %d total rows)",
            len(first_triggers_df),
            len(baseline_df),
        )

        # Recalculate baseline metrics with adjustment params (3-tuple)
        metrics, flat_equity, kelly_equity = self._metrics_calculator.calculate(
            df=first_triggers_df,
            gain_col=mapping.gain_pct,
            win_loss_col=mapping.win_loss,
            derived=mapping.win_loss_derived,
            breakeven_is_win=mapping.breakeven_is_win,
            adjustment_params=self._pending_adjustment_params,
            mae_col=mapping.mae_pct,
            date_col=mapping.date,
            time_col=mapping.time,
            flat_stake=flat_stake,
            start_capital=start_capital,
        )

        # Update AppState and re-emit data_loaded so Feature Explorer sees updated column
        self._app_state.baseline_df = baseline_df
        self._app_state.baseline_metrics = metrics
        # Store equity curves for chart display
        self._app_state.flat_stake_equity_curve = flat_equity
        self._app_state.kelly_equity_curve = kelly_equity
        self._app_state.data_loaded.emit(baseline_df)
        self._app_state.baseline_calculated.emit(metrics)
        # Emit equity curve signals for chart updates
        if flat_equity is not None:
            self._app_state.equity_curve_updated.emit(flat_equity)
        # Only emit Kelly equity curve if baseline Kelly is positive
        if kelly_equity is not None and metrics.kelly is not None and metrics.kelly > 0:
            self._app_state.kelly_equity_curve_updated.emit(kelly_equity)
        elif kelly_equity is not None:
            # Clear the Kelly chart when Kelly is negative
            self._app_state.kelly_equity_curve_updated.emit(pd.DataFrame())
            if metrics.kelly is not None:
                logger.info(
                    "Baseline Kelly is negative (%.2f%%), not plotting Kelly curve",
                    metrics.kelly,
                )
            else:
                logger.info("Baseline Kelly is None, not plotting Kelly curve")

        # Update metrics display
        self._metrics_panel.update_metrics(metrics)

        logger.info(
            "Recalculated metrics with adjustments: %d trades, %.1f%% win rate",
            metrics.num_trades,
            metrics.win_rate or 0,
        )
