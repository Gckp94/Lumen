"""Unit tests for PriceDataLoader class."""

from pathlib import Path

import pandas as pd
import pytest

from src.core.price_data import PriceDataLoader, Resolution


class TestResolution:
    """Tests for Resolution enum."""

    def test_resolution_minute_5_has_correct_label(self) -> None:
        """MINUTE_5 resolution has label '5m'."""
        assert Resolution.MINUTE_5.label == "5m"

    def test_resolution_minute_5_has_correct_value(self) -> None:
        """MINUTE_5 resolution has value 5."""
        assert Resolution.MINUTE_5.value == 5

    def test_resolution_minute_5_has_correct_unit(self) -> None:
        """MINUTE_5 resolution has unit 'minute'."""
        assert Resolution.MINUTE_5.unit == "minute"

    def test_resolution_daily_has_correct_label(self) -> None:
        """DAILY resolution has label '1D'."""
        assert Resolution.DAILY.label == "1D"

    def test_resolution_second_1_has_correct_unit(self) -> None:
        """SECOND_1 resolution has unit 'second'."""
        assert Resolution.SECOND_1.unit == "second"


class TestPriceDataLoaderLoad:
    """Tests for PriceDataLoader.load method."""

    def test_load_minute_data_returns_dataframe(self, tmp_path: Path) -> None:
        """Load minute data returns DataFrame with correct columns and length."""
        # Arrange: Create test parquet file with minute data
        test_data = pd.DataFrame({
            "ticker": ["AAPL", "AAPL", "AAPL", "MSFT", "MSFT"],
            "datetime": pd.to_datetime([
                "2024-01-15 09:30:00",
                "2024-01-15 09:31:00",
                "2024-01-15 09:32:00",
                "2024-01-15 09:30:00",
                "2024-01-15 09:31:00",
            ]),
            "open": [150.0, 150.5, 151.0, 300.0, 300.5],
            "high": [150.8, 151.0, 151.5, 300.8, 301.0],
            "low": [149.5, 150.0, 150.5, 299.5, 300.0],
            "close": [150.5, 151.0, 151.2, 300.5, 300.8],
            "volume": [1000, 1100, 1200, 2000, 2100],
        })
        parquet_file = tmp_path / "2024-01-15.parquet"
        test_data.to_parquet(parquet_file)

        # Act: Load data for AAPL
        loader = PriceDataLoader(minute_path=tmp_path)
        result = loader.load("AAPL", "2024-01-15", Resolution.MINUTE_1)

        # Assert
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert list(result.columns) == ["datetime", "open", "high", "low", "close", "volume"]

    def test_load_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        """Load returns None when parquet file does not exist."""
        loader = PriceDataLoader(minute_path=tmp_path)
        result = loader.load("AAPL", "2024-01-15", Resolution.MINUTE_1)
        assert result is None

    def test_load_returns_none_for_missing_ticker(self, tmp_path: Path) -> None:
        """Load returns None when ticker is not found in file."""
        # Create file with different ticker
        test_data = pd.DataFrame({
            "ticker": ["MSFT", "MSFT"],
            "datetime": pd.to_datetime(["2024-01-15 09:30:00", "2024-01-15 09:31:00"]),
            "open": [300.0, 300.5],
            "high": [300.8, 301.0],
            "low": [299.5, 300.0],
            "close": [300.5, 300.8],
            "volume": [2000, 2100],
        })
        parquet_file = tmp_path / "2024-01-15.parquet"
        test_data.to_parquet(parquet_file)

        loader = PriceDataLoader(minute_path=tmp_path)
        result = loader.load("AAPL", "2024-01-15", Resolution.MINUTE_1)
        assert result is None

    def test_load_normalizes_column_names(self, tmp_path: Path) -> None:
        """Load normalizes various column name formats to standard names."""
        # Create file with non-standard column names
        test_data = pd.DataFrame({
            "Ticker": ["AAPL", "AAPL"],
            "DateTime": pd.to_datetime(["2024-01-15 09:30:00", "2024-01-15 09:31:00"]),
            "Open": [150.0, 150.5],
            "High": [150.8, 151.0],
            "Low": [149.5, 150.0],
            "Close": [150.5, 151.0],
            "Volume": [1000, 1100],
        })
        parquet_file = tmp_path / "2024-01-15.parquet"
        test_data.to_parquet(parquet_file)

        loader = PriceDataLoader(minute_path=tmp_path)
        result = loader.load("AAPL", "2024-01-15", Resolution.MINUTE_1)

        assert result is not None
        assert list(result.columns) == ["datetime", "open", "high", "low", "close", "volume"]

    def test_load_aggregates_5min_from_1min_data(self, tmp_path: Path) -> None:
        """Load aggregates 1-minute data into 5-minute bars."""
        # Create 10 minutes of 1-minute data
        base_time = pd.Timestamp("2024-01-15 09:30:00")
        times = [base_time + pd.Timedelta(minutes=i) for i in range(10)]
        test_data = pd.DataFrame({
            "ticker": ["AAPL"] * 10,
            "datetime": times,
            "open": [150.0, 150.5, 151.0, 151.5, 152.0, 152.5, 153.0, 153.5, 154.0, 154.5],
            "high": [150.8, 151.0, 151.5, 152.0, 152.5, 153.0, 153.5, 154.0, 154.5, 155.0],
            "low": [149.5, 150.0, 150.5, 151.0, 151.5, 152.0, 152.5, 153.0, 153.5, 154.0],
            "close": [150.5, 151.0, 151.2, 151.8, 152.3, 152.8, 153.3, 153.8, 154.3, 154.8],
            "volume": [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900],
        })
        parquet_file = tmp_path / "2024-01-15.parquet"
        test_data.to_parquet(parquet_file)

        loader = PriceDataLoader(minute_path=tmp_path)
        result = loader.load("AAPL", "2024-01-15", Resolution.MINUTE_5)

        assert result is not None
        assert len(result) == 2  # 10 minutes -> 2 five-minute bars
        # First 5-min bar: open from first, high from max, low from min, close from last
        assert result.iloc[0]["open"] == 150.0
        assert result.iloc[0]["high"] == 152.5  # max of first 5 bars
        assert result.iloc[0]["low"] == 149.5   # min of first 5 bars
        assert result.iloc[0]["close"] == 152.3  # close of 5th bar
        assert result.iloc[0]["volume"] == 6000  # sum of first 5 volumes


