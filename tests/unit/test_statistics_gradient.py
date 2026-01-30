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


class TestGradientStyler:
    """Tests for GradientStyler class."""

    def test_set_and_get_column_range(self):
        """Should store and retrieve column ranges."""
        from src.tabs.statistics_tab import GradientStyler, GRADIENT_LOW

        styler = GradientStyler()
        styler.set_column_range("EG %", -5.0, 15.0)

        # Min value should get low gradient
        bg, _ = styler.get_cell_colors("EG %", -5.0)
        assert bg.red() == GRADIENT_LOW.red()

    def test_excluded_column_returns_default(self):
        """Excluded columns should return default colors."""
        from src.tabs.statistics_tab import GradientStyler, CELL_DEFAULT_BG

        styler = GradientStyler()
        styler.set_column_range("Level", 10, 100)

        bg, text = styler.get_cell_colors("Level", 50)

        assert bg.alpha() == CELL_DEFAULT_BG.alpha()

    def test_none_value_returns_default(self):
        """None values should return default colors."""
        from src.tabs.statistics_tab import GradientStyler, CELL_DEFAULT_BG

        styler = GradientStyler()
        styler.set_column_range("EG %", 0, 100)

        bg, text = styler.get_cell_colors("EG %", None)

        assert bg.alpha() == CELL_DEFAULT_BG.alpha()

    def test_nan_value_returns_default(self):
        """NaN values should return default colors."""
        from src.tabs.statistics_tab import GradientStyler, CELL_DEFAULT_BG

        styler = GradientStyler()
        styler.set_column_range("EG %", 0, 100)

        bg, text = styler.get_cell_colors("EG %", float('nan'))

        assert bg.alpha() == CELL_DEFAULT_BG.alpha()

    def test_unknown_column_returns_default(self):
        """Unknown columns should return default colors."""
        from src.tabs.statistics_tab import GradientStyler, CELL_DEFAULT_BG

        styler = GradientStyler()
        # Don't register any range

        bg, text = styler.get_cell_colors("Unknown Column", 50)

        assert bg.alpha() == CELL_DEFAULT_BG.alpha()

    def test_clear_ranges(self):
        """clear_ranges should remove all stored ranges."""
        from src.tabs.statistics_tab import GradientStyler, CELL_DEFAULT_BG

        styler = GradientStyler()
        styler.set_column_range("EG %", 0, 100)
        styler.clear_ranges()

        bg, text = styler.get_cell_colors("EG %", 50)

        # Should return default since range was cleared
        assert bg.alpha() == CELL_DEFAULT_BG.alpha()


class TestComputeColumnRanges:
    """Tests for compute_column_ranges_from_df helper."""

    def test_computes_ranges_from_dataframe(self):
        """Should compute min/max for numeric columns."""
        import pandas as pd
        from src.tabs.statistics_tab import GradientStyler, compute_column_ranges_from_df

        df = pd.DataFrame({
            "Level": ["10%", "20%", "30%"],
            "EG %": [5.0, 10.0, 15.0],
            "Win %": [50.0, 60.0, 70.0],
        })

        styler = GradientStyler()
        compute_column_ranges_from_df(df, styler, exclude_first_column=True)

        # Check EG % range was set
        assert "EG %" in styler._column_ranges
        assert styler._column_ranges["EG %"] == (5.0, 15.0)

    def test_excludes_first_column(self):
        """Should skip first column when exclude_first_column=True."""
        import pandas as pd
        from src.tabs.statistics_tab import GradientStyler, compute_column_ranges_from_df

        df = pd.DataFrame({
            "Level": [10, 20, 30],  # Numeric but should be excluded
            "EG %": [5.0, 10.0, 15.0],
        })

        styler = GradientStyler()
        compute_column_ranges_from_df(df, styler, exclude_first_column=True)

        # Level should not be in ranges
        assert "Level" not in styler._column_ranges

    def test_handles_nan_values(self):
        """Should ignore NaN when computing ranges."""
        import pandas as pd
        import numpy as np
        from src.tabs.statistics_tab import GradientStyler, compute_column_ranges_from_df

        df = pd.DataFrame({
            "Label": ["A", "B", "C"],
            "Value": [10.0, np.nan, 30.0],
        })

        styler = GradientStyler()
        compute_column_ranges_from_df(df, styler, exclude_first_column=True)

        # Range should be computed from non-NaN values
        assert styler._column_ranges["Value"] == (10.0, 30.0)

    def test_excludes_gradient_excluded_columns(self):
        """Should skip columns in GRADIENT_EXCLUDED_COLUMNS."""
        import pandas as pd
        from src.tabs.statistics_tab import GradientStyler, compute_column_ranges_from_df

        df = pd.DataFrame({
            "Label": ["A", "B", "C"],
            "Level": [10, 20, 30],  # In GRADIENT_EXCLUDED_COLUMNS
            "EG %": [5.0, 10.0, 15.0],
        })

        styler = GradientStyler()
        compute_column_ranges_from_df(df, styler, exclude_first_column=True)

        # Level should not be in ranges because it's in GRADIENT_EXCLUDED_COLUMNS
        assert "Level" not in styler._column_ranges
        # EG % should be included
        assert "EG %" in styler._column_ranges

    def test_includes_first_column_when_not_excluded(self):
        """Should include first column when exclude_first_column=False."""
        import pandas as pd
        from src.tabs.statistics_tab import GradientStyler, compute_column_ranges_from_df

        df = pd.DataFrame({
            "Value1": [10.0, 20.0, 30.0],
            "Value2": [5.0, 10.0, 15.0],
        })

        styler = GradientStyler()
        compute_column_ranges_from_df(df, styler, exclude_first_column=False)

        # Both columns should be in ranges
        assert "Value1" in styler._column_ranges
        assert "Value2" in styler._column_ranges
