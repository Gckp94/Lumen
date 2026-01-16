"""Vertical bar chart component for breakdown visualizations."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPaintEvent
from PyQt6.QtWidgets import QSizePolicy, QWidget

from src.ui.constants import Colors, Fonts


class VerticalBarChart(QWidget):
    """Custom vertical bar chart with labels and gradient coloring.

    Renders a set of vertical bars with labels below and values above.
    Supports gradient coloring based on value magnitude.
    """

    bar_hovered = pyqtSignal(str, float)  # label, value

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        """Initialize the vertical bar chart.

        Args:
            title: Chart title displayed above bars.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._title = title
        self._data: list[tuple[str, float]] = []  # (label, value)
        self._bar_width = 40
        self._bar_spacing = 12
        self._is_percentage = False
        self._is_currency = False
        self._hovered_index: int | None = None
        self.setMouseTracking(True)
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

    def set_data(
        self,
        data: list[tuple[str, float]],
        is_percentage: bool = False,
        is_currency: bool = False,
    ) -> None:
        """Update chart data and trigger repaint.

        Args:
            data: List of (label, value) tuples.
            is_percentage: Whether values are percentages.
            is_currency: Whether values are currency (dollars).
        """
        self._data = data
        self._is_percentage = is_percentage
        self._is_currency = is_currency
        self._update_size()
        self.update()

    def _update_size(self) -> None:
        """Update widget size based on data count."""
        content_width = len(self._data) * (self._bar_width + self._bar_spacing) + 60
        self.setMinimumWidth(max(200, content_width))

    def paintEvent(self, event: QPaintEvent) -> None:
        """Render vertical bars with gradient fills.

        Args:
            event: Paint event.
        """
        from PyQt6.QtCore import QRectF

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Draw title
        title_height = 0
        if self._title:
            title_font = QFont(Fonts.UI, 10)
            title_font.setBold(True)
            painter.setFont(title_font)
            painter.setPen(QColor(Colors.TEXT_SECONDARY))
            painter.drawText(10, 18, self._title)
            title_height = 28

        if not self._data:
            painter.end()
            return

        # Calculate min/max for gradient and bar heights
        values = [v for _, v in self._data if v is not None]
        if not values:
            painter.end()
            return

        min_val = min(values)
        max_val = max(values)

        # Reserve space for labels and values
        label_height = 40
        value_height = 20
        chart_height = height - title_height - label_height - value_height - 20

        # Calculate bar area
        total_bar_width = len(self._data) * (self._bar_width + self._bar_spacing)
        start_x = 10 + self._bar_spacing // 2  # Left-align with small padding

        label_font = QFont(Fonts.UI, 9)
        value_font = QFont(Fonts.DATA, 9)

        # Zero line position (for mixed positive/negative values)
        if min_val >= 0:
            zero_y = height - label_height
        elif max_val <= 0:
            zero_y = title_height + value_height
        else:
            # Mixed: calculate zero position
            range_val = max_val - min_val
            zero_ratio = max_val / range_val
            zero_y = title_height + value_height + int(chart_height * zero_ratio)

        for i, (label, value) in enumerate(self._data):
            x = start_x + i * (self._bar_width + self._bar_spacing)

            # Draw label below
            painter.setFont(label_font)
            painter.setPen(QColor(Colors.TEXT_PRIMARY))
            label_rect = QRectF(x - 5, height - label_height + 5, self._bar_width + 10, label_height)
            painter.drawText(
                label_rect,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                label,
            )

            if value is None:
                continue

            # Calculate bar height
            if max_val == min_val:
                bar_height = chart_height * 0.5
            elif min_val >= 0:
                bar_height = (value / max_val) * chart_height if max_val > 0 else 0
            elif max_val <= 0:
                bar_height = (abs(value) / abs(min_val)) * chart_height if min_val < 0 else 0
            else:
                range_val = max_val - min_val
                bar_height = (abs(value) / range_val) * chart_height

            bar_height = max(2, int(bar_height))

            # Calculate gradient color
            bar_color = self._calculate_gradient_color(value, min_val, max_val)

            # Draw bar
            if value >= 0:
                bar_y = zero_y - bar_height
            else:
                bar_y = zero_y

            # Highlight on hover
            if i == self._hovered_index:
                hover_rect = QRectF(x - 3, bar_y - 3, self._bar_width + 6, bar_height + 6)
                painter.fillRect(hover_rect, QColor(Colors.BG_ELEVATED))

            bar_rect = QRectF(x, bar_y, self._bar_width, bar_height)
            painter.fillRect(bar_rect, bar_color)

            # Draw value above/below bar
            painter.setFont(value_font)
            painter.setPen(QColor(Colors.TEXT_PRIMARY))
            value_text = self._format_value(value)
            if value >= 0:
                value_rect = QRectF(x - 10, bar_y - 18, self._bar_width + 20, 16)
            else:
                value_rect = QRectF(x - 10, bar_y + bar_height + 2, self._bar_width + 20, 16)
            painter.drawText(
                value_rect,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                value_text,
            )

        painter.end()

    def _calculate_gradient_color(
        self,
        value: float,
        min_val: float,
        max_val: float,
    ) -> QColor:
        """Calculate bar color using brightness interpolation.

        Args:
            value: Current value.
            min_val: Minimum value in dataset.
            max_val: Maximum value in dataset.

        Returns:
            QColor with brightness based on value magnitude.
        """
        if value < 0:
            dark_color = QColor(74, 26, 31)
            bright_color = QColor(255, 71, 87)
        else:
            dark_color = QColor(10, 61, 61)
            bright_color = QColor(0, 255, 212)

        if max_val == min_val:
            t = 0.7
        else:
            abs_max = max(abs(min_val), abs(max_val))
            t = abs(value) / abs_max if abs_max > 0 else 0
            t = 0.25 + (t * 0.75)

        r = int(dark_color.red() + t * (bright_color.red() - dark_color.red()))
        g = int(dark_color.green() + t * (bright_color.green() - dark_color.green()))
        b = int(dark_color.blue() + t * (bright_color.blue() - dark_color.blue()))

        return QColor(r, g, b)

    def _format_value(self, value: float) -> str:
        """Format a number for display.

        Args:
            value: Value to format.

        Returns:
            Formatted string.
        """
        if value is None:
            return "N/A"

        if self._is_percentage:
            return f"{value:.1f}%"

        if self._is_currency:
            abs_value = abs(value)
            sign = "-" if value < 0 else ""
            if abs_value >= 1_000_000:
                return f"{sign}${abs_value / 1_000_000:.1f}M"
            elif abs_value >= 1_000:
                return f"{sign}${abs_value / 1_000:.1f}K"
            else:
                return f"{sign}${abs_value:.0f}"

        # Plain number
        abs_value = abs(value)
        sign = "-" if value < 0 else ""
        if abs_value >= 1_000_000:
            return f"{sign}{abs_value / 1_000_000:.1f}M"
        elif abs_value >= 1_000:
            return f"{sign}{abs_value / 1_000:.1f}K"
        elif abs_value == int(abs_value):
            return f"{sign}{int(abs_value)}"
        else:
            return f"{sign}{abs_value:.1f}"

    def mouseMoveEvent(self, event: "QMouseEvent") -> None:
        """Handle mouse move for hover effect.

        Args:
            event: Mouse event.
        """
        x = event.position().x()
        total_bar_width = len(self._data) * (self._bar_width + self._bar_spacing)
        start_x = 10 + self._bar_spacing // 2  # Left-align with small padding

        new_index = None
        for i in range(len(self._data)):
            bar_x = start_x + i * (self._bar_width + self._bar_spacing)
            if bar_x <= x <= bar_x + self._bar_width:
                new_index = i
                break

        if new_index != self._hovered_index:
            self._hovered_index = new_index
            self.update()

            if new_index is not None and new_index < len(self._data):
                label, value = self._data[new_index]
                self.bar_hovered.emit(label, value if value is not None else 0)

    def leaveEvent(self, event: "QEvent") -> None:
        """Handle mouse leave.

        Args:
            event: Leave event.
        """
        self._hovered_index = None
        self.update()
