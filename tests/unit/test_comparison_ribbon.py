"""Unit tests for ComparisonRibbon delta calculation logic."""

import pytest

from src.ui.components.comparison_ribbon import (
    _calculate_delta,
    _get_delta_color,
)
from src.ui.constants import Colors


class TestCalculateDelta:
    """Tests for _calculate_delta function."""

    def test_calculate_delta_trades_positive(self) -> None:
        """Delta for trades is absolute difference (positive)."""
        delta, display = _calculate_delta(100, 80, "trades")
        assert delta == 20
        assert display == "+20"

    def test_calculate_delta_trades_negative(self) -> None:
        """Delta for trades is absolute difference (negative)."""
        delta, display = _calculate_delta(50, 80, "trades")
        assert delta == -30
        assert display == "-30"

    def test_calculate_delta_trades_zero(self) -> None:
        """Delta for trades handles zero difference."""
        delta, display = _calculate_delta(100, 100, "trades")
        assert delta == 0.0
        assert display == "0"

    def test_calculate_delta_win_rate_positive(self) -> None:
        """Delta for win_rate is percentage point difference (positive)."""
        delta, display = _calculate_delta(70.5, 65.2, "win_rate")
        assert delta == pytest.approx(5.3)
        assert display == "+5.3pp"

    def test_calculate_delta_win_rate_negative(self) -> None:
        """Delta for win_rate is percentage point difference (negative)."""
        delta, display = _calculate_delta(55.0, 65.2, "win_rate")
        assert delta == pytest.approx(-10.2)
        assert display == "-10.2pp"

    def test_calculate_delta_win_rate_zero(self) -> None:
        """Delta for win_rate handles zero difference."""
        delta, display = _calculate_delta(65.2, 65.2, "win_rate")
        assert delta == 0.0
        assert display == "0pp"

    def test_calculate_delta_ev_positive(self) -> None:
        """Delta for ev is percentage point difference (positive)."""
        delta, display = _calculate_delta(3.5, 2.1, "ev")
        assert delta == pytest.approx(1.4)
        assert display == "+1.4pp"

    def test_calculate_delta_ev_negative(self) -> None:
        """Delta for ev is percentage point difference (negative)."""
        delta, display = _calculate_delta(1.5, 2.1, "ev")
        assert delta == pytest.approx(-0.6)
        assert display == "-0.6pp"

    def test_calculate_delta_kelly_positive(self) -> None:
        """Delta for kelly is percentage point difference (positive)."""
        delta, display = _calculate_delta(15.5, 12.1, "kelly")
        assert delta == pytest.approx(3.4)
        assert display == "+3.4pp"

    def test_calculate_delta_kelly_negative(self) -> None:
        """Delta for kelly is percentage point difference (negative)."""
        delta, display = _calculate_delta(10.0, 12.1, "kelly")
        assert delta == pytest.approx(-2.1)
        assert display == "-2.1pp"

    def test_calculate_delta_filtered_none(self) -> None:
        """Delta handles None filtered value gracefully."""
        delta, display = _calculate_delta(None, 100, "trades")
        assert delta is None
        assert display == "N/A"

    def test_calculate_delta_baseline_none(self) -> None:
        """Delta handles None baseline value gracefully."""
        delta, display = _calculate_delta(100, None, "trades")
        assert delta is None
        assert display == "N/A"

    def test_calculate_delta_both_none(self) -> None:
        """Delta handles both values None gracefully."""
        delta, display = _calculate_delta(None, None, "trades")
        assert delta is None
        assert display == "N/A"


class TestGetDeltaColor:
    """Tests for _get_delta_color function."""

    def test_positive_delta_returns_cyan(self) -> None:
        """Positive delta returns SIGNAL_CYAN (improvement)."""
        color = _get_delta_color(5.0)
        assert color == Colors.SIGNAL_CYAN

    def test_negative_delta_returns_coral(self) -> None:
        """Negative delta returns SIGNAL_CORAL (decline)."""
        color = _get_delta_color(-5.0)
        assert color == Colors.SIGNAL_CORAL

    def test_zero_delta_returns_secondary(self) -> None:
        """Zero delta returns TEXT_SECONDARY (neutral)."""
        color = _get_delta_color(0.0)
        assert color == Colors.TEXT_SECONDARY

    def test_none_delta_returns_secondary(self) -> None:
        """None delta returns TEXT_SECONDARY."""
        color = _get_delta_color(None)
        assert color == Colors.TEXT_SECONDARY

    def test_small_positive_delta_returns_cyan(self) -> None:
        """Small positive delta (0.01) returns SIGNAL_CYAN."""
        color = _get_delta_color(0.01)
        assert color == Colors.SIGNAL_CYAN

    def test_small_negative_delta_returns_coral(self) -> None:
        """Small negative delta (-0.01) returns SIGNAL_CORAL."""
        color = _get_delta_color(-0.01)
        assert color == Colors.SIGNAL_CORAL


class TestDeltaColorMappingAllMetrics:
    """Tests verifying all 4 metrics use 'higher is better' logic."""

    def test_trades_higher_is_better(self) -> None:
        """Higher trades count shows as improvement (cyan)."""
        delta, _ = _calculate_delta(100, 80, "trades")
        color = _get_delta_color(delta)
        assert color == Colors.SIGNAL_CYAN

    def test_win_rate_higher_is_better(self) -> None:
        """Higher win rate shows as improvement (cyan)."""
        delta, _ = _calculate_delta(70.0, 60.0, "win_rate")
        color = _get_delta_color(delta)
        assert color == Colors.SIGNAL_CYAN

    def test_ev_higher_is_better(self) -> None:
        """Higher EV shows as improvement (cyan)."""
        delta, _ = _calculate_delta(3.0, 2.0, "ev")
        color = _get_delta_color(delta)
        assert color == Colors.SIGNAL_CYAN

    def test_kelly_higher_is_better(self) -> None:
        """Higher Kelly shows as improvement (cyan)."""
        delta, _ = _calculate_delta(15.0, 12.0, "kelly")
        color = _get_delta_color(delta)
        assert color == Colors.SIGNAL_CYAN
