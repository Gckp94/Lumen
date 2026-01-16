"""BreakdownTab - Yearly and monthly performance breakdown charts."""

import logging

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.core.app_state import AppState
from src.core.breakdown import BreakdownCalculator
from src.core.models import MetricsUserInputs
from src.ui.components.vertical_bar_chart import VerticalBarChart
from src.ui.components.year_selector_tabs import YearSelectorTabs
from src.ui.constants import Colors, Fonts, Spacing

logger = logging.getLogger(__name__)


class BreakdownTab(QWidget):
    """Tab displaying yearly and monthly performance breakdown charts.

    Shows 6 yearly charts in a 2x3 grid and 8 monthly charts (for selected year)
    in a 2x4 grid. Charts are updated reactively when filtered data changes.
    """

    def __init__(self, app_state: AppState) -> None:
        """Initialize breakdown tab.

        Args:
            app_state: Shared application state.
        """
        super().__init__()
        self._app_state = app_state
        self._calculator = self._create_calculator()

        # Chart widgets - yearly (6 charts)
        self._yearly_charts: dict[str, VerticalBarChart] = {}

        # Chart widgets - monthly (8 charts)
        self._monthly_charts: dict[str, VerticalBarChart] = {}

        # Year selector for monthly section
        self._year_selector: YearSelectorTabs | None = None

        self._setup_ui()
        self._connect_signals()
        self._initialize_from_state()

    def _create_calculator(self) -> BreakdownCalculator:
        """Create a BreakdownCalculator with current user inputs.

        Returns:
            BreakdownCalculator configured with user's flat_stake and starting_capital.
        """
        inputs = self._app_state.metrics_user_inputs
        return BreakdownCalculator(
            stake=inputs.flat_stake,
            start_capital=inputs.starting_capital,
        )

    def _setup_ui(self) -> None:
        """Set up the UI layout with scroll area and sections."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll area for all content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet(
            f"""
            QScrollArea {{
                background-color: {Colors.BG_SURFACE};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {Colors.BG_SURFACE};
                width: 8px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background-color: {Colors.BG_BORDER};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {Colors.TEXT_SECONDARY};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar:horizontal {{
                background-color: {Colors.BG_SURFACE};
                height: 8px;
                margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {Colors.BG_BORDER};
                border-radius: 4px;
                min-width: 20px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {Colors.TEXT_SECONDARY};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0;
            }}
        """
        )

        # Content widget
        content_widget = QWidget()
        content_widget.setStyleSheet(f"background-color: {Colors.BG_SURFACE};")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        content_layout.setSpacing(Spacing.XL)

        # Add sections
        content_layout.addWidget(self._create_years_section())
        content_layout.addWidget(self._create_months_section())
        content_layout.addStretch()

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

    def _create_years_section(self) -> QWidget:
        """Create the yearly breakdown section with 6 charts in 2x3 grid.

        Returns:
            Widget containing the yearly section.
        """
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.MD)

        # Section header
        header = QLabel("Yearly Breakdown")
        header.setFont(QFont(Fonts.UI, 14, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(header)

        # Charts grid: 2 rows x 3 columns
        grid = QGridLayout()
        grid.setHorizontalSpacing(Spacing.XS)
        grid.setVerticalSpacing(Spacing.SM)

        # Define yearly charts
        yearly_chart_defs = [
            ("total_gain_pct", "Total Gain (%)"),
            ("total_flat_stake", "Flat Stake ($)"),
            ("max_dd_pct", "Max DD (%)"),
            ("max_dd_dollars", "Max DD ($)"),
            ("count", "Count"),
            ("win_rate", "Win Rate (%)"),
        ]

        for i, (key, title) in enumerate(yearly_chart_defs):
            chart = VerticalBarChart(title=title)
            self._yearly_charts[key] = chart
            row = i // 3  # 0, 0, 0, 1, 1, 1
            col = i % 3  # 0, 1, 2, 0, 1, 2
            grid.addWidget(chart, row, col)

        # Wrap grid in horizontal layout with stretch to prevent spreading
        grid_container = QHBoxLayout()
        grid_container.setContentsMargins(0, 0, 0, 0)
        grid_container.setSpacing(0)
        grid_container.addLayout(grid)
        grid_container.addStretch()

        layout.addLayout(grid_container)
        return section

    def _create_months_section(self) -> QWidget:
        """Create the monthly breakdown section with year tabs and 8 charts in 2x4 grid.

        Returns:
            Widget containing the monthly section.
        """
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.MD)

        # Header row with title and year selector
        header_row = QHBoxLayout()
        header_row.setSpacing(Spacing.MD)

        header = QLabel("Monthly Breakdown")
        header.setFont(QFont(Fonts.UI, 14, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        header_row.addWidget(header)

        self._year_selector = YearSelectorTabs()
        header_row.addWidget(self._year_selector)
        header_row.addStretch()

        layout.addLayout(header_row)

        # Charts grid: 2 rows x 4 columns
        grid = QGridLayout()
        grid.setHorizontalSpacing(Spacing.XS)
        grid.setVerticalSpacing(Spacing.SM)

        # Define monthly charts (8 charts)
        monthly_chart_defs = [
            ("total_gain_pct", "Total Gain (%)"),
            ("total_flat_stake", "Flat Stake ($)"),
            ("max_dd_pct", "Max DD (%)"),
            ("max_dd_dollars", "Max DD ($)"),
            ("count", "Count"),
            ("win_rate", "Win Rate (%)"),
            ("avg_winner_pct", "Avg Winner (%)"),
            ("avg_loser_pct", "Avg Loser (%)"),
        ]

        for i, (key, title) in enumerate(monthly_chart_defs):
            chart = VerticalBarChart(title=title)
            self._monthly_charts[key] = chart
            row = i // 4  # 0, 0, 0, 0, 1, 1, 1, 1
            col = i % 4  # 0, 1, 2, 3, 0, 1, 2, 3
            grid.addWidget(chart, row, col)

        # Wrap grid in horizontal layout with stretch to prevent spreading
        grid_container = QHBoxLayout()
        grid_container.setContentsMargins(0, 0, 0, 0)
        grid_container.setSpacing(0)
        grid_container.addLayout(grid)
        grid_container.addStretch()

        layout.addLayout(grid_container)
        return section

    def _connect_signals(self) -> None:
        """Connect to app_state and internal signals."""
        self._app_state.filtered_data_updated.connect(self._on_filtered_data_updated)
        self._app_state.metrics_user_inputs_changed.connect(self._on_metrics_user_inputs_changed)

        if self._year_selector:
            self._year_selector.year_changed.connect(self._on_year_changed)

    def _initialize_from_state(self) -> None:
        """Populate charts if data already exists in state."""
        if self._app_state.filtered_df is not None and self._app_state.column_mapping:
            self._on_filtered_data_updated(self._app_state.filtered_df)

    def _on_filtered_data_updated(self, df: pd.DataFrame) -> None:
        """Handle filtered data update.

        Args:
            df: Updated filtered DataFrame.
        """
        if df is None or df.empty or not self._app_state.column_mapping:
            self._clear_charts()
            return

        mapping = self._app_state.column_mapping
        date_col = mapping.date
        gain_col = mapping.gain_pct
        win_loss_col = mapping.win_loss

        # Update year selector with available years
        years = self._calculator.get_available_years(df, date_col)
        if self._year_selector:
            self._year_selector.set_years(years)

        # Update yearly charts
        self._update_yearly_charts(df, date_col, gain_col, win_loss_col)

        # Update monthly charts for selected year
        selected_year = self._year_selector.selected_year() if self._year_selector else None
        if selected_year:
            self._update_monthly_charts(df, selected_year, date_col, gain_col, win_loss_col)

    def _on_year_changed(self, year: int) -> None:
        """Handle year selection change.

        Args:
            year: Newly selected year.
        """
        if self._app_state.filtered_df is None or not self._app_state.column_mapping:
            return

        mapping = self._app_state.column_mapping
        self._update_monthly_charts(
            self._app_state.filtered_df,
            year,
            mapping.date,
            mapping.gain_pct,
            mapping.win_loss,
        )

    def _on_metrics_user_inputs_changed(self, inputs: MetricsUserInputs) -> None:
        """Handle metrics user inputs changed.

        Recreates the calculator with new values and refreshes charts.

        Args:
            inputs: New user inputs.
        """
        self._calculator = BreakdownCalculator(
            stake=inputs.flat_stake,
            start_capital=inputs.starting_capital,
        )
        self._refresh_charts()

    def _refresh_charts(self) -> None:
        """Refresh all charts with current data.

        Re-triggers the data update handler with current filtered data.
        """
        if self._app_state.filtered_df is not None:
            self._on_filtered_data_updated(self._app_state.filtered_df)

    def _update_yearly_charts(
        self,
        df: pd.DataFrame,
        date_col: str,
        gain_col: str,
        win_loss_col: str | None,
    ) -> None:
        """Update all 6 yearly charts with calculated metrics.

        Args:
            df: DataFrame with trade data.
            date_col: Column name for date.
            gain_col: Column name for gain percentage.
            win_loss_col: Column name for win/loss indicator.
        """
        yearly_data = self._calculator.calculate_yearly(df, date_col, gain_col, win_loss_col)

        if not yearly_data:
            self._clear_yearly_charts()
            return

        # Prepare data for each chart
        years = sorted(yearly_data.keys())

        # total_gain_pct
        data = [(y, yearly_data[y]["total_gain_pct"]) for y in years]
        self._yearly_charts["total_gain_pct"].set_data(data, is_percentage=True)

        # total_flat_stake
        data = [(y, yearly_data[y]["total_flat_stake"]) for y in years]
        self._yearly_charts["total_flat_stake"].set_data(data, is_currency=True)

        # max_dd_pct
        data = [(y, yearly_data[y]["max_dd_pct"]) for y in years]
        self._yearly_charts["max_dd_pct"].set_data(data, is_percentage=True)

        # max_dd_dollars
        data = [(y, yearly_data[y]["max_dd_dollars"]) for y in years]
        self._yearly_charts["max_dd_dollars"].set_data(data, is_currency=True)

        # count
        data = [(y, yearly_data[y]["count"]) for y in years]
        self._yearly_charts["count"].set_data(data)

        # win_rate
        data = [(y, yearly_data[y]["win_rate"]) for y in years]
        self._yearly_charts["win_rate"].set_data(data, is_percentage=True)

    def _update_monthly_charts(
        self,
        df: pd.DataFrame,
        year: int,
        date_col: str,
        gain_col: str,
        win_loss_col: str | None,
    ) -> None:
        """Update all 8 monthly charts for the selected year.

        Args:
            df: DataFrame with trade data.
            year: Year to calculate monthly breakdown for.
            date_col: Column name for date.
            gain_col: Column name for gain percentage.
            win_loss_col: Column name for win/loss indicator.
        """
        monthly_data = self._calculator.calculate_monthly(
            df, year, date_col, gain_col, win_loss_col
        )

        if not monthly_data:
            self._clear_monthly_charts()
            return

        # Month order for sorting
        month_order = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        months = [m for m in month_order if m in monthly_data]

        # total_gain_pct
        data = [(m, monthly_data[m]["total_gain_pct"]) for m in months]
        self._monthly_charts["total_gain_pct"].set_data(data, is_percentage=True)

        # total_flat_stake
        data = [(m, monthly_data[m]["total_flat_stake"]) for m in months]
        self._monthly_charts["total_flat_stake"].set_data(data, is_currency=True)

        # max_dd_pct
        data = [(m, monthly_data[m]["max_dd_pct"]) for m in months]
        self._monthly_charts["max_dd_pct"].set_data(data, is_percentage=True)

        # max_dd_dollars
        data = [(m, monthly_data[m]["max_dd_dollars"]) for m in months]
        self._monthly_charts["max_dd_dollars"].set_data(data, is_currency=True)

        # count
        data = [(m, monthly_data[m]["count"]) for m in months]
        self._monthly_charts["count"].set_data(data)

        # win_rate
        data = [(m, monthly_data[m]["win_rate"]) for m in months]
        self._monthly_charts["win_rate"].set_data(data, is_percentage=True)

        # avg_winner_pct
        data = [(m, monthly_data[m]["avg_winner_pct"]) for m in months]
        self._monthly_charts["avg_winner_pct"].set_data(data, is_percentage=True)

        # avg_loser_pct
        data = [(m, monthly_data[m]["avg_loser_pct"]) for m in months]
        self._monthly_charts["avg_loser_pct"].set_data(data, is_percentage=True)

    def _clear_charts(self) -> None:
        """Clear all chart data."""
        self._clear_yearly_charts()
        self._clear_monthly_charts()

    def _clear_yearly_charts(self) -> None:
        """Clear all yearly chart data."""
        for chart in self._yearly_charts.values():
            chart.set_data([])

    def _clear_monthly_charts(self) -> None:
        """Clear all monthly chart data."""
        for chart in self._monthly_charts.values():
            chart.set_data([])

    def cleanup(self) -> None:
        """Clean up resources before destruction."""
        try:
            self._app_state.filtered_data_updated.disconnect(self._on_filtered_data_updated)
        except (TypeError, RuntimeError):
            pass
        try:
            self._app_state.metrics_user_inputs_changed.disconnect(
                self._on_metrics_user_inputs_changed
            )
        except (TypeError, RuntimeError):
            pass
