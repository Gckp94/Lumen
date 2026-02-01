"""Filter Threshold Analysis tab for what-if analysis of filter values."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.parameter_sensitivity import (
    ThresholdAnalysisResult,
    ThresholdAnalysisWorker,
)
from src.ui.components.no_scroll_widgets import NoScrollDoubleSpinBox

if TYPE_CHECKING:
    from src.core.app_state import AppState

logger = logging.getLogger(__name__)


# Color constants for the dark theme
COLORS = {
    "bg_primary": "#0d0d0f",
    "bg_secondary": "#131316",
    "bg_tertiary": "#18181b",
    "bg_elevated": "#222228",
    "row_current_bg": "#1a1814",
    "row_current_border": "#3d3425",
    "row_current_accent": "#c9a227",
    "delta_positive": "#22c55e",
    "delta_negative": "#ef4444",
    "text_primary": "#e4e4e7",
    "text_secondary": "#71717a",
    "text_muted": "#52525b",
    "border_subtle": "#27272a",
}

# Gradient color constants (matching Statistics Tab)
GRADIENT_LOW = QColor(255, 71, 87, 45)      # Coral-red (low values)
GRADIENT_MID = QColor(148, 148, 168, 25)    # Neutral gray (middle values)
GRADIENT_HIGH = QColor(0, 255, 180, 45)     # Teal-green (high values)

TEXT_LOW = QColor("#ff9090")     # Soft red text
TEXT_MID = QColor("#F4F4F8")     # Neutral text
TEXT_HIGH = QColor("#7DFFCC")    # Soft teal text


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
    invert: bool = False,
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


class ParameterSensitivityTab(QWidget):
    """Tab for filter threshold analysis.

    Allows users to see how trading metrics change when varying
    a single filter threshold up or down.
    """

    def __init__(self, app_state: AppState) -> None:
        """Initialize the tab.

        Args:
            app_state: Application state for accessing data and filters.
        """
        super().__init__()
        self._app_state = app_state
        self._worker: ThresholdAnalysisWorker | None = None
        self._result: ThresholdAnalysisResult | None = None
        self._current_filter_index: int = -1

        self._setup_ui()
        self._connect_signals()
        self._populate_filter_dropdown()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create splitter for sidebar and main area
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Sidebar
        sidebar = self._create_sidebar()
        splitter.addWidget(sidebar)

        # Main table area
        main_area = self._create_main_area()
        splitter.addWidget(main_area)

        # Set initial splitter sizes (sidebar: 280px, main: stretch)
        splitter.setSizes([280, 800])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

    def _create_sidebar(self) -> QWidget:
        """Create the sidebar with controls."""
        sidebar = QFrame()
        sidebar.setObjectName("threshold-sidebar")
        sidebar.setStyleSheet(f"""
            QFrame#threshold-sidebar {{
                background-color: {COLORS["bg_secondary"]};
                border-right: 1px solid {COLORS["border_subtle"]};
            }}
        """)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(20)

        # Filter selector section
        filter_section = QVBoxLayout()
        filter_section.setSpacing(8)

        filter_label = QLabel("FILTER")
        filter_label.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1px;
            color: {COLORS["text_secondary"]};
        """)
        filter_section.addWidget(filter_label)

        self._filter_combo = QComboBox()
        self._filter_combo.setPlaceholderText("Select a filter...")
        self._filter_combo.setMaxVisibleItems(15)
        self._filter_combo.setMinimumWidth(200)
        self._filter_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS["bg_tertiary"]};
                color: {COLORS["text_primary"]};
                font-size: 13px;
                border: 1px solid {COLORS["border_subtle"]};
                border-radius: 6px;
                padding: 10px 12px;
                min-height: 20px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
                subcontrol-origin: padding;
                subcontrol-position: center right;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {COLORS["text_secondary"]};
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS["bg_tertiary"]};
                color: {COLORS["text_primary"]};
                selection-background-color: {COLORS["row_current_bg"]};
                border: 1px solid {COLORS["border_subtle"]};
                padding: 4px;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px 12px;
                min-height: 24px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {COLORS["bg_elevated"]};
            }}
        """)
        filter_section.addWidget(self._filter_combo)
        layout.addLayout(filter_section)

        # Bound toggle section
        bound_section = QVBoxLayout()
        bound_section.setSpacing(8)

        bound_label = QLabel("VARY BOUND")
        bound_label.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1px;
            color: {COLORS["text_secondary"]};
        """)
        bound_section.addWidget(bound_label)

        self._bound_container = QFrame()
        self._bound_container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["bg_tertiary"]};
                border-radius: 6px;
                padding: 3px;
            }}
        """)
        bound_layout = QHBoxLayout(self._bound_container)
        bound_layout.setContentsMargins(3, 3, 3, 3)
        bound_layout.setSpacing(2)

        self._bound_group = QButtonGroup(self)
        self._min_radio = QRadioButton("Min")
        self._max_radio = QRadioButton("Max")
        self._min_radio.setChecked(True)

        for radio in [self._min_radio, self._max_radio]:
            radio.setStyleSheet(f"""
                QRadioButton {{
                    padding: 8px 20px;
                    border-radius: 4px;
                    color: {COLORS["text_secondary"]};
                    font-size: 13px;
                    font-weight: 600;
                    min-width: 50px;
                }}
                QRadioButton:checked {{
                    background-color: {COLORS["bg_elevated"]};
                    color: {COLORS["text_primary"]};
                }}
                QRadioButton::indicator {{
                    width: 0;
                    height: 0;
                }}
            """)
            self._bound_group.addButton(radio)
            bound_layout.addWidget(radio)

        bound_section.addWidget(self._bound_container)
        self._bound_container.setVisible(False)  # Hidden until dual-bound filter selected
        layout.addLayout(bound_section)

        # Step size section
        step_section = QVBoxLayout()
        step_section.setSpacing(8)

        step_label = QLabel("STEP SIZE")
        step_label.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1px;
            color: {COLORS["text_secondary"]};
        """)
        step_section.addWidget(step_label)

        self._step_spin = NoScrollDoubleSpinBox()
        self._step_spin.setRange(0.01, 10000)
        self._step_spin.setValue(1.0)
        self._step_spin.setDecimals(2)
        self._step_spin.setStyleSheet(f"""
            QDoubleSpinBox {{
                background-color: {COLORS["bg_tertiary"]};
                border: 1px solid {COLORS["border_subtle"]};
                border-radius: 6px;
                padding: 10px 12px;
                color: {COLORS["text_primary"]};
                font-family: "Azeret Mono";
                font-size: 13px;
            }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                background-color: {COLORS["bg_elevated"]};
                border: none;
                width: 24px;
            }}
        """)
        step_section.addWidget(self._step_spin)
        layout.addLayout(step_section)

        # Current value display
        current_section = QVBoxLayout()
        current_section.setSpacing(8)

        current_label = QLabel("CURRENT THRESHOLD")
        current_label.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1px;
            color: {COLORS["text_secondary"]};
        """)
        current_section.addWidget(current_label)

        self._current_frame = QFrame()
        self._current_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["row_current_bg"]};
                border: 1px solid {COLORS["row_current_border"]};
                border-radius: 6px;
                padding: 12px;
            }}
        """)
        current_inner = QHBoxLayout(self._current_frame)
        current_inner.setContentsMargins(12, 8, 12, 8)

        self._current_label = QLabel("Select filter")
        self._current_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        current_inner.addWidget(self._current_label)

        current_inner.addStretch()

        self._current_value = QLabel("")
        self._current_value.setStyleSheet(f"""
            font-family: "Azeret Mono";
            font-size: 15px;
            font-weight: 600;
            color: {COLORS["row_current_accent"]};
        """)
        current_inner.addWidget(self._current_value)

        current_section.addWidget(self._current_frame)
        layout.addLayout(current_section)

        # Run button
        self._run_btn = QPushButton("Analyze")
        self._run_btn.setEnabled(False)
        self._run_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["row_current_accent"]};
                color: {COLORS["bg_primary"]};
                border: none;
                border-radius: 6px;
                padding: 12px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #d4ad2f;
            }}
            QPushButton:disabled {{
                background-color: {COLORS["bg_tertiary"]};
                color: {COLORS["text_muted"]};
            }}
        """)
        layout.addWidget(self._run_btn)

        # Progress bar (hidden by default)
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS["bg_tertiary"]};
                border: none;
                border-radius: 4px;
                height: 6px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS["row_current_accent"]};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self._progress)

        layout.addStretch()

        # Empty state message
        self._empty_label = QLabel("Add filters in Feature Explorer\nto analyze thresholds")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(f"""
            color: {COLORS["text_muted"]};
            font-size: 12px;
        """)
        self._empty_label.setVisible(False)
        layout.addWidget(self._empty_label)

        return sidebar

    def _create_main_area(self) -> QWidget:
        """Create the main table area."""
        main = QFrame()
        main.setStyleSheet(f"background-color: {COLORS['bg_primary']};")

        layout = QVBoxLayout(main)
        layout.setContentsMargins(16, 16, 16, 16)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(10)
        self._table.setHorizontalHeaderLabels(
            [
                "Threshold",
                "# Trades",
                "EV %",
                "Win %",
                "Med Win %",
                "Profit Ratio",
                "Edge %",
                "EG %",
                "Kelly %",
                "Max Loss %",
            ]
        )

        # Style the table
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS["bg_secondary"]};
                border: 1px solid {COLORS["border_subtle"]};
                border-radius: 8px;
                gridline-color: {COLORS["border_subtle"]};
                font-family: "Azeret Mono";
                font-size: 12px;
                color: {COLORS["text_primary"]};
            }}
            QTableWidget::item {{
                padding: 10px 16px;
                border-bottom: 1px solid {COLORS["border_subtle"]};
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS["bg_elevated"]};
            }}
            QHeaderView::section {{
                background-color: {COLORS["bg_tertiary"]};
                color: {COLORS["text_secondary"]};
                font-family: "Geist";
                font-size: 10px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1px;
                padding: 12px 16px;
                border: none;
                border-bottom: 1px solid {COLORS["border_subtle"]};
            }}
        """)

        self._table.setAlternatingRowColors(False)  # Disabled - using gradient colors
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setWordWrap(True)  # Enable word wrap for multi-line cells

        # Set row height for two-line content
        self._table.verticalHeader().setDefaultSectionSize(52)

        # Set column widths
        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        # Disable text eliding
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        for i in range(10):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self._table)

        return main

    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        self._filter_combo.currentIndexChanged.connect(self._on_filter_selected)
        self._min_radio.toggled.connect(self._on_bound_changed)
        self._step_spin.valueChanged.connect(self._on_step_changed)
        self._run_btn.clicked.connect(self._on_run_clicked)

        # App state signals
        self._app_state.filters_changed.connect(self._populate_filter_dropdown)
        self._app_state.data_loaded.connect(self._populate_filter_dropdown)
        self._app_state.adjustment_params_changed.connect(self._on_params_changed)

    def _populate_filter_dropdown(self) -> None:
        """Populate the filter dropdown with current filters."""
        self._filter_combo.blockSignals(True)
        self._filter_combo.clear()
        filters = self._app_state.filters or []
        

        if not filters:
            self._filter_combo.blockSignals(False)
            self._empty_label.setVisible(True)
            self._run_btn.setEnabled(False)
            return

        self._empty_label.setVisible(False)

        for f in filters:
            # Format: "Column > value" or "Column < value" or "Column: min - max"
            if f.min_val is not None and f.max_val is not None:
                label = f"{f.column}: {f.min_val:.2f} - {f.max_val:.2f}"
            elif f.min_val is not None:
                label = f"{f.column} > {f.min_val:.2f}"
            else:
                label = f"{f.column} < {f.max_val:.2f}"
            self._filter_combo.addItem(label)

        # Reset to placeholder (index -1) so user can see prompt
        self._filter_combo.setCurrentIndex(-1)
        self._filter_combo.blockSignals(False)
        

    def _on_filter_selected(self, index: int) -> None:
        """Handle filter selection change."""
        filters = self._app_state.filters or []

        if index < 0 or index >= len(filters):
            self._current_filter_index = -1
            self._run_btn.setEnabled(False)
            self._bound_container.setVisible(False)
            return

        self._current_filter_index = index
        selected_filter = filters[index]

        # Show bound toggle only for dual-bound filters
        has_both_bounds = (
            selected_filter.min_val is not None and selected_filter.max_val is not None
        )
        self._bound_container.setVisible(has_both_bounds)

        # Update current value display
        if self._min_radio.isChecked() or not has_both_bounds:
            bound = "min"
            value = selected_filter.min_val
        else:
            bound = "max"
            value = selected_filter.max_val

        self._update_current_display(selected_filter.column, bound, value)
        self._auto_calculate_step_size(value)
        self._run_btn.setEnabled(True)

    def _on_bound_changed(self, checked: bool) -> None:
        """Handle bound toggle change."""
        if self._current_filter_index < 0:
            return

        filters = self._app_state.filters or []
        if self._current_filter_index >= len(filters):
            return

        selected_filter = filters[self._current_filter_index]
        bound = "min" if self._min_radio.isChecked() else "max"
        value = selected_filter.min_val if bound == "min" else selected_filter.max_val

        self._update_current_display(selected_filter.column, bound, value)
        self._auto_calculate_step_size(value)

    def _on_step_changed(self, value: float) -> None:
        """Handle step size change."""
        pass  # Just triggers re-analysis on next run

    def _on_params_changed(self) -> None:
        """Handle adjustment params change - clear results."""
        self._result = None
        self._table.setRowCount(0)

    def _update_current_display(self, column: str, bound: str, value: float | None) -> None:
        """Update the current threshold display."""
        if value is None:
            self._current_label.setText(column)
            self._current_value.setText("—")
        else:
            op = ">" if bound == "min" else "<"
            self._current_label.setText(f"{column} {op}")
            self._current_value.setText(f"{value:.2f}")

    def _auto_calculate_step_size(self, value: float | None) -> None:
        """Auto-calculate a sensible step size based on value magnitude."""
        if value is None:
            self._step_spin.setValue(1.0)
            return

        abs_val = abs(value)
        if abs_val < 1:
            step = 0.1
        elif abs_val < 10:
            step = 1
        elif abs_val < 100:
            step = 5
        elif abs_val < 1000:
            step = 50
        else:
            step = 100

        self._step_spin.setValue(step)

    def _on_run_clicked(self) -> None:
        """Run the threshold analysis."""
        if self._current_filter_index < 0:
            return

        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()

        # Get parameters
        vary_bound = "min" if self._min_radio.isChecked() else "max"
        step_size = self._step_spin.value()

        # Validate we have required data
        if self._app_state.baseline_df is None:
            logger.warning("No baseline data available")
            return
        if self._app_state.column_mapping is None:
            logger.warning("No column mapping available")
            return
        if not self._app_state.filters:
            logger.warning("No filters available")
            return

        # Get adjustment params (use defaults if not set)
        from src.core.models import AdjustmentParams

        adjustment_params = self._app_state.adjustment_params or AdjustmentParams()

        # Show progress
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._run_btn.setEnabled(False)

        # Use filtered_df as baseline to respect date/time range filters from Feature Explorer
        # filtered_df already has: date range + time range + feature filters + first trigger applied
        # This ensures the baseline row matches Feature Explorer's metrics exactly
        source_df = (
            self._app_state.filtered_df
            if self._app_state.filtered_df is not None
            else self._app_state.baseline_df
        )

        # Start worker
        # Note: first_trigger_enabled=False since filtered_df already has first trigger applied
        self._worker = ThresholdAnalysisWorker(
            baseline_df=source_df,
            column_mapping=self._app_state.column_mapping,
            active_filters=self._app_state.filters,
            adjustment_params=adjustment_params,
            filter_index=self._current_filter_index,
            vary_bound=vary_bound,
            step_size=step_size,
            first_trigger_enabled=False,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.completed.connect(self._on_completed)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, value: int) -> None:
        """Handle progress update."""
        self._progress.setValue(value)

    def _on_completed(self, result: ThresholdAnalysisResult) -> None:
        """Handle analysis completion."""
        self._result = result
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)
        self._display_results(result)

    def _on_error(self, message: str) -> None:
        """Handle analysis error."""
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)
        logger.error("Threshold analysis error: %s", message)

    def _display_results(self, result: ThresholdAnalysisResult) -> None:
        """Display analysis results in the table."""
        self._table.setRowCount(len(result.rows))

        # Get baseline values for delta calculation
        baseline_row = result.rows[result.current_index]

        # Compute column ranges for gradient coloring
        column_ranges: dict[str, tuple[float, float]] = {}
        
        # Collect all values per column
        num_trades_vals = [r.num_trades for r in result.rows]
        ev_vals = [r.ev_pct for r in result.rows if r.ev_pct is not None]
        win_vals = [r.win_pct for r in result.rows if r.win_pct is not None]
        med_win_vals = [r.median_winner_pct for r in result.rows if r.median_winner_pct is not None]
        profit_vals = [r.profit_ratio for r in result.rows if r.profit_ratio is not None]
        edge_vals = [r.edge_pct for r in result.rows if r.edge_pct is not None]
        eg_vals = [r.eg_pct for r in result.rows if r.eg_pct is not None]
        kelly_vals = [r.kelly_pct for r in result.rows if r.kelly_pct is not None]
        max_loss_vals = [r.max_loss_pct for r in result.rows if r.max_loss_pct is not None]

        if num_trades_vals:
            column_ranges["# Trades"] = (min(num_trades_vals), max(num_trades_vals))
        if ev_vals:
            column_ranges["EV %"] = (min(ev_vals), max(ev_vals))
        if win_vals:
            column_ranges["Win %"] = (min(win_vals), max(win_vals))
        if med_win_vals:
            column_ranges["Med Win %"] = (min(med_win_vals), max(med_win_vals))
        if profit_vals:
            column_ranges["Profit Ratio"] = (min(profit_vals), max(profit_vals))
        if edge_vals:
            column_ranges["Edge %"] = (min(edge_vals), max(edge_vals))
        if eg_vals:
            column_ranges["EG %"] = (min(eg_vals), max(eg_vals))
        if kelly_vals:
            column_ranges["Kelly %"] = (min(kelly_vals), max(kelly_vals))
        if max_loss_vals:
            column_ranges["Max Loss %"] = (min(max_loss_vals), max(max_loss_vals))

        for row_idx, row in enumerate(result.rows):
            is_current = row_idx == result.current_index

            # Column 0: Threshold (no gradient)
            threshold_item = self._create_cell(
                f"{row.threshold:.2f}",
                is_current=is_current,
                show_marker=is_current,
            )
            self._table.setItem(row_idx, 0, threshold_item)

            # Column 1: # Trades (gradient: higher is better)
            trades_delta = None if is_current else (row.num_trades - baseline_row.num_trades)
            self._table.setItem(
                row_idx,
                1,
                self._create_cell(
                    str(row.num_trades),
                    delta=trades_delta,
                    is_current=is_current,
                    invert_delta=True,
                    gradient_range=column_ranges.get("# Trades"),
                    gradient_value=float(row.num_trades),
                ),
            )

            # Column 2: EV %
            self._table.setItem(
                row_idx,
                2,
                self._create_metric_cell(
                    row.ev_pct, baseline_row.ev_pct, is_current, "pct",
                    gradient_range=column_ranges.get("EV %"),
                ),
            )

            # Column 3: Win %
            self._table.setItem(
                row_idx,
                3,
                self._create_metric_cell(
                    row.win_pct, baseline_row.win_pct, is_current, "pct",
                    gradient_range=column_ranges.get("Win %"),
                ),
            )

            # Column 4: Median Winner %
            self._table.setItem(
                row_idx,
                4,
                self._create_metric_cell(
                    row.median_winner_pct, baseline_row.median_winner_pct, is_current, "pct",
                    gradient_range=column_ranges.get("Med Win %"),
                ),
            )

            # Column 5: Profit Ratio
            self._table.setItem(
                row_idx,
                5,
                self._create_metric_cell(
                    row.profit_ratio, baseline_row.profit_ratio, is_current, "ratio",
                    gradient_range=column_ranges.get("Profit Ratio"),
                ),
            )

            # Column 6: Edge %
            self._table.setItem(
                row_idx,
                6,
                self._create_metric_cell(
                    row.edge_pct, baseline_row.edge_pct, is_current, "pct",
                    gradient_range=column_ranges.get("Edge %"),
                ),
            )

            # Column 7: EG %
            self._table.setItem(
                row_idx,
                7,
                self._create_metric_cell(
                    row.eg_pct, baseline_row.eg_pct, is_current, "pct",
                    gradient_range=column_ranges.get("EG %"),
                ),
            )

            # Column 8: Kelly %
            self._table.setItem(
                row_idx,
                8,
                self._create_metric_cell(
                    row.kelly_pct, baseline_row.kelly_pct, is_current, "pct",
                    gradient_range=column_ranges.get("Kelly %"),
                ),
            )

            # Column 9: Max Loss % (lower is better, so invert gradient)
            self._table.setItem(
                row_idx,
                9,
                self._create_metric_cell(
                    row.max_loss_pct, baseline_row.max_loss_pct, is_current, "pct",
                    invert=True,
                    gradient_range=column_ranges.get("Max Loss %"),
                    gradient_invert=True,
                ),
            )

    def _create_cell(
        self,
        text: str,
        delta: float | None = None,
        is_current: bool = False,
        show_marker: bool = False,
        invert_delta: bool = False,
        gradient_range: tuple[float, float] | None = None,
        gradient_value: float | None = None,
        gradient_invert: bool = False,
    ) -> QTableWidgetItem:
        """Create a styled table cell with optional gradient background."""
        display_text = text
        if show_marker:
            display_text = f"● {text}"

        if delta is not None and not is_current:
            sign = "+" if delta > 0 else ""
            display_text = f"{text}\n({sign}{delta:.0f})"
        elif is_current:
            display_text = f"{text}\n—"

        item = QTableWidgetItem(display_text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        if is_current:
            item.setBackground(QColor(COLORS["row_current_bg"]))
            if show_marker:
                item.setForeground(QColor(COLORS["row_current_accent"]))
        elif gradient_range is not None and gradient_value is not None:
            # Apply gradient coloring
            min_val, max_val = gradient_range
            bg_color, text_color = calculate_gradient_colors(
                gradient_value, min_val, max_val, invert=gradient_invert
            )
            item.setBackground(bg_color)
            item.setForeground(text_color)
        elif delta is not None:
            # Color based on delta direction (text only)
            is_good = (delta > 0) if not invert_delta else (delta < 0)
            if is_good:
                item.setForeground(QColor(COLORS["delta_positive"]))
            elif delta != 0:
                item.setForeground(QColor(COLORS["delta_negative"]))

        return item

    def _create_metric_cell(
        self,
        value: float | None,
        baseline: float | None,
        is_current: bool,
        fmt: str = "pct",
        invert: bool = False,
        gradient_range: tuple[float, float] | None = None,
        gradient_invert: bool = False,
    ) -> QTableWidgetItem:
        """Create a metric cell with delta display and gradient coloring."""
        if value is None:
            item = QTableWidgetItem("—")
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item.setForeground(QColor(COLORS["text_muted"]))
            if is_current:
                item.setBackground(QColor(COLORS["row_current_bg"]))
            return item

        # Format value
        if fmt == "pct":
            text = f"{value:.2f}%"
        else:  # ratio
            text = f"{value:.2f}"

        # Calculate delta
        delta = None
        if baseline is not None and not is_current:
            delta = value - baseline

        # Build display text
        if is_current:
            display_text = f"{text}\n—"
        elif delta is not None:
            sign = "+" if delta > 0 else ""
            if fmt == "pct":
                display_text = f"{text}\n({sign}{delta:.2f})"
            else:
                display_text = f"{text}\n({sign}{delta:.2f})"
        else:
            display_text = text

        item = QTableWidgetItem(display_text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        if is_current:
            item.setBackground(QColor(COLORS["row_current_bg"]))
        elif gradient_range is not None:
            # Apply gradient coloring
            min_val, max_val = gradient_range
            bg_color, text_color = calculate_gradient_colors(
                value, min_val, max_val, invert=gradient_invert
            )
            item.setBackground(bg_color)
            item.setForeground(text_color)
        elif delta is not None:
            is_good = (delta > 0) if not invert else (delta < 0)
            if is_good:
                item.setForeground(QColor(COLORS["delta_positive"]))
            elif delta != 0:
                item.setForeground(QColor(COLORS["delta_negative"]))

        return item

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._worker is not None:
            # Disconnect signals first
            try:
                self._worker.progress.disconnect()
                self._worker.completed.disconnect()
                self._worker.error.disconnect()
            except (TypeError, RuntimeError):
                pass  # Already disconnected or worker deleted

            if self._worker.isRunning():
                self._worker.cancel()
                self._worker.wait()

            self._worker = None

