"""ComparisonRibbon widget for displaying key metrics with baseline comparison."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from src.ui.constants import Colors, Fonts, FontSizes, Spacing

if TYPE_CHECKING:
    from src.core.models import TradingMetrics

logger = logging.getLogger(__name__)


METRICS = ["trades", "win_rate", "ev", "kelly"]

# Metric display configuration
_METRIC_CONFIG: dict[str, dict[str, str | bool]] = {
    "trades": {"label": "Trades", "format": ",d", "suffix": "", "is_pct": False},
    "win_rate": {"label": "Win Rate", "format": ".1f", "suffix": "%", "is_pct": True},
    "ev": {"label": "EV", "format": ".2f", "suffix": "%", "is_pct": True},
    "kelly": {"label": "Kelly", "format": ".1f", "suffix": "%", "is_pct": True},
}


def _calculate_delta(
    filtered: float | int | None,
    baseline: float | int | None,
    metric_name: str,
) -> tuple[float | None, str]:
    """Calculate delta between filtered and baseline values.

    Args:
        filtered: Filtered metric value.
        baseline: Baseline metric value.
        metric_name: Name of the metric (for formatting).

    Returns:
        Tuple of (delta_value, formatted_display_string).
    """
    if filtered is None or baseline is None:
        return None, "N/A"

    delta = filtered - baseline

    if metric_name == "trades":
        # Absolute difference for trades
        if delta > 0:
            return delta, f"+{delta:,d}"
        if delta < 0:
            return delta, f"{delta:,d}"
        return 0.0, "0"

    # Percentage point difference for win_rate, ev, kelly
    if delta > 0:
        return delta, f"+{delta:.1f}pp"
    if delta < 0:
        return delta, f"{delta:.1f}pp"
    return 0.0, "0pp"


def _get_delta_color(delta: float | None) -> str:
    """Get color for delta indicator based on value.

    All 4 metrics use 'higher is better' logic.

    Args:
        delta: Delta value.

    Returns:
        Hex color code.
    """
    if delta is None:
        return Colors.TEXT_SECONDARY
    if delta > 0:
        return Colors.SIGNAL_CYAN  # Improvement
    elif delta < 0:
        return Colors.SIGNAL_CORAL  # Decline
    else:
        return Colors.TEXT_SECONDARY  # Neutral


def _get_delta_arrow(delta: float | None) -> str:
    """Get arrow indicator for delta.

    Args:
        delta: Delta value.

    Returns:
        Arrow character or em dash for neutral.
    """
    if delta is None:
        return ""
    if delta > 0:
        return "▲ "
    elif delta < 0:
        return "▼ "
    else:
        return "— "


class _RibbonCard(QFrame):
    """Internal widget displaying a single metric with delta and baseline."""

    def __init__(self, metric_name: str, parent: QFrame | None = None) -> None:
        """Initialize RibbonCard.

        Args:
            metric_name: Name of the metric to display.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._metric_name = metric_name
        self._config = _METRIC_CONFIG[metric_name]
        self._setup_ui()
        self._apply_style()
        self.clear()

    def _setup_ui(self) -> None:
        """Set up the widget UI layout."""
        self.setFixedWidth(200)
        self.setMinimumHeight(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        layout.setSpacing(Spacing.XS)

        # Metric label at top
        self._label_widget = QLabel(str(self._config["label"]))
        self._label_widget.setObjectName("cardLabel")
        layout.addWidget(self._label_widget)

        # Filtered value (large, center)
        self._value_widget = QLabel("—")
        self._value_widget.setObjectName("cardValue")
        layout.addWidget(self._value_widget)

        # Delta indicator
        self._delta_widget = QLabel("")
        self._delta_widget.setObjectName("cardDelta")
        layout.addWidget(self._delta_widget)

        # Baseline reference (small, below)
        self._baseline_widget = QLabel("")
        self._baseline_widget.setObjectName("cardBaseline")
        layout.addWidget(self._baseline_widget)

    def _apply_style(self) -> None:
        """Apply base styling to the card."""
        self.setStyleSheet(f"""
            _RibbonCard {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: 8px;
            }}
            QLabel#cardLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.UI};
                font-size: 12px;
            }}
            QLabel#cardValue {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.DATA};
                font-size: {FontSizes.KPI_HERO}px;
            }}
            QLabel#cardDelta {{
                font-family: {Fonts.DATA};
                font-size: 13px;
            }}
            QLabel#cardBaseline {{
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.UI};
                font-size: 12px;
            }}
        """)

    def set_values(
        self,
        filtered_value: float | int | None,
        baseline_value: float | int | None,
    ) -> None:
        """Update the card with new values.

        Args:
            filtered_value: Current filtered metric value.
            baseline_value: Baseline metric value for comparison.
        """
        config = self._config

        # Format filtered value
        if filtered_value is None:
            self._value_widget.setText("N/A")
            self._value_widget.setStyleSheet(f"""
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.DATA};
                font-size: {FontSizes.KPI_HERO}px;
            """)
        else:
            if config["is_pct"]:
                text = f"{filtered_value:{config['format']}}{config['suffix']}"
            else:
                text = f"{filtered_value:{config['format']}}"
            self._value_widget.setText(text)
            self._value_widget.setStyleSheet(f"""
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.DATA};
                font-size: {FontSizes.KPI_HERO}px;
            """)

        # Calculate and display delta
        delta, delta_text = _calculate_delta(
            filtered_value, baseline_value, self._metric_name
        )
        arrow = _get_delta_arrow(delta)
        color = _get_delta_color(delta)

        self._delta_widget.setText(f"{arrow}{delta_text}")
        self._delta_widget.setStyleSheet(f"""
            color: {color};
            font-family: {Fonts.DATA};
            font-size: 13px;
        """)

        # Display baseline reference
        if baseline_value is None:
            self._baseline_widget.setText("")
        else:
            if config["is_pct"]:
                baseline_text = f"Baseline: {baseline_value:{config['format']}}{config['suffix']}"
            else:
                baseline_text = f"Baseline: {baseline_value:{config['format']}}"
            self._baseline_widget.setText(baseline_text)

    def clear(self) -> None:
        """Show empty state with no filter applied."""
        self._value_widget.setText("—")
        self._value_widget.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-family: {Fonts.DATA};
            font-size: {FontSizes.KPI_HERO}px;
        """)
        self._delta_widget.setText("(no filter applied)")
        self._delta_widget.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-family: {Fonts.UI};
            font-size: 12px;
        """)
        self._baseline_widget.setText("")


