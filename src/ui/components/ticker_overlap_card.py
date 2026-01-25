"""Ticker overlap analysis card."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.ui.constants import Colors, Fonts, Spacing


class TickerOverlapCard(QFrame):
    """Card displaying ticker overlap analysis."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("tickerOverlapCard")
        self.setStyleSheet(f"""
            QFrame#tickerOverlapCard {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # Title
        title = QLabel("TICKER OVERLAP")
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

        # Stats grid
        grid = QGridLayout()
        grid.setSpacing(Spacing.SM)

        # Overlap percentage
        self._overlap_pct = self._create_stat_card("Overlap %", "—")
        grid.addWidget(self._overlap_pct, 0, 0)

        # Shared tickers
        self._shared_count = self._create_stat_card("Shared Tickers", "—")
        grid.addWidget(self._shared_count, 0, 1)

        # Concurrent exposure (full width)
        self._concurrent = self._create_stat_card("Concurrent Exposure", "—")
        grid.addWidget(self._concurrent, 1, 0, 1, 2)

        layout.addLayout(grid)
        layout.addStretch()

    def _create_stat_card(self, label: str, value: str) -> QFrame:
        """Create a stat card widget."""
        card = QFrame()
        card.setObjectName("statCard")
        card.setStyleSheet(f"""
            QFrame#statCard {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: 4px;
            }}
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        card_layout.setSpacing(4)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        value_label = QLabel(value)
        value_label.setObjectName("value")
        value_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.DATA}';
                font-size: 24px;
                font-weight: 600;
            }}
        """)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(value_label)

        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_DISABLED};
                font-family: '{Fonts.UI}';
                font-size: 10px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
        """)
        label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(label_widget)

        return card

    def update_metrics(
        self,
        overlap: dict[str, int | float] | None,
        concurrent: dict[str, int | float] | None,
    ) -> None:
        """Update ticker overlap metrics."""
        if overlap:
            overlap_pct = overlap.get("overlap_pct")
            shared = overlap.get("overlapping_count")

            if overlap_pct is not None:
                value_label = self._overlap_pct.findChild(QLabel, "value")
                if value_label:
                    value_label.setText(f"{overlap_pct:.1f}%")

            if shared is not None:
                value_label = self._shared_count.findChild(QLabel, "value")
                if value_label:
                    value_label.setText(str(shared))
        else:
            # No ticker data available
            for card in [self._overlap_pct, self._shared_count]:
                value_label = card.findChild(QLabel, "value")
                if value_label:
                    value_label.setText("N/A")

        if concurrent:
            concurrent_pct = concurrent.get("concurrent_pct")
            if concurrent_pct is not None:
                value_label = self._concurrent.findChild(QLabel, "value")
                if value_label:
                    value_label.setText(f"{concurrent_pct:.1f}%")
                    # Color based on exposure level
                    if concurrent_pct > 20:
                        color = Colors.SIGNAL_CORAL
                    elif concurrent_pct > 10:
                        color = Colors.SIGNAL_AMBER
                    else:
                        color = Colors.TEXT_PRIMARY
                    value_label.setStyleSheet(f"""
                        QLabel {{
                            color: {color};
                            font-family: '{Fonts.DATA}';
                            font-size: 24px;
                            font-weight: 600;
                        }}
                    """)
        else:
            value_label = self._concurrent.findChild(QLabel, "value")
            if value_label:
                value_label.setText("N/A")
