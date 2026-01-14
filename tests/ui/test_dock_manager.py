"""Tests for DockManager."""

import PyQt6Ads as ads
import pytest
from PyQt6.QtWidgets import QWidget

from src.ui.dock_manager import DockManager


@pytest.mark.widget
class TestDockManager:
    """Tests for DockManager class."""

    def test_dock_manager_initialization(self, qtbot):
        """Test DockManager initializes correctly."""
        manager = DockManager()
        qtbot.addWidget(manager)
        assert manager is not None

    def test_add_dock_widget(self, qtbot):
        """Test adding a dock widget."""
        manager = DockManager()
        qtbot.addWidget(manager)

        test_widget = QWidget()
        manager.add_dock("Test Tab", test_widget)

        assert manager.dock_count() == 1

    def test_add_multiple_dock_widgets(self, qtbot):
        """Test adding multiple dock widgets."""
        manager = DockManager()
        qtbot.addWidget(manager)

        for i in range(3):
            widget = QWidget()
            manager.add_dock(f"Tab {i}", widget)

        assert manager.dock_count() == 3

    def test_floating_dock_widget_is_closable(self, qtbot):
        """Floating dock widgets should have closable feature enabled."""
        manager = DockManager()
        qtbot.addWidget(manager)

        widget = QWidget()
        dock_widget = manager.add_dock("Test", widget)

        # Verify closable feature is enabled (allows close button when floating)
        closable = ads.CDockWidget.DockWidgetFeature.DockWidgetClosable
        assert dock_widget.features().value & closable.value
