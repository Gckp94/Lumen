"""Feature Impact tab for ranking features by predictive power.

Displays a scorecard table showing correlation, win rate lift, expectancy lift,
and composite impact score for each numeric feature in the dataset.
"""

import logging

import numpy as np
import pandas as pd
import pyqtgraph as pg

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.app_state import AppState
from src.core.feature_exclusion_manager import FeatureExclusionManager
from src.core.feature_impact_calculator import FeatureImpactCalculator, FeatureImpactResult
from src.ui.components.resizable_exclude_panel import ResizableExcludePanel
from src.ui.constants import Colors, Fonts, FontSizes, Spacing
from src.ui.mixins.background_calculation import BackgroundCalculationMixin

logger = logging.getLogger(__name__)

# Gradient colors (matching statistics_tab.py pattern)
GRADIENT_CORAL = QColor(Colors.SIGNAL_CORAL)  # Negative
GRADIENT_NEUTRAL = QColor(Colors.BG_ELEVATED)  # Zero
GRADIENT_CYAN = QColor(Colors.SIGNAL_CYAN)  # Positive
TEXT_ON_DARK = QColor(Colors.TEXT_PRIMARY)
TEXT_ON_LIGHT = QColor(Colors.BG_BASE)


def lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
    """Linear interpolation between two colors."""
    t = max(0.0, min(1.0, t))
    return QColor(
        int(c1.red() + (c2.red() - c1.red()) * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue() + (c2.blue() - c1.blue()) * t),
    )


def get_gradient_color(
    value: float,
    min_val: float,
    max_val: float,
) -> tuple[QColor, QColor]:
    """Get background and text colors for a value in range.

    Args:
        value: The value to color.
        min_val: Minimum value in range (maps to coral).
        max_val: Maximum value in range (maps to cyan).

    Returns:
        Tuple of (background_color, text_color).
    """
    if min_val == max_val:
        return (GRADIENT_NEUTRAL, TEXT_ON_DARK)

    # Normalize to -1 to +1 range where 0 is neutral
    if min_val < 0 and max_val > 0:
        # Range spans zero - normalize around zero
        if value < 0:
            t = value / min_val  # 0 to 1 for negative values
            bg = lerp_color(GRADIENT_NEUTRAL, GRADIENT_CORAL, t)
        else:
            t = value / max_val  # 0 to 1 for positive values
            bg = lerp_color(GRADIENT_NEUTRAL, GRADIENT_CYAN, t)
    else:
        # Range doesn't span zero - use full range
        normalized = (value - min_val) / (max_val - min_val)
        bg = lerp_color(GRADIENT_CORAL, GRADIENT_CYAN, normalized)

    # Text color based on background brightness
    brightness = (bg.red() * 299 + bg.green() * 587 + bg.blue() * 114) / 1000
    text = TEXT_ON_DARK if brightness < 128 else TEXT_ON_LIGHT

    return (bg, text)


