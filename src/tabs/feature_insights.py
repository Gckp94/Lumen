"""Feature Insights tab for ML-based feature analysis."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from src.core.app_state import AppState

logger = logging.getLogger(__name__)


class AnalysisWorker(QThread):
    """Worker thread for running feature analysis."""

    finished = pyqtSignal(object)  # FeatureAnalyzerResults
    error = pyqtSignal(str)

    def __init__(
        self,
        df,
        gain_col: str,
        exclude_columns: set[str],
        date_col: str | None = None,
    ):
        super().__init__()
        self.df = df
        self.gain_col = gain_col
        self.exclude_columns = exclude_columns
        self.date_col = date_col

    def run(self):
        try:
            from src.core.feature_analyzer import FeatureAnalyzer, FeatureAnalyzerConfig

            config = FeatureAnalyzerConfig(
                exclude_columns=self.exclude_columns,
                bootstrap_iterations=500,  # Balanced speed/accuracy
            )

            analyzer = FeatureAnalyzer(config)
            results = analyzer.run(self.df, self.gain_col, self.date_col)

            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class FeatureInsightsTab(QWidget):
    """Tab for analyzing feature impact on trading performance."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None):
        """Initialize the Feature Insights tab.

        Args:
            app_state: Application state for data access.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.app_state = app_state
        self._results = None
        self._column_checkboxes = {}
        self._worker = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header with title and run button
        header = QHBoxLayout()

        title = QLabel("Feature Insights")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(title)

        header.addStretch()

        self._run_button = QPushButton("Run Analysis")
        self._run_button.setEnabled(False)
        self._run_button.clicked.connect(self._on_run_clicked)
        header.addWidget(self._run_button)

        layout.addLayout(header)

        # Configuration section
        config_frame = QFrame()
        config_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        config_layout = QVBoxLayout(config_frame)

        config_label = QLabel("Exclude Columns (lookahead bias prevention):")
        config_label.setStyleSheet("font-weight: bold;")
        config_layout.addWidget(config_label)

        # Scrollable checkbox area for columns
        self._column_scroll = QScrollArea()
        self._column_scroll.setWidgetResizable(True)
        self._column_scroll.setMaximumHeight(150)
        self._column_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._column_container = QWidget()
        self._column_layout = QHBoxLayout(self._column_container)
        self._column_layout.setContentsMargins(0, 0, 0, 0)

        self._column_scroll.setWidget(self._column_container)
        config_layout.addWidget(self._column_scroll)

        layout.addWidget(config_frame)

        # Placeholder content
        self._content_area = QScrollArea()
        self._content_area.setWidgetResizable(True)
        self._content_area.setFrameShape(QFrame.Shape.NoFrame)

        self._placeholder = QLabel(
            "Load data and click 'Run Analysis' to identify impactful features."
        )
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #888; font-size: 14px;")
        self._content_area.setWidget(self._placeholder)

        layout.addWidget(self._content_area, 1)

    def _connect_signals(self) -> None:
        """Connect to app state signals."""
        self.app_state.data_loaded.connect(self._on_data_loaded)
        self.app_state.filtered_data_updated.connect(self._on_data_updated)

    @pyqtSlot(object)
    def _on_data_loaded(self, df) -> None:
        """Handle data loaded event."""
        self._run_button.setEnabled(df is not None and len(df) > 0)
        if df is not None and len(df) > 0:
            self._populate_column_checkboxes(df)

    @pyqtSlot(object)
    def _on_data_updated(self, df) -> None:
        """Handle filtered data update."""
        self._run_button.setEnabled(df is not None and len(df) > 0)

    @pyqtSlot()
    def _on_run_clicked(self) -> None:
        """Handle run analysis button click."""
        if self.app_state.filtered_df is None:
            return

        # Get excluded columns
        exclude = {
            col for col, cb in self._column_checkboxes.items() if cb.isChecked()
        }

        # Get column names from mapping
        mapping = self.app_state.column_mapping
        if mapping is None:
            return

        self._run_button.setEnabled(False)
        self._run_button.setText("Analyzing...")

        # Start worker
        self._worker = AnalysisWorker(
            df=self.app_state.filtered_df.copy(),
            gain_col=mapping.gain_pct,
            exclude_columns=exclude,
            date_col=mapping.date,
        )
        self._worker.finished.connect(self._on_analysis_complete)
        self._worker.error.connect(self._on_analysis_error)
        self._worker.start()

    @pyqtSlot(object)
    def _on_analysis_complete(self, results) -> None:
        """Handle analysis completion."""
        self._results = results
        self._run_button.setEnabled(True)
        self._run_button.setText("Run Analysis")
        self._display_results(results)

    @pyqtSlot(str)
    def _on_analysis_error(self, error: str) -> None:
        """Handle analysis error."""
        logger.error("Feature analysis failed: %s", error)
        self._run_button.setEnabled(True)
        self._run_button.setText("Run Analysis")

    def _display_results(self, results) -> None:
        """Display analysis results."""
        # TODO: Will be implemented in Task 13
        logger.info("Analysis complete with %d features", len(results.features))

    def _populate_column_checkboxes(self, df) -> None:
        """Populate column exclusion checkboxes."""
        import pandas as pd

        # Clear existing
        while self._column_layout.count():
            child = self._column_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self._column_checkboxes = {}

        # Default exclusions
        default_exclude = {"gain_pct", "mae_pct", "mfe_pct", "close", "exit_price"}

        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                cb = QCheckBox(col)
                cb.setChecked(col in default_exclude)
                self._column_checkboxes[col] = cb
                self._column_layout.addWidget(cb)

        self._column_layout.addStretch()
