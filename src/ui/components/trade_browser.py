"""TradeBrowser widget for displaying and navigating filtered trades."""

import pandas as pd
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.constants import Colors, Fonts, Spacing


class TradeBrowser(QWidget):
    """Widget for browsing and selecting trades from a filtered list.

    Displays trades in a list with Prev/Next navigation buttons.
    Emits trade_selected signal when a trade is selected.

    Attributes:
        trade_selected: Signal emitted when a trade is selected, passes trade dict.
        trade_list: QListWidget showing the trades.
    """

    trade_selected = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize TradeBrowser.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._trades_df: pd.DataFrame | None = None
        self._setup_ui()
        self._apply_style()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the widget UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(Spacing.SM)

        # Trade list
        self.trade_list = QListWidget()
        self.trade_list.setObjectName("tradeList")
        layout.addWidget(self.trade_list)

        # Navigation buttons
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(Spacing.SM)

        self._prev_btn = QPushButton("Prev")
        self._prev_btn.setObjectName("prevBtn")
        self._prev_btn.setEnabled(False)
        nav_layout.addWidget(self._prev_btn)

        self._next_btn = QPushButton("Next")
        self._next_btn.setObjectName("nextBtn")
        self._next_btn.setEnabled(False)
        nav_layout.addWidget(self._next_btn)

        layout.addLayout(nav_layout)

    def _apply_style(self) -> None:
        """Apply Observatory theme styling."""
        self.setStyleSheet(f"""
            TradeBrowser {{
                background-color: {Colors.BG_SURFACE};
            }}
            QListWidget#tradeList {{
                background-color: {Colors.BG_ELEVATED};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.DATA};
                font-size: 13px;
            }}
            QListWidget#tradeList::item {{
                padding: {Spacing.XS}px {Spacing.SM}px;
            }}
            QListWidget#tradeList::item:selected {{
                background-color: {Colors.SIGNAL_BLUE};
                color: {Colors.BG_BASE};
            }}
            QListWidget#tradeList::item:hover {{
                background-color: {Colors.BG_BORDER};
            }}
            QPushButton {{
                background-color: {Colors.BG_ELEVATED};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.UI};
                font-size: 12px;
                padding: {Spacing.XS}px {Spacing.MD}px;
                min-width: 60px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_BORDER};
            }}
            QPushButton:disabled {{
                color: {Colors.TEXT_DISABLED};
            }}
        """)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.trade_list.currentRowChanged.connect(self._on_row_changed)
        self._prev_btn.clicked.connect(self._on_prev)
        self._next_btn.clicked.connect(self._on_next)

    def set_trades(self, df: pd.DataFrame) -> None:
        """Populate the list from DataFrame.

        Args:
            df: DataFrame with trade data. Expected columns:
                - ticker: str
                - entry_time: datetime
                - entry_price: float
                - date: datetime
                - pnl_pct: float
        """
        self._trades_df = df
        self.trade_list.clear()

        if df.empty:
            self._update_button_states()
            return

        for _, row in df.iterrows():
            # Format as "TICKER HH:MM"
            entry_time = row["entry_time"]
            time_str = entry_time.strftime("%H:%M")
            text = f"{row['ticker']} {time_str}"

            item = QListWidgetItem(text)
            self.trade_list.addItem(item)

        self._update_button_states()

    def _on_row_changed(self, row: int) -> None:
        """Handle row selection change.

        Args:
            row: The newly selected row index.
        """
        self._update_button_states()

        if row >= 0 and self._trades_df is not None and row < len(self._trades_df):
            trade_row = self._trades_df.iloc[row]
            trade_dict = trade_row.to_dict()
            self.trade_selected.emit(trade_dict)

    def _on_prev(self) -> None:
        """Handle Prev button click."""
        current = self.trade_list.currentRow()
        if current > 0:
            self.trade_list.setCurrentRow(current - 1)

    def _on_next(self) -> None:
        """Handle Next button click."""
        current = self.trade_list.currentRow()
        if current < self.trade_list.count() - 1:
            self.trade_list.setCurrentRow(current + 1)

    def _update_button_states(self) -> None:
        """Update Prev/Next button enabled states based on current selection."""
        current = self.trade_list.currentRow()
        count = self.trade_list.count()

        # Prev enabled if not at first item
        self._prev_btn.setEnabled(current > 0)

        # Next enabled if not at last item
        self._next_btn.setEnabled(current >= 0 and current < count - 1)
