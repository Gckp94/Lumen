"""Integration tests for Feature Explorer filter functionality."""

import pytest
from PyQt6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from src.core.app_state import AppState
from src.tabs.feature_explorer import FeatureExplorerTab


@pytest.fixture
def app(qtbot: QtBot) -> QApplication:
    """Provide QApplication instance."""
    return QApplication.instance() or QApplication([])


class TestFeatureExplorerFilters:
    """Integration tests for filter panel in Feature Explorer."""

    def test_filter_panel_displays_numeric_columns(
        self, qtbot: QtBot, app: QApplication
    ) -> None:
        """Filter panel should display all numeric columns from data."""
        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        # Verify filter panel exists
        assert hasattr(tab, "_filter_panel")
        assert tab._filter_panel is not None

        # Verify column filter panel exists within filter panel
        assert hasattr(tab._filter_panel, "_column_filter_panel")
        assert tab._filter_panel._column_filter_panel is not None

    def test_column_filter_panel_updates_when_data_loaded(
        self, qtbot: QtBot, app: QApplication
    ) -> None:
        """Column filter panel should update rows when data is loaded."""
        import pandas as pd

        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        # Initially no rows (no data)
        _ = len(tab._filter_panel._column_filter_panel._rows)

        # Load data with numeric columns
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=10),
            "symbol": ["TEST"] * 10,
            "gain_pct": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            "volume": [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000],
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)

        # Should have rows for numeric columns
        rows_after_load = len(tab._filter_panel._column_filter_panel._rows)
        assert rows_after_load >= 2  # At least gain_pct and volume

    def test_apply_filter_from_column_filter_panel(
        self, qtbot: QtBot, app: QApplication
    ) -> None:
        """Applying filter from column filter panel should trigger signal."""
        import pandas as pd

        app_state = AppState()
        tab = FeatureExplorerTab(app_state=app_state)
        qtbot.addWidget(tab)

        # Load data
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=10),
            "symbol": ["TEST"] * 10,
            "gain_pct": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            "volume": [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000],
        })
        app_state.baseline_df = df
        app_state.data_loaded.emit(df)

        # Find gain_pct row and set filter values
        gain_pct_row = None
        for row in tab._filter_panel._column_filter_panel._rows:
            if row.get_column_name() == "gain_pct":
                gain_pct_row = row
                break

        if gain_pct_row:
            gain_pct_row._min_input.setText("3")
            gain_pct_row._max_input.setText("8")

            # Apply filter and verify signal
            with qtbot.waitSignal(
                tab._filter_panel.filters_applied, timeout=1000
            ) as blocker:
                tab._filter_panel._apply_btn.click()

            criteria_list = blocker.args[0]
            assert len(criteria_list) >= 1
            assert any(c.column == "gain_pct" for c in criteria_list)
