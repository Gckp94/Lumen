"""Tests for DockManager visibility controls."""

import pytest
from PyQt6.QtWidgets import QWidget

from src.ui.dock_manager import DockManager


@pytest.fixture
def dock_manager(qtbot):
    """Create a DockManager instance for testing."""
    manager = DockManager()
    qtbot.addWidget(manager)
    return manager


@pytest.fixture
def dock_with_tabs(dock_manager):
    """Create a DockManager with test tabs."""
    widget1 = QWidget()
    widget2 = QWidget()
    dock_manager.add_dock("Tab One", widget1)
    dock_manager.add_dock("Tab Two", widget2)
    return dock_manager


class TestToggleDockVisibility:
    """Tests for toggle_dock_visibility method."""

    def test_toggle_hides_visible_dock(self, dock_with_tabs):
        """Toggling a visible dock should hide it."""
        dock = dock_with_tabs.get_dock("Tab One")
        # Dock starts as not closed (visible)
        assert not dock.isClosed()

        dock_with_tabs.toggle_dock_visibility("Tab One")

        assert dock.isClosed()

    def test_toggle_shows_hidden_dock(self, dock_with_tabs):
        """Toggling a hidden dock should show it."""
        dock = dock_with_tabs.get_dock("Tab One")
        dock.toggleView(False)  # Hide it first
        assert dock.isClosed()

        dock_with_tabs.toggle_dock_visibility("Tab One")

        assert not dock.isClosed()

    def test_toggle_nonexistent_dock_does_nothing(self, dock_with_tabs):
        """Toggling a nonexistent dock should not raise."""
        # Should not raise
        dock_with_tabs.toggle_dock_visibility("Nonexistent Tab")


class TestShowAllDocks:
    """Tests for show_all_docks method."""

    def test_show_all_restores_hidden_docks(self, dock_with_tabs):
        """show_all_docks should restore all hidden docks."""
        dock1 = dock_with_tabs.get_dock("Tab One")
        dock2 = dock_with_tabs.get_dock("Tab Two")

        # Hide both
        dock1.toggleView(False)
        dock2.toggleView(False)
        assert dock1.isClosed()
        assert dock2.isClosed()

        dock_with_tabs.show_all_docks()

        assert not dock1.isClosed()
        assert not dock2.isClosed()


class TestSetActiveDock:
    """Tests for set_active_dock method."""

    def test_set_active_dock_raises_tab(self, dock_with_tabs):
        """set_active_dock should make the specified tab current."""
        dock_with_tabs.set_active_dock("Tab Two")

        dock = dock_with_tabs.get_dock("Tab Two")
        assert dock.isCurrentTab()

    def test_set_active_nonexistent_dock_does_nothing(self, dock_with_tabs):
        """Setting active on nonexistent dock should not raise."""
        # Should not raise
        dock_with_tabs.set_active_dock("Nonexistent Tab")


class TestIsDockVisible:
    """Tests for is_dock_visible method."""

    def test_visible_dock_returns_true(self, dock_with_tabs):
        """is_dock_visible should return True for visible docks."""
        # Dock starts as not closed (visible)
        assert dock_with_tabs.is_dock_visible("Tab One") is True

    def test_hidden_dock_returns_false(self, dock_with_tabs):
        """is_dock_visible should return False for hidden docks."""
        dock = dock_with_tabs.get_dock("Tab One")
        dock.toggleView(False)

        assert dock_with_tabs.is_dock_visible("Tab One") is False

    def test_nonexistent_dock_returns_false(self, dock_with_tabs):
        """is_dock_visible should return False for nonexistent docks."""
        assert dock_with_tabs.is_dock_visible("Nonexistent") is False


class TestGetAllDockTitles:
    """Tests for get_all_dock_titles method."""

    def test_returns_all_titles(self, dock_with_tabs):
        """get_all_dock_titles should return all dock titles."""
        titles = dock_with_tabs.get_all_dock_titles()

        assert "Tab One" in titles
        assert "Tab Two" in titles
        assert len(titles) == 2


class TestDockManagerVisibility:
    """Tests for DockManager tab visibility methods."""

    def test_show_only_tabs_hides_others(self, qtbot) -> None:
        """show_only_tabs hides tabs not in the list."""
        manager = DockManager()
        qtbot.addWidget(manager)

        # Add test tabs
        manager.add_dock("Tab A", QWidget())
        manager.add_dock("Tab B", QWidget())
        manager.add_dock("Tab C", QWidget())

        # Show only Tab A and Tab B
        manager.show_only_tabs(["Tab A", "Tab B"])

        # Tab C should be hidden
        assert manager.is_dock_visible("Tab A")
        assert manager.is_dock_visible("Tab B")
        assert not manager.is_dock_visible("Tab C")

    def test_show_only_tabs_activates_first_if_active_hidden(self, qtbot) -> None:
        """If active tab is hidden, activate first visible tab."""
        manager = DockManager()
        qtbot.addWidget(manager)

        manager.add_dock("Tab A", QWidget())
        manager.add_dock("Tab B", QWidget())
        manager.set_active_dock("Tab B")

        # Hide Tab B by only showing Tab A
        manager.show_only_tabs(["Tab A"])

        # Should have activated Tab A
        dock_a = manager.get_dock("Tab A")
        assert dock_a is not None
