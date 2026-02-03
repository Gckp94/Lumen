"""Unit tests for TradeBrowser widget."""

import pandas as pd
import pytest
from PyQt6.QtCore import Qt

from src.ui.components.trade_browser import TradeBrowser


class TestTradeBrowserInitialization:
    """Tests for TradeBrowser initialization."""

    def test_creates_trade_list(self, qtbot):
        """Widget creates a QListWidget for trades."""
        browser = TradeBrowser()
        qtbot.addWidget(browser)

        assert browser.trade_list is not None

    def test_creates_prev_button(self, qtbot):
        """Widget creates a Prev navigation button."""
        browser = TradeBrowser()
        qtbot.addWidget(browser)

        assert browser._prev_btn is not None
        assert browser._prev_btn.text() == "Prev"

    def test_creates_next_button(self, qtbot):
        """Widget creates a Next navigation button."""
        browser = TradeBrowser()
        qtbot.addWidget(browser)

        assert browser._next_btn is not None
        assert browser._next_btn.text() == "Next"

    def test_buttons_disabled_when_empty(self, qtbot):
        """Prev/Next buttons are disabled when no trades loaded."""
        browser = TradeBrowser()
        qtbot.addWidget(browser)

        assert browser._prev_btn.isEnabled() is False
        assert browser._next_btn.isEnabled() is False

    def test_trade_list_empty_initially(self, qtbot):
        """Trade list is empty initially."""
        browser = TradeBrowser()
        qtbot.addWidget(browser)

        assert browser.trade_list.count() == 0


class TestTradeBrowserSignals:
    """Tests for TradeBrowser signals."""

    def test_has_trade_selected_signal(self, qtbot):
        """Widget has trade_selected signal."""
        browser = TradeBrowser()
        qtbot.addWidget(browser)

        assert hasattr(browser, "trade_selected")

    def test_clicking_item_emits_trade_selected(self, qtbot):
        """Clicking a trade item emits trade_selected signal with trade dict."""
        browser = TradeBrowser()
        qtbot.addWidget(browser)

        df = pd.DataFrame({
            "ticker": ["AAPL"],
            "entry_time": pd.to_datetime(["2024-01-15 09:32:00"]),
            "entry_price": [150.0],
            "date": pd.to_datetime(["2024-01-15"]),
            "pnl_pct": [1.5],
        })
        browser.set_trades(df)

        signal_received = []
        browser.trade_selected.connect(lambda t: signal_received.append(t))

        # Click the first item
        browser.trade_list.setCurrentRow(0)

        assert len(signal_received) == 1
        assert signal_received[0]["ticker"] == "AAPL"
        assert signal_received[0]["entry_price"] == 150.0
        assert signal_received[0]["pnl_pct"] == 1.5


class TestTradeBrowserSetTrades:
    """Tests for TradeBrowser.set_trades() method."""

    def test_set_trades_populates_list(self, qtbot):
        """set_trades() populates the list widget."""
        browser = TradeBrowser()
        qtbot.addWidget(browser)

        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL", "MSFT"],
            "entry_time": pd.to_datetime([
                "2024-01-15 09:32:00",
                "2024-01-15 10:15:00",
                "2024-01-15 11:45:00",
            ]),
            "entry_price": [150.0, 140.0, 380.0],
            "date": pd.to_datetime(["2024-01-15", "2024-01-15", "2024-01-15"]),
            "pnl_pct": [1.5, -0.8, 2.1],
        })
        browser.set_trades(df)

        assert browser.trade_list.count() == 3

    def test_set_trades_formats_items_correctly(self, qtbot):
        """set_trades() formats items as 'TICKER HH:MM'."""
        browser = TradeBrowser()
        qtbot.addWidget(browser)

        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL"],
            "entry_time": pd.to_datetime([
                "2024-01-15 09:32:00",
                "2024-01-15 14:05:00",
            ]),
            "entry_price": [150.0, 140.0],
            "date": pd.to_datetime(["2024-01-15", "2024-01-15"]),
            "pnl_pct": [1.5, -0.8],
        })
        browser.set_trades(df)

        assert browser.trade_list.item(0).text() == "AAPL 09:32"
        assert browser.trade_list.item(1).text() == "GOOGL 14:05"

    def test_set_trades_enables_buttons(self, qtbot):
        """set_trades() enables navigation buttons when trades loaded."""
        browser = TradeBrowser()
        qtbot.addWidget(browser)

        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL"],
            "entry_time": pd.to_datetime([
                "2024-01-15 09:32:00",
                "2024-01-15 10:15:00",
            ]),
            "entry_price": [150.0, 140.0],
            "date": pd.to_datetime(["2024-01-15", "2024-01-15"]),
            "pnl_pct": [1.5, -0.8],
        })
        browser.set_trades(df)

        # Select first item
        browser.trade_list.setCurrentRow(0)

        # Prev should be disabled (at start), Next should be enabled
        assert browser._prev_btn.isEnabled() is False
        assert browser._next_btn.isEnabled() is True

    def test_set_trades_clears_previous(self, qtbot):
        """set_trades() clears previous trades before adding new ones."""
        browser = TradeBrowser()
        qtbot.addWidget(browser)

        df1 = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL"],
            "entry_time": pd.to_datetime([
                "2024-01-15 09:32:00",
                "2024-01-15 10:15:00",
            ]),
            "entry_price": [150.0, 140.0],
            "date": pd.to_datetime(["2024-01-15", "2024-01-15"]),
            "pnl_pct": [1.5, -0.8],
        })
        browser.set_trades(df1)
        assert browser.trade_list.count() == 2

        df2 = pd.DataFrame({
            "ticker": ["MSFT"],
            "entry_time": pd.to_datetime(["2024-01-15 11:00:00"]),
            "entry_price": [380.0],
            "date": pd.to_datetime(["2024-01-15"]),
            "pnl_pct": [2.1],
        })
        browser.set_trades(df2)
        assert browser.trade_list.count() == 1

    def test_set_trades_empty_dataframe(self, qtbot):
        """set_trades() handles empty DataFrame."""
        browser = TradeBrowser()
        qtbot.addWidget(browser)

        df = pd.DataFrame({
            "ticker": [],
            "entry_time": [],
            "entry_price": [],
            "date": [],
            "pnl_pct": [],
        })
        browser.set_trades(df)

        assert browser.trade_list.count() == 0
        assert browser._prev_btn.isEnabled() is False
        assert browser._next_btn.isEnabled() is False


