"""Data Binning tab for defining custom bin ranges on numeric columns."""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QEvent, QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPaintEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from src.core.models import BinConfig, BinDefinition
from src.ui.components.empty_state import EmptyState
from src.ui.components.toast import Toast
from src.ui.constants import Colors, Fonts, Spacing

if TYPE_CHECKING:
    from src.core.app_state import AppState

logger = logging.getLogger(__name__)


def parse_time_input(value: str | int) -> str:
    """Parse HHMMSS integer or string to HH:MM:SS format.

    Args:
        value: Time as integer (93000), numeric string ("093000"),
               or formatted string ("09:30:00")

    Returns:
        Formatted time string "HH:MM:SS"

    Raises:
        ValueError: If time is invalid (hours > 23, minutes > 59, seconds > 59)
    """
    # Handle None or empty
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError("Empty time value")

    # Handle negative numbers
    if isinstance(value, int) and value < 0:
        raise ValueError(f"Negative time value: {value}")

    if isinstance(value, str) and value.strip().startswith("-"):
        raise ValueError(f"Negative time value: {value}")

    # Already formatted - validate pattern
    if isinstance(value, str) and ":" in value:
        parts = value.split(":")
        if len(parts) == 3:
            try:
                hours, mins, secs = int(parts[0]), int(parts[1]), int(parts[2])
                if hours > 23 or mins > 59 or secs > 59:
                    raise ValueError(f"Invalid time: {value}")
                if hours < 0 or mins < 0 or secs < 0:
                    raise ValueError(f"Invalid time: {value}")
                return value
            except (ValueError, IndexError) as err:
                raise ValueError(f"Invalid time format: {value}") from err
        raise ValueError(f"Invalid time format: {value}")

    # Convert to integer and then format
    if isinstance(value, int) or (isinstance(value, str) and value.replace(" ", "").isdigit()):
        int_value = int(value)

        # Check for invalid range (> 235959)
        if int_value > 235959:
            raise ValueError(f"Invalid time: {value} (exceeds 23:59:59)")
        if int_value < 0:
            raise ValueError(f"Negative time value: {value}")

        # Zero-pad to 6 digits
        value_str = str(int_value).zfill(6)
        hours = int(value_str[:2])
        mins = int(value_str[2:4])
        secs = int(value_str[4:6])

        if hours > 23 or mins > 59 or secs > 59:
            raise ValueError(f"Invalid time: {value}")

        return f"{value_str[:2]}:{value_str[2:4]}:{value_str[4:6]}"

    raise ValueError(f"Unrecognized time format: {value}")


def is_time_column(column_name: str) -> bool:
    """Check if a column appears to be time-based by its name.

    Columns that are already in numeric time format (like time_minutes)
    are excluded since they should be treated as regular numeric columns.

    Args:
        column_name: Name of the column to check.

    Returns:
        True if the column name suggests it contains time data in HH:MM:SS format.
    """
    column_lower = column_name.lower()

    # Exclude columns that are already in numeric time format
    numeric_time_suffixes = ["_minutes", "_seconds", "_hours", "_mins", "_secs"]
    if any(column_lower.endswith(suffix) for suffix in numeric_time_suffixes):
        return False

    time_indicators = ["time", "timestamp", "hour", "minute", "second"]
    return any(indicator in column_lower for indicator in time_indicators)


