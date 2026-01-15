"""MetricsSectionCard component for displaying a single metrics section.

Part of the horizontal 4-column layout refactoring. Each card displays
a section with header and scrollable rows of metrics with baseline,
filtered, and delta values.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.ui.components.comparison_grid import (
    _calculate_delta,
    _format_value,
    _get_delta_color,
)
from src.ui.constants import Colors, Fonts, FontSizes, Spacing

# Column widths - wider to fit values like $1,234,567.89
COL_WIDTH_NAME = 130
COL_WIDTH_VALUE = 120  # Increased from 100 to fit millions


class _MetricRow(QFrame):
    """Single row displaying metric name, baseline, filtered, and delta values."""

    def __init__(
        self, field_name: str, display_label: str, parent: QWidget | None = None
    ) -> None:
        """Initialize metric row.

        Args:
            field_name: Name of the metric field (e.g., "num_trades").
            display_label: Display label for the metric (e.g., "Trades").
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._field_name = field_name
        self._display_label = display_label
        self._setup_ui()
        self._apply_style()
        self.clear()

    def _setup_ui(self) -> None:
        """Set up the 4-column layout."""
        self.setFixedHeight(26)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, 2, Spacing.SM, 2)
        layout.setSpacing(Spacing.SM)

        # Column 1: Metric name (left-aligned)
        self._name_label = QLabel(self._display_label)
        self._name_label.setObjectName("metricName")
        self._name_label.setFixedWidth(COL_WIDTH_NAME)
        layout.addWidget(self._name_label)

        # Column 2: Baseline value (right-aligned)
        self._baseline_label = QLabel("—")
        self._baseline_label.setObjectName("baselineValue")
        self._baseline_label.setFixedWidth(COL_WIDTH_VALUE)
        self._baseline_label.setMinimumWidth(COL_WIDTH_VALUE)
        layout.addWidget(self._baseline_label)

        # Column 3: Filtered value (right-aligned)
        self._filtered_label = QLabel("—")
        self._filtered_label.setObjectName("filteredValue")
        self._filtered_label.setFixedWidth(COL_WIDTH_VALUE)
        self._filtered_label.setMinimumWidth(COL_WIDTH_VALUE)
        layout.addWidget(self._filtered_label)

        # Column 4: Delta value with arrow + color (right-aligned)
        self._delta_label = QLabel("—")
        self._delta_label.setObjectName("deltaValue")
        self._delta_label.setFixedWidth(COL_WIDTH_VALUE)
        layout.addWidget(self._delta_label)

        layout.addStretch()

    def _apply_style(self) -> None:
        """Apply base styling to the row."""
        self.setStyleSheet(f"""
            _MetricRow {{
                background-color: transparent;
            }}
            QLabel#metricName {{
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
            }}
            QLabel#baselineValue {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.DATA};
                font-size: {FontSizes.BODY}px;
                qproperty-alignment: 'AlignRight | AlignVCenter';
            }}
            QLabel#filteredValue {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.DATA};
                font-size: {FontSizes.BODY}px;
                qproperty-alignment: 'AlignRight | AlignVCenter';
            }}
            QLabel#deltaValue {{
                font-family: {Fonts.DATA};
                font-size: {FontSizes.BODY}px;
                qproperty-alignment: 'AlignRight | AlignVCenter';
            }}
        """)

    def set_values(
        self,
        baseline_val: float | int | str | None,
        filtered_val: float | int | str | None,
    ) -> None:
        """Set row values.

        Args:
            baseline_val: Baseline metric value.
            filtered_val: Filtered metric value.
        """
        # Format and display baseline
        baseline_text = _format_value(baseline_val, self._field_name)
        self._baseline_label.setText(baseline_text)

        # Format and display filtered
        if filtered_val is None:
            self._filtered_label.setText("—")
            self._delta_label.setText("—")
            self._delta_label.setStyleSheet(f"""
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.DATA};
                font-size: {FontSizes.BODY}px;
                qproperty-alignment: 'AlignRight | AlignVCenter';
            """)
            return

        filtered_text = _format_value(filtered_val, self._field_name)
        self._filtered_label.setText(filtered_text)

        # Calculate and display delta
        delta, delta_text = _calculate_delta(
            baseline_val, filtered_val, self._field_name
        )
        color = _get_delta_color(delta, self._field_name)

        # Add arrow indicator
        if delta is not None and delta != 0:
            arrow = "▲ " if delta > 0 else "▼ "
            delta_text = f"{arrow}{delta_text}"

        self._delta_label.setText(delta_text)
        self._delta_label.setStyleSheet(f"""
            color: {color};
            font-family: {Fonts.DATA};
            font-size: {FontSizes.BODY}px;
            qproperty-alignment: 'AlignRight | AlignVCenter';
        """)

    def clear(self) -> None:
        """Clear all values, showing dashes."""
        self._baseline_label.setText("—")
        self._filtered_label.setText("—")
        self._delta_label.setText("—")
        self._delta_label.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-family: {Fonts.DATA};
            font-size: {FontSizes.BODY}px;
            qproperty-alignment: 'AlignRight | AlignVCenter';
        """)


class MetricsSectionCard(QFrame):
    """Card displaying a single metrics section with header and scrollable rows.

    Used in the horizontal 4-column layout where each column is a section.
    """

    def __init__(
        self,
        title: str,
        metrics: list[tuple[str, str]],
        parent: QWidget | None = None,
    ) -> None:
        """Initialize MetricsSectionCard.

        Args:
            title: Section title (e.g., "Core Statistics").
            metrics: List of (field_name, display_label) tuples.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._title = title
        self._metrics = metrics
        self._rows: dict[str, _MetricRow] = {}
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        """Set up the card layout with header and rows."""
        self.setObjectName("metricsSectionCard")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        main_layout.setSpacing(Spacing.XS)

        # Section header
        header = QFrame()
        header.setFixedHeight(28)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(Spacing.SM, Spacing.XS, Spacing.SM, Spacing.XS)
        header_layout.setSpacing(0)

        self._title_label = QLabel(self._title)
        self._title_label.setObjectName("sectionTitle")
        header_layout.addWidget(self._title_label)
        header_layout.addStretch()

        main_layout.addWidget(header)

        # Column headers row
        col_header = QFrame()
        col_header.setFixedHeight(22)
        col_header_layout = QHBoxLayout(col_header)
        col_header_layout.setContentsMargins(Spacing.SM, 0, Spacing.SM, 0)
        col_header_layout.setSpacing(Spacing.SM)

        # Metric column header
        metric_header = QLabel("Metric")
        metric_header.setObjectName("columnHeader")
        metric_header.setFixedWidth(COL_WIDTH_NAME)
        col_header_layout.addWidget(metric_header)

        # Baseline column header
        baseline_header = QLabel("Baseline")
        baseline_header.setObjectName("columnHeader")
        baseline_header.setFixedWidth(COL_WIDTH_VALUE)
        col_header_layout.addWidget(baseline_header)

        # Filtered column header
        filtered_header = QLabel("Filtered")
        filtered_header.setObjectName("columnHeader")
        filtered_header.setFixedWidth(COL_WIDTH_VALUE)
        col_header_layout.addWidget(filtered_header)

        # Delta column header
        delta_header = QLabel("Delta")
        delta_header.setObjectName("columnHeader")
        delta_header.setFixedWidth(COL_WIDTH_VALUE)
        col_header_layout.addWidget(delta_header)

        col_header_layout.addStretch()
        main_layout.addWidget(col_header)

        # Scroll area for rows
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(0)

        # Create rows for each metric
        for field_name, display_label in self._metrics:
            row = _MetricRow(field_name, display_label)
            scroll_layout.addWidget(row)
            self._rows[field_name] = row

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, stretch=1)

    def _apply_style(self) -> None:
        """Apply styling to the card."""
        self.setStyleSheet(f"""
            QFrame#metricsSectionCard {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 6px;
            }}
            QLabel#sectionTitle {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
                font-weight: bold;
            }}
            QLabel#columnHeader {{
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.UI};
                font-size: 11px;
                font-weight: bold;
                qproperty-alignment: 'AlignRight | AlignVCenter';
            }}
            QScrollArea {{
                background-color: transparent;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}
        """)

    def set_values(
        self,
        baseline: dict[str, float | int | str | None],
        filtered: dict[str, float | int | str | None] | None = None,
    ) -> None:
        """Update all rows with baseline and filtered values.

        Args:
            baseline: Dict mapping field_name to baseline value.
            filtered: Dict mapping field_name to filtered value, or None.
        """
        for field_name, row in self._rows.items():
            baseline_val = baseline.get(field_name)
            filtered_val = filtered.get(field_name) if filtered else None
            row.set_values(baseline_val, filtered_val)

    def clear(self) -> None:
        """Clear all rows, showing dashes."""
        for row in self._rows.values():
            row.clear()
