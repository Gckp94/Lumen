"""Strategy table widget for managing strategy configurations."""

from dataclasses import replace
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from src.core.portfolio_models import PositionSizeType, StrategyConfig
from src.ui.components.no_scroll_widgets import NoScrollComboBox, NoScrollDoubleSpinBox


class StrategyTableWidget(QTableWidget):
    """Table widget for displaying and editing strategy configurations.

    Provides inline editing for numeric fields and checkboxes for baseline/candidate
    selection. Emits strategy_changed signal when any configuration changes.
    """

    # Column definitions: (header, width)
    COLUMNS = [
        ("Name", 120),
        ("File", 30),
        ("BL", 53),
        ("CND", 60),
        ("Stop%", 170),
        ("Efficiency", 180),
        ("Size Type", 200),
        ("Size Value", 150),
        ("Max Compound", 173),
        ("Menu", 80),
    ]

    # Column indices
    COL_NAME = 0
    COL_FILE = 1
    COL_BL = 2
    COL_CND = 3
    COL_STOP = 4
    COL_EFFICIENCY = 5
    COL_SIZE_TYPE = 6
    COL_SIZE_VALUE = 7
    COL_MAX_COMPOUND = 8
    COL_MENU = 9

    # Size type display names mapping
    SIZE_TYPE_DISPLAY = {
        PositionSizeType.FRAC_KELLY: "Frac Kelly",
        PositionSizeType.CUSTOM_PCT: "Custom %",
        PositionSizeType.FLAT_DOLLAR: "Flat $",
    }

    SIZE_TYPE_FROM_DISPLAY = {v: k for k, v in SIZE_TYPE_DISPLAY.items()}

    strategy_changed = pyqtSignal()
    load_data_requested = pyqtSignal(str)  # Emits strategy name

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the strategy table.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._strategies: list[StrategyConfig] = []
        self._setup_table()

    def _setup_table(self) -> None:
        """Configure table appearance and behavior."""
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels([col[0] for col in self.COLUMNS])

        # Set column widths
        header = self.horizontalHeader()
        if header:
            # File column stretches to fill remaining space
            header.setSectionResizeMode(self.COL_FILE, QHeaderView.ResizeMode.Stretch)

        for i, (_, width) in enumerate(self.COLUMNS):
            self.setColumnWidth(i, width)

        # Table settings
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)

    def add_strategy(self, config: StrategyConfig) -> None:
        """Add a strategy to the table.

        Args:
            config: Strategy configuration to add.
        """
        self._strategies.append(config)
        row = self.rowCount()
        self.insertRow(row)
        self._populate_row(row, config)

    def _populate_row(self, row: int, config: StrategyConfig) -> None:
        """Populate a table row with strategy data.

        Args:
            row: Row index.
            config: Strategy configuration.
        """
        # Name (editable text)
        name_item = QTableWidgetItem(config.name)
        name_item.setFlags(name_item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.setItem(row, self.COL_NAME, name_item)

        # File (read-only)
        file_item = QTableWidgetItem(config.file_path)
        file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        file_item.setToolTip(config.file_path)
        self.setItem(row, self.COL_FILE, file_item)

        # Baseline checkbox
        bl_container, bl_checkbox = self._create_centered_checkbox(config.is_baseline)
        bl_checkbox.stateChanged.connect(
            lambda state, r=row: self._on_baseline_changed(r, state)
        )
        self.setCellWidget(row, self.COL_BL, bl_container)

        # Candidate checkbox
        cnd_container, cnd_checkbox = self._create_centered_checkbox(config.is_candidate)
        cnd_checkbox.stateChanged.connect(
            lambda state, r=row: self._on_candidate_changed(r, state)
        )
        self.setCellWidget(row, self.COL_CND, cnd_container)

        # Stop% spinbox
        stop_spin = NoScrollDoubleSpinBox()
        stop_spin.setRange(0.0, 100.0)
        stop_spin.setDecimals(2)
        stop_spin.setSuffix("%")
        stop_spin.setValue(config.stop_pct)
        stop_spin.valueChanged.connect(
            lambda val, r=row: self._on_stop_changed(r, val)
        )
        self.setCellWidget(row, self.COL_STOP, stop_spin)

        # Efficiency spinbox
        eff_spin = NoScrollDoubleSpinBox()
        eff_spin.setRange(0.0, 2.0)
        eff_spin.setDecimals(2)
        eff_spin.setSingleStep(0.1)
        eff_spin.setValue(config.efficiency)
        eff_spin.valueChanged.connect(
            lambda val, r=row: self._on_efficiency_changed(r, val)
        )
        self.setCellWidget(row, self.COL_EFFICIENCY, eff_spin)

        # Size Type combo
        size_combo = NoScrollComboBox()
        size_combo.addItems(list(self.SIZE_TYPE_DISPLAY.values()))
        size_combo.setCurrentText(self.SIZE_TYPE_DISPLAY[config.size_type])
        size_combo.currentTextChanged.connect(
            lambda text, r=row: self._on_size_type_changed(r, text)
        )
        self.setCellWidget(row, self.COL_SIZE_TYPE, size_combo)

        # Size Value spinbox
        size_spin = NoScrollDoubleSpinBox()
        size_spin.setRange(0.0, 1000000.0)
        size_spin.setDecimals(2)
        size_spin.setValue(config.size_value)
        size_spin.valueChanged.connect(
            lambda val, r=row: self._on_size_value_changed(r, val)
        )
        self.setCellWidget(row, self.COL_SIZE_VALUE, size_spin)

        # Max Compound spinbox (optional - None means no limit)
        max_spin = NoScrollDoubleSpinBox()
        max_spin.setRange(0.0, 1000000.0)
        max_spin.setDecimals(2)
        max_spin.setSpecialValueText("None")
        max_spin.setValue(config.max_compound if config.max_compound else 0.0)
        max_spin.valueChanged.connect(
            lambda val, r=row: self._on_max_compound_changed(r, val)
        )
        self.setCellWidget(row, self.COL_MAX_COMPOUND, max_spin)

        # Menu button
        menu_btn = QPushButton("...")
        menu_btn.setFixedWidth(30)
        menu_btn.clicked.connect(lambda _, r=row: self._show_row_menu(r))
        self.setCellWidget(row, self.COL_MENU, menu_btn)

    def _create_centered_checkbox(self, checked: bool) -> tuple[QWidget, QCheckBox]:
        """Create a checkbox widget centered in its container.

        Args:
            checked: Initial checked state.

        Returns:
            Tuple of (container widget, checkbox widget).
        """
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        layout.addWidget(checkbox)

        return container, checkbox

    def _get_checkbox(self, row: int, col: int) -> Optional[QCheckBox]:
        """Get checkbox from a cell widget.

        Args:
            row: Row index.
            col: Column index.

        Returns:
            The checkbox widget or None if not found.
        """
        container = self.cellWidget(row, col)
        if container:
            checkbox = container.findChild(QCheckBox)
            return checkbox
        return None

    def set_baseline(self, row: int, checked: bool) -> None:
        """Set the baseline checkbox state for a row.

        Args:
            row: Row index.
            checked: Whether to check the checkbox.
        """
        checkbox = self._get_checkbox(row, self.COL_BL)
        if checkbox:
            checkbox.setChecked(checked)

    def set_candidate(self, row: int, checked: bool) -> None:
        """Set the candidate checkbox state for a row.

        Args:
            row: Row index.
            checked: Whether to check the checkbox.
        """
        checkbox = self._get_checkbox(row, self.COL_CND)
        if checkbox:
            checkbox.setChecked(checked)

    def _on_baseline_changed(self, row: int, state: int) -> None:
        """Handle baseline checkbox state change.

        Args:
            row: Row index.
            state: Qt check state.
        """
        checked = state == Qt.CheckState.Checked.value
        self._strategies[row] = replace(self._strategies[row], is_baseline=checked)
        self.strategy_changed.emit()

    def _on_candidate_changed(self, row: int, state: int) -> None:
        """Handle candidate checkbox state change.

        Args:
            row: Row index.
            state: Qt check state.
        """
        checked = state == Qt.CheckState.Checked.value
        self._strategies[row] = replace(self._strategies[row], is_candidate=checked)
        self.strategy_changed.emit()

    def _on_stop_changed(self, row: int, value: float) -> None:
        """Handle stop% value change.

        Args:
            row: Row index.
            value: New stop percentage.
        """
        self._strategies[row] = replace(self._strategies[row], stop_pct=value)
        self.strategy_changed.emit()

    def _on_efficiency_changed(self, row: int, value: float) -> None:
        """Handle efficiency value change.

        Args:
            row: Row index.
            value: New efficiency value.
        """
        self._strategies[row] = replace(self._strategies[row], efficiency=value)
        self.strategy_changed.emit()

    def _on_size_type_changed(self, row: int, text: str) -> None:
        """Handle size type combo change.

        Args:
            row: Row index.
            text: Selected display text.
        """
        size_type = self.SIZE_TYPE_FROM_DISPLAY.get(text, PositionSizeType.CUSTOM_PCT)
        self._strategies[row] = replace(self._strategies[row], size_type=size_type)
        self.strategy_changed.emit()

    def _on_size_value_changed(self, row: int, value: float) -> None:
        """Handle size value change.

        Args:
            row: Row index.
            value: New size value.
        """
        self._strategies[row] = replace(self._strategies[row], size_value=value)
        self.strategy_changed.emit()

    def _on_max_compound_changed(self, row: int, value: float) -> None:
        """Handle max compound value change.

        Args:
            row: Row index.
            value: New max compound value (0 means None).
        """
        max_val = value if value > 0 else None
        self._strategies[row] = replace(self._strategies[row], max_compound=max_val)
        self.strategy_changed.emit()

    def _show_row_menu(self, row: int) -> None:
        """Show context menu for a row.

        Args:
            row: Row index.
        """
        from src.ui.constants import Colors

        menu = QMenu(self)
        # Apply dark theme styling directly to menu
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 4px 0;
            }}
            QMenu::item {{
                padding: 8px 24px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QMenu::item:selected {{
                background-color: rgba(0, 255, 212, 0.15);
                color: {Colors.TEXT_PRIMARY};
            }}
        """)

        # Add Load Data action
        load_action = menu.addAction("Load Data")
        if load_action:
            strategy_name = self._strategies[row].name
            load_action.triggered.connect(lambda: self.load_data_requested.emit(strategy_name))

        # Add Delete action
        delete_action = menu.addAction("Delete")
        if delete_action:
            delete_action.triggered.connect(lambda: self.remove_strategy(row))

        # Get the menu button position
        btn = self.cellWidget(row, self.COL_MENU)
        if btn:
            menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def get_strategies(self) -> list[StrategyConfig]:
        """Get all strategy configurations.

        Returns:
            List of strategy configurations with current values.
        """
        # Update names from table items (editable cells)
        for row in range(self.rowCount()):
            name_item = self.item(row, self.COL_NAME)
            if name_item:
                current_name = name_item.text()
                if current_name != self._strategies[row].name:
                    self._strategies[row] = replace(
                        self._strategies[row], name=current_name
                    )

        return list(self._strategies)

    def remove_strategy(self, row: int) -> None:
        """Remove a strategy from the table.

        Args:
            row: Row index to remove.
        """
        if 0 <= row < len(self._strategies):
            del self._strategies[row]
            self.removeRow(row)
            self.strategy_changed.emit()

    def clear_all(self) -> None:
        """Remove all strategies from the table."""
        self._strategies.clear()
        self.setRowCount(0)
        self.strategy_changed.emit()
