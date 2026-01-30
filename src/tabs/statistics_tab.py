"""Statistics tab with 5 analytical tables for trade analysis."""

import logging

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.app_state import AppState
from src.core.models import AdjustmentParams, TradingMetrics
from src.core.statistics import (
    calculate_mae_before_win,
    calculate_mfe_before_loss,
    calculate_offset_table,
    calculate_scaling_table,
    calculate_stop_loss_table,
)
from src.ui.constants import Colors, Fonts, Spacing

logger = logging.getLogger(__name__)


class StatisticsTab(QWidget):
    """Tab displaying 5 statistics tables as sub-tabs."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._app_state = app_state
        self._setup_ui()
        self._connect_signals()
        self._initialize_from_state()

    def _setup_ui(self) -> None:
        """Set up the tab UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Sub-tabs using QTabWidget
        self._tab_widget = QTabWidget()
        self._style_tab_widget()

        # Create 5 sub-tabs
        self._mae_table = self._create_table()
        self._mfe_table = self._create_table()
        self._stop_loss_table = self._create_table()
        self._offset_table = self._create_table()
        self._scaling_widget = self._create_scaling_widget()

        self._tab_widget.addTab(self._mae_table, "MAE Before Win")
        self._tab_widget.addTab(self._mfe_table, "MFE Before Loss")
        self._tab_widget.addTab(self._stop_loss_table, "Stop Loss")
        self._tab_widget.addTab(self._offset_table, "Offset")
        self._tab_widget.addTab(self._scaling_widget, "Scaling")

        layout.addWidget(self._tab_widget)

    def _style_tab_widget(self) -> None:
        """Apply Observatory theme styling to tab widget."""
        self._tab_widget.setStyleSheet(f"""
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
        """)

    def _create_table(self) -> QTableWidget:
        """Create a styled table widget."""
        table = QTableWidget()
        table.setStyleSheet(f"""
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
        """)
        return table

    def _create_scaling_widget(self) -> QWidget:
        """Create scaling sub-tab with spinbox control."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # Scale Out control row
        control_row = QHBoxLayout()
        control_row.setSpacing(Spacing.SM)

        label = QLabel("Scale Out:")
        label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: 13px;
            }}
        """)
        control_row.addWidget(label)

        self._scale_out_spin = QSpinBox()
        self._scale_out_spin.setRange(10, 90)
        self._scale_out_spin.setValue(50)
        self._scale_out_spin.setSingleStep(10)
        self._scale_out_spin.setSuffix("%")
        self._scale_out_spin.setStyleSheet(f"""
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
        """)
        control_row.addWidget(self._scale_out_spin)
        control_row.addStretch()

        layout.addLayout(control_row)

        # Scaling table
        self._scaling_table = self._create_table()
        layout.addWidget(self._scaling_table)

        return widget

    def _connect_signals(self) -> None:
        """Connect app state signals."""
        # Connect to baseline calculated signal for initial data display
        self._app_state.baseline_calculated.connect(self._on_baseline_calculated)

        # Connect to filtered data for when filters are applied
        self._app_state.filtered_data_updated.connect(self._on_filtered_data_updated)

        # Connect to adjustment params changes (stop loss, efficiency)
        self._app_state.adjustment_params_changed.connect(self._on_adjustment_params_changed)

        # Connect scale out spinbox to refresh scaling table
        self._scale_out_spin.valueChanged.connect(self._on_scale_out_changed)

    def _initialize_from_state(self) -> None:
        """Populate tables if data already exists in state.

        Uses filtered_df if available, otherwise falls back to baseline_df.
        This ensures tables display data immediately when tab is opened.
        """
        if not self._app_state.column_mapping:
            return

        # Prefer filtered data if available, otherwise use baseline
        if self._app_state.filtered_df is not None and not self._app_state.filtered_df.empty:
            self._update_all_tables(self._app_state.filtered_df)
        elif self._app_state.baseline_df is not None and not self._app_state.baseline_df.empty:
            self._update_all_tables(self._app_state.baseline_df)

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

        self._update_all_tables(self._app_state.baseline_df)

    def _on_filtered_data_updated(self, df: pd.DataFrame) -> None:
        """Handle filtered data update.

        Args:
            df: Updated filtered DataFrame.
        """
        if not self._app_state.column_mapping:
            return

        self._update_all_tables(df)

    def _on_adjustment_params_changed(self, params: AdjustmentParams) -> None:
        """Handle adjustment parameters changed.

        Refreshes stop loss and offset tables which depend on these params.

        Args:
            params: New adjustment parameters.
        """
        self._refresh_all_tables()

    def _on_scale_out_changed(self, value: int) -> None:
        """Handle scale out spinbox value change.

        Args:
            value: New scale out percentage (10-90).
        """
        self._refresh_scaling_table()

    def _get_current_df(self) -> pd.DataFrame | None:
        """Get the current DataFrame to use for calculations.

        Prefers filtered data, falls back to baseline.

        Returns:
            Current DataFrame or None if no data available.
        """
        if self._app_state.filtered_df is not None and not self._app_state.filtered_df.empty:
            return self._app_state.filtered_df
        return self._app_state.baseline_df

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

        # Calculate and populate Stop Loss table
        # Efficiency is stored as percentage (5 = 5%), but function expects 0-1
        try:
            efficiency = params.efficiency / 100.0 if params.efficiency > 1 else params.efficiency
            stop_loss_df = calculate_stop_loss_table(df, mapping, efficiency)
            self._populate_table(self._stop_loss_table, stop_loss_df)
        except Exception as e:
            logger.warning(f"Error calculating Stop Loss table: {e}")
            self._stop_loss_table.setRowCount(0)

        # Calculate and populate Offset table
        try:
            offset_df = calculate_offset_table(df, mapping, params.stop_loss, efficiency)
            self._populate_table(self._offset_table, offset_df)
        except Exception as e:
            logger.warning(f"Error calculating Offset table: {e}")
            self._offset_table.setRowCount(0)

        # Calculate and populate Scaling table
        try:
            scale_out_pct = self._scale_out_spin.value() / 100.0
            scaling_df = calculate_scaling_table(df, mapping, scale_out_pct)
            self._populate_table(self._scaling_table, scaling_df)
        except Exception as e:
            logger.warning(f"Error calculating Scaling table: {e}")
            self._scaling_table.setRowCount(0)

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

        mapping = self._app_state.column_mapping

        try:
            scale_out_pct = self._scale_out_spin.value() / 100.0
            scaling_df = calculate_scaling_table(df, mapping, scale_out_pct)
            self._populate_table(self._scaling_table, scaling_df)
        except Exception as e:
            logger.warning(f"Error refreshing Scaling table: {e}")

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
        table.setHorizontalHeaderLabels(list(df.columns))

        # Populate cells
        for row_idx, (_, row) in enumerate(df.iterrows()):
            for col_idx, value in enumerate(row):
                item = self._create_table_item(value)
                table.setItem(row_idx, col_idx, item)

        # Resize columns to content
        header = table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

    def _create_table_item(self, value) -> QTableWidgetItem:
        """Create a formatted table item from a value.

        Args:
            value: The value to display (can be str, int, float, or None).

        Returns:
            Formatted QTableWidgetItem.
        """
        if value is None:
            text = "-"
        elif isinstance(value, float):
            # Format floats with 2 decimal places
            text = f"{value:.2f}"
        elif isinstance(value, int):
            text = str(value)
        else:
            text = str(value)

        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Make read-only

        # Right-align numeric values
        if isinstance(value, (int, float)) and value is not None:
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        else:
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        return item
