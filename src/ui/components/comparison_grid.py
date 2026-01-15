"""ComparisonGrid widget for displaying 23 metrics with baseline vs filtered comparison."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.ui.constants import Colors, Fonts, FontSizes, Spacing

if TYPE_CHECKING:
    from src.core.models import TradingMetrics

logger = logging.getLogger(__name__)

# Section structure: (section_id, display_title, list of metric field names)
SECTIONS: list[tuple[str, str, list[str]]] = [
    (
        "core_statistics",
        "Core Statistics",
        [
            "num_trades",
            "win_rate",
            "avg_winner",
            "avg_loser",
            "rr_ratio",
            "ev",
            "edge",
            "kelly",
            "fractional_kelly",
            "eg_full_kelly",
            "eg_frac_kelly",
            "eg_flat_stake",
            "median_winner",
            "median_loser",
        ],
    ),  # 14 metrics
    (
        "streak_loss",
        "Streak & Loss",
        [
            "max_consecutive_wins",
            "max_consecutive_losses",
            "max_loss_pct",
        ],
    ),  # 3 metrics
    (
        "flat_stake",
        "Flat Stake",
        [
            "flat_stake_pnl",
            "flat_stake_max_dd",
            "flat_stake_max_dd_pct",
            "flat_stake_dd_duration",
        ],
    ),  # 4 metrics
    (
        "kelly",
        "Compounded Kelly",
        [
            "kelly_pnl",
            "kelly_max_dd",
            "kelly_max_dd_pct",
            "kelly_dd_duration",
        ],
    ),  # 4 metrics
]

# Metric display configuration: field_name -> (label, format_spec, delta_type, improvement)
# delta_type: "pp" (percentage point), "$" (dollar), "ratio", "days", "count"
# improvement: "higher" (higher is better), "lower" (lower is better), "neutral"
METRIC_CONFIG: dict[str, tuple[str, str | None, str, str]] = {
    # Core Statistics
    "num_trades": ("Trades", ",d", "count", "neutral"),
    "win_rate": ("Win Rate", ".1f", "pp", "higher"),
    "avg_winner": ("Avg Winner", ".2f", "pp", "higher"),
    "avg_loser": ("Avg Loser", ".2f", "pp", "higher"),  # Less negative is better
    "rr_ratio": ("R:R Ratio", ".2f", "ratio", "higher"),
    "ev": ("EV", ".2f", "pp", "higher"),
    "edge": ("Edge", ".2f", "pp", "higher"),
    "kelly": ("Kelly %", ".2f", "pp", "higher"),
    "fractional_kelly": ("Frac Kelly %", ".2f", "pp", "higher"),
    "eg_full_kelly": ("EG Full Kelly", ".2f", "pp", "higher"),
    "eg_frac_kelly": ("EG Frac Kelly", ".2f", "pp", "higher"),
    "eg_flat_stake": ("EG Flat Stake", ".2f", "pp", "higher"),
    "median_winner": ("Median Winner", ".2f", "pp", "higher"),
    "median_loser": ("Median Loser", ".2f", "pp", "higher"),  # Less negative is better
    # Streak & Loss
    "max_consecutive_wins": ("Max Win Streak", "d", "count", "higher"),
    "max_consecutive_losses": ("Max Loss Streak", "d", "count", "lower"),
    "max_loss_pct": ("Max Loss %", ".2f", "pp", "lower"),  # Less negative is better
    # Flat Stake
    "flat_stake_pnl": ("Flat Stake PnL", ",.2f", "$", "higher"),
    "flat_stake_max_dd": ("Max DD ($)", ",.2f", "$", "lower"),
    "flat_stake_max_dd_pct": ("Max DD (%)", ".2f", "pp", "lower"),
    "flat_stake_dd_duration": ("DD Duration", None, "days", "lower"),
    # Compounded Kelly
    "kelly_pnl": ("Kelly PnL", ",.2f", "$", "higher"),
    "kelly_max_dd": ("Kelly Max DD ($)", ",.2f", "$", "lower"),
    "kelly_max_dd_pct": ("Kelly Max DD (%)", ".2f", "pp", "lower"),
    "kelly_dd_duration": ("Kelly DD Duration", None, "days", "lower"),
}

# Animation duration for collapse/expand
COLLAPSE_ANIMATION_MS = 150


def _format_value(
    value: float | int | str | None, field_name: str
) -> str:
    """Format a metric value for display.

    Args:
        value: The metric value.
        field_name: Name of the metric field.

    Returns:
        Formatted string for display.
    """
    if value is None:
        return "—"

    config = METRIC_CONFIG.get(field_name)
    if config is None:
        return str(value)

    _, format_spec, delta_type, _ = config

    # Special handling for DD duration fields
    if field_name in ("flat_stake_dd_duration", "kelly_dd_duration"):
        if isinstance(value, int):
            return f"{value} days"
        return str(value)  # "Not recovered" or "Blown"

    if format_spec is None:
        return str(value)

    # Format based on delta type
    if delta_type == "$":
        return f"${value:{format_spec}}"
    elif delta_type == "pp":
        return f"{value:{format_spec}}%"
    else:
        return f"{value:{format_spec}}"


def _calculate_delta(
    baseline: float | int | str | None,
    filtered: float | int | str | None,
    field_name: str,
) -> tuple[float | None, str]:
    """Calculate delta between baseline and filtered values.

    Args:
        baseline: Baseline metric value.
        filtered: Filtered metric value.
        field_name: Name of the metric field.

    Returns:
        Tuple of (delta_value, formatted_display_string).
    """
    # Can't calculate delta if either value is None or string (for duration fields)
    if baseline is None or filtered is None:
        return None, "—"

    # Special handling for DD duration - can't compare strings
    if field_name in ("flat_stake_dd_duration", "kelly_dd_duration") and (
        isinstance(baseline, str) or isinstance(filtered, str)
    ):
        return None, "—"

    # Ensure numeric values
    if not isinstance(baseline, int | float) or not isinstance(filtered, int | float):
        return None, "—"

    delta = filtered - baseline

    config = METRIC_CONFIG.get(field_name)
    if config is None:
        return delta, str(delta)

    _, _, delta_type, _ = config

    # Format delta based on type
    if delta_type == "count":
        if delta > 0:
            return delta, f"+{int(delta):,d}"
        elif delta < 0:
            return delta, f"{int(delta):,d}"
        return 0.0, "0"

    elif delta_type == "pp":
        if delta > 0:
            return delta, f"+{delta:.2f}pp"
        elif delta < 0:
            return delta, f"{delta:.2f}pp"
        return 0.0, "0pp"

    elif delta_type == "$":
        if delta > 0:
            return delta, f"+${delta:,.2f}"
        elif delta < 0:
            return delta, f"-${abs(delta):,.2f}"
        return 0.0, "$0"

    elif delta_type == "ratio":
        if delta > 0:
            return delta, f"+{delta:.2f}"
        elif delta < 0:
            return delta, f"{delta:.2f}"
        return 0.0, "0"

    elif delta_type == "days":
        if delta > 0:
            return delta, f"+{int(delta)} days"
        elif delta < 0:
            return delta, f"{int(delta)} days"
        return 0.0, "0 days"

    return delta, str(delta)


def _get_delta_color(delta: float | None, field_name: str) -> str:
    """Get color for delta indicator based on value and improvement direction.

    Args:
        delta: Delta value.
        field_name: Name of the metric field.

    Returns:
        Hex color code.
    """
    if delta is None or delta == 0:
        return Colors.TEXT_SECONDARY

    config = METRIC_CONFIG.get(field_name)
    if config is None:
        return Colors.TEXT_SECONDARY

    _, _, _, improvement = config

    # num_trades is always neutral
    if improvement == "neutral":
        return Colors.TEXT_SECONDARY

    if improvement == "higher":
        # Higher values are better
        if delta > 0:
            return Colors.SIGNAL_CYAN  # Improvement
        else:
            return Colors.SIGNAL_CORAL  # Decline
    else:  # improvement == "lower"
        # Lower values are better
        if delta < 0:
            return Colors.SIGNAL_CYAN  # Improvement
        else:
            return Colors.SIGNAL_CORAL  # Decline


class _SectionHeader(QFrame):
    """Collapsible section header with toggle functionality."""

    toggled = pyqtSignal(str, bool)  # section_id, expanded

    def __init__(
        self, section_id: str, title: str, parent: QWidget | None = None
    ) -> None:
        """Initialize section header.

        Args:
            section_id: Unique identifier for the section.
            title: Display title for the section.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._section_id = section_id
        self._title = title
        self._expanded = True
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        """Set up the header layout."""
        self.setFixedHeight(32)
        self.setCursor(self.cursor())

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.XS, Spacing.SM, Spacing.XS)
        layout.setSpacing(Spacing.SM)

        # Arrow indicator
        self._arrow = QLabel("▼")
        self._arrow.setObjectName("sectionArrow")
        self._arrow.setFixedWidth(16)
        layout.addWidget(self._arrow)

        # Title
        self._title_label = QLabel(self._title)
        self._title_label.setObjectName("sectionTitle")
        layout.addWidget(self._title_label)

        layout.addStretch()

    def _apply_style(self) -> None:
        """Apply styling to the header."""
        self.setStyleSheet(f"""
            _SectionHeader {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: 4px;
            }}
            _SectionHeader:hover {{
                background-color: {Colors.BG_BORDER};
            }}
            QLabel#sectionArrow {{
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.UI};
                font-size: 10px;
            }}
            QLabel#sectionTitle {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
                font-weight: bold;
            }}
        """)

    def mousePressEvent(self, event: object) -> None:
        """Handle mouse click to toggle section."""
        self._expanded = not self._expanded
        self._arrow.setText("▼" if self._expanded else "▶")
        self.toggled.emit(self._section_id, self._expanded)

    @property
    def expanded(self) -> bool:
        """Return whether section is expanded."""
        return self._expanded

    def set_expanded(self, expanded: bool) -> None:
        """Set expansion state.

        Args:
            expanded: Whether section should be expanded.
        """
        self._expanded = expanded
        self._arrow.setText("▼" if self._expanded else "▶")


