# tests/unit/test_strategy_table.py
import pytest
from PyQt6.QtWidgets import QAbstractItemView, QApplication, QCheckBox
from PyQt6.QtCore import Qt
from src.ui.components.strategy_table import StrategyTableWidget
from src.core.portfolio_models import (
    StrategyConfig,
    PortfolioColumnMapping,
    PositionSizeType,
)


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance() or QApplication([])
    yield app


class TestStrategyTableWidget:
    def test_table_creates_successfully(self, app, qtbot):
        table = StrategyTableWidget()
        qtbot.addWidget(table)
        assert table is not None

    def test_add_strategy_adds_row(self, app, qtbot):
        table = StrategyTableWidget()
        qtbot.addWidget(table)

        config = StrategyConfig(
            name="Test Strategy",
            file_path="/path/test.csv",
            column_mapping=PortfolioColumnMapping("date", "gain_pct", "wl"),
        )
        table.add_strategy(config)

        assert table.rowCount() == 1

    def test_get_strategies_returns_all_configs(self, app, qtbot):
        table = StrategyTableWidget()
        qtbot.addWidget(table)

        config1 = StrategyConfig(
            name="Strategy A",
            file_path="a.csv",
            column_mapping=PortfolioColumnMapping("date", "gain", "wl"),
        )
        config2 = StrategyConfig(
            name="Strategy B",
            file_path="b.csv",
            column_mapping=PortfolioColumnMapping("date", "gain", "wl"),
        )
        table.add_strategy(config1)
        table.add_strategy(config2)

        strategies = table.get_strategies()
        assert len(strategies) == 2
        assert strategies[0].name == "Strategy A"
        assert strategies[1].name == "Strategy B"

    def test_baseline_checkbox_updates_config(self, app, qtbot):
        table = StrategyTableWidget()
        qtbot.addWidget(table)

        config = StrategyConfig(
            name="Test",
            file_path="test.csv",
            column_mapping=PortfolioColumnMapping("date", "gain", "wl"),
        )
        table.add_strategy(config)

        # Simulate checking baseline checkbox
        table.set_baseline(0, True)

        strategies = table.get_strategies()
        assert strategies[0].is_baseline is True

    def test_candidate_checkbox_updates_config(self, app, qtbot):
        table = StrategyTableWidget()
        qtbot.addWidget(table)

        config = StrategyConfig(
            name="Test",
            file_path="test.csv",
            column_mapping=PortfolioColumnMapping("date", "gain", "wl"),
        )
        table.add_strategy(config)

        table.set_candidate(0, True)

        strategies = table.get_strategies()
        assert strategies[0].is_candidate is True

    def test_strategy_changed_signal_emitted_on_baseline_change(self, app, qtbot):
        table = StrategyTableWidget()
        qtbot.addWidget(table)

        config = StrategyConfig(
            name="Test",
            file_path="test.csv",
            column_mapping=PortfolioColumnMapping("date", "gain", "wl"),
        )
        table.add_strategy(config)

        with qtbot.waitSignal(table.strategy_changed, timeout=1000):
            table.set_baseline(0, True)

    def test_remove_strategy_removes_row(self, app, qtbot):
        table = StrategyTableWidget()
        qtbot.addWidget(table)

        config = StrategyConfig(
            name="Test",
            file_path="test.csv",
            column_mapping=PortfolioColumnMapping("date", "gain", "wl"),
        )
        table.add_strategy(config)
        assert table.rowCount() == 1

        table.remove_strategy(0)
        assert table.rowCount() == 0
        assert len(table.get_strategies()) == 0

    def test_clear_all_removes_all_strategies(self, app, qtbot):
        table = StrategyTableWidget()
        qtbot.addWidget(table)

        for i in range(3):
            config = StrategyConfig(
                name=f"Strategy {i}",
                file_path=f"s{i}.csv",
                column_mapping=PortfolioColumnMapping("date", "gain", "wl"),
            )
            table.add_strategy(config)

        assert table.rowCount() == 3

        table.clear_all()
        assert table.rowCount() == 0
        assert len(table.get_strategies()) == 0

    def test_size_type_defaults_to_custom_pct(self, app, qtbot):
        table = StrategyTableWidget()
        qtbot.addWidget(table)

        config = StrategyConfig(
            name="Test",
            file_path="test.csv",
            column_mapping=PortfolioColumnMapping("date", "gain", "wl"),
        )
        table.add_strategy(config)

        strategies = table.get_strategies()
        assert strategies[0].size_type == PositionSizeType.CUSTOM_PCT

    def test_numeric_field_defaults(self, app, qtbot):
        table = StrategyTableWidget()
        qtbot.addWidget(table)

        config = StrategyConfig(
            name="Test",
            file_path="test.csv",
            column_mapping=PortfolioColumnMapping("date", "gain", "wl"),
            stop_pct=3.5,
            efficiency=0.8,
            size_value=15.0,
        )
        table.add_strategy(config)

        strategies = table.get_strategies()
        assert strategies[0].stop_pct == 3.5
        assert strategies[0].efficiency == 0.8
        assert strategies[0].size_value == 15.0

    def test_row_menu_has_load_data_requested_signal(self, app, qtbot):
        """Verify load_data_requested signal exists on strategy table."""
        table = StrategyTableWidget()
        qtbot.addWidget(table)

        assert hasattr(table, 'load_data_requested')

    def test_efficiency_spinbox_displays_percentage(self, app, qtbot):
        """Efficiency spinbox should display values as percentage with % suffix."""
        table = StrategyTableWidget()
        qtbot.addWidget(table)

        config = StrategyConfig(
            name="Test",
            file_path="test.csv",
            column_mapping=PortfolioColumnMapping("date", "gain_pct", "wl"),
            efficiency=100.0,  # 100% efficiency stored as percentage points
        )
        table.add_strategy(config)

        # Get the efficiency spinbox
        eff_spin = table.cellWidget(0, table.COL_EFFICIENCY)

        # Should display 100 (percentage points)
        assert eff_spin.value() == 100.0
        # Should have % suffix
        assert eff_spin.suffix() == "%"
        # Range should be 0-200
        assert eff_spin.minimum() == 0.0
        assert eff_spin.maximum() == 200.0

    def test_efficiency_spinbox_change_updates_strategy(self, app, qtbot):
        """Changing efficiency percentage should update strategy."""
        table = StrategyTableWidget()
        qtbot.addWidget(table)

        config = StrategyConfig(
            name="Test",
            file_path="test.csv",
            column_mapping=PortfolioColumnMapping("date", "gain_pct", "wl"),
            efficiency=100.0,  # 100% stored as percentage points
        )
        table.add_strategy(config)

        # Get the efficiency spinbox and change value to 50%
        eff_spin = table.cellWidget(0, table.COL_EFFICIENCY)
        eff_spin.setValue(50.0)  # 50%

        # Strategy should store 50.0 (percentage points)
        strategies = table.get_strategies()
        assert strategies[0].efficiency == 50.0