class TestPriceDataAggregation:
    """Tests for price data aggregation logic."""

    def test_aggregate_to_5_minute_bars(self, tmp_path: Path) -> None:
        """10 one-minute bars aggregate correctly into 2 five-minute bars.

        Tests the OHLCV aggregation rules:
        - Open = first bar's open
        - High = max of all highs
        - Low = min of all lows
        - Close = last bar's close
        - Volume = sum of volumes
        """
        # Arrange: Create 10 one-minute bars with known OHLCV values
        # Bar 0-4 will form the first 5-minute bar
        # Bar 5-9 will form the second 5-minute bar
        base_time = pd.Timestamp("2024-01-15 09:30:00")
        times = [base_time + pd.Timedelta(minutes=i) for i in range(10)]

        # First 5 bars (09:30-09:34): designed to test aggregation math
        # Open should be 100.0 (from bar 0)
        # High should be 108.0 (from bar 2 - the max)
        # Low should be 97.0 (from bar 4 - the min)
        # Close should be 104.0 (from bar 4)
        # Volume should be 1000+1100+1200+1300+1400 = 6000

        # Second 5 bars (09:35-09:39): different values to verify both bars
        # Open should be 105.0 (from bar 5)
        # High should be 115.0 (from bar 7 - the max)
        # Low should be 101.0 (from bar 9 - the min)
        # Close should be 110.0 (from bar 9)
        # Volume should be 2000+2100+2200+2300+2400 = 11000

        test_data = pd.DataFrame({
            "ticker": ["AAPL"] * 10,
            "datetime": times,
            # Bar:     0      1      2      3      4      5      6      7      8      9
            "open":  [100.0, 102.0, 105.0, 103.0, 99.0,  105.0, 107.0, 112.0, 108.0, 103.0],
            "high":  [103.0, 106.0, 108.0, 105.0, 102.0, 110.0, 113.0, 115.0, 111.0, 106.0],
            "low":   [99.0,  100.0, 103.0, 98.0,  97.0,  104.0, 105.0, 110.0, 106.0, 101.0],
            "close": [102.0, 105.0, 106.0, 100.0, 104.0, 107.0, 111.0, 113.0, 107.0, 110.0],
            "volume": [1000, 1100, 1200, 1300, 1400, 2000, 2100, 2200, 2300, 2400],
        })
        parquet_file = tmp_path / "2024-01-15.parquet"
        test_data.to_parquet(parquet_file)

        # Act: Load as 5-minute bars
        loader = PriceDataLoader(minute_path=tmp_path)
        result = loader.load("AAPL", "2024-01-15", Resolution.MINUTE_5)

        # Assert: Should have 2 five-minute bars
        assert result is not None
        assert len(result) == 2, f"Expected 2 bars, got {len(result)}"

        # Verify first 5-minute bar (09:30-09:34)
        bar1 = result.iloc[0]
        assert bar1["open"] == 100.0, f"Bar 1 open: expected 100.0, got {bar1['open']}"
        assert bar1["high"] == 108.0, f"Bar 1 high: expected 108.0 (max), got {bar1['high']}"
        assert bar1["low"] == 97.0, f"Bar 1 low: expected 97.0 (min), got {bar1['low']}"
        assert bar1["close"] == 104.0, f"Bar 1 close: expected 104.0, got {bar1['close']}"
        assert bar1["volume"] == 6000, f"Bar 1 volume: expected 6000 (sum), got {bar1['volume']}"

        # Verify second 5-minute bar (09:35-09:39)
        bar2 = result.iloc[1]
        assert bar2["open"] == 105.0, f"Bar 2 open: expected 105.0, got {bar2['open']}"
        assert bar2["high"] == 115.0, f"Bar 2 high: expected 115.0 (max), got {bar2['high']}"
        assert bar2["low"] == 101.0, f"Bar 2 low: expected 101.0 (min), got {bar2['low']}"
        assert bar2["close"] == 110.0, f"Bar 2 close: expected 110.0, got {bar2['close']}"
        assert bar2["volume"] == 11000, f"Bar 2 volume: expected 11000 (sum), got {bar2['volume']}"


class TestPriceDataLoaderDefaultPaths:
    """Tests for PriceDataLoader default paths."""

    def test_default_second_path(self) -> None:
        """Default second_path is d:\\Second-Level."""
        loader = PriceDataLoader()
        assert loader.second_path == Path("d:/Second-Level")

    def test_default_minute_path(self) -> None:
        """Default minute_path is d:\\Minute-Level."""
        loader = PriceDataLoader()
        assert loader.minute_path == Path("d:/Minute-Level")

    def test_default_daily_path(self) -> None:
        """Default daily_path is d:\\Daily-Level."""
        loader = PriceDataLoader()
        assert loader.daily_path == Path("d:/Daily-Level")

    def test_custom_paths_override_defaults(self, tmp_path: Path) -> None:
        """Custom paths override defaults."""
        custom_second = tmp_path / "custom_second"
        custom_minute = tmp_path / "custom_minute"
        custom_daily = tmp_path / "custom_daily"

        loader = PriceDataLoader(
            second_path=custom_second,
            minute_path=custom_minute,
            daily_path=custom_daily,
        )

        assert loader.second_path == custom_second
        assert loader.minute_path == custom_minute
        assert loader.daily_path == custom_daily
