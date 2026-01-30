"""Tests for Statistics tab gradient coloring system."""

import math
import pytest
from PyQt6.QtGui import QColor


class TestLerpColor:
    """Tests for color interpolation."""

    def test_lerp_color_at_zero_returns_first_color(self):
        """t=0 should return color1."""
        from src.tabs.statistics_tab import lerp_color

        color1 = QColor(255, 0, 0, 100)
        color2 = QColor(0, 255, 0, 200)

        result = lerp_color(color1, color2, 0.0)

        assert result.red() == 255
        assert result.green() == 0
        assert result.blue() == 0
        assert result.alpha() == 100

    def test_lerp_color_at_one_returns_second_color(self):
        """t=1 should return color2."""
        from src.tabs.statistics_tab import lerp_color

        color1 = QColor(255, 0, 0, 100)
        color2 = QColor(0, 255, 0, 200)

        result = lerp_color(color1, color2, 1.0)

        assert result.red() == 0
        assert result.green() == 255
        assert result.blue() == 0
        assert result.alpha() == 200

    def test_lerp_color_at_half_returns_midpoint(self):
        """t=0.5 should return midpoint."""
        from src.tabs.statistics_tab import lerp_color

        color1 = QColor(0, 0, 0, 0)
        color2 = QColor(100, 200, 50, 100)

        result = lerp_color(color1, color2, 0.5)

        assert result.red() == 50
        assert result.green() == 100
        assert result.blue() == 25
        assert result.alpha() == 50

    def test_lerp_color_clamps_t_below_zero(self):
        """t < 0 should clamp to 0."""
        from src.tabs.statistics_tab import lerp_color

        color1 = QColor(100, 100, 100, 100)
        color2 = QColor(200, 200, 200, 200)

        result = lerp_color(color1, color2, -0.5)

        assert result.red() == 100

    def test_lerp_color_clamps_t_above_one(self):
        """t > 1 should clamp to 1."""
        from src.tabs.statistics_tab import lerp_color

        color1 = QColor(100, 100, 100, 100)
        color2 = QColor(200, 200, 200, 200)

        result = lerp_color(color1, color2, 1.5)

        assert result.red() == 200


class TestCalculateGradientColors:
    """Tests for gradient color calculation."""

    def test_min_value_returns_low_gradient(self):
        """Minimum value should return red gradient."""
        from src.tabs.statistics_tab import calculate_gradient_colors, GRADIENT_LOW

        bg, text = calculate_gradient_colors(0.0, 0.0, 100.0)

        assert bg.red() == GRADIENT_LOW.red()
        assert bg.green() == GRADIENT_LOW.green()

    def test_max_value_returns_high_gradient(self):
        """Maximum value should return green gradient."""
        from src.tabs.statistics_tab import calculate_gradient_colors, GRADIENT_HIGH

        bg, text = calculate_gradient_colors(100.0, 0.0, 100.0)

        assert bg.red() == GRADIENT_HIGH.red()
        assert bg.green() == GRADIENT_HIGH.green()

    def test_mid_value_returns_neutral_gradient(self):
        """Middle value should return neutral gradient."""
        from src.tabs.statistics_tab import calculate_gradient_colors, GRADIENT_MID

        bg, text = calculate_gradient_colors(50.0, 0.0, 100.0)

        assert bg.red() == GRADIENT_MID.red()
        assert bg.green() == GRADIENT_MID.green()

    def test_equal_min_max_returns_mid(self):
        """When min equals max, return mid gradient."""
        from src.tabs.statistics_tab import calculate_gradient_colors, GRADIENT_MID

        bg, text = calculate_gradient_colors(50.0, 50.0, 50.0)

        assert bg.red() == GRADIENT_MID.red()

    def test_inverted_gradient_swaps_colors(self):
        """Inverted gradient should swap low and high."""
        from src.tabs.statistics_tab import calculate_gradient_colors

        bg_normal, _ = calculate_gradient_colors(100.0, 0.0, 100.0, invert=False)
        bg_inverted, _ = calculate_gradient_colors(100.0, 0.0, 100.0, invert=True)

        assert bg_normal.green() > bg_inverted.green()
        assert bg_inverted.red() > bg_normal.red()
