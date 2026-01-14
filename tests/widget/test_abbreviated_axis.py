"""Tests for AbbreviatedAxisItem."""

from __future__ import annotations

from pytestqt.qtbot import QtBot

from src.ui.components.abbreviated_axis import AbbreviatedAxisItem


class TestAbbreviatedAxisItem:
    """Tests for AbbreviatedAxisItem tick formatting."""

    def test_tick_strings_billions(self, qtbot: QtBot) -> None:
        """Billion values format with B suffix."""
        axis = AbbreviatedAxisItem(orientation="left")
        values = [1_000_000_000, 2_500_000_000]
        result = axis.tickStrings(values, scale=1, spacing=1)
        assert result == ["1B", "2.5B"]

    def test_tick_strings_millions(self, qtbot: QtBot) -> None:
        """Million values format with M suffix."""
        axis = AbbreviatedAxisItem(orientation="left")
        values = [1_000_000, 5_500_000, 10_000_000]
        result = axis.tickStrings(values, scale=1, spacing=1)
        assert result == ["1M", "5.5M", "10M"]

    def test_tick_strings_thousands(self, qtbot: QtBot) -> None:
        """Thousand values format with K suffix."""
        axis = AbbreviatedAxisItem(orientation="bottom")
        values = [1_000, 25_000, 100_000]
        result = axis.tickStrings(values, scale=1, spacing=1)
        assert result == ["1K", "25K", "100K"]

    def test_tick_strings_small_values(self, qtbot: QtBot) -> None:
        """Small values display without suffix."""
        axis = AbbreviatedAxisItem(orientation="left")
        values = [0, 50, 500]
        result = axis.tickStrings(values, scale=1, spacing=1)
        assert result == ["0", "50", "500"]

    def test_tick_strings_negative(self, qtbot: QtBot) -> None:
        """Negative values preserve sign."""
        axis = AbbreviatedAxisItem(orientation="left")
        values = [-1_000_000, 0, 1_000_000]
        result = axis.tickStrings(values, scale=1, spacing=1)
        assert result == ["-1M", "0", "1M"]