class ComparisonRibbon(QFrame):
    """Signature element: 4 key metrics with large numbers and deltas.

    Displays Trades, Win Rate, EV, and Kelly with comparison between
    filtered and baseline values.
    """

    def __init__(self, parent: QFrame | None = None) -> None:
        """Initialize ComparisonRibbon.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setObjectName("comparisonRibbon")
        self._cards: dict[str, _RibbonCard] = {}
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        """Set up the widget UI layout."""
        self.setMinimumHeight(140)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.SM, Spacing.LG, Spacing.SM)
        layout.setSpacing(Spacing.LG)

        # Create 4 ribbon cards, one per metric
        for metric in METRICS:
            card = _RibbonCard(metric)
            self._cards[metric] = card
            layout.addWidget(card)

        # Add stretch to center cards if needed
        layout.addStretch()

    def _apply_style(self) -> None:
        """Apply styling to the ribbon frame."""
        self.setStyleSheet(f"""
            QFrame#comparisonRibbon {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: 8px;
            }}
        """)

    def set_values(
        self,
        baseline: TradingMetrics,
        filtered: TradingMetrics,
    ) -> None:
        """Update all 4 metric cards with comparison data.

        Callers must use clear() for empty state; set_values() requires valid
        filtered metrics.

        Args:
            baseline: Baseline metrics (full dataset).
            filtered: Filtered metrics (after filter applied).
        """
        # Extract values and update each card
        self._cards["trades"].set_values(filtered.num_trades, baseline.num_trades)
        self._cards["win_rate"].set_values(filtered.win_rate, baseline.win_rate)
        self._cards["ev"].set_values(filtered.ev, baseline.ev)
        self._cards["kelly"].set_values(filtered.kelly, baseline.kelly)

        logger.debug("Ribbon updated: %d filtered trades", filtered.num_trades)

    def clear(self) -> None:
        """Show empty state (no filters applied)."""
        for card in self._cards.values():
            card.clear()
