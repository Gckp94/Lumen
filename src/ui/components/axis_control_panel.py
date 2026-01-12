"""Axis control panel for chart range and grid settings.

Provides controls for manually setting chart axis ranges, auto-fitting,
and toggling grid visibility.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.components.no_scroll_widgets import NoScrollDoubleSpinBox
from src.ui.constants import Animation, Colors, Spacing


class AxisControlPanel(QWidget):
    """Axis range controls with min/max inputs and auto-fit.

    Provides spin boxes for X and Y axis ranges, an Auto Fit button to reset
    the view, and a grid toggle checkbox.

    Signals:
        range_changed: Emitted when axis range inputs change (x_min, x_max, y_min, y_max).
        auto_fit_clicked: Emitted when Auto Fit button is clicked.
        grid_toggled: Emitted when grid checkbox state changes (visible: bool).

    Attributes:
        _x_min: X-axis minimum value spin box.
        _x_max: X-axis maximum value spin box.
        _y_min: Y-axis minimum value spin box.
        _y_max: Y-axis maximum value spin box.
        _auto_fit_btn: Auto Fit button.
        _grid_checkbox: Show Grid checkbox.
    """

    range_changed = pyqtSignal(float, float, float, float)  # x_min, x_max, y_min, y_max
    auto_fit_clicked = pyqtSignal()
    grid_toggled = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the AxisControlPanel.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._setup_ui()
        self._apply_style()
        self._connect_signals()
        self._setup_debounce()

    def _setup_ui(self) -> None:
        """Set up the panel layout with axis inputs and controls."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, Spacing.SM, 0, Spacing.SM)
        layout.setSpacing(Spacing.SM)

        # Section label
        section_label = QLabel("Axis Controls")
        section_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-size: 12px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(section_label)

        # X-axis row
        x_row = QHBoxLayout()
        x_row.setSpacing(Spacing.XS)
        x_label = QLabel("X:")
        x_label.setFixedWidth(20)
        x_row.addWidget(x_label)

        self._x_min = NoScrollDoubleSpinBox()
        self._x_min.setRange(-1e9, 1e9)
        self._x_min.setDecimals(0)
        self._x_min.setFixedWidth(80)
        x_row.addWidget(self._x_min)

        x_to_label = QLabel("to")
        x_to_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        x_row.addWidget(x_to_label)

        self._x_max = NoScrollDoubleSpinBox()
        self._x_max.setRange(-1e9, 1e9)
        self._x_max.setDecimals(0)
        self._x_max.setFixedWidth(80)
        x_row.addWidget(self._x_max)

        x_row.addStretch()
        layout.addLayout(x_row)

        # Y-axis row
        y_row = QHBoxLayout()
        y_row.setSpacing(Spacing.XS)
        y_label = QLabel("Y:")
        y_label.setFixedWidth(20)
        y_row.addWidget(y_label)

        self._y_min = NoScrollDoubleSpinBox()
        self._y_min.setRange(-1e9, 1e9)
        self._y_min.setDecimals(2)
        self._y_min.setFixedWidth(80)
        y_row.addWidget(self._y_min)

        y_to_label = QLabel("to")
        y_to_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        y_row.addWidget(y_to_label)

        self._y_max = NoScrollDoubleSpinBox()
        self._y_max.setRange(-1e9, 1e9)
        self._y_max.setDecimals(2)
        self._y_max.setFixedWidth(80)
        y_row.addWidget(self._y_max)

        y_row.addStretch()
        layout.addLayout(y_row)

        # Controls row
        controls_row = QHBoxLayout()
        controls_row.setSpacing(Spacing.SM)

        self._auto_fit_btn = QPushButton("Auto Fit")
        controls_row.addWidget(self._auto_fit_btn)

        self._grid_checkbox = QCheckBox("Show Grid")
        controls_row.addWidget(self._grid_checkbox)

        controls_row.addStretch()
        layout.addLayout(controls_row)

    def _apply_style(self) -> None:
        """Apply Observatory theme styling to controls."""
        spinbox_style = f"""
            QDoubleSpinBox {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 4px;
            }}
            QDoubleSpinBox:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QDoubleSpinBox:focus {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
        """
        self._x_min.setStyleSheet(spinbox_style)
        self._x_max.setStyleSheet(spinbox_style)
        self._y_min.setStyleSheet(spinbox_style)
        self._y_max.setStyleSheet(spinbox_style)

        self._auto_fit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: {Spacing.XS}px {Spacing.SM}px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_BORDER};
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QPushButton:pressed {{
                background-color: {Colors.BG_SURFACE};
            }}
        """)

        self._grid_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {Colors.TEXT_PRIMARY};
                spacing: {Spacing.XS}px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 3px;
                background-color: {Colors.BG_SURFACE};
            }}
            QCheckBox::indicator:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QCheckBox::indicator:checked {{
                background-color: {Colors.SIGNAL_CYAN};
                border-color: {Colors.SIGNAL_CYAN};
            }}
        """)

        # Style labels
        for label in self.findChildren(QLabel):
            if label.text() in ("X:", "Y:", "to"):
                label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")

    def _connect_signals(self) -> None:
        """Connect spin box and button signals."""
        # Spin box value changes trigger debounced range update
        self._x_min.valueChanged.connect(self._on_value_changed)
        self._x_max.valueChanged.connect(self._on_value_changed)
        self._y_min.valueChanged.connect(self._on_value_changed)
        self._y_max.valueChanged.connect(self._on_value_changed)

        # Button and checkbox signals
        self._auto_fit_btn.clicked.connect(self.auto_fit_clicked.emit)
        self._grid_checkbox.toggled.connect(self.grid_toggled.emit)

    def _setup_debounce(self) -> None:
        """Set up debounce timer for range change signals."""
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._emit_range_change)

    def _on_value_changed(self) -> None:
        """Handle spin box value change with debounce."""
        self._debounce_timer.start(Animation.DEBOUNCE_INPUT)

    def _emit_range_change(self) -> None:
        """Emit range_changed signal with current values."""
        self.range_changed.emit(
            self._x_min.value(),
            self._x_max.value(),
            self._y_min.value(),
            self._y_max.value(),
        )

    def set_range(
        self, x_min: float, x_max: float, y_min: float, y_max: float
    ) -> None:
        """Set axis ranges without triggering signals.

        Args:
            x_min: Minimum X value.
            x_max: Maximum X value.
            y_min: Minimum Y value.
            y_max: Maximum Y value.
        """
        # Block signals to prevent feedback loop
        for spinbox in (self._x_min, self._x_max, self._y_min, self._y_max):
            spinbox.blockSignals(True)

        self._x_min.setValue(x_min)
        self._x_max.setValue(x_max)
        self._y_min.setValue(y_min)
        self._y_max.setValue(y_max)

        for spinbox in (self._x_min, self._x_max, self._y_min, self._y_max):
            spinbox.blockSignals(False)

    def set_grid_checked(self, checked: bool) -> None:
        """Set grid checkbox state without triggering signal.

        Args:
            checked: Whether grid should be checked.
        """
        self._grid_checkbox.blockSignals(True)
        self._grid_checkbox.setChecked(checked)
        self._grid_checkbox.blockSignals(False)
