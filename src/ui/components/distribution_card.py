"""DistributionCard widget for displaying winner/loser distribution statistics."""

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from src.ui.constants import Colors, Fonts, FontSizes, Spacing

logger = logging.getLogger(__name__)


class _ClickableLabel(QLabel):
    """QLabel that emits a signal when clicked."""

    clicked = pyqtSignal()

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        """Handle mouse press by emitting clicked signal."""
        self.clicked.emit()
        super().mousePressEvent(event)


class DistributionCard(QFrame):
    """Card displaying distribution statistics for winners or losers.

    Displays: count, range (min-max), mean, median, std dev
    With colored border based on card type.
    """

    # Card types
    WINNER = "winner"
    LOSER = "loser"

    # Signals
    view_histogram_clicked = pyqtSignal()  # Emitted when "View Histogram" clicked

    def __init__(
        self,
        card_type: str,  # WINNER or LOSER
        parent: QWidget | None = None,
    ) -> None:
        """Initialize DistributionCard.

        Args:
            card_type: Type of card (WINNER or LOSER).
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._card_type = card_type
        self._suggested_bins: int | None = None
        self._setup_ui()
        self._apply_style()

    @property
    def card_type(self) -> str:
        """Return the card type (WINNER or LOSER) for testing verification."""
        return self._card_type

    def _setup_ui(self) -> None:
        """Set up the widget UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.SM)

        # Header
        header_text = "Winners" if self._card_type == self.WINNER else "Losers"
        header_color = Colors.SIGNAL_CYAN if self._card_type == self.WINNER else Colors.SIGNAL_CORAL
        self._header = QLabel(header_text)
        self._header.setObjectName("header")
        self._header.setStyleSheet(f"""
            color: {header_color};
            font-family: {Fonts.UI};
            font-size: {FontSizes.H2}px;
            font-weight: bold;
        """)
        layout.addWidget(self._header)

        # Stats grid (2 columns: label, value)
        grid = QGridLayout()
        grid.setSpacing(Spacing.SM)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        # Create stat rows
        stats = [
            ("Count:", "countLabel"),
            ("Range:", "rangeLabel"),
            ("Mean:", "meanLabel"),
            ("Median:", "medianLabel"),
            ("Std Dev:", "stdLabel"),
        ]

        self._stat_labels: dict[str, QLabel] = {}
        for row, (label_text, object_name) in enumerate(stats):
            # Label
            label = QLabel(label_text)
            label.setStyleSheet(f"""
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
            """)
            grid.addWidget(label, row, 0)

            # Value
            value_label = QLabel("\u2014")  # Em dash
            value_label.setObjectName(object_name)
            value_label.setStyleSheet(f"""
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.DATA};
                font-size: {FontSizes.BODY}px;
            """)
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            grid.addWidget(value_label, row, 1)
            self._stat_labels[object_name] = value_label

        layout.addLayout(grid)

        # Spacer
        layout.addStretch()

        # View Histogram link
        self._histogram_link = _ClickableLabel("View Histogram")
        self._histogram_link.setObjectName("histogramLink")
        self._histogram_link.setStyleSheet(f"""
            QLabel {{
                color: {Colors.SIGNAL_BLUE};
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
            }}
            QLabel:hover {{
                text-decoration: underline;
            }}
        """)
        self._histogram_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self._histogram_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._histogram_link.clicked.connect(self.view_histogram_clicked.emit)
        layout.addWidget(self._histogram_link)

    def _apply_style(self) -> None:
        """Apply styling with colored border based on card type."""
        border_color = (
            Colors.SIGNAL_CYAN if self._card_type == self.WINNER else Colors.SIGNAL_CORAL
        )
        self.setStyleSheet(f"""
            DistributionCard {{
                background-color: {Colors.BG_ELEVATED};
                border: 2px solid {border_color};
                border-radius: 8px;
            }}
        """)
        self.setMinimumHeight(180)
        self.setMinimumWidth(200)

    def update_stats(
        self,
        count: int | None,
        min_val: float | None,
        max_val: float | None,
        mean: float | None,
        median: float | None,
        std: float | None,
        suggested_bins: int | None = None,
    ) -> None:
        """Update displayed statistics.

        Args:
            count: Number of trades in this category.
            min_val: Minimum gain/loss percentage.
            max_val: Maximum gain/loss percentage.
            mean: Mean gain/loss percentage.
            median: Median gain/loss percentage.
            std: Standard deviation of gains/losses.
            suggested_bins: Suggested number of histogram bins.
        """
        self._suggested_bins = suggested_bins

        # Count
        if count is not None:
            self._stat_labels["countLabel"].setText(f"{count:,}")
        else:
            self._stat_labels["countLabel"].setText("\u2014")

        # Range
        if min_val is not None and max_val is not None:
            self._stat_labels["rangeLabel"].setText(f"{min_val:.2f}% to {max_val:.2f}%")
        else:
            self._stat_labels["rangeLabel"].setText("\u2014")

        # Mean
        if mean is not None:
            self._stat_labels["meanLabel"].setText(f"{mean:.2f}%")
        else:
            self._stat_labels["meanLabel"].setText("\u2014")

        # Median
        if median is not None:
            self._stat_labels["medianLabel"].setText(f"{median:.2f}%")
        else:
            self._stat_labels["medianLabel"].setText("\u2014")

        # Std Dev
        if std is not None:
            self._stat_labels["stdLabel"].setText(f"{std:.2f}%")
        else:
            self._stat_labels["stdLabel"].setText("\u2014")

    def clear(self) -> None:
        """Clear all stats to show em dash."""
        for label in self._stat_labels.values():
            label.setText("\u2014")
        self._suggested_bins = None
