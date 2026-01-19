"""Hero metric card widget for Monte Carlo display."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
)
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.ui.constants import Colors, Fonts, Spacing

if TYPE_CHECKING:
    from src.core.monte_carlo import MonteCarloResults


def _make_qt_property(type_: type, getter: object, setter: object) -> object:
    """Create a Qt property, working around mypy stub issues."""
    from PyQt6 import QtCore

    prop_factory = getattr(QtCore, "pyqt" + "Property")  # noqa: B009
    return prop_factory(type_, getter, setter)


def get_probability_color(value: float) -> str:
    """Get semantic color for probability values.

    Args:
        value: Probability percentage (0-100).

    Returns:
        Color hex string.
    """
    if value > 60:
        return Colors.SIGNAL_CYAN
    elif value >= 40:
        return Colors.SIGNAL_AMBER
    else:
        return Colors.SIGNAL_CORAL


def get_risk_color(value: float) -> str:
    """Get semantic color for risk values.

    Args:
        value: Risk percentage (0-100).

    Returns:
        Color hex string.
    """
    if value < 5:
        return Colors.SIGNAL_CYAN
    elif value <= 15:
        return Colors.SIGNAL_AMBER
    else:
        return Colors.SIGNAL_CORAL


def get_drawdown_color(value: float) -> str:
    """Get semantic color for drawdown values.

    Args:
        value: Drawdown as decimal (e.g., 0.25 for 25%).

    Returns:
        Color hex string.
    """
    abs_val = abs(value) * 100  # Convert to percentage
    if abs_val < 20:
        return Colors.SIGNAL_CYAN
    elif abs_val <= 35:
        return Colors.SIGNAL_AMBER
    else:
        return Colors.SIGNAL_CORAL


class HeroMetricCard(QFrame):
    """Large metric card for hero metrics display.

    Features:
    - Large value display: Azeret Mono 56px, weight 600
    - Label: Geist 14px, uppercase
    - Subtitle/context line: Azeret Mono 18px
    - Background gradient: BG_SURFACE -> BG_ELEVATED
    - 2px left accent border in semantic color
    - Border-radius 8px, padding 24px
    """

    def __init__(
        self,
        label: str,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the hero metric card.

        Args:
            label: Metric label text.
            subtitle: Optional subtitle/context text.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._label = label
        self._subtitle = subtitle
        self._accent_color = Colors.SIGNAL_CYAN
        self._display_value = 0.0
        self._target_value = 0.0
        self._setup_ui()
        self._setup_animation()

    def _setup_ui(self) -> None:
        """Set up the card UI."""
        self.setObjectName("heroMetricCard")
        self._update_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        layout.setSpacing(Spacing.SM)

        # Label (uppercase)
        self._label_widget = QLabel(self._label.upper())
        self._label_widget.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-family: {Fonts.UI};
            font-size: 14px;
            font-weight: normal;
            letter-spacing: 1px;
        """)
        layout.addWidget(self._label_widget)

        # Value (large)
        self._value_widget = QLabel("\u2014")  # Em dash placeholder
        self._value_widget.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-family: {Fonts.DATA};
            font-size: 56px;
            font-weight: 600;
            letter-spacing: -2px;
        """)
        layout.addWidget(self._value_widget)

        # Subtitle (context)
        self._subtitle_widget = QLabel(self._subtitle)
        self._subtitle_widget.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-family: {Fonts.DATA};
            font-size: 18px;
        """)
        if not self._subtitle:
            self._subtitle_widget.hide()
        layout.addWidget(self._subtitle_widget)

        layout.addStretch()

        # Set fixed height for hero cards
        self.setFixedHeight(180)
        self.setMinimumWidth(250)

    def _setup_animation(self) -> None:
        """Set up value animation for number ticker effect."""
        self._animation = QPropertyAnimation(self, b"displayValue")
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _get_display_value(self) -> float:
        """Get current display value."""
        return self._display_value

    def _set_display_value(self, value: float) -> None:
        """Set display value and update text."""
        self._display_value = value
        # Format and update display (will be called during animation)
        self._update_value_text()

    def _update_value_text(self) -> None:
        """Update the value text with current display value."""
        # This is called during animation - format based on current display value
        # The actual formatting is done in update_value() which sets the format
        pass

    def _update_style(self) -> None:
        """Update card styling with current accent color."""
        self.setStyleSheet(f"""
            QFrame#heroMetricCard {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 {Colors.BG_SURFACE},
                    stop: 1 {Colors.BG_ELEVATED}
                );
                border-radius: 8px;
                border-left: 2px solid {self._accent_color};
            }}
        """)

    def update_value(
        self,
        value: float | None,
        format_str: str = "{:.1f}%",
        color: str | None = None,
        subtitle: str | None = None,
        animate: bool = True,
    ) -> None:
        """Update the displayed value.

        Args:
            value: Value to display (None shows em dash).
            format_str: Format string for the value.
            color: Accent color for the card border.
            subtitle: Optional updated subtitle text.
            animate: Whether to animate the value change.
        """
        if value is None:
            self._value_widget.setText("\u2014")
            self._accent_color = Colors.TEXT_DISABLED
            self._update_style()
            return

        # Update accent color
        if color is not None:
            self._accent_color = color
            self._update_style()

        # Update subtitle if provided
        if subtitle is not None:
            self._subtitle_widget.setText(subtitle)
            self._subtitle_widget.setVisible(bool(subtitle))

        # Format and display value
        try:
            text = format_str.format(value)
        except (ValueError, TypeError):
            text = str(value)

        self._value_widget.setText(text)

        # Update value color to match accent
        self._value_widget.setStyleSheet(f"""
            color: {self._accent_color};
            font-family: {Fonts.DATA};
            font-size: 56px;
            font-weight: 600;
            letter-spacing: -2px;
        """)

    def set_accent_color(self, color: str) -> None:
        """Set the accent color.

        Args:
            color: Hex color string.
        """
        self._accent_color = color
        self._update_style()

    def clear(self) -> None:
        """Clear the displayed value."""
        self._value_widget.setText("\u2014")
        self._subtitle_widget.setText("")
        self._subtitle_widget.hide()
        self._accent_color = Colors.TEXT_DISABLED
        self._update_style()


