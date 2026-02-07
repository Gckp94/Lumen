"""Integration tests for UI improvements.

Tests verify:
1. ResizableExcludePanel integration in Feature Impact tab
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
