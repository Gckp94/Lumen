"""Unit tests for AxisControlPanel component."""


from src.ui.components.axis_control_panel import AxisControlPanel


class TestAxisControlPanelInitialization:
    """Tests for AxisControlPanel initialization."""

    def test_panel_creates_spin_boxes(self, qtbot):
        """Panel creates X and Y min/max spin boxes."""
        panel = AxisControlPanel()
        qtbot.addWidget(panel)

        assert panel._x_min is not None
        assert panel._x_max is not None
        assert panel._y_min is not None
        assert panel._y_max is not None

    def test_panel_creates_auto_fit_button(self, qtbot):
        """Panel creates Auto Fit button."""
        panel = AxisControlPanel()
        qtbot.addWidget(panel)

        assert panel._auto_fit_btn is not None
        assert panel._auto_fit_btn.text() == "Auto Fit"

    def test_panel_creates_grid_checkbox(self, qtbot):
        """Panel creates Show Grid checkbox."""
        panel = AxisControlPanel()
        qtbot.addWidget(panel)

        assert panel._grid_checkbox is not None
        assert panel._grid_checkbox.text() == "Show Grid"

    def test_grid_checkbox_unchecked_by_default(self, qtbot):
        """Grid checkbox is unchecked by default."""
        panel = AxisControlPanel()
        qtbot.addWidget(panel)

        assert panel._grid_checkbox.isChecked() is False

    def test_spin_boxes_have_correct_ranges(self, qtbot):
        """Spin boxes have large ranges for flexibility."""
        panel = AxisControlPanel()
        qtbot.addWidget(panel)

        # Should allow very large values
        assert panel._x_min.minimum() == -1e9
        assert panel._x_max.maximum() == 1e9
        assert panel._y_min.minimum() == -1e9
        assert panel._y_max.maximum() == 1e9

    def test_x_spin_boxes_have_zero_decimals(self, qtbot):
        """X spin boxes have 0 decimals (index values)."""
        panel = AxisControlPanel()
        qtbot.addWidget(panel)

        assert panel._x_min.decimals() == 0
        assert panel._x_max.decimals() == 0

    def test_y_spin_boxes_have_two_decimals(self, qtbot):
        """Y spin boxes have 2 decimals (float values)."""
        panel = AxisControlPanel()
        qtbot.addWidget(panel)

        assert panel._y_min.decimals() == 2
        assert panel._y_max.decimals() == 2


class TestAxisControlPanelSignals:
    """Tests for AxisControlPanel signals."""

    def test_has_range_changed_signal(self, qtbot):
        """Panel has range_changed signal."""
        panel = AxisControlPanel()
        qtbot.addWidget(panel)

        assert hasattr(panel, "range_changed")

    def test_has_auto_fit_clicked_signal(self, qtbot):
        """Panel has auto_fit_clicked signal."""
        panel = AxisControlPanel()
        qtbot.addWidget(panel)

        assert hasattr(panel, "auto_fit_clicked")

    def test_has_grid_toggled_signal(self, qtbot):
        """Panel has grid_toggled signal."""
        panel = AxisControlPanel()
        qtbot.addWidget(panel)

        assert hasattr(panel, "grid_toggled")

    def test_auto_fit_button_emits_signal(self, qtbot):
        """Auto Fit button click emits auto_fit_clicked signal."""
        panel = AxisControlPanel()
        qtbot.addWidget(panel)

        with qtbot.waitSignal(panel.auto_fit_clicked, timeout=1000):
            panel._auto_fit_btn.click()

    def test_grid_checkbox_emits_signal(self, qtbot):
        """Grid checkbox toggle emits grid_toggled signal."""
        panel = AxisControlPanel()
        qtbot.addWidget(panel)

        with qtbot.waitSignal(panel.grid_toggled, timeout=1000):
            panel._grid_checkbox.click()

    def test_range_change_signal_debounced(self, qtbot):
        """Signal is debounced - emits after delay, not immediately."""
        panel = AxisControlPanel()
        qtbot.addWidget(panel)

        # Use waitSignal with timeout to wait for debounced signal
        with qtbot.waitSignal(panel.range_changed, timeout=500):
            panel._x_min.setValue(10)
            panel._x_max.setValue(100)
            # Signal should fire after debounce delay (150ms)


class TestAxisControlPanelSetRange:
    """Tests for AxisControlPanel.set_range() method."""

    def test_set_range_updates_values(self, qtbot):
        """set_range() updates spin box values."""
        panel = AxisControlPanel()
        qtbot.addWidget(panel)

        panel.set_range(0, 1000, -10.5, 10.5)

        assert panel._x_min.value() == 0
        assert panel._x_max.value() == 1000
        assert panel._y_min.value() == -10.5
        assert panel._y_max.value() == 10.5

    def test_set_range_does_not_emit_signal(self, qtbot):
        """set_range() updates values without emitting range_changed."""
        panel = AxisControlPanel()
        qtbot.addWidget(panel)

        signal_received = []
        panel.range_changed.connect(lambda *args: signal_received.append(args))

        panel.set_range(0, 1000, -10, 10)

        # Wait past debounce time
        qtbot.wait(200)

        assert len(signal_received) == 0

    def test_set_range_handles_negative_values(self, qtbot):
        """set_range() handles negative values correctly."""
        panel = AxisControlPanel()
        qtbot.addWidget(panel)

        panel.set_range(-500, 500, -100.25, 100.25)

        assert panel._x_min.value() == -500
        assert panel._x_max.value() == 500
        assert panel._y_min.value() == -100.25
        assert panel._y_max.value() == 100.25


class TestAxisControlPanelGridCheckbox:
    """Tests for AxisControlPanel grid checkbox functionality."""

    def test_set_grid_checked_true(self, qtbot):
        """set_grid_checked(True) checks the checkbox."""
        panel = AxisControlPanel()
        qtbot.addWidget(panel)

        panel.set_grid_checked(True)

        assert panel._grid_checkbox.isChecked() is True

    def test_set_grid_checked_false(self, qtbot):
        """set_grid_checked(False) unchecks the checkbox."""
        panel = AxisControlPanel()
        qtbot.addWidget(panel)

        panel.set_grid_checked(True)
        panel.set_grid_checked(False)

        assert panel._grid_checkbox.isChecked() is False

    def test_set_grid_checked_does_not_emit_signal(self, qtbot):
        """set_grid_checked() does not emit grid_toggled signal."""
        panel = AxisControlPanel()
        qtbot.addWidget(panel)

        signal_received = []
        panel.grid_toggled.connect(lambda v: signal_received.append(v))

        panel.set_grid_checked(True)
        panel.set_grid_checked(False)

        assert len(signal_received) == 0