class _ComparisonRow(QFrame):
    """Single row displaying metric name, baseline, filtered, and delta values."""

    def __init__(self, field_name: str, parent: QWidget | None = None) -> None:
        """Initialize comparison row.

        Args:
            field_name: Name of the metric field.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._field_name = field_name
        self._config = METRIC_CONFIG.get(field_name, ("Unknown", None, "count", "neutral"))
        self._setup_ui()
        self._apply_style()
        self.clear()

    def _setup_ui(self) -> None:
        """Set up the 4-column layout."""
        self.setFixedHeight(28)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.XS, Spacing.SM, Spacing.XS)
        layout.setSpacing(Spacing.SM)

        # Column 1: Metric name (left-aligned)
        label, _, _, _ = self._config
        self._name_label = QLabel(label)
        self._name_label.setObjectName("metricName")
        self._name_label.setFixedWidth(140)
        layout.addWidget(self._name_label)

        # Column 2: Baseline value (right-aligned)
        self._baseline_label = QLabel("—")
        self._baseline_label.setObjectName("baselineValue")
        self._baseline_label.setFixedWidth(100)
        self._baseline_label.setAlignment(
            self._baseline_label.alignment()
        )
        layout.addWidget(self._baseline_label)

        # Column 3: Filtered value (right-aligned)
        self._filtered_label = QLabel("—")
        self._filtered_label.setObjectName("filteredValue")
        self._filtered_label.setFixedWidth(100)
        layout.addWidget(self._filtered_label)

        # Column 4: Delta value with arrow + color (right-aligned)
        self._delta_label = QLabel("—")
        self._delta_label.setObjectName("deltaValue")
        self._delta_label.setFixedWidth(100)
        layout.addWidget(self._delta_label)

        layout.addStretch()

    def _apply_style(self) -> None:
        """Apply base styling to the row."""
        self.setStyleSheet(f"""
            _ComparisonRow {{
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
        delta, delta_text = _calculate_delta(baseline_val, filtered_val, self._field_name)
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
        """Clear filtered and delta values, keep baseline."""
        self._filtered_label.setText("—")
        self._delta_label.setText("—")
        self._delta_label.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-family: {Fonts.DATA};
            font-size: {FontSizes.BODY}px;
            qproperty-alignment: 'AlignRight | AlignVCenter';
        """)


class _SectionContent(QWidget):
    """Container for section rows with animation support."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize section content container."""
        super().__init__(parent)
        self._rows: list[_ComparisonRow] = []
        self._expanded = True
        self._animation: QPropertyAnimation | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the content layout."""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

    def add_row(self, row: _ComparisonRow) -> None:
        """Add a row to the section."""
        self._rows.append(row)
        self._layout.addWidget(row)

    def get_rows(self) -> list[_ComparisonRow]:
        """Return list of rows in this section."""
        return self._rows

    def set_expanded(self, expanded: bool, animate: bool = True) -> None:
        """Set expansion state with optional animation.

        Args:
            expanded: Whether to expand or collapse.
            animate: Whether to animate the transition.
        """
        if self._expanded == expanded:
            return

        self._expanded = expanded

        if not animate:
            self.setMaximumHeight(16777215 if expanded else 0)
            self.setVisible(expanded)
            return

        # Stop any existing animation
        if self._animation is not None:
            self._animation.stop()

        # Calculate heights
        content_height = sum(row.height() for row in self._rows)
        start_height = self.height() if not expanded else 0
        end_height = content_height if expanded else 0

        # Make visible before expanding
        if expanded:
            self.setVisible(True)
            self.setMaximumHeight(0)

        # Create and configure animation
        self._animation = QPropertyAnimation(self, b"maximumHeight")
        self._animation.setDuration(COLLAPSE_ANIMATION_MS)
        self._animation.setStartValue(start_height)
        self._animation.setEndValue(end_height)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Hide after collapsing
        if not expanded:
            self._animation.finished.connect(lambda: self.setVisible(False))

        self._animation.start()

    @property
    def expanded(self) -> bool:
        """Return whether section is expanded."""
        return self._expanded


class ComparisonGrid(QFrame):
    """Grid displaying 23 metrics with baseline vs filtered comparison.

    Organized into 4 collapsible sections:
    - Core Statistics (12 metrics)
    - Streak & Loss (3 metrics)
    - Flat Stake (4 metrics)
    - Compounded Kelly (4 metrics)
    """

    section_toggled = pyqtSignal(str, bool)  # section_id, expanded

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize ComparisonGrid.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._sections: dict[str, tuple[_SectionHeader, _SectionContent]] = {}
        self._rows: dict[str, _ComparisonRow] = {}
        self._section_states: dict[str, bool] = {}
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        """Set up the grid layout with collapsible sections."""
        self.setObjectName("comparisonGrid")

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(Spacing.SM)

        # Column headers
        header_widget = QFrame()
        header_widget.setFixedHeight(24)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(Spacing.SM, 0, Spacing.SM, 0)
        header_layout.setSpacing(Spacing.SM)

        # Header labels
        name_header = QLabel("Metric")
        name_header.setObjectName("columnHeader")
        name_header.setFixedWidth(140)
        header_layout.addWidget(name_header)

        baseline_header = QLabel("Baseline")
        baseline_header.setObjectName("columnHeader")
        baseline_header.setFixedWidth(100)
        header_layout.addWidget(baseline_header)

        filtered_header = QLabel("Filtered")
        filtered_header.setObjectName("columnHeader")
        filtered_header.setFixedWidth(100)
        header_layout.addWidget(filtered_header)

        delta_header = QLabel("Delta")
        delta_header.setObjectName("columnHeader")
        delta_header.setFixedWidth(100)
        header_layout.addWidget(delta_header)

        header_layout.addStretch()
        main_layout.addWidget(header_widget)

        # Scroll area for sections
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(
            scroll_area.horizontalScrollBarPolicy()
        )

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(Spacing.SM)

        # Create sections
        for section_id, title, metrics in SECTIONS:
            # Section header
            header = _SectionHeader(section_id, title)
            header.toggled.connect(self._on_section_toggled)
            scroll_layout.addWidget(header)

            # Section content
            content = _SectionContent()
            for field_name in metrics:
                row = _ComparisonRow(field_name)
                content.add_row(row)
                self._rows[field_name] = row
            scroll_layout.addWidget(content)

            self._sections[section_id] = (header, content)
            self._section_states[section_id] = True  # Default expanded

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, stretch=1)

    def _apply_style(self) -> None:
        """Apply styling to the grid."""
        self.setStyleSheet(f"""
            QFrame#comparisonGrid {{
                background-color: {Colors.BG_SURFACE};
            }}
            QLabel#columnHeader {{
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.UI};
                font-size: 11px;
                font-weight: bold;
                qproperty-alignment: 'AlignRight | AlignVCenter';
            }}
            QLabel#columnHeader:first-child {{
                qproperty-alignment: 'AlignLeft | AlignVCenter';
            }}
            QScrollArea {{
                background-color: transparent;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}
        """)

    def _on_section_toggled(self, section_id: str, expanded: bool) -> None:
        """Handle section header toggle.

        Args:
            section_id: ID of the toggled section.
            expanded: New expansion state.
        """
        if section_id in self._sections:
            _, content = self._sections[section_id]
            content.set_expanded(expanded, animate=True)
            self._section_states[section_id] = expanded
            self.section_toggled.emit(section_id, expanded)

    def toggle_section(self, section_id: str) -> None:
        """Toggle a section's expanded state.

        Args:
            section_id: ID of the section to toggle.
        """
        if section_id in self._sections:
            header, content = self._sections[section_id]
            new_state = not self._section_states.get(section_id, True)
            header.set_expanded(new_state)
            content.set_expanded(new_state, animate=True)
            self._section_states[section_id] = new_state

    def set_values(
        self,
        baseline: TradingMetrics,
        filtered: TradingMetrics | None = None,
    ) -> None:
        """Update all rows with baseline and filtered values.

        Args:
            baseline: Baseline metrics (full dataset).
            filtered: Filtered metrics, or None if no filter applied.
        """
        count = 0
        for field_name, row in self._rows.items():
            baseline_val = getattr(baseline, field_name, None)
            filtered_val = getattr(filtered, field_name, None) if filtered else None
            row.set_values(baseline_val, filtered_val)
            count += 1

        logger.debug("ComparisonGrid updated: %d metrics", count)

    def clear(self) -> None:
        """Clear filtered and delta columns, showing baseline only with dashes."""
        for row in self._rows.values():
            row.clear()

    def get_section_state(self, section_id: str) -> bool:
        """Get expansion state of a section.

        Args:
            section_id: ID of the section.

        Returns:
            True if expanded, False if collapsed.
        """
        return self._section_states.get(section_id, True)
