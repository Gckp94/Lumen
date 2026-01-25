# src/tabs/portfolio_metrics.py
"""Portfolio Metrics tab for comprehensive strategy comparison.

Displays quantitative metrics comparing baseline vs combined portfolio
strategies using data from Portfolio Overview.
"""
import logging

import pandas as pd
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.core.portfolio_metrics_calculator import (
    PortfolioMetrics,
    PortfolioMetricsCalculator,
)
from src.ui.components.comparison_panel import ComparisonPanel
from src.ui.components.contribution_panel import ContributionPanel
from src.ui.components.correlation_panel import CorrelationPanel
from src.ui.components.edge_decay_card import EdgeDecayCard
from src.ui.components.period_metrics_card import PeriodMetricsCard
from src.ui.components.ticker_overlap_card import TickerOverlapCard
from src.ui.constants import Colors, Fonts, Spacing

logger = logging.getLogger(__name__)


class PortfolioMetricsTab(QWidget):
    """Tab displaying comprehensive portfolio metrics."""

    # Metric definitions: (key, label, tooltip, higher_is_better)
    CORE_METRICS = [
        ("cagr", "CAGR", "Compound Annual Growth Rate", True),
        ("sharpe_ratio", "Sharpe Ratio", "Risk-adjusted return (excess return / volatility)", True),
        ("sortino_ratio", "Sortino Ratio", "Downside risk-adjusted return", True),
        ("calmar_ratio", "Calmar Ratio", "CAGR / Max Drawdown", True),
        ("profit_factor", "Profit Factor", "Gross profits / Gross losses", True),
        ("win_rate", "Win Rate", "Percentage of winning trades", True),
    ]

    RISK_METRICS = [
        ("max_drawdown_pct", "Max DD %", "Maximum peak-to-trough decline", False),
        ("max_drawdown_dollars", "Max DD $", "Maximum drawdown in dollars", False),
        ("max_dd_duration_days", "DD Duration", "Days to recover from max drawdown", False),
        ("time_underwater_pct", "Time Underwater", "Percent of time below peak", False),
        ("var_95", "VaR (95%)", "Value at Risk at 95% confidence", False),
        ("cvar_95", "CVaR (95%)", "Expected Shortfall at 95% confidence", False),
    ]

    STAT_METRICS = [
        ("t_statistic", "T-Statistic", "Statistical significance of returns", True),
        ("p_value", "P-Value", "Probability returns are random", False),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize Portfolio Metrics tab.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._calculator = PortfolioMetricsCalculator()
        self._baseline_data: pd.DataFrame | None = None
        self._combined_data: pd.DataFrame | None = None
        self._baseline_metrics: PortfolioMetrics | None = None
        self._combined_metrics: PortfolioMetrics | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the tab UI."""
        self.setObjectName("portfolioMetricsTab")
        self.setStyleSheet(f"""
            QWidget#portfolioMetricsTab {{
                background-color: {Colors.BG_BASE};
            }}
        """)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {Colors.BG_BASE};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {Colors.BG_SURFACE};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {Colors.BG_BORDER};
                border-radius: 4px;
                min-height: 20px;
            }}
        """)

        # Content widget
        content = QWidget()
        content.setStyleSheet(f"background-color: {Colors.BG_BASE};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        content_layout.setSpacing(Spacing.XL)

        # Header
        header = self._create_header()
        content_layout.addWidget(header)

        # Main metrics panels (3 columns)
        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(Spacing.LG)

        # Left column: Core + Risk metrics
        left_col = QVBoxLayout()
        left_col.setSpacing(Spacing.LG)

        self._core_panel = ComparisonPanel("Performance Metrics", self.CORE_METRICS)
        left_col.addWidget(self._core_panel)

        self._risk_panel = ComparisonPanel("Risk Metrics", self.RISK_METRICS)
        left_col.addWidget(self._risk_panel)

        left_col.addStretch()
        panels_layout.addLayout(left_col, 1)

        # Center column: Correlation + Contribution panels
        center_col = QVBoxLayout()
        center_col.setSpacing(Spacing.LG)

        self._correlation_panel = CorrelationPanel()
        center_col.addWidget(self._correlation_panel)

        self._contribution_panel = ContributionPanel()
        center_col.addWidget(self._contribution_panel)

        center_col.addStretch()
        panels_layout.addLayout(center_col, 1)

        # Right column: Statistical + Edge decay + Ticker overlap + Period metrics
        right_col = QVBoxLayout()
        right_col.setSpacing(Spacing.LG)

        self._stat_panel = ComparisonPanel("Statistical Analysis", self.STAT_METRICS)
        right_col.addWidget(self._stat_panel)

        self._edge_decay_card = EdgeDecayCard()
        right_col.addWidget(self._edge_decay_card)

        self._ticker_overlap_card = TickerOverlapCard()
        right_col.addWidget(self._ticker_overlap_card)

        # Period metrics section
        period_section = self._create_period_section()
        right_col.addWidget(period_section)

        right_col.addStretch()
        panels_layout.addLayout(right_col, 1)

        content_layout.addLayout(panels_layout)
        content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _create_header(self) -> QWidget:
        """Create the header widget."""
        header = QWidget()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, Spacing.MD)
        layout.setSpacing(Spacing.XS)

        title = QLabel("Portfolio Metrics")
        title.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: 24px;
                font-weight: 700;
            }}
        """)
        layout.addWidget(title)

        subtitle = QLabel(
            "Comprehensive quantitative analysis comparing baseline vs combined portfolio"
        )
        subtitle.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: 13px;
            }}
        """)
        layout.addWidget(subtitle)

        return header

    def _create_period_section(self) -> QWidget:
        """Create the period metrics section."""
        section = QFrame()
        section.setObjectName("periodSection")
        section.setStyleSheet(f"""
            QFrame#periodSection {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(section)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # Title
        title = QLabel("PERIOD PERFORMANCE")
        title.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: 14px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
        """)
        layout.addWidget(title)

        # Period cards row
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(Spacing.MD)

        self._daily_card = PeriodMetricsCard("Daily")
        cards_layout.addWidget(self._daily_card)

        self._weekly_card = PeriodMetricsCard("Weekly")
        cards_layout.addWidget(self._weekly_card)

        self._monthly_card = PeriodMetricsCard("Monthly")
        cards_layout.addWidget(self._monthly_card)

        layout.addLayout(cards_layout)

        return section

    def _infer_starting_capital(self) -> float:
        """Infer starting capital from equity curve data."""
        data = self._baseline_data if self._baseline_data is not None else self._combined_data
        if data is not None and not data.empty and len(data) > 0:
            first_equity = data["equity"].iloc[0]
            first_pnl = data["pnl"].iloc[0]
            return first_equity - first_pnl
        return 100_000  # Default

    @pyqtSlot(dict)
    def on_portfolio_data_changed(self, data: dict[str, pd.DataFrame]) -> None:
        """Handle portfolio data update from Portfolio Overview.

        Args:
            data: Dict with "baseline" and/or "combined" DataFrames.
        """
        self._baseline_data = data.get("baseline")
        self._combined_data = data.get("combined")

        # Update calculator starting capital
        starting_capital = self._infer_starting_capital()
        self._calculator = PortfolioMetricsCalculator(starting_capital)

        # Calculate metrics
        if self._baseline_data is not None and not self._baseline_data.empty:
            self._baseline_metrics = self._calculator.calculate_all_metrics(self._baseline_data)
        else:
            self._baseline_metrics = None

        if self._combined_data is not None and not self._combined_data.empty:
            self._combined_metrics = self._calculator.calculate_all_metrics(self._combined_data)
        else:
            self._combined_metrics = None

        # Update UI
        self._update_panels()
        self._update_period_cards()
        self._update_advanced_metrics()

        logger.debug("Portfolio metrics updated")

    def _update_panels(self) -> None:
        """Update comparison panels with calculated metrics."""
        baseline_values: dict[str, tuple[str, float | None]] = {}
        combined_values: dict[str, tuple[str, float | None]] = {}

        all_metrics = self.CORE_METRICS + self.RISK_METRICS + self.STAT_METRICS

        for key, _, _, _ in all_metrics:
            # Baseline
            if self._baseline_metrics is not None:
                raw = getattr(self._baseline_metrics, key, None)
                formatted = self._format_metric(key, raw)
                baseline_values[key] = (formatted, raw)
            else:
                baseline_values[key] = ("—", None)

            # Combined
            if self._combined_metrics is not None:
                raw = getattr(self._combined_metrics, key, None)
                formatted = self._format_metric(key, raw)
                combined_values[key] = (formatted, raw)
            else:
                combined_values[key] = ("—", None)

        self._core_panel.update_metrics(baseline_values, combined_values)
        self._risk_panel.update_metrics(baseline_values, combined_values)
        self._stat_panel.update_metrics(baseline_values, combined_values)

    def _update_period_cards(self) -> None:
        """Update period metric cards."""
        baseline_daily = self._baseline_metrics.daily if self._baseline_metrics else None
        baseline_weekly = self._baseline_metrics.weekly if self._baseline_metrics else None
        baseline_monthly = self._baseline_metrics.monthly if self._baseline_metrics else None

        combined_daily = self._combined_metrics.daily if self._combined_metrics else None
        combined_weekly = self._combined_metrics.weekly if self._combined_metrics else None
        combined_monthly = self._combined_metrics.monthly if self._combined_metrics else None

        self._daily_card.update_metrics(baseline_daily, combined_daily)
        self._weekly_card.update_metrics(baseline_weekly, combined_weekly)
        self._monthly_card.update_metrics(baseline_monthly, combined_monthly)

    def _update_advanced_metrics(self) -> None:
        """Update correlation, contribution, edge decay, and overlap metrics."""
        if self._baseline_data is None or self._combined_data is None:
            # Clear panels when data unavailable
            self._correlation_panel.update_metrics(None, None, None, None)
            self._contribution_panel.update_metrics(None, None, None)
            self._edge_decay_card.update_metrics(None, None, None)
            self._ticker_overlap_card.update_metrics(None, None)
            return

        # Correlation metrics
        pearson = self._calculator.calculate_pearson_correlation(
            self._baseline_data, self._combined_data
        )
        tail = self._calculator.calculate_tail_correlation(
            self._baseline_data, self._combined_data
        )
        dd_corr = self._calculator.calculate_drawdown_correlation(
            self._baseline_data, self._combined_data
        )
        ltd = self._calculator.calculate_lower_tail_dependence(
            self._baseline_data, self._combined_data
        )

        self._correlation_panel.update_metrics(pearson, tail, dd_corr, ltd)

        # Contribution metrics
        sharpe_contrib = self._calculator.calculate_marginal_sharpe_contribution(
            self._baseline_data, self._combined_data
        )
        var_contrib = self._calculator.calculate_var_contribution(
            self._baseline_data, self._combined_data
        )
        cvar_contrib = self._calculator.calculate_cvar_contribution(
            self._baseline_data, self._combined_data
        )

        self._contribution_panel.update_metrics(sharpe_contrib, var_contrib, cvar_contrib)

        # Edge decay analysis (on combined portfolio)
        edge_decay = self._calculator.calculate_edge_decay(self._combined_data)
        if edge_decay:
            self._edge_decay_card.update_metrics(
                edge_decay.get("rolling_sharpe_current"),
                edge_decay.get("rolling_sharpe_early"),
                edge_decay.get("decay_pct"),
            )
        else:
            self._edge_decay_card.update_metrics(None, None, None)

        # Ticker overlap (if ticker data available)
        overlap = self._calculator.calculate_ticker_overlap(
            self._baseline_data, self._combined_data
        )
        concurrent = self._calculator.calculate_concurrent_exposure(
            self._baseline_data, self._combined_data
        )
        self._ticker_overlap_card.update_metrics(overlap, concurrent)

    def _format_metric(self, key: str, value: float | int | None) -> str:
        """Format a metric value for display.

        Args:
            key: Metric key.
            value: Raw metric value.

        Returns:
            Formatted string.
        """
        if value is None:
            return "—"

        # Format based on metric type
        if key in ("cagr", "win_rate", "time_underwater_pct", "max_drawdown_pct"):
            return f"{value:.2f}%"
        elif key in ("sharpe_ratio", "sortino_ratio", "calmar_ratio", "profit_factor", "rr_ratio"):
            return f"{value:.2f}"
        elif key in ("max_drawdown_dollars",):
            return f"${value:,.0f}"
        elif key in ("max_dd_duration_days",):
            return f"{value} days"
        elif key in ("var_95", "cvar_95"):
            return f"{value:.2f}%"
        elif key in ("t_statistic",):
            return f"{value:.2f}"
        elif key in ("p_value",):
            return f"{value:.4f}"
        else:
            return str(value)
