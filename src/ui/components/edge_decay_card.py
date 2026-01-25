"""Edge decay analysis card with sparkline visualization."""
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.ui.constants import Colors, Fonts, Spacing


class EdgeDecayCard(QFrame):
    """Card displaying edge decay analysis with sparkline."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("edgeDecayCard")
        self.setStyleSheet(f"""
            QFrame#edgeDecayCard {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # Title
        title = QLabel("EDGE DECAY ANALYSIS")
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

        # Main content card
        content = QFrame()
        content.setObjectName("edgeDecayContent")
        content.setStyleSheet(f"""
            QFrame#edgeDecayContent {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: 4px;
            }}
        """)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        content_layout.setSpacing(Spacing.SM)

        # Header row
        header = QHBoxLayout()

        header_label = QLabel("Rolling Sharpe (252d)")
        header_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: 11px;
            }}
        """)
        header.addWidget(header_label)
        header.addStretch()

        self._current_value = QLabel("—")
        self._current_value.setStyleSheet(f"""
            QLabel {{
                color: {Colors.SIGNAL_CYAN};
                font-family: '{Fonts.DATA}';
                font-size: 14px;
                font-weight: 600;
            }}
        """)
        header.addWidget(self._current_value)

        content_layout.addLayout(header)

        # Stats row
        stats = QHBoxLayout()
        stats.setSpacing(Spacing.LG)

        # Early Sharpe
        early_container = QVBoxLayout()
        early_label = QLabel("EARLY")
        early_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_DISABLED};
                font-family: '{Fonts.UI}';
                font-size: 9px;
            }}
        """)
        early_container.addWidget(early_label)
        self._early_value = QLabel("—")
        self._early_value.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.DATA}';
                font-size: 10px;
            }}
        """)
        early_container.addWidget(self._early_value)
        stats.addLayout(early_container)

        # Recent Sharpe
        recent_container = QVBoxLayout()
        recent_label = QLabel("RECENT")
        recent_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_DISABLED};
                font-family: '{Fonts.UI}';
                font-size: 9px;
            }}
        """)
        recent_container.addWidget(recent_label)
        self._recent_value = QLabel("—")
        self._recent_value.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.DATA}';
                font-size: 10px;
            }}
        """)
        recent_container.addWidget(self._recent_value)
        stats.addLayout(recent_container)

        stats.addStretch()
        content_layout.addLayout(stats)

        # Decay indicator
        self._decay_indicator = QFrame()
        self._decay_indicator.setObjectName("decayIndicator")
        indicator_layout = QHBoxLayout(self._decay_indicator)
        indicator_layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        indicator_layout.setSpacing(Spacing.SM)

        self._decay_dot = QLabel()
        self._decay_dot.setFixedSize(8, 8)
        self._decay_dot.setStyleSheet(f"""
            QLabel {{
                background-color: {Colors.SIGNAL_CYAN};
                border-radius: 4px;
            }}
        """)
        indicator_layout.addWidget(self._decay_dot)

        self._decay_text = QLabel("No significant decay")
        self._decay_text.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: 10px;
            }}
        """)
        indicator_layout.addWidget(self._decay_text)
        indicator_layout.addStretch()

        self._decay_pct = QLabel("")
        self._decay_pct.setStyleSheet(f"""
            QLabel {{
                color: {Colors.SIGNAL_CYAN};
                font-family: '{Fonts.DATA}';
                font-size: 10px;
            }}
        """)
        indicator_layout.addWidget(self._decay_pct)

        content_layout.addWidget(self._decay_indicator)

        layout.addWidget(content)
        layout.addStretch()

    def update_metrics(
        self,
        current: float | None,
        early: float | None,
        decay_pct: float | None,
    ) -> None:
        """Update edge decay metrics."""
        if current is not None:
            self._current_value.setText(f"{current:.2f}")
        else:
            self._current_value.setText("—")

        if early is not None:
            self._early_value.setText(f"{early:.2f}")
        else:
            self._early_value.setText("—")

        if current is not None:
            self._recent_value.setText(f"{current:.2f}")
        else:
            self._recent_value.setText("—")

        if decay_pct is not None:
            self._decay_pct.setText(f"{decay_pct:+.1f}%")

            if decay_pct < -30:
                dot_color = Colors.SIGNAL_CORAL
                text = "Significant decay detected"
                text_color = Colors.SIGNAL_CORAL
            elif decay_pct < -10:
                dot_color = Colors.SIGNAL_AMBER
                text = "Moderate decay detected"
                text_color = Colors.SIGNAL_AMBER
            else:
                dot_color = Colors.SIGNAL_CYAN
                text = "Edge stable"
                text_color = Colors.TEXT_SECONDARY

            self._decay_dot.setStyleSheet(f"""
                QLabel {{
                    background-color: {dot_color};
                    border-radius: 4px;
                }}
            """)
            self._decay_text.setText(text)
            self._decay_pct.setStyleSheet(f"""
                QLabel {{
                    color: {text_color};
                    font-family: '{Fonts.DATA}';
                    font-size: 10px;
                }}
            """)
        else:
            self._decay_pct.setText("")
            self._decay_text.setText("Insufficient data")
