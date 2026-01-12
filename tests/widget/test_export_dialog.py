"""Widget tests for ExportDialog."""

from PyQt6.QtCore import Qt

from src.ui.components.export_dialog import (
    ExportCategory,
    ExportDialog,
    ExportFormat,
)


class TestExportDialogBasic:
    """Basic tests for ExportDialog."""

    def test_dialog_creates(self, qtbot) -> None:
        """Dialog can be created."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        assert dialog is not None

    def test_dialog_minimum_size(self, qtbot) -> None:
        """Dialog has minimum size of 400x300."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        assert dialog.minimumWidth() >= 400
        assert dialog.minimumHeight() >= 300

    def test_dialog_title(self, qtbot) -> None:
        """Dialog has correct title."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Export"

    def test_dialog_is_modal(self, qtbot) -> None:
        """Dialog is modal."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        assert dialog.isModal()


class TestExportDialogCategories:
    """Tests for ExportDialog category selection."""

    def test_default_category_is_data(self, qtbot) -> None:
        """Default category is Data."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        assert dialog.selected_category == ExportCategory.DATA

    def test_data_radio_checked_by_default(self, qtbot) -> None:
        """Data radio button is checked by default."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        assert dialog._data_radio.isChecked()

    def test_set_category_charts(self, qtbot) -> None:
        """Can set category to Charts."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        dialog.set_category(ExportCategory.CHARTS)
        assert dialog.selected_category == ExportCategory.CHARTS
        assert dialog._charts_radio.isChecked()

    def test_set_category_data(self, qtbot) -> None:
        """Can set category to Data."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        dialog.set_category(ExportCategory.CHARTS)
        dialog.set_category(ExportCategory.DATA)
        assert dialog.selected_category == ExportCategory.DATA

    def test_report_radio_disabled(self, qtbot) -> None:
        """Report radio button is disabled (deferred)."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        assert not dialog._report_radio.isEnabled()


class TestExportDialogResolution:
    """Tests for ExportDialog resolution dropdown."""

    def test_resolution_hidden_for_data(self, qtbot) -> None:
        """Resolution dropdown hidden for Data category."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        dialog.set_category(ExportCategory.DATA)
        assert not dialog._resolution_container.isVisible()

    def test_resolution_visible_for_charts(self, qtbot) -> None:
        """Resolution dropdown visible for Charts category."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        dialog.show()
        dialog.set_category(ExportCategory.CHARTS)
        assert dialog._resolution_container.isVisible()

    def test_default_resolution_1080p(self, qtbot) -> None:
        """Default resolution is 1080p."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        assert dialog.selected_resolution == (1920, 1080)

    def test_can_select_4k_resolution(self, qtbot) -> None:
        """Can select 4K resolution."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        dialog._resolution_combo.setCurrentIndex(1)
        assert dialog.selected_resolution == (3840, 2160)


class TestExportDialogFormats:
    """Tests for ExportDialog format selection."""

    def test_data_default_format_csv(self, qtbot) -> None:
        """Default data format is CSV."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        assert dialog.selected_format == ExportFormat.CSV

    def test_data_format_parquet(self, qtbot) -> None:
        """Can select Parquet format."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        dialog._parquet_radio.setChecked(True)
        assert dialog.selected_format == ExportFormat.PARQUET

    def test_data_format_metrics_csv(self, qtbot) -> None:
        """Can select Metrics CSV format."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        dialog._metrics_csv_radio.setChecked(True)
        assert dialog.selected_format == ExportFormat.METRICS_CSV

    def test_charts_default_format_png(self, qtbot) -> None:
        """Default charts format is PNG."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        dialog.set_category(ExportCategory.CHARTS)
        assert dialog.selected_format == ExportFormat.PNG

    def test_charts_format_zip(self, qtbot) -> None:
        """Can select ZIP format for charts."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        dialog.set_category(ExportCategory.CHARTS)
        dialog._zip_radio.setChecked(True)
        assert dialog.selected_format == ExportFormat.ZIP


class TestExportDialogProgress:
    """Tests for ExportDialog progress indicator."""

    def test_progress_bar_hidden_initially(self, qtbot) -> None:
        """Progress bar is hidden initially."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        assert not dialog._progress_bar.isVisible()

    def test_show_progress_shows_bar(self, qtbot) -> None:
        """show_progress() shows progress bar."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        dialog.show()
        dialog.show_progress()
        assert dialog._progress_bar.isVisible()

    def test_show_progress_disables_export_button(self, qtbot) -> None:
        """show_progress() disables export button."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        dialog.show_progress()
        assert not dialog._export_btn.isEnabled()

    def test_hide_progress_hides_bar(self, qtbot) -> None:
        """hide_progress() hides progress bar."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        dialog.show_progress()
        dialog.hide_progress()
        assert not dialog._progress_bar.isVisible()

    def test_hide_progress_enables_export_button(self, qtbot) -> None:
        """hide_progress() re-enables export button."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        dialog.show_progress()
        dialog.hide_progress()
        assert dialog._export_btn.isEnabled()

    def test_update_progress_value(self, qtbot) -> None:
        """update_progress() updates progress bar value."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        dialog.show_progress(indeterminate=False)
        dialog.update_progress(50)
        assert dialog._progress_bar.value() == 50


class TestExportDialogButtons:
    """Tests for ExportDialog buttons."""

    def test_cancel_button_exists(self, qtbot) -> None:
        """Cancel button exists."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        assert dialog._cancel_btn is not None
        assert dialog._cancel_btn.text() == "Cancel"

    def test_export_button_exists(self, qtbot) -> None:
        """Export button exists."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        assert dialog._export_btn is not None
        assert dialog._export_btn.text() == "Export"

    def test_cancel_button_rejects_dialog(self, qtbot) -> None:
        """Cancel button rejects dialog."""
        dialog = ExportDialog()
        qtbot.addWidget(dialog)
        dialog.show()

        with qtbot.waitSignal(dialog.rejected, timeout=1000):
            qtbot.mouseClick(dialog._cancel_btn, Qt.MouseButton.LeftButton)
