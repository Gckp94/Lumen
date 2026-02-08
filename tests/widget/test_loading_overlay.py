"""Tests for LoadingOverlay widget."""

from PyQt6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from src.ui.components.loading_overlay import LoadingOverlay


class TestLoadingOverlay:
    """Tests for LoadingOverlay."""

    def test_overlay_hidden_by_default(self, qtbot: QtBot) -> None:
        """Overlay should be hidden when created."""
        parent = QWidget()
        qtbot.addWidget(parent)
        overlay = LoadingOverlay(parent)

        assert not overlay.isVisible()

    def test_show_overlay_makes_visible(self, qtbot: QtBot) -> None:
        """show() should make overlay visible."""
        parent = QWidget()
        parent.resize(400, 300)
        qtbot.addWidget(parent)
        parent.show()  # Parent must be shown for child visibility
        overlay = LoadingOverlay(parent)

        overlay.show()

        assert overlay.isVisible()

    def test_overlay_covers_parent(self, qtbot: QtBot) -> None:
        """Overlay should match parent geometry."""
        parent = QWidget()
        parent.resize(400, 300)
        qtbot.addWidget(parent)
        parent.show()  # Parent must be shown for showEvent to fire properly
        overlay = LoadingOverlay(parent)

        overlay.show()

        assert overlay.geometry() == parent.rect()

    def test_overlay_has_spinner(self, qtbot: QtBot) -> None:
        """Overlay should contain a spinner widget."""
        parent = QWidget()
        qtbot.addWidget(parent)
        overlay = LoadingOverlay(parent)

        assert overlay._spinner is not None
