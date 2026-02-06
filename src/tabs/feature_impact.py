"""Feature Impact tab for ranking features by predictive power.

Displays a scorecard table showing correlation, win rate lift, expectancy lift,
and composite impact score for each numeric feature in the dataset.
"""

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.app_state import AppState
from src.core.feature_impact_calculator import FeatureImpactCalculator, FeatureImpactResult
from src.ui.constants import Colors, Fonts, FontSizes, Spacing

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


class FeatureImpactTab(QWidget):
    """Tab displaying feature impact rankings."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        """Initialize the Feature Impact tab.

        Args:
            app_state: Application state for data access.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._app_state = app_state
        self._calculator = FeatureImpactCalculator()
        self._baseline_results: list[FeatureImpactResult] = []
        self._filtered_results: list[FeatureImpactResult] = []
        self._baseline_scores: dict[str, float] = {}
        self._filtered_scores: dict[str, float] = {}
        self._filtered_by_name: dict[str, FeatureImpactResult] = {}

        self._setup_ui()
        self._connect_signals()
        self._show_empty_state(True)

    def _setup_ui(self) -> None:
        """Set up the tab UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # Header section
        header = self._create_header()
        layout.addWidget(header)

        # Empty state label
        self._empty_label = QLabel("Load trade data to view feature impact analysis")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: 16px;
                padding: 40px;
            }}
        """)
        layout.addWidget(self._empty_label)

        # Main table
        self._table = self._create_table()
        layout.addWidget(self._table)

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
        title.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: {FontSizes.H2}px;
                font-weight: 600;
                letter-spacing: 1px;
            }}
        """)
        title_layout.addWidget(title)

        self._summary_label = QLabel("Analyzing features...")
        self._summary_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: {FontSizes.BODY}px;
            }}
        """)
        title_layout.addWidget(self._summary_label)

        layout.addWidget(title_section)
        layout.addStretch()

        return header

    def _create_table(self) -> QTableWidget:
        """Create the main scorecard table with baseline/filtered columns."""
        table = QTableWidget()
        table.setColumnCount(11)
        table.setHorizontalHeaderLabels([
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
        ])

        # Style the table
        table.setStyleSheet(f"""
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
        """)

        # Configure header
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 11):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        return table

    def _connect_signals(self) -> None:
        """Connect to app state signals."""
        self._app_state.baseline_calculated.connect(self._on_data_updated)
        self._app_state.filtered_data_updated.connect(self._on_data_updated)

    def _show_empty_state(self, show: bool) -> None:
        """Toggle between empty state and table."""
        self._empty_label.setVisible(show)
        self._table.setVisible(not show)

    def _on_data_updated(self) -> None:
        """Handle data updates from app state."""
        if not self._app_state.has_data:
            self._show_empty_state(True)
            return

        self._show_empty_state(False)
        self._analyze_features()

    def _analyze_features(self) -> None:
        """Analyze features for both baseline and filtered data."""
        baseline_df = self._app_state.baseline_df
        filtered_df = self._app_state.filtered_df

        if baseline_df is None or baseline_df.empty:
            return

        gain_col = "gain_pct"
        if self._app_state.column_mapping:
            gain_col = self._app_state.column_mapping.gain_pct

        # Calculate for baseline
        self._baseline_results = self._calculator.calculate_all_features(
            df=baseline_df,
            gain_col=gain_col,
        )
        self._baseline_scores = self._calculator.calculate_impact_scores(
            self._baseline_results
        )

        # Calculate for filtered (if different from baseline)
        if filtered_df is not None and not filtered_df.empty and len(filtered_df) != len(baseline_df):
            self._filtered_results = self._calculator.calculate_all_features(
                df=filtered_df,
                gain_col=gain_col,
            )
            self._filtered_scores = self._calculator.calculate_impact_scores(
                self._filtered_results
            )
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

        self._update_summary()
        self._populate_table()

    def _update_summary(self) -> None:
        """Update the summary label."""
        n_features = len(self._baseline_results)
        n_trades = self._baseline_results[0].trades_total if self._baseline_results else 0
        self._summary_label.setText(
            f"Analyzing {n_features} features across {n_trades:,} trades"
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
            self._set_gradient_item(row, 2, f"{b_result.correlation:+.3f}",
                                   b_result.correlation, *corr_range)
            self._set_gradient_item(row, 3, f"{f_result.correlation:+.3f}",
                                   f_result.correlation, *corr_range)

            # Col 4-5: WR Lift (B/F)
            self._set_gradient_item(row, 4, f"{b_result.win_rate_lift:+.1f}%",
                                   b_result.win_rate_lift, *wr_range)
            self._set_gradient_item(row, 5, f"{f_result.win_rate_lift:+.1f}%",
                                   f_result.win_rate_lift, *wr_range)

            # Col 6-7: EV Lift (B/F)
            self._set_gradient_item(row, 6, f"{b_result.expectancy_lift:+.4f}",
                                   b_result.expectancy_lift, *ev_range)
            self._set_gradient_item(row, 7, f"{f_result.expectancy_lift:+.4f}",
                                   f_result.expectancy_lift, *ev_range)

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
        self, row: int, col: int, text: str,
        value: float, min_val: float, max_val: float
    ) -> None:
        """Set a gradient-colored table item."""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        bg, text_color = get_gradient_color(value, min_val, max_val)
        item.setBackground(QBrush(bg))
        item.setForeground(QBrush(text_color))
        self._table.setItem(row, col, item)
