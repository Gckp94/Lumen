# Fix Tab Auto-Undock on Startup

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ensure all tabs start docked when the application launches, preventing intermittent auto-undocking behavior.

**Architecture:** Add a `dock_all_floating()` method to DockManager that iterates through all floating widgets and re-docks them to the center area. Call this method at the end of MainWindow initialization to guarantee consistent startup state.

**Tech Stack:** PyQt6, PyQt6Ads

---

## Task 1: Add dock_all_floating method to DockManager

**Files:**
- Modify: `src/ui/dock_manager.py:230-260` (add new method at end of class)
- Test: `tests/unit/test_dock_manager.py` (create new file)

**Step 1: Write the failing test**

Create the test file:

```python
"""Unit tests for DockManager."""

import pytest
from unittest.mock import MagicMock, patch


class TestDockAllFloating:
    """Tests for dock_all_floating method."""

    def test_dock_all_floating_redocks_floating_widgets(self):
        """Verify floating widgets are re-docked to center area."""
        with patch("src.ui.dock_manager.ads") as mock_ads:
            from src.ui.dock_manager import DockManager

            # Create mock parent
            mock_parent = MagicMock()

            # Create manager
            manager = DockManager(mock_parent)

            # Create mock floating widget
            mock_floating_widget = MagicMock()
            mock_floating_widget.dockWidget.return_value = MagicMock()

            # Create mock center area
            mock_center_area = MagicMock()
            manager._center_area = mock_center_area

            # Setup floatingWidgets to return our mock
            manager.floatingWidgets = MagicMock(return_value=[mock_floating_widget])

            # Call dock_all_floating
            manager.dock_all_floating()

            # Verify addDockWidget was called to re-dock the floating widget
            manager.addDockWidget.assert_called()

    def test_dock_all_floating_does_nothing_when_no_floating(self):
        """Verify no errors when no floating widgets exist."""
        with patch("src.ui.dock_manager.ads") as mock_ads:
            from src.ui.dock_manager import DockManager

            mock_parent = MagicMock()
            manager = DockManager(mock_parent)
            manager._center_area = MagicMock()

            # No floating widgets
            manager.floatingWidgets = MagicMock(return_value=[])

            # Should not raise
            manager.dock_all_floating()

            # addDockWidget should not be called
            manager.addDockWidget.assert_not_called()

    def test_dock_all_floating_handles_none_center_area(self):
        """Verify graceful handling when center area not initialized."""
        with patch("src.ui.dock_manager.ads") as mock_ads:
            from src.ui.dock_manager import DockManager

            mock_parent = MagicMock()
            manager = DockManager(mock_parent)
            manager._center_area = None

            mock_floating = MagicMock()
            mock_floating.dockWidget.return_value = MagicMock()
            manager.floatingWidgets = MagicMock(return_value=[mock_floating])

            # Should not raise even with None center area
            manager.dock_all_floating()
```

**Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/unit/test_dock_manager.py -v`
Expected: FAIL with "AttributeError: 'DockManager' object has no attribute 'dock_all_floating'"

**Step 3: Write minimal implementation**

Add to `src/ui/dock_manager.py` after `get_all_dock_titles()` method:

```python
    def dock_all_floating(self) -> None:
        """Dock all floating widgets back to the center area.

        Iterates through all floating containers and re-docks their
        dock widgets to the center dock area. This ensures a consistent
        startup state with all tabs docked.
        """
        if self._center_area is None:
            logger.warning("Cannot dock floating widgets: center area not initialized")
            return

        floating_containers = self.floatingWidgets()
        for container in floating_containers:
            # Each floating container holds dock widgets
            dock_widget = container.dockWidget()
            if dock_widget is not None:
                self.addDockWidget(
                    ads.DockWidgetArea.CenterDockWidgetArea,
                    dock_widget,
                    self._center_area,
                )
                logger.debug("Docked floating widget: %s", dock_widget.windowTitle())
```

**Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/unit/test_dock_manager.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_dock_manager.py src/ui/dock_manager.py
git commit -m "feat(dock): add dock_all_floating method to ensure tabs start docked"
```

---

## Task 2: Call dock_all_floating at startup

**Files:**
- Modify: `src/ui/main_window.py:48-52` (add call after set_active_dock)

**Step 1: Write the failing test**

Add test to verify MainWindow calls dock_all_floating:

```python
# Add to tests/unit/test_dock_manager.py

class TestMainWindowStartup:
    """Tests for MainWindow startup behavior."""

    def test_main_window_docks_all_floating_at_startup(self):
        """Verify MainWindow ensures all tabs are docked on init."""
        with patch("src.ui.main_window.DockManager") as MockDockManager:
            with patch("src.ui.main_window.DataInputTab"):
                with patch("src.ui.main_window.FeatureExplorerTab"):
                    with patch("src.ui.main_window.BreakdownTab"):
                        with patch("src.ui.main_window.DataBinningTab"):
                            with patch("src.ui.main_window.PnLStatsTab"):
                                with patch("src.ui.main_window.MonteCarloTab"):
                                    with patch("src.ui.main_window.ParameterSensitivityTab"):
                                        with patch("src.ui.main_window.FeatureInsightsTab"):
                                            with patch("src.ui.main_window.PortfolioOverviewTab"):
                                                with patch("src.ui.main_window.AppState"):
                                                    from src.ui.main_window import MainWindow

                                                    mock_dock_manager = MagicMock()
                                                    MockDockManager.return_value = mock_dock_manager

                                                    window = MainWindow()

                                                    # Verify dock_all_floating was called
                                                    mock_dock_manager.dock_all_floating.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/unit/test_dock_manager.py::TestMainWindowStartup -v`
Expected: FAIL with "AssertionError: Expected 'dock_all_floating' to be called once"

**Step 3: Write minimal implementation**

Modify `src/ui/main_window.py` in `__init__`:

```python
        # Set Data Input as the default active tab
        self.dock_manager.set_active_dock("Data Input")

        # Ensure all tabs are docked (fixes intermittent auto-undocking on startup)
        self.dock_manager.dock_all_floating()

        logger.debug("MainWindow initialized with dockable tabs")
```

**Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/unit/test_dock_manager.py::TestMainWindowStartup -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/ui/main_window.py tests/unit/test_dock_manager.py
git commit -m "fix(startup): ensure all tabs are docked when app launches"
```

---

## Task 3: Manual testing

**Step 1: Run the application**

Run: `.venv/Scripts/python -m src.main`

**Step 2: Verify behavior**

1. All tabs should appear docked in the center area
2. Undock a tab by dragging it out
3. Close the application
4. Reopen the application
5. Verify all tabs are docked (the previously floating tab should now be docked)

**Step 3: Test edge cases**

1. Open app with different window sizes
2. Open app on different monitors (if available)
3. Rapidly open/close the app several times

**Step 4: Commit any adjustments if needed**

---

## Summary

This fix ensures consistent startup behavior by explicitly docking any floating widgets after the dock manager initializes. Even if some external factor causes tabs to float during initialization, the `dock_all_floating()` call will immediately correct the state before the user sees the window.
