"""Unit tests for UserInputsPanel component."""

from PyQt6.QtWidgets import QDoubleSpinBox

from src.core.models import AdjustmentParams, MetricsUserInputs
from src.ui.components.user_inputs_panel import UserInputsPanel


class TestUserInputsPanel:
    """Tests for UserInputsPanel component."""

    def test_creation(self, qtbot):
        """Panel can be created."""
        panel = UserInputsPanel()
        qtbot.addWidget(panel)
        assert panel is not None
        panel.cleanup()

    def test_default_values(self, qtbot):
        """Panel initializes with correct default values."""
        panel = UserInputsPanel()
        qtbot.addWidget(panel)

        inputs = panel.get_metrics_inputs()
        assert inputs.flat_stake == 10000.0
        assert inputs.starting_capital == 100000.0
        assert inputs.fractional_kelly == 25.0

        params = panel.get_adjustment_params()
        assert params.stop_loss == 8.0
        assert params.efficiency == 5.0

        panel.cleanup()

    def test_spinbox_ranges_flat_stake(self, qtbot):
        """Flat stake spinbox has correct range."""
        panel = UserInputsPanel()
        qtbot.addWidget(panel)

        spin = panel._flat_stake_spin
        assert spin.minimum() == 1.0
        assert spin.maximum() == 1_000_000.0
        assert spin.singleStep() == 100.0
        assert spin.prefix() == "$ "

        panel.cleanup()

    def test_spinbox_ranges_starting_capital(self, qtbot):
        """Starting capital spinbox has correct range."""
        panel = UserInputsPanel()
        qtbot.addWidget(panel)

        spin = panel._starting_capital_spin
        assert spin.minimum() == 1.0
        assert spin.maximum() == 10_000_000.0
        assert spin.singleStep() == 1000.0
        assert spin.prefix() == "$ "

        panel.cleanup()

    def test_spinbox_ranges_fractional_kelly(self, qtbot):
        """Fractional Kelly spinbox has correct range."""
        panel = UserInputsPanel()
        qtbot.addWidget(panel)

        spin = panel._fractional_kelly_spin
        assert spin.minimum() == 1.0
        assert spin.maximum() == 100.0
        assert spin.singleStep() == 5.0
        assert spin.suffix() == " %"

        panel.cleanup()

    def test_spinbox_ranges_stop_loss(self, qtbot):
        """Stop loss spinbox has correct range."""
        panel = UserInputsPanel()
        qtbot.addWidget(panel)

        spin = panel._stop_loss_spin
        assert spin.minimum() == 0.0  # 0 allowed for no stop loss
        assert spin.maximum() == 100.0
        assert spin.singleStep() == 0.5
        assert spin.suffix() == " %"

        panel.cleanup()

    def test_spinbox_ranges_efficiency(self, qtbot):
        """Efficiency spinbox has correct range."""
        panel = UserInputsPanel()
        qtbot.addWidget(panel)

        spin = panel._efficiency_spin
        assert spin.minimum() == 0.0
        assert spin.maximum() == 100.0
        assert spin.singleStep() == 0.5
        assert spin.suffix() == " %"

        panel.cleanup()

    def test_metrics_inputs_changed_signal(self, qtbot):
        """metrics_inputs_changed signal emits MetricsUserInputs."""
        panel = UserInputsPanel()
        qtbot.addWidget(panel)

        received = []
        panel.metrics_inputs_changed.connect(lambda x: received.append(x))

        # Change flat stake
        panel._flat_stake_spin.setValue(2000.0)

        # Wait for debounce
        qtbot.wait(200)

        assert len(received) == 1
        assert isinstance(received[0], MetricsUserInputs)
        assert received[0].flat_stake == 2000.0

        panel.cleanup()

    def test_adjustment_params_changed_signal(self, qtbot):
        """adjustment_params_changed signal emits AdjustmentParams."""
        panel = UserInputsPanel()
        qtbot.addWidget(panel)

        received = []
        panel.adjustment_params_changed.connect(lambda x: received.append(x))

        # Change stop loss
        panel._stop_loss_spin.setValue(10.0)

        # Wait for debounce
        qtbot.wait(200)

        assert len(received) == 1
        assert isinstance(received[0], AdjustmentParams)
        assert received[0].stop_loss == 10.0

        panel.cleanup()

    def test_debounce_coalesces_rapid_changes(self, qtbot):
        """Rapid changes are coalesced into single signal emission."""
        panel = UserInputsPanel()
        qtbot.addWidget(panel)

        received = []
        panel.metrics_inputs_changed.connect(lambda x: received.append(x))

        # Make multiple rapid changes
        panel._flat_stake_spin.setValue(2000.0)
        panel._starting_capital_spin.setValue(20000.0)
        panel._fractional_kelly_spin.setValue(30.0)

        # Wait for debounce
        qtbot.wait(200)

        # Should coalesce into single emission
        assert len(received) == 1
        assert received[0].flat_stake == 2000.0
        assert received[0].starting_capital == 20000.0
        assert received[0].fractional_kelly == 30.0

        panel.cleanup()

    def test_set_adjustment_params_no_signal(self, qtbot):
        """set_adjustment_params updates UI without emitting signal."""
        panel = UserInputsPanel()
        qtbot.addWidget(panel)

        signal_received = []
        panel.adjustment_params_changed.connect(lambda x: signal_received.append(x))

        params = AdjustmentParams(stop_loss=12.0, efficiency=3.0)
        panel.set_adjustment_params(params)

        # Wait to ensure no debounced signal
        qtbot.wait(200)

        assert len(signal_received) == 0
        assert panel._stop_loss_spin.value() == 12.0
        assert panel._efficiency_spin.value() == 3.0

        panel.cleanup()

    def test_set_metrics_inputs_no_signal(self, qtbot):
        """set_metrics_inputs updates UI without emitting signal."""
        panel = UserInputsPanel()
        qtbot.addWidget(panel)

        signal_received = []
        panel.metrics_inputs_changed.connect(lambda x: signal_received.append(x))

        inputs = MetricsUserInputs(
            flat_stake=5000.0,
            starting_capital=100000.0,
            fractional_kelly=50.0,
        )
        panel.set_metrics_inputs(inputs)

        # Wait to ensure no debounced signal
        qtbot.wait(200)

        assert len(signal_received) == 0
        assert panel._flat_stake_spin.value() == 5000.0
        assert panel._starting_capital_spin.value() == 100000.0
        assert panel._fractional_kelly_spin.value() == 50.0

        panel.cleanup()

    def test_get_metrics_inputs_returns_current(self, qtbot):
        """get_metrics_inputs returns current spinbox values."""
        panel = UserInputsPanel()
        qtbot.addWidget(panel)

        panel._flat_stake_spin.setValue(3000.0)
        panel._starting_capital_spin.setValue(50000.0)
        panel._fractional_kelly_spin.setValue(40.0)

        # Wait for internal state update
        qtbot.wait(200)

        inputs = panel.get_metrics_inputs()
        assert inputs.flat_stake == 3000.0
        assert inputs.starting_capital == 50000.0
        assert inputs.fractional_kelly == 40.0

        panel.cleanup()

    def test_get_adjustment_params_returns_current(self, qtbot):
        """get_adjustment_params returns current spinbox values."""
        panel = UserInputsPanel()
        qtbot.addWidget(panel)

        panel._stop_loss_spin.setValue(15.0)
        panel._efficiency_spin.setValue(7.0)

        # Wait for internal state update
        qtbot.wait(200)

        params = panel.get_adjustment_params()
        assert params.stop_loss == 15.0
        assert params.efficiency == 7.0

        panel.cleanup()

    def test_all_spinboxes_exist(self, qtbot):
        """Panel has all required spinboxes."""
        panel = UserInputsPanel()
        qtbot.addWidget(panel)

        spinboxes = panel.findChildren(QDoubleSpinBox)
        # flat_stake, starting_capital, fractional_kelly, stop_loss, efficiency
        assert len(spinboxes) == 5

        panel.cleanup()

    def test_cleanup_stops_timer(self, qtbot):
        """cleanup() stops the debounce timer."""
        panel = UserInputsPanel()
        qtbot.addWidget(panel)

        # Trigger a change to start debounce timer
        panel._flat_stake_spin.setValue(2000.0)

        # Timer should be active
        assert panel._debounce_timer.isActive()

        # Cleanup should stop it
        panel.cleanup()
        assert not panel._debounce_timer.isActive()
