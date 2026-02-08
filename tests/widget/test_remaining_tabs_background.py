"""Tests for remaining tabs background calculation integration."""

from unittest.mock import MagicMock

import pytest
from pytestqt.qtbot import QtBot


class TestDataBinningBackground:
    """Tests for DataBinning tab."""

    def test_data_binning_has_loading_overlay(self, qtbot: QtBot) -> None:
        """DataBinning tab should have loading overlay."""
        from src.tabs.data_binning import DataBinningTab

        app_state = MagicMock()
        app_state.column_mapping = None
        app_state.baseline_df = None
        app_state.filtered_df = None
        app_state.visibility_tracker = MagicMock()
        app_state.data_loaded = MagicMock()
        app_state.adjustment_params_changed = MagicMock()
        app_state.filtered_data_updated = MagicMock()

        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_loading_overlay")
        assert tab._loading_overlay is not None

    def test_data_binning_has_dock_widget_attribute(self, qtbot: QtBot) -> None:
        """DataBinning tab should have dock widget attribute from mixin."""
        from src.tabs.data_binning import DataBinningTab

        app_state = MagicMock()
        app_state.column_mapping = None
        app_state.baseline_df = None
        app_state.filtered_df = None
        app_state.visibility_tracker = MagicMock()
        app_state.data_loaded = MagicMock()
        app_state.adjustment_params_changed = MagicMock()
        app_state.filtered_data_updated = MagicMock()

        tab = DataBinningTab(app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_dock_widget")
        assert hasattr(tab, "set_dock_widget")


class TestFeatureInsightsBackground:
    """Tests for FeatureInsights tab."""

    def test_feature_insights_has_loading_overlay(self, qtbot: QtBot) -> None:
        """FeatureInsights tab should have loading overlay."""
        from src.tabs.feature_insights import FeatureInsightsTab

        app_state = MagicMock()
        app_state.column_mapping = None
        app_state.baseline_df = None
        app_state.filtered_df = None
        app_state.visibility_tracker = MagicMock()
        app_state.data_loaded = MagicMock()
        app_state.filtered_data_updated = MagicMock()

        tab = FeatureInsightsTab(app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_loading_overlay")
        assert tab._loading_overlay is not None

    def test_feature_insights_has_dock_widget_attribute(self, qtbot: QtBot) -> None:
        """FeatureInsights tab should have dock widget attribute from mixin."""
        from src.tabs.feature_insights import FeatureInsightsTab

        app_state = MagicMock()
        app_state.column_mapping = None
        app_state.baseline_df = None
        app_state.filtered_df = None
        app_state.visibility_tracker = MagicMock()
        app_state.data_loaded = MagicMock()
        app_state.filtered_data_updated = MagicMock()

        tab = FeatureInsightsTab(app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_dock_widget")
        assert hasattr(tab, "set_dock_widget")


class TestFeatureImpactBackground:
    """Tests for FeatureImpact tab."""

    def test_feature_impact_has_loading_overlay(self, qtbot: QtBot) -> None:
        """FeatureImpact tab should have loading overlay."""
        from src.tabs.feature_impact import FeatureImpactTab

        app_state = MagicMock()
        app_state.column_mapping = None
        app_state.baseline_df = None
        app_state.filtered_df = None
        app_state.has_data = False
        app_state.first_trigger_enabled = False
        app_state.visibility_tracker = MagicMock()
        app_state.baseline_calculated = MagicMock()
        app_state.filtered_data_updated = MagicMock()
        app_state.first_trigger_toggled = MagicMock()

        tab = FeatureImpactTab(app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_loading_overlay")
        assert tab._loading_overlay is not None

    def test_feature_impact_has_dock_widget_attribute(self, qtbot: QtBot) -> None:
        """FeatureImpact tab should have dock widget attribute from mixin."""
        from src.tabs.feature_impact import FeatureImpactTab

        app_state = MagicMock()
        app_state.column_mapping = None
        app_state.baseline_df = None
        app_state.filtered_df = None
        app_state.has_data = False
        app_state.first_trigger_enabled = False
        app_state.visibility_tracker = MagicMock()
        app_state.baseline_calculated = MagicMock()
        app_state.filtered_data_updated = MagicMock()
        app_state.first_trigger_toggled = MagicMock()

        tab = FeatureImpactTab(app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_dock_widget")
        assert hasattr(tab, "set_dock_widget")
