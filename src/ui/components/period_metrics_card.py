# src/ui/components/period_metrics_card.py
"""Period metrics card for daily/weekly/monthly statistics.

Displays the 6 period metrics in a compact card format.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.core.portfolio_metrics_calculator import PeriodMetrics
from src.ui.constants import Colors, Fonts, Spacing


class PeriodMetricsCard(QFrame):
    """Card displaying period-based metrics (day/week/month)."""

    METRIC_LABELS = [
        ("avg_green_pct", "Avg Green", "Average return on winning periods", True),
        ("avg_red_pct", "Avg Red", "Average return on losing periods", True),
        ("win_pct", "Win %", "Percentage of winning periods", True),
        ("rr_ratio", "R:R", "Reward to Risk ratio", True),
        ("max_win_pct", "Max Win", "Maximum winning period return", True),
        ("max_loss_pct", "Max Loss", "Maximum losing period return", False),
    ]

    def __init__(
        self,
        title: str,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize period metrics card.

        Args:
            title: Card title (e.g., "Daily", "Weekly", "Monthly").
            parent: Parent widget.
        """
        super().__init__(parent)
        self._title = title
        self._value_labels: dict[str, QLabel] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the card layout."""
        self.setObjectName("periodMetricsCard")
        self.setStyleSheet(f"""
            QFrame#periodMetricsCard {{
                background-color: {Colors.BG_ELEVATED};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 10px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.SM)

        # Title
        title_label = QLabel(self._title)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: 13px;
                font-weight: 600;
            }}
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Metrics grid (2 columns x 3 rows)
        grid = QGridLayout()
        grid.setSpacing(Spacing.SM)

        for i, (key, label, tooltip, _) in enumerate(self.METRIC_LABELS):
            row, col = divmod(i, 2)

            # Container for label + value
            container = QWidget()
            container.setToolTip(tooltip)
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(2)

            # Label
            lbl = QLabel(label)
            lbl.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.TEXT_SECONDARY};
                    font-family: '{Fonts.UI}';
                    font-size: 10px;
                }}
            """)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            container_layout.addWidget(lbl)

            # Value
            val = QLabel("—")
            val.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.TEXT_PRIMARY};
                    font-family: '{Fonts.DATA}';
                    font-size: 14px;
                    font-weight: 500;
                }}
            """)
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            container_layout.addWidget(val)

            self._value_labels[key] = val
            grid.addWidget(container, row, col)

        layout.addLayout(grid)

    def update_metrics(
        self,
        baseline: PeriodMetrics | None,
        combined: PeriodMetrics | None,
    ) -> None:
        """Update displayed metrics.

        Args:
            baseline: Baseline period metrics.
            combined: Combined period metrics (displayed if available, else baseline).
        """
        metrics = combined if combined is not None else baseline

        if metrics is None:
            self.clear()
            return

        for key, _, _, higher_is_better in self.METRIC_LABELS:
            value = getattr(metrics, key, None)
            label = self._value_labels[key]

            if value is None:
                label.setText("—")
                color = Colors.TEXT_PRIMARY
            else:
                # Format value
                if key == "rr_ratio":
                    text = f"{value:.2f}"
                    color = Colors.SIGNAL_CYAN if value > 1 else Colors.SIGNAL_CORAL
                elif key in ("avg_green_pct", "max_win_pct"):
                    text = f"{value:+.2f}%"
                    color = Colors.SIGNAL_CYAN
                elif key in ("avg_red_pct", "max_loss_pct"):
                    text = f"{value:.2f}%"
                    color = Colors.SIGNAL_CORAL
                elif key == "win_pct":
                    text = f"{value:.1f}%"
                    color = Colors.SIGNAL_CYAN if value > 50 else Colors.SIGNAL_CORAL
                else:
                    text = f"{value:.2f}"
                    color = Colors.TEXT_PRIMARY

                label.setText(text)

            label.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-family: '{Fonts.DATA}';
                    font-size: 14px;
                    font-weight: 500;
                }}
            """)

    def clear(self) -> None:
        """Clear all values."""
        for label in self._value_labels.values():
            label.setText("—")
            label.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.TEXT_PRIMARY};
                    font-family: '{Fonts.DATA}';
                    font-size: 14px;
                    font-weight: 500;
                }}
            """)
