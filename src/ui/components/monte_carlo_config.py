"""Monte Carlo configuration panel with controls and run button."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.core.monte_carlo import MonteCarloConfig, PositionSizingMode
from src.ui.constants import Colors, Fonts, Spacing

if TYPE_CHECKING:
    from PyQt6.QtGui import QPaintEvent


def _make_qt_property(type_: type, getter: object, setter: object) -> object:
    """Create a Qt property, working around mypy stub issues."""
    from PyQt6 import QtCore

    prop_factory = getattr(QtCore, "pyqt" + "Property")  # noqa: B009
    return prop_factory(type_, getter, setter)


class SimulationTypeToggle(QWidget):
    """Pill-shaped toggle for Resample/Reshuffle simulation types.

    Signals:
        type_changed: Emitted with simulation type string when changed.
    """

    type_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the toggle.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._selected = "resample"  # Default
        self._animation_progress = 0.0
        self._setup_ui()
        self._setup_animation()

    def _setup_ui(self) -> None:
        """Set up the pill toggle UI."""
        self.setFixedHeight(32)
        self.setMinimumWidth(200)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        self._resample_btn = self._create_option("Resample", True)
        self._reshuffle_btn = self._create_option("Reshuffle", False)

        layout.addWidget(self._resample_btn)
        layout.addWidget(self._reshuffle_btn)

        self._update_styles()

    def _create_option(self, text: str, active: bool) -> QLabel:
        """Create an option label.

        Args:
            text: Button text.
            active: Whether initially active.

        Returns:
            Configured QLabel.
        """
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFixedHeight(28)
        label.setCursor(Qt.CursorShape.PointingHandCursor)
        return label

    def _setup_animation(self) -> None:
        """Set up the transition animation."""
        self._animation = QPropertyAnimation(self, b"animationProgress")
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _get_animation_progress(self) -> float:
        """Get animation progress."""
        return self._animation_progress

    def _set_animation_progress(self, value: float) -> None:
        """Set animation progress and update styles."""
        self._animation_progress = value
        self._update_styles()

    def _update_styles(self) -> None:
        """Update button styles based on selection."""
        active_style = f"""
            QLabel {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.UI};
                font-size: 12px;
                font-weight: bold;
                border: 1px solid {Colors.SIGNAL_CYAN};
                border-radius: 4px;
                padding: 0 12px;
            }}
        """
        inactive_style = f"""
            QLabel {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.UI};
                font-size: 12px;
                border: none;
                border-radius: 4px;
                padding: 0 12px;
            }}
            QLabel:hover {{
                color: {Colors.TEXT_PRIMARY};
            }}
        """

        if self._selected == "resample":
            self._resample_btn.setStyleSheet(active_style)
            self._reshuffle_btn.setStyleSheet(inactive_style)
        else:
            self._resample_btn.setStyleSheet(inactive_style)
            self._reshuffle_btn.setStyleSheet(active_style)

        self.setStyleSheet(f"""
            SimulationTypeToggle {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 6px;
            }}
        """)

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        """Handle click to switch selection.

        Args:
            event: Mouse event.
        """
        if event is None:
            return

        # Determine which half was clicked
        mid_x = self.width() / 2
        new_selection = "resample" if event.position().x() < mid_x else "reshuffle"

        if new_selection != self._selected:
            self._selected = new_selection
            self._update_styles()
            self.type_changed.emit(self._selected)

        super().mousePressEvent(event)

    def simulation_type(self) -> str:
        """Get current simulation type.

        Returns:
            'resample' or 'reshuffle'.
        """
        return self._selected

    def set_simulation_type(self, sim_type: str) -> None:
        """Set simulation type without emitting signal.

        Args:
            sim_type: 'resample' or 'reshuffle'.
        """
        if sim_type in ("resample", "reshuffle"):
            self._selected = sim_type
            self._update_styles()


# Register Qt property for animation
SimulationTypeToggle.animationProgress = _make_qt_property(  # type: ignore[attr-defined]
    float,
    SimulationTypeToggle._get_animation_progress,
    SimulationTypeToggle._set_animation_progress,
)


class ProgressRing(QWidget):
    """Circular progress ring with percentage display."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the progress ring.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._progress = 0.0  # 0.0 to 1.0
        self._sweep_angle = 0.0
        self.setFixedSize(24, 24)
        self._setup_animation()

    def _setup_animation(self) -> None:
        """Set up the sweep animation."""
        self._animation = QPropertyAnimation(self, b"sweepAngle")
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _get_sweep_angle(self) -> float:
        """Get current sweep angle."""
        return self._sweep_angle

    def _set_sweep_angle(self, value: float) -> None:
        """Set sweep angle and repaint."""
        self._sweep_angle = value
        self.update()

    def set_progress(self, progress: float) -> None:
        """Set progress value with animation.

        Args:
            progress: Progress value from 0.0 to 1.0.
        """
        self._progress = max(0.0, min(1.0, progress))
        target_angle = self._progress * 360.0

        self._animation.stop()
        self._animation.setStartValue(self._sweep_angle)
        self._animation.setEndValue(target_angle)
        self._animation.start()

    def reset(self) -> None:
        """Reset progress to zero."""
        self._progress = 0.0
        self._sweep_angle = 0.0
        self.update()

    def paintEvent(self, event: QPaintEvent | None) -> None:
        """Paint the progress ring.

        Args:
            event: Paint event.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate ring dimensions
        margin = 2
        rect = QRectF(margin, margin, self.width() - 2 * margin, self.height() - 2 * margin)

        # Draw background ring
        pen = QPen(QColor(Colors.BG_BORDER))
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)

        # Draw progress arc
        if self._sweep_angle > 0:
            pen = QPen(QColor(Colors.SIGNAL_CYAN))
            pen.setWidth(3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            # Qt uses 1/16th of a degree, start at top (90 degrees)
            start_angle = 90 * 16
            span_angle = -int(self._sweep_angle * 16)  # Negative for clockwise
            painter.drawArc(rect, start_angle, span_angle)

        painter.end()


# Register Qt property
ProgressRing.sweepAngle = _make_qt_property(  # type: ignore[attr-defined]
    float,
    ProgressRing._get_sweep_angle,
    ProgressRing._set_sweep_angle,
)


class RunButton(QFrame):
    """Run button with progress ring and cancel capability.

    States:
        - Idle: Cyan border, transparent fill, text "RUN SIM"
        - Hover: Cyan fill 20% opacity
        - Running: Animated progress ring, percentage, text "CANCEL"
        - Disabled: Dimmed appearance

    Signals:
        clicked: Emitted when clicked in idle state.
        cancel_clicked: Emitted when clicked in running state.
    """

    clicked = pyqtSignal()
    cancel_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the run button.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._is_running = False
        self._is_hovered = False
        self._is_enabled = True
        self._progress = 0.0
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the button UI."""
        self.setFixedSize(100, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(6)

        # Progress ring (hidden when idle)
        self._progress_ring = ProgressRing()
        self._progress_ring.hide()
        layout.addWidget(self._progress_ring)

        # Button text
        self._text_label = QLabel("RUN SIM")
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._text_label, stretch=1)

        self._update_style()

    def _update_style(self) -> None:
        """Update button style based on state."""
        if not self._is_enabled:
            bg_color = "transparent"
            border_color = Colors.TEXT_DISABLED
            text_color = Colors.TEXT_DISABLED
        elif self._is_running:
            bg_color = "rgba(255, 71, 87, 0.1)"  # Coral tint
            border_color = Colors.SIGNAL_CORAL
            text_color = Colors.SIGNAL_CORAL
        elif self._is_hovered:
            bg_color = "rgba(0, 255, 212, 0.2)"  # Cyan tint
            border_color = Colors.SIGNAL_CYAN
            text_color = Colors.SIGNAL_CYAN
        else:
            bg_color = "transparent"
            border_color = Colors.SIGNAL_CYAN
            text_color = Colors.SIGNAL_CYAN

        self.setStyleSheet(f"""
            RunButton {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 4px;
            }}
        """)

        self._text_label.setStyleSheet(f"""
            color: {text_color};
            font-family: {Fonts.UI};
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 1px;
        """)

    def set_running(self, running: bool) -> None:
        """Set running state.

        Args:
            running: Whether simulation is running.
        """
        self._is_running = running
        if running:
            self._text_label.setText("CANCEL")
            self._progress_ring.show()
            self._progress_ring.reset()
        else:
            self._text_label.setText("RUN SIM")
            self._progress_ring.hide()
        self._update_style()

    def set_enabled(self, enabled: bool) -> None:
        """Set enabled state.

        Args:
            enabled: Whether button is enabled.
        """
        self._is_enabled = enabled
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ForbiddenCursor
        )
        self._update_style()

    def set_progress(self, completed: int, total: int) -> None:
        """Update progress display.

        Args:
            completed: Number of completed simulations.
            total: Total number of simulations.
        """
        if total > 0:
            self._progress = completed / total
            self._progress_ring.set_progress(self._progress)
            pct = int(self._progress * 100)
            self._text_label.setText(f"{pct}%")

    def enterEvent(self, event: object) -> None:
        """Handle mouse enter."""
        self._is_hovered = True
        self._update_style()
        super().enterEvent(event)

    def leaveEvent(self, event: object) -> None:
        """Handle mouse leave."""
        self._is_hovered = False
        self._update_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        """Handle mouse press.

        Args:
            event: Mouse event.
        """
        if event is None or not self._is_enabled:
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_running:
                self.cancel_clicked.emit()
            else:
                self.clicked.emit()

        super().mousePressEvent(event)


