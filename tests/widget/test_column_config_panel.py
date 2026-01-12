"""Widget tests for ColumnConfigPanel."""

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QComboBox, QLabel, QPushButton
from pytestqt.qtbot import QtBot

from src.core.models import ColumnMapping, DetectionResult
from src.tabs.data_input import ColumnConfigPanel, ColumnMappingSuccessPanel


class TestColumnConfigPanel:
    """Tests for ColumnConfigPanel widget."""

    def test_panel_has_required_dropdowns(self, qtbot: QtBot) -> None:
        """Panel has 5 required column dropdowns."""
        panel = ColumnConfigPanel()
        qtbot.addWidget(panel)

        ticker_combo = panel.findChild(QComboBox, "ticker_combo")
        date_combo = panel.findChild(QComboBox, "date_combo")
        time_combo = panel.findChild(QComboBox, "time_combo")
        gain_combo = panel.findChild(QComboBox, "gain_pct_combo")
        mae_combo = panel.findChild(QComboBox, "mae_pct_combo")

        assert ticker_combo is not None
        assert date_combo is not None
        assert time_combo is not None
        assert gain_combo is not None
        assert mae_combo is not None

    def test_panel_has_winloss_dropdown(self, qtbot: QtBot) -> None:
        """Panel has Win/Loss dropdown."""
        panel = ColumnConfigPanel()
        qtbot.addWidget(panel)

        winloss_combo = panel.findChild(QComboBox, "win_loss_combo")
        assert winloss_combo is not None

    def test_derive_checkbox_toggles_winloss(self, qtbot: QtBot) -> None:
        """Derive Win/Loss checkbox toggles Win/Loss dropdown visibility."""
        panel = ColumnConfigPanel()
        qtbot.addWidget(panel)
        panel.show()

        checkbox = panel.findChild(QCheckBox, "derive_winloss_checkbox")
        winloss_combo = panel.findChild(QComboBox, "win_loss_combo")

        assert checkbox is not None
        assert winloss_combo is not None

        # Initially not checked, combo not hidden
        assert not checkbox.isChecked()
        assert not winloss_combo.isHidden()

        # Check the box, combo should hide
        checkbox.setChecked(True)
        assert winloss_combo.isHidden()

        # Uncheck, combo should show again
        checkbox.setChecked(False)
        assert not winloss_combo.isHidden()

    def test_breakeven_checkbox_visibility(self, qtbot: QtBot) -> None:
        """Breakeven checkbox only visible when deriving."""
        panel = ColumnConfigPanel()
        qtbot.addWidget(panel)
        panel.show()

        derive_checkbox = panel.findChild(QCheckBox, "derive_winloss_checkbox")
        breakeven_checkbox = panel.findChild(QCheckBox, "breakeven_checkbox")

        assert derive_checkbox is not None
        assert breakeven_checkbox is not None

        # Initially hidden
        assert breakeven_checkbox.isHidden()

        # Show when derive is checked
        derive_checkbox.setChecked(True)
        assert not breakeven_checkbox.isHidden()

        # Hide when derive is unchecked
        derive_checkbox.setChecked(False)
        assert breakeven_checkbox.isHidden()

    def test_continue_button_initially_disabled(self, qtbot: QtBot) -> None:
        """Continue button is disabled until valid."""
        panel = ColumnConfigPanel()
        qtbot.addWidget(panel)

        button = panel.findChild(QPushButton, "continue_button")
        assert button is not None
        assert not button.isEnabled()

    def test_continue_button_enabled_when_valid(
        self, qtbot: QtBot, sample_dataframe: pd.DataFrame
    ) -> None:
        """Continue button enabled when all required fields mapped."""
        panel = ColumnConfigPanel()
        qtbot.addWidget(panel)

        # Set up columns with all required detected
        detection_result = DetectionResult(
            mapping=ColumnMapping(
                ticker="ticker",
                date="date",
                time="time",
                gain_pct="gain_pct",
                mae_pct="mae_pct",
            ),
            statuses={
                "ticker": "detected",
                "date": "detected",
                "time": "detected",
                "gain_pct": "detected",
                "mae_pct": "detected",
                "win_loss": "missing",
            },
            all_required_detected=True,
        )
        panel.set_columns(list(sample_dataframe.columns), sample_dataframe, detection_result)

        button = panel.findChild(QPushButton, "continue_button")
        assert button is not None
        assert button.isEnabled()

    def test_status_indicators_display(self, qtbot: QtBot, sample_dataframe: pd.DataFrame) -> None:
        """Status indicators display correctly per detection result."""
        panel = ColumnConfigPanel()
        qtbot.addWidget(panel)

        detection_result = DetectionResult(
            mapping=None,
            statuses={
                "ticker": "detected",
                "date": "guessed",
                "time": "missing",
                "gain_pct": "detected",
                "mae_pct": "detected",
                "win_loss": "missing",
            },
            all_required_detected=False,
        )
        panel.set_columns(list(sample_dataframe.columns), sample_dataframe, detection_result)

        # Check status labels exist
        assert panel._status_labels["ticker"].text() == "✓"
        assert panel._status_labels["date"].text() == "⚠"
        assert panel._status_labels["time"].text() == "✗"
        assert panel._status_labels["gain_pct"].text() == "✓"
        assert panel._status_labels["mae_pct"].text() == "✓"

    def test_status_indicator_updates_on_manual_selection(
        self, qtbot: QtBot, sample_dataframe: pd.DataFrame
    ) -> None:
        """Status indicator updates to checkmark when user manually selects a column."""
        panel = ColumnConfigPanel()
        qtbot.addWidget(panel)

        # Set up with win_loss as missing (not auto-detected)
        detection_result = DetectionResult(
            mapping=None,
            statuses={
                "ticker": "detected",
                "date": "detected",
                "time": "detected",
                "gain_pct": "detected",
                "mae_pct": "detected",
                "win_loss": "missing",  # Not auto-detected
            },
            all_required_detected=True,
        )
        panel.set_columns(list(sample_dataframe.columns), sample_dataframe, detection_result)

        # Initially win_loss should show ✗ (not auto-detected)
        assert panel._status_labels["win_loss"].text() == "✗"

        # Manually select a column for win_loss
        panel._combos["win_loss"].setCurrentText("ticker")

        # Status should now show ✓ (valid selection)
        assert panel._status_labels["win_loss"].text() == "✓"

        # Clear the selection
        panel._combos["win_loss"].setCurrentText("")

        # Status should return to ✗ (no selection)
        assert panel._status_labels["win_loss"].text() == "✗"

    def test_preview_updates_on_selection(
        self, qtbot: QtBot, sample_dataframe: pd.DataFrame
    ) -> None:
        """Preview updates when dropdown selection changes."""
        panel = ColumnConfigPanel()
        qtbot.addWidget(panel)

        detection_result = DetectionResult(
            mapping=ColumnMapping(
                ticker="ticker",
                date="date",
                time="time",
                gain_pct="gain_pct",
                mae_pct="mae_pct",
            ),
            statuses={
                "ticker": "detected",
                "date": "detected",
                "time": "detected",
                "gain_pct": "detected",
                "mae_pct": "detected",
                "win_loss": "missing",
            },
            all_required_detected=True,
        )
        panel.set_columns(list(sample_dataframe.columns), sample_dataframe, detection_result)

        # Check ticker preview shows values
        ticker_preview = panel._preview_labels["ticker"]
        assert "AAPL" in ticker_preview.text()

        # Change selection and verify preview updates
        panel._combos["ticker"].setCurrentText("volume")
        assert "1000" in ticker_preview.text()

    def test_validation_error_on_duplicate(
        self, qtbot: QtBot, sample_dataframe: pd.DataFrame
    ) -> None:
        """Validation shows error for duplicate column selections."""
        panel = ColumnConfigPanel()
        qtbot.addWidget(panel)
        panel.show()

        detection_result = DetectionResult(
            mapping=ColumnMapping(
                ticker="ticker",
                date="date",
                time="time",
                gain_pct="gain_pct",
                mae_pct="mae_pct",
            ),
            statuses={
                "ticker": "detected",
                "date": "detected",
                "time": "detected",
                "gain_pct": "detected",
                "mae_pct": "detected",
                "win_loss": "missing",
            },
            all_required_detected=True,
        )
        panel.set_columns(list(sample_dataframe.columns), sample_dataframe, detection_result)

        # Set duplicate selection
        panel._combos["date"].setCurrentText("ticker")

        # Verify validation fails
        error_label = panel.findChild(QLabel, "error_label")
        assert error_label is not None
        assert not error_label.isHidden()
        assert "Duplicate" in error_label.text()

        # Verify continue button disabled
        button = panel.findChild(QPushButton, "continue_button")
        assert not button.isEnabled()

    def test_mapping_completed_signal(self, qtbot: QtBot, sample_dataframe: pd.DataFrame) -> None:
        """mapping_completed signal emits ColumnMapping on continue."""
        panel = ColumnConfigPanel()
        qtbot.addWidget(panel)

        detection_result = DetectionResult(
            mapping=ColumnMapping(
                ticker="ticker",
                date="date",
                time="time",
                gain_pct="gain_pct",
                mae_pct="mae_pct",
            ),
            statuses={
                "ticker": "detected",
                "date": "detected",
                "time": "detected",
                "gain_pct": "detected",
                "mae_pct": "detected",
                "win_loss": "missing",
            },
            all_required_detected=True,
        )
        panel.set_columns(list(sample_dataframe.columns), sample_dataframe, detection_result)

        # Connect signal
        received_mapping = []
        panel.mapping_completed.connect(lambda m: received_mapping.append(m))

        # Click continue
        button = panel.findChild(QPushButton, "continue_button")
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton)

        assert len(received_mapping) == 1
        assert received_mapping[0].ticker == "ticker"
        assert received_mapping[0].date == "date"

    def test_get_mapping_returns_valid_mapping(
        self, qtbot: QtBot, sample_dataframe: pd.DataFrame
    ) -> None:
        """get_mapping returns ColumnMapping when valid."""
        panel = ColumnConfigPanel()
        qtbot.addWidget(panel)

        detection_result = DetectionResult(
            mapping=ColumnMapping(
                ticker="ticker",
                date="date",
                time="time",
                gain_pct="gain_pct",
                mae_pct="mae_pct",
            ),
            statuses={
                "ticker": "detected",
                "date": "detected",
                "time": "detected",
                "gain_pct": "detected",
                "mae_pct": "detected",
                "win_loss": "missing",
            },
            all_required_detected=True,
        )
        panel.set_columns(list(sample_dataframe.columns), sample_dataframe, detection_result)

        mapping = panel.get_mapping()
        assert mapping is not None
        assert mapping.ticker == "ticker"

    def test_get_mapping_returns_none_when_invalid(self, qtbot: QtBot) -> None:
        """get_mapping returns None when not valid."""
        panel = ColumnConfigPanel()
        qtbot.addWidget(panel)

        # No columns set, should be invalid
        mapping = panel.get_mapping()
        assert mapping is None


