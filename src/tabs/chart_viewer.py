"""Chart Viewer tab for visualizing individual trades with candlestick charts."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.core.app_state import AppState
from src.core.exit_simulator import ExitSimulator, ScalingConfig
from src.core.price_data import PriceDataLoader, Resolution
from src.ui.components.candlestick_chart import CandlestickChart
from src.ui.components.trade_browser import TradeBrowser
from src.ui.constants import Colors, Fonts, FontSizes, Spacing

if TYPE_CHECKING:
    from src.core.models import ColumnMapping

logger = logging.getLogger(__name__)

# Resolution label to Resolution enum mapping
RESOLUTION_MAP = {
    "1s": Resolution.SECOND_1,
    "5s": Resolution.SECOND_5,
    "15s": Resolution.SECOND_15,
    "30s": Resolution.SECOND_30,
    "1m": Resolution.MINUTE_1,
    "2m": Resolution.MINUTE_2,
    "5m": Resolution.MINUTE_5,
    "15m": Resolution.MINUTE_15,
    "30m": Resolution.MINUTE_30,
    "60m": Resolution.MINUTE_60,
    "Daily": Resolution.DAILY,
}

# Zoom preset to minutes mapping
ZOOM_PRESETS = {
    "Trade only": 0,
    "Trade +/- 15min": 15,
    "Trade +/- 30min": 30,
    "Trade +/- 60min": 60,
    "Full session": -1,  # Special: show full session
}


class ChartViewerTab(QWidget):
    """Tab for viewing individual trades with candlestick charts.

    Integrates TradeBrowser, CandlestickChart, resolution/zoom selectors,
    and scaling configuration panel.

    Layout:
    +-----------------------------------------------------------------+
    | [Resolution: v 1-Min] [Zoom: v Trade +/- 30min]  Trade Info Box  |
    +---------------+-------------------------------------------------+
    | Trade Browser |                                                 |
    | +----------+  |          Candlestick Chart                      |
    | | List     |  |                                                 |
    | +----------+  |                                                 |
    | [< Prev][Next>]                                                 |
    +---------------+                                                 |
    | Scaling Config|                                                 |
    | [50]% at [35]%|                                                 |
    | profit        |                                                 |
    +---------------+-------------------------------------------------+

    Attributes:
        _app_state: Reference to centralized app state.
        _trade_browser: TradeBrowser component for trade list.
        _chart: CandlestickChart component for price visualization.
        _resolution_combo: Dropdown for bar resolution selection.
        _zoom_combo: Dropdown for zoom preset selection.
        _trade_info_label: Label showing current trade info.
        _scale_pct_spin: Spinbox for scale out percentage.
        _profit_target_spin: Spinbox for profit target percentage.
        _price_loader: PriceDataLoader for loading OHLC data.
        _splitter: QSplitter for left panel and chart layout.
    """

    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        """Initialize the Chart Viewer tab.

        Args:
            app_state: Centralized application state.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._app_state = app_state
        self._price_loader = PriceDataLoader()
        self._current_trade: dict | None = None

        self._setup_ui()
        self._apply_styles()
        self._connect_signals()
        self._initialize_from_state()

    def _setup_ui(self) -> None:
        """Set up the tab UI layout."""
        self.setObjectName("chartViewerTab")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        main_layout.setSpacing(Spacing.MD)

        # Top controls row
        top_row = self._create_top_controls()
        main_layout.addLayout(top_row)

        # Main content splitter (left panel | chart)
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel (trade browser + scaling config)
        left_panel = self._create_left_panel()
        self._splitter.addWidget(left_panel)

        # Right panel (candlestick chart)
        self._chart = CandlestickChart()
        self._splitter.addWidget(self._chart)

        # Set splitter proportions (1:3 ratio)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 3)
        self._splitter.setSizes([250, 750])

        main_layout.addWidget(self._splitter, stretch=1)

    def _create_top_controls(self) -> QHBoxLayout:
        """Create the top row with resolution, zoom, and trade info.

        Returns:
            QHBoxLayout with control widgets.
        """
        layout = QHBoxLayout()
        layout.setSpacing(Spacing.MD)

        # Resolution selector
        res_label = QLabel("Resolution:")
        res_label.setObjectName("controlLabel")
        layout.addWidget(res_label)

        self._resolution_combo = QComboBox()
        self._resolution_combo.setObjectName("resolutionCombo")
        for label in RESOLUTION_MAP:
            self._resolution_combo.addItem(label)
        # Default to 1-minute
        self._resolution_combo.setCurrentText("1m")
        layout.addWidget(self._resolution_combo)

        layout.addSpacing(Spacing.LG)

        # Zoom selector
        zoom_label = QLabel("Zoom:")
        zoom_label.setObjectName("controlLabel")
        layout.addWidget(zoom_label)

        self._zoom_combo = QComboBox()
        self._zoom_combo.setObjectName("zoomCombo")
        for preset in ZOOM_PRESETS:
            self._zoom_combo.addItem(preset)
        # Default to +/- 30min
        self._zoom_combo.setCurrentText("Trade +/- 30min")
        layout.addWidget(self._zoom_combo)

        layout.addStretch()

        # Trade info box
        self._trade_info_label = QLabel("Select a trade to view")
        self._trade_info_label.setObjectName("tradeInfoLabel")
        self._trade_info_label.setMinimumWidth(200)
        layout.addWidget(self._trade_info_label)

        return layout

    def _create_left_panel(self) -> QWidget:
        """Create the left panel with trade browser and scaling config.

        Returns:
            QWidget containing trade browser and scaling config.
        """
        panel = QWidget()
        panel.setObjectName("leftPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.MD)

        # Trade browser
        self._trade_browser = TradeBrowser()
        layout.addWidget(self._trade_browser, stretch=1)

        # Scaling config section
        scaling_section = self._create_scaling_config()
        layout.addWidget(scaling_section)

        return panel

    def _create_scaling_config(self) -> QWidget:
        """Create the scaling configuration panel.

        Returns:
            QWidget with scale percentage and profit target spinboxes.
        """
        widget = QWidget()
        widget.setObjectName("scalingConfig")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(Spacing.SM)

        # Section header
        header = QLabel("Scaling Config")
        header.setObjectName("scalingHeader")
        layout.addWidget(header)

        # Scale percentage row
        scale_row = QHBoxLayout()
        scale_row.setSpacing(Spacing.XS)

        self._scale_pct_spin = QSpinBox()
        self._scale_pct_spin.setObjectName("scalePctSpin")
        self._scale_pct_spin.setRange(1, 100)
        self._scale_pct_spin.setValue(50)
        self._scale_pct_spin.setSuffix("%")
        scale_row.addWidget(self._scale_pct_spin)

        scale_at_label = QLabel("at")
        scale_row.addWidget(scale_at_label)

        self._profit_target_spin = QSpinBox()
        self._profit_target_spin.setObjectName("profitTargetSpin")
        self._profit_target_spin.setRange(1, 200)
        self._profit_target_spin.setValue(35)
        self._profit_target_spin.setSuffix("%")
        scale_row.addWidget(self._profit_target_spin)

        profit_label = QLabel("profit")
        scale_row.addWidget(profit_label)

        scale_row.addStretch()
        layout.addLayout(scale_row)

        return widget

    def _apply_styles(self) -> None:
        """Apply Observatory theme styling."""
        self.setStyleSheet(f"""
            QWidget#chartViewerTab {{
                background-color: {Colors.BG_SURFACE};
            }}
            QLabel#controlLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
            }}
            QComboBox {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
                padding: {Spacing.XS}px {Spacing.SM}px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                min-width: 100px;
            }}
            QComboBox:hover {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
                selection-background-color: {Colors.SIGNAL_BLUE};
            }}
            QLabel#tradeInfoLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.DATA};
                font-size: {FontSizes.BODY}px;
                padding: {Spacing.SM}px;
                background-color: {Colors.BG_ELEVATED};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
            }}
            QWidget#leftPanel {{
                background-color: {Colors.BG_SURFACE};
            }}
            QWidget#scalingConfig {{
                background-color: {Colors.BG_ELEVATED};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
            }}
            QLabel#scalingHeader {{
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
                font-weight: bold;
            }}
            QSpinBox {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.DATA};
                font-size: {FontSizes.BODY}px;
                padding: {Spacing.XS}px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
                min-width: 60px;
            }}
            QSpinBox:focus {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
            QSplitter::handle {{
                background-color: {Colors.BG_BORDER};
                width: 2px;
            }}
            QSplitter::handle:hover {{
                background-color: {Colors.SIGNAL_CYAN};
            }}
        """)

    def _connect_signals(self) -> None:
        """Connect signals to handlers."""
        # App state signals
        self._app_state.filtered_data_updated.connect(self._on_filtered_data_updated)
        self._app_state.baseline_calculated.connect(self._on_baseline_calculated)
        self._app_state.view_chart_requested.connect(self._on_view_chart_requested)
        self._app_state.column_mapping_changed.connect(self._on_column_mapping_changed)

        # Trade browser signals
        self._trade_browser.trade_selected.connect(self._on_trade_selected)

        # Control change signals
        self._resolution_combo.currentTextChanged.connect(self._on_settings_changed)
        self._zoom_combo.currentTextChanged.connect(self._on_settings_changed)
        self._scale_pct_spin.valueChanged.connect(self._on_settings_changed)
        self._profit_target_spin.valueChanged.connect(self._on_settings_changed)

    def _initialize_from_state(self) -> None:
        """Initialize from existing app state if available."""
        logger.debug("_initialize_from_state called")
        logger.debug("filtered_df=%s, baseline_df=%s",
                    "None" if self._app_state.filtered_df is None else f"{len(self._app_state.filtered_df)} rows",
                    "None" if self._app_state.baseline_df is None else f"{len(self._app_state.baseline_df)} rows")
        
        if self._app_state.filtered_df is not None and not self._app_state.filtered_df.empty:
            logger.debug("Using filtered_df")
            self._update_trade_browser(self._app_state.filtered_df)
        elif self._app_state.baseline_df is not None and not self._app_state.baseline_df.empty:
            logger.debug("Using baseline_df")
            self._update_trade_browser(self._app_state.baseline_df)
        else:
            logger.debug("No data available to initialize from")

    def _on_column_mapping_changed(self, mapping: object = None) -> None:
        """Handle column mapping changes - re-initialize trade browser.
        
        Args:
            mapping: The new column mapping (unused, we read from app_state).
        """
        logger.debug("_on_column_mapping_changed signal received")
        self._initialize_from_state()

    def _on_filtered_data_updated(self, df: pd.DataFrame) -> None:
        """Handle filtered data update.

        Args:
            df: Updated filtered DataFrame.
        """
        self._update_trade_browser(df)

    def _on_baseline_calculated(self, metrics) -> None:
        """Handle baseline calculated signal.

        Args:
            metrics: TradingMetrics (unused, we use baseline_df).
        """
        if (
            (self._app_state.filtered_df is None or self._app_state.filtered_df.empty)
            and self._app_state.baseline_df is not None
        ):
            self._update_trade_browser(self._app_state.baseline_df)

    def _update_trade_browser(self, df: pd.DataFrame) -> None:
        """Update trade browser with DataFrame.

        Args:
            df: DataFrame with trade data.
        """
        logger.debug("_update_trade_browser called with df=%s", 
                    "None" if df is None else f"{len(df)} rows")
        
        if df is None or df.empty:
            logger.debug("DataFrame is None or empty, clearing trade browser")
            self._trade_browser.set_trades(pd.DataFrame())
            return

        mapping = self._app_state.column_mapping
        logger.debug("column_mapping=%s", "None" if mapping is None else "set")
        
        if mapping is None:
            logger.debug("No column mapping, returning early")
            return

        # Transform data for trade browser
        # TradeBrowser expects: ticker, entry_time, entry_price, date, pnl_pct
        browser_df = self._prepare_browser_dataframe(df, mapping)
        logger.debug("Prepared browser_df with %d rows", len(browser_df))
        self._trade_browser.set_trades(browser_df)

    def _prepare_browser_dataframe(
        self, df: pd.DataFrame, mapping: ColumnMapping
    ) -> pd.DataFrame:
        """Prepare DataFrame for trade browser.

        Args:
            df: Source DataFrame.
            mapping: Column mapping.

        Returns:
            DataFrame with columns needed by TradeBrowser.
        """
        try:
            logger.debug("Preparing browser DataFrame with %d rows", len(df))
            logger.debug("Column mapping: ticker=%s, date=%s, time=%s, gain_pct=%s",
                        mapping.ticker, mapping.date, mapping.time, mapping.gain_pct)
            logger.debug("Available columns: %s", list(df.columns))
            
            result = pd.DataFrame()
            result["ticker"] = df[mapping.ticker]
            
            # Parse dates - use format='mixed' to handle various date formats
            date_col = df[mapping.date]
            result["date"] = pd.to_datetime(date_col, format='mixed', dayfirst=True)

            # Combine date and time for entry_time
            time_col = df[mapping.time]
            
            # Handle various time formats
            if time_col.dtype == "object":
                # String times like "09:30:00"
                datetime_strs = date_col.astype(str) + " " + time_col.astype(str)
                result["entry_time"] = pd.to_datetime(datetime_strs, format='mixed', dayfirst=True)
            elif pd.api.types.is_float_dtype(time_col):
                # Check if Excel serial time (float between 0 and 1)
                non_null_times = time_col.dropna()
                if len(non_null_times) > 0 and non_null_times.between(0, 1).all():
                    # Excel serial time: fraction of day (0.5 = 12:00 noon)
                    # Convert to timedelta and add to date
                    time_delta = pd.to_timedelta(time_col * 24, unit='h')
                    result["entry_time"] = pd.to_datetime(date_col, format='mixed', dayfirst=True) + time_delta
                    logger.debug("Converted Excel serial time format")
                else:
                    # Try as timestamp
                    result["entry_time"] = pd.to_datetime(time_col)
            elif pd.api.types.is_integer_dtype(time_col):
                # Integer HHMMSS format (e.g., 93000 for 09:30:00)
                def int_to_time_str(val):
                    if pd.isna(val):
                        return None
                    val_str = str(int(val)).zfill(6)
                    return f"{val_str[:2]}:{val_str[2:4]}:{val_str[4:6]}"
                time_strs = time_col.apply(int_to_time_str)
                datetime_strs = date_col.astype(str) + " " + time_strs.astype(str)
                result["entry_time"] = pd.to_datetime(datetime_strs, format='mixed', dayfirst=True)
                logger.debug("Converted integer HHMMSS time format")
            else:
                # Already datetime
                result["entry_time"] = pd.to_datetime(time_col)

            result["pnl_pct"] = df[mapping.gain_pct]

            # Entry price - check common column names
            price_columns = [
                "entry_price",
                "price",
                "trigger_price_unadjusted",
                "trigger_price",
                "fill_price",
                "avg_price",
                "open",
            ]
            entry_price_col = None
            for col in price_columns:
                if col in df.columns:
                    entry_price_col = col
                    break

            if entry_price_col:
                result["entry_price"] = df[entry_price_col]
                logger.debug("Using '%s' column for entry price", entry_price_col)
            else:
                # Default to 100 for percentage calculations
                result["entry_price"] = 100.0
                logger.debug("No entry price column found, using default 100.0")

            logger.debug("Successfully prepared browser DataFrame with %d rows", len(result))
            return result

        except Exception as e:
            logger.error("Failed to prepare browser DataFrame: %s", e, exc_info=True)
            return pd.DataFrame()

    def _on_trade_selected(self, trade_data: dict) -> None:
        """Handle trade selection from browser.

        Args:
            trade_data: Dictionary with trade information.
        """
        self._current_trade = trade_data
        self._update_trade_info(trade_data)
        self._load_chart_for_trade(trade_data)

    def _on_view_chart_requested(self, trade_data: dict) -> None:
        """Handle external request to view chart for a trade.

        Called when another tab (e.g., Statistics) requests to view a trade's chart.

        Args:
            trade_data: Dictionary with trade information (ticker, entry_time, etc.).
        """
        logger.debug("View chart requested for trade: %s", trade_data.get("ticker", "N/A"))
        self._current_trade = trade_data
        self._update_trade_info(trade_data)
        self._load_chart_for_trade(trade_data)

    def _update_trade_info(self, trade_data: dict) -> None:
        """Update the trade info label.

        Args:
            trade_data: Dictionary with trade information.
        """
        ticker = trade_data.get("ticker", "N/A")
        entry_time = trade_data.get("entry_time")
        pnl_pct = trade_data.get("pnl_pct", 0)
        entry_price = trade_data.get("entry_price", 0)

        time_str = ""
        if entry_time is not None and hasattr(entry_time, "strftime"):
            time_str = entry_time.strftime("%Y-%m-%d %H:%M")
        elif entry_time is not None:
            time_str = str(entry_time)

        # Format PnL with color indication in text
        pnl_sign = "+" if pnl_pct >= 0 else ""
        info_text = f"{ticker} @ ${entry_price:.2f} | {time_str} | {pnl_sign}{pnl_pct:.2f}%"

        self._trade_info_label.setText(info_text)

    def _on_settings_changed(self) -> None:
        """Handle settings change - reload chart with new settings."""
        if self._current_trade is not None:
            self._load_chart_for_trade(self._current_trade)

    def _load_chart_for_trade(self, trade_data: dict) -> None:
        """Load and display chart for the selected trade.

        Args:
            trade_data: Dictionary with trade information.
        """
        ticker = trade_data.get("ticker")
        entry_time = trade_data.get("entry_time")
        entry_price = trade_data.get("entry_price", 100.0)

        logger.info("Loading chart for trade: ticker=%s, entry_time=%s, entry_price=%s",
                   ticker, entry_time, entry_price)

        if not ticker or not entry_time:
            logger.warning("Missing ticker or entry_time for chart loading")
            return

        # Get date string
        try:
            if hasattr(entry_time, "date"):
                date_str = entry_time.date().isoformat()
            else:
                date = trade_data.get("date")
                date_str = date.isoformat() if hasattr(date, "isoformat") else str(date)
            logger.info("Date string for price data: %s", date_str)
        except (AttributeError, TypeError, ValueError) as e:
            logger.warning("Failed to parse date for chart loading: %s", e)
            return

        # Get resolution
        resolution_label = self._resolution_combo.currentText()
        resolution = RESOLUTION_MAP.get(resolution_label, Resolution.MINUTE_1)
        logger.info("Resolution: %s", resolution.label)

        # Load price data
        price_df = self._price_loader.load(ticker, date_str, resolution)

        if price_df is None or price_df.empty:
            logger.warning("No price data available for %s on %s at %s resolution",
                          ticker, date_str, resolution.label)
            self._chart.clear()
            return

        logger.info("Loaded %d price bars for %s", len(price_df), ticker)

        # Check zoom setting to determine if we show extended hours
        zoom_preset = self._zoom_combo.currentText()
        zoom_minutes = ZOOM_PRESETS.get(zoom_preset, 30)
        show_extended_hours = (zoom_minutes == -1)  # Full session shows extended hours

        if "datetime" in price_df.columns:
            # Add session type column for background highlighting
            # Pre-market: before 9:30 AM, Regular: 9:30 AM - 4:00 PM, Post-market: after 4:00 PM
            def get_session_type(dt):
                hour, minute = dt.hour, dt.minute
                if hour < 9 or (hour == 9 and minute < 30):
                    return "pre"
                elif hour >= 16:
                    return "post"
                else:
                    return "regular"
            
            price_df["session"] = price_df["datetime"].apply(get_session_type)
            
            if show_extended_hours:
                # Full session - keep all data including pre/post market
                # Filter to extended hours (4:00 AM - 8:00 PM ET for typical extended hours)
                extended_hours_mask = (price_df["datetime"].dt.hour >= 4) & (price_df["datetime"].dt.hour < 20)
                price_df = price_df[extended_hours_mask].reset_index(drop=True)
                logger.info("Full session with extended hours: %d bars", len(price_df))
            else:
                # Filter to regular trading hours only (9:30 AM - 4:00 PM ET)
                regular_hours_mask = (
                    (price_df["datetime"].dt.hour > 9) |
                    ((price_df["datetime"].dt.hour == 9) & (price_df["datetime"].dt.minute >= 30))
                ) & (price_df["datetime"].dt.hour < 16)
                price_df = price_df[regular_hours_mask].reset_index(drop=True)
                logger.info("After regular hours filter: %d bars", len(price_df))

            # Log first 5 bars after filtering
            if len(price_df) >= 5:
                logger.info("First 5 bars after filter (displayed on chart):")
                for i in range(5):
                    row = price_df.iloc[i]
                    session = row.get("session", "?")
                    logger.info("  [%d] %s O=%.4f H=%.4f L=%.4f C=%.4f session=%s",
                               i, row["datetime"], row["open"], row["high"], row["low"], row["close"], session)

        # Apply zoom filter (only affects non-full-session modes)
        price_df = self._apply_zoom_filter(price_df, entry_time)

        if price_df.empty:
            logger.warning("No valid price data after filtering")
            self._chart.clear()
            return

        # Log price data statistics
        if not price_df.empty:
            logger.info(
                "Price data stats - rows: %d, open: [%.2f, %.2f], high: [%.2f, %.2f], low: [%.2f, %.2f], close: [%.2f, %.2f]",
                len(price_df),
                price_df["open"].min(), price_df["open"].max(),
                price_df["high"].min(), price_df["high"].max(),
                price_df["low"].min(), price_df["low"].max(),
                price_df["close"].min(), price_df["close"].max(),
            )

        # Set chart data (pass session info for background highlighting)
        self._chart.set_data(price_df)

        # Run exit simulation
        stop_level = self._calculate_stop_level(entry_price)
        scaling_config = self._get_scaling_config()

        # Convert entry_time to datetime if needed
        if hasattr(entry_time, "to_pydatetime"):
            entry_dt = entry_time.to_pydatetime()
        else:
            entry_dt = entry_time

        # Debug: Log entry time and first/last bar times for comparison
        if not price_df.empty and "datetime" in price_df.columns:
            first_bar_time = price_df["datetime"].iloc[0]
            last_bar_time = price_df["datetime"].iloc[-1]
            if hasattr(first_bar_time, "to_pydatetime"):
                first_bar_time = first_bar_time.to_pydatetime()
                last_bar_time = last_bar_time.to_pydatetime()
            logger.info("Entry time: %s (type: %s, tz: %s)", entry_dt, type(entry_dt).__name__, 
                       getattr(entry_dt, 'tzinfo', None))
            logger.info("First bar time: %s (type: %s, tz: %s)", first_bar_time, type(first_bar_time).__name__,
                       getattr(first_bar_time, 'tzinfo', None))
            logger.info("Last bar time: %s (type: %s, tz: %s)", last_bar_time, type(last_bar_time).__name__,
                       getattr(last_bar_time, 'tzinfo', None))
            # Check if entry is within the bar range
            try:
                entry_before_first = entry_dt <= first_bar_time
                entry_after_last = entry_dt >= last_bar_time
                logger.info("Entry <= first bar? %s, Entry >= last bar? %s", entry_before_first, entry_after_last)
            except TypeError as e:
                logger.warning("Cannot compare datetimes (likely timezone mismatch): %s", e)

        try:
            simulator = ExitSimulator(
                entry_price=entry_price,
                entry_time=entry_dt,
                stop_level=stop_level,
                scaling_config=scaling_config,
            )
            exits = simulator.simulate(price_df)
            profit_target = simulator.profit_target
            
            # Debug: Log exit details
            for i, exit_event in enumerate(exits):
                logger.info("Exit[%d]: time=%s, price=%.4f, reason=%s", 
                           i, exit_event.time, exit_event.price, exit_event.reason)
        except ValueError as e:
            logger.warning("Could not create ExitSimulator: %s", e)
            exits = []
            profit_target = None

        # Set markers on chart
        self._chart.set_markers(
            entry_time=entry_dt,
            entry_price=entry_price,
            exits=exits,
            stop_level=stop_level,
            profit_target=profit_target,
        )

        # Ensure chart fits all data including markers
        self._chart.auto_range()

        logger.info(
            "Chart loaded for %s: %d bars, %d exits",
            ticker,
            len(price_df),
            len(exits),
        )

    def _apply_zoom_filter(
        self, df: pd.DataFrame, entry_time: datetime
    ) -> pd.DataFrame:
        """Filter price data based on zoom setting.

        Args:
            df: Price DataFrame with datetime column.
            entry_time: Trade entry time.

        Returns:
            Filtered DataFrame.
        """
        zoom_preset = self._zoom_combo.currentText()
        minutes = ZOOM_PRESETS.get(zoom_preset, 30)

        if minutes == -1:
            # Full session - no filter
            return df

        if minutes == 0:
            # Trade only - narrow window around entry
            minutes = 5  # Show at least 5 minutes around entry

        # Convert entry_time if needed
        if hasattr(entry_time, "to_pydatetime"):
            entry_dt = entry_time.to_pydatetime()
        else:
            entry_dt = entry_time

        start_time = entry_dt - timedelta(minutes=minutes)
        end_time = entry_dt + timedelta(minutes=minutes)

        # Validate datetime column exists
        if "datetime" not in df.columns:
            return df

        # Filter by datetime
        mask = (df["datetime"] >= start_time) & (df["datetime"] <= end_time)
        return df[mask].reset_index(drop=True)

    def _calculate_stop_level(self, entry_price: float) -> float:
        """Calculate stop loss level from adjustment params.

        For long trades: stop_level = entry_price * (1 - stop_loss_percent/100)
        For short trades: stop_level = entry_price * (1 + stop_loss_percent/100)

        Args:
            entry_price: Trade entry price.

        Returns:
            Stop loss price level.
        """
        stop_loss_pct = self._app_state.adjustment_params.stop_loss
        is_short = self._app_state.adjustment_params.is_short

        if is_short:
            # Short trade: stop is above entry price
            return entry_price * (1 + stop_loss_pct / 100)
        else:
            # Long trade: stop is below entry price
            return entry_price * (1 - stop_loss_pct / 100)

    def _get_scaling_config(self) -> ScalingConfig:
        """Get current scaling configuration from UI.

        Returns:
            ScalingConfig with current spinbox values.
        """
        # Get values with validation and fallback to defaults
        scale_pct = self._scale_pct_spin.value()
        profit_target_pct = self._profit_target_spin.value()

        # Validate scale_pct is in valid range (1-100)
        if not 1 <= scale_pct <= 100:
            logger.warning("Invalid scale_pct %d, using default 50", scale_pct)
            scale_pct = 50

        # Validate profit_target_pct is in valid range (1-200)
        if not 1 <= profit_target_pct <= 200:
            logger.warning("Invalid profit_target_pct %d, using default 35", profit_target_pct)
            profit_target_pct = 35

        return ScalingConfig(
            scale_pct=float(scale_pct),
            profit_target_pct=float(profit_target_pct),
        )

    def closeEvent(self, event) -> None:
        """Handle widget close - disconnect signals to prevent memory leaks.

        Args:
            event: Close event.
        """
        try:
            # Disconnect app state signals
            self._app_state.filtered_data_updated.disconnect(self._on_filtered_data_updated)
            self._app_state.baseline_calculated.disconnect(self._on_baseline_calculated)
            self._app_state.view_chart_requested.disconnect(self._on_view_chart_requested)
            self._app_state.column_mapping_changed.disconnect(self._on_column_mapping_changed)

            # Disconnect trade browser signals
            self._trade_browser.trade_selected.disconnect(self._on_trade_selected)

            # Disconnect control signals
            self._resolution_combo.currentTextChanged.disconnect(self._on_settings_changed)
            self._zoom_combo.currentTextChanged.disconnect(self._on_settings_changed)
            self._scale_pct_spin.valueChanged.disconnect(self._on_settings_changed)
            self._profit_target_spin.valueChanged.disconnect(self._on_settings_changed)
        except (TypeError, RuntimeError) as e:
            # Signals may already be disconnected
            logger.debug("Signal disconnect during close: %s", e)

        super().closeEvent(event)