class TestTradeBrowserNavigation:
    """Tests for TradeBrowser Prev/Next navigation."""

    def test_next_button_advances_selection(self, qtbot):
        """Next button advances to next trade."""
        browser = TradeBrowser()
        qtbot.addWidget(browser)

        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL", "MSFT"],
            "entry_time": pd.to_datetime([
                "2024-01-15 09:32:00",
                "2024-01-15 10:15:00",
                "2024-01-15 11:45:00",
            ]),
            "entry_price": [150.0, 140.0, 380.0],
            "date": pd.to_datetime(["2024-01-15", "2024-01-15", "2024-01-15"]),
            "pnl_pct": [1.5, -0.8, 2.1],
        })
        browser.set_trades(df)
        browser.trade_list.setCurrentRow(0)

        browser._next_btn.click()

        assert browser.trade_list.currentRow() == 1

    def test_prev_button_goes_back(self, qtbot):
        """Prev button goes to previous trade."""
        browser = TradeBrowser()
        qtbot.addWidget(browser)

        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL", "MSFT"],
            "entry_time": pd.to_datetime([
                "2024-01-15 09:32:00",
                "2024-01-15 10:15:00",
                "2024-01-15 11:45:00",
            ]),
            "entry_price": [150.0, 140.0, 380.0],
            "date": pd.to_datetime(["2024-01-15", "2024-01-15", "2024-01-15"]),
            "pnl_pct": [1.5, -0.8, 2.1],
        })
        browser.set_trades(df)
        browser.trade_list.setCurrentRow(2)

        browser._prev_btn.click()

        assert browser.trade_list.currentRow() == 1

    def test_next_disabled_at_end(self, qtbot):
        """Next button is disabled when at last trade."""
        browser = TradeBrowser()
        qtbot.addWidget(browser)

        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL"],
            "entry_time": pd.to_datetime([
                "2024-01-15 09:32:00",
                "2024-01-15 10:15:00",
            ]),
            "entry_price": [150.0, 140.0],
            "date": pd.to_datetime(["2024-01-15", "2024-01-15"]),
            "pnl_pct": [1.5, -0.8],
        })
        browser.set_trades(df)
        browser.trade_list.setCurrentRow(1)  # Last item

        assert browser._next_btn.isEnabled() is False

    def test_prev_disabled_at_start(self, qtbot):
        """Prev button is disabled when at first trade."""
        browser = TradeBrowser()
        qtbot.addWidget(browser)

        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL"],
            "entry_time": pd.to_datetime([
                "2024-01-15 09:32:00",
                "2024-01-15 10:15:00",
            ]),
            "entry_price": [150.0, 140.0],
            "date": pd.to_datetime(["2024-01-15", "2024-01-15"]),
            "pnl_pct": [1.5, -0.8],
        })
        browser.set_trades(df)
        browser.trade_list.setCurrentRow(0)  # First item

        assert browser._prev_btn.isEnabled() is False

    def test_navigation_emits_trade_selected(self, qtbot):
        """Navigation buttons emit trade_selected signal."""
        browser = TradeBrowser()
        qtbot.addWidget(browser)

        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL"],
            "entry_time": pd.to_datetime([
                "2024-01-15 09:32:00",
                "2024-01-15 10:15:00",
            ]),
            "entry_price": [150.0, 140.0],
            "date": pd.to_datetime(["2024-01-15", "2024-01-15"]),
            "pnl_pct": [1.5, -0.8],
        })
        browser.set_trades(df)
        browser.trade_list.setCurrentRow(0)

        signal_received = []
        browser.trade_selected.connect(lambda t: signal_received.append(t))

        browser._next_btn.click()

        # Should have received signal for GOOGL
        assert len(signal_received) == 1
        assert signal_received[0]["ticker"] == "GOOGL"
