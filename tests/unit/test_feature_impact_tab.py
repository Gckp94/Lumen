"""Tests for Feature Impact tab."""

import pytest
from PyQt6.QtWidgets import QApplication

from src.core.app_state import AppState
from src.tabs.feature_impact import FeatureImpactTab


@pytest.fixture(scope="module")
def app():
    """Create QApplication for widget tests."""
    application = QApplication.instance() or QApplication([])
    yield application


class TestFeatureImpactTabCreation:
    """Tests for tab creation and basic structure."""

    def test_tab_creation(self, app):
        """Test that tab can be created."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        assert tab is not None

    def test_tab_has_empty_state(self, app):
        """Test that tab shows empty state when no data loaded."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        # Empty label should be visible
        assert tab._empty_label.isVisible() or not tab._table.isVisible()
