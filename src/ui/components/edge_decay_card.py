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

        # Divider line
        divider1 = QFrame()
        divider1.setFixedHeight(1)
        divider1.setStyleSheet(f"background-color: {Colors.BG_BORDER};")
        content_layout.addWidget(divider1)

        # Avg Gain row
        avg_gain_header = QHBoxLayout()
        avg_gain_label = QLabel("Avg Gain %")
        avg_gain_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: 11px;
            }}
        """)
        avg_gain_header.addWidget(avg_gain_label)
        avg_gain_header.addStretch()

        self._avg_gain_change = QLabel("—")
        self._avg_gain_change.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.DATA}';
                font-size: 12px;
                font-weight: 600;
            }}
        """)
        avg_gain_header.addWidget(self._avg_gain_change)
        content_layout.addLayout(avg_gain_header)

        # Avg Gain early/recent stats
        avg_stats = QHBoxLayout()
        avg_stats.setSpacing(Spacing.LG)

        avg_early_container = QVBoxLayout()
        avg_early_label = QLabel("EARLY")
        avg_early_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_DISABLED};
                font-family: '{Fonts.UI}';
                font-size: 9px;
            }}
        """)
        avg_early_container.addWidget(avg_early_label)
        self._avg_early_value = QLabel("—")
        self._avg_early_value.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.DATA}';
                font-size: 10px;
            }}
        """)
        avg_early_container.addWidget(self._avg_early_value)
        avg_stats.addLayout(avg_early_container)

        avg_recent_container = QVBoxLayout()
        avg_recent_label = QLabel("RECENT")
        avg_recent_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_DISABLED};
                font-family: '{Fonts.UI}';
                font-size: 9px;
            }}
        """)
        avg_recent_container.addWidget(avg_recent_label)
        self._avg_recent_value = QLabel("—")
        self._avg_recent_value.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.DATA}';
                font-size: 10px;
            }}
        """)
        avg_recent_container.addWidget(self._avg_recent_value)
        avg_stats.addLayout(avg_recent_container)

        avg_stats.addStretch()
        content_layout.addLayout(avg_stats)

        # Divider line
        divider2 = QFrame()
        divider2.setFixedHeight(1)
        divider2.setStyleSheet(f"background-color: {Colors.BG_BORDER};")
        content_layout.addWidget(divider2)

        # Median Gain row
        median_gain_header = QHBoxLayout()
        median_gain_label = QLabel("Median Gain %")
        median_gain_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: 11px;
            }}
        """)
        median_gain_header.addWidget(median_gain_label)
        median_gain_header.addStretch()

        self._median_gain_change = QLabel("—")
        self._median_gain_change.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.DATA}';
                font-size: 12px;
                font-weight: 600;
            }}
        """)
        median_gain_header.addWidget(self._median_gain_change)
        content_layout.addLayout(median_gain_header)

        # Median Gain early/recent stats
        median_stats = QHBoxLayout()
        median_stats.setSpacing(Spacing.LG)

        median_early_container = QVBoxLayout()
        median_early_label = QLabel("EARLY")
        median_early_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_DISABLED};
                font-family: '{Fonts.UI}';
                font-size: 9px;
            }}
        """)
        median_early_container.addWidget(median_early_label)
        self._median_early_value = QLabel("—")
        self._median_early_value.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.DATA}';
                font-size: 10px;
            }}
        """)
        median_early_container.addWidget(self._median_early_value)
        median_stats.addLayout(median_early_container)

        median_recent_container = QVBoxLayout()
        median_recent_label = QLabel("RECENT")
        median_recent_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_DISABLED};
                font-family: '{Fonts.UI}';
                font-size: 9px;
            }}
        """)
        median_recent_container.addWidget(median_recent_label)
        self._median_recent_value = QLabel("—")
        self._median_recent_value.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.DATA}';
                font-size: 10px;
            }}
        """)
        median_recent_container.addWidget(self._median_recent_value)
        median_stats.addLayout(median_recent_container)

        median_stats.addStretch()
        content_layout.addLayout(median_stats)

        layout.addWidget(content)
        layout.addStretch()

    def update_metrics(
        self,
        current: float | None,
        early: float | None,
        decay_pct: float | None,
        avg_gain_early: float | None = None,
        avg_gain_recent: float | None = None,
        avg_gain_change_pct: float | None = None,
        median_gain_early: float | None = None,
        median_gain_recent: float | None = None,
        median_gain_change_pct: float | None = None,
    ) -> None:
        """Update edge decay metrics including Sharpe and gain metrics."""
        # Existing Sharpe metric updates
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

            dot_color = self._get_change_color(decay_pct)
            if decay_pct < -30:
                text = "Significant decay detected"
                text_color = Colors.SIGNAL_CORAL
            elif decay_pct < -10:
                text = "Moderate decay detected"
                text_color = Colors.SIGNAL_AMBER
            else:
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

        # Avg gain metric updates
        if avg_gain_early is not None:
            self._avg_early_value.setText(f"{avg_gain_early:.2f}%")
        else:
            self._avg_early_value.setText("—")

        if avg_gain_recent is not None:
            self._avg_recent_value.setText(f"{avg_gain_recent:.2f}%")
        else:
            self._avg_recent_value.setText("—")

        if avg_gain_change_pct is not None:
            self._avg_gain_change.setText(f"{avg_gain_change_pct:+.1f}%")
            color = self._get_change_color(avg_gain_change_pct)
            self._avg_gain_change.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-family: '{Fonts.DATA}';
                    font-size: 12px;
                    font-weight: 600;
                }}
            """)
        else:
            self._avg_gain_change.setText("—")
            self._avg_gain_change.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.TEXT_SECONDARY};
                    font-family: '{Fonts.DATA}';
                    font-size: 12px;
                    font-weight: 600;
                }}
            """)

        # Median gain metric updates
        if median_gain_early is not None:
            self._median_early_value.setText(f"{median_gain_early:.2f}%")
        else:
            self._median_early_value.setText("—")

        if median_gain_recent is not None:
            self._median_recent_value.setText(f"{median_gain_recent:.2f}%")
        else:
            self._median_recent_value.setText("—")

        if median_gain_change_pct is not None:
            self._median_gain_change.setText(f"{median_gain_change_pct:+.1f}%")
            color = self._get_change_color(median_gain_change_pct)
            self._median_gain_change.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-family: '{Fonts.DATA}';
                    font-size: 12px;
                    font-weight: 600;
                }}
            """)
        else:
            self._median_gain_change.setText("—")
            self._median_gain_change.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.TEXT_SECONDARY};
                    font-family: '{Fonts.DATA}';
                    font-size: 12px;
                    font-weight: 600;
                }}
            """)

    def _get_change_color(self, change_pct: float) -> str:
        """Get color for change percentage based on severity."""
        if change_pct < -30:
            return Colors.SIGNAL_CORAL
        elif change_pct < -10:
            return Colors.SIGNAL_AMBER
        else:
            return Colors.SIGNAL_CYAN
