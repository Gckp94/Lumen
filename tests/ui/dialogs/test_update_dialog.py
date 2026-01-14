"""Tests for UpdateDialog."""

import pytest

from src.core.update_checker import UpdateInfo
from src.ui.dialogs.update_dialog import UpdateDialog


@pytest.mark.widget
class TestUpdateDialog:
    """Tests for UpdateDialog class."""

    def test_dialog_shows_version_info(self, qtbot):
        """Test dialog displays version information."""
        info = UpdateInfo(
            version="2.0.0",
            download_url="https://example.com/Lumen.exe",
            release_url="https://github.com/owner/repo/releases/tag/v2.0.0",
        )

        dialog = UpdateDialog(info, "1.0.0")
        qtbot.addWidget(dialog)

        assert "2.0.0" in dialog.message_label.text()
        assert "1.0.0" in dialog.message_label.text()

    def test_dialog_has_update_and_skip_buttons(self, qtbot):
        """Test dialog has appropriate buttons."""
        info = UpdateInfo(
            version="2.0.0",
            download_url="https://example.com/Lumen.exe",
            release_url="https://github.com/owner/repo/releases/tag/v2.0.0",
        )

        dialog = UpdateDialog(info, "1.0.0")
        qtbot.addWidget(dialog)

        buttons = dialog.button_box.buttons()
        assert len(buttons) == 2
