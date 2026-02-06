"""Statistics tab with 5 analytical tables for trade analysis."""

import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.app_state import AppState
from src.core.exceptions import ExportError
from src.core.export_manager import ExportManager
from src.core.models import AdjustmentParams, ComputedMetrics, TradingMetrics
from src.core.statistics import (
    SCALING_TARGET_LEVELS,
    calculate_loss_chance_table,
    calculate_mae_before_win,
    calculate_mfe_before_loss,
    calculate_offset_table,
    calculate_partial_cover_table,
    calculate_profit_chance_table,
    calculate_scale_adjusted_gains,
    calculate_scaling_table,
    calculate_stop_loss_table,
)
from src.ui.components.toast import Toast
from src.ui.constants import Colors, Fonts, Spacing
from src.utils.table_export import table_to_markdown

logger = logging.getLogger(__name__)

# Best row highlight (highest EG% per table)
ROW_OPTIMAL_BG = QColor(0, 255, 212, 20)  # Subtle cyan glow (8% alpha ~ 20/255)
ROW_OPTIMAL_BORDER = QColor("#00FFD4")  # Left border accent

# Columns that are ratios (3 decimal places)
RATIO_COLUMNS = {
    "Profit Ratio",
    "Blended Profit Ratio",
    "Full Hold Profit Ratio",
}

# Columns that are counts (integer with thousands separator)
COUNT_COLUMNS = {
    "# of Plays",
    "# of Trades",
}

# Columns that are percentages (2 decimal places with % symbol)
PERCENTAGE_COLUMNS = {
    "% of Total",
    "Win %",
    "Edge %",
    "EG %",
    "Max Loss %",
    "Avg %",
    "Median %",
    "% of Trades",
    "Avg. Gain %",
    "Median Gain %",
    "EV %",
    "Total Gain %",
    "Avg Blended Return %",
    "Avg Full Hold Return %",
    "Total Blended Return %",
    "Total Full Hold Return %",
    "Blended Win %",
    "Full Hold Win %",
    "Blended Edge %",
    "Full Hold Edge %",
    "Blended EG %",
    "Full Hold EG %",
    ">5% MAE Probability",
    ">10% MAE Probability",
    ">15% MAE Probability",
    ">20% MAE Probability",
    ">5% MFE Probability",
    ">10% MFE Probability",
    ">15% MFE Probability",
    ">20% MFE Probability",
    "Max DD %",
}

# Kelly columns (show as percentages with 2 decimals)
KELLY_COLUMNS = {
    "Full Kelly (Stop Adj)",
    "Half Kelly (Stop Adj)",
    "Quarter Kelly (Stop Adj)",
}

# Dollar/currency columns (show with $ symbol and commas)
DOLLAR_COLUMNS = {
    "Total Kelly $",
}

# =============================================================================
# GRADIENT COLOR CONSTANTS (Observatory Theme)
# =============================================================================

# Three-point gradient anchors (for background colors with alpha)
GRADIENT_LOW = QColor(255, 71, 87, 45)      # Coral-red (low values)
GRADIENT_MID = QColor(148, 148, 168, 25)    # Neutral gray (middle values)
GRADIENT_HIGH = QColor(0, 255, 180, 45)     # Teal-green (high values)

# Text colors for each gradient region
TEXT_LOW = QColor("#FF6B7A")                 # Softer coral for readability
TEXT_MID = QColor("#B8B8C8")                 # Neutral light gray
TEXT_HIGH = QColor("#4FFFB0")                # Soft teal-green

# Fallback for non-numeric or excluded cells
CELL_DEFAULT_BG = QColor(0, 0, 0, 0)         # Transparent
CELL_DEFAULT_TEXT = QColor("#F4F4F8")        # Primary text


# =============================================================================
# GRADIENT INTERPOLATION FUNCTIONS
# =============================================================================

def lerp_color(color1: QColor, color2: QColor, t: float) -> QColor:
    """Linear interpolation between two QColors."""
    t = max(0.0, min(1.0, t))

    r = int(color1.red() + (color2.red() - color1.red()) * t)
    g = int(color1.green() + (color2.green() - color1.green()) * t)
    b = int(color1.blue() + (color2.blue() - color1.blue()) * t)
    a = int(color1.alpha() + (color2.alpha() - color1.alpha()) * t)

    return QColor(r, g, b, a)


def calculate_gradient_colors(
    value: float,
    min_val: float,
    max_val: float,
    invert: bool = False
) -> tuple[QColor, QColor]:
    """Calculate background and text colors based on value position in range."""
    if min_val == max_val:
        return (GRADIENT_MID, TEXT_MID)

    normalized = (value - min_val) / (max_val - min_val)
    normalized = max(0.0, min(1.0, normalized))

    if invert:
        normalized = 1.0 - normalized

    if normalized < 0.5:
        t = normalized * 2
        bg_color = lerp_color(GRADIENT_LOW, GRADIENT_MID, t)
        text_color = lerp_color(TEXT_LOW, TEXT_MID, t)
    else:
        t = (normalized - 0.5) * 2
        bg_color = lerp_color(GRADIENT_MID, GRADIENT_HIGH, t)
        text_color = lerp_color(TEXT_MID, TEXT_HIGH, t)

    return (bg_color, text_color)


# Columns to exclude from gradient styling (first/label columns)
GRADIENT_EXCLUDED_COLUMNS = frozenset({
    "Level",
    "Stop Loss %",
    "Offset %",
    "Target %",
    "Scale Out %",
    "Cover %",
    "Gain Bucket",
})


class GradientStyler:
    """Manages gradient styling for table columns.

    Usage:
        styler = GradientStyler()
        styler.set_column_range("EG %", -5.0, 15.0)
        bg, text = styler.get_cell_colors("EG %", 8.5)
    """

    def __init__(self):
        self._column_ranges: dict[str, tuple[float, float]] = {}

    def set_column_range(self, column_name: str, min_val: float, max_val: float) -> None:
        """Register the min/max range for a column."""
        self._column_ranges[column_name] = (min_val, max_val)

    def clear_ranges(self) -> None:
        """Clear all registered column ranges."""
        self._column_ranges.clear()

    def get_cell_colors(
        self,
        column_name: str,
        value: float | None
    ) -> tuple[QColor, QColor]:
        """Get background and text colors for a cell.

        Args:
            column_name: Name of the column
            value: Cell's numeric value (or None)

        Returns:
            Tuple of (background_color, text_color)
        """
        # Excluded columns get default styling
        if column_name in GRADIENT_EXCLUDED_COLUMNS:
            return (CELL_DEFAULT_BG, CELL_DEFAULT_TEXT)

        # Non-numeric values get default styling
        if value is None:
            return (CELL_DEFAULT_BG, CELL_DEFAULT_TEXT)

        if isinstance(value, float) and math.isnan(value):
            return (CELL_DEFAULT_BG, CELL_DEFAULT_TEXT)

        # Get column range
        range_data = self._column_ranges.get(column_name)
        if range_data is None:
            return (CELL_DEFAULT_BG, CELL_DEFAULT_TEXT)

        min_val, max_val = range_data

        return calculate_gradient_colors(value, min_val, max_val, invert=False)


