"""Unit tests for PriceDataLoader class."""

from datetime import datetime
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
