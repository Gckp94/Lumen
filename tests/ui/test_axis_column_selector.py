"""Tests for AxisColumnSelector component."""

from pytestqt.qtbot import QtBot

from src.ui.components.axis_column_selector import AxisColumnSelector


class TestAxisColumnSelector:
    """Tests for the AxisColumnSelector widget."""

    def test_initial_state(self, qtbot: QtBot) -> None:
        """Widget initializes with empty dropdowns and disabled state."""
        selector = AxisColumnSelector()
        qtbot.addWidget(selector)

        assert selector._x_combo.count() == 1  # Just "(Index)"
        assert selector._x_combo.currentText() == "(Index)"
        assert selector._y_combo.count() == 0
        assert not selector._x_combo.isEnabled()
        assert not selector._y_combo.isEnabled()

    def test_set_columns_populates_dropdowns(self, qtbot: QtBot) -> None:
        """set_columns populates both dropdowns with column names."""
        selector = AxisColumnSelector()
        qtbot.addWidget(selector)

        selector.set_columns(["feature_a", "feature_b", "pnl"])

        # X combo has (Index) + columns
        assert selector._x_combo.count() == 4
        assert selector._x_combo.itemText(0) == "(Index)"
        assert selector._x_combo.itemText(1) == "feature_a"

        # Y combo has just columns
        assert selector._y_combo.count() == 3
        assert selector._y_combo.itemText(0) == "feature_a"

    def test_set_columns_enables_dropdowns(self, qtbot: QtBot) -> None:
        """set_columns enables the dropdowns when columns are provided."""
        selector = AxisColumnSelector()
        qtbot.addWidget(selector)

        selector.set_columns(["feature_a", "pnl"])

        assert selector._x_combo.isEnabled()
        assert selector._y_combo.isEnabled()

    def test_x_column_returns_none_for_index(self, qtbot: QtBot) -> None:
        """x_column property returns None when (Index) is selected."""
        selector = AxisColumnSelector()
        qtbot.addWidget(selector)
        selector.set_columns(["feature_a"])

        selector._x_combo.setCurrentIndex(0)  # (Index)
        assert selector.x_column is None

    def test_x_column_returns_column_name(self, qtbot: QtBot) -> None:
        """x_column property returns column name when selected."""
        selector = AxisColumnSelector()
        qtbot.addWidget(selector)
        selector.set_columns(["feature_a", "feature_b"])

        selector._x_combo.setCurrentText("feature_b")
        assert selector.x_column == "feature_b"

    def test_y_column_returns_selected_column(self, qtbot: QtBot) -> None:
        """y_column property returns the selected Y column name."""
        selector = AxisColumnSelector()
        qtbot.addWidget(selector)
        selector.set_columns(["feature_a", "pnl"])

        selector._y_combo.setCurrentText("pnl")
        assert selector.y_column == "pnl"

    def test_selection_changed_signal_emitted(self, qtbot: QtBot) -> None:
        """selection_changed signal emits when either dropdown changes."""
        selector = AxisColumnSelector()
        qtbot.addWidget(selector)
        selector.set_columns(["feature_a", "feature_b"])

        with qtbot.waitSignal(selector.selection_changed, timeout=1000):
            selector._y_combo.setCurrentText("feature_b")

    def test_x_bounds_signal_emitted(self, qtbot: QtBot) -> None:
        """X bounds change emits signal."""
        selector = AxisColumnSelector()
        qtbot.addWidget(selector)

        with qtbot.waitSignal(selector.x_bounds_changed, timeout=500):
            selector._x_min.setValue(10.0)

    def test_y_bounds_signal_emitted(self, qtbot: QtBot) -> None:
        """Y bounds change emits signal."""
        selector = AxisColumnSelector()
        qtbot.addWidget(selector)

        with qtbot.waitSignal(selector.y_bounds_changed, timeout=500):
            selector._y_min.setValue(5.0)

    def test_set_x_bounds_no_signal(self, qtbot: QtBot) -> None:
        """set_x_bounds does not emit signal."""
        selector = AxisColumnSelector()
        qtbot.addWidget(selector)

        with qtbot.assertNotEmitted(selector.x_bounds_changed):
            selector.set_x_bounds(0, 100)

        assert selector.x_bounds == (0, 100)

    def test_set_y_bounds_no_signal(self, qtbot: QtBot) -> None:
        """set_y_bounds does not emit signal."""
        selector = AxisColumnSelector()
        qtbot.addWidget(selector)

        with qtbot.assertNotEmitted(selector.y_bounds_changed):
            selector.set_y_bounds(-50, 50)

        assert selector.y_bounds == (-50, 50)