# Register Qt property for animation
HeroMetricCard.displayValue = _make_qt_property(  # type: ignore[attr-defined]
    float,
    HeroMetricCard._get_display_value,
    HeroMetricCard._set_display_value,
)


class HeroMetricsPanel(QWidget):
    """Panel containing three hero metric cards in a row.

    Displays:
    - Probability of Profit
    - Risk of Ruin
    - Median Max Drawdown
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the hero metrics panel.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel with three cards."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.LG)

        # Probability of Profit card
        self._prob_profit_card = HeroMetricCard(
            label="Probability of Profit",
            subtitle="chance of ending above initial capital",
        )
        layout.addWidget(self._prob_profit_card)

        # Risk of Ruin card
        self._risk_ruin_card = HeroMetricCard(
            label="Risk of Ruin",
            subtitle="chance of hitting ruin threshold",
        )
        layout.addWidget(self._risk_ruin_card)

        # Median Max Drawdown card
        self._median_dd_card = HeroMetricCard(
            label="Median Max Drawdown",
            subtitle="typical maximum decline from peak",
        )
        layout.addWidget(self._median_dd_card)

    def update_from_results(self, results: MonteCarloResults) -> None:
        """Update all cards from Monte Carlo results.

        Args:
            results: Monte Carlo simulation results.
        """
        # Probability of Profit
        prob_profit = results.probability_of_profit * 100  # Convert to percentage
        prob_color = get_probability_color(prob_profit)
        self._prob_profit_card.update_value(
            prob_profit,
            format_str="{:.1f}%",
            color=prob_color,
        )

        # Risk of Ruin
        risk_ruin = results.risk_of_ruin * 100  # Convert to percentage
        risk_color = get_risk_color(risk_ruin)
        self._risk_ruin_card.update_value(
            risk_ruin,
            format_str="{:.1f}%",
            color=risk_color,
        )

        # Median Max Drawdown (already a decimal, e.g., 0.25 for 25%)
        median_dd = results.median_max_dd
        dd_color = get_drawdown_color(median_dd)
        self._median_dd_card.update_value(
            median_dd * 100,  # Convert to percentage for display
            format_str="-{:.1f}%",  # Show as negative
            color=dd_color,
        )

    def clear(self) -> None:
        """Clear all cards."""
        self._prob_profit_card.clear()
        self._risk_ruin_card.clear()
        self._median_dd_card.clear()
