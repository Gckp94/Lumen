"""Export dialog for Lumen application.

Provides UI for exporting data and charts in various formats.
"""

from __future__ import annotations

import logging
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.ui.components.no_scroll_widgets import NoScrollComboBox
from src.ui.constants import Colors, Fonts, FontSizes, Spacing

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ExportCategory(Enum):
    """Export category types."""

    DATA = auto()
    CHARTS = auto()
    REPORT = auto()


class ExportFormat(Enum):
    """Export format types."""

    # Data formats
    CSV = "csv"
    EXCEL = "xlsx"
    PARQUET = "parquet"
    METRICS_CSV = "metrics_csv"
    # Chart formats
    PNG = "png"
    ZIP = "zip"


class ExportResolution(Enum):
    """Export resolution options."""

    HD_1080P = (1920, 1080)
    UHD_4K = (3840, 2160)

    @property
    def label(self) -> str:
        """Get display label for resolution."""
        if self == ExportResolution.HD_1080P:
            return "1080p (1920x1080)"
        return "4K (3840x2160)"


class ExportWorker(QThread):
    """Background worker for export operations.

    Runs export operations in a background thread to prevent UI freeze.
    Emits progress updates and completion/error signals.

    Note: This class is internal to export_dialog.py and should NOT be
    exported via __init__.py.
    """

    progress = pyqtSignal(int)  # 0-100 percentage
    finished = pyqtSignal(object)  # Emits Path to exported file on success
    error = pyqtSignal(str)  # Emits error message string on failure

    def __init__(
        self,
        export_func: Any,
        export_args: dict[str, Any],
        output_path: Path,
    ) -> None:
        """Initialize export worker.

        Args:
            export_func: The export function to call
            export_args: Arguments to pass to export function
            output_path: Output file path
        """
        super().__init__()
        self._export_func = export_func
        self._export_args = export_args
        self._output_path = output_path

    def run(self) -> None:
        """Run the export operation in background thread."""
        try:
            self.progress.emit(10)

            # Add progress callback if export supports it
            if "progress_callback" in self._export_args:
                self._export_args["progress_callback"] = self._emit_progress

            self._export_func(**self._export_args)

            self.progress.emit(100)
            self.finished.emit(self._output_path)

        except PermissionError as e:
            self.error.emit(f"Permission denied: Cannot write to {self._output_path}")
            logger.error("Export failed - permission denied: %s", e)
        except OSError as e:
            self.error.emit(f"Disk full or write error: {e}")
            logger.error("Export failed - OS error: %s", e)
        except Exception as e:
            self.error.emit(f"Export failed: {e}")
            logger.error("Export failed: %s", e)

    def _emit_progress(self, value: int) -> None:
        """Emit progress signal.

        Args:
            value: Progress value (0-100)
        """
        self.progress.emit(value)


