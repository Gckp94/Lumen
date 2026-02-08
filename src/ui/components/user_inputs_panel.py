"""User inputs panel for PnL Stats tab configuration."""

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QGridLayout,
    QLabel,
    QWidget,
)

from src.core.models import AdjustmentParams, MetricsUserInputs
from src.ui.components.no_scroll_widgets import NoScrollDoubleSpinBox
from src.ui.constants import Animation, Colors, Fonts, Spacing


class UserInputsPanel(QWidget):
    """Panel for configuring all PnL Stats user inputs.

    Contains spinboxes for:
    - Flat Stake ($): Amount per trade for flat stake calculations
    - Starting Capital ($): Initial capital for Kelly calculations
    - Fractional Kelly (%): Kelly fraction percentage
    - Stop Loss (%): Stop loss percentage (synced with Data Input tab)
    - Efficiency (%): Efficiency/slippage percentage (synced with Data Input)

    Signals:
        metrics_inputs_changed: Emitted when metrics inputs change.
        adjustment_params_changed: Emitted when stop_loss or efficiency changes.
    """

    metrics_inputs_changed = pyqtSignal(object)  # MetricsUserInputs
    adjustment_params_changed = pyqtSignal(object)  # AdjustmentParams

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the user inputs panel.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._metrics_inputs = MetricsUserInputs()
        self._adjustment_params = AdjustmentParams()

        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._emit_changes)

        # Track which signals to emit
        self._metrics_changed = False
        self._adjustment_changed = False

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the UI with grid layout for inputs."""
        self.setObjectName("userInputsPanel")
        self.setStyleSheet(f"""
            QWidget#userInputsPanel {{
                background-color: {Colors.BG_ELEVATED};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 8px;
            }}
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.UI};
                font-size: 12px;
            }}
            QDoubleSpinBox {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.DATA};
                font-size: 13px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 100px;
            }}
            QDoubleSpinBox:focus {{
                border-color: {Colors.SIGNAL_BLUE};
            }}
            QDoubleSpinBox[invalid="true"] {{
                border-color: {Colors.SIGNAL_CORAL};
            }}
        """)

        layout = QGridLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        layout.setHorizontalSpacing(Spacing.XL)
        layout.setVerticalSpacing(Spacing.SM)

        # Row 0: Flat Stake, Starting Capital, Fractional Kelly
        self._flat_stake_spin = self._create_spinbox(
            min_val=1.0,
            max_val=1_000_000.0,
            default=10000.0,
            step=100.0,
            decimals=0,
            prefix="$ ",
        )
        layout.addWidget(QLabel("Flat Stake"), 0, 0)
        layout.addWidget(self._flat_stake_spin, 1, 0)

        self._starting_capital_spin = self._create_spinbox(
            min_val=1.0,
            max_val=10_000_000.0,
            default=100000.0,
            step=1000.0,
            decimals=0,
            prefix="$ ",
        )
        layout.addWidget(QLabel("Starting Capital"), 0, 1)
        layout.addWidget(self._starting_capital_spin, 1, 1)

        self._fractional_kelly_spin = self._create_spinbox(
            min_val=1.0,
            max_val=100.0,
            default=25.0,
            step=5.0,
            decimals=1,
            suffix=" %",
        )
        layout.addWidget(QLabel("Fractional Kelly"), 0, 2)
        layout.addWidget(self._fractional_kelly_spin, 1, 2)

        # Row 2: Stop Loss, Efficiency
        self._stop_loss_spin = self._create_spinbox(
            min_val=0.0,
            max_val=100.0,
            default=100.0,
            step=0.5,
            decimals=1,
            suffix=" %",
        )
        layout.addWidget(QLabel("Stop Loss"), 0, 3)
        layout.addWidget(self._stop_loss_spin, 1, 3)

        self._efficiency_spin = self._create_spinbox(
            min_val=0.0,
            max_val=100.0,
            default=5.0,
            step=0.5,
            decimals=1,
            suffix=" %",
        )
        layout.addWidget(QLabel("Efficiency"), 0, 4)
        layout.addWidget(self._efficiency_spin, 1, 4)

        # Add stretch to push inputs left
        layout.setColumnStretch(5, 1)

    def _create_spinbox(
        self,
        min_val: float,
        max_val: float,
        default: float,
        step: float,
        decimals: int,
        prefix: str = "",
        suffix: str = "",
    ) -> NoScrollDoubleSpinBox:
        """Create a configured spinbox.

        Args:
            min_val: Minimum value.
            max_val: Maximum value.
            default: Default value.
            step: Single step increment.
            decimals: Number of decimal places.
            prefix: Optional prefix string.
            suffix: Optional suffix string.

        Returns:
            Configured NoScrollDoubleSpinBox.
        """
        spin = NoScrollDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setSingleStep(step)
        spin.setDecimals(decimals)
        if prefix:
            spin.setPrefix(prefix)
        if suffix:
            spin.setSuffix(suffix)
        return spin

    def _connect_signals(self) -> None:
        """Connect spinbox value changes to debounced update."""
        # Metrics inputs
        self._flat_stake_spin.valueChanged.connect(self._on_metrics_input_changed)
        self._starting_capital_spin.valueChanged.connect(self._on_metrics_input_changed)
        self._fractional_kelly_spin.valueChanged.connect(self._on_metrics_input_changed)

        # Adjustment params
        self._stop_loss_spin.editingFinished.connect(self._on_adjustment_input_changed)
        self._efficiency_spin.editingFinished.connect(self._on_adjustment_input_changed)

    def _on_metrics_input_changed(self) -> None:
        """Handle metrics input value change."""
        self._metrics_inputs = MetricsUserInputs(
            flat_stake=self._flat_stake_spin.value(),
            starting_capital=self._starting_capital_spin.value(),
            fractional_kelly=self._fractional_kelly_spin.value(),
        )
        self._validate_inputs()
        self._metrics_changed = True
        self._start_debounce()

    def _on_adjustment_input_changed(self) -> None:
        """Handle adjustment input value change."""
        self._adjustment_params = AdjustmentParams(
            stop_loss=self._stop_loss_spin.value(),
            efficiency=self._efficiency_spin.value(),
        )
        self._adjustment_changed = True
        self._start_debounce()

    def _start_debounce(self) -> None:
        """Start or restart debounce timer."""
        self._debounce_timer.start(Animation.DEBOUNCE_INPUT)

    def _emit_changes(self) -> None:
        """Emit signals after debounce."""
        if self._metrics_changed:
            self.metrics_inputs_changed.emit(self._metrics_inputs)
            self._metrics_changed = False

        if self._adjustment_changed:
            self.adjustment_params_changed.emit(self._adjustment_params)
            self._adjustment_changed = False

    def _validate_inputs(self) -> None:
        """Validate inputs and show error state if invalid."""
        errors = self._metrics_inputs.validate()
        has_errors = len(errors) > 0

        # Update visual state
        self._flat_stake_spin.setProperty("invalid", self._metrics_inputs.flat_stake <= 0)
        self._starting_capital_spin.setProperty(
            "invalid", self._metrics_inputs.starting_capital <= 0
        )
        self._fractional_kelly_spin.setProperty(
            "invalid", not 1 <= self._metrics_inputs.fractional_kelly <= 100
        )

        # Force style refresh
        if has_errors:
            for spin in [
                self._flat_stake_spin,
                self._starting_capital_spin,
                self._fractional_kelly_spin,
            ]:
                style = spin.style()
                if style:
                    style.unpolish(spin)
                    style.polish(spin)

    def set_adjustment_params(self, params: AdjustmentParams) -> None:
        """Update stop_loss and efficiency without triggering signals.

        Used for bidirectional sync from AppState.

        Args:
            params: New adjustment parameters.
        """
        self._adjustment_params = params

        self._stop_loss_spin.blockSignals(True)
        self._efficiency_spin.blockSignals(True)

        self._stop_loss_spin.setValue(params.stop_loss)
        self._efficiency_spin.setValue(params.efficiency)

        self._stop_loss_spin.blockSignals(False)
        self._efficiency_spin.blockSignals(False)

    def set_metrics_inputs(self, inputs: MetricsUserInputs) -> None:
        """Update metrics inputs without triggering signals.

        Used for initialization from AppState.

        Args:
            inputs: New metrics inputs.
        """
        self._metrics_inputs = inputs

        self._flat_stake_spin.blockSignals(True)
        self._starting_capital_spin.blockSignals(True)
        self._fractional_kelly_spin.blockSignals(True)

        self._flat_stake_spin.setValue(inputs.flat_stake)
        self._starting_capital_spin.setValue(inputs.starting_capital)
        self._fractional_kelly_spin.setValue(inputs.fractional_kelly)

        self._flat_stake_spin.blockSignals(False)
        self._starting_capital_spin.blockSignals(False)
        self._fractional_kelly_spin.blockSignals(False)

    def get_metrics_inputs(self) -> MetricsUserInputs:
        """Return current metrics user inputs.

        Returns:
            Current MetricsUserInputs state.
        """
        return self._metrics_inputs

    def get_adjustment_params(self) -> AdjustmentParams:
        """Return current adjustment parameters.

        Returns:
            Current AdjustmentParams state.
        """
        return self._adjustment_params

    def cleanup(self) -> None:
        """Clean up resources. Call before destruction."""
        self._debounce_timer.stop()
