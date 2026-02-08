"""File loading functionality for Excel, CSV, and Parquet files."""

import logging
from pathlib import Path

import pandas as pd

from src.core.exceptions import FileLoadError

logger = logging.getLogger(__name__)


class FileLoader:
    """Load Excel, CSV, and Parquet files into DataFrames."""

    SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".parquet"}

    def get_sheet_names(self, path: Path) -> list[str]:
        """Get sheet names from an Excel file.

        Args:
            path: Path to the Excel file.

        Returns:
            List of sheet names in the file.

        Raises:
            FileLoadError: If the file cannot be read or is not an Excel file.
        """
        suffix = path.suffix.lower()
        if suffix not in {".xlsx", ".xls"}:
            raise FileLoadError(f"Cannot get sheet names from non-Excel file: {path.name}")

        try:
            excel_file = pd.ExcelFile(path)
            return [str(name) for name in excel_file.sheet_names]
        except FileNotFoundError:
            raise FileLoadError(f"File not found: {path.name}") from None
        except PermissionError:
            raise FileLoadError("Cannot access file. Check permissions.") from None
        except Exception as e:
            logger.error("Failed to read Excel file: %s", e)
            raise FileLoadError("Unable to read file. The file may be corrupted.") from None

    def load(self, path: Path, sheet: str | None = None) -> pd.DataFrame:
        """Load a file into a DataFrame.

        Args:
            path: Path to the file to load.
            sheet: Sheet name for Excel files. If None, uses the first sheet.

        Returns:
            DataFrame containing the file data.

        Raises:
            FileLoadError: If the file cannot be loaded.
        """
        suffix = path.suffix.lower()

        if suffix not in self.SUPPORTED_EXTENSIONS:
            raise FileLoadError(
                f"Unsupported file type: {suffix}. "
                f"Supported types: {', '.join(sorted(self.SUPPORTED_EXTENSIONS))}"
            )

        try:
            df: pd.DataFrame
            if suffix == ".csv":
                df = pd.read_csv(path)
            elif suffix == ".parquet":
                df = pd.read_parquet(path)
            elif suffix == ".xlsx":
                # Use first sheet (index 0) if no sheet specified
                sheet_to_load = sheet if sheet is not None else 0
                result = pd.read_excel(path, sheet_name=sheet_to_load, engine="openpyxl")
                assert isinstance(result, pd.DataFrame)
                df = result
            elif suffix == ".xls":
                # Use first sheet (index 0) if no sheet specified
                sheet_to_load = sheet if sheet is not None else 0
                result = pd.read_excel(path, sheet_name=sheet_to_load, engine="xlrd")
                assert isinstance(result, pd.DataFrame)
                df = result
            else:
                raise FileLoadError(f"Unsupported file type: {suffix}")

            logger.info("Loaded %d rows from %s", len(df), path.name)
            return df

        except FileNotFoundError:
            logger.error("File not found: %s", path)
            raise FileLoadError(f"File not found: {path.name}") from None
        except PermissionError:
            logger.error("Permission denied: %s", path)
            raise FileLoadError("Cannot access file. Check permissions.") from None
        except FileLoadError:
            raise
        except Exception as e:
            logger.error("Failed to load file: %s", e)
            raise FileLoadError("Unable to read file. The file may be corrupted.") from None

    def _precompute_columns(
        self, df: pd.DataFrame, column_mapping: dict[str, str | None]
    ) -> pd.DataFrame:
        """Pre-compute derived columns to avoid repeated recalculation.

        Args:
            df: DataFrame to augment.
            column_mapping: Column mapping with at least 'time' key.

        Returns:
            DataFrame with pre-computed columns added.
        """
        result = df.copy()

        # Pre-compute time in minutes if time column exists
        time_col = column_mapping.get("time")
        if time_col and time_col in result.columns:
            result["_time_minutes"] = self._parse_time_to_minutes(result[time_col])

        return result

    def _parse_time_to_minutes(self, time_series: pd.Series) -> pd.Series:
        """Convert time strings to minutes since midnight.

        Args:
            time_series: Series of time strings (HH:MM:SS or HH:MM).

        Returns:
            Series of integer minutes.
        """

        def parse_single(t: object) -> int | None:
            if pd.isna(t):
                return None
            if isinstance(t, str):
                parts = t.split(":")
                hours = int(parts[0])
                minutes = int(parts[1]) if len(parts) > 1 else 0
                return hours * 60 + minutes
            return None

        return time_series.apply(parse_single)
