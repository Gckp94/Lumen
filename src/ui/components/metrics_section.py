# src/ui/components/metrics_section.py
"""Metrics section component for Portfolio Metrics tab.

Displays a titled group of metrics with consistent styling.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.ui.constants import Colors, Fonts, Spacing


class MetricDisplay(QFrame):
    """Single metric display with label and value."""

    def __init__(
        self,
        label: str,
        tooltip: str = "",
        parent: QWidget | None = None,
    ) -> None:
        """Initialize metric display.

        Args:
            label: Metric label text.
            tooltip: Tooltip description.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._label_text = label
        self._setup_ui()
        if tooltip:
            self.setToolTip(tooltip)

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        self.setObjectName("metricDisplay")
        self.setStyleSheet(f"""
            QFrame#metricDisplay {{
                background-color: {Colors.BG_ELEVATED};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 8px;
                padding: {Spacing.SM}px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        layout.setSpacing(Spacing.XS)

        # Label
        self._label = QLabel(self._label_text)
        self._label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: 11px;
                font-weight: 500;
            }}
        """)
        layout.addWidget(self._label)

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

    def set_value(self, value: str, positive: bool | None = None) -> None:
        """Update the displayed value.

        Args:
            value: Formatted value string.
            positive: True for positive color, False for negative, None for neutral.
        """
        self._value.setText(value)

        if positive is True:
            color = Colors.SIGNAL_CYAN
        elif positive is False:
            color = Colors.SIGNAL_CORAL
        else:
            color = Colors.TEXT_PRIMARY

        self._value.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-family: '{Fonts.DATA}';
                font-size: 18px;
                font-weight: 600;
            }}
        """)


class MetricsSection(QFrame):
    """Section containing multiple metrics with a title."""

    def __init__(
        self,
        title: str,
        metrics: list[tuple[str, str, str]],  # (key, label, tooltip)
        columns: int = 3,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize metrics section.

        Args:
            title: Section title.
            metrics: List of (key, label, tooltip) tuples.
            columns: Number of columns in grid.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._title = title
        self._metrics = metrics
        self._columns = columns
        self._displays: dict[str, MetricDisplay] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        self.setObjectName("metricsSection")
        self.setStyleSheet(f"""
            QFrame#metricsSection {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # Title
        title_label = QLabel(self._title)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: 14px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
        """)
        layout.addWidget(title_label)

        # Metrics grid
        grid = QGridLayout()
        grid.setSpacing(Spacing.SM)

        for i, (key, label, tooltip) in enumerate(self._metrics):
            row, col = divmod(i, self._columns)
            display = MetricDisplay(label, tooltip)
            self._displays[key] = display
            grid.addWidget(display, row, col)

        # Set equal column stretch
        for col in range(self._columns):
            grid.setColumnStretch(col, 1)

        layout.addLayout(grid)

    def update_metrics(self, values: dict[str, tuple[str, bool | None]]) -> None:
        """Update metric values.

        Args:
            values: Dict mapping key to (formatted_value, is_positive).
        """
        for key, (value, positive) in values.items():
            if key in self._displays:
                self._displays[key].set_value(value, positive)

    def clear(self) -> None:
        """Clear all metric values."""
        for display in self._displays.values():
            display.set_value("—", None)
