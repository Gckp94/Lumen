"""Statistics tab with 5 analytical tables for trade analysis."""

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.app_state import AppState
from src.ui.constants import Colors, Fonts, Spacing


class StatisticsTab(QWidget):
    """Tab displaying 5 statistics tables as sub-tabs."""

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._app_state = app_state
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the tab UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Sub-tabs using QTabWidget
        self._tab_widget = QTabWidget()
        self._style_tab_widget()

        # Create 5 sub-tabs
        self._mae_table = self._create_table()
        self._mfe_table = self._create_table()
        self._stop_loss_table = self._create_table()
        self._offset_table = self._create_table()
        self._scaling_widget = self._create_scaling_widget()

        self._tab_widget.addTab(self._mae_table, "MAE Before Win")
        self._tab_widget.addTab(self._mfe_table, "MFE Before Loss")
        self._tab_widget.addTab(self._stop_loss_table, "Stop Loss")
        self._tab_widget.addTab(self._offset_table, "Offset")
        self._tab_widget.addTab(self._scaling_widget, "Scaling")

        layout.addWidget(self._tab_widget)

    def _style_tab_widget(self) -> None:
        """Apply Observatory theme styling to tab widget."""
        self._tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                background-color: {Colors.BG_SURFACE};
                border: none;
            }}
            QTabBar::tab {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_SECONDARY};
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {Colors.BG_BORDER};
            }}
        """)

    def _create_table(self) -> QTableWidget:
        """Create a styled table widget."""
        table = QTableWidget()
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                gridline-color: {Colors.BG_BORDER};
                border: none;
                font-family: '{Fonts.DATA}';
            }}
            QHeaderView::section {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_SECONDARY};
                padding: 8px;
                border: none;
                font-weight: 600;
            }}
            QTableWidget::item {{
                padding: 8px;
            }}
        """)
        return table

    def _create_scaling_widget(self) -> QWidget:
        """Create scaling sub-tab with spinbox control."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # Scale Out control row
        control_row = QHBoxLayout()
        control_row.setSpacing(Spacing.SM)

        label = QLabel("Scale Out:")
        label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: 13px;
            }}
        """)
        control_row.addWidget(label)

        self._scale_out_spin = QSpinBox()
        self._scale_out_spin.setRange(10, 90)
        self._scale_out_spin.setValue(50)
        self._scale_out_spin.setSingleStep(10)
        self._scale_out_spin.setSuffix("%")
        self._scale_out_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.DATA}';
                padding: 6px 12px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
            }}
            QSpinBox:focus {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
        """)
        control_row.addWidget(self._scale_out_spin)
        control_row.addStretch()

        layout.addLayout(control_row)

        # Scaling table
        self._scaling_table = self._create_table()
        layout.addWidget(self._scaling_table)

        return widget

    def _connect_signals(self) -> None:
        """Connect app state signals."""
        pass  # Will be implemented in later task
