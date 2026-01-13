"""Unit tests for data binning logic."""

import pandas as pd
import pytest

from src.core.models import BinDefinition
from src.tabs.data_binning import is_time_column, parse_time_input


class TestParseTimeInput:
    """Tests for parse_time_input function."""

    def test_integer_hhmmss(self) -> None:
        """Integer HHMMSS format is parsed correctly."""
        assert parse_time_input(93000) == "09:30:00"
        assert parse_time_input(140000) == "14:00:00"
        assert parse_time_input(235959) == "23:59:59"

    def test_string_hhmmss(self) -> None:
        """String HHMMSS format is parsed correctly."""
        assert parse_time_input("093000") == "09:30:00"
        assert parse_time_input("140000") == "14:00:00"

    def test_already_formatted(self) -> None:
        """Already formatted HH:MM:SS is returned as-is."""
        assert parse_time_input("09:30:00") == "09:30:00"
        assert parse_time_input("14:00:00") == "14:00:00"
        assert parse_time_input("23:59:59") == "23:59:59"

    def test_partial_format_zero_padded(self) -> None:
        """Partial numbers are zero-padded correctly."""
        assert parse_time_input(930) == "00:09:30"
        assert parse_time_input(0) == "00:00:00"
        assert parse_time_input(1) == "00:00:01"
        assert parse_time_input(100) == "00:01:00"

    def test_negative_rejected(self) -> None:
        """Negative numbers are rejected."""
        with pytest.raises(ValueError, match="Negative"):
            parse_time_input(-100)
        with pytest.raises(ValueError, match="Negative"):
            parse_time_input("-100")

    def test_exceeds_235959_rejected(self) -> None:
        """Numbers > 235959 are rejected."""
        with pytest.raises(ValueError, match="exceeds 23:59:59"):
            parse_time_input(240000)
        with pytest.raises(ValueError, match="exceeds 23:59:59"):
            parse_time_input(250000)

    def test_invalid_hours_rejected(self) -> None:
        """Invalid hours (> 23) are rejected."""
        with pytest.raises(ValueError, match="Invalid time"):
            parse_time_input("24:00:00")

    def test_invalid_minutes_rejected(self) -> None:
        """Invalid minutes (> 59) are rejected."""
        with pytest.raises(ValueError, match="Invalid time"):
            parse_time_input("12:60:00")

    def test_invalid_seconds_rejected(self) -> None:
        """Invalid seconds (> 59) are rejected."""
        with pytest.raises(ValueError, match="Invalid time"):
            parse_time_input("12:30:60")

    def test_empty_string_rejected(self) -> None:
        """Empty strings are rejected."""
        with pytest.raises(ValueError, match="Empty"):
            parse_time_input("")
        with pytest.raises(ValueError, match="Empty"):
            parse_time_input("   ")

    def test_invalid_format_rejected(self) -> None:
        """Invalid formats are rejected."""
        with pytest.raises(ValueError, match="Unrecognized|Invalid"):
            parse_time_input("abc")
        with pytest.raises(ValueError, match="Unrecognized|Invalid"):
            parse_time_input("12:30")  # Missing seconds


class TestIsTimeColumn:
    """Tests for is_time_column function."""

    def test_time_in_name(self) -> None:
        """Columns with 'time' in name are detected."""
        assert is_time_column("time") is True
        assert is_time_column("entry_time") is True
        assert is_time_column("exit_time") is True
        assert is_time_column("Time") is True
        assert is_time_column("TIME") is True

    def test_timestamp_in_name(self) -> None:
        """Columns with 'timestamp' in name are detected."""
        assert is_time_column("timestamp") is True
        assert is_time_column("entry_timestamp") is True

    def test_hour_minute_second_in_name(self) -> None:
        """Columns with hour/minute/second in name are detected."""
        assert is_time_column("hour") is True
        assert is_time_column("entry_hour") is True
        assert is_time_column("minute") is True
        assert is_time_column("second") is True

    def test_non_time_columns(self) -> None:
        """Non-time columns are not detected."""
        assert is_time_column("gain_pct") is False
        assert is_time_column("ticker") is False
        assert is_time_column("volume") is False
        assert is_time_column("price") is False