class FeatureDetailWidget(QWidget):
    """Expandable detail widget showing threshold analysis."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        layout.setSpacing(Spacing.SM)

        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: 4px;
            }}
        """
        )

        # Threshold label
        self._threshold_label = QLabel()
        self._threshold_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: {FontSizes.BODY}px;
                font-weight: 600;
            }}
        """
        )
        layout.addWidget(self._threshold_label)

        # Spark chart
        self._chart = pg.PlotWidget()
        self._chart.setBackground(Colors.BG_ELEVATED)
        self._chart.setMinimumHeight(80)
        self._chart.setMaximumHeight(100)
        self._chart.hideAxis("left")
        self._chart.hideAxis("bottom")
        self._chart.setMouseEnabled(False, False)
        layout.addWidget(self._chart)

        # Comparison stats
        stats_row = QHBoxLayout()

        self._below_stats = self._create_stats_card("BELOW THRESHOLD")
        self._above_stats = self._create_stats_card("ABOVE THRESHOLD")

        stats_row.addWidget(self._below_stats)
        stats_row.addWidget(self._above_stats)
        layout.addLayout(stats_row)

    def _create_stats_card(self, title: str) -> QWidget:
        """Create a stats comparison card."""
        card = QWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: 10px;
                letter-spacing: 1px;
            }}
        """
        )
        layout.addWidget(title_label)

        # Stats labels will be added dynamically
        card._stats_layout = layout
        card._stat_labels = {}

        return card

    def set_data(self, result: FeatureImpactResult) -> None:
        """Populate the detail widget with result data."""
        # Threshold label
        direction = ">" if result.threshold_direction == "above" else "<"
        self._threshold_label.setText(
            f"Threshold: {result.feature_name} {direction} {result.optimal_threshold:.2f}"
        )

        # Spark chart - win rate by percentile
        self._chart.clear()
        x = list(range(len(result.percentile_win_rates)))
        y = result.percentile_win_rates

        # Bar chart
        bar = pg.BarGraphItem(
            x=x,
            height=y,
            width=0.8,
            brush=Colors.SIGNAL_CYAN,
            pen=pg.mkPen(None),
        )
        self._chart.addItem(bar)

        # Threshold line (approximate position)
        thresh_pct = 50  # Would need to calculate actual percentile
        line = pg.InfiniteLine(
            pos=thresh_pct / 5,  # Scale to bar count
            angle=90,
            pen=pg.mkPen(Colors.SIGNAL_AMBER, width=2),
        )
        self._chart.addItem(line)

        # Update stats cards
        self._update_stats_card(
            self._below_stats,
            {
                "Trades": f"{result.trades_below:,}",
                "Win Rate": f"{result.win_rate_below:.1f}%",
                "Expectancy": f"{result.expectancy_below:.4f}",
            },
        )

        lift_wr = result.win_rate_above - result.win_rate_baseline
        lift_ev = result.expectancy_above - result.expectancy_baseline
        self._update_stats_card(
            self._above_stats,
            {
                "Trades": f"{result.trades_above:,}",
                "Win Rate": f"{result.win_rate_above:.1f}% ({lift_wr:+.1f}%)",
                "Expectancy": f"{result.expectancy_above:.4f} ({lift_ev:+.4f})",
            },
            highlight=result.threshold_direction == "above",
        )

    def _update_stats_card(
        self, card: QWidget, stats: dict[str, str], highlight: bool = False
    ) -> None:
        """Update stats card labels."""
        # Clear existing stat labels
        for label in card._stat_labels.values():
            label.deleteLater()
        card._stat_labels.clear()

        color = Colors.SIGNAL_CYAN if highlight else Colors.TEXT_PRIMARY

        for key, value in stats.items():
            label = QLabel(f"{key}: {value}")
            label.setStyleSheet(
                f"""
                QLabel {{
                    color: {color};
                    font-family: '{Fonts.DATA}';
                    font-size: 12px;
                }}
            """
            )
            card._stats_layout.addWidget(label)
            card._stat_labels[key] = label


