# tests/unit/test_import_strategy_dialog.py
"""Unit tests for ImportStrategyDialog."""
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
        })
        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        dialog.set_preview_data(df)

        dialog._date_combo.setCurrentText("trade_date")
        dialog._gain_combo.setCurrentText("return_pct")

        mapping = dialog.get_column_mapping()
        assert mapping.date_col == "trade_date"
        assert mapping.gain_pct_col == "return_pct"

    def test_import_button_disabled_until_all_mapped(self, app, qtbot):
        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)

        assert not dialog._import_btn.isEnabled()

        df = pd.DataFrame({
            "date": ["2024-01-01"],
            "gain": [5.0],
        })
        dialog.set_preview_data(df)
        dialog._date_combo.setCurrentText("date")
        dialog._gain_combo.setCurrentText("gain")

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


class TestImportStrategyDialogSheetSelection:
    def test_sheet_selector_hidden_by_default(self, app, qtbot):
        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        assert not dialog._sheet_selector.isVisible()
        assert not dialog._sheet_label.isVisible()

    def test_get_selected_sheet_returns_none_when_hidden(self, app, qtbot):
        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        assert dialog.get_selected_sheet() is None


class TestImportStrategyDialogMaeColumn:
    def test_dialog_has_mae_combo(self, app, qtbot):
        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        assert hasattr(dialog, "_mae_combo")

    def test_mae_combo_has_optional_placeholder(self, app, qtbot):
        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        df = pd.DataFrame({
            "date": ["2024-01-01"],
            "gain": [5.0],
            "wl": ["W"],
            "mae": [2.0],
        })
        dialog.set_preview_data(df)

        items = [dialog._mae_combo.itemText(i) for i in range(dialog._mae_combo.count())]
        assert dialog.PLACEHOLDER_OPTIONAL in items
        assert "mae" in items

    def test_get_column_mapping_returns_mae_when_selected(self, app, qtbot):
        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        df = pd.DataFrame({
            "date": ["2024-01-01"],
            "gain": [5.0],
            "mae": [2.0],
        })
        dialog.set_preview_data(df)

        dialog._date_combo.setCurrentText("date")
        dialog._gain_combo.setCurrentText("gain")
        dialog._mae_combo.setCurrentText("mae")

        mapping = dialog.get_column_mapping()
        assert mapping.mae_pct_col == "mae"

    def test_get_column_mapping_returns_none_when_optional_placeholder(self, app, qtbot):
        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        df = pd.DataFrame({
            "date": ["2024-01-01"],
            "gain": [5.0],
            "mae": [2.0],
        })
        dialog.set_preview_data(df)

        dialog._date_combo.setCurrentText("date")
        dialog._gain_combo.setCurrentText("gain")
        dialog._mae_combo.setCurrentText(dialog.PLACEHOLDER_OPTIONAL)

        mapping = dialog.get_column_mapping()
        assert mapping.mae_pct_col is None


class TestImportStrategyDialogExcelSheetSelection:
    def test_shows_sheet_selector_for_excel_file(self, app, qtbot, tmp_path):
        # Create a test Excel file with multiple sheets
        excel_path = tmp_path / "test.xlsx"
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            pd.DataFrame({"col1": [1]}).to_excel(writer, sheet_name="Sheet1", index=False)
            pd.DataFrame({"col2": [2]}).to_excel(writer, sheet_name="Sheet2", index=False)

        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)

        # Simulate loading the Excel file
        dialog._load_file(str(excel_path))

        # Use isVisibleTo to check visibility relative to parent (works without showing dialog)
        assert not dialog._sheet_selector.isHidden()
        assert not dialog._sheet_label.isHidden()
        assert dialog._sheet_selector.count() == 2
        assert dialog._sheet_selector.itemText(0) == "Sheet1"
        assert dialog._sheet_selector.itemText(1) == "Sheet2"

    def test_hides_sheet_selector_for_csv_file(self, app, qtbot, tmp_path):
        csv_path = tmp_path / "test.csv"
        pd.DataFrame({"col1": [1, 2]}).to_csv(csv_path, index=False)

        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        dialog._load_file(str(csv_path))

        assert dialog._sheet_selector.isHidden()
        assert dialog._sheet_label.isHidden()

    def test_loads_selected_sheet_data(self, app, qtbot, tmp_path):
        excel_path = tmp_path / "test.xlsx"
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            pd.DataFrame({"sheet1_col": [1]}).to_excel(writer, sheet_name="First", index=False)
            pd.DataFrame({"sheet2_col": [2]}).to_excel(writer, sheet_name="Second", index=False)

        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        dialog._load_file(str(excel_path))

        # Select second sheet
        dialog._sheet_selector.setCurrentText("Second")

        # Verify preview shows second sheet data
        assert "sheet2_col" in [dialog._preview_table.horizontalHeaderItem(i).text()
                                for i in range(dialog._preview_table.columnCount())]


class TestImportStrategyDialogErrors:
    """Test error handling in import dialog."""

    def test_shows_error_on_invalid_file(self, app, qtbot, tmp_path, monkeypatch):
        """Should show error message when file cannot be loaded."""
        from PyQt6.QtWidgets import QMessageBox

        # Create invalid CSV
        invalid_file = tmp_path / "invalid.csv"
        invalid_file.write_text("not,valid\ncsv,file\n\"unclosed quote")

        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)

        # Mock QMessageBox to capture the error
        error_shown = []

        def mock_critical(parent, title, message):
            error_shown.append(message)

        monkeypatch.setattr(QMessageBox, "critical", mock_critical)

        dialog._load_file(str(invalid_file))

        # Should show error and NOT have data loaded
        assert len(error_shown) == 1
        assert "Failed to load file:" in error_shown[0]
        assert dialog.get_dataframe() is None

    def test_loads_valid_csv_successfully(self, app, qtbot, tmp_path):
        """Should load valid CSV without errors."""
        valid_file = tmp_path / "valid.csv"
        valid_file.write_text("date,gain_pct\n2024-01-01,1.5\n2024-01-02,-0.5\n")

        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        dialog._load_file(str(valid_file))

        df = dialog.get_dataframe()
        assert df is not None
        assert len(df) == 2
        assert list(df.columns) == ["date", "gain_pct"]

    def test_get_file_path_returns_loaded_path(self, app, qtbot, tmp_path):
        """Should return the loaded file path."""
        valid_file = tmp_path / "valid.csv"
        valid_file.write_text("date,gain_pct\n2024-01-01,1.5\n")

        dialog = ImportStrategyDialog()
        qtbot.addWidget(dialog)
        dialog._load_file(str(valid_file))

        assert dialog.get_file_path() == str(valid_file)
