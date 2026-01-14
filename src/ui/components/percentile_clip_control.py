"""Percentile clip control widget for outlier handling."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.constants import Colors, Spacing


class PercentileClipControl(QWidget):
    """Control for clipping axis bounds to percentiles.

    Provides preset percentile options (95%, 99%, 99.9%) and a clip button.
    Also includes a "Smart Auto-Fit" button that uses IQR-based detection.

    Signals:
        clip_requested: Emitted when Clip button clicked (percentile: float).
        smart_auto_fit_requested: Emitted when Smart Auto-Fit clicked.
    """

    clip_requested = pyqtSignal(float)
    smart_auto_fit_requested = pyqtSignal()

    # Preset percentiles: (display_text, value)
    PRESETS = [
        ("95%", 95.0),
        ("99%", 99.0),
        ("99.9%", 99.9),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the PercentileClipControl.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._setup_ui()
        self._apply_style()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the control layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, Spacing.SM, 0, 0)
        layout.setSpacing(Spacing.XS)

        # Section label
        section_label = QLabel("Clip Outliers")
        section_label.setObjectName("sectionLabel")
        layout.addWidget(section_label)

        # Percentile row: combo + clip button
        percentile_row = QHBoxLayout()
        percentile_row.setSpacing(Spacing.XS)

        self._combo = QComboBox()
        for text, _ in self.PRESETS:
            self._combo.addItem(text)
        self._combo.setCurrentIndex(1)  # Default to 99%
        self._combo.setFixedWidth(70)
        percentile_row.addWidget(self._combo)

        self._clip_btn = QPushButton("Clip")
        self._clip_btn.setFixedWidth(50)
        self._clip_btn.setToolTip("Set axis bounds to selected percentile")
        percentile_row.addWidget(self._clip_btn)

        self._smart_btn = QPushButton("Smart")
        self._smart_btn.setFixedWidth(55)
        self._smart_btn.setToolTip("Auto-fit using IQR-based outlier detection")
        percentile_row.addWidget(self._smart_btn)

        percentile_row.addStretch()
        layout.addLayout(percentile_row)

        # Clipped indicator
        self._indicator = QLabel("")
        self._indicator.setObjectName("clippedIndicator")
        layout.addWidget(self._indicator)

    def _apply_style(self) -> None:
        """Apply Observatory theme styling."""
        self.setStyleSheet(f"""
            QLabel#sectionLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-size: 12px;
                font-weight: bold;
            }}
            QLabel#clippedIndicator {{
                color: {Colors.SIGNAL_AMBER};
                font-size: 11px;
            }}
            QComboBox {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QComboBox:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {Colors.TEXT_SECONDARY};
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                selection-background-color: {Colors.BG_BORDER};
            }}
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                padding: {Spacing.XS}px {Spacing.SM}px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_BORDER};
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QPushButton:pressed {{
                background-color: {Colors.BG_SURFACE};
            }}
        """)

    def _connect_signals(self) -> None:
        """Connect button signals."""
        self._clip_btn.clicked.connect(self._on_clip_clicked)
        self._smart_btn.clicked.connect(self.smart_auto_fit_requested.emit)

    def _on_clip_clicked(self) -> None:
        """Handle clip button click."""
        self.clip_requested.emit(self.selected_percentile)

    @property
    def selected_percentile(self) -> float:
        """Get currently selected percentile value."""
        index = self._combo.currentIndex()
        if 0 <= index < len(self.PRESETS):
            return self.PRESETS[index][1]
        return 99.0  # Fallback

    def set_clipped_state(
        self, is_clipped: bool, percentile: float | None = None
    ) -> None:
        """Update visual indicator for clipped state.

        Args:
            is_clipped: Whether bounds are currently clipped.
            percentile: The percentile used for clipping (if clipped).
        """
        if is_clipped and percentile is not None:
            self._indicator.setText(f"Clipped to {percentile}%")
        else:
            self._indicator.setText("")
