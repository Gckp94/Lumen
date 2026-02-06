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
        self._results: list[FeatureImpactResult] = []
        self._impact_scores: dict[str, float] = {}

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
        """Create the main scorecard table."""
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels([
            "Feature",
            "Impact Score",
            "Correlation",
            "WR Lift",
            "EV Lift",
            "Threshold",
            "Trades",
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
        for i in range(1, 7):
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
        """Analyze all features and populate table."""
        df = self._app_state.baseline_df
        if df is None or df.empty:
            return

        # Get gain column from mapping
        gain_col = "gain_pct"
        if self._app_state.column_mapping:
            gain_col = self._app_state.column_mapping.gain_pct

        # Calculate impact for all features
        self._results = self._calculator.calculate_all_features(
            df=df,
            gain_col=gain_col,
        )
        self._impact_scores = self._calculator.calculate_impact_scores(self._results)

        # Sort by impact score (descending)
        self._results.sort(
            key=lambda r: self._impact_scores.get(r.feature_name, 0),
            reverse=True,
        )

        # Update UI
        self._update_summary()
        self._populate_table()

    def _update_summary(self) -> None:
        """Update the summary label."""
        n_features = len(self._results)
        n_trades = self._results[0].trades_total if self._results else 0
        self._summary_label.setText(
            f"Analyzing {n_features} features across {n_trades:,} trades"
        )

    def _populate_table(self) -> None:
        """Populate the table with analysis results."""
        self._table.setRowCount(len(self._results))

        # Calculate ranges for gradient coloring
        correlations = [r.correlation for r in self._results]
        wr_lifts = [r.win_rate_lift for r in self._results]
        ev_lifts = [r.expectancy_lift for r in self._results]
        scores = [self._impact_scores.get(r.feature_name, 0) for r in self._results]

        corr_range = (min(correlations), max(correlations)) if correlations else (0, 0)
        wr_range = (min(wr_lifts), max(wr_lifts)) if wr_lifts else (0, 0)
        ev_range = (min(ev_lifts), max(ev_lifts)) if ev_lifts else (0, 0)
        score_range = (min(scores), max(scores)) if scores else (0, 0)

        for row, result in enumerate(self._results):
            score = self._impact_scores.get(result.feature_name, 0)

            # Feature name (no gradient)
            name_item = QTableWidgetItem(result.feature_name)
            name_item.setForeground(QBrush(QColor(Colors.TEXT_PRIMARY)))
            self._table.setItem(row, 0, name_item)

            # Impact score (cyan gradient only - always positive)
            score_item = QTableWidgetItem(f"{score:.2f}")
            score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            bg, text = get_gradient_color(score, 0, score_range[1])
            score_item.setBackground(QBrush(bg))
            score_item.setForeground(QBrush(text))
            self._table.setItem(row, 1, score_item)

            # Correlation (coral to cyan)
            corr_item = QTableWidgetItem(f"{result.correlation:+.3f}")
            corr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            bg, text = get_gradient_color(result.correlation, corr_range[0], corr_range[1])
            corr_item.setBackground(QBrush(bg))
            corr_item.setForeground(QBrush(text))
            self._table.setItem(row, 2, corr_item)

            # Win rate lift (coral to cyan)
            wr_item = QTableWidgetItem(f"{result.win_rate_lift:+.1f}%")
            wr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            bg, text = get_gradient_color(result.win_rate_lift, wr_range[0], wr_range[1])
            wr_item.setBackground(QBrush(bg))
            wr_item.setForeground(QBrush(text))
            self._table.setItem(row, 3, wr_item)

            # Expectancy lift (coral to cyan)
            ev_item = QTableWidgetItem(f"{result.expectancy_lift:+.4f}")
            ev_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            bg, text = get_gradient_color(result.expectancy_lift, ev_range[0], ev_range[1])
            ev_item.setBackground(QBrush(bg))
            ev_item.setForeground(QBrush(text))
            self._table.setItem(row, 4, ev_item)

            # Threshold (no gradient)
            direction = ">" if result.threshold_direction == "above" else "<"
            thresh_item = QTableWidgetItem(f"{direction} {result.optimal_threshold:.2f}")
            thresh_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            thresh_item.setForeground(QBrush(QColor(Colors.TEXT_PRIMARY)))
            self._table.setItem(row, 5, thresh_item)

            # Trades (no gradient)
            trades_item = QTableWidgetItem(f"{result.trades_total:,}")
            trades_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            trades_item.setForeground(QBrush(QColor(Colors.TEXT_PRIMARY)))
            self._table.setItem(row, 6, trades_item)
