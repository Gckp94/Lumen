"""Monte Carlo metric section components."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.ui.constants import Colors, Fonts, Spacing

if TYPE_CHECKING:
    from src.core.monte_carlo import MonteCarloResults


class MonteCarloMetricCard(QFrame):
    """Compact metric card for Monte Carlo sections.

    Features:
    - Value: Azeret Mono 32px
    - Label: Geist 11px, uppercase
    - Optional context hint: 10px, TEXT_DISABLED
    """

    def __init__(
        self,
        label: str,
        hint: str = "",
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the metric card.

        Args:
            label: Metric label.
            hint: Optional context hint.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._label = label
        self._hint = hint
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the card UI."""
        self.setObjectName("mcMetricCard")
        self.setStyleSheet(f"""
            QFrame#mcMetricCard {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: 6px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.XS)

        # Label (uppercase)
        self._label_widget = QLabel(self._label.upper())
        self._label_widget.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-family: {Fonts.UI};
            font-size: 11px;
            letter-spacing: 1px;
        """)
        layout.addWidget(self._label_widget)

        # Value
        self._value_widget = QLabel("\u2014")
        self._value_widget.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-family: {Fonts.DATA};
            font-size: 32px;
            font-weight: 500;
        """)
        layout.addWidget(self._value_widget)

        # Hint (optional)
        self._hint_widget = QLabel(self._hint)
        self._hint_widget.setStyleSheet(f"""
            color: {Colors.TEXT_DISABLED};
            font-family: {Fonts.UI};
            font-size: 10px;
        """)
        if not self._hint:
            self._hint_widget.hide()
        layout.addWidget(self._hint_widget)

        self.setMinimumWidth(140)
        self.setMinimumHeight(90)

    def update_value(
        self,
        value: float | int | str | None,
        format_str: str = "{:.2f}",
        color: str | None = None,
        hint: str | None = None,
    ) -> None:
        """Update the displayed value.

        Args:
            value: Value to display.
            format_str: Format string for numeric values.
            color: Optional color override.
            hint: Optional updated hint text.
        """
        if value is None:
            self._value_widget.setText("\u2014")
            return

        # Format value
        if isinstance(value, str):
            text = value
        else:
            try:
                text = format_str.format(value)
            except (ValueError, TypeError):
                text = str(value)

        self._value_widget.setText(text)

        # Apply color
        value_color = color or Colors.TEXT_PRIMARY
        self._value_widget.setStyleSheet(f"""
            color: {value_color};
            font-family: {Fonts.DATA};
            font-size: 32px;
            font-weight: 500;
        """)

        # Update hint if provided
        if hint is not None:
            self._hint_widget.setText(hint)
            self._hint_widget.setVisible(bool(hint))

    def clear(self) -> None:
        """Clear the displayed value."""
        self._value_widget.setText("\u2014")
        self._value_widget.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-family: {Fonts.DATA};
            font-size: 32px;
            font-weight: 500;
        """)