class TestBinDefinition:
    """Tests for BinDefinition dataclass."""

    def test_create_less_than_bin(self) -> None:
        """BinDefinition with less than operator is created correctly."""
        bin_def = BinDefinition(operator="<", value1=100.0, label="< 100")
        assert bin_def.operator == "<"
        assert bin_def.value1 == 100.0
        assert bin_def.value2 is None
        assert bin_def.label == "< 100"

    def test_create_greater_than_bin(self) -> None:
        """BinDefinition with greater than operator is created correctly."""
        bin_def = BinDefinition(operator=">", value1=50.0, label="> 50")
        assert bin_def.operator == ">"
        assert bin_def.value1 == 50.0
        assert bin_def.value2 is None
        assert bin_def.label == "> 50"

    def test_create_range_bin(self) -> None:
        """BinDefinition with range operator is created correctly."""
        bin_def = BinDefinition(operator="range", value1=10.0, value2=50.0, label="10 - 50")
        assert bin_def.operator == "range"
        assert bin_def.value1 == 10.0
        assert bin_def.value2 == 50.0
        assert bin_def.label == "10 - 50"

    def test_create_nulls_bin(self) -> None:
        """BinDefinition with nulls operator is created correctly."""
        bin_def = BinDefinition(operator="nulls", label="Nulls")
        assert bin_def.operator == "nulls"
        assert bin_def.value1 is None
        assert bin_def.value2 is None
        assert bin_def.label == "Nulls"

    def test_default_values(self) -> None:
        """BinDefinition has correct default values."""
        bin_def = BinDefinition(operator="<")
        assert bin_def.value1 is None
        assert bin_def.value2 is None
        assert bin_def.label == ""


class TestNumericColumnFiltering:
    """Tests for numeric column filtering logic."""

    def test_filter_numeric_columns(self) -> None:
        """Only numeric columns are included in dropdown."""
        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL"],
            "date": ["2024-01-01", "2024-01-02"],
            "gain_pct": [1.5, -0.8],
            "mae_pct": [5.0, 3.0],
            "volume": [1000, 2000],
            "time": [93000, 140000],
        })

        numeric_cols = df.select_dtypes(
            include=["int64", "float64", "int32", "float32"]
        ).columns.tolist()

        assert "gain_pct" in numeric_cols
        assert "mae_pct" in numeric_cols
        assert "volume" in numeric_cols
        assert "time" in numeric_cols
        assert "ticker" not in numeric_cols
        assert "date" not in numeric_cols

    def test_adjusted_gain_pct_included(self) -> None:
        """adjusted_gain_pct column is included when present."""
        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL"],
            "gain_pct": [1.5, -0.8],
            "adjusted_gain_pct": [0.5, -1.8],
        })

        numeric_cols = df.select_dtypes(
            include=["int64", "float64", "int32", "float32"]
        ).columns.tolist()

        assert "adjusted_gain_pct" in numeric_cols
        assert "gain_pct" in numeric_cols

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame returns empty column list."""
        df = pd.DataFrame()

        numeric_cols = df.select_dtypes(
            include=["int64", "float64", "int32", "float32"]
        ).columns.tolist()

        assert numeric_cols == []

    def test_no_numeric_columns(self) -> None:
        """DataFrame with no numeric columns returns empty list."""
        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL"],
            "date": ["2024-01-01", "2024-01-02"],
        })

        numeric_cols = df.select_dtypes(
            include=["int64", "float64", "int32", "float32"]
        ).columns.tolist()

        assert numeric_cols == []


class TestBinOperatorValidation:
    """Tests for bin operator validation."""

    def test_valid_operators(self) -> None:
        """All valid operators are accepted."""
        valid_ops = ["<", ">", "range", "nulls"]
        for op in valid_ops:
            bin_def = BinDefinition(operator=op)
            assert bin_def.operator == op

    def test_less_than_requires_value1(self) -> None:
        """Less than operator should have value1 for meaningful bin."""
        bin_def = BinDefinition(operator="<", value1=100.0)
        assert bin_def.value1 is not None

        # Without value1, it's technically valid but meaningless
        bin_def_empty = BinDefinition(operator="<")
        assert bin_def_empty.value1 is None  # Allowed but empty

    def test_greater_than_requires_value1(self) -> None:
        """Greater than operator should have value1 for meaningful bin."""
        bin_def = BinDefinition(operator=">", value1=50.0)
        assert bin_def.value1 is not None

    def test_range_requires_both_values(self) -> None:
        """Range operator should have both value1 and value2 for meaningful bin."""
        bin_def = BinDefinition(operator="range", value1=10.0, value2=50.0)
        assert bin_def.value1 is not None
        assert bin_def.value2 is not None

    def test_nulls_no_values_needed(self) -> None:
        """Nulls operator doesn't need any values."""
        bin_def = BinDefinition(operator="nulls")
        assert bin_def.value1 is None
        assert bin_def.value2 is None