def compute_column_ranges_from_df(
    df: pd.DataFrame,
    styler: GradientStyler,
    exclude_first_column: bool = True
) -> None:
    """Pre-compute column ranges from a DataFrame and register them with the styler.

    Args:
        df: pandas DataFrame with table data
        styler: GradientStyler instance to register ranges with
        exclude_first_column: If True, skip the first column (usually labels)
    """
    styler.clear_ranges()

    columns = list(df.columns)
    if exclude_first_column and columns:
        columns = columns[1:]

    for col in columns:
        if col in GRADIENT_EXCLUDED_COLUMNS:
            continue

        try:
            values = df[col].dropna().tolist()
            if values:
                min_val, max_val = min(values), max(values)
                styler.set_column_range(col, min_val, max_val)
        except (TypeError, ValueError):
            # Column contains non-numeric data
            pass


class StatisticsTab(QWidget):
    """Tab displaying 5 statistics tables as sub-tabs."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._app_state = app_state
        self._gradient_styler = GradientStyler()
        # Scaling export state
        self._selected_scaling_target: int = SCALING_TARGET_LEVELS[0]
        self._scaling_radio_group: QButtonGroup | None = None
        # Flag to skip duplicate Stop/Offset calculations when golden metrics fire
        self._stop_offset_from_golden: bool = False
        self._setup_ui()
        self._connect_signals()
        self._initialize_from_state()

    def _setup_ui(self) -> None:
        """Set up the tab UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Empty state label - shown when no data is loaded
        self._empty_label = QLabel("Load trade data to view statistics")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: 16px;
            }}
        """
        )

        # Sub-tabs using QTabWidget
        self._tab_widget = QTabWidget()
        self._style_tab_widget()

        # Create 3 sub-tabs (MAE/MFE combined, Stop Loss/Offset combined)
        self._mae_mfe_widget = self._create_mae_mfe_widget()
        self._stop_loss_offset_widget = self._create_stop_loss_offset_widget()
        self._scaling_widget = self._create_scaling_widget()

        self._tab_widget.addTab(self._mae_mfe_widget, "MAE/MFE")
        self._tab_widget.addTab(self._stop_loss_offset_widget, "Stop Loss/Offset")
        self._tab_widget.addTab(self._scaling_widget, "Scaling")

        # Profit/Loss Chance tab
        self._profit_loss_chance_widget = self._create_profit_loss_chance_widget()
        self._tab_widget.addTab(self._profit_loss_chance_widget, "Profit/Loss Chance")

        # Time Stop tab
        self._time_stop_widget = self._create_time_stop_widget()
        self._tab_widget.addTab(self._time_stop_widget, "Time Stop")

        # Add both widgets to layout
        layout.addWidget(self._empty_label)
        layout.addWidget(self._tab_widget)

        # Export button row
        export_row = QHBoxLayout()
        export_row.addStretch()

        self._export_btn = QPushButton("Export")
        self._export_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                padding: 8px 16px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_BORDER};
            }}
            QPushButton:pressed {{
                background-color: {Colors.BG_SURFACE};
            }}
        """
        )
        self._export_btn.clicked.connect(self._on_export_clicked)
        export_row.addWidget(self._export_btn)

        layout.addLayout(export_row)

        # Initially show empty state
        self._show_empty_state(True)

    def _style_tab_widget(self) -> None:
        """Apply Observatory theme styling to tab widget."""
        self._tab_widget.setStyleSheet(
            f"""
            QTabWidget::pane {{
                background-color: {Colors.BG_SURFACE};
                border: none;
            }}
            QTabBar::tab {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_SECONDARY};
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {Colors.BG_BORDER};
            }}
        """
        )

    def _create_table(self) -> QTableWidget:
        """Create a styled table widget."""
        table = QTableWidget()
        table.setStyleSheet(
            f"""
            QTableWidget {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                gridline-color: {Colors.BG_BORDER};
                border: none;
                font-family: '{Fonts.DATA}';
            }}
            QHeaderView::section {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_SECONDARY};
                padding: 8px;
                border: none;
                font-weight: 600;
            }}
            QTableWidget::item {{
                padding: 8px;
            }}
        """
        )
        return table

    def _create_scaling_widget(self) -> QWidget:
        """Create scaling sub-tab with spinbox controls for target and cover."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # Scale Out control row
        scale_out_row = QHBoxLayout()
        scale_out_row.setSpacing(Spacing.SM)

        scale_out_label = QLabel("Scale Out:")
        scale_out_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: 13px;
            }}
        """
        )
        scale_out_row.addWidget(scale_out_label)

        self._scale_out_spin = QSpinBox()
        self._scale_out_spin.setRange(0, 100)
        self._scale_out_spin.setValue(50)
        self._scale_out_spin.setSingleStep(10)
        self._scale_out_spin.setSuffix("%")
        self._scale_out_spin.setStyleSheet(
            f"""
            QSpinBox {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.DATA}';
                padding: 6px 12px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
            }}
            QSpinBox:focus {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
        """
        )
        scale_out_row.addWidget(self._scale_out_spin)

        # Export button for scaling table
        self._scaling_export_btn = QPushButton("Export")
        self._scaling_export_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                padding: 6px 12px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_BORDER};
            }}
            QPushButton:pressed {{
                background-color: {Colors.BG_SURFACE};
            }}
        """
        )
        self._scaling_export_btn.clicked.connect(self._on_scaling_export_clicked)
        scale_out_row.addWidget(self._scaling_export_btn)

        scale_out_row.addStretch()

        layout.addLayout(scale_out_row)

        # Initialize radio button group for scaling table selection
        self._scaling_radio_group = QButtonGroup(self)
        self._scaling_radio_group.setExclusive(True)

        # Scaling table (Partial Target %)
        self._scaling_table = self._create_table()
        layout.addWidget(self._scaling_table)

        # Message label for missing timing columns (scaling)
        self._scaling_timing_msg = QLabel("MAE/MFE Time Mapping is required")
        self._scaling_timing_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scaling_timing_msg.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: 14px;
                padding: 40px;
            }}
        """
        )
        self._scaling_timing_msg.hide()
        layout.addWidget(self._scaling_timing_msg)

        # Spacer between sections
        layout.addSpacing(Spacing.LG)

        # Cover control row
        cover_row = QHBoxLayout()
        cover_row.setSpacing(Spacing.SM)

        cover_label = QLabel("Cover:")
        cover_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: 13px;
            }}
        """
        )
        cover_row.addWidget(cover_label)

        self._cover_spin = QSpinBox()
        self._cover_spin.setRange(0, 100)
        self._cover_spin.setValue(50)
        self._cover_spin.setSingleStep(10)
        self._cover_spin.setSuffix("%")
        self._cover_spin.setStyleSheet(
            f"""
            QSpinBox {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.DATA}';
                padding: 6px 12px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
            }}
            QSpinBox:focus {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
        """
        )
        cover_row.addWidget(self._cover_spin)
        cover_row.addStretch()

        layout.addLayout(cover_row)

        # Cover table (Partial Cover %)
        self._cover_table = self._create_table()
        layout.addWidget(self._cover_table)

        # Message label for missing timing columns (cover)
        self._cover_timing_msg = QLabel("MAE/MFE Time Mapping is required")
        self._cover_timing_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cover_timing_msg.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: 14px;
                padding: 40px;
            }}
        """
        )
        self._cover_timing_msg.hide()
        layout.addWidget(self._cover_timing_msg)

        return widget

    def _create_mae_mfe_widget(self) -> QWidget:
        """Create combined MAE/MFE sub-tab with stacked tables."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # MAE section label
        mae_label = QLabel("MAE Before Win")
        mae_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: 14px;
                font-weight: 600;
            }}
        """
        )
        layout.addWidget(mae_label)

        # MAE table
        self._mae_table = self._create_table()
        layout.addWidget(self._mae_table, 1)  # stretch factor 1

        # Spacer
        layout.addSpacing(Spacing.LG)

        # MFE section label
        mfe_label = QLabel("MFE Before Loss")
        mfe_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: 14px;
                font-weight: 600;
            }}
        """
        )
        layout.addWidget(mfe_label)

        # MFE table
        self._mfe_table = self._create_table()
        layout.addWidget(self._mfe_table, 1)  # stretch factor 1

        return widget

    def _create_stop_loss_offset_widget(self) -> QWidget:
        """Create combined Stop Loss/Offset sub-tab with stacked tables."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # Stop Loss section label
        stop_loss_label = QLabel("Stop Loss")
        stop_loss_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: 14px;
                font-weight: 600;
            }}
        """
        )
        layout.addWidget(stop_loss_label)

        # Stop Loss table
        self._stop_loss_table = self._create_table()
        layout.addWidget(self._stop_loss_table, 1)  # stretch factor 1

        # Spacer
        layout.addSpacing(Spacing.LG)

        # Offset section label
        offset_label = QLabel("Offset")
        offset_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: 14px;
                font-weight: 600;
            }}
        """
        )
        layout.addWidget(offset_label)

        # Offset table
        self._offset_table = self._create_table()
        layout.addWidget(self._offset_table, 1)  # stretch factor 1

        return widget

    def _create_profit_loss_chance_widget(self) -> QWidget:
        """Create Profit/Loss Chance sub-tab with stacked tables."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # Chance of Profit section label
        profit_label = QLabel("Chance of Profit")
        profit_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: 14px;
                font-weight: 600;
            }}
        """
        )
        layout.addWidget(profit_label)

        # Profit Chance table
        self._profit_chance_table = self._create_table()
        layout.addWidget(self._profit_chance_table, 1)

        # Spacer
        layout.addSpacing(Spacing.LG)

        # Chance of Loss section label
        loss_label = QLabel("Chance of Loss")
        loss_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: 14px;
                font-weight: 600;
            }}
        """
        )
        layout.addWidget(loss_label)

        # Loss Chance table
        self._loss_chance_table = self._create_table()
        layout.addWidget(self._loss_chance_table, 1)

        return widget

    def _create_time_stop_widget(self) -> QWidget:
        """Create Time Stop sub-tab with scale spinbox and two tables."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # Scale Out control row
        scale_out_row = QHBoxLayout()
        scale_out_row.setSpacing(Spacing.SM)

        scale_out_label = QLabel("Scale Out:")
        scale_out_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: 13px;
            }}
        """
        )
        scale_out_row.addWidget(scale_out_label)

        self._time_stop_scale_spin = QSpinBox()
        self._time_stop_scale_spin.setRange(0, 100)
        self._time_stop_scale_spin.setValue(50)
        self._time_stop_scale_spin.setSingleStep(10)
        self._time_stop_scale_spin.setSuffix("%")
        self._time_stop_scale_spin.setStyleSheet(
            f"""
            QSpinBox {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.DATA}';
                padding: 6px 12px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
            }}
            QSpinBox:focus {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
        """
        )
        scale_out_row.addWidget(self._time_stop_scale_spin)

        # Export button for time stop tables
        self._time_stop_export_btn = QPushButton("Export")
        self._time_stop_export_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                padding: 6px 12px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_BORDER};
            }}
            QPushButton:pressed {{
                background-color: {Colors.BG_SURFACE};
            }}
        """
        )
        self._time_stop_export_btn.clicked.connect(self._on_time_stop_export_clicked)
        scale_out_row.addWidget(self._time_stop_export_btn)

        scale_out_row.addStretch()

        layout.addLayout(scale_out_row)

        # Time Statistics section label
        time_stats_label = QLabel("Time Statistics")
        time_stats_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: 14px;
                font-weight: 600;
            }}
        """
        )
        layout.addWidget(time_stats_label)

        # Time Statistics table
        self._time_stats_table = self._create_table()
        layout.addWidget(self._time_stats_table, 1)

        # Spacer
        layout.addSpacing(Spacing.LG)

        # Time Stop section label
        time_stop_label = QLabel("Time Stop")
        time_stop_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: 14px;
                font-weight: 600;
            }}
        """
        )
        layout.addWidget(time_stop_label)

        # Time Stop table
        self._time_stop_table = self._create_table()
        layout.addWidget(self._time_stop_table, 1)

        # Message label for when no time columns are mapped
        self._time_stop_timing_msg = QLabel("Time column mapping is required")
        self._time_stop_timing_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._time_stop_timing_msg.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: 14px;
                padding: 40px;
            }}
        """
        )
        self._time_stop_timing_msg.hide()
        layout.addWidget(self._time_stop_timing_msg)

        return widget

    def _on_time_stop_export_clicked(self) -> None:
        """Export Time Statistics and Time Stop tables to CSV."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"time_stop_export_{timestamp}.csv"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Time Stop Tables", default_name, "CSV Files (*.csv)"
        )

        if not file_path:
            return

        try:
            stats_df = self._table_to_dataframe(self._time_stats_table)
            stop_df = self._table_to_dataframe(self._time_stop_table)

            scale_out = self._time_stop_scale_spin.value()

            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                f.write("# Time Statistics\n")
                if stats_df is not None:
                    stats_df.to_csv(f, index=False)
                f.write(f"\n# Time Stop (Scale Out: {scale_out}%)\n")
                if stop_df is not None:
                    stop_df.to_csv(f, index=False)

            Toast.display(self, f"Exported to {Path(file_path).name}", "success")

        except Exception as e:
            logger.error(f"Time Stop export failed: {e}")
            Toast.display(self, f"Export failed: {e}", "error")

    def _connect_signals(self) -> None:
        """Connect app state signals."""
        # Connect to baseline calculated signal for initial data display
        self._app_state.baseline_calculated.connect(self._on_baseline_calculated)

        # Connect to filtered data for when filters are applied
        self._app_state.filtered_data_updated.connect(self._on_filtered_data_updated)

        # Connect to adjustment params changes (stop loss, efficiency)
        self._app_state.adjustment_params_changed.connect(self._on_adjustment_params_changed)

        # Connect to metrics user inputs changes (Kelly/capital)
        self._app_state.metrics_user_inputs_changed.connect(self._on_metrics_inputs_changed)

        # Connect scale out spinbox to refresh scaling table
        self._scale_out_spin.valueChanged.connect(self._on_scale_out_changed)
        self._cover_spin.valueChanged.connect(self._on_cover_changed)

        # Connect time stop scale spinbox to refresh time stop tables
        self._time_stop_scale_spin.valueChanged.connect(self._on_time_stop_scale_changed)

        # Connect to unified metrics signal (golden statistics)
        self._app_state.all_metrics_ready.connect(self._on_all_metrics_ready)

    def _initialize_from_state(self) -> None:
        """Populate tables if data already exists in state.

        Uses filtered_df if available, otherwise falls back to baseline_df.
        This ensures tables display data immediately when tab is opened.
        """
        if not self._app_state.column_mapping:
            return

        # Prefer filtered data if available, otherwise use baseline
        df = None
        if self._app_state.filtered_df is not None and not self._app_state.filtered_df.empty:
            df = self._app_state.filtered_df
        elif self._app_state.baseline_df is not None and not self._app_state.baseline_df.empty:
            df = self._app_state.baseline_df

        if df is not None:
            # Hide empty state and show tables
            self._show_empty_state(False)
            # Check column availability and enable/disable tabs accordingly
            self._check_column_availability(df)
            self._update_all_tables(df)

    def _on_baseline_calculated(self, metrics: TradingMetrics) -> None:
        """Handle baseline metrics calculated signal.

        Displays baseline data in tables when no filters are applied.

        Args:
            metrics: Calculated baseline metrics (unused, we need the DataFrame).
        """
        # Only use baseline if no filtered data exists yet
        if self._app_state.filtered_df is not None and not self._app_state.filtered_df.empty:
            return

        if self._app_state.baseline_df is None or not self._app_state.column_mapping:
            return

        # Hide empty state and show tables
        self._show_empty_state(False)

        # Check column availability and enable/disable tabs accordingly
        self._check_column_availability(self._app_state.baseline_df)

        self._update_all_tables(self._app_state.baseline_df)

    def _on_filtered_data_updated(self, df: pd.DataFrame) -> None:
        """Handle filtered data update.

        Args:
            df: Updated filtered DataFrame.
        """
        if not self._app_state.column_mapping:
            return

        # Hide empty state and show tables
        self._show_empty_state(False)

        # Check column availability and enable/disable tabs accordingly
        self._check_column_availability(df)

        self._update_all_tables(df)

    def _on_adjustment_params_changed(self, params: AdjustmentParams) -> None:
        """Handle adjustment parameters changed.

        Refreshes stop loss and offset tables which depend on these params.

        Args:
            params: New adjustment parameters.
        """
        self._refresh_all_tables()

    def _on_metrics_inputs_changed(self, inputs) -> None:
        """Refresh tables when Kelly/capital inputs change.

        Args:
            inputs: New metrics user inputs (starting capital, fractional kelly, etc.).
        """
        self._refresh_all_tables()

    def _on_all_metrics_ready(self, computed: ComputedMetrics) -> None:
        """Handle unified metrics update from golden statistics.

        Populates Stop Loss and Offset tables from pre-computed scenarios,
        avoiding duplicate calculations.

        Args:
            computed: Pre-computed metrics including scenarios.
        """
        if not self._app_state.column_mapping:
            return

        # Hide empty state and show tables
        self._show_empty_state(False)

        # Populate Stop Loss table from pre-computed scenarios
        if computed.stop_scenarios:
            stop_df = self._scenarios_to_stop_dataframe(computed.stop_scenarios)
            self._populate_table(self._stop_loss_table, stop_df)
            # Set flag to skip duplicate calculation in _update_all_tables
            self._stop_offset_from_golden = True

        # Populate Offset table from pre-computed scenarios
        if computed.offset_scenarios:
            offset_df = self._scenarios_to_offset_dataframe(computed.offset_scenarios)
            self._populate_table(self._offset_table, offset_df)
            # Set flag to skip duplicate calculation in _update_all_tables
            self._stop_offset_from_golden = True

    def _scenarios_to_stop_dataframe(self, scenarios: list) -> pd.DataFrame:
        """Convert StopScenario list to DataFrame for table display.

        Args:
            scenarios: List of StopScenario objects from pre-computed metrics.

        Returns:
            DataFrame formatted for the Stop Loss table display.
        """
        rows = []
        for s in scenarios:
            rows.append({
                "Stop %": s.stop_pct,
                "Win %": s.win_pct,
                "EV %": s.ev_pct,
                "Avg. Gain %": s.avg_gain_pct,
                "Median Gain %": s.median_gain_pct,
                "Edge %": s.edge_pct,
                "Max Loss %": s.max_loss_pct,
                "Full Kelly (Stop Adj)": s.stop_adjusted_kelly_pct,
                "Half Kelly (Stop Adj)": s.stop_adjusted_kelly_pct / 2 if s.stop_adjusted_kelly_pct else None,
                "Quarter Kelly (Stop Adj)": s.stop_adjusted_kelly_pct / 4 if s.stop_adjusted_kelly_pct else None,
                "Max DD %": s.max_dd_pct,
                "Total Kelly $": s.kelly_pnl,
            })
        return pd.DataFrame(rows)

    def _scenarios_to_offset_dataframe(self, scenarios: list) -> pd.DataFrame:
        """Convert OffsetScenario list to DataFrame for table display.

        Args:
            scenarios: List of OffsetScenario objects from pre-computed metrics.

        Returns:
            DataFrame formatted for the Offset table display.
        """
        rows = []
        for s in scenarios:
            rows.append({
                "Offset %": s.offset_pct,
                "# of Trades": s.num_trades,
                "Win %": s.win_pct,
                "Total Return %": s.total_return_pct,
                "EG %": s.eg_pct,
            })
        return pd.DataFrame(rows)

    def _on_scale_out_changed(self, value: int) -> None:
        """Handle scale out spinbox value change.

        Args:
            value: New scale out percentage (10-90).
        """
        self._refresh_scaling_table()

    def _on_cover_changed(self, value: int) -> None:
        """Handle cover percentage spinbox value change.

        Args:
            value: New cover percentage (0-100).
        """
        self._refresh_cover_table()

    def _show_empty_state(self, show: bool) -> None:
        """Show or hide the empty state.

        Args:
            show: True to show empty state, False to show tables.
        """
        self._empty_label.setVisible(show)
        self._tab_widget.setVisible(not show)

    def _check_column_availability(self, df: pd.DataFrame | None) -> None:
        """Check which columns are available and enable/disable tabs accordingly.

        Args:
            df: The DataFrame to check for column availability, or None.
        """
        mapping = self._app_state.column_mapping

        if mapping is None or df is None:
            # Disable all tabs when no mapping or data
            for i in range(self._tab_widget.count()):
                self._tab_widget.setTabEnabled(i, False)
            return

        # Check if MAE and MFE columns exist in the actual DataFrame
        df_columns = list(df.columns)
        has_mae = mapping.mae_pct in df_columns
        has_mfe = mapping.mfe_pct in df_columns

        # Combined MAE/MFE tab - enable if either column available
        self._tab_widget.setTabEnabled(0, has_mae or has_mfe)  # MAE/MFE

        # Combined Stop Loss/Offset tab - MAE-dependent
        self._tab_widget.setTabEnabled(1, has_mae)  # Stop Loss/Offset

        # Scaling tab - MFE-dependent
        self._tab_widget.setTabEnabled(2, has_mfe)  # Scaling

        # Find the index of Profit/Loss Chance tab
        profit_loss_idx = None
        for i in range(self._tab_widget.count()):
            if self._tab_widget.tabText(i) == "Profit/Loss Chance":
                profit_loss_idx = i
                break

        if profit_loss_idx is not None:
            has_mfe_mae = has_mfe and has_mae
            self._tab_widget.setTabEnabled(profit_loss_idx, has_mfe_mae)

        # Log warnings for missing columns
        if not has_mae:
            logger.warning(
                f"MAE column '{mapping.mae_pct}' not found in data. MAE-dependent tabs disabled."
            )
        if not has_mfe:
            logger.warning(
                f"MFE column '{mapping.mfe_pct}' not found in data. MFE-dependent tabs disabled."
            )

    def _get_current_df(self) -> pd.DataFrame | None:
        """Get the current DataFrame to use for calculations.

        Prefers filtered data, falls back to baseline.

        Returns:
            Current DataFrame or None if no data available.
        """
        if self._app_state.filtered_df is not None and not self._app_state.filtered_df.empty:
            return self._app_state.filtered_df
        return self._app_state.baseline_df

    def _has_timing_columns(self, df: pd.DataFrame | None = None) -> bool:
        """Check if timing columns (mae_time, mfe_time) are mapped and available.

        Args:
            df: DataFrame to check. If None, uses current data.

        Returns:
            True if both timing columns are mapped and present in data.
        """
        mapping = self._app_state.column_mapping
        if mapping is None:
            return False

        if mapping.mae_time is None or mapping.mfe_time is None:
            return False

        if df is None:
            df = self._get_current_df()

        if df is None or df.empty:
            return False

        return mapping.mae_time in df.columns and mapping.mfe_time in df.columns

    def _has_time_interval_columns(self, df: pd.DataFrame | None = None) -> bool:
        """Check if any time interval price columns are mapped and computed."""
        mapping = self._app_state.column_mapping
        if mapping is None:
            return False

        if df is None:
            df = self._get_current_df()
        if df is None or df.empty:
            return False

        # Check if any change_X_min columns exist
        for interval in [10, 20, 30, 60, 90, 120, 150, 180, 240]:
            if f"change_{interval}_min" in df.columns:
                return True
        return False

    def _update_all_tables(self, df: pd.DataFrame) -> None:
        """Update all 5 tables with the given DataFrame.

        Args:
            df: DataFrame containing trade data to display.
        """
        if df is None or df.empty or not self._app_state.column_mapping:
            self._clear_all_tables()
            return

        mapping = self._app_state.column_mapping
        params = self._app_state.adjustment_params

        # Compute fresh adjusted_gain_pct to ensure Scaling/Cover tables use current efficiency
        # This avoids race conditions with other tabs that also update adjusted_gain_pct
        if mapping.mae_pct is not None and mapping.mae_pct in df.columns:
            adjusted_gains = params.calculate_adjusted_gains(
                df, mapping.gain_pct, mapping.mae_pct
            )
            df = df.copy()  # Don't modify the original
            df["adjusted_gain_pct"] = adjusted_gains

        # Calculate and populate MAE Before Win table
        try:
            mae_df = calculate_mae_before_win(df, mapping)
            self._populate_table(self._mae_table, mae_df)
        except Exception as e:
            logger.warning(f"Error calculating MAE table: {e}")
            self._mae_table.setRowCount(0)

        # Calculate and populate MFE Before Loss table
        try:
            mfe_df = calculate_mfe_before_loss(df, mapping)
            self._populate_table(self._mfe_table, mfe_df)
        except Exception as e:
            logger.warning(f"Error calculating MFE table: {e}")
            self._mfe_table.setRowCount(0)

        # Skip Stop Loss and Offset calculations if already populated from golden metrics
        # This prevents duplicate work when all_metrics_ready fires before filtered_data_changed
        if not self._stop_offset_from_golden:
            # Calculate and populate Stop Loss table
            # Pass AdjustmentParams directly - function will compute adjusted gains fresh
            try:
                # Get Kelly parameters from app state
                metrics_inputs = self._app_state.metrics_user_inputs
                start_capital = metrics_inputs.starting_capital if metrics_inputs else 100000.0
                fractional_kelly_pct = metrics_inputs.fractional_kelly if metrics_inputs else 25.0

                stop_loss_df = calculate_stop_loss_table(
                    df,
                    mapping,
                    params,
                    start_capital=start_capital,
                    fractional_kelly_pct=fractional_kelly_pct,
                )
                self._populate_table(self._stop_loss_table, stop_loss_df)
            except Exception as e:
                logger.warning(f"Error calculating Stop Loss table: {e}")
                self._stop_loss_table.setRowCount(0)

            # Calculate and populate Offset table
            # Pass AdjustmentParams directly - function will compute adjusted gains fresh
            try:
                offset_df = calculate_offset_table(
                    df,
                    mapping,
                    params,
                    start_capital=start_capital,
                    fractional_kelly_pct=fractional_kelly_pct,
                )
                self._populate_table(self._offset_table, offset_df)
            except Exception as e:
                logger.warning(f"Error calculating Offset table: {e}")
                self._offset_table.setRowCount(0)
        else:
            # Reset flag after skipping - next update should calculate fresh
            self._stop_offset_from_golden = False

        # Check if timing columns are available for Scaling/Cover tables
        has_timing = self._has_timing_columns(df)

        # Calculate and populate Scaling table (requires timing columns)
        if has_timing:
            self._scaling_timing_msg.hide()
            self._scaling_table.show()
            try:
                scale_out_pct = self._scale_out_spin.value() / 100.0
                scaling_df = calculate_scaling_table(df, mapping, scale_out_pct, params)
                
                # Clear table completely before repopulating to avoid duplicate columns
                self._scaling_table.clear()
                self._scaling_table.setRowCount(0)
                self._scaling_table.setColumnCount(0)
                
                self._populate_table(self._scaling_table, scaling_df)
                self._add_scaling_radio_buttons(scaling_df)
            except Exception as e:
                logger.warning(f"Error calculating Scaling table: {e}")
                self._scaling_table.setRowCount(0)
        else:
            self._scaling_table.hide()
            self._scaling_timing_msg.show()

        # Calculate and populate Cover table (requires timing columns)
        if has_timing:
            self._cover_timing_msg.hide()
            self._cover_table.show()
            try:
                cover_pct = self._cover_spin.value() / 100.0
                cover_df = calculate_partial_cover_table(df, mapping, cover_pct)
                self._populate_table(self._cover_table, cover_df)
            except Exception as e:
                logger.warning(f"Error calculating Cover table: {e}")
                self._cover_table.setRowCount(0)
        else:
            self._cover_table.hide()
            self._cover_timing_msg.show()

        # Profit/Loss Chance tables
        try:
            profit_chance_df = calculate_profit_chance_table(df, mapping, params)
            self._populate_table(self._profit_chance_table, profit_chance_df)
        except Exception as e:
            logger.error(f"Failed to calculate profit chance table: {e}")
            self._profit_chance_table.setRowCount(0)

        try:
            loss_chance_df = calculate_loss_chance_table(df, mapping, params)
            self._populate_table(self._loss_chance_table, loss_chance_df)
        except Exception as e:
            logger.error(f"Failed to calculate loss chance table: {e}")
            self._loss_chance_table.setRowCount(0)

        # Time Stop tables
        self._refresh_time_stop_tables()

    def _refresh_all_tables(self) -> None:
        """Refresh all tables with current data.

        Uses filtered_df if available, otherwise falls back to baseline_df.
        """
        df = self._get_current_df()
        if df is not None and not df.empty:
            self._update_all_tables(df)

    def _refresh_scaling_table(self) -> None:
        """Refresh only the scaling table with current data."""
        if not self._app_state.column_mapping:
            return

        df = self._get_current_df()
        if df is None or df.empty:
            return

        # Check if timing columns are available
        if not self._has_timing_columns(df):
            self._scaling_table.hide()
            self._scaling_timing_msg.show()
            return

        self._scaling_timing_msg.hide()
        self._scaling_table.show()

        mapping = self._app_state.column_mapping

        try:
            scale_out_pct = self._scale_out_spin.value() / 100.0
            adjustment_params = self._app_state.adjustment_params
            scaling_df = calculate_scaling_table(df, mapping, scale_out_pct, adjustment_params)
            
            # Clear table completely before repopulating to avoid duplicate columns
            self._scaling_table.clear()
            self._scaling_table.setRowCount(0)
            self._scaling_table.setColumnCount(0)
            
            self._populate_table(self._scaling_table, scaling_df)
            self._add_scaling_radio_buttons(scaling_df)
        except Exception as e:
            logger.warning(f"Error refreshing Scaling table: {e}")

    def _add_scaling_radio_buttons(self, scaling_df: pd.DataFrame) -> None:
        """Add radio button selection column to scaling table.

        Args:
            scaling_df: DataFrame used to populate the table (for target values).
        """
        if scaling_df is None or scaling_df.empty:
            return

        table = self._scaling_table
        row_count = table.rowCount()
        col_count = table.columnCount()

        if row_count == 0 or col_count == 0:
            return

        # Check if Select column already exists (first header is "Select")
        first_header = table.horizontalHeaderItem(0)
        if first_header is None or first_header.text() != "Select":
            # Insert new column at position 0 only if it doesn't exist
            table.insertColumn(0)
            table.setHorizontalHeaderItem(0, QTableWidgetItem("Select"))

        # Clear existing radio group
        if self._scaling_radio_group:
            for button in self._scaling_radio_group.buttons():
                self._scaling_radio_group.removeButton(button)

        # Get target values from DataFrame
        targets = scaling_df["Partial Target %"].tolist()

        # Add radio buttons for each row
        for row_idx in range(row_count):
            radio = QRadioButton()
            radio.setStyleSheet(
                f"""
                QRadioButton {{
                    margin-left: 8px;
                }}
                QRadioButton::indicator {{
                    width: 14px;
                    height: 14px;
                }}
                QRadioButton::indicator:checked {{
                    background-color: {Colors.SIGNAL_CYAN};
                    border: 2px solid {Colors.SIGNAL_CYAN};
                    border-radius: 7px;
                }}
                QRadioButton::indicator:unchecked {{
                    background-color: {Colors.BG_ELEVATED};
                    border: 2px solid {Colors.BG_BORDER};
                    border-radius: 7px;
                }}
            """
            )

            # Store target value as property
            target_value = targets[row_idx] if row_idx < len(targets) else SCALING_TARGET_LEVELS[0]
            radio.setProperty("target", target_value)

            # Connect signal
            radio.toggled.connect(
                lambda checked, t=target_value: self._on_scaling_target_selected(checked, t)
            )

            # Add to button group
            self._scaling_radio_group.addButton(radio, row_idx)

            # Create container widget for centering
            container = QWidget()
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(4, 0, 4, 0)
            container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            container_layout.addWidget(radio)

            table.setCellWidget(row_idx, 0, container)

            # Check first row by default (or match current selection)
            if target_value == self._selected_scaling_target:
                radio.setChecked(True)

        # If no selection matched, select first row
        if self._scaling_radio_group.checkedButton() is None and row_count > 0:
            first_button = self._scaling_radio_group.button(0)
            if first_button:
                first_button.setChecked(True)
                self._selected_scaling_target = targets[0] if targets else SCALING_TARGET_LEVELS[0]

        # Resize the select column to be narrow
        table.setColumnWidth(0, 60)

    def _on_scaling_target_selected(self, checked: bool, target: int) -> None:
        """Handle scaling target selection change.

        Args:
            checked: Whether the radio button is now checked.
            target: The target percentage value selected.
        """
        if checked:
            self._selected_scaling_target = target

    def _on_scaling_export_clicked(self) -> None:
        """Handle scaling export button click.

        Exports filtered data with a scale_adjusted_gain_pct column based on
        the selected target level and current scale out percentage.
        """
        # Get current filtered DataFrame
        df = self._get_current_df()
        if df is None or df.empty:
            Toast.display(self, "No data available for export", "error")
            return

        if not self._app_state.column_mapping:
            Toast.display(self, "Column mapping not configured", "error")
            return

        mapping = self._app_state.column_mapping

        # Get scale out percentage
        scale_out_pct = self._scale_out_spin.value() / 100.0

        # Get adjustment params
        adjustment_params = self._app_state.adjustment_params

        # Calculate scale-adjusted gains
        try:
            scale_adjusted = calculate_scale_adjusted_gains(
                df,
                mapping,
                self._selected_scaling_target,
                scale_out_pct,
                adjustment_params,
            )
        except Exception as e:
            Toast.display(self, f"Error calculating scale-adjusted gains: {e}", "error")
            logger.error(f"Scale-adjusted calculation error: {e}")
            return

        # Create export DataFrame with the new column
        export_df = df.copy()
        export_df["scale_adjusted_gain_pct"] = scale_adjusted

        # Generate suggested filename with user's home directory as default
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = self._selected_scaling_target
        scale_out = self._scale_out_spin.value()
        default_dir = Path.home()
        suggested_path = default_dir / f"lumen_scaling_target{target}_scale{scale_out}_{timestamp}.csv"

        # Show save dialog with CSV and Excel options
        path_str, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Scaling Data",
            str(suggested_path),
            "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*)",
        )

        if not path_str:
            return  # User cancelled

        path = Path(path_str)

        # Determine format based on extension or selected filter
        is_excel = path.suffix.lower() == ".xlsx" or "Excel" in selected_filter

        # Ensure correct extension
        if is_excel and path.suffix.lower() != ".xlsx":
            path = path.with_suffix(".xlsx")
        elif not is_excel and path.suffix.lower() != ".csv":
            path = path.with_suffix(".csv")

        try:
            exporter = ExportManager()
            export_args = {
                "df": export_df,
                "path": path,
                "filters": self._app_state.filters,
                "first_trigger_enabled": self._app_state.first_trigger_enabled,
                "total_rows": (
                    len(self._app_state.raw_df)
                    if self._app_state.raw_df is not None
                    else None
                ),
            }

            if is_excel:
                exporter.to_excel(**export_args)
            else:
                exporter.to_csv(**export_args)

            Toast.display(
                self,
                f"Exported {len(export_df):,} rows to {path.name}",
                "success",
            )
            logger.info(f"Scaling export completed: {path}")
        except ExportError as e:
            Toast.display(self, str(e), "error")
            logger.error(f"Scaling export failed: {e}")

    def _refresh_cover_table(self) -> None:
        """Refresh only the cover table with current data."""
        if not self._app_state.column_mapping:
            return

        mapping = self._app_state.column_mapping
        df = self._get_current_df()

        if df is None or df.empty:
            return

        # Check if timing columns are available
        if not self._has_timing_columns(df):
            self._cover_table.hide()
            self._cover_timing_msg.show()
            return

        self._cover_timing_msg.hide()
        self._cover_table.show()

        try:
            cover_pct = self._cover_spin.value() / 100.0
            cover_df = calculate_partial_cover_table(df, mapping, cover_pct)
            self._populate_table(self._cover_table, cover_df)
        except Exception as e:
            logger.warning(f"Error refreshing Cover table: {e}")

    def _refresh_time_stop_tables(self) -> None:
        """Refresh Time Statistics and Time Stop tables."""
        if not self._app_state.column_mapping:
            return

        df = self._get_current_df()
        if df is None or df.empty:
            return

        if not self._has_time_interval_columns(df):
            self._time_stats_table.hide()
            self._time_stop_table.hide()
            self._time_stop_timing_msg.show()
            return

        self._time_stop_timing_msg.hide()
        self._time_stats_table.show()
        self._time_stop_table.show()

        mapping = self._app_state.column_mapping

        try:
            # Time Statistics table
            from src.core.statistics import calculate_time_statistics_table
            stats_df = calculate_time_statistics_table(df, mapping)
            self._time_stats_table.clear()
            self._time_stats_table.setRowCount(0)
            self._time_stats_table.setColumnCount(0)
            self._populate_table(self._time_stats_table, stats_df)

            # Time Stop table
            from src.core.statistics import calculate_time_stop_table
            scale_out_pct = self._time_stop_scale_spin.value() / 100.0
            stop_df = calculate_time_stop_table(df, mapping, scale_out_pct)
            self._time_stop_table.clear()
            self._time_stop_table.setRowCount(0)
            self._time_stop_table.setColumnCount(0)
            self._populate_table(self._time_stop_table, stop_df)
        except Exception as e:
            logger.warning(f"Error refreshing Time Stop tables: {e}")

    def _on_time_stop_scale_changed(self) -> None:
        """Handle Time Stop scale out spinbox change."""
        self._refresh_time_stop_tables()

    def _clear_all_tables(self) -> None:
        """Clear all table contents."""
        self._mae_table.setRowCount(0)
        self._mae_table.setColumnCount(0)
        self._mfe_table.setRowCount(0)
        self._mfe_table.setColumnCount(0)
        self._stop_loss_table.setRowCount(0)
        self._stop_loss_table.setColumnCount(0)
        self._offset_table.setRowCount(0)
        self._offset_table.setColumnCount(0)
        self._scaling_table.setRowCount(0)
        self._scaling_table.setColumnCount(0)
        self._cover_table.setRowCount(0)
        self._cover_table.setColumnCount(0)
        self._profit_chance_table.setRowCount(0)
        self._profit_chance_table.setColumnCount(0)
        self._loss_chance_table.setRowCount(0)
        self._loss_chance_table.setColumnCount(0)
        self._time_stats_table.setRowCount(0)
        self._time_stats_table.setColumnCount(0)
        self._time_stop_table.setRowCount(0)
        self._time_stop_table.setColumnCount(0)
        # Reset scaling/cover visibility
        self._scaling_timing_msg.hide()
        self._scaling_table.show()
        self._cover_timing_msg.hide()
        self._cover_table.show()
        # Reset time stop visibility
        self._time_stop_timing_msg.hide()
        self._time_stats_table.show()
        self._time_stop_table.show()

    def _populate_table(self, table: QTableWidget, df: pd.DataFrame) -> None:
        """Populate a QTableWidget from a DataFrame.

        Args:
            table: The QTableWidget to populate.
            df: DataFrame with data to display.
        """
        if df is None or df.empty:
            table.setRowCount(0)
            table.setColumnCount(0)
            return

        # Set dimensions
        table.setRowCount(len(df))
        table.setColumnCount(len(df.columns))

        # Set headers
        columns = list(df.columns)
        table.setHorizontalHeaderLabels(columns)

        # Compute column ranges for gradient styling (exclude first column)
        compute_column_ranges_from_df(df, self._gradient_styler, exclude_first_column=True)

        # Populate cells with styling
        for row_idx, (_, row) in enumerate(df.iterrows()):
            for col_idx, value in enumerate(row):
                column_name = columns[col_idx]
                is_first_column = col_idx == 0
                item = self._create_table_item(value, column_name, is_first_column)
                self._style_cell(item, value, column_name, is_first_column)
                table.setItem(row_idx, col_idx, item)

        # Highlight optimal row (highest EG%) for tables that have EG % column
        self._highlight_optimal_row(table, columns)

        # Resize columns to content
        header = table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

    def _create_table_item(
        self, value, column_name: str = "", is_first_column: bool = False
    ) -> QTableWidgetItem:
        """Create a formatted table item from a value.

        Args:
            value: The value to display (can be str, int, float, or None).
            column_name: The name of the column for formatting decisions.
            is_first_column: Whether this is the first column (label column).

        Returns:
            Formatted QTableWidgetItem.
        """
        text = self._format_value(value, column_name)
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Make read-only

        # Set alignment and font based on column type
        if is_first_column:
            # First column: bold, left-aligned
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            font = QFont(Fonts.DATA)
            font.setBold(True)
            item.setFont(font)
        elif isinstance(value, (int, float)) and value is not None:
            # Numeric columns: right-aligned, Azeret Mono font
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item.setFont(QFont(Fonts.DATA))
        else:
            # Other columns: left-aligned
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            item.setFont(QFont(Fonts.DATA))

        return item

    def _format_value(self, value, column_name: str) -> str:
        """Format a value for display based on column type.

        Args:
            value: The value to format.
            column_name: The column name for determining format.

        Returns:
            Formatted string representation.
        """
        if value is None:
            return "-"

        # Count columns: integer with thousands separator
        if column_name in COUNT_COLUMNS:
            return f"{int(value):,}"

        # Ratio columns: 3 decimal places
        if column_name in RATIO_COLUMNS:
            return f"{value:.3f}"

        # Percentage columns: 2 decimal places with % symbol
        if column_name in PERCENTAGE_COLUMNS:
            return f"{value:.2f}%"

        # Kelly columns: 2 decimal places with % symbol
        if column_name in KELLY_COLUMNS:
            return f"{value:.2f}%"

        # Dollar columns: currency format with commas
        if column_name in DOLLAR_COLUMNS:
            return f"${value:,.2f}"

        # Default formatting for other floats
        if isinstance(value, float):
            return f"{value:.2f}"
        elif isinstance(value, int):
            return str(value)
        else:
            return str(value)

    def _style_cell(
        self, item: QTableWidgetItem, value, column_name: str, is_first_column: bool = False
    ) -> None:
        """Apply gradient styling to a cell based on column value range.

        Args:
            item: The QTableWidgetItem to style.
            value: The numeric value (or None).
            column_name: The column name.
            is_first_column: Whether this is the first (label) column.
        """
        # First column gets no gradient styling
        if is_first_column:
            return

        # Convert value to float if numeric
        numeric_value = None
        if isinstance(value, (int, float)) and not (isinstance(value, float) and math.isnan(value)):
            numeric_value = float(value)

        # Get gradient colors
        bg_color, text_color = self._gradient_styler.get_cell_colors(column_name, numeric_value)

        # Apply colors
        item.setBackground(QBrush(bg_color))
        item.setForeground(QBrush(text_color))

    def _highlight_optimal_row(self, table: QTableWidget, columns: list[str]) -> None:
        """Highlight the row with the best EG% value.

        Args:
            table: The QTableWidget to modify.
            columns: List of column names.
        """
        # Find EG % column index
        eg_col_idx = None
        for idx, col in enumerate(columns):
            if col == "EG %":
                eg_col_idx = idx
                break

        if eg_col_idx is None:
            return  # No EG % column in this table

        # Find row with highest EG%
        max_eg = float("-inf")
        max_row = -1

        for row in range(table.rowCount()):
            item = table.item(row, eg_col_idx)
            if item and item.text() not in ("-", ""):
                try:
                    # Remove % symbol if present and convert to float
                    text = item.text().replace("%", "")
                    val = float(text)
                    if val > max_eg:
                        max_eg = val
                        max_row = row
                except ValueError:
                    continue

        # Apply optimal row styling (only if we found a valid max)
        if max_row >= 0 and max_eg > float("-inf"):
            for col in range(table.columnCount()):
                item = table.item(max_row, col)
                if item:
                    # Apply subtle cyan background to entire row
                    # Only if cell doesn't already have positive styling
                    current_bg = item.background().color()
                    if current_bg.alpha() == 0:  # No existing background
                        item.setBackground(QBrush(ROW_OPTIMAL_BG))


    def _table_to_dataframe(self, table: QTableWidget) -> Optional[pd.DataFrame]:
        """Convert a QTableWidget to a pandas DataFrame.

        Args:
            table: The QTableWidget to convert.

        Returns:
            DataFrame with table contents, or None if table is empty.
        """
        row_count = table.rowCount()
        col_count = table.columnCount()

        if row_count == 0 or col_count == 0:
            return None

        # Get column headers
        headers = []
        for col_idx in range(col_count):
            header_item = table.horizontalHeaderItem(col_idx)
            headers.append(header_item.text() if header_item else f"Column {col_idx}")

        # Skip "Select" column if present (it contains radio buttons, not data)
        start_col = 1 if headers and headers[0] == "Select" else 0
        headers = headers[start_col:]

        # Get data
        data = []
        for row_idx in range(row_count):
            row_data = []
            for col_idx in range(start_col, col_count):
                item = table.item(row_idx, col_idx)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        return pd.DataFrame(data, columns=headers)

    def _on_export_clicked(self) -> None:
        """Handle export button click - export all tables to CSV or Excel."""
        from datetime import datetime
        
        # Collect all tables with their titles
        tables_data = [
            ("MAE Before Win", self._mae_table),
            ("MFE Before Loss", self._mfe_table),
            ("Stop Loss", self._stop_loss_table),
            ("Offset", self._offset_table),
            ("Scaling", self._scaling_table),
            ("Cover", self._cover_table),
            ("Profit Chance", self._profit_chance_table),
            ("Loss Chance", self._loss_chance_table),
        ]

        # Check if there's any data to export
        has_data = any(table.rowCount() > 0 for _, table in tables_data)
        if not has_data:
            QMessageBox.information(self, "Export", "No data to export.")
            return

        # Generate suggested filename with user's home directory as default
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_dir = Path.home()
        suggested_path = default_dir / f"lumen_statistics_{timestamp}.csv"

        # Show save dialog with CSV and Excel options
        path_str, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Statistics",
            str(suggested_path),
            "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*)",
        )

        if not path_str:
            return  # User cancelled

        path = Path(path_str)

        # Determine format based on extension or selected filter
        is_excel = path.suffix.lower() == ".xlsx" or "Excel" in selected_filter

        # Ensure correct extension
        if is_excel and path.suffix.lower() != ".xlsx":
            path = path.with_suffix(".xlsx")
        elif not is_excel and path.suffix.lower() != ".csv":
            path = path.with_suffix(".csv")

        try:
            if is_excel:
                # Export each table to a separate sheet
                with pd.ExcelWriter(path, engine="openpyxl") as writer:
                    for title, table in tables_data:
                        if table.rowCount() > 0:
                            df = self._table_to_dataframe(table)
                            if df is not None and not df.empty:
                                # Clean sheet name (Excel has restrictions)
                                sheet_name = title.replace("/", "-")[:31]
                                df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                # Export all tables to a single CSV, writing each table separately
                with open(path, "w", newline="", encoding="utf-8") as f:
                    first_table = True
                    for title, table in tables_data:
                        if table.rowCount() > 0:
                            df = self._table_to_dataframe(table)
                            if df is not None and not df.empty:
                                # Add blank line between tables (not before first)
                                if not first_table:
                                    f.write("\n")
                                first_table = False
                                
                                # Write section header
                                f.write(f"=== {title} ===\n")
                                
                                # Write table data
                                df.to_csv(f, index=False)

            QMessageBox.information(
                self, "Export Complete", f"Statistics exported to:\n{path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export:\n{e}")