class MonteCarloConfigPanel(QFrame):
    """Configuration panel for Monte Carlo simulation settings.

    Contains simulation type toggle, parameter inputs, and run button.

    Signals:
        config_changed: Emitted when any configuration value changes.
        run_requested: Emitted when Run button is clicked.
        cancel_requested: Emitted when Cancel is clicked during running.
    """

    config_changed = pyqtSignal(object)  # MonteCarloConfig
    run_requested = pyqtSignal()
    cancel_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the configuration panel.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._position_sizing_mode = PositionSizingMode.COMPOUNDED_KELLY
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the panel UI."""
        self.setObjectName("mcConfigPanel")
        self.setStyleSheet(f"""
            QFrame#mcConfigPanel {{
                background-color: {Colors.BG_ELEVATED};
                border-bottom: 1px solid {Colors.BG_BORDER};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        layout.setSpacing(Spacing.XL)

        # Simulation type toggle
        type_container = self._create_input_group("Simulation Type")
        self._type_toggle = SimulationTypeToggle()
        type_container.layout().addWidget(self._type_toggle)
        layout.addWidget(type_container)

        # Number of simulations
        sims_container = self._create_input_group("Simulations")
        self._num_sims_spin = QSpinBox()
        self._num_sims_spin.setRange(100, 50000)
        self._num_sims_spin.setValue(5000)
        self._num_sims_spin.setSingleStep(100)
        self._num_sims_spin.setStyleSheet(self._spinbox_style())
        sims_container.layout().addWidget(self._num_sims_spin)
        layout.addWidget(sims_container)

        # Initial capital
        capital_container = self._create_input_group("Initial Capital")
        self._capital_spin = QDoubleSpinBox()
        self._capital_spin.setRange(1000, 10000000)
        self._capital_spin.setValue(100000)
        self._capital_spin.setSingleStep(10000)
        self._capital_spin.setDecimals(0)
        self._capital_spin.setPrefix("$")
        self._capital_spin.setStyleSheet(self._spinbox_style())
        capital_container.layout().addWidget(self._capital_spin)
        layout.addWidget(capital_container)

        # Ruin threshold
        ruin_container = self._create_input_group("Ruin Threshold")
        self._ruin_spin = QDoubleSpinBox()
        self._ruin_spin.setRange(0, 99)
        self._ruin_spin.setValue(50)
        self._ruin_spin.setSingleStep(5)
        self._ruin_spin.setDecimals(0)
        self._ruin_spin.setSuffix("%")
        self._ruin_spin.setStyleSheet(self._spinbox_style())
        ruin_container.layout().addWidget(self._ruin_spin)
        layout.addWidget(ruin_container)

        # VaR confidence
        var_container = self._create_input_group("VaR Confidence")
        self._var_spin = QDoubleSpinBox()
        self._var_spin.setRange(1, 20)
        self._var_spin.setValue(5)
        self._var_spin.setSingleStep(1)
        self._var_spin.setDecimals(0)
        self._var_spin.setSuffix("%")
        self._var_spin.setStyleSheet(self._spinbox_style())
        var_container.layout().addWidget(self._var_spin)
        layout.addWidget(var_container)

        # Position sizing toggle
        sizing_container = self._create_input_group("Position Sizing")
        sizing_btn_layout = QHBoxLayout()
        sizing_btn_layout.setContentsMargins(0, 0, 0, 0)
        sizing_btn_layout.setSpacing(4)

        self._flat_stake_btn = QPushButton("Flat Stake")
        self._flat_stake_btn.setCheckable(True)
        self._flat_stake_btn.setChecked(False)
        self._flat_stake_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._flat_stake_btn.setStyleSheet(self._toggle_btn_style())

        self._kelly_btn = QPushButton("Compounded Kelly")
        self._kelly_btn.setCheckable(True)
        self._kelly_btn.setChecked(True)  # Default
        self._kelly_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._kelly_btn.setStyleSheet(self._toggle_btn_style())

        self._custom_btn = QPushButton("Custom %")
        self._custom_btn.setCheckable(True)
        self._custom_btn.setChecked(False)
        self._custom_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._custom_btn.setStyleSheet(self._toggle_btn_style())

        sizing_btn_layout.addWidget(self._flat_stake_btn)
        sizing_btn_layout.addWidget(self._kelly_btn)
        sizing_btn_layout.addWidget(self._custom_btn)

        # Custom position percentage spinner (initially hidden)
        self._custom_pct_spin = QDoubleSpinBox()
        self._custom_pct_spin.setRange(0.1, 100)
        self._custom_pct_spin.setValue(10.0)
        self._custom_pct_spin.setSingleStep(1.0)
        self._custom_pct_spin.setDecimals(1)
        self._custom_pct_spin.setSuffix("%")
        self._custom_pct_spin.setStyleSheet(self._spinbox_style())
        self._custom_pct_spin.setFixedWidth(80)
        self._custom_pct_spin.setVisible(False)  # Hidden until Custom mode selected

        sizing_btn_layout.addWidget(self._custom_pct_spin)
        sizing_container.layout().addLayout(sizing_btn_layout)
        layout.addWidget(sizing_container)

        layout.addStretch()

        # Run button
        self._run_btn = RunButton()
        layout.addWidget(self._run_btn)

    def _create_input_group(self, label: str) -> QWidget:
        """Create a labeled input group container.

        Args:
            label: Label text.

        Returns:
            Container widget with label.
        """
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-family: {Fonts.UI};
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        """)
        layout.addWidget(label_widget)

        return container

    def _spinbox_style(self) -> str:
        """Get consistent spinbox styling.

        Returns:
            Stylesheet string.
        """
        return f"""
            QSpinBox, QDoubleSpinBox {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.DATA};
                font-size: 13px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 100px;
            }}
            QSpinBox:focus, QDoubleSpinBox:focus {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                width: 16px;
                border: none;
            }}
        """

    def _toggle_btn_style(self) -> str:
        """Get consistent toggle button styling.

        Returns:
            Stylesheet string.
        """
        return f"""
            QPushButton {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.UI};
                font-size: 11px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 4px 10px;
                min-width: 80px;
            }}
            QPushButton:hover {{
                color: {Colors.TEXT_PRIMARY};
                border-color: {Colors.TEXT_SECONDARY};
            }}
            QPushButton:checked {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border-color: {Colors.SIGNAL_CYAN};
                font-weight: bold;
            }}
            QPushButton:disabled {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_DISABLED};
                border-color: {Colors.BG_BORDER};
            }}
        """

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self._type_toggle.type_changed.connect(self._emit_config_changed)
        self._num_sims_spin.valueChanged.connect(self._emit_config_changed)
        self._capital_spin.valueChanged.connect(self._emit_config_changed)
        self._ruin_spin.valueChanged.connect(self._emit_config_changed)
        self._var_spin.valueChanged.connect(self._emit_config_changed)

        # Position sizing toggle
        self._flat_stake_btn.clicked.connect(
            lambda: self._on_position_mode_changed(PositionSizingMode.FLAT_STAKE)
        )
        self._kelly_btn.clicked.connect(
            lambda: self._on_position_mode_changed(PositionSizingMode.COMPOUNDED_KELLY)
        )
        self._custom_btn.clicked.connect(
            lambda: self._on_position_mode_changed(PositionSizingMode.COMPOUNDED_CUSTOM)
        )
        self._custom_pct_spin.valueChanged.connect(self._emit_config_changed)

        self._run_btn.clicked.connect(self.run_requested.emit)
        self._run_btn.cancel_clicked.connect(self.cancel_requested.emit)

    def _emit_config_changed(self, _: object = None) -> None:
        """Emit config_changed signal with current configuration."""
        self.config_changed.emit(self.get_config())

    def _on_position_mode_changed(self, mode: PositionSizingMode) -> None:
        """Handle position sizing mode change.

        Args:
            mode: The new position sizing mode.
        """
        self._position_sizing_mode = mode
        self._flat_stake_btn.setChecked(mode == PositionSizingMode.FLAT_STAKE)
        self._kelly_btn.setChecked(mode == PositionSizingMode.COMPOUNDED_KELLY)
        self._custom_btn.setChecked(mode == PositionSizingMode.COMPOUNDED_CUSTOM)

        # Show/hide custom percentage spinner
        self._custom_pct_spin.setVisible(mode == PositionSizingMode.COMPOUNDED_CUSTOM)

        self._emit_config_changed()

    def get_config(self) -> MonteCarloConfig:
        """Get current configuration as MonteCarloConfig.

        Returns:
            MonteCarloConfig with current values.
        """
        return MonteCarloConfig(
            num_simulations=self._num_sims_spin.value(),
            initial_capital=self._capital_spin.value(),
            ruin_threshold_pct=self._ruin_spin.value(),
            var_confidence_pct=self._var_spin.value(),
            simulation_type=self._type_toggle.simulation_type(),
            position_sizing_mode=self._position_sizing_mode,
            flat_stake=10000.0,  # Will be overwritten from app_state
            fractional_kelly_pct=25.0,  # Will be overwritten from app_state
        )

    def set_config(self, config: MonteCarloConfig) -> None:
        """Set configuration values without emitting signals.

        Args:
            config: Configuration to apply.
        """
        # Block signals during update
        self._num_sims_spin.blockSignals(True)
        self._capital_spin.blockSignals(True)
        self._ruin_spin.blockSignals(True)
        self._var_spin.blockSignals(True)
        self._flat_stake_btn.blockSignals(True)
        self._kelly_btn.blockSignals(True)

        self._type_toggle.set_simulation_type(config.simulation_type)
        self._num_sims_spin.setValue(config.num_simulations)
        self._capital_spin.setValue(config.initial_capital)
        self._ruin_spin.setValue(config.ruin_threshold_pct)
        self._var_spin.setValue(config.var_confidence_pct)

        # Set position sizing mode
        self._position_sizing_mode = config.position_sizing_mode
        self._flat_stake_btn.setChecked(
            config.position_sizing_mode == PositionSizingMode.FLAT_STAKE
        )
        self._kelly_btn.setChecked(
            config.position_sizing_mode == PositionSizingMode.COMPOUNDED_KELLY
        )

        self._num_sims_spin.blockSignals(False)
        self._capital_spin.blockSignals(False)
        self._ruin_spin.blockSignals(False)
        self._var_spin.blockSignals(False)
        self._flat_stake_btn.blockSignals(False)
        self._kelly_btn.blockSignals(False)

    def set_running(self, running: bool) -> None:
        """Set running state.

        Args:
            running: Whether simulation is running.
        """
        self._run_btn.set_running(running)
        # Disable inputs while running
        self._type_toggle.setEnabled(not running)
        self._num_sims_spin.setEnabled(not running)
        self._capital_spin.setEnabled(not running)
        self._ruin_spin.setEnabled(not running)
        self._var_spin.setEnabled(not running)
        self._flat_stake_btn.setEnabled(not running)
        self._kelly_btn.setEnabled(not running)

    def set_run_enabled(self, enabled: bool) -> None:
        """Set whether run button is enabled.

        Args:
            enabled: Whether run is enabled.
        """
        self._run_btn.set_enabled(enabled)

    def update_progress(self, completed: int, total: int) -> None:
        """Update progress display.

        Args:
            completed: Completed simulations.
            total: Total simulations.
        """
        self._run_btn.set_progress(completed, total)