class MonteCarloSection(QWidget):
    """Section container with diamond bullet header and metric cards grid.

    Features:
    - Header: Diamond bullet (cyan) + Geist 14px weight 600
    - Grid of MonteCarloMetricCards
    """

    def __init__(
        self,
        title: str,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the section.

        Args:
            title: Section title.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._title = title
        self._cards: dict[str, MonteCarloMetricCard] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        # Header with diamond bullet
        header_layout = QHBoxLayout()
        header_layout.setSpacing(Spacing.SM)

        # Diamond bullet
        bullet = QLabel("◆")
        bullet.setStyleSheet(f"""
            color: {Colors.SIGNAL_CYAN};
            font-size: 10px;
        """)
        header_layout.addWidget(bullet)

        # Title
        title_label = QLabel(self._title)
        title_label.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-family: {Fonts.UI};
            font-size: 14px;
            font-weight: 600;
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Grid for cards
        self._grid_widget = QWidget()
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setSpacing(Spacing.SM)
        layout.addWidget(self._grid_widget)

    def add_card(
        self,
        key: str,
        label: str,
        hint: str = "",
        row: int = 0,
        col: int = 0,
    ) -> MonteCarloMetricCard:
        """Add a metric card to the grid.

        Args:
            key: Unique key for the card.
            label: Card label.
            hint: Optional hint text.
            row: Grid row.
            col: Grid column.

        Returns:
            The created card.
        """
        card = MonteCarloMetricCard(label, hint)
        self._cards[key] = card
        self._grid_layout.addWidget(card, row, col)
        return card

    def get_card(self, key: str) -> MonteCarloMetricCard | None:
        """Get a card by key.

        Args:
            key: Card key.

        Returns:
            The card or None if not found.
        """
        return self._cards.get(key)

    def update_card(
        self,
        key: str,
        value: float | int | str | None,
        format_str: str = "{:.2f}",
        color: str | None = None,
    ) -> None:
        """Update a card's value by key.

        Args:
            key: Card key.
            value: Value to display.
            format_str: Format string.
            color: Optional color.
        """
        card = self._cards.get(key)
        if card:
            card.update_value(value, format_str, color)

    def clear_all(self) -> None:
        """Clear all cards."""
        for card in self._cards.values():
            card.clear()


def create_drawdown_section(parent: QWidget | None = None) -> MonteCarloSection:
    """Create the Drawdown Analysis section.

    Args:
        parent: Optional parent widget.

    Returns:
        Configured MonteCarloSection.
    """
    section = MonteCarloSection("Drawdown Analysis", parent)
    section.add_card("median_dd", "Median DD", row=0, col=0)
    section.add_card("p95_dd", "95th DD", row=0, col=1)
    section.add_card("p99_dd", "99th DD", row=0, col=2)
    section.add_card("avg_duration", "Avg Duration", hint="trades", row=0, col=3)
    section.add_card("max_duration", "Max Duration", hint="trades", row=0, col=4)
    return section


def create_equity_outcomes_section(parent: QWidget | None = None) -> MonteCarloSection:
    """Create the Equity Outcomes section.

    Args:
        parent: Optional parent widget.

    Returns:
        Configured MonteCarloSection.
    """
    section = MonteCarloSection("Equity Outcomes", parent)
    section.add_card("mean_final", "Mean Final", row=0, col=0)
    section.add_card("std_dev", "Std Dev", row=0, col=1)
    section.add_card("p5_final", "5th Pctl", row=0, col=2)
    section.add_card("p95_final", "95th Pctl", row=0, col=3)
    section.add_card("prob_profit", "Prob Profit", row=0, col=4)
    return section


def create_growth_section(parent: QWidget | None = None) -> MonteCarloSection:
    """Create the Growth Metrics section.

    Args:
        parent: Optional parent widget.

    Returns:
        Configured MonteCarloSection.
    """
    section = MonteCarloSection("Growth Metrics", parent)
    section.add_card("mean_cagr", "Mean CAGR", row=0, col=0)
    section.add_card("median_cagr", "Median CAGR", row=0, col=1)
    section.add_card("recovery_factor", "Recovery Factor", row=0, col=2)
    return section


def create_risk_adjusted_section(parent: QWidget | None = None) -> MonteCarloSection:
    """Create the Risk-Adjusted Returns section.

    Args:
        parent: Optional parent widget.

    Returns:
        Configured MonteCarloSection.
    """
    section = MonteCarloSection("Risk-Adjusted Returns", parent)
    section.add_card("sharpe", "Sharpe", row=0, col=0)
    section.add_card("sortino", "Sortino", row=0, col=1)
    section.add_card("calmar", "Calmar", row=0, col=2)
    section.add_card("profit_factor", "Profit Factor", row=0, col=3)
    return section


def create_risk_metrics_section(parent: QWidget | None = None) -> MonteCarloSection:
    """Create the Risk Metrics section.

    Args:
        parent: Optional parent widget.

    Returns:
        Configured MonteCarloSection.
    """
    section = MonteCarloSection("Risk Metrics", parent)
    section.add_card("risk_of_ruin", "Risk of Ruin", row=0, col=0)
    section.add_card("var", "VaR", row=0, col=1)
    section.add_card("cvar", "CVaR", row=0, col=2)
    return section


def create_streak_section(parent: QWidget | None = None) -> MonteCarloSection:
    """Create the Streak Analysis section.

    Args:
        parent: Optional parent widget.

    Returns:
        Configured MonteCarloSection.
    """
    section = MonteCarloSection("Streak Analysis", parent)
    section.add_card("mean_max_win", "Mean Max Win", row=0, col=0)
    section.add_card("max_max_win", "Max Max Win", row=0, col=1)
    section.add_card("mean_max_loss", "Mean Max Loss", row=0, col=2)
    section.add_card("max_max_loss", "Max Max Loss", row=0, col=3)
    return section


class MonteCarloSectionsContainer(QWidget):
    """Container for all Monte Carlo metric sections."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the sections container.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up all sections."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.LG)

        # Create all sections
        self._drawdown_section = create_drawdown_section()
        self._equity_section = create_equity_outcomes_section()
        self._growth_section = create_growth_section()
        self._risk_adjusted_section = create_risk_adjusted_section()
        self._risk_section = create_risk_metrics_section()
        self._streak_section = create_streak_section()

        # Add to layout
        layout.addWidget(self._drawdown_section)
        layout.addWidget(self._equity_section)
        layout.addWidget(self._growth_section)
        layout.addWidget(self._risk_adjusted_section)
        layout.addWidget(self._risk_section)
        layout.addWidget(self._streak_section)

    def update_from_results(self, results: MonteCarloResults) -> None:
        """Update all sections from Monte Carlo results.

        Args:
            results: Monte Carlo simulation results.
        """
        # Drawdown Analysis
        self._drawdown_section.update_card(
            "median_dd", results.median_max_dd * 100, "{:.1f}%"
        )
        self._drawdown_section.update_card(
            "p95_dd", results.p95_max_dd * 100, "{:.1f}%"
        )
        self._drawdown_section.update_card(
            "p99_dd", results.p99_max_dd * 100, "{:.1f}%"
        )
        self._drawdown_section.update_card(
            "avg_duration", results.mean_avg_dd_duration, "{:.0f}"
        )
        self._drawdown_section.update_card(
            "max_duration", results.mean_max_dd_duration, "{:.0f}"
        )

        # Equity Outcomes
        self._equity_section.update_card(
            "mean_final", results.mean_final_equity, "${:,.0f}"
        )
        self._equity_section.update_card(
            "std_dev", results.std_final_equity, "${:,.0f}"
        )
        self._equity_section.update_card(
            "p5_final", results.p5_final_equity, "${:,.0f}"
        )
        self._equity_section.update_card(
            "p95_final", results.p95_final_equity, "${:,.0f}"
        )
        self._equity_section.update_card(
            "prob_profit", results.probability_of_profit * 100, "{:.1f}%"
        )

        # Growth Metrics
        self._growth_section.update_card(
            "mean_cagr", results.mean_cagr * 100, "{:.1f}%"
        )
        self._growth_section.update_card(
            "median_cagr", results.median_cagr * 100, "{:.1f}%"
        )
        self._growth_section.update_card(
            "recovery_factor", results.mean_recovery_factor, "{:.2f}"
        )

        # Risk-Adjusted Returns
        self._risk_adjusted_section.update_card(
            "sharpe", results.mean_sharpe, "{:.2f}"
        )
        self._risk_adjusted_section.update_card(
            "sortino", results.mean_sortino, "{:.2f}"
        )
        self._risk_adjusted_section.update_card(
            "calmar", results.mean_calmar, "{:.2f}"
        )
        self._risk_adjusted_section.update_card(
            "profit_factor", results.mean_profit_factor, "{:.2f}"
        )

        # Risk Metrics
        self._risk_section.update_card(
            "risk_of_ruin", results.risk_of_ruin * 100, "{:.1f}%"
        )
        self._risk_section.update_card(
            "var", results.var * 100, "{:.2f}%"
        )
        self._risk_section.update_card(
            "cvar", results.cvar * 100, "{:.2f}%"
        )

        # Streak Analysis
        self._streak_section.update_card(
            "mean_max_win", results.mean_max_win_streak, "{:.1f}"
        )
        self._streak_section.update_card(
            "max_max_win", results.max_max_win_streak, "{:d}"
        )
        self._streak_section.update_card(
            "mean_max_loss", results.mean_max_loss_streak, "{:.1f}"
        )
        self._streak_section.update_card(
            "max_max_loss", results.max_max_loss_streak, "{:d}"
        )

    def clear_all(self) -> None:
        """Clear all sections."""
        self._drawdown_section.clear_all()
        self._equity_section.clear_all()
        self._growth_section.clear_all()
        self._risk_adjusted_section.clear_all()
        self._risk_section.clear_all()
        self._streak_section.clear_all()
