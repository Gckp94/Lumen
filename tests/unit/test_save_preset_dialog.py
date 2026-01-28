"""Tests for SavePresetDialog."""

import pytest
from pytestqt.qtbot import QtBot

from src.ui.dialogs.save_preset_dialog import SavePresetDialog


class TestSavePresetDialog:
    """Tests for SavePresetDialog."""

    def test_dialog_creation(self, qtbot: QtBot):
        """Test dialog can be created."""
        dialog = SavePresetDialog()
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Save Filter Preset"

    def test_get_preset_name_returns_input(self, qtbot: QtBot):
        """Test get_preset_name returns the entered name."""
        dialog = SavePresetDialog()
        qtbot.addWidget(dialog)

        dialog._name_input.setText("My Preset")

        assert dialog.get_preset_name() == "My Preset"

    def test_save_button_disabled_when_empty(self, qtbot: QtBot):
        """Test save button is disabled when name is empty."""
        dialog = SavePresetDialog()
        qtbot.addWidget(dialog)

        dialog._name_input.setText("")

        assert not dialog._save_btn.isEnabled()

    def test_save_button_enabled_when_name_entered(self, qtbot: QtBot):
        """Test save button is enabled when name is entered."""
        dialog = SavePresetDialog()
        qtbot.addWidget(dialog)

        dialog._name_input.setText("Test")

        assert dialog._save_btn.isEnabled()

    def test_set_existing_names_for_validation(self, qtbot: QtBot):
        """Test setting existing names for duplicate checking."""
        dialog = SavePresetDialog(existing_names=["Existing"])
        qtbot.addWidget(dialog)

        dialog._name_input.setText("Existing")

        # Should show warning but still allow save (for overwrite)
        assert dialog._save_btn.isEnabled()
        # Use isVisibleTo to check visibility relative to parent (works when dialog not shown)
        assert dialog._warning_label.isVisibleTo(dialog)
