"""FilterPanel container for managing filters."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.core.models import FilterCriteria, FilterPreset
from src.ui.components.column_filter_panel import ColumnFilterPanel
from src.ui.components.date_range_filter import DateRangeFilter
from src.ui.components.filter_chip import FilterChip
from src.ui.components.time_range_filter import TimeRangeFilter
from src.ui.components.toggle_switch import ToggleSwitch
from src.ui.constants import Colors, Spacing
from src.ui.utils.flow_layout import FlowLayout


class FilterPanel(QWidget):
    """Panel for managing filter rows and displaying active filters.

    Attributes:
        filters_applied: Signal emitted with list of FilterCriteria when applied.
        filters_cleared: Signal emitted when all filters are cleared.
        date_range_changed: Signal emitted when date range changes.
            Args: (start: str | None, end: str | None, all_dates: bool)
        time_range_changed: Signal emitted when time range changes.
            Args: (start: str | None, end: str | None, all_times: bool)
    """

    filters_applied = pyqtSignal(list)  # list[FilterCriteria]
    filters_cleared = pyqtSignal()
    first_trigger_toggled = pyqtSignal(bool)
    date_range_changed = pyqtSignal(object, object, bool)  # start, end, all_dates
    time_range_changed = pyqtSignal(object, object, bool)  # start, end, all_times
    single_filter_applied = pyqtSignal(object)  # Emits single FilterCriteria
    preset_save_requested = pyqtSignal()  # Emitted when Save clicked
    preset_load_requested = pyqtSignal(str)  # Emitted with preset name

    def __init__(
        self,
        columns: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize FilterPanel.

        Args:
            columns: Initial list of numeric column names.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._columns = columns or []
        self._filter_chips: list[FilterChip] = []
        self._active_filters: list[FilterCriteria] = []
        # Date range state
        self._date_start: str | None = None
        self._date_end: str | None = None
        self._all_dates: bool = True
        # Time range state
        self._time_start: str | None = None
        self._time_end: str | None = None
        self._all_times_time: bool = True
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        """Set up the panel UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, Spacing.MD, 0, Spacing.MD)
        layout.setSpacing(Spacing.SM)

        # Section header
        header = QLabel("Filters")
        header.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-weight: bold;
                font-size: 13px;
            }}
        """)
        layout.addWidget(header)

        # Date range filter (above filter rows)
        self._date_range_filter = DateRangeFilter()
        self._date_range_filter.date_range_changed.connect(self._on_date_range_changed)
        layout.addWidget(self._date_range_filter)

        # Time range filter
        self._time_range_filter = TimeRangeFilter()
        self._time_range_filter.time_range_changed.connect(self._on_time_range_changed)
        layout.addWidget(self._time_range_filter)

        # Chips area for active filters (scrollable, uses FlowLayout for wrapping)
        self._chips_scroll = QScrollArea()
        self._chips_scroll.setWidgetResizable(True)
        self._chips_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._chips_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._chips_scroll.setMaximumHeight(80)  # Limit height, scroll if more chips
        self._chips_scroll.setMinimumHeight(0)

        self._chips_frame = QFrame()
        self._chips_layout = FlowLayout(margin=0, spacing=Spacing.XS)
        self._chips_frame.setLayout(self._chips_layout)

        self._chips_scroll.setWidget(self._chips_frame)
        layout.addWidget(self._chips_scroll)

        # Column filter panel (scrollable inline filter system)
        self._column_filter_panel = ColumnFilterPanel(columns=self._columns)
        self._column_filter_panel.setMinimumHeight(220)
        self._column_filter_panel.setMaximumHeight(240)
        self._column_filter_panel.single_filter_applied.connect(
            self._on_single_filter_applied
        )
        layout.addWidget(self._column_filter_panel)

        # Add spacing before toggle
        layout.addSpacing(Spacing.XL)

        # First trigger toggle (above buttons)
        self._first_trigger_toggle = ToggleSwitch(
            label="First Trigger Only",
            initial=True,  # ON by default, matching AppState default
        )
        self._first_trigger_toggle.toggled.connect(self.first_trigger_toggled.emit)
        layout.addWidget(self._first_trigger_toggle)

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(Spacing.SM)

        self._apply_btn = QPushButton("Apply Filters")
        self._apply_btn.clicked.connect(self._on_apply_filters)
        btn_layout.addWidget(self._apply_btn)

        self._clear_btn = QPushButton("Clear All")
        self._clear_btn.clicked.connect(self._on_clear_filters)
        btn_layout.addWidget(self._clear_btn)

        btn_layout.addSpacing(Spacing.MD)

        self._save_btn = QPushButton("Save")
        self._save_btn.clicked.connect(self._on_save_clicked)
        btn_layout.addWidget(self._save_btn)

        self._load_combo = QComboBox()
        self._load_combo.addItem("Load preset...")
        self._load_combo.currentIndexChanged.connect(self._on_load_selected)
        btn_layout.addWidget(self._load_combo)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()

    def _apply_style(self) -> None:
        """Apply Observatory theme styling."""
        primary_btn_style = f"""
            QPushButton {{
                background-color: {Colors.SIGNAL_CYAN};
                color: {Colors.BG_BASE};
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.SIGNAL_BLUE};
            }}
            QPushButton:disabled {{
                background-color: {Colors.BG_BORDER};
                color: {Colors.TEXT_DISABLED};
            }}
        """
        self._apply_btn.setStyleSheet(primary_btn_style)

        secondary_btn_style = f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                border-color: {Colors.SIGNAL_CYAN};
                color: {Colors.SIGNAL_CYAN};
            }}
            QPushButton:disabled {{
                color: {Colors.TEXT_DISABLED};
            }}
        """
        self._clear_btn.setStyleSheet(secondary_btn_style)

        # Save button (amber accent)
        save_btn_style = f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                border-color: {Colors.SIGNAL_AMBER};
                color: {Colors.SIGNAL_AMBER};
            }}
        """
        self._save_btn.setStyleSheet(save_btn_style)

        # Load combo
        load_combo_style = f"""
            QComboBox {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 120px;
            }}
            QComboBox:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {Colors.TEXT_SECONDARY};
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                selection-background-color: {Colors.BG_SURFACE};
            }}
        """
        self._load_combo.setStyleSheet(load_combo_style)

        # Add chips scroll area and frame styling - use explicit backgrounds to prevent bleeding
        self._chips_scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {Colors.BG_SURFACE};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {Colors.BG_ELEVATED};
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {Colors.BG_BORDER};
                border-radius: 3px;
                min-height: 15px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {Colors.TEXT_SECONDARY};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        # Set viewport and chips frame backgrounds explicitly
        self._chips_scroll.viewport().setStyleSheet(f"background-color: {Colors.BG_SURFACE};")
        self._chips_frame.setStyleSheet(f"background-color: {Colors.BG_SURFACE};")

    def _on_date_range_changed(
        self, start: str | None, end: str | None, all_dates: bool
    ) -> None:
        """Handle date range filter change.

        Args:
            start: Start date ISO string or None.
            end: End date ISO string or None.
            all_dates: Whether 'All Dates' is checked.
        """
        self._date_start = start
        self._date_end = end
        self._all_dates = all_dates
        self.date_range_changed.emit(start, end, all_dates)

    def _on_time_range_changed(
        self, start: str | None, end: str | None, all_times: bool
    ) -> None:
        """Handle time range filter change.

        Args:
            start: Start time string (HH:MM:SS) or None.
            end: End time string (HH:MM:SS) or None.
            all_times: Whether 'All Times' is checked.
        """
        self._time_start = start
        self._time_end = end
        self._all_times_time = all_times
        self.time_range_changed.emit(start, end, all_times)

    def _on_single_filter_applied(self, criteria: FilterCriteria) -> None:
        """Handle single filter applied from column row.

        Args:
            criteria: The FilterCriteria to apply.
        """
        # Check if filter for this column already exists, replace it
        self._active_filters = [
            f for f in self._active_filters if f.column != criteria.column
        ]
        self._active_filters.append(criteria)
        self._update_chips()
        self.single_filter_applied.emit(criteria)

    def _on_apply_filters(self) -> None:
        """Handle apply filters button click."""
        criteria_list = self._column_filter_panel.get_active_criteria()
        self._active_filters = criteria_list
        self._update_chips()
        self.filters_applied.emit(criteria_list)

    def _on_clear_filters(self) -> None:
        """Handle clear all filters button click."""
        # Clear column filter panel
        self._column_filter_panel.clear_all()

        # Clear chips
        for chip in self._filter_chips[:]:
            chip.deleteLater()
        self._filter_chips.clear()

        # Reset date range filter
        self._date_range_filter.reset()
        self._date_start = None
        self._date_end = None
        self._all_dates = True

        # Reset time range filter
        self._time_range_filter.reset()
        self._time_start = None
        self._time_end = None
        self._all_times_time = True

        self._active_filters.clear()
        self.filters_cleared.emit()

    def _update_chips(self) -> None:
        """Update chip display based on active filters."""
        # Clear existing chips - must remove from layout before deleting
        for chip in self._filter_chips[:]:
            self._chips_layout.removeWidget(chip)
            chip.deleteLater()
        self._filter_chips.clear()

        # Add new chips (FlowLayout handles positioning)
        for criteria in self._active_filters:
            chip = FilterChip(criteria)
            chip.removed.connect(self._on_chip_removed)
            self._filter_chips.append(chip)
            self._chips_layout.addWidget(chip)

        # Trigger geometry update so scroll area recalculates content size
        self._chips_frame.updateGeometry()

    def _on_chip_removed(self, criteria: FilterCriteria) -> None:
        """Handle chip removal.

        Args:
            criteria: The FilterCriteria to remove.
        """
        if criteria in self._active_filters:
            self._active_filters.remove(criteria)

        self._update_chips()

        # Re-emit with updated list
        if self._active_filters:
            self.filters_applied.emit(self._active_filters)
        else:
            self.filters_cleared.emit()

    def set_columns(self, columns: list[str]) -> None:
        """Update available columns for filtering.

        Args:
            columns: List of numeric column names.
        """
        self._columns = columns
        self._column_filter_panel.set_columns(columns)

    def get_date_range(self) -> tuple[str | None, str | None, bool]:
        """Get current date range.

        Returns:
            Tuple of (start_iso, end_iso, all_dates).
        """
        return (self._date_start, self._date_end, self._all_dates)

    def get_time_range(self) -> tuple[str | None, str | None, bool]:
        """Get current time range filter values.

        Returns:
            Tuple of (start_time, end_time, all_times).
            Times are HH:MM:SS strings or None if all_times=True.
        """
        return self._time_range_filter.get_range()

    def _on_save_clicked(self) -> None:
        """Handle Save button click."""
        self.preset_save_requested.emit()

    def _on_load_selected(self, index: int) -> None:
        """Handle Load combo selection.

        Args:
            index: Selected item index.
        """
        if index > 0:  # Skip placeholder
            preset_name = self._load_combo.itemText(index)
            self.preset_load_requested.emit(preset_name)
            # Reset to placeholder
            self._load_combo.blockSignals(True)
            self._load_combo.setCurrentIndex(0)
            self._load_combo.blockSignals(False)

    def update_preset_list(self, names: list[str]) -> None:
        """Update the Load dropdown with available presets.

        Args:
            names: List of preset names (already sorted).
        """
        self._load_combo.blockSignals(True)
        self._load_combo.clear()

        if names:
            self._load_combo.addItem("Load preset...")
            for name in names:
                self._load_combo.addItem(name)
        else:
            self._load_combo.addItem("No saved presets")

        self._load_combo.blockSignals(False)

    def get_full_state(self, name: str) -> FilterPreset:
        """Get complete filter state as a FilterPreset.

        Args:
            name: Name for the preset.

        Returns:
            FilterPreset with all current filter state.
        """
        return FilterPreset(
            name=name,
            column_filters=self._column_filter_panel.get_active_criteria(),
            date_range=self.get_date_range(),
            time_range=self.get_time_range(),
            first_trigger_only=self._first_trigger_toggle.isChecked(),
        )

    def set_full_state(self, preset: FilterPreset) -> list[str]:
        """Apply a FilterPreset to all filter controls.

        Args:
            preset: FilterPreset to apply.

        Returns:
            List of column names that were skipped (not found).
        """
        # Set column filters
        skipped = self._column_filter_panel.set_filter_values(preset.column_filters)

        # Set date range
        self._date_range_filter.set_range(*preset.date_range)

        # Set time range
        self._time_range_filter.set_range(*preset.time_range)

        # Set first trigger toggle
        self._first_trigger_toggle.setChecked(preset.first_trigger_only)

        return skipped
