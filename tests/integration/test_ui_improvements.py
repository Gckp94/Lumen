"""Integration tests for UI improvements.

Tests verify:
1. ResizableExcludePanel integration in Feature Impact tab
2. TwoTierTabBar category navigation
3. All 14 tabs accessible via two-tier navigation
"""

import numpy as np
import pandas as pd
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QSplitter

from src.core.app_state import AppState
from src.core.models import ColumnMapping
from src.tabs.feature_impact import FeatureImpactTab
from src.ui.components.resizable_exclude_panel import ResizableExcludePanel
from src.ui.components.two_tier_tab_bar import TwoTierTabBar
from src.ui.tab_categories import TAB_CATEGORIES, get_tabs_in_category


@pytest.fixture(scope="module")
def app():
    """Provide QApplication instance for Qt tests."""
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def sample_trade_data() -> pd.DataFrame:
    """Create realistic sample trade data."""
    np.random.seed(42)
    n = 100
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=n),
        "time": ["09:30:00"] * n,
        "ticker": np.random.choice(["AAPL", "MSFT", "GOOG"], n),
        "gap_pct": np.random.uniform(-5, 10, n),
        "volume_ratio": np.random.uniform(0.5, 3, n),
        "gain_pct": np.random.normal(0.02, 0.05, n),
        "mae_pct": np.random.uniform(0, 5, n),
        "mfe_pct": np.random.uniform(0, 10, n),
    })


@pytest.fixture
def app_state_with_data(sample_trade_data: pd.DataFrame) -> AppState:
    """AppState configured with sample trade data."""
    app_state = AppState()
    app_state.raw_df = sample_trade_data
    app_state.baseline_df = sample_trade_data.copy()
    app_state.column_mapping = ColumnMapping(
        date="date",
        time="time",
        ticker="ticker",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
    )
    return app_state


class TestExcludePanelIntegration:
    """Integration tests for ResizableExcludePanel in Feature Impact tab."""

    def test_feature_impact_has_resizable_panel(self, app, qtbot, app_state_with_data):
        """Feature Impact tab uses ResizableExcludePanel with QSplitter."""
        # Create the Feature Impact tab
        tab = FeatureImpactTab(app_state_with_data)
        qtbot.addWidget(tab)

        # Verify the tab has an exclude panel of the correct type
        assert hasattr(tab, "_exclude_panel"), "Tab should have _exclude_panel attribute"
        assert isinstance(tab._exclude_panel, ResizableExcludePanel), (
            "Exclude panel should be ResizableExcludePanel"
        )

        # Find the QSplitter in the tab's layout
        splitter = None
        for i in range(tab.layout().count()):
            widget = tab.layout().itemAt(i).widget()
            if isinstance(widget, QSplitter):
                splitter = widget
                break

        assert splitter is not None, "Tab should contain a QSplitter"
        assert splitter.orientation() == Qt.Orientation.Horizontal, (
            "Splitter should be horizontal"
        )

        # Verify the exclude panel is in the splitter
        assert splitter.count() >= 2, "Splitter should have at least 2 widgets"
        assert splitter.widget(0) is tab._exclude_panel, (
            "First widget in splitter should be exclude panel"
        )

        # Verify the panel has the expected width constraints
        assert tab._exclude_panel.minimumWidth() == ResizableExcludePanel.MIN_WIDTH
        assert tab._exclude_panel.maximumWidth() == ResizableExcludePanel.MAX_WIDTH

    def test_exclude_panel_populates_with_columns(self, app, qtbot, app_state_with_data):
        """Exclude panel should populate with analyzable columns when data loads."""
        tab = FeatureImpactTab(app_state_with_data)
        qtbot.addWidget(tab)

        # Trigger data analysis
        app_state_with_data.baseline_calculated.emit(None)
        qtbot.wait(50)

        # Panel should have checkboxes for numeric columns
        # gap_pct, volume_ratio, mae_pct, mfe_pct = 4 features (gain_pct is target)
        assert len(tab._exclude_panel._checkboxes) >= 4, (
            "Exclude panel should have checkboxes for numeric columns"
        )

    def test_splitter_is_resizable(self, app, qtbot, app_state_with_data):
        """Splitter should allow resizing the exclude panel."""
        tab = FeatureImpactTab(app_state_with_data)
        qtbot.addWidget(tab)

        # Find the splitter
        splitter = None
        for i in range(tab.layout().count()):
            widget = tab.layout().itemAt(i).widget()
            if isinstance(widget, QSplitter):
                splitter = widget
                break

        assert splitter is not None

        # Splitter should have a handle width for dragging
        assert splitter.handleWidth() > 0, "Splitter should have draggable handle"

        # Splitter should have 2 widgets (exclude panel and table)
        assert splitter.count() == 2, "Splitter should contain 2 widgets"

        # Stretch factors should prioritize table expansion
        # Index 0 (exclude panel) should have 0 stretch, index 1 (table) should have 1
        assert splitter.widget(0) is tab._exclude_panel
        assert splitter.widget(1) is tab._table


