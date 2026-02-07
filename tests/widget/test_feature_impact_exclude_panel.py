"""Tests for Feature Impact tab exclude panel integration."""

import pytest
from pytestqt.qtbot import QtBot
from PyQt6.QtWidgets import QSplitter

from src.core.app_state import AppState
from src.tabs.feature_impact import FeatureImpactTab
from src.ui.components.resizable_exclude_panel import ResizableExcludePanel


class TestFeatureImpactExcludePanel:
    """Test exclude panel integration."""

    def test_tab_has_splitter(self, qtbot: QtBot) -> None:
        """Tab should use QSplitter for resizable layout."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        qtbot.addWidget(tab)

        splitter = tab.findChild(QSplitter)
        assert splitter is not None

    def test_exclude_panel_is_resizable(self, qtbot: QtBot) -> None:
        """Exclude panel should be in splitter for resize."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        qtbot.addWidget(tab)

        panel = tab.findChild(ResizableExcludePanel)
        assert panel is not None

    def test_splitter_has_two_widgets(self, qtbot: QtBot) -> None:
        """Splitter should have exclude panel and table."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        qtbot.addWidget(tab)

        splitter = tab.findChild(QSplitter)
        assert splitter is not None
        assert splitter.count() == 2

    def test_exclude_panel_is_first_widget(self, qtbot: QtBot) -> None:
        """Exclude panel should be first (left) widget in splitter."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        qtbot.addWidget(tab)

        splitter = tab.findChild(QSplitter)
        panel = tab.findChild(ResizableExcludePanel)
        assert splitter.widget(0) == panel

    def test_table_is_second_widget(self, qtbot: QtBot) -> None:
        """Table should be second (right) widget in splitter."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        qtbot.addWidget(tab)

        splitter = tab.findChild(QSplitter)
        # Table is wrapped in the splitter
        assert splitter.widget(1) == tab._table

    def test_exclude_panel_has_reference(self, qtbot: QtBot) -> None:
        """Tab should store reference to exclude panel."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_exclude_panel")
        assert isinstance(tab._exclude_panel, ResizableExcludePanel)


class TestFeatureImpactExcludePanelSignalConnection:
    """Test signal connections between panel and tab."""

    def test_exclusion_changed_updates_excluded_set(self, qtbot: QtBot) -> None:
        """exclusion_changed signal should update user excluded cols."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        qtbot.addWidget(tab)

        # Simulate exclusion change
        tab._on_exclusion_changed("test_column", True)

        assert "test_column" in tab._user_excluded_cols

    def test_exclusion_changed_removes_from_excluded(self, qtbot: QtBot) -> None:
        """exclusion_changed with False should remove from excluded."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        qtbot.addWidget(tab)

        # Add first
        tab._user_excluded_cols.add("test_column")
        # Then remove
        tab._on_exclusion_changed("test_column", False)

        assert "test_column" not in tab._user_excluded_cols


class TestFeatureImpactSplitterLayout:
    """Test splitter layout configuration."""

    def test_splitter_has_handle_width(self, qtbot: QtBot) -> None:
        """Splitter should have visible handle width."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        qtbot.addWidget(tab)

        splitter = tab.findChild(QSplitter)
        assert splitter.handleWidth() >= 4

    def test_splitter_stretch_factors(self, qtbot: QtBot) -> None:
        """Exclude panel should not stretch, table should."""
        app_state = AppState()
        tab = FeatureImpactTab(app_state)
        qtbot.addWidget(tab)

        splitter = tab.findChild(QSplitter)
        # Index 0 = exclude panel (no stretch)
        # Index 1 = table (stretch)
        assert splitter.widget(0).sizePolicy().horizontalStretch() == 0 or \
               splitter.sizes()[0] <= 400  # Panel has max width constraint