class DataBinningTab(QWidget):
    """Tab for configuring data binning on numeric columns.

    Provides UI for selecting a numeric column from the loaded dataset
    and defining custom bins with operators: Less than (<), Greater than (>),
    and Range (X-Y). A Nulls bin is automatically included.

    Signals:
        column_selected: Emitted when user changes column selection.
        bin_config_changed: Emitted when bin configuration changes.
        analyze_requested: Emitted when user requests bin analysis (Story 6.2).
    """

    # Signals for future integration (Story 6.2)
    column_selected = pyqtSignal(str)  # column_name
    bin_config_changed = pyqtSignal(str, list)  # column_name, list of BinDefinition
    analyze_requested = pyqtSignal()

    def __init__(self, app_state: "AppState", parent: QWidget | None = None) -> None:
        """Initialize the Data Binning tab.

        Args:
            app_state: Centralized application state.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._app_state = app_state
        self._bin_rows: list[BinConfigRow] = []
        self._is_time_column: bool = False
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._update_chart_panel)
        self._last_save_dir: Path | None = None
        self._setup_ui()
        self._connect_signals()
        self._initialize_from_state()

    def _setup_ui(self) -> None:
        """Set up the UI with sidebar and content area layout."""
        # Sidebar
        self._sidebar = self._create_sidebar()

        # Content area (chart area for Story 6.2)
        self._content_area = self._create_content_area()

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {Colors.BG_BORDER};
            }}
            QSplitter::handle:hover {{
                background: {Colors.SIGNAL_CYAN};
            }}
        """)

        splitter.addWidget(self._sidebar)
        splitter.addWidget(self._content_area)

        # Set initial sizes (280px sidebar, rest for charts)
        splitter.setSizes([280, 800])

        # Prevent panels from collapsing
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(splitter)

    def _create_sidebar(self) -> QFrame:
        """Create the sidebar with column selector and bin configuration.

        Returns:
            Configured sidebar frame.
        """
        sidebar = QFrame()
        sidebar.setMinimumWidth(200)
        sidebar.setMaximumWidth(500)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_SURFACE};
                border-right: 1px solid {Colors.BG_BORDER};
            }}
        """)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # Column selector section
        column_label = QLabel("Column")
        column_label.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-family: {Fonts.UI};
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
        """)
        layout.addWidget(column_label)

        self._column_dropdown = QComboBox()
        self._column_dropdown.setPlaceholderText("Load data first")
        self._column_dropdown.setEnabled(False)
        self._column_dropdown.setStyleSheet(f"""
            QComboBox {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.UI};
                font-size: 13px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 8px 12px;
            }}
            QComboBox:disabled {{
                color: {Colors.TEXT_DISABLED};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {Colors.TEXT_SECONDARY};
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                selection-background-color: {Colors.SIGNAL_BLUE};
                border: 1px solid {Colors.BG_BORDER};
            }}
        """)
        layout.addWidget(self._column_dropdown)

        layout.addSpacing(Spacing.MD)

        # Bins section label
        bins_label = QLabel("Bins")
        bins_label.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-family: {Fonts.UI};
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
        """)
        layout.addWidget(bins_label)

        # Scrollable bin configuration area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)

        self._bin_container = QWidget()
        self._bin_layout = QVBoxLayout(self._bin_container)
        self._bin_layout.setContentsMargins(0, 0, 0, 0)
        self._bin_layout.setSpacing(Spacing.SM)
        self._bin_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll_area.setWidget(self._bin_container)
        layout.addWidget(scroll_area, stretch=1)

        # Add Bin button
        self._add_bin_button = QPushButton("+ Add Bin")
        self._add_bin_button.setEnabled(False)
        self._add_bin_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_bin_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.UI};
                font-size: 13px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_BORDER};
            }}
            QPushButton:disabled {{
                color: {Colors.TEXT_DISABLED};
            }}
        """)
        layout.addWidget(self._add_bin_button)

        # Auto-split section
        layout.addSpacing(Spacing.SM)

        auto_split_label = QLabel("Auto-Split")
        auto_split_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.UI};
                font-size: 10px;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 1.5px;
            }}
        """)
        layout.addWidget(auto_split_label)

        layout.addSpacing(Spacing.XS)

        # Horizontal button group
        auto_split_container = QWidget()
        auto_split_layout = QHBoxLayout(auto_split_container)
        auto_split_layout.setContentsMargins(0, 0, 0, 0)
        auto_split_layout.setSpacing(Spacing.XS)

        self._quartile_btn = AutoSplitButton("Q4", 4)
        self._quartile_btn.setToolTip("Split into 4 quartiles (25th, 50th, 75th percentiles)")
        self._quartile_btn.setEnabled(False)

        self._quintile_btn = AutoSplitButton("Q5", 5)
        self._quintile_btn.setToolTip("Split into 5 quintiles (20th, 40th, 60th, 80th percentiles)")
        self._quintile_btn.setEnabled(False)

        self._decile_btn = AutoSplitButton("D10", 10)
        self._decile_btn.setToolTip("Split into 10 deciles (10th through 90th percentiles)")
        self._decile_btn.setEnabled(False)

        auto_split_layout.addWidget(self._quartile_btn)
        auto_split_layout.addWidget(self._quintile_btn)
        auto_split_layout.addWidget(self._decile_btn)
        auto_split_layout.addStretch()

        layout.addWidget(auto_split_container)

        # Separator before save/load buttons
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {Colors.BG_BORDER};")
        separator.setFixedHeight(1)
        layout.addSpacing(Spacing.MD)
        layout.addWidget(separator)
        layout.addSpacing(Spacing.MD)

        # Save Config button
        self._save_config_btn = QPushButton("Save Config")
        self._save_config_btn.setObjectName("save_config_btn")
        self._save_config_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_config_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.UI};
                font-size: 13px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: {Spacing.SM}px {Spacing.MD}px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_BORDER};
            }}
        """)
        layout.addWidget(self._save_config_btn)

        # Load Config button
        self._load_config_btn = QPushButton("Load Config")
        self._load_config_btn.setObjectName("load_config_btn")
        self._load_config_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._load_config_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.UI};
                font-size: 13px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: {Spacing.SM}px {Spacing.MD}px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_BORDER};
            }}
        """)
        layout.addWidget(self._load_config_btn)

        return sidebar

    def _create_content_area(self) -> QFrame:
        """Create the main content area with BinChartPanel.

        Returns:
            Configured content area frame.
        """
        content = QFrame()
        content.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_BASE};
            }}
        """)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        # Chart panel for bin analysis
        self._chart_panel = BinChartPanel(self._app_state)
        layout.addWidget(self._chart_panel)

        return content

    def _connect_signals(self) -> None:
        """Connect AppState signals to local handlers."""
        self._app_state.data_loaded.connect(self._on_data_loaded)
        self._app_state.adjustment_params_changed.connect(self._on_adjustment_changed)
        self._column_dropdown.currentTextChanged.connect(self._on_column_selected)
        self._add_bin_button.clicked.connect(self._on_add_bin_clicked)
        self._save_config_btn.clicked.connect(self._on_save_config_clicked)
        self._load_config_btn.clicked.connect(self._on_load_config_clicked)

        # Connect bin config changes to debounced chart update
        self.bin_config_changed.connect(self._on_bin_config_changed)
        self.column_selected.connect(self._on_column_selected_for_chart)

    def _initialize_from_state(self) -> None:
        """Initialize UI from current AppState if data exists."""
        if self._app_state.baseline_df is not None:
            self._populate_column_dropdown(self._app_state.baseline_df)

    def _on_data_loaded(self, df: "object") -> None:
        """Handle data loaded signal.

        Args:
            df: Loaded DataFrame (typed as object due to signal limitation).
        """
        import pandas as pd

        if isinstance(df, pd.DataFrame):
            # Use baseline_df for column population (includes adjusted_gain_pct)
            if self._app_state.baseline_df is not None:
                self._populate_column_dropdown(self._app_state.baseline_df)
            else:
                self._populate_column_dropdown(df)

    def _on_adjustment_changed(self, params: "object") -> None:
        """Handle adjustment parameters changed signal.

        Re-populate column dropdown in case adjusted_gain_pct column is now available.

        Args:
            params: AdjustmentParams (typed as object due to signal limitation).
        """
        if self._app_state.baseline_df is not None:
            current_selection = self._column_dropdown.currentText()
            self._populate_column_dropdown(self._app_state.baseline_df)
            # Restore selection if it still exists
            idx = self._column_dropdown.findText(current_selection)
            if idx >= 0:
                self._column_dropdown.setCurrentIndex(idx)

    def _populate_column_dropdown(self, df: "object") -> None:
        """Populate column dropdown with numeric columns from DataFrame.

        Args:
            df: DataFrame to extract numeric columns from.
        """
        import pandas as pd

        if not isinstance(df, pd.DataFrame):
            return

        # Get numeric columns
        numeric_cols = df.select_dtypes(
            include=["int64", "float64", "int32", "float32"]
        ).columns.tolist()

        self._column_dropdown.clear()
        self._column_dropdown.setPlaceholderText("Select a column...")
        self._column_dropdown.setEnabled(True)
        self._column_dropdown.addItems(numeric_cols)

        # Enable add bin button
        self._add_bin_button.setEnabled(True)

        logger.debug("Populated column dropdown with %d numeric columns", len(numeric_cols))

    def _on_column_selected(self, column_name: str) -> None:
        """Handle column selection change.

        Args:
            column_name: Name of the selected column.
        """
        if column_name:
            # Detect if this is a time column
            self._is_time_column = is_time_column(column_name)
            self.column_selected.emit(column_name)
            self._setup_default_bins(column_name)
            logger.debug(
                "Column selected: %s (time_column=%s)", column_name, self._is_time_column
            )

    def _setup_default_bins(self, column_name: str) -> None:
        """Set up default bins for the selected column.

        Args:
            column_name: Name of the selected column.
        """
        # Clear existing bins
        self._clear_bin_rows()

        # Add the permanent Nulls bin
        nulls_row = BinConfigRow(
            operator="nulls", is_removable=False, is_time_column=self._is_time_column
        )
        self._add_bin_row(nulls_row)

        # Emit config changed
        self._emit_bin_config_changed()

    def _clear_bin_rows(self) -> None:
        """Clear all bin configuration rows."""
        for row in self._bin_rows:
            row.setParent(None)
            row.deleteLater()
        self._bin_rows.clear()

    def _add_bin_row(self, row: "BinConfigRow") -> None:
        """Add a bin configuration row to the container.

        Args:
            row: BinConfigRow widget to add.
        """
        row.remove_requested.connect(self._on_bin_remove_requested)
        row.config_changed.connect(self._on_bin_row_changed)
        self._bin_layout.addWidget(row)
        self._bin_rows.append(row)

    def _on_add_bin_clicked(self) -> None:
        """Handle Add Bin button click."""
        if not self._column_dropdown.currentText():
            return

        # Create new bin row with default "Range" operator
        new_row = BinConfigRow(
            operator="range", is_removable=True, is_time_column=self._is_time_column
        )
        # Insert before the nulls row (which should be last)
        if self._bin_rows:
            self._bin_layout.insertWidget(self._bin_layout.count() - 1, new_row)
            new_row.remove_requested.connect(self._on_bin_remove_requested)
            new_row.config_changed.connect(self._on_bin_row_changed)
            self._bin_rows.insert(len(self._bin_rows) - 1, new_row)
        else:
            self._add_bin_row(new_row)

        self._emit_bin_config_changed()
        logger.debug("Added new bin row")

    def _on_bin_remove_requested(self, row: "BinConfigRow") -> None:
        """Handle bin row removal request.

        Args:
            row: The BinConfigRow requesting removal.
        """
        if row in self._bin_rows:
            self._bin_rows.remove(row)
            row.setParent(None)
            row.deleteLater()
            self._emit_bin_config_changed()
            logger.debug("Removed bin row")

    def _on_bin_row_changed(self) -> None:
        """Handle bin row configuration change."""
        self._emit_bin_config_changed()

    def _emit_bin_config_changed(self) -> None:
        """Emit bin_config_changed signal with current configuration."""
        column_name = self._column_dropdown.currentText()
        if column_name:
            bins = [row.get_bin_definition() for row in self._bin_rows]
            self.bin_config_changed.emit(column_name, bins)

    def _on_bin_config_changed(self, column: str, bins: list) -> None:
        """Handle bin configuration change with debouncing.

        Args:
            column: Column name being binned.
            bins: List of BinDefinition objects.
        """
        # Debounce chart updates to prevent excessive recalculations
        self._debounce_timer.start(300)

    def _on_column_selected_for_chart(self, column: str) -> None:
        """Handle column selection for chart update.

        Args:
            column: Selected column name.
        """
        # Trigger immediate chart update on column change
        self._debounce_timer.start(50)

    def _update_chart_panel(self) -> None:
        """Update the chart panel with current bin configuration."""
        column = self._column_dropdown.currentText()
        bins = self.get_bin_definitions()
        self._chart_panel.update_charts(column, bins)

    def get_bin_definitions(self) -> list["BinDefinition"]:
        """Get current bin definitions.

        Returns:
            List of BinDefinition objects.
        """
        return [row.get_bin_definition() for row in self._bin_rows]


    def _get_current_config(self) -> BinConfig | None:
        """Collect current configuration state into BinConfig.

        Returns:
            BinConfig if valid configuration exists, None otherwise.
        """
        column = self._column_dropdown.currentText()
        if not column:
            return None

        bins = self.get_bin_definitions()
        if not bins:
            return None

        # Get metric selection from chart panel
        metric_column = self._chart_panel._current_metric_column

        return BinConfig(column=column, bins=bins, metric_column=metric_column)

    def _apply_config(self, config: BinConfig) -> None:
        """Populate UI from BinConfig.

        Args:
            config: The configuration to apply.
        """
        # Set column dropdown if column exists in current data
        column_index = self._column_dropdown.findText(config.column)
        if column_index >= 0:
            self._column_dropdown.setCurrentIndex(column_index)
        else:
            # Column not found, show warning but still populate bin rows
            Toast.display(
                self,
                f"Column '{config.column}' not found in data. Please select a column manually.",
                "info",
                duration=5000,
            )

        # Clear existing bin rows and populate with loaded bin definitions
        self._clear_bin_rows()
        for bin_def in config.bins:
            # Create a BinConfigRow with the correct operator
            is_nulls = bin_def.operator == "nulls"
            row = BinConfigRow(
                operator=bin_def.operator,
                is_removable=not is_nulls,  # Nulls row is not removable
                is_time_column=self._is_time_column,
            )

            # Set values for non-nulls rows
            if not is_nulls and hasattr(row, "_value1_input"):
                if bin_def.value1 is not None:
                    row._value1_input.setText(str(bin_def.value1))
                if bin_def.operator == "range" and bin_def.value2 is not None:
                    row._value2_input.setText(str(bin_def.value2))

            self._add_bin_row(row)

        # Set metric toggle
        self._chart_panel.set_metric_column(config.metric_column)

        # Emit signal to update charts
        self._emit_bin_config_changed()

    def _on_save_config_clicked(self) -> None:
        """Handle Save Config button click."""
        config = self._get_current_config()
        if config is None:
            Toast.display(self, "No bins configured to save", "error", duration=3000)
            return

        errors = config.validate()
        if errors:
            Toast.display(self, errors[0], "error", duration=3000)
            return

        # Get default filename
        default_dir = str(self._last_save_dir or Path.home())
        default_name = f"bin_config_{config.column}.json"

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Bin Configuration",
            str(Path(default_dir) / default_name),
            "JSON Files (*.json)",
        )

        if not path:
            return  # User cancelled

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, indent=2)

            # Update last used directory
            self._last_save_dir = Path(path).parent

            Toast.display(self, "Configuration saved", "success")
        except OSError as e:
            logger.exception("Failed to save bin configuration")
            Toast.display(self, f"Failed to save: {e}", "error", duration=5000)

    def _on_load_config_clicked(self) -> None:
        """Handle Load Config button click."""
        default_dir = str(self._last_save_dir or Path.home())

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Bin Configuration",
            default_dir,
            "JSON Files (*.json)",
        )

        if not path:
            return  # User cancelled

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            config = BinConfig.from_dict(data)
            errors = config.validate()
            if errors:
                Toast.display(self, errors[0], "error", duration=5000)
                return

            # Update last used directory
            self._last_save_dir = Path(path).parent

            # Apply the loaded configuration
            self._apply_config(config)

            Toast.display(self, "Configuration loaded", "success")

        except json.JSONDecodeError as e:
            logger.exception("Invalid JSON in bin configuration file")
            Toast.display(self, f"Invalid JSON file: {e}", "error", duration=5000)
        except (KeyError, TypeError) as e:
            logger.exception("Invalid bin configuration structure")
            Toast.display(self, f"Invalid configuration file: {e}", "error", duration=5000)
        except OSError as e:
            logger.exception("Failed to load bin configuration")
            Toast.display(self, f"Failed to load: {e}", "error", duration=5000)


