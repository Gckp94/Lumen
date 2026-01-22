# tests/unit/test_import_strategy_dialog.py
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from PyQt6.QtWidgets import QApplication
from src.ui.dialogs.import_strategy_dialog import ImportStrategyDialog
from src.core.portfolio_models import PortfolioColumnMapping


@pytest.fixture(scope="module")
def app():
    """Create QApplication for Qt tests."""
    app = QApplication.instance() or QApplication([])
    yield app


class TestImportStrategyDialog:
    def test_dialog_creates_successfully(self, app, qtbot):
        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        assert dialog is not None

    def test_dialog_populates_columns_from_dataframe(self, app, qtbot):
        df = pd.DataFrame({
            "trade_date": ["2024-01-01"],
            "return_pct": [5.0],
            "outcome": ["W"],
        })
        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        dialog.set_preview_data(df)

        date_items = [dialog._date_combo.itemText(i) for i in range(dialog._date_combo.count())]
        assert "trade_date" in date_items
        assert "return_pct" in date_items
        assert "outcome" in date_items

    def test_get_column_mapping_returns_selected_values(self, app, qtbot):
        df = pd.DataFrame({
            "trade_date": ["2024-01-01"],
            "return_pct": [5.0],
            "outcome": ["W"],
        })
        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        dialog.set_preview_data(df)

        dialog._date_combo.setCurrentText("trade_date")
        dialog._gain_combo.setCurrentText("return_pct")
        dialog._wl_combo.setCurrentText("outcome")

        mapping = dialog.get_column_mapping()
        assert mapping.date_col == "trade_date"
        assert mapping.gain_pct_col == "return_pct"
        assert mapping.win_loss_col == "outcome"

    def test_import_button_disabled_until_all_mapped(self, app, qtbot):
        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)

        assert not dialog._import_btn.isEnabled()

        df = pd.DataFrame({
            "date": ["2024-01-01"],
            "gain": [5.0],
            "wl": ["W"],
        })
        dialog.set_preview_data(df)
        dialog._date_combo.setCurrentText("date")
        dialog._gain_combo.setCurrentText("gain")
        dialog._wl_combo.setCurrentText("wl")

        assert dialog._import_btn.isEnabled()

    def test_get_strategy_name_returns_entered_name(self, app, qtbot):
        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        dialog._name_edit.setText("My Strategy")
        assert dialog.get_strategy_name() == "My Strategy"

    def test_get_strategy_name_returns_default_when_empty(self, app, qtbot):
        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        assert dialog.get_strategy_name() == "Unnamed Strategy"

    def test_get_file_path_returns_none_initially(self, app, qtbot):
        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        assert dialog.get_file_path() is None

    def test_get_dataframe_returns_preview_data(self, app, qtbot):
        df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        dialog.set_preview_data(df)
        result = dialog.get_dataframe()
        assert result is not None
        assert list(result.columns) == ["col1", "col2"]
        assert len(result) == 2
