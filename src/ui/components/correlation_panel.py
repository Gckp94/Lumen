# src/ui/components/correlation_panel.py
"""Correlation analysis panel for portfolio metrics.

Displays correlation metrics with visual indicators and sparkline.
"""
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.ui.constants import Colors, Fonts, Spacing


class CorrelationCard(QFrame):
    """Single correlation metric card with value and badge."""

    def __init__(
        self,
        label: str,
        tooltip: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._label_text = label
        self._setup_ui()
        if tooltip:
            self.setToolTip(tooltip)

    def _setup_ui(self) -> None:
        self.setObjectName("correlationCard")
        self.setStyleSheet(f"""
            QFrame#correlationCard {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: 4px;
                padding: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.SM)

        # Header row: label + badge
        header = QHBoxLayout()

        self._label = QLabel(self._label_text)
        self._label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: 11px;
            }}
        """)
        header.addWidget(self._label)
        header.addStretch()

        self._badge = QLabel("")
        self._badge.setStyleSheet(f"""
            QLabel {{
                color: {Colors.SIGNAL_CYAN};
                font-family: '{Fonts.UI}';
                font-size: 9px;
                font-weight: 600;
                padding: 2px 6px;
                border-radius: 3px;
                background-color: {Colors.BG_SURFACE};
            }}
        """)
        header.addWidget(self._badge)

        layout.addLayout(header)

        # Value
        self._value = QLabel("—")
        self._value.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.DATA}';
                font-size: 18px;
                font-weight: 600;
            }}
        """)
        layout.addWidget(self._value)

    def set_value(self, value: float | None, thresholds: tuple[float, float] = (0.3, 0.5)) -> None:
        """Update value and badge based on thresholds.

        Args:
            value: Correlation value (-1 to 1).
            thresholds: (good_threshold, moderate_threshold) for badges.
        """
        if value is None:
            self._value.setText("—")
            self._badge.setText("")
            return

        self._value.setText(f"{value:.2f}")

        good_thresh, moderate_thresh = thresholds

        if abs(value) < good_thresh:
            badge_text = "EXCELLENT"
            badge_color = Colors.SIGNAL_CYAN
            value_color = Colors.SIGNAL_CYAN
        elif abs(value) < moderate_thresh:
            badge_text = "GOOD"
            badge_color = Colors.SIGNAL_CYAN
            value_color = Colors.SIGNAL_CYAN
        else:
            badge_text = "MODERATE"
            badge_color = Colors.SIGNAL_AMBER
            value_color = Colors.SIGNAL_AMBER

        self._badge.setText(badge_text)
        self._badge.setStyleSheet(f"""
            QLabel {{
                color: {badge_color};
                font-family: '{Fonts.UI}';
                font-size: 9px;
                font-weight: 600;
                padding: 2px 6px;
                border-radius: 3px;
                background-color: rgba(255, 255, 255, 0.05);
            }}
        """)
        self._value.setStyleSheet(f"""
            QLabel {{
                color: {value_color};
                font-family: '{Fonts.DATA}';
                font-size: 18px;
                font-weight: 600;
            }}
        """)


class CorrelationPanel(QFrame):
    """Panel displaying correlation analysis metrics."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("correlationPanel")
        self.setStyleSheet(f"""
            QFrame#correlationPanel {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.SM)

        # Title
        title = QLabel("CORRELATION ANALYSIS")
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

        # Correlation cards
        self._pearson_card = CorrelationCard(
            "Pearson Correlation",
            "Standard linear correlation between daily returns"
        )
        layout.addWidget(self._pearson_card)

        self._tail_card = CorrelationCard(
            "Tail Correlation (Crisis)",
            "Correlation during stress periods"
        )
        layout.addWidget(self._tail_card)

        self._drawdown_card = CorrelationCard(
            "Drawdown Correlation",
            "Correlation of drawdown series"
        )
        layout.addWidget(self._drawdown_card)

        self._ltd_card = CorrelationCard(
            "Lower Tail Dependence",
            "Joint extreme loss probability"
        )
        layout.addWidget(self._ltd_card)

        layout.addStretch()

    def update_metrics(
        self,
        pearson: float | None,
        tail: float | None,
        drawdown: float | None,
        ltd: float | None,
    ) -> None:
        """Update all correlation metrics."""
        self._pearson_card.set_value(pearson)
        self._tail_card.set_value(tail)
        self._drawdown_card.set_value(drawdown)
        self._ltd_card.set_value(ltd, thresholds=(0.15, 0.25))