class FeatureImpactTab(BackgroundCalculationMixin, QWidget):
    """Tab displaying feature impact rankings."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        """Initialize the Feature Impact tab.

        Args:
            app_state: Application state for data access.
            parent: Parent widget.
        """
        QWidget.__init__(self, parent)
        BackgroundCalculationMixin.__init__(self, app_state, "Feature Impact")
        self._calculator = FeatureImpactCalculator()
        self._baseline_results: list[FeatureImpactResult] = []
        self._filtered_results: list[FeatureImpactResult] = []
        self._baseline_scores: dict[str, float] = {}
        self._filtered_scores: dict[str, float] = {}
        self._filtered_by_name: dict[str, FeatureImpactResult] = {}

        self._sort_column = 1  # Default sort by Impact Score
        self._sort_ascending = False

        self._user_excluded_cols: set[str] = set()
        self._exclusion_manager = FeatureExclusionManager()

        self._expanded_row: int | None = None

        self._setup_ui()
        self._setup_background_calculation()
        self._connect_signals()
        self._show_empty_state(True)

    def _setup_ui(self) -> None:
        """Set up the tab UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # Header row
        header = self._create_header()
        layout.addWidget(header)

        # Empty state label
        self._empty_label = QLabel("Load trade data to view feature impact analysis")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: 16px;
                padding: 40px;
            }}
        """
        )
        layout.addWidget(self._empty_label)

        # Detail widget (hidden by default)
        self._detail_widget = FeatureDetailWidget()
        self._detail_widget.setVisible(False)
        layout.addWidget(self._detail_widget)

        # Splitter with exclude panel and table
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet(
            f"""
            QSplitter::handle {{
                background-color: {Colors.BG_BORDER};
            }}
            QSplitter::handle:hover {{
                background-color: {Colors.SIGNAL_CYAN};
            }}
        """
        )

        # Exclude panel (left)
        self._exclude_panel = ResizableExcludePanel()
        self._exclude_panel.exclusion_changed.connect(self._on_exclusion_changed)
        splitter.addWidget(self._exclude_panel)

        # Table (right)
        self._table = self._create_table()
        splitter.addWidget(self._table)

        splitter.setSizes([280, 800])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)

    def _create_header(self) -> QWidget:
        """Create the header section with title and summary."""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title and summary on left
        title_section = QWidget()
        title_layout = QVBoxLayout(title_section)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(Spacing.XS)

        title = QLabel("FEATURE IMPACT")
        title.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: {FontSizes.H2}px;
                font-weight: 600;
                letter-spacing: 1px;
            }}
        """
        )
        title_layout.addWidget(title)

        self._summary_label = QLabel("Analyzing features...")
        self._summary_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: {FontSizes.BODY}px;
            }}
        """
        )
        title_layout.addWidget(self._summary_label)

        layout.addWidget(title_section)
        layout.addStretch()

        return header

    def _create_table(self) -> QTableWidget:
        """Create the main scorecard table with baseline/filtered columns."""
        table = QTableWidget()
        table.setColumnCount(11)
        table.setHorizontalHeaderLabels(
            [
                "Feature",
                "Impact",
                "Corr (B)",
                "Corr (F)",
                "WR Lift (B)",
                "WR Lift (F)",
                "EV Lift (B)",
                "EV Lift (F)",
                "Threshold",
                "Trades (B)",
                "Trades (F)",
            ]
        )

        # Style the table
        table.setStyleSheet(
            f"""
            QTableWidget {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                gridline-color: {Colors.BG_BORDER};
            }}
            QTableWidget::item {{
                padding: {Spacing.SM}px;
                font-family: '{Fonts.DATA}';
                font-size: {FontSizes.BODY}px;
            }}
            QHeaderView::section {{
                background-color: {Colors.BG_BASE};
                color: {Colors.TEXT_SECONDARY};
                padding: {Spacing.SM}px {Spacing.MD}px;
                border: none;
                border-bottom: 1px solid {Colors.BG_BORDER};
                border-right: 1px solid {Colors.BG_BORDER};
                font-family: '{Fonts.UI}';
                font-size: 12px;
                font-weight: 500;
                text-transform: uppercase;
            }}
        """
        )

        # Configure header
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 11):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        # Enable sorting via header clicks
        header.setSortIndicatorShown(True)
        header.sectionClicked.connect(self._on_header_clicked)

        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Connect row click
        table.cellClicked.connect(self._on_row_clicked)

        return table

    def _on_exclusion_changed(self, column: str, is_excluded: bool) -> None:
        """Handle column exclusion change from panel.

        Args:
            column: The column name that changed.
            is_excluded: True if the column is now excluded, False otherwise.
        """
        if is_excluded:
            self._user_excluded_cols.add(column)
        else:
            self._user_excluded_cols.discard(column)

        # Persist exclusions for this source file
        if self._app_state.source_file_path:
            self._exclusion_manager.save(
                self._app_state.source_file_path,
                self._user_excluded_cols,
            )

        # Re-analyze with updated exclusions
        self._analyze_features()

    def _connect_signals(self) -> None:
        """Connect to app state signals."""
        self._app_state.data_loaded.connect(self._on_data_loaded)
        self._app_state.baseline_calculated.connect(self._on_data_updated)
        self._app_state.filtered_data_updated.connect(self._on_data_updated)
        self._app_state.first_trigger_toggled.connect(self._on_data_updated)

        # Connect to tab visibility for stale refresh
        self._app_state.tab_became_visible.connect(self._on_tab_became_visible)

    def _on_data_loaded(self) -> None:
        """Handle new data being loaded - restore saved exclusions."""
        if not self._app_state.source_file_path:
            return

        # Load saved exclusions for this file
        saved_exclusions = self._exclusion_manager.load(
            self._app_state.source_file_path
        )
        self._user_excluded_cols = saved_exclusions

        # Update the exclude panel UI to reflect loaded exclusions
        if hasattr(self, "_exclude_panel"):
            self._exclude_panel.set_excluded(saved_exclusions)

    def _show_empty_state(self, show: bool) -> None:
        """Toggle between empty state and table."""
        self._empty_label.setVisible(show)
        self._table.setVisible(not show)

    def _on_data_updated(self) -> None:
        """Handle data updates from app state."""
        # Check visibility first
        if self._dock_widget is not None:
            if not self._app_state.visibility_tracker.is_visible(self._dock_widget):
                self._app_state.visibility_tracker.mark_stale(self._tab_name)
                return

        if not self._app_state.has_data:
            self._show_empty_state(True)
            return

        self._show_empty_state(False)
        self._analyze_features()

    def _on_tab_became_visible(self, tab_name: str) -> None:
        """Handle tab becoming visible after being marked stale.

        Args:
            tab_name: Name of the tab that became visible.
        """
        if tab_name == self._tab_name:
            # Rerun data update logic which will analyze if data exists
            self._on_data_updated()

    def _analyze_features(self) -> None:
        """Analyze features for both baseline and filtered data."""
        baseline_df = self._app_state.baseline_df
        filtered_df = self._app_state.filtered_df

        if baseline_df is None or baseline_df.empty:
            return

        gain_col = "gain_pct"
        if self._app_state.column_mapping:
            gain_col = self._app_state.column_mapping.gain_pct

        # Apply First Trigger Only filtering to baseline data if enabled
        # Note: filtered_df already has first trigger filtering applied by Feature Explorer,
        # so we don't apply it again to avoid double filtering
        if self._app_state.first_trigger_enabled and "trigger_number" in baseline_df.columns:
            baseline_df = baseline_df[baseline_df["trigger_number"] == 1].copy()

        # Build full exclusion list
        excluded = list(self._user_excluded_cols)

        # Calculate for baseline
        self._baseline_results = self._calculator.calculate_all_features(
            df=baseline_df,
            gain_col=gain_col,
            excluded_cols=excluded,
        )
        self._baseline_scores = self._calculator.calculate_impact_scores(self._baseline_results)

        # Calculate for filtered - always recalculate if filtered_df exists
        # Use 'is not' to check if it's a different DataFrame object
        if filtered_df is not None and not filtered_df.empty and filtered_df is not baseline_df:
            self._filtered_results = self._calculator.calculate_all_features(
                df=filtered_df,
                gain_col=gain_col,
                excluded_cols=excluded,
            )
            self._filtered_scores = self._calculator.calculate_impact_scores(self._filtered_results)
        else:
            self._filtered_results = self._baseline_results
            self._filtered_scores = self._baseline_scores

        # Create lookup dict for filtered results
        self._filtered_by_name = {r.feature_name: r for r in self._filtered_results}

        # Sort by baseline impact score
        self._baseline_results.sort(
            key=lambda r: self._baseline_scores.get(r.feature_name, 0),
            reverse=True,
        )

        # Update exclude panel with available columns
        numeric_cols = baseline_df.select_dtypes(include=[np.number]).columns.tolist()
        analyzable = [c for c in numeric_cols if c != gain_col]
        if hasattr(self, "_exclude_panel"):
            self._exclude_panel.set_columns(analyzable)

        self._update_summary(baseline_df, filtered_df)
        self._populate_table()

    def _update_summary(self, baseline_df: pd.DataFrame, filtered_df: pd.DataFrame | None) -> None:
        """Update the summary label with actual trade counts."""
        n_features = len(self._baseline_results)
        n_baseline = len(baseline_df)

        # Indicate first trigger mode
        ft_suffix = " (1st trigger)" if self._app_state.first_trigger_enabled else ""

        if filtered_df is not None and filtered_df is not baseline_df:
            n_filtered = len(filtered_df)
            self._summary_label.setText(
                f"Analyzing {n_features} features{ft_suffix} | Baseline: {n_baseline:,} | Filtered: {n_filtered:,}"
            )
        else:
            self._summary_label.setText(
                f"Analyzing {n_features} features across {n_baseline:,} trades{ft_suffix}"
            )

    def _populate_table(self) -> None:
        """Populate table with baseline and filtered results."""
        self._table.setRowCount(len(self._baseline_results))

        # Calculate ranges for gradients (using baseline)
        b_corrs = [r.correlation for r in self._baseline_results]
        b_wr = [r.win_rate_lift for r in self._baseline_results]
        b_ev = [r.expectancy_lift for r in self._baseline_results]

        f_corrs = [r.correlation for r in self._filtered_results]
        f_wr = [r.win_rate_lift for r in self._filtered_results]
        f_ev = [r.expectancy_lift for r in self._filtered_results]

        corr_range = (min(b_corrs + f_corrs), max(b_corrs + f_corrs)) if b_corrs else (0, 0)
        wr_range = (min(b_wr + f_wr), max(b_wr + f_wr)) if b_wr else (0, 0)
        ev_range = (min(b_ev + f_ev), max(b_ev + f_ev)) if b_ev else (0, 0)

        for row, b_result in enumerate(self._baseline_results):
            f_result = self._filtered_by_name.get(b_result.feature_name, b_result)
            b_score = self._baseline_scores.get(b_result.feature_name, 0)

            # Col 0: Feature name
            self._set_text_item(row, 0, b_result.feature_name)

            # Col 1: Impact score (baseline)
            self._set_gradient_item(row, 1, f"{b_score:.2f}", b_score, 0, 1)

            # Col 2-3: Correlation (B/F)
            self._set_gradient_item(
                row, 2, f"{b_result.correlation:+.3f}", b_result.correlation, *corr_range
            )
            self._set_gradient_item(
                row, 3, f"{f_result.correlation:+.3f}", f_result.correlation, *corr_range
            )

            # Col 4-5: WR Lift (B/F)
            self._set_gradient_item(
                row, 4, f"{b_result.win_rate_lift:+.1f}%", b_result.win_rate_lift, *wr_range
            )
            self._set_gradient_item(
                row, 5, f"{f_result.win_rate_lift:+.1f}%", f_result.win_rate_lift, *wr_range
            )

            # Col 6-7: EV Lift (B/F)
            self._set_gradient_item(
                row, 6, f"{b_result.expectancy_lift:+.4f}", b_result.expectancy_lift, *ev_range
            )
            self._set_gradient_item(
                row, 7, f"{f_result.expectancy_lift:+.4f}", f_result.expectancy_lift, *ev_range
            )

            # Col 8: Threshold
            direction = ">" if b_result.threshold_direction == "above" else "<"
            self._set_text_item(row, 8, f"{direction} {b_result.optimal_threshold:.2f}")

            # Col 9-10: Trades (B/F)
            self._set_text_item(row, 9, f"{b_result.trades_total:,}")
            self._set_text_item(row, 10, f"{f_result.trades_total:,}")

    def _set_text_item(self, row: int, col: int, text: str) -> None:
        """Set a plain text table item."""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setForeground(QBrush(QColor(Colors.TEXT_PRIMARY)))
        self._table.setItem(row, col, item)

    def _set_gradient_item(
        self, row: int, col: int, text: str, value: float, min_val: float, max_val: float
    ) -> None:
        """Set a gradient-colored table item."""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        bg, text_color = get_gradient_color(value, min_val, max_val)
        item.setBackground(QBrush(bg))
        item.setForeground(QBrush(text_color))
        self._table.setItem(row, col, item)

    def _on_header_clicked(self, col: int) -> None:
        """Handle column header click for sorting."""
        if col == self._sort_column:
            self._sort_ascending = not self._sort_ascending
        else:
            self._sort_column = col
            self._sort_ascending = False  # Default descending for new column

        self._sort_and_repopulate()

    def _sort_and_repopulate(self) -> None:
        """Sort results and repopulate table."""
        if not self._baseline_results:
            return

        # Define sort key based on column
        def get_sort_key(result: FeatureImpactResult) -> float:
            f_result = self._filtered_by_name.get(result.feature_name, result)
            col = self._sort_column

            if col == 0:  # Feature name (alphabetical)
                return result.feature_name.lower()
            elif col == 1:  # Impact score
                return self._baseline_scores.get(result.feature_name, 0)
            elif col == 2:  # Corr (B)
                return result.correlation
            elif col == 3:  # Corr (F)
                return f_result.correlation
            elif col == 4:  # WR Lift (B)
                return result.win_rate_lift
            elif col == 5:  # WR Lift (F)
                return f_result.win_rate_lift
            elif col == 6:  # EV Lift (B)
                return result.expectancy_lift
            elif col == 7:  # EV Lift (F)
                return f_result.expectancy_lift
            elif col == 9:  # Trades (B)
                return result.trades_total
            elif col == 10:  # Trades (F)
                return f_result.trades_total
            else:
                return 0

        # Handle alphabetical vs numeric sorting
        if self._sort_column == 0:
            self._baseline_results.sort(
                key=lambda r: r.feature_name.lower(),
                reverse=not self._sort_ascending,
            )
        else:
            self._baseline_results.sort(
                key=get_sort_key,
                reverse=not self._sort_ascending,
            )

        # Update sort indicator
        order = (
            Qt.SortOrder.AscendingOrder if self._sort_ascending else Qt.SortOrder.DescendingOrder
        )
        self._table.horizontalHeader().setSortIndicator(self._sort_column, order)

        self._populate_table()

    def _on_row_clicked(self, row: int, col: int) -> None:
        """Handle row click to expand/collapse detail."""
        if self._expanded_row == row:
            # Collapse
            self._detail_widget.setVisible(False)
            self._expanded_row = None
        else:
            # Expand
            if row < len(self._baseline_results):
                result = self._baseline_results[row]
                self._detail_widget.set_data(result)
                self._detail_widget.setVisible(True)
                self._expanded_row = row
