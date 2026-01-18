"""Feature Insights tab for ML-based feature analysis."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
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

    @pyqtSlot(object)
    def _on_data_updated(self, df) -> None:
        """Handle filtered data update."""
        self._run_button.setEnabled(df is not None and len(df) > 0)

    @pyqtSlot()
    def _on_run_clicked(self) -> None:
        """Handle run analysis button click."""
        logger.info("Feature analysis requested")
        # TODO: Implement analysis execution
        pass
