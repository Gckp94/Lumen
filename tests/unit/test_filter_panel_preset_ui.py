"""Tests for FilterPanel preset save/load UI."""

import pytest
from pytestqt.qtbot import QtBot

from src.ui.components.filter_panel import FilterPanel


class TestFilterPanelPresetUI:
    """Tests for FilterPanel preset save/load buttons."""

    def test_has_save_button(self, qtbot: QtBot):
        """Test FilterPanel has a Save button."""
        panel = FilterPanel()
        qtbot.addWidget(panel)

        assert hasattr(panel, "_save_btn")
        assert panel._save_btn.text() == "Save"

    def test_has_load_combo(self, qtbot: QtBot):
        """Test FilterPanel has a Load dropdown."""
        panel = FilterPanel()
        qtbot.addWidget(panel)

        assert hasattr(panel, "_load_combo")

    def test_save_button_emits_signal(self, qtbot: QtBot):
        """Test Save button click emits preset_save_requested signal."""
        panel = FilterPanel()
        qtbot.addWidget(panel)

        with qtbot.waitSignal(panel.preset_save_requested, timeout=1000):
            panel._save_btn.click()

    def test_load_combo_emits_signal_on_selection(self, qtbot: QtBot):
        """Test Load combo selection emits preset_load_requested signal."""
        panel = FilterPanel()
        qtbot.addWidget(panel)

        # Add a preset to the combo
        panel.update_preset_list(["Test Preset"])

        with qtbot.waitSignal(panel.preset_load_requested, timeout=1000) as blocker:
            panel._load_combo.setCurrentIndex(1)  # Select "Test Preset"

        assert blocker.args == ["Test Preset"]

    def test_update_preset_list(self, qtbot: QtBot):
        """Test update_preset_list populates the dropdown."""
        panel = FilterPanel()
        qtbot.addWidget(panel)

        panel.update_preset_list(["Alpha", "Beta", "Gamma"])

        # First item is placeholder, then presets
        assert panel._load_combo.count() == 4
        assert panel._load_combo.itemText(1) == "Alpha"
        assert panel._load_combo.itemText(2) == "Beta"
        assert panel._load_combo.itemText(3) == "Gamma"

    def test_empty_preset_list_shows_placeholder(self, qtbot: QtBot):
        """Test empty preset list shows 'No saved presets'."""
        panel = FilterPanel()
        qtbot.addWidget(panel)

        panel.update_preset_list([])

        assert panel._load_combo.count() == 1
        assert "No saved presets" in panel._load_combo.itemText(0)
