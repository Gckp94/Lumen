"""Fullscreen chart expansion dialog.

Provides a modal dialog for viewing charts at full screen or maximized size.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.constants import Colors, Fonts, Spacing

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ChartExpandDialog(QDialog):
    """Modal dialog for displaying charts at full size.

    Provides maximized or fullscreen viewing of chart widgets with
    keyboard shortcuts for navigation and closing.

    Attributes:
        _chart_widget: The chart widget being displayed.
        _is_fullscreen: Whether currently in fullscreen mode.
    """

    def __init__(
        self,
        chart_widget: QWidget,
        title: str = "Chart View",
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the ChartExpandDialog.

        Args:
            chart_widget: The chart widget to display.
            title: Dialog window title.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._chart_widget = chart_widget
        self._is_fullscreen = False
        self._original_parent = chart_widget.parent()

        self.setWindowTitle(title)
        self.setMinimumSize(800, 600)
        self.resize(1200, 800)

        # Modal dialog settings
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )

        self._setup_ui()
        self._setup_styling()

    def _setup_ui(self) -> None:
        """Set up the dialog layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.SM)

        # Chart container - takes the chart widget temporarily
        self._chart_container = QWidget()
        chart_layout = QVBoxLayout(self._chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.addWidget(self._chart_widget)
        layout.addWidget(self._chart_container, stretch=1)

        # Button row
        button_layout = QHBoxLayout()
        button_layout.setSpacing(Spacing.MD)

        # Fullscreen toggle button
        self._fullscreen_btn = QPushButton("Fullscreen (F11)")
        self._fullscreen_btn.setFixedWidth(140)
        self._fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        button_layout.addWidget(self._fullscreen_btn)

        button_layout.addStretch()

        # Close button
        self._close_btn = QPushButton("Close (Esc)")
        self._close_btn.setFixedWidth(120)
        self._close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self._close_btn)

        layout.addLayout(button_layout)

    def _setup_styling(self) -> None:
        """Apply Observatory theme styling."""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_ELEVATED};
            }}
            QPushButton {{
                background-color: {Colors.BG_BORDER};
                color: {Colors.TEXT_PRIMARY};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-family: {Fonts.UI};
            }}
            QPushButton:hover {{
                background-color: {Colors.SIGNAL_BLUE};
            }}
            QPushButton:pressed {{
                background-color: {Colors.BG_SURFACE};
            }}
        """)

    def _toggle_fullscreen(self) -> None:
        """Toggle between normal and fullscreen mode."""
        if self._is_fullscreen:
            self.showNormal()
            self._fullscreen_btn.setText("Fullscreen (F11)")
            self._is_fullscreen = False
        else:
            self.showFullScreen()
            self._fullscreen_btn.setText("Exit Fullscreen (F11)")
            self._is_fullscreen = True

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        """Handle keyboard shortcuts.

        Args:
            event: The key press event.
        """
        if event is None:
            return

        key = event.key()

        # Escape: close dialog
        if key == Qt.Key.Key_Escape:
            self.accept()
        # F11: toggle fullscreen
        elif key == Qt.Key.Key_F11:
            self._toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        """Handle dialog close - return chart to original parent.

        Args:
            event: The close event.
        """
        # Return the chart widget to its original parent
        if self._original_parent is not None:
            self._chart_widget.setParent(self._original_parent)
        super().closeEvent(event)

    def reject(self) -> None:
        """Handle dialog rejection (close button or Escape)."""
        # Return the chart widget to its original parent
        if self._original_parent is not None:
            self._chart_widget.setParent(self._original_parent)
        super().reject()

    def accept(self) -> None:
        """Handle dialog acceptance."""
        # Return the chart widget to its original parent
        if self._original_parent is not None:
            self._chart_widget.setParent(self._original_parent)
        super().accept()
