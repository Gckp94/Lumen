# src/ui/components/comparison_panel.py
"""Comparison panel for baseline vs combined metrics.

Displays two columns of metrics side-by-side with delta indicators.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.ui.constants import Colors, Fonts, Spacing


class ComparisonRow(QFrame):
    """Single row comparing baseline vs combined metric."""

    def __init__(
        self,
        label: str,
        tooltip: str = "",
        higher_is_better: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize comparison row.

        Args:
            label: Metric label.
            tooltip: Tooltip text.
            higher_is_better: True if higher values are better.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._label_text = label
        self._higher_is_better = higher_is_better
        self._setup_ui()
        if tooltip:
            self.setToolTip(tooltip)

    def _setup_ui(self) -> None:
        """Set up the row layout."""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, Spacing.XS, 0, Spacing.XS)
        layout.setSpacing(Spacing.MD)

        # Label (left)
        self._label = QLabel(self._label_text)
        self._label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: 12px;
            }}
        """)
        self._label.setFixedWidth(140)
        layout.addWidget(self._label)

        # Baseline value (center-left)
        self._baseline = QLabel("—")
        self._baseline.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.DATA}';
                font-size: 14px;
            }}
        """)
        self._baseline.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._baseline.setFixedWidth(100)
        layout.addWidget(self._baseline)

        # Arrow/Delta indicator (center)
        self._delta = QLabel("")
        self._delta.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.DATA}';
                font-size: 12px;
            }}
        """)
        self._delta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._delta.setFixedWidth(80)
        layout.addWidget(self._delta)

        # Combined value (center-right)
        self._combined = QLabel("—")
        self._combined.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.DATA}';
                font-size: 14px;
            }}
        """)
        self._combined.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._combined.setFixedWidth(100)
        layout.addWidget(self._combined)

        layout.addStretch()

    def set_values(
        self,
        baseline: str | None,
        combined: str | None,
        baseline_raw: float | None = None,
        combined_raw: float | None = None,
    ) -> None:
        """Update both values and calculate delta.

        Args:
            baseline: Formatted baseline value.
            combined: Formatted combined value.
            baseline_raw: Raw numeric baseline value for comparison.
            combined_raw: Raw numeric combined value for comparison.
        """
        self._baseline.setText(baseline or "—")
        self._combined.setText(combined or "—")

        # Calculate delta indicator
        if baseline_raw is not None and combined_raw is not None:
            diff = combined_raw - baseline_raw
            if diff > 0:
                arrow = "▲"
                is_better = self._higher_is_better
            elif diff < 0:
                arrow = "▼"
                is_better = not self._higher_is_better
            else:
                arrow = "="
                is_better = None

            # Format delta
            if abs(diff) < 0.01:
                delta_text = arrow
            else:
                delta_text = f"{arrow} {abs(diff):.2f}"

            # Color based on improvement
            if is_better is True:
                color = Colors.SIGNAL_CYAN
            elif is_better is False:
                color = Colors.SIGNAL_CORAL
            else:
                color = Colors.TEXT_SECONDARY

            self._delta.setText(delta_text)
            self._delta.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-family: '{Fonts.DATA}';
                    font-size: 12px;
                }}
            """)
        else:
            self._delta.setText("")


class ComparisonPanel(QFrame):
    """Panel comparing baseline vs combined portfolio metrics."""

    def __init__(
        self,
        title: str,
        metrics: list[tuple[str, str, str, bool]],  # (key, label, tooltip, higher_is_better)
        parent: QWidget | None = None,
    ) -> None:
        """Initialize comparison panel.

        Args:
            title: Panel title.
            metrics: List of metric definitions.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._title = title
        self._metrics = metrics
        self._rows: dict[str, ComparisonRow] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel layout."""
        self.setObjectName("comparisonPanel")
        self.setStyleSheet(f"""
            QFrame#comparisonPanel {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.SM)

        # Header
        header = QHBoxLayout()
        header.setSpacing(Spacing.MD)

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
        title_label.setFixedWidth(140)
        header.addWidget(title_label)

        # Column headers
        baseline_header = QLabel("Baseline")
        baseline_header.setStyleSheet(f"""
            QLabel {{
                color: {Colors.SIGNAL_BLUE};
                font-family: '{Fonts.UI}';
                font-size: 11px;
                font-weight: 600;
            }}
        """)
        baseline_header.setAlignment(Qt.AlignmentFlag.AlignRight)
        baseline_header.setFixedWidth(100)
        header.addWidget(baseline_header)

        delta_header = QLabel("Delta")
        delta_header.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: 11px;
            }}
        """)
        delta_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        delta_header.setFixedWidth(80)
        header.addWidget(delta_header)

        combined_header = QLabel("Combined")
        combined_header.setStyleSheet(f"""
            QLabel {{
                color: {Colors.SIGNAL_CYAN};
                font-family: '{Fonts.UI}';
                font-size: 11px;
                font-weight: 600;
            }}
        """)
        combined_header.setAlignment(Qt.AlignmentFlag.AlignLeft)
        combined_header.setFixedWidth(100)
        header.addWidget(combined_header)

        header.addStretch()
        layout.addLayout(header)

        # Separator
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {Colors.BG_BORDER};")
        layout.addWidget(separator)

        # Metric rows
        for key, label, tooltip, higher_is_better in self._metrics:
            row = ComparisonRow(label, tooltip, higher_is_better)
            self._rows[key] = row
            layout.addWidget(row)

        layout.addStretch()

    def update_metrics(
        self,
        baseline: dict[str, tuple[str, float | None]],
        combined: dict[str, tuple[str, float | None]],
    ) -> None:
        """Update all metric values.

        Args:
            baseline: Dict mapping key to (formatted_value, raw_value).
            combined: Dict mapping key to (formatted_value, raw_value).
        """
        for key, row in self._rows.items():
            b_formatted, b_raw = baseline.get(key, ("—", None))
            c_formatted, c_raw = combined.get(key, ("—", None))
            row.set_values(b_formatted, c_formatted, b_raw, c_raw)

    def clear(self) -> None:
        """Clear all values."""
        for row in self._rows.values():
            row.set_values(None, None)
