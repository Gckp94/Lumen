"""Tests for number formatting utilities."""

from __future__ import annotations

from src.ui.utils.number_format import format_number_abbreviated


class TestFormatNumberAbbreviated:
    """Tests for format_number_abbreviated function."""

    def test_billions(self) -> None:
        """Values >= 1B show B suffix."""
        assert format_number_abbreviated(1_500_000_000) == "1.5B"
        assert format_number_abbreviated(25_000_000_000) == "25B"

    def test_millions(self) -> None:
        """Values >= 1M show M suffix."""
        assert format_number_abbreviated(1_500_000) == "1.5M"
        assert format_number_abbreviated(25_000_000) == "25M"

    def test_thousands(self) -> None:
        """Values >= 1K show K suffix."""
        assert format_number_abbreviated(1_500) == "1.5K"
        assert format_number_abbreviated(25_000) == "25K"

    def test_small_numbers(self) -> None:
        """Values < 1000 show as-is."""
        assert format_number_abbreviated(500) == "500"
        assert format_number_abbreviated(0.5) == "0.5"
        assert format_number_abbreviated(0) == "0"

    def test_negative_numbers(self) -> None:
        """Negative values preserve sign."""
        assert format_number_abbreviated(-1_500_000) == "-1.5M"
        assert format_number_abbreviated(-25_000) == "-25K"

    def test_integer_display(self) -> None:
        """Whole numbers don't show decimal."""
        assert format_number_abbreviated(2_000_000) == "2M"
        assert format_number_abbreviated(5_000) == "5K"

    def test_small_decimals(self) -> None:
        """Very small decimals use precision."""
        assert format_number_abbreviated(0.005) == "0.005"
        assert format_number_abbreviated(0.12) == "0.12"

    def test_special_float_values(self) -> None:
        """Special float values handled gracefully."""
        assert format_number_abbreviated(float("inf")) == "inf"
        assert format_number_abbreviated(float("-inf")) == "-inf"
        assert format_number_abbreviated(float("nan")) == "NaN"
