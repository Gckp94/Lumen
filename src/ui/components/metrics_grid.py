"""MetricsGrid widget for displaying 23 core trading metrics."""

from PyQt6.QtWidgets import QGridLayout, QWidget

from src.core.models import TradingMetrics
from src.ui.components.metric_card import MetricCard
from src.ui.constants import Colors, Spacing

# Tooltip descriptions for each metric
METRIC_TOOLTIPS = {
    "Trades": "Total number of trades in dataset",
    "Win Rate": "Percentage of winning trades",
    "Avg Winner": "Average gain percentage of winning trades",
    "Avg Loser": "Average loss percentage of losing trades",
    "R:R Ratio": "Risk-Reward ratio (Avg Winner / |Avg Loser|)",
    "EV": "Expected Value per trade",
    "Edge": "Total expected edge (EV × Trades)",
    "Kelly %": "Kelly criterion optimal bet fraction",
    "Stop Adj Kelly %": "Kelly adjusted for stop loss: kelly / stop_loss × 100",
    "Frac Kelly %": "Fractional Kelly based on user input",
    "EG Full Kelly": "Expected log-growth per trade at full Kelly sizing. Negative values indicate overbetting.",
    "EG Frac Kelly": "Expected log-growth per trade at fractional Kelly sizing (uses stop-adjusted Kelly if configured)",
    "EG Flat Stake": "Expected log-growth per trade at flat stake sizing",
    "Median Winner": "Median gain of winning trades",
    "Median Loser": "Median loss of losing trades",
    "Max Win Streak": "Maximum consecutive winning trades",
    "Max Loss Streak": "Maximum consecutive losing trades",
    "Max Loss %": "Percentage of trades that hit stop loss level",
    # Flat Stake (Story 3.4 - metrics 16-19)
    "Flat Stake PnL": "Total profit/loss with fixed stake size",
    "Max DD ($)": "Maximum drawdown in dollars",
    "Max DD (%)": "Maximum drawdown as percentage of peak equity",
    "DD Duration": "Trading days to recover from max drawdown",
    # Compounded Kelly (Story 3.5 - metrics 20-23)
    "Kelly PnL": "Total profit/loss with compounded Kelly position sizing",
    "Kelly Max DD ($)": "Maximum drawdown in dollars (Kelly sizing)",
    "Kelly Max DD (%)": "Maximum drawdown as percentage of peak (Kelly sizing)",
    "Kelly DD Duration": "Trading days to recover from max drawdown (Kelly sizing)",
}

# Metric display configuration: (label, field_name, format_spec)
METRIC_CONFIG = [
    ("Trades", "num_trades", "d"),
    ("Win Rate", "win_rate", ".1f"),
    ("Avg Winner", "avg_winner", ".2f"),
    ("Avg Loser", "avg_loser", ".2f"),
    ("R:R Ratio", "rr_ratio", ".2f"),
    ("EV", "ev", ".2f"),
    ("Edge", "edge", ".2f"),
    ("Kelly %", "kelly", ".2f"),
    ("Stop Adj Kelly %", "stop_adjusted_kelly", ".2f"),
    ("Frac Kelly %", "fractional_kelly", ".2f"),
    ("EG Full Kelly", "eg_full_kelly", ".2f"),
    ("EG Frac Kelly", "eg_frac_kelly", ".2f"),
    ("EG Flat Stake", "eg_flat_stake", ".2f"),
    ("Median Winner", "median_winner", ".2f"),
    ("Median Loser", "median_loser", ".2f"),
    # Streak & Loss (Story 3.3 - metrics 13-15)
    ("Max Win Streak", "max_consecutive_wins", "d"),
    ("Max Loss Streak", "max_consecutive_losses", "d"),
    ("Max Loss %", "max_loss_pct", ".2f"),
    # Flat Stake (Story 3.4 - metrics 16-19)
    ("Flat Stake PnL", "flat_stake_pnl", ",.2f"),
    ("Max DD ($)", "flat_stake_max_dd", ",.2f"),
    ("Max DD (%)", "flat_stake_max_dd_pct", ".2f"),
    ("DD Duration", "flat_stake_dd_duration", None),  # Special formatting
    # Compounded Kelly (Story 3.5 - metrics 20-23)
    ("Kelly PnL", "kelly_pnl", ",.2f"),
    ("Kelly Max DD ($)", "kelly_max_dd", ",.2f"),
    ("Kelly Max DD (%)", "kelly_max_dd_pct", ".2f"),
    ("Kelly DD Duration", "kelly_dd_duration", None),  # Special formatting
]


class MetricsGrid(QWidget):
    """Grid display of trading metrics.

    Displays metrics in a 3-column grid layout with tooltips
    and color-coded values (cyan for positive, coral for negative).

    Attributes:
        _cards: Dictionary mapping field names to MetricCard widgets.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize MetricsGrid.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._cards: dict[str, MetricCard] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Create 3-column grid of MetricCards."""
        self.setObjectName("metricsGrid")
        self.setStyleSheet(f"""
            QWidget#metricsGrid {{
                background-color: {Colors.BG_SURFACE};
            }}
        """)

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.MD)

        for i, (label, field_name, _) in enumerate(METRIC_CONFIG):
            row, col = divmod(i, 3)
            card = MetricCard(label, variant=MetricCard.STANDARD)
            card.setToolTip(METRIC_TOOLTIPS.get(label, ""))
            self._cards[field_name] = card
            layout.addWidget(card, row, col)

        # Set equal column stretch
        for col in range(3):
            layout.setColumnStretch(col, 1)

        # Add stretch at the bottom to push cards up (row 9 after 25 metrics in 9 rows)
        layout.setRowStretch(9, 1)

    def update_metrics(self, metrics: TradingMetrics) -> None:
        """Update all cards with new metrics values.

        Args:
            metrics: TradingMetrics instance with calculated values.
        """
        for _, field_name, format_spec in METRIC_CONFIG:
            value = getattr(metrics, field_name, None)
            card = self._cards.get(field_name)
            if card:
                # Special handling for DD Duration fields (Story 3.4 + 3.5)
                if field_name in ("flat_stake_dd_duration", "kelly_dd_duration"):
                    if isinstance(value, int):
                        # Format as "X days"
                        card.update_value(
                            f"{value} days", format_spec=None, color=Colors.TEXT_PRIMARY
                        )
                    elif value in ("Not recovered", "Blown"):
                        # Display in coral color for unrecovered or blown account
                        card.update_value(value, format_spec=None, color=Colors.SIGNAL_CORAL)
                    else:
                        card.update_value(value)
                    continue
                # Cap Max DD % at 100% for display (account is bust beyond 100%)
                if (
                    field_name in ("flat_stake_max_dd_pct", "kelly_max_dd_pct")
                    and isinstance(value, (int, float))
                    and value > 100
                ):
                    card.update_value(">100%", format_spec=None)
                    continue
                card.update_value(value, format_spec)

    def clear_metrics(self) -> None:
        """Clear all metric card values (show em dash)."""
        for card in self._cards.values():
            card.update_value(None)