class TestColumnMappingSuccessPanel:
    """Tests for ColumnMappingSuccessPanel widget."""

    def test_panel_has_continue_button(self, qtbot: QtBot) -> None:
        """Panel has continue button."""
        panel = ColumnMappingSuccessPanel()
        qtbot.addWidget(panel)

        button = panel.findChild(QPushButton, "continue_button")
        assert button is not None

    def test_panel_has_edit_button(self, qtbot: QtBot) -> None:
        """Panel has edit mappings button."""
        panel = ColumnMappingSuccessPanel()
        qtbot.addWidget(panel)

        button = panel.findChild(QPushButton, "edit_mappings_button")
        assert button is not None

    def test_set_mapping_updates_summary(
        self, qtbot: QtBot, sample_column_mapping: ColumnMapping
    ) -> None:
        """set_mapping updates the summary display."""
        panel = ColumnMappingSuccessPanel()
        qtbot.addWidget(panel)

        panel.set_mapping(sample_column_mapping)

        assert "ticker" in panel._summary_label.text()
        assert "date" in panel._summary_label.text()

    def test_edit_requested_signal(self, qtbot: QtBot) -> None:
        """edit_requested signal emits when edit button clicked."""
        panel = ColumnMappingSuccessPanel()
        qtbot.addWidget(panel)

        # Connect signal
        edit_requested = []
        panel.edit_requested.connect(lambda: edit_requested.append(True))

        # Click edit
        button = panel.findChild(QPushButton, "edit_mappings_button")
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton)

        assert len(edit_requested) == 1

    def test_continue_requested_signal(self, qtbot: QtBot) -> None:
        """continue_requested signal emits when continue button clicked."""
        panel = ColumnMappingSuccessPanel()
        qtbot.addWidget(panel)

        # Connect signal
        continue_requested = []
        panel.continue_requested.connect(lambda: continue_requested.append(True))

        # Click continue
        button = panel.findChild(QPushButton, "continue_button")
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton)

        assert len(continue_requested) == 1

    def test_get_mapping_returns_set_mapping(
        self, qtbot: QtBot, sample_column_mapping: ColumnMapping
    ) -> None:
        """get_mapping returns the mapping that was set."""
        panel = ColumnMappingSuccessPanel()
        qtbot.addWidget(panel)

        panel.set_mapping(sample_column_mapping)

        mapping = panel.get_mapping()
        assert mapping is not None
        assert mapping.ticker == "ticker"
