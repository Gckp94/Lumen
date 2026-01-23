# tests/unit/test_strategy_table.py
import pytest
from PyQt6.QtWidgets import QApplication
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
            efficiency=1.0,  # 100% efficiency stored as decimal
        )
        table.add_strategy(config)

        # Get the efficiency spinbox
        eff_spin = table.cellWidget(0, table.COL_EFFICIENCY)

        # Should display 100 (percentage) not 1.0 (decimal)
        assert eff_spin.value() == 100.0
        # Should have % suffix
        assert eff_spin.suffix() == "%"
        # Range should be 0-200
        assert eff_spin.minimum() == 0.0
        assert eff_spin.maximum() == 200.0

    def test_efficiency_spinbox_change_updates_strategy_as_decimal(self, app, qtbot):
        """Changing efficiency percentage should store as decimal multiplier."""
        table = StrategyTableWidget()
        qtbot.addWidget(table)

        config = StrategyConfig(
            name="Test",
            file_path="test.csv",
            column_mapping=PortfolioColumnMapping("date", "gain_pct", "wl"),
            efficiency=1.0,
        )
        table.add_strategy(config)

        # Get the efficiency spinbox and change value to 50%
        eff_spin = table.cellWidget(0, table.COL_EFFICIENCY)
        eff_spin.setValue(50.0)  # 50%

        # Strategy should store 0.5 (decimal multiplier)
        strategies = table.get_strategies()
        assert strategies[0].efficiency == 0.5
