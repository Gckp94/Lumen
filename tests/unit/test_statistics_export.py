# tests/unit/test_statistics_export.py
"""Tests for statistics tab export date normalization."""

import pytest
import pandas as pd


class TestScalingExportDateNormalization:
    """Test that scaling exports normalize dates to ISO format."""

    def test_day_first_dates_normalized_to_iso(self) -> None:
        """DD/MM/YYYY dates should be converted to YYYY-MM-DD."""
        df = pd.DataFrame({
            "date": ["05/02/2021", "25/12/2021", "01/03/2022"],
            "gain_pct": [0.05, -0.02, 0.03],
        })

        # Apply normalization (same logic as in export)
        parsed_dates = pd.to_datetime(
            df["date"],
            format='mixed',
            dayfirst=True,
            errors='coerce'
        )
        df["date"] = parsed_dates.dt.strftime('%Y-%m-%d')

        assert df["date"].iloc[0] == "2021-02-05"  # Feb 5
        assert df["date"].iloc[1] == "2021-12-25"  # Dec 25
        assert df["date"].iloc[2] == "2022-03-01"  # Mar 1

    def test_iso_dates_preserved(self) -> None:
        """YYYY-MM-DD dates should remain unchanged."""
        df = pd.DataFrame({
            "date": ["2021-02-05", "2021-12-25", "2022-03-01"],
            "gain_pct": [0.05, -0.02, 0.03],
        })

        parsed_dates = pd.to_datetime(
            df["date"],
            format='mixed',
            dayfirst=True,
            errors='coerce'
        )
        df["date"] = parsed_dates.dt.strftime('%Y-%m-%d')

        assert df["date"].iloc[0] == "2021-02-05"
        assert df["date"].iloc[1] == "2021-12-25"
        assert df["date"].iloc[2] == "2022-03-01"

    def test_month_first_with_disambiguation(self) -> None:
        """Month-first dates with day > 12 should be detected correctly."""
        # 12/25/2021 can only be Dec 25 (month-first), not 12th day of 25th month
        df = pd.DataFrame({
            "date": ["12/25/2021"],  # This is Dec 25 in US format
            "gain_pct": [0.05],
        })

        # With dayfirst=True, pandas will try day-first but 25 > 12 months
        # so it will fall back to interpreting as month-first
        parsed_dates = pd.to_datetime(
            df["date"],
            format='mixed',
            dayfirst=True,
            errors='coerce'
        )
        df["date"] = parsed_dates.dt.strftime('%Y-%m-%d')

        assert df["date"].iloc[0] == "2021-12-25"  # Dec 25

    def test_handles_invalid_dates_gracefully(self) -> None:
        """Invalid dates should result in NaN after strftime."""
        df = pd.DataFrame({
            "date": ["2021-02-05", "invalid_date", "2022-03-01"],
            "gain_pct": [0.05, -0.02, 0.03],
        })

        parsed_dates = pd.to_datetime(
            df["date"],
            format='mixed',
            dayfirst=True,
            errors='coerce'
        )
        df["date"] = parsed_dates.dt.strftime('%Y-%m-%d')

        assert df["date"].iloc[0] == "2021-02-05"
        assert pd.isna(df["date"].iloc[1])  # Invalid becomes NaN after strftime
        assert df["date"].iloc[2] == "2022-03-01"

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame should not cause errors."""
        df = pd.DataFrame({
            "date": pd.Series([], dtype=str),
            "gain_pct": pd.Series([], dtype=float),
        })

        parsed_dates = pd.to_datetime(
            df["date"],
            format='mixed',
            dayfirst=True,
            errors='coerce'
        )
        df["date"] = parsed_dates.dt.strftime('%Y-%m-%d')

        assert len(df) == 0
