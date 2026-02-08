"""Widget tests for AdjustmentInputsPanel."""

from PyQt6.QtWidgets import QDoubleSpinBox
from pytestqt.qtbot import QtBot

from src.core.models import AdjustmentParams
from src.tabs.data_input import AdjustmentInputsPanel


class TestAdjustmentInputsPanel:
    """Tests for AdjustmentInputsPanel widget."""

    def test_panel_has_stop_loss_spinner(self, qtbot: QtBot) -> None:
        """Panel has Stop Loss % spinner."""
        panel = AdjustmentInputsPanel()
        qtbot.addWidget(panel)

        spinner = panel.findChild(QDoubleSpinBox, "stop_loss_spin")
        assert spinner is not None

    def test_panel_has_efficiency_spinner(self, qtbot: QtBot) -> None:
        """Panel has Efficiency % spinner."""
        panel = AdjustmentInputsPanel()
        qtbot.addWidget(panel)

        spinner = panel.findChild(QDoubleSpinBox, "efficiency_spin")
        assert spinner is not None

    def test_default_stop_loss_value(self, qtbot: QtBot) -> None:
        """Stop Loss % has default value of 100 (disabled by default)."""
        panel = AdjustmentInputsPanel()
        qtbot.addWidget(panel)

        spinner = panel.findChild(QDoubleSpinBox, "stop_loss_spin")
        assert spinner is not None
        assert spinner.value() == 100.0

    def test_default_efficiency_value(self, qtbot: QtBot) -> None:
        """Efficiency % has default value of 5."""
        panel = AdjustmentInputsPanel()
        qtbot.addWidget(panel)

        spinner = panel.findChild(QDoubleSpinBox, "efficiency_spin")
        assert spinner is not None
        assert spinner.value() == 5.0

    def test_stop_loss_range(self, qtbot: QtBot) -> None:
        """Stop Loss % has range 0-100."""
        panel = AdjustmentInputsPanel()
        qtbot.addWidget(panel)

        spinner = panel.findChild(QDoubleSpinBox, "stop_loss_spin")
        assert spinner is not None
        assert spinner.minimum() == 0.0
        assert spinner.maximum() == 100.0

    def test_efficiency_range(self, qtbot: QtBot) -> None:
        """Efficiency % has range 0-100."""
        panel = AdjustmentInputsPanel()
        qtbot.addWidget(panel)

        spinner = panel.findChild(QDoubleSpinBox, "efficiency_spin")
        assert spinner is not None
        assert spinner.minimum() == 0.0
        assert spinner.maximum() == 100.0

    def test_params_changed_signal_on_stop_loss_change(self, qtbot: QtBot) -> None:
        """params_changed signal emits when stop loss changed.

        Note: Since editingFinished is used (not valueChanged), we need to
        explicitly trigger the signal emission after programmatic setValue.
        """
        panel = AdjustmentInputsPanel()
        qtbot.addWidget(panel)

        received_params: list[AdjustmentParams] = []
        panel.params_changed.connect(lambda p: received_params.append(p))

        spinner = panel.findChild(QDoubleSpinBox, "stop_loss_spin")
        assert spinner is not None
        spinner.setValue(10.0)
        # Explicitly call handler since editingFinished doesn't fire on setValue
        panel._on_value_changed()

        assert len(received_params) == 1
        assert received_params[0].stop_loss == 10.0
        assert received_params[0].efficiency == 5.0

    def test_params_changed_signal_on_efficiency_change(self, qtbot: QtBot) -> None:
        """params_changed signal emits when efficiency changed.

        Note: Since editingFinished is used (not valueChanged), we need to
        explicitly trigger the signal emission after programmatic setValue.
        """
        panel = AdjustmentInputsPanel()
        qtbot.addWidget(panel)

        received_params: list[AdjustmentParams] = []
        panel.params_changed.connect(lambda p: received_params.append(p))

        spinner = panel.findChild(QDoubleSpinBox, "efficiency_spin")
        assert spinner is not None
        spinner.setValue(3.0)
        # Explicitly call handler since editingFinished doesn't fire on setValue
        panel._on_value_changed()

        assert len(received_params) == 1
        assert received_params[0].stop_loss == 100.0  # Default is now 100
        assert received_params[0].efficiency == 3.0

    def test_get_params_returns_current_values(self, qtbot: QtBot) -> None:
        """get_params returns current AdjustmentParams.

        Note: get_params returns the internal _params state, which is only
        updated when _on_value_changed is called. We need to trigger the
        handler after programmatic setValue for the internal state to update.
        """
        panel = AdjustmentInputsPanel()
        qtbot.addWidget(panel)

        params = panel.get_params()
        assert params.stop_loss == 100.0  # Default is now 100
        assert params.efficiency == 5.0

        # Change values and trigger handler since editingFinished doesn't fire
        panel._stop_loss_spin.setValue(12.0)
        panel._efficiency_spin.setValue(7.0)
        panel._on_value_changed()  # Update internal state

        params = panel.get_params()
        assert params.stop_loss == 12.0
        assert params.efficiency == 7.0

    def test_set_params_updates_spinners(self, qtbot: QtBot) -> None:
        """set_params updates spinner values."""
        panel = AdjustmentInputsPanel()
        qtbot.addWidget(panel)

        new_params = AdjustmentParams(stop_loss=15.0, efficiency=2.5)
        panel.set_params(new_params)

        assert panel._stop_loss_spin.value() == 15.0
        assert panel._efficiency_spin.value() == 2.5

    def test_set_params_does_not_emit_signal(self, qtbot: QtBot) -> None:
        """set_params does not emit params_changed signal."""
        panel = AdjustmentInputsPanel()
        qtbot.addWidget(panel)

        received_params: list[AdjustmentParams] = []
        panel.params_changed.connect(lambda p: received_params.append(p))

        new_params = AdjustmentParams(stop_loss=15.0, efficiency=2.5)
        panel.set_params(new_params)

        # Should not emit signal during set
        assert len(received_params) == 0
