"""Tests for stale tab recalculation on visibility change."""

from unittest.mock import MagicMock

import pandas as pd
import pytest
from pytestqt.qtbot import QtBot


class TestStaleTabRecalculation:
    """Tests for recalculating stale tabs when they become visible."""

    def test_tab_recalculates_when_becoming_visible(self, qtbot: QtBot) -> None:
        """Stale tab should recalculate when it becomes visible."""
        from src.core.app_state import AppState

        app_state = AppState()

        # Mark a tab as stale
        app_state.visibility_tracker.mark_stale("Statistics")

        # Emit visibility signal
        recalc_triggered = []
        app_state.tab_became_visible.connect(
            lambda name: recalc_triggered.append(name)
        )

        app_state.notify_tab_visible("Statistics")

        assert "Statistics" in recalc_triggered
        assert not app_state.visibility_tracker.is_stale("Statistics")

    def test_non_stale_tab_does_not_trigger_recalc(self, qtbot: QtBot) -> None:
        """Non-stale tab should not trigger recalculation."""
        from src.core.app_state import AppState

        app_state = AppState()

        # Do NOT mark the tab as stale

        recalc_triggered = []
        app_state.tab_became_visible.connect(
            lambda name: recalc_triggered.append(name)
        )

        app_state.notify_tab_visible("Statistics")

        assert "Statistics" not in recalc_triggered

    def test_multiple_stale_tabs_recalculate_independently(self, qtbot: QtBot) -> None:
        """Each stale tab should recalculate independently when visible."""
        from src.core.app_state import AppState

        app_state = AppState()

        # Mark multiple tabs as stale
        app_state.visibility_tracker.mark_stale("Statistics")
        app_state.visibility_tracker.mark_stale("Breakdown")

        recalc_triggered = []
        app_state.tab_became_visible.connect(
            lambda name: recalc_triggered.append(name)
        )

        # Only make Statistics visible
        app_state.notify_tab_visible("Statistics")

        assert "Statistics" in recalc_triggered
        assert "Breakdown" not in recalc_triggered
        assert not app_state.visibility_tracker.is_stale("Statistics")
        assert app_state.visibility_tracker.is_stale("Breakdown")

        # Now make Breakdown visible
        app_state.notify_tab_visible("Breakdown")

        assert "Breakdown" in recalc_triggered
        assert not app_state.visibility_tracker.is_stale("Breakdown")