class TestTwoTierNavigation:
    """Integration tests for TwoTierTabBar navigation."""

    def test_category_navigation(self, app, qtbot):
        """Category switching works and updates visible tabs."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)

        # Initially ANALYZE is active
        assert bar.active_category == "ANALYZE"

        # Verify ANALYZE tabs are visible
        for tab_name in get_tabs_in_category("ANALYZE"):
            assert not bar._tab_buttons[tab_name].isHidden(), (
                f"Tab '{tab_name}' should be visible in ANALYZE category"
            )

        # Verify PORTFOLIO tabs are hidden initially
        for tab_name in get_tabs_in_category("PORTFOLIO"):
            assert bar._tab_buttons[tab_name].isHidden(), (
                f"Tab '{tab_name}' should be hidden when PORTFOLIO is not active"
            )

        # Click PORTFOLIO category
        qtbot.mouseClick(bar._category_buttons["PORTFOLIO"], Qt.MouseButton.LeftButton)

        # Verify category changed
        assert bar.active_category == "PORTFOLIO"

        # Verify PORTFOLIO tabs are now visible
        for tab_name in get_tabs_in_category("PORTFOLIO"):
            assert not bar._tab_buttons[tab_name].isHidden(), (
                f"Tab '{tab_name}' should be visible after PORTFOLIO clicked"
            )

        # Verify ANALYZE tabs are now hidden
        for tab_name in get_tabs_in_category("ANALYZE"):
            assert bar._tab_buttons[tab_name].isHidden(), (
                f"Tab '{tab_name}' should be hidden when ANALYZE is not active"
            )

    def test_all_tabs_accessible(self, app, qtbot):
        """All 14 tabs can be reached via two-tier navigation."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)

        # Count expected tabs from TAB_CATEGORIES
        expected_tabs = []
        for category, tabs in TAB_CATEGORIES.items():
            expected_tabs.extend(tabs)

        # Verify we have 14 tabs
        assert len(expected_tabs) == 14, (
            f"Expected 14 tabs, found {len(expected_tabs)}: {expected_tabs}"
        )

        # Track which tabs we successfully activated
        activated_tabs = []

        # Navigate to each tab through its category
        for category in TAB_CATEGORIES.keys():
            # Click the category button
            qtbot.mouseClick(
                bar._category_buttons[category],
                Qt.MouseButton.LeftButton
            )
            assert bar.active_category == category

            # Click each tab in the category
            for tab_name in get_tabs_in_category(category):
                assert tab_name in bar._tab_buttons, (
                    f"Tab button for '{tab_name}' should exist"
                )

                # Tab should be visible in its category
                assert not bar._tab_buttons[tab_name].isHidden(), (
                    f"Tab '{tab_name}' should be visible in category '{category}'"
                )

                # Click the tab
                with qtbot.waitSignal(bar.tab_activated, timeout=1000) as blocker:
                    qtbot.mouseClick(
                        bar._tab_buttons[tab_name],
                        Qt.MouseButton.LeftButton
                    )

                # Verify signal was emitted with correct tab name
                assert blocker.args == [tab_name], (
                    f"tab_activated should emit '{tab_name}', got {blocker.args}"
                )

                # Verify active tab updated
                assert bar.active_tab == tab_name, (
                    f"Active tab should be '{tab_name}', got '{bar.active_tab}'"
                )

                activated_tabs.append(tab_name)

        # Verify all 14 tabs were activated
        assert len(activated_tabs) == 14, (
            f"Should have activated 14 tabs, activated {len(activated_tabs)}: {activated_tabs}"
        )
        assert set(activated_tabs) == set(expected_tabs), (
            f"Activated tabs should match expected tabs"
        )

    def test_category_changed_signal(self, app, qtbot):
        """Category changes emit the category_changed signal."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)

        categories_to_test = ["SIMULATE", "FEATURES", "PORTFOLIO", "CHARTS"]

        for category in categories_to_test:
            with qtbot.waitSignal(bar.category_changed, timeout=1000) as blocker:
                qtbot.mouseClick(
                    bar._category_buttons[category],
                    Qt.MouseButton.LeftButton
                )

            assert blocker.args == [category], (
                f"category_changed should emit '{category}'"
            )

    def test_set_active_tab_switches_category(self, app, qtbot):
        """set_active_tab switches category when needed."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)

        # Start in ANALYZE
        assert bar.active_category == "ANALYZE"

        # Set tab in PORTFOLIO category
        bar.set_active_tab("Portfolio Overview")

        # Verify category switched
        assert bar.active_category == "PORTFOLIO", (
            "Category should switch to PORTFOLIO"
        )
        assert bar.active_tab == "Portfolio Overview", (
            "Active tab should be Portfolio Overview"
        )

        # Verify Portfolio Overview is visible
        assert not bar._tab_buttons["Portfolio Overview"].isHidden()

    def test_keyboard_navigation_ctrl_numbers(self, app, qtbot):
        """Ctrl+1-5 switches categories."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)
        bar.setFocus()

        categories = list(TAB_CATEGORIES.keys())

        # Test Ctrl+2 switches to second category (SIMULATE)
        qtbot.keyClick(bar, Qt.Key.Key_2, Qt.KeyboardModifier.ControlModifier)
        assert bar.active_category == categories[1], (
            f"Ctrl+2 should switch to {categories[1]}"
        )

        # Test Ctrl+5 switches to fifth category (CHARTS)
        qtbot.keyClick(bar, Qt.Key.Key_5, Qt.KeyboardModifier.ControlModifier)
        assert bar.active_category == categories[4], (
            f"Ctrl+5 should switch to {categories[4]}"
        )

    def test_five_categories_exist(self, app, qtbot):
        """Verify exactly 5 categories are configured."""
        bar = TwoTierTabBar()
        qtbot.addWidget(bar)

        assert len(bar._category_buttons) == 5, (
            f"Should have 5 categories, found {len(bar._category_buttons)}"
        )

        expected_categories = ["ANALYZE", "SIMULATE", "FEATURES", "PORTFOLIO", "CHARTS"]
        for category in expected_categories:
            assert category in bar._category_buttons, (
                f"Category '{category}' should exist"
            )
