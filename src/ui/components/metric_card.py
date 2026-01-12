"""MetricCard widget for displaying single metric values."""

from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout

from src.ui.constants import Colors, Fonts, Spacing


class MetricCard(QFrame):
    """Display a single metric value with label.

    Variants:
        HERO: 56px value, for Comparison Ribbon (Epic 3)
        STANDARD: 24px value, for metrics grid
        COMPACT: 16px value, for dense displays
    """

    HERO = "hero"
    STANDARD = "standard"
    COMPACT = "compact"

    def __init__(
        self,
        label: str,
        variant: str = STANDARD,
        parent: QFrame | None = None,
    ) -> None:
        """Initialize MetricCard.

        Args:
            label: The label text to display above the value.
            variant: Size variant (HERO, STANDARD, or COMPACT).
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setObjectName("metricCard")
        self._label = label
        self._variant = variant
        self._value: float | int | str | None = None
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        """Set up the widget UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.XS)

        # Label
        self._label_widget = QLabel(self._label)
        self._label_widget.setObjectName("label")
        self._label_widget.setWordWrap(False)
        layout.addWidget(self._label_widget)

        # Value
        self._value_widget = QLabel("\u2014")  # Em dash
        self._value_widget.setObjectName("value")
        layout.addWidget(self._value_widget)

        # Set minimum size based on variant
        min_height = {
            self.HERO: 100,
            self.STANDARD: 70,
            self.COMPACT: 50,
        }.get(self._variant, 70)
        self.setMinimumHeight(min_height)
        self.setMinimumWidth(120)

    def _apply_style(self) -> None:
        """Apply styling based on variant."""
        font_size = {
            self.HERO: 56,
            self.STANDARD: 24,
            self.COMPACT: 16,
        }.get(self._variant, 24)

        self.setStyleSheet(f"""
            QFrame#metricCard {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: 8px;
            }}
            QLabel#label {{
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.UI};
                font-size: 12px;
            }}
            QLabel#value {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.DATA};
                font-size: {font_size}px;
            }}
        """)

    def update_value(
        self,
        value: float | int | str | None,
        format_spec: str | None = ".2f",
        color: str | None = None,
    ) -> None:
        """Update displayed value.

        Args:
            value: The value to display (None shows em dash).
            format_spec: Format specification for the value (None for pre-formatted strings).
            color: Optional color override for the value text.
        """
        self._value = value

        if value is None:
            self._value_widget.setText("\u2014")  # Em dash
            self._update_value_color(Colors.TEXT_PRIMARY)
            return

        # Format value
        if isinstance(value, str):
            text = value
        elif format_spec is None:
            text = str(value)
        else:
            try:
                text = f"{value:,}" if isinstance(value, int) else f"{value:{format_spec}}"
            except (ValueError, TypeError):
                text = str(value)

        self._value_widget.setText(text)

        # Use color override if provided
        if color is not None:
            self._update_value_color(color)
            return

        # Color code based on sign
        if isinstance(value, int | float):
            if value > 0:
                display_color = Colors.SIGNAL_CYAN
            elif value < 0:
                display_color = Colors.SIGNAL_CORAL
            else:
                display_color = Colors.TEXT_PRIMARY
        else:
            display_color = Colors.TEXT_PRIMARY

        self._update_value_color(display_color)

    def _update_value_color(self, color: str) -> None:
        """Update the value label color.

        Args:
            color: The hex color code to apply.
        """
        font_size = {
            self.HERO: 56,
            self.STANDARD: 24,
            self.COMPACT: 16,
        }.get(self._variant, 24)

        self._value_widget.setStyleSheet(f"""
            color: {color};
            font-family: {Fonts.DATA};
            font-size: {font_size}px;
        """)
