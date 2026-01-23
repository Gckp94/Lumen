"""Unit tests for DockManager.

Tests use mock-binding technique to test DockManager method logic in isolation
without requiring full Qt GUI initialization.
"""

from unittest.mock import MagicMock


class TestDockAllFloating:
    """Tests for dock_all_floating method."""

    def _create_mock_manager(self):
        """Create a minimal mock that simulates DockManager structure.

        We test the method logic in isolation by creating a mock object
        and attaching the actual method from DockManager.
        """
        # Import the module to get access to ads
        import PyQt6Ads as ads

        mock_manager = MagicMock()
        mock_manager._center_area = MagicMock()
        mock_manager.floatingWidgets = MagicMock(return_value=[])
        mock_manager.addDockWidget = MagicMock()

        return mock_manager, ads

    def test_dock_all_floating_redocks_floating_widgets(self):
        """Verify floating widgets are re-docked to center area."""
        mock_manager, ads = self._create_mock_manager()

        # Import the method we want to test
        from src.ui.dock_manager import DockManager

        # Create mock floating widget with dock widget
        mock_dock_widget = MagicMock()
        mock_dock_widget.windowTitle.return_value = "Test Tab"
        mock_floating_widget = MagicMock()
        mock_floating_widget.dockWidget.return_value = mock_dock_widget

        # Setup floatingWidgets to return our mock
        mock_manager.floatingWidgets.return_value = [mock_floating_widget]

        # Call the actual method on our mock (bind it)
        DockManager.dock_all_floating(mock_manager)

        # Verify addDockWidget was called to re-dock the floating widget
        mock_manager.addDockWidget.assert_called_once()
        call_args = mock_manager.addDockWidget.call_args
        assert call_args[0][0] == ads.DockWidgetArea.CenterDockWidgetArea
        assert call_args[0][1] == mock_dock_widget
        assert call_args[0][2] == mock_manager._center_area

    def test_dock_all_floating_does_nothing_when_no_floating(self):
        """Verify no errors when no floating widgets exist."""
        mock_manager, ads = self._create_mock_manager()

        from src.ui.dock_manager import DockManager

        # No floating widgets
        mock_manager.floatingWidgets.return_value = []

        # Should not raise
        DockManager.dock_all_floating(mock_manager)

        # addDockWidget should not be called
        mock_manager.addDockWidget.assert_not_called()

    def test_dock_all_floating_handles_none_center_area(self):
        """Verify graceful handling when center area not initialized."""
        mock_manager, ads = self._create_mock_manager()

        from src.ui.dock_manager import DockManager

        mock_manager._center_area = None

        mock_dock_widget = MagicMock()
        mock_floating = MagicMock()
        mock_floating.dockWidget.return_value = mock_dock_widget
        mock_manager.floatingWidgets.return_value = [mock_floating]

        # Should not raise even with None center area
        DockManager.dock_all_floating(mock_manager)

        # addDockWidget should not be called when center_area is None
        mock_manager.addDockWidget.assert_not_called()

    def test_dock_all_floating_handles_none_dock_widget(self):
        """Verify graceful handling when floating container has no dock widget."""
        mock_manager, ads = self._create_mock_manager()

        from src.ui.dock_manager import DockManager

        # Floating container with None dock widget
        mock_floating = MagicMock()
        mock_floating.dockWidget.return_value = None
        mock_manager.floatingWidgets.return_value = [mock_floating]

        # Should not raise
        DockManager.dock_all_floating(mock_manager)

        # addDockWidget should not be called for None dock widget
        mock_manager.addDockWidget.assert_not_called()

    def test_dock_all_floating_handles_multiple_floating_widgets(self):
        """Verify all floating widgets are re-docked."""
        mock_manager, ads = self._create_mock_manager()

        from src.ui.dock_manager import DockManager

        # Create multiple floating widgets
        mock_dock_widget_1 = MagicMock()
        mock_dock_widget_1.windowTitle.return_value = "Tab 1"
        mock_floating_1 = MagicMock()
        mock_floating_1.dockWidget.return_value = mock_dock_widget_1

        mock_dock_widget_2 = MagicMock()
        mock_dock_widget_2.windowTitle.return_value = "Tab 2"
        mock_floating_2 = MagicMock()
        mock_floating_2.dockWidget.return_value = mock_dock_widget_2

        mock_manager.floatingWidgets.return_value = [mock_floating_1, mock_floating_2]

        # Call the method
        DockManager.dock_all_floating(mock_manager)

        # Verify addDockWidget was called twice
        assert mock_manager.addDockWidget.call_count == 2


class TestDockManagerConfig:
    """Tests for DockManager configuration."""

    def test_double_click_undock_disabled(self):
        """Verify DoubleClickUndocksWidget is disabled to prevent accidental undocking."""
        import inspect
        from src.ui.dock_manager import DockManager

        # Get the source code of __init__
        source = inspect.getsource(DockManager.__init__)

        # Verify DoubleClickUndocksWidget is explicitly disabled
        assert "DoubleClickUndocksWidget" in source, (
            "Expected DockManager to configure DoubleClickUndocksWidget flag"
        )
        assert "DoubleClickUndocksWidget, False" in source, (
            "Expected DoubleClickUndocksWidget to be set to False"
        )
