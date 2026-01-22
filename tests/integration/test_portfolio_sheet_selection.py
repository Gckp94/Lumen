# tests/integration/test_portfolio_sheet_selection.py
import pytest
import pandas as pd
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from src.ui.dialogs.import_strategy_dialog import ImportStrategyDialog


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance() or QApplication([])
    yield app


class TestPortfolioSheetSelectionIntegration:
    def test_full_excel_import_flow(self, app, qtbot, tmp_path):
        """Test complete flow: load Excel -> select sheet -> get correct data."""
        # Create test Excel with distinct data per sheet
        excel_path = tmp_path / "strategies.xlsx"
        sheet1_df = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-02"],
            "gain_pct": [1.5, -0.5],
            "win_loss": ["W", "L"],
        })
        sheet2_df = pd.DataFrame({
            "trade_date": ["2024-02-01"],
            "return": [3.0],
            "outcome": ["W"],
        })

        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            sheet1_df.to_excel(writer, sheet_name="Strategy1", index=False)
            sheet2_df.to_excel(writer, sheet_name="Strategy2", index=False)

        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)

        # Load file
        dialog._load_file(str(excel_path))

        # Verify sheet selector populated
        assert dialog._sheet_selector.count() == 2

        # Select second sheet
        dialog._sheet_selector.setCurrentText("Strategy2")

        # Verify data loaded from second sheet
        df = dialog.get_dataframe()
        assert "trade_date" in df.columns
        assert "return" in df.columns
        assert len(df) == 1

        # Verify selected sheet returned
        assert dialog.get_selected_sheet() == "Strategy2"
