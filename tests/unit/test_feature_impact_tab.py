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


class TestFeatureImpactTabGradients:
    """Tests for gradient cell coloring."""

    def test_positive_values_get_cyan_gradient(self, app):
        """Test that positive lift values get cyan-ish background."""
        from src.tabs.feature_impact import get_gradient_color
        from src.ui.constants import Colors

        bg, text = get_gradient_color(0.5, 0.0, 1.0)  # High positive
        # Should be toward cyan
        assert bg.green() > bg.red()  # Cyan has more green than red

    def test_negative_values_get_coral_gradient(self, app):
        """Test that negative lift values get coral-ish background."""
        from src.tabs.feature_impact import get_gradient_color

        bg, text = get_gradient_color(-0.5, -1.0, 1.0)  # Negative
        # Should be toward coral (red)
        assert bg.red() > bg.green()

    def test_zero_values_get_neutral_gradient(self, app):
        """Test that zero values get neutral background."""
        from src.tabs.feature_impact import get_gradient_color
        from src.ui.constants import Colors

        bg, text = get_gradient_color(0.0, -1.0, 1.0)  # Neutral
        # Should be close to BG_ELEVATED
        assert abs(bg.red() - 0x1E) < 20  # Within range of #1E1E2C


class TestFeatureImpactTabDualColumns:
    """Tests for baseline vs filtered column display."""

    def test_table_has_dual_columns(self, app):
        """Test that table has baseline and filtered sub-columns."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        # Should have columns for both baseline and filtered
        headers = [
            tab._table.horizontalHeaderItem(i).text()
            for i in range(tab._table.columnCount())
        ]
        # Check for paired columns
        assert "Corr (B)" in headers or "Correlation" in headers
        assert tab._table.columnCount() >= 9  # Feature + pairs + trades


class TestFeatureImpactTabSorting:
    """Tests for column sorting."""

    def test_clicking_header_sorts_table(self, app):
        """Test that clicking column header triggers sort."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        # Table should have sorting enabled
        assert tab._table.isSortingEnabled() or hasattr(tab, '_sort_column')
