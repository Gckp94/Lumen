"""Tests for Feature Insights tab layout."""

import pandas as pd
import pytest
from PyQt6.QtWidgets import QSplitter

from src.core.app_state import AppState
from src.tabs.feature_insights import FeatureInsightsTab
from src.ui.components.exclude_column_panel import ExcludeColumnPanel


@pytest.fixture
def app_state():
    """Create app state with mock data."""
    state = AppState()
    return state


@pytest.fixture
def insights_tab(qtbot, app_state):
    """Create Feature Insights tab."""
    widget = FeatureInsightsTab(app_state)
    qtbot.addWidget(widget)
    return widget


def test_tab_has_main_splitter(insights_tab):
    """Tab contains a main horizontal splitter."""
    splitter = insights_tab.findChild(QSplitter, "mainSplitter")
    assert splitter is not None


def test_tab_has_exclude_panel(insights_tab):
    """Tab contains the ExcludeColumnPanel."""
    panel = insights_tab.findChild(ExcludeColumnPanel)
    assert panel is not None


def test_splitter_is_resizable(insights_tab):
    """Main splitter allows resizing."""
    splitter = insights_tab.findChild(QSplitter, "mainSplitter")
    assert not splitter.childrenCollapsible()
    # Left panel should have reasonable min width
    left_widget = splitter.widget(0)
    assert left_widget.minimumWidth() >= 150
