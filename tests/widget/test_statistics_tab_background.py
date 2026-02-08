# tests/widget/test_statistics_tab_background.py
"""Tests for Statistics tab background calculation integration."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from pytestqt.qtbot import QtBot


class TestStatisticsTabBackground:
    """Tests for background calculation in Statistics tab."""

    def test_statistics_tab_has_loading_overlay(self, qtbot: QtBot) -> None:
        """Statistics tab should have loading overlay."""
        from src.tabs.statistics_tab import StatisticsTab

        app_state = MagicMock()
        app_state.column_mapping = None
        app_state.filtered_df = None
        app_state.visibility_tracker = MagicMock()

        tab = StatisticsTab(app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_loading_overlay")
        assert tab._loading_overlay is not None

    def test_filtered_data_update_checks_visibility(self, qtbot: QtBot) -> None:
        """Tab should check visibility before calculating."""
        from src.tabs.statistics_tab import StatisticsTab

        app_state = MagicMock()
        app_state.column_mapping = MagicMock()
        app_state.filtered_df = pd.DataFrame({"gain_pct": [0.01, -0.02]})
        app_state.visibility_tracker = MagicMock()
        app_state.visibility_tracker.is_visible.return_value = False

        tab = StatisticsTab(app_state)
        qtbot.addWidget(tab)

        # Simulate dock widget being set
        dock = MagicMock()
        tab.set_dock_widget(dock)

        # Simulate filter update
        tab._on_filtered_data_updated(pd.DataFrame({"gain_pct": [0.01]}))

        # Should have checked visibility
        app_state.visibility_tracker.is_visible.assert_called()
