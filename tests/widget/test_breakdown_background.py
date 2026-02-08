# tests/widget/test_breakdown_background.py
"""Tests for Breakdown tab background calculation integration."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from pytestqt.qtbot import QtBot

from src.core.app_state import AppState


class TestBreakdownBackground:
    """Tests for background calculation in Breakdown tab."""

    def test_breakdown_has_loading_overlay(self, qtbot: QtBot) -> None:
        """Breakdown tab should have loading overlay."""
        from src.tabs.breakdown import BreakdownTab

        # Use real AppState for clean initialization
        app_state = AppState()

        tab = BreakdownTab(app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_loading_overlay")
        tab.cleanup()

    def test_filtered_data_update_checks_visibility(self, qtbot: QtBot) -> None:
        """Tab should check visibility before calculating."""
        from src.tabs.breakdown import BreakdownTab

        # Use real AppState
        app_state = AppState()

        # Create mock visibility tracker
        mock_tracker = MagicMock()
        mock_tracker.is_visible.return_value = False

        tab = BreakdownTab(app_state)
        qtbot.addWidget(tab)

        # Simulate dock widget being set
        dock = MagicMock()
        tab.set_dock_widget(dock)

        # Patch the visibility tracker property on the app_state instance
        with patch.object(type(app_state), 'visibility_tracker', new_callable=lambda: property(lambda self: mock_tracker)):
            # Simulate filter update
            tab._on_filtered_data_updated(pd.DataFrame({"gain_pct": [0.01]}))

            # Should have checked visibility
            mock_tracker.is_visible.assert_called()

        tab.cleanup()
