"""Feature Insights tab for ML-based feature analysis."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.ui.components.feature_impact_chart import FeatureImpactChart
from src.ui.components.range_analysis_table import RangeAnalysisTable

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
        self._selected_feature = None
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
        self._run_button.setToolTip(
            "Analyze features to identify which have the most impact on trading performance"
        )
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
        config_label.setToolTip(
            "Select columns that should not be analyzed to prevent lookahead bias. "
            "Common exclusions include gain_pct, mae_pct, mfe_pct, and exit prices."
        )
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

        # Results container with splitter
        self._results_widget = QWidget()
        results_layout = QVBoxLayout(self._results_widget)
        results_layout.setContentsMargins(0, 0, 0, 0)

        # Impact chart at top
        self._impact_chart = FeatureImpactChart()
        self._impact_chart.setMinimumHeight(250)
        results_layout.addWidget(self._impact_chart)

        # Splitter for feature list and details
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Feature list
        feature_list_frame = QFrame()
        fl_layout = QVBoxLayout(feature_list_frame)
        fl_layout.setContentsMargins(0, 0, 0, 0)
        fl_label = QLabel("Features (by Impact)")
        fl_label.setStyleSheet("font-weight: bold;")
        fl_layout.addWidget(fl_label)

        self._feature_list = QListWidget()
        self._feature_list.currentItemChanged.connect(self._on_feature_selected)
        fl_layout.addWidget(self._feature_list)
        splitter.addWidget(feature_list_frame)

        # Right: Details panel
        details_frame = QFrame()
        details_layout = QVBoxLayout(details_frame)
        details_layout.setContentsMargins(0, 0, 0, 0)

        # Validation metrics group
        self._validation_group = QGroupBox("Validation Metrics")
        validation_layout = QVBoxLayout(self._validation_group)
        self._stability_label = QLabel("Bootstrap Stability: --")
        self._stability_label.setToolTip(
            "How stable the impact score is across bootstrap resampling (higher is better)"
        )
        self._consistency_label = QLabel("Time Consistency: --")
        self._consistency_label.setToolTip(
            "How consistent the feature's impact is across different time periods "
            "(higher is better)"
        )
        self._warnings_label = QLabel("Warnings: None")
        self._warnings_label.setWordWrap(True)
        validation_layout.addWidget(self._stability_label)
        validation_layout.addWidget(self._consistency_label)
        validation_layout.addWidget(self._warnings_label)
        details_layout.addWidget(self._validation_group)

        # Range table
        self._range_table = RangeAnalysisTable()
        details_layout.addWidget(self._range_table)

        # Apply filter button
        self._apply_filter_btn = QPushButton("Apply Favorable Ranges as Filter")
        self._apply_filter_btn.setEnabled(False)
        self._apply_filter_btn.setToolTip(
            "Create filters based on the favorable ranges of the selected feature"
        )
        self._apply_filter_btn.clicked.connect(self._on_apply_filter)
        details_layout.addWidget(self._apply_filter_btn)

        splitter.addWidget(details_frame)

        splitter.setSizes([250, 500])
        results_layout.addWidget(splitter)

        self._content_area.setWidget(self._placeholder)  # Start with placeholder

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
        logger.info("Analysis complete with %d features", len(results.features))

        # Update impact chart
        self._impact_chart.update_data(results)

        # Populate feature list
        self._feature_list.clear()
        for feature in results.features:
            item = QListWidgetItem(f"{feature.feature_name} ({feature.impact_score:.1f})")
            item.setData(Qt.ItemDataRole.UserRole, feature.feature_name)
            self._feature_list.addItem(item)

        # Select first feature by default
        if results.features:
            self._feature_list.setCurrentRow(0)

        self._content_area.setWidget(self._results_widget)

    @pyqtSlot(QListWidgetItem, QListWidgetItem)
    def _on_feature_selected(
        self, current: QListWidgetItem | None, previous: QListWidgetItem | None
    ) -> None:
        """Handle feature selection change."""
        if current is None or self._results is None:
            return

        feature_name = current.data(Qt.ItemDataRole.UserRole)

        # Find the feature in results
        for feature in self._results.features:
            if feature.feature_name == feature_name:
                self._selected_feature = feature
                self._update_feature_details(feature)
                break

    def _update_feature_details(self, feature) -> None:
        """Update the details panel with selected feature info."""
        # Update validation metrics
        self._stability_label.setText(
            f"Bootstrap Stability: {feature.bootstrap_stability:.1%}"
        )

        if feature.time_consistency is not None:
            self._consistency_label.setText(
                f"Time Consistency: {feature.time_consistency:.1%}"
            )
        else:
            self._consistency_label.setText("Time Consistency: N/A (no date column)")

        if feature.warnings:
            warnings_text = "\n".join(f"• {w}" for w in feature.warnings)
            self._warnings_label.setText(f"Warnings:\n{warnings_text}")
            self._warnings_label.setStyleSheet("color: #ffaa00;")
        else:
            self._warnings_label.setText("Warnings: None")
            self._warnings_label.setStyleSheet("color: #888;")

        # Update range table
        self._range_table.update_data(feature)

        # Enable apply filter button if there are favorable ranges
        from src.core.feature_analyzer import RangeClassification

        has_favorable = any(
            r.classification == RangeClassification.FAVORABLE for r in feature.ranges
        )
        self._apply_filter_btn.setEnabled(has_favorable)

    @pyqtSlot()
    def _on_apply_filter(self) -> None:
        """Create filter from favorable ranges of selected feature."""
        if self._selected_feature is None:
            return

        from src.core.feature_analyzer import RangeClassification
        from src.core.models import FilterCriteria

        # Get favorable ranges
        favorable_ranges = [
            r
            for r in self._selected_feature.ranges
            if r.classification == RangeClassification.FAVORABLE
        ]

        if not favorable_ranges:
            logger.warning("No favorable ranges to apply as filter")
            return

        # Create filter criteria for each favorable range
        for range_result in favorable_ranges:
            criteria = FilterCriteria(
                column=self._selected_feature.feature_name,
                operator="between",
                value=(range_result.range_min, range_result.range_max),
            )
            # Add to app state filters
            self.app_state.filters.append(criteria)

        logger.info("Applied %d favorable ranges as filters", len(favorable_ranges))
        self.app_state.filters_changed.emit(self.app_state.filters)

    def _populate_column_checkboxes(self, df) -> None:
        """Populate column exclusion checkboxes."""
        import pandas as pd

        # Clear existing
        while self._column_layout.count():
            child = self._column_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self._column_checkboxes = {}

        # Load saved exclusions, falling back to defaults
        saved_exclusions = self._load_excluded_columns()
        default_exclude = {"gain_pct", "mae_pct", "mfe_pct", "close", "exit_price"}
        exclusions = saved_exclusions if saved_exclusions else default_exclude

        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                cb = QCheckBox(col)
                cb.setChecked(col in exclusions)
                cb.stateChanged.connect(self._on_exclusion_changed)  # Save on change
                self._column_checkboxes[col] = cb
                self._column_layout.addWidget(cb)

        self._column_layout.addStretch()

    def _save_excluded_columns(self) -> None:
        """Save current exclusion settings."""
        from PyQt6.QtCore import QSettings

        settings = QSettings("Lumen", "FeatureInsights")
        excluded = [col for col, cb in self._column_checkboxes.items() if cb.isChecked()]
        settings.setValue("excluded_columns", excluded)

    def _load_excluded_columns(self) -> set[str]:
        """Load saved exclusion settings."""
        from PyQt6.QtCore import QSettings

        settings = QSettings("Lumen", "FeatureInsights")
        return set(settings.value("excluded_columns", []))

    @pyqtSlot(int)
    def _on_exclusion_changed(self, state: int) -> None:
        """Handle checkbox state change - save settings."""
        self._save_excluded_columns()
