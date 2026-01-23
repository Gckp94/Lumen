# src/tabs/portfolio_breakdown.py
"""Portfolio Breakdown Tab for yearly/monthly metrics visualization."""

import logging

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.portfolio_breakdown import PortfolioBreakdownCalculator
from src.ui.components.vertical_bar_chart import VerticalBarChart
from src.ui.components.year_selector_tabs import YearSelectorTabs
from src.ui.constants import Colors, Fonts, Spacing

logger = logging.getLogger(__name__)

# Chart metric definitions: (key, title, is_percentage, is_currency)
CHART_METRICS = [
    ("total_gain_pct", "Total Gain %", True, False),
    ("total_gain_dollars", "Total Gain $", False, True),
    ("account_growth_pct", "Account Growth %", True, False),
    ("max_dd_pct", "Max Drawdown %", True, False),
    ("max_dd_dollars", "Max Drawdown $", False, True),
    ("win_rate_pct", "Win Rate %", True, False),
    ("trade_count", "Number of Trades", False, False),
    ("dd_duration_days", "DD Duration (days)", False, False),
]


class PortfolioBreakdownTab(QWidget):
    """Tab displaying breakdown metrics for portfolio data."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the Portfolio Breakdown Tab."""
        super().__init__(parent)

        self._calculator = PortfolioBreakdownCalculator()
        self._baseline_data: pd.DataFrame | None = None
        self._combined_data: pd.DataFrame | None = None

        # Chart storage: key format is "{metric_key}_{portfolio}" e.g. "total_gain_pct_baseline"
        self._yearly_charts: dict[str, VerticalBarChart] = {}
        self._monthly_charts: dict[str, VerticalBarChart] = {}

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        layout.addWidget(self._create_toolbar())

        # Content area with scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet(f"background-color: {Colors.BG_SURFACE};")

        # Stacked widget for yearly/monthly views
        self._stacked = QStackedWidget()
        self._stacked.addWidget(self._create_yearly_view())
        self._stacked.addWidget(self._create_monthly_view())

        scroll.setWidget(self._stacked)
        layout.addWidget(scroll)

    def _create_toolbar(self) -> QWidget:
        """Create the toolbar with period tabs and visibility toggles."""
        toolbar = QWidget()
        toolbar.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_BASE};
                border-bottom: 1px solid {Colors.BG_BORDER};
            }}
        """)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        layout.setSpacing(Spacing.LG)

        # Period tabs (Yearly / Monthly)
        period_container = QWidget()
        period_container.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: 6px;
                border: none;
            }}
        """)
        period_layout = QHBoxLayout(period_container)
        period_layout.setContentsMargins(2, 2, 2, 2)
        period_layout.setSpacing(0)

        self._period_group = QButtonGroup(self)
        self._yearly_btn = self._create_period_button("Yearly", checked=True)
        self._monthly_btn = self._create_period_button("Monthly")
        self._period_group.addButton(self._yearly_btn, 0)
        self._period_group.addButton(self._monthly_btn, 1)

        period_layout.addWidget(self._yearly_btn)
        period_layout.addWidget(self._monthly_btn)
        layout.addWidget(period_container)

        # Divider
        layout.addWidget(self._create_divider())

        # Visibility toggles
        self._baseline_toggle = self._create_toggle_button("Baseline", Colors.SIGNAL_BLUE)
        self._combined_toggle = self._create_toggle_button("Combined", Colors.SIGNAL_CYAN)
        layout.addWidget(self._baseline_toggle)
        layout.addWidget(self._combined_toggle)

        # Divider
        layout.addWidget(self._create_divider())

        # Year selector (for monthly view)
        self._year_selector = YearSelectorTabs()
        self._year_selector.setVisible(False)  # Hidden by default (yearly view)
        layout.addWidget(self._year_selector)

        layout.addStretch()

        return toolbar

    def _create_period_button(self, text: str, checked: bool = False) -> QPushButton:
        """Create a period tab button."""
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: none;
                padding: {Spacing.SM}px {Spacing.LG}px;
                font-family: "{Fonts.UI}";
                font-size: 13px;
                font-weight: 500;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                color: {Colors.TEXT_PRIMARY};
            }}
            QPushButton:checked {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        return btn

    def _create_toggle_button(self, text: str, color: str) -> QPushButton:
        """Create a visibility toggle button."""
        btn = QPushButton(f"  {text}")
        btn.setCheckable(True)
        btn.setChecked(True)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BG_BORDER};
                padding: {Spacing.SM}px {Spacing.MD}px;
                font-family: "{Fonts.UI}";
                font-size: 12px;
                font-weight: 500;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                border-color: {Colors.TEXT_SECONDARY};
            }}
            QPushButton:checked {{
                border-color: {color};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        return btn

    def _create_divider(self) -> QWidget:
        """Create a vertical divider."""
        divider = QWidget()
        divider.setFixedSize(1, 24)
        divider.setStyleSheet(f"background-color: {Colors.BG_BORDER};")
        return divider

    def _create_yearly_view(self) -> QWidget:
        """Create the yearly charts view."""
        return self._create_charts_view(self._yearly_charts, "yearly")

    def _create_monthly_view(self) -> QWidget:
        """Create the monthly charts view."""
        return self._create_charts_view(self._monthly_charts, "monthly")

    def _create_charts_view(
        self, charts_dict: dict[str, VerticalBarChart], prefix: str
    ) -> QWidget:
        """Create a charts grid view.

        Args:
            charts_dict: Dict to store chart references.
            prefix: Prefix for chart keys.

        Returns:
            Widget containing the charts grid.
        """
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        layout.setSpacing(Spacing.LG)

        # 4 columns × 4 rows grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(Spacing.LG)
        grid.setVerticalSpacing(Spacing.LG)

        # Create charts: 8 metrics × 2 portfolios = 16 charts
        # Layout: [Metric1_Base, Metric1_Comb, Metric2_Base, Metric2_Comb] per row pair
        row = 0
        for i in range(0, len(CHART_METRICS), 2):
            metric1 = CHART_METRICS[i]
            metric2 = CHART_METRICS[i + 1] if i + 1 < len(CHART_METRICS) else None

            # Metric 1: Baseline and Combined
            chart1_base = self._create_chart_card(metric1, "baseline")
            chart1_comb = self._create_chart_card(metric1, "combined")
            charts_dict[f"{metric1[0]}_baseline"] = chart1_base
            charts_dict[f"{metric1[0]}_combined"] = chart1_comb
            grid.addWidget(chart1_base, row, 0)
            grid.addWidget(chart1_comb, row, 1)

            # Metric 2: Baseline and Combined
            if metric2:
                chart2_base = self._create_chart_card(metric2, "baseline")
                chart2_comb = self._create_chart_card(metric2, "combined")
                charts_dict[f"{metric2[0]}_baseline"] = chart2_base
                charts_dict[f"{metric2[0]}_combined"] = chart2_comb
                grid.addWidget(chart2_base, row, 2)
                grid.addWidget(chart2_comb, row, 3)

            row += 1

        layout.addLayout(grid)
        layout.addStretch()

        return view

    def _create_chart_card(
        self, metric: tuple[str, str, bool, bool], portfolio: str
    ) -> VerticalBarChart:
        """Create a chart card for a metric.

        Args:
            metric: Tuple of (key, title, is_percentage, is_currency).
            portfolio: Either "baseline" or "combined".

        Returns:
            VerticalBarChart widget.
        """
        key, title, is_pct, is_currency = metric
        badge = "BASE" if portfolio == "baseline" else "COMB"

        chart = VerticalBarChart(title=f"{title} ({badge})")
        return chart

    def _connect_signals(self) -> None:
        """Connect UI signals."""
        self._period_group.idClicked.connect(self._on_period_changed)
        self._baseline_toggle.toggled.connect(self._on_visibility_changed)
        self._combined_toggle.toggled.connect(self._on_visibility_changed)
        self._year_selector.year_changed.connect(self._on_year_changed)

    def _on_period_changed(self, index: int) -> None:
        """Handle period tab change."""
        self._stacked.setCurrentIndex(index)
        # Show/hide year selector based on period
        self._year_selector.setVisible(index == 1)  # Monthly view

    def _on_visibility_changed(self) -> None:
        """Handle visibility toggle change."""
        show_baseline = self._baseline_toggle.isChecked()
        show_combined = self._combined_toggle.isChecked()

        # Update chart visibility in both views
        for charts in (self._yearly_charts, self._monthly_charts):
            for key, chart in charts.items():
                if "_baseline" in key:
                    chart.setVisible(show_baseline)
                elif "_combined" in key:
                    chart.setVisible(show_combined)

    def _on_year_changed(self, year: int) -> None:
        """Handle year selection change."""
        self._refresh_monthly_charts()

    def on_portfolio_data_changed(self, data: dict[str, pd.DataFrame]) -> None:
        """Handle portfolio data update from Portfolio Overview.

        Args:
            data: Dict with "baseline" and/or "combined" DataFrames.
        """
        self._baseline_data = data.get("baseline")
        self._combined_data = data.get("combined")

        # Update available years
        years = set()
        if self._baseline_data is not None and not self._baseline_data.empty:
            years.update(self._calculator.get_available_years(self._baseline_data))
        if self._combined_data is not None and not self._combined_data.empty:
            years.update(self._calculator.get_available_years(self._combined_data))

        self._year_selector.set_years(sorted(years))

        # Refresh charts
        self._refresh_yearly_charts()
        self._refresh_monthly_charts()

    def _refresh_yearly_charts(self) -> None:
        """Refresh all yearly charts with current data."""
        self._update_charts(self._yearly_charts, is_monthly=False)

    def _refresh_monthly_charts(self) -> None:
        """Refresh all monthly charts with current data."""
        self._update_charts(self._monthly_charts, is_monthly=True)

    def _update_charts(
        self, charts: dict[str, VerticalBarChart], is_monthly: bool
    ) -> None:
        """Update a set of charts with calculated metrics.

        Args:
            charts: Chart dict to update.
            is_monthly: Whether these are monthly charts.
        """
        year = self._year_selector.selected_year() if is_monthly else None

        # Calculate metrics for each portfolio
        baseline_metrics = {}
        combined_metrics = {}

        if self._baseline_data is not None and not self._baseline_data.empty:
            if is_monthly and year:
                baseline_metrics = self._calculator.calculate_monthly(
                    self._baseline_data, year
                )
            else:
                baseline_metrics = self._calculator.calculate_yearly(self._baseline_data)

        if self._combined_data is not None and not self._combined_data.empty:
            if is_monthly and year:
                combined_metrics = self._calculator.calculate_monthly(
                    self._combined_data, year
                )
            else:
                combined_metrics = self._calculator.calculate_yearly(self._combined_data)

        # Update each chart
        for metric_key, title, is_pct, is_currency in CHART_METRICS:
            # Baseline chart
            baseline_chart = charts.get(f"{metric_key}_baseline")
            if baseline_chart:
                data = [
                    (str(period), metrics.get(metric_key, 0))
                    for period, metrics in sorted(baseline_metrics.items())
                ]
                baseline_chart.set_data(data, is_percentage=is_pct, is_currency=is_currency)

            # Combined chart
            combined_chart = charts.get(f"{metric_key}_combined")
            if combined_chart:
                data = [
                    (str(period), metrics.get(metric_key, 0))
                    for period, metrics in sorted(combined_metrics.items())
                ]
                combined_chart.set_data(data, is_percentage=is_pct, is_currency=is_currency)