class TestStrategyTableMultipleEntry:
    """Tests for Multiple Entry checkbox column."""

    def test_multi_column_exists(self, app, qtbot) -> None:
        """Table has Multi column after CND."""
        table = StrategyTableWidget()
        qtbot.addWidget(table)
        headers = [
            table.horizontalHeaderItem(i).text()
            for i in range(table.columnCount())
        ]
        assert "Multi" in headers
        # Should be after CND (index 3), so at index 4
        assert headers.index("Multi") == 4

    def test_multi_checkbox_defaults_checked(self, app, qtbot) -> None:
        """Multi checkbox defaults to checked (allow multiple entry)."""
        table = StrategyTableWidget()
        qtbot.addWidget(table)
        config = StrategyConfig(
            name="Test",
            file_path="/path/to/file.xlsx",
            column_mapping=PortfolioColumnMapping(
                ticker_col="ticker",
                date_col="date",
                gain_pct_col="gain_pct",
            ),
        )
        table.add_strategy(config)
        # Get checkbox from Multi column (index 4)
        checkbox = table.cellWidget(0, 4).findChild(QCheckBox)
        assert checkbox.isChecked() is True

    def test_multi_checkbox_updates_config(self, app, qtbot) -> None:
        """Unchecking Multi updates strategy config."""
        table = StrategyTableWidget()
        qtbot.addWidget(table)
        config = StrategyConfig(
            name="Test",
            file_path="/path/to/file.xlsx",
            column_mapping=PortfolioColumnMapping(
                ticker_col="ticker",
                date_col="date",
                gain_pct_col="gain_pct",
            ),
        )
        table.add_strategy(config)
        checkbox = table.cellWidget(0, 4).findChild(QCheckBox)
        checkbox.setChecked(False)
        strategies = table.get_strategies()
        assert strategies[0].allow_multiple_entry is False


class TestStrategyTableDragDrop:
    """Tests for drag-drop row reordering."""

    def test_drag_drop_enabled(self, app, qtbot) -> None:
        """Table supports internal drag-drop."""
        table = StrategyTableWidget()
        qtbot.addWidget(table)
        assert table.dragDropMode() == QAbstractItemView.DragDropMode.InternalMove
        assert table.dragEnabled() is True

    def test_reorder_strategies_updates_list(self, app, qtbot) -> None:
        """Reordering rows updates internal strategies list."""
        table = StrategyTableWidget()
        qtbot.addWidget(table)
        config1 = StrategyConfig(
            name="Alpha",
            file_path="/path/to/alpha.xlsx",
            column_mapping=PortfolioColumnMapping(
                ticker_col="ticker", date_col="date", gain_pct_col="gain_pct"
            ),
        )
        config2 = StrategyConfig(
            name="Beta",
            file_path="/path/to/beta.xlsx",
            column_mapping=PortfolioColumnMapping(
                ticker_col="ticker", date_col="date", gain_pct_col="gain_pct"
            ),
        )
        table.add_strategy(config1)
        table.add_strategy(config2)
        # Simulate reorder: move Beta to top
        table.move_strategy(1, 0)
        strategies = table.get_strategies()
        assert strategies[0].name == "Beta"
        assert strategies[1].name == "Alpha"

    def test_reorder_emits_strategy_changed(self, app, qtbot) -> None:
        """Reordering emits strategy_changed signal."""
        table = StrategyTableWidget()
        qtbot.addWidget(table)
        config1 = StrategyConfig(
            name="Alpha",
            file_path="/path/to/alpha.xlsx",
            column_mapping=PortfolioColumnMapping(
                ticker_col="ticker", date_col="date", gain_pct_col="gain_pct"
            ),
        )
        config2 = StrategyConfig(
            name="Beta",
            file_path="/path/to/beta.xlsx",
            column_mapping=PortfolioColumnMapping(
                ticker_col="ticker", date_col="date", gain_pct_col="gain_pct"
            ),
        )
        table.add_strategy(config1)
        table.add_strategy(config2)
        with qtbot.waitSignal(table.strategy_changed, timeout=1000):
            table.move_strategy(1, 0)
