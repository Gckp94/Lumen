"""Unit tests for FileLoader class."""

from pathlib import Path

import pandas as pd
import pytest

from src.core.exceptions import FileLoadError
from src.core.file_loader import FileLoader


class TestFileLoaderSupportedExtensions:
    """Tests for SUPPORTED_EXTENSIONS constant."""

    def test_supported_extensions_contains_xlsx(self) -> None:
        """FileLoader supports .xlsx files."""
        assert ".xlsx" in FileLoader.SUPPORTED_EXTENSIONS

    def test_supported_extensions_contains_xls(self) -> None:
        """FileLoader supports .xls files."""
        assert ".xls" in FileLoader.SUPPORTED_EXTENSIONS

    def test_supported_extensions_contains_csv(self) -> None:
        """FileLoader supports .csv files."""
        assert ".csv" in FileLoader.SUPPORTED_EXTENSIONS

    def test_supported_extensions_contains_parquet(self) -> None:
        """FileLoader supports .parquet files."""
        assert ".parquet" in FileLoader.SUPPORTED_EXTENSIONS


class TestFileLoaderGetSheetNames:
    """Tests for get_sheet_names method."""

    def test_get_sheet_names_returns_list(self, sample_excel_file: Path) -> None:
        """get_sheet_names returns list of sheet names."""
        loader = FileLoader()
        sheet_names = loader.get_sheet_names(sample_excel_file)
        assert isinstance(sheet_names, list)
        assert len(sheet_names) == 2
        assert "Sheet1" in sheet_names
        assert "Sheet2" in sheet_names

    def test_get_sheet_names_non_excel_raises_error(self, sample_csv_file: Path) -> None:
        """get_sheet_names raises error for non-Excel files."""
        loader = FileLoader()
        with pytest.raises(FileLoadError, match="non-Excel file"):
            loader.get_sheet_names(sample_csv_file)

    def test_get_sheet_names_missing_file_raises_error(self) -> None:
        """get_sheet_names raises error for missing file."""
        loader = FileLoader()
        with pytest.raises(FileLoadError, match="File not found"):
            loader.get_sheet_names(Path("/nonexistent/file.xlsx"))


class TestFileLoaderLoad:
    """Tests for load method."""

    def test_load_csv_returns_dataframe(self, sample_csv_file: Path) -> None:
        """Load CSV file returns pandas DataFrame."""
        loader = FileLoader()
        df = loader.load(sample_csv_file)
        assert len(df) == 3
        assert "ticker" in df.columns
        assert "date" in df.columns
        assert "gain_pct" in df.columns

    def test_load_excel_returns_dataframe(self, sample_excel_file: Path) -> None:
        """Load Excel file returns pandas DataFrame."""
        loader = FileLoader()
        df = loader.load(sample_excel_file)
        assert len(df) == 2
        assert "ticker" in df.columns

    def test_load_excel_with_sheet_name(self, sample_excel_file: Path) -> None:
        """Load Excel file with specific sheet name."""
        loader = FileLoader()
        df = loader.load(sample_excel_file, sheet="Sheet2")
        assert len(df) == 2
        assert "ticker" in df.columns

    def test_load_parquet_returns_dataframe(self, sample_parquet_file: Path) -> None:
        """Load Parquet file returns pandas DataFrame."""
        loader = FileLoader()
        df = loader.load(sample_parquet_file)
        assert len(df) == 2
        assert "ticker" in df.columns

    def test_load_missing_file_raises_error(self) -> None:
        """Loading missing file raises FileLoadError."""
        loader = FileLoader()
        with pytest.raises(FileLoadError, match="File not found"):
            loader.load(Path("/nonexistent/file.csv"))

    def test_load_unsupported_extension_raises_error(self, tmp_path: Path) -> None:
        """Loading unsupported extension raises FileLoadError."""
        bad_file = tmp_path / "test.txt"
        bad_file.write_text("data")
        loader = FileLoader()
        with pytest.raises(FileLoadError, match="Unsupported file type"):
            loader.load(bad_file)


class TestPrecomputedColumns:
    """Tests for pre-computed columns on load."""

    def test_time_minutes_precomputed(self) -> None:
        """Loaded DataFrame should have _time_minutes column."""
        loader = FileLoader()
        # Create test data with time column
        df = pd.DataFrame({
            "time": ["09:30:00", "10:15:00"],
            "gain_pct": [0.01, -0.02],
        })

        result = loader._precompute_columns(df, {"time": "time"})

        assert "_time_minutes" in result.columns
        assert result["_time_minutes"].iloc[0] == 570  # 9*60 + 30
        assert result["_time_minutes"].iloc[1] == 615  # 10*60 + 15

    def test_time_minutes_with_short_format(self) -> None:
        """Time in HH:MM format should also work."""
        loader = FileLoader()
        df = pd.DataFrame({
            "time": ["09:30", "14:45"],
            "gain_pct": [0.01, -0.02],
        })

        result = loader._precompute_columns(df, {"time": "time"})

        assert result["_time_minutes"].iloc[0] == 570  # 9*60 + 30
        assert result["_time_minutes"].iloc[1] == 885  # 14*60 + 45

    def test_time_minutes_with_missing_time_column(self) -> None:
        """DataFrame without time column should not have _time_minutes."""
        loader = FileLoader()
        df = pd.DataFrame({
            "gain_pct": [0.01, -0.02],
        })

        result = loader._precompute_columns(df, {"time": None})

        assert "_time_minutes" not in result.columns

    def test_time_minutes_with_na_values(self) -> None:
        """NA values in time column should produce NA in _time_minutes."""
        loader = FileLoader()
        df = pd.DataFrame({
            "time": ["09:30:00", None, "10:15:00"],
            "gain_pct": [0.01, 0.0, -0.02],
        })

        result = loader._precompute_columns(df, {"time": "time"})

        assert result["_time_minutes"].iloc[0] == 570
        assert pd.isna(result["_time_minutes"].iloc[1])
        assert result["_time_minutes"].iloc[2] == 615

    def test_precompute_does_not_modify_original(self) -> None:
        """Precompute should not modify the original DataFrame."""
        loader = FileLoader()
        df = pd.DataFrame({
            "time": ["09:30:00"],
            "gain_pct": [0.01],
        })
        original_columns = list(df.columns)

        loader._precompute_columns(df, {"time": "time"})

        assert list(df.columns) == original_columns
        assert "_time_minutes" not in df.columns
