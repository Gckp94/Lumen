"""Axis column selector for choosing X and Y plot columns.

Provides two dropdowns for selecting which DataFrame columns to plot
on the X and Y axes of a scatter chart, with inline Min/Max bound inputs.
"""

from __future__ import annotations

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.ui.components.no_scroll_widgets import NoScrollComboBox, NoScrollDoubleSpinBox
from src.ui.constants import Animation, Colors, Fonts, Spacing

# Sentinel value for index-based X axis
INDEX_OPTION = "(Index)"


class AxisColumnSelector(QWidget):
    """Dropdown selectors for X and Y axis columns.

    Provides two combo boxes: one for X-axis (with Index option) and one
    for Y-axis. Emits selection_changed when either selection changes.
    Also provides Min/Max bound inputs for each axis.

    Signals:
        selection_changed: Emitted when X or Y selection changes.
        x_bounds_changed: Emitted when X axis bounds change (x_min, x_max).
        y_bounds_changed: Emitted when Y axis bounds change (y_min, y_max).

    Properties:
        x_column: Selected X column name, or None if Index selected.
        y_column: Selected Y column name.
        x_bounds: Tuple of (x_min, x_max) values.
        y_bounds: Tuple of (y_min, y_max) values.
    """

    selection_changed = pyqtSignal()
    x_bounds_changed = pyqtSignal(float, float)  # x_min, x_max
    y_bounds_changed = pyqtSignal(float, float)  # y_min, y_max

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the AxisColumnSelector.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._setup_ui()
        self._apply_style()
        self._connect_signals()
        self._setup_debounce()

    def _setup_ui(self) -> None:
        """Set up the selector layout with X and Y dropdowns and bounds."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, Spacing.SM)
        layout.setSpacing(Spacing.SM)

        # Section label
        section_label = QLabel("Plot Columns")
        section_label.setObjectName("section_label")
        layout.addWidget(section_label)

        # X-axis row
        x_row = QHBoxLayout()
        x_row.setSpacing(Spacing.SM)

        x_label = QLabel("X:")
        x_label.setFixedWidth(20)
        x_label.setObjectName("axis_label")
        x_row.addWidget(x_label)

        self._x_combo = NoScrollComboBox()
        self._x_combo.addItem(INDEX_OPTION)
        self._x_combo.setEnabled(False)
        x_row.addWidget(self._x_combo, stretch=1)

        layout.addLayout(x_row)

        # X-axis bounds row
        x_bounds_row = QHBoxLayout()
        x_bounds_row.setSpacing(Spacing.XS)
        x_bounds_row.setContentsMargins(20, 0, 0, 0)  # Indent to align with combo

        x_min_label = QLabel("Min:")
        x_min_label.setObjectName("bounds_label")
        x_min_label.setFixedWidth(30)
        x_bounds_row.addWidget(x_min_label)

        self._x_min = NoScrollDoubleSpinBox()
        self._x_min.setRange(-1e9, 1e9)
        self._x_min.setDecimals(2)
        self._x_min.setFixedWidth(80)
        self._x_min.setSpecialValueText("")  # Show empty when at minimum
        x_bounds_row.addWidget(self._x_min)

        x_max_label = QLabel("Max:")
        x_max_label.setObjectName("bounds_label")
        x_max_label.setFixedWidth(30)
        x_bounds_row.addWidget(x_max_label)

        self._x_max = NoScrollDoubleSpinBox()
        self._x_max.setRange(-1e9, 1e9)
        self._x_max.setDecimals(2)
        self._x_max.setFixedWidth(80)
        self._x_max.setSpecialValueText("")  # Show empty when at minimum
        x_bounds_row.addWidget(self._x_max)

        x_bounds_row.addStretch()
        layout.addLayout(x_bounds_row)

        # Y-axis row
        y_row = QHBoxLayout()
        y_row.setSpacing(Spacing.SM)

        y_label = QLabel("Y:")
        y_label.setFixedWidth(20)
        y_label.setObjectName("axis_label")
        y_row.addWidget(y_label)

        self._y_combo = NoScrollComboBox()
        self._y_combo.setEnabled(False)
        y_row.addWidget(self._y_combo, stretch=1)

        layout.addLayout(y_row)

        # Y-axis bounds row
        y_bounds_row = QHBoxLayout()
        y_bounds_row.setSpacing(Spacing.XS)
        y_bounds_row.setContentsMargins(20, 0, 0, 0)  # Indent to align with combo

        y_min_label = QLabel("Min:")
        y_min_label.setObjectName("bounds_label")
        y_min_label.setFixedWidth(30)
        y_bounds_row.addWidget(y_min_label)

        self._y_min = NoScrollDoubleSpinBox()
        self._y_min.setRange(-1e9, 1e9)
        self._y_min.setDecimals(2)
        self._y_min.setFixedWidth(80)
        self._y_min.setSpecialValueText("")  # Show empty when at minimum
        y_bounds_row.addWidget(self._y_min)

        y_max_label = QLabel("Max:")
        y_max_label.setObjectName("bounds_label")
        y_max_label.setFixedWidth(30)
        y_bounds_row.addWidget(y_max_label)

        self._y_max = NoScrollDoubleSpinBox()
        self._y_max.setRange(-1e9, 1e9)
        self._y_max.setDecimals(2)
        self._y_max.setFixedWidth(80)
        self._y_max.setSpecialValueText("")  # Show empty when at minimum
        y_bounds_row.addWidget(self._y_max)

        y_bounds_row.addStretch()
        layout.addLayout(y_bounds_row)

    def _apply_style(self) -> None:
        """Apply Observatory theme styling."""
        # Section label style
        section_style = f"""
            QLabel#section_label {{
                color: {Colors.TEXT_PRIMARY};
                font-size: 12px;
                font-weight: bold;
            }}
        """
        self.setStyleSheet(section_style)

        # Axis label style
        for label in self.findChildren(QLabel):
            if label.objectName() == "axis_label":
                label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")

        # Combo box style (matching existing column_selector)
        combo_style = f"""
            QComboBox {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 13px;
            }}
            QComboBox:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                selection-background-color: {Colors.BG_BORDER};
                selection-color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
            }}
        """
        self._x_combo.setStyleSheet(combo_style)
        self._y_combo.setStyleSheet(combo_style)

        # Bounds label style
        for label in self.findChildren(QLabel):
            if label.objectName() == "bounds_label":
                label.setStyleSheet(f"""
                    color: {Colors.TEXT_SECONDARY};
                    font-family: "{Fonts.UI}";
                    font-size: 11px;
                """)

        # Spin box style
        spinbox_style = f"""
            QDoubleSpinBox {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 4px 6px;
                font-family: "{Fonts.DATA}";
                font-size: 12px;
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

    def _connect_signals(self) -> None:
        """Connect combo box and spin box signals."""
        self._x_combo.currentTextChanged.connect(self._on_selection_changed)
        self._y_combo.currentTextChanged.connect(self._on_selection_changed)

        # Bounds change signals
        self._x_min.valueChanged.connect(self._on_x_bounds_changed)
        self._x_max.valueChanged.connect(self._on_x_bounds_changed)
        self._y_min.valueChanged.connect(self._on_y_bounds_changed)
        self._y_max.valueChanged.connect(self._on_y_bounds_changed)

    def _setup_debounce(self) -> None:
        """Set up debounce timer for bounds change signals."""
        self._x_debounce = QTimer()
        self._x_debounce.setSingleShot(True)
        self._x_debounce.timeout.connect(self._emit_x_bounds)

        self._y_debounce = QTimer()
        self._y_debounce.setSingleShot(True)
        self._y_debounce.timeout.connect(self._emit_y_bounds)

    def _emit_x_bounds(self) -> None:
        """Emit x_bounds_changed signal."""
        self.x_bounds_changed.emit(self._x_min.value(), self._x_max.value())

    def _emit_y_bounds(self) -> None:
        """Emit y_bounds_changed signal."""
        self.y_bounds_changed.emit(self._y_min.value(), self._y_max.value())

    def _on_x_bounds_changed(self) -> None:
        """Handle X bounds input change with debounce."""
        self._x_debounce.start(Animation.DEBOUNCE_INPUT)

    def _on_y_bounds_changed(self) -> None:
        """Handle Y bounds input change with debounce."""
        self._y_debounce.start(Animation.DEBOUNCE_INPUT)

    def _on_selection_changed(self, _text: str) -> None:
        """Handle combo selection change."""
        self.selection_changed.emit()

    def set_columns(self, columns: list[str]) -> None:
        """Populate dropdowns with available columns.

        Args:
            columns: List of column names to add to dropdowns.
        """
        # Block signals during population
        self._x_combo.blockSignals(True)
        self._y_combo.blockSignals(True)

        # Clear and repopulate X combo (keep Index option)
        self._x_combo.clear()
        self._x_combo.addItem(INDEX_OPTION)
        self._x_combo.addItems(columns)

        # Clear and repopulate Y combo
        self._y_combo.clear()
        self._y_combo.addItems(columns)

        # Enable if columns available
        has_columns = len(columns) > 0
        self._x_combo.setEnabled(has_columns)
        self._y_combo.setEnabled(has_columns)

        self._x_combo.blockSignals(False)
        self._y_combo.blockSignals(False)

    @property
    def x_column(self) -> str | None:
        """Get selected X column, or None if Index is selected."""
        text = self._x_combo.currentText()
        return None if text == INDEX_OPTION else text

    @property
    def y_column(self) -> str:
        """Get selected Y column name."""
        return self._y_combo.currentText()

    def set_y_column(self, column: str) -> None:
        """Set the Y column selection.

        Args:
            column: Column name to select.
        """
        index = self._y_combo.findText(column)
        if index >= 0:
            self._y_combo.setCurrentIndex(index)

    def set_x_bounds(self, x_min: float, x_max: float) -> None:
        """Set X axis bounds without triggering signals."""
        self._x_min.blockSignals(True)
        self._x_max.blockSignals(True)
        self._x_min.setValue(x_min)
        self._x_max.setValue(x_max)
        self._x_min.blockSignals(False)
        self._x_max.blockSignals(False)

    def set_y_bounds(self, y_min: float, y_max: float) -> None:
        """Set Y axis bounds without triggering signals."""
        self._y_min.blockSignals(True)
        self._y_max.blockSignals(True)
        self._y_min.setValue(y_min)
        self._y_max.setValue(y_max)
        self._y_min.blockSignals(False)
        self._y_max.blockSignals(False)

    @property
    def x_bounds(self) -> tuple[float, float]:
        """Get current X axis bounds."""
        return (self._x_min.value(), self._x_max.value())

    @property
    def y_bounds(self) -> tuple[float, float]:
        """Get current Y axis bounds."""
        return (self._y_min.value(), self._y_max.value())
