"""Price data loading functionality for chart visualization."""

import logging
from enum import Enum
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class Resolution(Enum):
    """Time resolution for price data bars.

    Each resolution has a label, value, and unit.
    - label: Human-readable short form (e.g., "5m" for 5 minutes)
    - value: Numeric value of the resolution
    - unit: Time unit ("second", "minute", or "daily")
    """

    SECOND_1 = ("1s", 1, "second")
    SECOND_5 = ("5s", 5, "second")
    SECOND_15 = ("15s", 15, "second")
    SECOND_30 = ("30s", 30, "second")
    MINUTE_1 = ("1m", 1, "minute")
    MINUTE_2 = ("2m", 2, "minute")
    MINUTE_5 = ("5m", 5, "minute")
    MINUTE_15 = ("15m", 15, "minute")
    MINUTE_30 = ("30m", 30, "minute")
    MINUTE_60 = ("60m", 60, "minute")
    DAILY = ("1D", 1, "daily")

    def __init__(self, label: str, value: int, unit: str) -> None:
        """Initialize resolution with label, value, and unit.

        Args:
            label: Human-readable label (e.g., "5m").
            value: Numeric value of the resolution.
            unit: Time unit ("second", "minute", or "daily").
        """
        self._label = label
        self._value = value
        self._unit = unit

    @property
    def label(self) -> str:
        """Human-readable label for the resolution."""
        return self._label

    @property
    def value(self) -> int:
        """Numeric value of the resolution."""
        return self._value

    @property
    def unit(self) -> str:
        """Time unit of the resolution."""
        return self._unit


class PriceDataLoader:
    """Load price data from parquet files for chart visualization.

    Supports loading second-level, minute-level, and daily price data from
    parquet files organized by date. Data can be aggregated to higher resolutions
    (e.g., 5-minute bars from 1-minute data).

    Attributes:
        second_path: Path to second-level data directory.
        minute_path: Path to minute-level data directory.
        daily_path: Path to daily data directory.
    """

    # Column name mappings for normalization (lowercase key -> standard name)
    _COLUMN_MAPPINGS: dict[str, str] = {
        "ticker": "ticker",
        "symbol": "ticker",
        "datetime": "datetime",
        "date": "datetime",
        "time": "datetime",
        "timestamp": "datetime",
        "open": "open",
        "o": "open",
        "high": "high",
        "h": "high",
        "low": "low",
        "l": "low",
        "close": "close",
        "c": "close",
        "volume": "volume",
        "vol": "volume",
        "v": "volume",
    }

    def __init__(
        self,
        second_path: Path | None = None,
        minute_path: Path | None = None,
        daily_path: Path | None = None,
    ) -> None:
        """Initialize the price data loader.

        Args:
            second_path: Path to second-level data directory. Defaults to d:/Second-Level.
            minute_path: Path to minute-level data directory. Defaults to d:/Minute-Level.
            daily_path: Path to daily data directory. Defaults to d:/Daily-Level.
        """
        self.second_path = second_path if second_path is not None else Path("d:/Second-Level")
        self.minute_path = minute_path if minute_path is not None else Path("d:/Minute-Level")
        self.daily_path = daily_path if daily_path is not None else Path("d:/Daily-Level")

    def load(
        self,
        ticker: str,
        date: str,
        resolution: Resolution,
    ) -> pd.DataFrame | None:
        """Load price data for a ticker on a specific date.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL").
            date: Date string in YYYY-MM-DD format.
            resolution: Time resolution for the data.

        Returns:
            DataFrame with columns [datetime, open, high, low, close, volume],
            or None if data cannot be loaded.
        """
        # Determine base path based on resolution unit
        base_path = self._get_base_path(resolution)
        file_path = base_path / f"{date}.parquet"

        # Check if file exists
        if not file_path.exists():
            logger.debug("Price data file not found: %s", file_path)
            return None

        try:
            # Load parquet file
            df = pd.read_parquet(file_path)

            # Normalize column names
            df = self._normalize_columns(df)

            # Filter to specified ticker
            df = self._filter_ticker(df, ticker)
            if df is None or len(df) == 0:
                logger.debug("Ticker %s not found in %s", ticker, file_path)
                return None

            # Aggregate if needed
            df = self._aggregate_if_needed(df, resolution)

            # Select and order final columns
            output_columns = ["datetime", "open", "high", "low", "close", "volume"]
            df = df[output_columns].reset_index(drop=True)

            logger.info("Loaded %d bars for %s on %s at %s resolution", len(df), ticker, date,
                        resolution.label)
            return df

        except Exception as e:
            logger.error("Failed to load price data: %s", e)
            return None

    def _get_base_path(self, resolution: Resolution) -> Path:
        """Get the base data path for a resolution.

        Args:
            resolution: Time resolution for the data.

        Returns:
            Path to the data directory for this resolution's unit.
        """
        if resolution.unit == "second":
            return self.second_path
        elif resolution.unit == "minute":
            return self.minute_path
        else:  # daily
            return self.daily_path

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to standard lowercase format.

        Args:
            df: Input DataFrame with potentially non-standard column names.

        Returns:
            DataFrame with normalized column names.
        """
        # Create mapping from current columns to normalized names
        rename_map: dict[str, str] = {}
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in self._COLUMN_MAPPINGS:
                rename_map[col] = self._COLUMN_MAPPINGS[col_lower]

        return df.rename(columns=rename_map)

    def _filter_ticker(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame | None:
        """Filter DataFrame to rows matching the specified ticker.

        Args:
            df: Input DataFrame with a 'ticker' column.
            ticker: Ticker symbol to filter for.

        Returns:
            Filtered DataFrame, or None if ticker column not found.
        """
        if "ticker" not in df.columns:
            logger.warning("No ticker column found in data")
            return None

        filtered = df[df["ticker"].str.upper() == ticker.upper()].copy()
        return filtered if len(filtered) > 0 else None

    def _aggregate_if_needed(self, df: pd.DataFrame, resolution: Resolution) -> pd.DataFrame:
        """Aggregate data to the target resolution if needed.

        For minute data, aggregates from 1-minute bars to higher resolutions.
        For second data, aggregates from 1-second bars to higher resolutions.

        Args:
            df: Input DataFrame with 1-minute or 1-second bars.
            resolution: Target resolution.

        Returns:
            Aggregated DataFrame, or original if no aggregation needed.
        """
        # No aggregation needed for base resolutions
        if resolution in (Resolution.MINUTE_1, Resolution.SECOND_1, Resolution.DAILY):
            return df

        # Determine aggregation period
        if resolution.unit == "minute":
            freq = f"{resolution.value}min"
        else:  # second
            freq = f"{resolution.value}s"

        # Sort by datetime
        df = df.sort_values("datetime")

        # Set datetime as index for resampling
        df = df.set_index("datetime")

        # Resample and aggregate OHLCV
        agg_df = df.resample(freq, origin="start").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }).dropna()

        # Reset index to get datetime back as column
        agg_df = agg_df.reset_index()

        return agg_df
