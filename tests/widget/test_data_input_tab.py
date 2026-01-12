"""Widget tests for DataInputTab."""

from PyQt6.QtWidgets import QComboBox, QLineEdit, QPushButton
from pytestqt.qtbot import QtBot

from src.tabs.data_input import AdjustmentInputsPanel, DataInputTab


class TestDataInputTabWidgets:
    """Tests for DataInputTab widget structure."""

    def test_tab_has_select_file_button(self, qtbot: QtBot) -> None:
        """DataInputTab contains Select File button."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        button = tab.findChild(QPushButton, "select_file_button")
        assert button is not None
        assert "Select File" in button.text()

    def test_file_path_display_exists(self, qtbot: QtBot) -> None:
        """DataInputTab contains file path display."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        line_edit = tab.findChild(QLineEdit, "file_path_display")
        assert line_edit is not None

    def test_file_path_display_is_readonly(self, qtbot: QtBot) -> None:
        """File path display is read-only."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        line_edit = tab.findChild(QLineEdit, "file_path_display")
        assert line_edit is not None
        assert line_edit.isReadOnly()

    def test_load_button_exists(self, qtbot: QtBot) -> None:
        """DataInputTab contains Load Data button."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        button = tab.findChild(QPushButton, "load_data_button")
        assert button is not None
        assert "Load Data" in button.text()

    def test_load_button_initially_disabled(self, qtbot: QtBot) -> None:
        """Load Data button is disabled until file selected."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        button = tab.findChild(QPushButton, "load_data_button")
        assert button is not None
        assert not button.isEnabled()

    def test_sheet_selector_exists(self, qtbot: QtBot) -> None:
        """DataInputTab contains sheet selector."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        combo = tab.findChild(QComboBox, "sheet_selector")
        assert combo is not None

    def test_sheet_selector_initially_hidden(self, qtbot: QtBot) -> None:
        """Sheet selector is hidden until Excel file selected."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        combo = tab.findChild(QComboBox, "sheet_selector")
        assert combo is not None
        assert not combo.isVisible()

    def test_dataframe_property_initially_none(self, qtbot: QtBot) -> None:
        """DataFrame property is None before loading."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        assert tab.dataframe is None


class TestDataInputTabAdjustmentPanel:
    """Tests for AdjustmentInputsPanel integration in DataInputTab."""

    def test_tab_has_adjustment_panel(self, qtbot: QtBot) -> None:
        """DataInputTab contains AdjustmentInputsPanel."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        panel = tab.findChild(AdjustmentInputsPanel, "adjustment_inputs_panel")
        assert panel is not None

    def test_adjustment_panel_initially_hidden(self, qtbot: QtBot) -> None:
        """AdjustmentInputsPanel is hidden before mapping complete."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        panel = tab.findChild(AdjustmentInputsPanel, "adjustment_inputs_panel")
        assert panel is not None
        assert not panel.isVisible()

    def test_adjustment_debounce_timer_exists(self, qtbot: QtBot) -> None:
        """DataInputTab has debounce timer for adjustments."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        assert hasattr(tab, "_adjustment_debounce_timer")
        assert tab._adjustment_debounce_timer.interval() == 300
        assert tab._adjustment_debounce_timer.isSingleShot()

    def test_pending_adjustment_params_initially_none(self, qtbot: QtBot) -> None:
        """Pending adjustment params is None before mapping."""
        tab = DataInputTab()
        qtbot.addWidget(tab)
        assert tab._pending_adjustment_params is None