class AutoSplitButton(QPushButton):
    """Custom button with visual segment indicator for auto-split binning."""

    def __init__(
        self, label: str, segments: int, parent: QWidget | None = None
    ) -> None:
        """Initialize auto-split button.

        Args:
            label: Button label (e.g., "Q4", "Q5", "D10").
            segments: Number of segments to display (4, 5, or 10).
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.label = label
        self.segments = segments
        self.setFixedSize(68, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event: "QPaintEvent") -> None:
        """Custom paint with segment bars and label."""
        from PyQt6.QtGui import QColor, QFont, QPainter

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        is_hovered = self.underMouse()
        bg_color = QColor(Colors.BG_BORDER if is_hovered else Colors.BG_ELEVATED)
        border_color = QColor(
            Colors.SIGNAL_CYAN if is_hovered else Colors.BG_BORDER
        )

        painter.setBrush(bg_color)
        painter.setPen(border_color)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)

        # Draw segment bars at top
        max_bars = min(self.segments, 10)
        total_bar_width = self.width() - 16
        bar_width = max(2, (total_bar_width - (max_bars - 1) * 2) // max_bars)
        bar_height = 4
        bar_y = 8
        bar_color = QColor(
            Colors.SIGNAL_CYAN if is_hovered else Colors.TEXT_SECONDARY
        )
        painter.setBrush(bar_color)
        painter.setPen(Qt.PenStyle.NoPen)

        start_x = (self.width() - (max_bars * bar_width + (max_bars - 1) * 2)) // 2
        for i in range(max_bars):
            x = start_x + i * (bar_width + 2)
            painter.drawRoundedRect(x, bar_y, bar_width, bar_height, 1, 1)

        # Draw label
        painter.setPen(QColor(Colors.TEXT_PRIMARY))
        font = QFont(Fonts.UI, 11)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        label_rect = self.rect().adjusted(0, 14, 0, 0)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignHCenter, self.label)

        # Draw disabled overlay if needed
        if not self.isEnabled():
            painter.setBrush(QColor(0, 0, 0, 100))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)


class BinConfigRow(QFrame):
    """Widget for configuring a single bin definition.

    Provides operator selection and value input fields based on the operator type.
    For time columns, parses HHMMSS format to HH:MM:SS display format.
    """

    remove_requested = pyqtSignal(object)  # Self reference
    config_changed = pyqtSignal()

    def __init__(
        self,
        operator: str = "<",
        is_removable: bool = True,
        is_time_column: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize bin configuration row.

        Args:
            operator: Initial operator ("<", ">", "range", "nulls").
            is_removable: Whether this row can be removed.
            is_time_column: Whether the column contains time data.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._is_removable = is_removable
        self._is_time_column = is_time_column
        self._setup_ui(operator)

    def _setup_ui(self, operator: str) -> None:
        """Set up the row UI.

        Args:
            operator: Initial operator to select.
        """
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_ELEVATED};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(Spacing.SM)

        if operator == "nulls":
            # Special nulls row - just a label
            label = QLabel("Nulls")
            label.setStyleSheet(f"""
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.UI};
                font-size: 13px;
            """)
            layout.addWidget(label, stretch=1)
        else:
            # Operator dropdown
            self._operator_dropdown = QComboBox()
            self._operator_dropdown.addItems(["Less than (<)", "Greater than (>)", "Range"])
            self._operator_dropdown.setFixedWidth(110)
            self._operator_dropdown.setStyleSheet(f"""
                QComboBox {{
                    background-color: {Colors.BG_SURFACE};
                    color: {Colors.TEXT_PRIMARY};
                    font-family: {Fonts.UI};
                    font-size: 12px;
                    border: 1px solid {Colors.BG_BORDER};
                    border-radius: 3px;
                    padding: 4px 8px;
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 16px;
                }}
                QComboBox::down-arrow {{
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 4px solid {Colors.TEXT_SECONDARY};
                }}
                QComboBox QAbstractItemView {{
                    background-color: {Colors.BG_ELEVATED};
                    color: {Colors.TEXT_PRIMARY};
                    selection-background-color: {Colors.SIGNAL_BLUE};
                    border: 1px solid {Colors.BG_BORDER};
                }}
            """)

            # Set initial operator
            if operator == "<":
                self._operator_dropdown.setCurrentIndex(0)
            elif operator == ">":
                self._operator_dropdown.setCurrentIndex(1)
            else:
                self._operator_dropdown.setCurrentIndex(2)

            self._operator_dropdown.currentIndexChanged.connect(self._on_operator_changed)
            layout.addWidget(self._operator_dropdown)

            # Value input(s) container
            self._value_container = QWidget()
            self._value_layout = QHBoxLayout(self._value_container)
            self._value_layout.setContentsMargins(0, 0, 0, 0)
            self._value_layout.setSpacing(Spacing.XS)

            from PyQt6.QtWidgets import QLineEdit

            self._value1_input = QLineEdit()
            placeholder = "HH:MM:SS" if self._is_time_column else "Value"
            self._value1_input.setPlaceholderText(placeholder)
            self._value1_input.setStyleSheet(self._get_input_style())
            self._value1_input.textChanged.connect(self._on_value_changed)
            self._value1_input.editingFinished.connect(self._on_value1_editing_finished)
            self._value_layout.addWidget(self._value1_input)

            self._range_separator = QLabel("-")
            self._range_separator.setStyleSheet(f"""
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.UI};
            """)
            self._range_separator.setVisible(False)
            self._value_layout.addWidget(self._range_separator)

            self._value2_input = QLineEdit()
            self._value2_input.setPlaceholderText(placeholder)
            self._value2_input.setStyleSheet(self._get_input_style())
            self._value2_input.setVisible(False)
            self._value2_input.textChanged.connect(self._on_value_changed)
            self._value2_input.editingFinished.connect(self._on_value2_editing_finished)
            self._value_layout.addWidget(self._value2_input)

            layout.addWidget(self._value_container, stretch=1)

            # Update visibility based on initial operator
            self._update_value_visibility()

        # Remove button (if removable)
        if self._is_removable:
            remove_btn = QPushButton("×")
            remove_btn.setFixedSize(24, 24)
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {Colors.TEXT_SECONDARY};
                    font-family: {Fonts.UI};
                    font-size: 16px;
                    font-weight: bold;
                    border: none;
                    border-radius: 12px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.SIGNAL_CORAL};
                    color: {Colors.TEXT_PRIMARY};
                }}
            """)
            remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))
            layout.addWidget(remove_btn)

        # Store operator for nulls case
        self._current_operator = operator

    def _get_input_style(self) -> str:
        """Get stylesheet for value input fields.

        Returns:
            CSS stylesheet string.
        """
        return f"""
            QLineEdit {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.DATA};
                font-size: 12px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 3px;
                padding: 4px 8px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.SIGNAL_BLUE};
            }}
        """

    def _on_operator_changed(self, index: int) -> None:
        """Handle operator dropdown change.

        Args:
            index: New selected index.
        """
        self._update_value_visibility()
        self.config_changed.emit()

    def _update_value_visibility(self) -> None:
        """Update value input visibility based on selected operator."""
        if not hasattr(self, "_operator_dropdown"):
            return

        is_range = self._operator_dropdown.currentIndex() == 2
        self._range_separator.setVisible(is_range)
        self._value2_input.setVisible(is_range)

    def _on_value_changed(self) -> None:
        """Handle value input change."""
        self.config_changed.emit()

    def _on_value1_editing_finished(self) -> None:
        """Handle value1 input editing finished - format time if applicable."""
        if self._is_time_column and hasattr(self, "_value1_input"):
            self._format_time_input(self._value1_input)

    def _on_value2_editing_finished(self) -> None:
        """Handle value2 input editing finished - format time if applicable."""
        if self._is_time_column and hasattr(self, "_value2_input"):
            self._format_time_input(self._value2_input)

    def _format_time_input(self, line_edit: QLineEdit) -> None:
        """Format time input to HH:MM:SS if valid.

        Args:
            line_edit: The QLineEdit to format.
        """
        text = line_edit.text().strip()
        if not text:
            return

        try:
            formatted = parse_time_input(text)
            # Only update if different to avoid cursor jumping
            if formatted != text:
                line_edit.setText(formatted)
        except ValueError:
            # Leave invalid input for user to correct
            pass

    def get_operator(self) -> str:
        """Get the current operator.

        Returns:
            Operator string ("<", ">", "range", "nulls").
        """
        if hasattr(self, "_current_operator") and self._current_operator == "nulls":
            return "nulls"

        if not hasattr(self, "_operator_dropdown"):
            return "<"

        index = self._operator_dropdown.currentIndex()
        if index == 0:
            return "<"
        elif index == 1:
            return ">"
        else:
            return "range"

    def get_bin_definition(self) -> "BinDefinition":
        """Get the bin definition for this row.

        Returns:
            BinDefinition object representing this row's configuration.
        """
        from src.core.models import BinDefinition

        operator = self.get_operator()

        if operator == "nulls":
            return BinDefinition(operator="nulls", label="Nulls")

        value1 = None
        value2 = None
        label_val1 = ""
        label_val2 = ""

        if hasattr(self, "_value1_input"):
            text = self._value1_input.text().strip()
            if text:
                value1, label_val1 = self._parse_value(text)

        if operator == "range" and hasattr(self, "_value2_input"):
            text = self._value2_input.text().strip()
            if text:
                value2, label_val2 = self._parse_value(text)

        # Generate label
        if operator == "<" and value1 is not None:
            label = f"< {label_val1}"
        elif operator == ">" and value1 is not None:
            label = f"> {label_val1}"
        elif operator == "range" and value1 is not None and value2 is not None:
            label = f"{label_val1} - {label_val2}"
        else:
            label = ""

        return BinDefinition(operator=operator, value1=value1, value2=value2, label=label)

    def _parse_value(self, text: str) -> tuple[float | None, str]:
        """Parse a value from text, handling time format if applicable.

        Args:
            text: The text to parse.

        Returns:
            Tuple of (numeric_value, display_label).
        """
        if self._is_time_column:
            try:
                formatted = parse_time_input(text)
                # Convert back to numeric for binning (HHMMSS format)
                parts = formatted.split(":")
                numeric = int(parts[0]) * 10000 + int(parts[1]) * 100 + int(parts[2])
                return float(numeric), formatted
            except ValueError:
                pass

        # Standard numeric parsing
        try:
            value = float(text)
            return value, self._format_number_label(value)
        except ValueError:
            return None, ""

    def set_values(
        self, value1: float, value2: float | None = None
    ) -> None:
        """Set bin values programmatically.

        Args:
            value1: First value (threshold for <, >, or range start).
            value2: Second value (range end, only for range operator).
        """
        if not hasattr(self, "_value1_input"):
            return

        # Format value for display
        if self._is_time_column:
            # Convert HHMMSS numeric to HH:MM:SS string
            text1 = self._format_time_value(value1)
            self._value1_input.setText(text1)
            if value2 is not None and hasattr(self, "_value2_input"):
                text2 = self._format_time_value(value2)
                self._value2_input.setText(text2)
        else:
            # Format numeric value (remove unnecessary decimals)
            text1 = self._format_numeric_value(value1)
            self._value1_input.setText(text1)
            if value2 is not None and hasattr(self, "_value2_input"):
                text2 = self._format_numeric_value(value2)
                self._value2_input.setText(text2)

        self.config_changed.emit()

    def _format_time_value(self, value: float) -> str:
        """Format HHMMSS numeric to HH:MM:SS string.

        Args:
            value: Time as HHMMSS numeric (e.g., 93000 for 09:30:00).

        Returns:
            Formatted time string (HH:MM:SS).
        """
        int_val = int(value)
        hours = int_val // 10000
        minutes = (int_val // 100) % 100
        seconds = int_val % 100
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _format_numeric_value(self, value: float) -> str:
        """Format numeric value for display.

        Args:
            value: Numeric value.

        Returns:
            Formatted string (integer if whole number, else 2 decimals).
        """
        if value == int(value):
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def _format_number_label(self, value: float) -> str:
        """Format a number with K/M/B abbreviations for bin labels.

        Only abbreviates values >= 100K. Smaller values display normally,
        with 2 decimal places for double-digit values (10-99).

        Args:
            value: Number to format.

        Returns:
            Formatted string with appropriate suffix.
        """
        abs_value = abs(value)
        sign = "-" if value < 0 else ""

        if abs_value >= 1_000_000_000:
            formatted = abs_value / 1_000_000_000
            suffix = "B"
        elif abs_value >= 1_000_000:
            formatted = abs_value / 1_000_000
            suffix = "M"
        elif abs_value >= 100_000:
            formatted = abs_value / 1_000
            suffix = "K"
        else:
            # Values under 100K: show as-is
            if abs_value == int(abs_value):
                return f"{sign}{int(abs_value)}"
            # Double-digit values (10-99): show 2 decimal places
            if 10 <= abs_value < 100:
                return f"{sign}{abs_value:.2f}"
            return f"{sign}{abs_value:.1f}"

        # Format with suffix, removing unnecessary decimals
        rounded = round(formatted, 1)
        if rounded == int(rounded):
            return f"{sign}{int(rounded)}{suffix}"
        return f"{sign}{rounded:.1f}{suffix}"


class HorizontalBarChart(QWidget):
    """Custom horizontal bar chart with labels and gradient coloring.

    Renders a set of horizontal bars with bin labels on the left and
    values on the right. Supports gradient coloring based on value magnitude.
    """

    bar_hovered = pyqtSignal(str, float)  # bin_label, value

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        """Initialize the horizontal bar chart.

        Args:
            title: Chart title displayed above bars.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._title = title
        self._data: list[tuple[str, float]] = []  # (label, value)
        self._bar_height = 24
        self._bar_spacing = 8
        self._label_width = 120
        self._value_width = 80
        self._hovered_index: int | None = None
        self._is_percentage = False
        self._total_count: int | None = None
        self.setMouseTracking(True)
        self._update_height()

    def set_data(
        self,
        data: list[tuple[str, float]],
        is_percentage: bool = False,
        total_count: int | None = None,
    ) -> None:
        """Update chart data and trigger repaint.

        Args:
            data: List of (label, value) tuples.
            is_percentage: Whether values are percentages.
            total_count: Total count for calculating percentages (for count chart).
        """
        self._data = data
        self._is_percentage = is_percentage
        self._total_count = total_count
        self._update_height()
        self.update()

    def _update_height(self) -> None:
        """Update widget height based on data count."""
        title_height = 30 if self._title else 0
        content_height = len(self._data) * (self._bar_height + self._bar_spacing) + 10
        self.setMinimumHeight(max(60, title_height + content_height))
        self.setMaximumHeight(max(60, title_height + content_height))

    def paintEvent(self, event: QPaintEvent) -> None:
        """Render horizontal bars with gradient fills.

        Args:
            event: Paint event.
        """
        from PyQt6.QtCore import QRectF
        from PyQt6.QtGui import QFont, QPainter

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        y_offset = 0

        # Draw title
        if self._title:
            title_font = QFont(Fonts.UI, 11)
            title_font.setBold(True)
            painter.setFont(title_font)
            painter.setPen(QColor(Colors.TEXT_SECONDARY))
            painter.drawText(0, 18, self._title)
            y_offset = 30

        if not self._data:
            return

        # Calculate min/max for gradient
        values = [v for _, v in self._data if v is not None]
        if not values:
            return
        min_val = min(values)
        max_val = max(values)

        # Draw bars
        bar_area_width = width - self._label_width - self._value_width - 20
        label_font = QFont(Fonts.UI, 10)
        value_font = QFont(Fonts.DATA, 10)

        for i, (label, value) in enumerate(self._data):
            y = y_offset + i * (self._bar_height + self._bar_spacing)

            # Draw label
            painter.setFont(label_font)
            painter.setPen(QColor(Colors.TEXT_PRIMARY))
            label_rect = QRectF(0, y, self._label_width - 5, self._bar_height)
            painter.drawText(
                label_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                label[:15] + "..." if len(label) > 15 else label,
            )

            if value is None:
                continue

            # Calculate bar width (normalized 0-1)
            if max_val == min_val:
                normalized = 0.5
            elif min_val >= 0:
                normalized = value / max_val if max_val > 0 else 0
            else:
                # Handle negative values
                range_val = max_val - min_val
                normalized = (value - min_val) / range_val if range_val > 0 else 0

            bar_width = max(2, int(bar_area_width * normalized))

            # Calculate gradient color
            bar_color = self._calculate_gradient_color(value, min_val, max_val)

            # Draw bar background
            bar_x = self._label_width
            bar_rect = QRectF(bar_x, y + 2, bar_width, self._bar_height - 4)

            # Highlight on hover
            if i == self._hovered_index:
                painter.fillRect(
                    QRectF(bar_x - 5, y, bar_area_width + 10, self._bar_height),
                    QColor(Colors.BG_ELEVATED),
                )

            painter.fillRect(bar_rect, bar_color)

            # Draw value
            painter.setFont(value_font)
            painter.setPen(QColor(Colors.TEXT_PRIMARY))
            value_rect = QRectF(
                self._label_width + bar_area_width + 5,
                y,
                self._value_width,
                self._bar_height,
            )
            value_text = self._format_value(value)
            painter.drawText(
                value_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                value_text,
            )

        painter.end()

    def _calculate_gradient_color(
        self,
        value: float,
        min_val: float,
        max_val: float,
    ) -> QColor:
        """Calculate bar color using brightness interpolation.

        Higher values = brighter, lower values = darker.
        No alpha transparency - solid colors for cleaner appearance.

        Args:
            value: Current value.
            min_val: Minimum value in dataset.
            max_val: Maximum value in dataset.

        Returns:
            QColor with brightness based on value magnitude.
        """
        # Define dark (low value) and bright (high value) color endpoints
        if value < 0:
            # Coral range: dark muted to full bright
            dark_color = QColor(74, 26, 31)      # ~20% brightness coral
            bright_color = QColor(255, 71, 87)   # Full coral (#FF4757)
        else:
            # Cyan range: dark muted to full bright
            dark_color = QColor(10, 61, 61)      # ~20% brightness cyan
            bright_color = QColor(0, 255, 212)   # Full cyan (#00FFD4)

        # Normalize value to 0-1 range (0 = lowest magnitude, 1 = highest)
        if max_val == min_val:
            t = 0.7  # Default to moderately bright if all values equal
        else:
            abs_max = max(abs(min_val), abs(max_val))
            t = abs(value) / abs_max if abs_max > 0 else 0
            t = 0.25 + (t * 0.75)  # Map to 0.25-1.0 range (never fully dark)

        # Linear interpolation between dark and bright colors
        r = int(dark_color.red() + t * (bright_color.red() - dark_color.red()))
        g = int(dark_color.green() + t * (bright_color.green() - dark_color.green()))
        b = int(dark_color.blue() + t * (bright_color.blue() - dark_color.blue()))

        return QColor(r, g, b)  # Fully opaque, no alpha

    def _format_value(self, value: float) -> str:
        """Format a number with K/M/B abbreviations for readability.

        Args:
            value: Value to format.

        Returns:
            Formatted string with appropriate suffix.
        """
        if value is None:
            return "N/A"

        if self._is_percentage:
            return f"{value:.2f}%"

        abs_value = abs(value)
        sign = "-" if value < 0 else ""

        if abs_value >= 1_000_000_000:
            formatted = abs_value / 1_000_000_000
            suffix = "B"
        elif abs_value >= 1_000_000:
            formatted = abs_value / 1_000_000
            suffix = "M"
        elif abs_value >= 1_000:
            formatted = abs_value / 1_000
            suffix = "K"
        else:
            # Small numbers: show as-is with reasonable precision
            if abs_value == 0:
                return "0"
            elif abs_value < 0.01:
                return f"{sign}{abs_value:.4f}"
            elif abs_value < 1:
                # Remove trailing zeros for decimals < 1
                formatted_str = f"{abs_value:.2f}".rstrip("0").rstrip(".")
                return f"{sign}{formatted_str}"
            else:
                if abs_value != int(abs_value):
                    return f"{sign}{abs_value:.1f}"
                else:
                    return f"{sign}{int(abs_value)}"

        # Format with suffix, removing unnecessary decimals
        # Use rounding to handle floating point precision issues
        rounded = round(formatted, 2)
        if rounded == int(rounded):
            return f"{sign}{int(rounded)}{suffix}"
        elif round(rounded * 10) == rounded * 10:
            return f"{sign}{rounded:.1f}{suffix}"
        else:
            return f"{sign}{rounded:.2f}{suffix}"

    def mouseMoveEvent(self, event: "QMouseEvent") -> None:
        """Handle mouse move for hover effect and tooltip.

        Args:
            event: Mouse event.
        """
        y = event.position().y()
        title_height = 30 if self._title else 0

        if y < title_height:
            new_index = None
        else:
            index = int((y - title_height) / (self._bar_height + self._bar_spacing))
            new_index = index if 0 <= index < len(self._data) else None

        if new_index != self._hovered_index:
            self._hovered_index = new_index
            self.update()

            if new_index is not None and new_index < len(self._data):
                label, value = self._data[new_index]
                self.bar_hovered.emit(label, value if value is not None else 0)

                # Show tooltip
                tooltip_text = self.get_tooltip_text(new_index)
                global_pos = self.mapToGlobal(QPoint(int(event.position().x()), int(y)))
                QToolTip.showText(global_pos, tooltip_text, self)
            else:
                QToolTip.hideText()

    def leaveEvent(self, event: "QEvent") -> None:
        """Handle mouse leave.

        Args:
            event: Leave event.
        """
        self._hovered_index = None
        self.update()

    def get_tooltip_text(self, index: int) -> str:
        """Get tooltip text for a bar at given index.

        Args:
            index: Bar index.

        Returns:
            Formatted tooltip text.
        """
        if index < 0 or index >= len(self._data):
            return ""

        label, value = self._data[index]
        if value is None:
            return f"{label}: No data"

        text = f"{label}: {self._format_value(value)}"

        # Add percentage of total for count charts
        if self._total_count and not self._is_percentage:
            pct = (value / self._total_count * 100) if self._total_count > 0 else 0
            text += f" ({pct:.1f}% of total)"

        return text


class BinChartPanel(QWidget):
    """Panel displaying bin metrics as horizontal bar charts.

    Shows 4 chart sections: Average, Median, Count, and Win Rate.
    Includes a toggle for switching between gain_pct and adjusted_gain_pct.
    """

    metric_toggled = pyqtSignal(str)  # metric_column name

    def __init__(self, app_state: "AppState", parent: QWidget | None = None) -> None:
        """Initialize the chart panel.

        Args:
            app_state: Centralized application state.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._app_state = app_state
        self._current_metric_column = "adjusted_gain_pct"
        self._bin_definitions: list[BinDefinition] = []
        self._selected_column: str = ""
        self._cumulative_mode = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the chart panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # Header with toggle
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        header_label = QLabel("Bin Analysis")
        header_label.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-family: {Fonts.UI};
            font-size: 14px;
            font-weight: bold;
        """)
        header_layout.addWidget(header_label)

        header_layout.addStretch()

        # Metric toggle
        toggle_container = QWidget()
        toggle_layout = QHBoxLayout(toggle_container)
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        toggle_layout.setSpacing(Spacing.SM)

        self._gain_btn = QPushButton("gain_pct")
        self._gain_btn.setCheckable(True)
        self._gain_btn.setStyleSheet(self._get_toggle_style())
        self._gain_btn.clicked.connect(lambda: self._on_metric_toggle("gain_pct"))
        toggle_layout.addWidget(self._gain_btn)

        self._adjusted_btn = QPushButton("adjusted_gain_pct")
        self._adjusted_btn.setCheckable(True)
        self._adjusted_btn.setChecked(True)
        self._adjusted_btn.setStyleSheet(self._get_toggle_style())
        self._adjusted_btn.clicked.connect(
            lambda: self._on_metric_toggle("adjusted_gain_pct")
        )
        toggle_layout.addWidget(self._adjusted_btn)

        header_layout.addWidget(toggle_container)
        layout.addWidget(header)

        # Scrollable chart area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
        """)

        self._chart_container = QWidget()
        self._chart_layout = QVBoxLayout(self._chart_container)
        self._chart_layout.setContentsMargins(0, 0, 0, 0)
        self._chart_layout.setSpacing(Spacing.LG)

        # Create 5 chart sections
        self._average_chart = HorizontalBarChart("Average")
        self._median_chart = HorizontalBarChart("Median")
        self._count_chart = HorizontalBarChart("Count")
        self._win_rate_chart = HorizontalBarChart("Win Rate")

        self._chart_layout.addWidget(self._average_chart)
        self._chart_layout.addWidget(self._median_chart)
        self._chart_layout.addWidget(self._count_chart)
        self._chart_layout.addWidget(self._win_rate_chart)

        # % of Total Gains with cumulative toggle
        pct_total_section = self._create_pct_total_section()
        self._chart_layout.addWidget(pct_total_section)

        self._chart_layout.addStretch()

        scroll_area.setWidget(self._chart_container)
        layout.addWidget(scroll_area, stretch=1)

        # Empty state overlay
        self._empty_state = EmptyState()
        self._empty_state.set_message(
            icon="📊",
            title="No Bins Configured",
            description="Add bin definitions in the sidebar to see analysis charts",
        )
        layout.addWidget(self._empty_state)

        # Initially show empty state
        self._chart_container.hide()
        self._empty_state.show()

    def _get_toggle_style(self) -> str:
        """Get stylesheet for toggle buttons.

        Returns:
            CSS stylesheet string.
        """
        return f"""
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.DATA};
                font-size: 11px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QPushButton:checked {{
                background-color: {Colors.SIGNAL_BLUE};
                color: {Colors.TEXT_PRIMARY};
                border-color: {Colors.SIGNAL_BLUE};
            }}
            QPushButton:hover {{
                border-color: {Colors.TEXT_SECONDARY};
            }}
        """

    def _create_pct_total_section(self) -> QWidget:
        """Create the % of Total Gains chart with cumulative toggle."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header with title and toggle
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 4)

        title = QLabel("% of Total Gains")
        title.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-family: {Fonts.UI};
            font-size: 11px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
        """)
        header.addWidget(title)
        header.addStretch()

        # Cumulative toggle
        toggle_container = QFrame()
        toggle_container.setStyleSheet(f"""
            QFrame {{
                background: {Colors.BG_ELEVATED};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 6px;
            }}
        """)
        toggle_layout = QHBoxLayout(toggle_container)
        toggle_layout.setContentsMargins(4, 4, 4, 4)
        toggle_layout.setSpacing(4)

        self._abs_btn = QPushButton("Absolute")
        self._cum_btn = QPushButton("Cumulative")

        for btn in [self._abs_btn, self._cum_btn]:
            btn.setMinimumWidth(85)
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self._abs_btn.clicked.connect(lambda: self._set_cumulative_mode(False))
        self._cum_btn.clicked.connect(lambda: self._set_cumulative_mode(True))

        toggle_layout.addWidget(self._abs_btn)
        toggle_layout.addWidget(self._cum_btn)
        header.addWidget(toggle_container)

        layout.addLayout(header)

        # Chart (without title since we have custom header)
        self._pct_total_chart = HorizontalBarChart()  # No title in constructor
        layout.addWidget(self._pct_total_chart)

        # Initialize toggle styles
        self._update_toggle_styles()

        return container

    def _set_cumulative_mode(self, cumulative: bool) -> None:
        """Switch between absolute and cumulative display modes."""
        self._cumulative_mode = cumulative
        self._update_toggle_styles()
        self._recalculate_charts()

    def _update_toggle_styles(self) -> None:
        """Update toggle button visual states."""
        active_style = f"""
            QPushButton {{
                background: {Colors.SIGNAL_CYAN};
                color: {Colors.BG_BASE};
                border: none;
                border-radius: 4px;
                font-family: {Fonts.UI};
                font-size: 12px;
                font-weight: 600;
            }}
        """
        inactive_style = f"""
            QPushButton {{
                background: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                font-family: {Fonts.UI};
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {Colors.BG_BORDER};
                color: {Colors.TEXT_PRIMARY};
            }}
        """

        if self._cumulative_mode:
            self._cum_btn.setStyleSheet(active_style)
            self._abs_btn.setStyleSheet(inactive_style)
        else:
            self._abs_btn.setStyleSheet(active_style)
            self._cum_btn.setStyleSheet(inactive_style)

    def _on_metric_toggle(self, metric: str) -> None:
        """Handle metric toggle button click.

        Args:
            metric: Selected metric column name.
        """
        self._current_metric_column = metric
        self._gain_btn.setChecked(metric == "gain_pct")
        self._adjusted_btn.setChecked(metric == "adjusted_gain_pct")
        self.metric_toggled.emit(metric)
        self._recalculate_charts()

    def update_charts(
        self,
        column: str,
        bin_definitions: list["BinDefinition"],
    ) -> None:
        """Update charts with new bin configuration.

        Args:
            column: Column name being binned.
            bin_definitions: List of bin definitions.
        """
        self._selected_column = column
        self._bin_definitions = bin_definitions
        self._recalculate_charts()

    def _recalculate_charts(self) -> None:
        """Recalculate and render all charts."""
        from src.core.binning_engine import BinningEngine

        df = self._app_state.baseline_df
        if df is None or df.empty:
            self._show_empty_state("No Data Loaded", "Load trade data to begin analysis")
            return

        # Filter to first triggers only for accurate analysis
        # This matches the pattern used in PnL Stats and Data Input tabs
        if "trigger_number" in df.columns:
            df = df[df["trigger_number"] == 1].copy()

        if not self._selected_column:
            self._show_empty_state(
                "Select a Column", "Choose a numeric column to configure bins"
            )
            return

        if not self._bin_definitions:
            self._show_empty_state(
                "No Bins Configured",
                "Add bin definitions in the sidebar to see analysis charts",
            )
            return

        # Check metric column exists
        if self._current_metric_column not in df.columns:
            # Fall back to gain_pct if adjusted not available
            if "gain_pct" in df.columns:
                self._current_metric_column = "gain_pct"
                self._gain_btn.setChecked(True)
                self._adjusted_btn.setChecked(False)
            else:
                self._show_empty_state(
                    "No Metric Column",
                    "Dataset must contain gain_pct or adjusted_gain_pct column",
                )
                return

        # Run binning engine
        engine = BinningEngine()
        try:
            bin_labels = engine.assign_bins(df, self._selected_column, self._bin_definitions)
            metrics = engine.calculate_bin_metrics(df, bin_labels, self._current_metric_column)
        except Exception as e:
            logger.exception("Error calculating bin metrics")
            self._show_empty_state("Calculation Error", str(e))
            return

        if not metrics:
            self._show_empty_state(
                "No Matching Data",
                "All rows fell outside defined bin ranges. Adjust bin thresholds.",
            )
            return

        # Prepare chart data (preserve bin order)
        ordered_labels = []
        for bin_def in self._bin_definitions:
            label = bin_def.label or engine._generate_label(bin_def)
            if label in metrics:
                ordered_labels.append(label)

        # Add Uncategorized if present
        if engine.UNCATEGORIZED in metrics:
            ordered_labels.append(engine.UNCATEGORIZED)

        total_count = sum(m.count for m in metrics.values())

        average_data = [(label, metrics[label].average) for label in ordered_labels]
        median_data = [(label, metrics[label].median) for label in ordered_labels]
        count_data = [
            (label, float(metrics[label].count)) for label in ordered_labels
        ]
        win_rate_data = [(label, metrics[label].win_rate) for label in ordered_labels]

        # Calculate % of Total Gains (absolute)
        total_all_gains = sum(
            metrics[label].total_gain
            for label in ordered_labels
            if metrics[label].total_gain is not None
        )

        if total_all_gains != 0:
            pct_values = [
                (metrics[label].total_gain / total_all_gains) * 100
                for label in ordered_labels
                if metrics[label].total_gain is not None
            ]
        else:
            pct_values = [0.0 for _ in ordered_labels]

        # Apply cumulative if enabled
        if self._cumulative_mode:
            cumulative_values = []
            running_total = 0.0
            for pct in pct_values:
                running_total += pct
                cumulative_values.append(running_total)
            pct_values = cumulative_values

        pct_total_data = list(zip(ordered_labels, pct_values, strict=False))

        # Update charts
        self._average_chart.set_data(average_data, is_percentage=False)
        self._median_chart.set_data(median_data, is_percentage=False)
        self._count_chart.set_data(count_data, total_count=total_count)
        self._win_rate_chart.set_data(win_rate_data, is_percentage=True)
        self._pct_total_chart.set_data(pct_total_data, is_percentage=True)

        # Show charts, hide empty state
        self._empty_state.hide()
        self._chart_container.show()

    def _show_empty_state(self, title: str, description: str) -> None:
        """Show empty state with message.

        Args:
            title: Empty state title.
            description: Empty state description.
        """
        self._empty_state.set_message(icon="📊", title=title, description=description)
        self._chart_container.hide()
        self._empty_state.show()

    def set_metric_column(self, column: str) -> None:
        """Set the metric column for calculations.

        Args:
            column: Metric column name (gain_pct or adjusted_gain_pct).
        """
        if column in ("gain_pct", "adjusted_gain_pct"):
            self._current_metric_column = column
            self._gain_btn.setChecked(column == "gain_pct")
            self._adjusted_btn.setChecked(column == "adjusted_gain_pct")