class ExportDialog(QDialog):
    """Dialog for selecting export options.

    Provides category selection (Data/Charts/Report), format options,
    and resolution settings for chart exports.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize export dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._selected_category = ExportCategory.DATA
        self._selected_format = ExportFormat.CSV
        self._selected_resolution = ExportResolution.HD_1080P

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up dialog UI."""
        self.setWindowTitle("Export")
        self.setMinimumSize(400, 300)
        self.setModal(True)

        # Apply Observatory styling
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_ELEVATED};
            }}
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: "{Fonts.UI}";
                font-size: {FontSizes.BODY}px;
            }}
            QRadioButton {{
                color: {Colors.TEXT_PRIMARY};
                font-family: "{Fonts.UI}";
                font-size: {FontSizes.BODY}px;
                spacing: {Spacing.SM}px;
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
            }}
            QRadioButton::indicator:checked {{
                background-color: {Colors.SIGNAL_CYAN};
                border: 2px solid {Colors.SIGNAL_CYAN};
                border-radius: 8px;
            }}
            QRadioButton::indicator:unchecked {{
                background-color: transparent;
                border: 2px solid {Colors.TEXT_SECONDARY};
                border-radius: 8px;
            }}
            QComboBox {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                font-family: "{Fonts.UI}";
                font-size: {FontSizes.BODY}px;
                padding: {Spacing.SM}px {Spacing.MD}px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                min-width: 150px;
            }}
            QComboBox:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: {Spacing.SM}px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                selection-background-color: {Colors.SIGNAL_CYAN};
                selection-color: {Colors.BG_BASE};
            }}
            QPushButton {{
                font-family: "{Fonts.UI}";
                font-size: {FontSizes.BODY}px;
                padding: {Spacing.SM}px {Spacing.LG}px;
                border-radius: 4px;
                min-width: 80px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.LG)
        layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)

        # Category selector
        layout.addWidget(self._create_category_selector())

        # Format options (stacked for each category)
        self._format_stack = self._create_format_stack()
        layout.addWidget(self._format_stack)

        # Resolution dropdown (for charts only)
        self._resolution_container = self._create_resolution_selector()
        layout.addWidget(self._resolution_container)
        self._resolution_container.hide()

        # Progress bar (initially hidden)
        self._progress_bar = self._create_progress_bar()
        layout.addWidget(self._progress_bar)
        self._progress_bar.hide()

        # Spacer
        layout.addStretch()

        # Buttons
        layout.addWidget(self._create_buttons())

    def _create_category_selector(self) -> QWidget:
        """Create category selector widget."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.MD)

        label = QLabel("Category:")
        layout.addWidget(label)

        self._category_group = QButtonGroup(self)

        self._data_radio = QRadioButton("Data")
        self._data_radio.setChecked(True)
        self._category_group.addButton(self._data_radio, ExportCategory.DATA.value)
        layout.addWidget(self._data_radio)

        self._charts_radio = QRadioButton("Charts")
        self._category_group.addButton(self._charts_radio, ExportCategory.CHARTS.value)
        layout.addWidget(self._charts_radio)

        self._report_radio = QRadioButton("Report")
        self._report_radio.setEnabled(False)  # Deferred to future story
        self._report_radio.setStyleSheet(f"color: {Colors.TEXT_DISABLED};")
        self._category_group.addButton(self._report_radio, ExportCategory.REPORT.value)
        layout.addWidget(self._report_radio)

        layout.addStretch()
        return container

    def _create_format_stack(self) -> QStackedWidget:
        """Create stacked widget for format options."""
        stack = QStackedWidget()

        # Data formats page
        data_page = self._create_data_format_page()
        stack.addWidget(data_page)

        # Charts formats page
        charts_page = self._create_charts_format_page()
        stack.addWidget(charts_page)

        # Report page (placeholder)
        report_page = QWidget()
        stack.addWidget(report_page)

        return stack

    def _create_data_format_page(self) -> QWidget:
        """Create data format options page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, Spacing.MD, 0, 0)
        layout.setSpacing(Spacing.SM)

        label = QLabel("Format:")
        layout.addWidget(label)

        self._data_format_group = QButtonGroup(self)

        self._csv_radio = QRadioButton("CSV (with metadata header)")
        self._csv_radio.setChecked(True)
        self._data_format_group.addButton(self._csv_radio, 0)
        layout.addWidget(self._csv_radio)

        self._excel_radio = QRadioButton("Excel (.xlsx)")
        self._data_format_group.addButton(self._excel_radio, 1)
        layout.addWidget(self._excel_radio)

        self._parquet_radio = QRadioButton("Parquet (with embedded metadata)")
        self._data_format_group.addButton(self._parquet_radio, 2)
        layout.addWidget(self._parquet_radio)

        self._metrics_csv_radio = QRadioButton("Metrics CSV (comparison table)")
        self._data_format_group.addButton(self._metrics_csv_radio, 3)
        layout.addWidget(self._metrics_csv_radio)

        layout.addStretch()
        return page

    def _create_charts_format_page(self) -> QWidget:
        """Create charts format options page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, Spacing.MD, 0, 0)
        layout.setSpacing(Spacing.SM)

        label = QLabel("Format:")
        layout.addWidget(label)

        self._charts_format_group = QButtonGroup(self)

        self._png_radio = QRadioButton("Individual PNG")
        self._png_radio.setChecked(True)
        self._charts_format_group.addButton(self._png_radio, 0)
        layout.addWidget(self._png_radio)

        self._zip_radio = QRadioButton("All Charts ZIP")
        self._charts_format_group.addButton(self._zip_radio, 1)
        layout.addWidget(self._zip_radio)

        layout.addStretch()
        return page

    def _create_resolution_selector(self) -> QWidget:
        """Create resolution selector for chart exports."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.MD)

        label = QLabel("Resolution:")
        layout.addWidget(label)

        self._resolution_combo = NoScrollComboBox()
        self._resolution_combo.addItem(
            ExportResolution.HD_1080P.label, ExportResolution.HD_1080P
        )
        self._resolution_combo.addItem(
            ExportResolution.UHD_4K.label, ExportResolution.UHD_4K
        )
        layout.addWidget(self._resolution_combo)

        layout.addStretch()
        return container

    def _create_progress_bar(self) -> QProgressBar:
        """Create progress bar widget."""
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(False)
        progress_bar.setFixedHeight(4)
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {Colors.BG_SURFACE};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {Colors.SIGNAL_CYAN};
                border-radius: 2px;
            }}
        """)
        return progress_bar

    def _create_buttons(self) -> QWidget:
        """Create dialog buttons."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.MD)

        layout.addStretch()

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
            }}
            QPushButton:hover {{
                border-color: {Colors.TEXT_SECONDARY};
            }}
        """)
        layout.addWidget(self._cancel_btn)

        self._export_btn = QPushButton("Export")
        self._export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SIGNAL_CYAN};
                color: {Colors.BG_BASE};
                border: none;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #00E5BE;
            }}
            QPushButton:disabled {{
                background-color: {Colors.BG_BORDER};
                color: {Colors.TEXT_DISABLED};
            }}
        """)
        layout.addWidget(self._export_btn)

        return container

    def _connect_signals(self) -> None:
        """Connect widget signals."""
        self._category_group.idClicked.connect(self._on_category_changed)
        self._cancel_btn.clicked.connect(self.reject)
        self._export_btn.clicked.connect(self.accept)

    def _on_category_changed(self, category_id: int) -> None:
        """Handle category selection change.

        Args:
            category_id: Selected category enum value
        """
        if category_id == ExportCategory.DATA.value:
            self._selected_category = ExportCategory.DATA
            self._format_stack.setCurrentIndex(0)
            self._resolution_container.hide()
        elif category_id == ExportCategory.CHARTS.value:
            self._selected_category = ExportCategory.CHARTS
            self._format_stack.setCurrentIndex(1)
            self._resolution_container.show()
        else:
            self._selected_category = ExportCategory.REPORT
            self._format_stack.setCurrentIndex(2)
            self._resolution_container.hide()

    @property
    def selected_category(self) -> ExportCategory:
        """Get selected export category."""
        return self._selected_category


    def start_export(
        self,
        export_func: Any,
        export_args: dict[str, Any],
        output_path: Path,
        use_progress: bool = False,
    ) -> None:
        """Start an export operation in background thread.

        Args:
            export_func: The export function to call
            export_args: Arguments to pass to export function
            output_path: Output file path
            use_progress: If True, show determinate progress bar
        """
        self.show_progress(indeterminate=not use_progress)

        self._worker = ExportWorker(export_func, export_args, output_path)
        self._worker.progress.connect(self._on_export_progress)
        self._worker.finished.connect(self._on_export_finished)
        self._worker.error.connect(self._on_export_error)
        self._worker.start()

    def _on_export_progress(self, value: int) -> None:
        """Handle export progress update.

        Args:
            value: Progress value (0-100)
        """
        self.update_progress(value)

    def _on_export_finished(self, path: Path) -> None:
        """Handle successful export completion.

        Args:
            path: Path to exported file
        """
        from src.ui.components.toast import Toast

        self.hide_progress()
        Toast.display(self.parent(), "Export complete", "success")
        logger.info("Export completed: %s", path)
        self.accept()

    def _on_export_error(self, message: str) -> None:
        """Handle export error.

        Args:
            message: Error message
        """
        from src.ui.components.toast import Toast

        self.hide_progress()
        Toast.display(self.parent(), message, "error", duration=5000)
        logger.error("Export error: %s", message)
    @property
    def selected_format(self) -> ExportFormat:
        """Get selected export format."""
        if self._selected_category == ExportCategory.DATA:
            checked_id = self._data_format_group.checkedId()
            if checked_id == 0:
                return ExportFormat.CSV
            elif checked_id == 1:
                return ExportFormat.EXCEL
            elif checked_id == 2:
                return ExportFormat.PARQUET
            return ExportFormat.METRICS_CSV
        elif self._selected_category == ExportCategory.CHARTS:
            checked_id = self._charts_format_group.checkedId()
            if checked_id == 0:
                return ExportFormat.PNG
            return ExportFormat.ZIP
        return ExportFormat.CSV

    @property
    def selected_resolution(self) -> tuple[int, int]:
        """Get selected resolution as (width, height) tuple."""
        resolution = self._resolution_combo.currentData()
        if resolution:
            return resolution.value
        return ExportResolution.HD_1080P.value

    def set_category(self, category: ExportCategory) -> None:
        """Set the selected category.

        Args:
            category: Category to select
        """
        if category == ExportCategory.DATA:
            self._data_radio.setChecked(True)
        elif category == ExportCategory.CHARTS:
            self._charts_radio.setChecked(True)
        elif category == ExportCategory.REPORT:
            self._report_radio.setChecked(True)
        self._on_category_changed(category.value)

    def show_progress(self, indeterminate: bool = False) -> None:
        """Show progress bar and disable export button.

        Args:
            indeterminate: If True, show busy indicator (no percentage)
        """
        self._export_btn.setEnabled(False)
        self._progress_bar.show()
        if indeterminate:
            self._progress_bar.setMaximum(0)  # Indeterminate mode
        else:
            self._progress_bar.setMaximum(100)
            self._progress_bar.setValue(0)

    def update_progress(self, value: int) -> None:
        """Update progress bar value.

        Args:
            value: Progress value (0-100)
        """
        if self._progress_bar.maximum() > 0:
            self._progress_bar.setValue(value)

    def hide_progress(self) -> None:
        """Hide progress bar and re-enable export button."""
        self._progress_bar.hide()
        self._progress_bar.setValue(0)
        self._export_btn.setEnabled(True)
