"""Tests for axis bounds data filtering."""

import pandas as pd
import pytest


class TestAxisBoundsFilter:
    """Test axis bounds filter out-of-range data."""

    def test_filter_by_x_bounds(self):
        """Rows outside X bounds are excluded."""
        df = pd.DataFrame({
            "x_col": [-100, 0, 50, 100, 300_000_000_000],  # outlier at end
            "y_col": [1, 2, 3, 4, 5],
        })

        # Import after creating test data
        from src.tabs.feature_explorer import FeatureExplorerTab

        # Filter to x_col between -100 and 100
        result = FeatureExplorerTab._apply_bounds_filter(
            df,
            x_column="x_col",
            y_column="y_col",
            x_min=-100,
            x_max=100,
            y_min=None,
            y_max=None,
        )

        assert len(result) == 4  # Outlier row removed
        assert 300_000_000_000 not in result["x_col"].values

    def test_filter_by_y_bounds(self):
        """Rows outside Y bounds are excluded."""
        df = pd.DataFrame({
            "x_col": [1, 2, 3, 4, 5],
            "y_col": [-50, 0, 25, 50, 1_000_000],  # outlier at end
        })

        from src.tabs.feature_explorer import FeatureExplorerTab

        result = FeatureExplorerTab._apply_bounds_filter(
            df,
            x_column="x_col",
            y_column="y_col",
            x_min=None,
            x_max=None,
            y_min=-50,
            y_max=50,
        )

        assert len(result) == 4
        assert 1_000_000 not in result["y_col"].values

    def test_filter_by_both_bounds(self):
        """Rows outside either X or Y bounds are excluded."""
        df = pd.DataFrame({
            "x_col": [0, 50, 100, 200, 50],  # row 3 x out of bounds
            "y_col": [0, 25, 50, 25, 1000],  # row 4 y out of bounds
        })

        from src.tabs.feature_explorer import FeatureExplorerTab

        result = FeatureExplorerTab._apply_bounds_filter(
            df,
            x_column="x_col",
            y_column="y_col",
            x_min=0,
            x_max=100,
            y_min=0,
            y_max=50,
        )

        assert len(result) == 3  # Rows 3 and 4 removed

    def test_no_bounds_returns_all(self):
        """When no bounds set, all data returned."""
        df = pd.DataFrame({
            "x_col": [1, 2, 3],
            "y_col": [4, 5, 6],
        })

        from src.tabs.feature_explorer import FeatureExplorerTab

        result = FeatureExplorerTab._apply_bounds_filter(
            df,
            x_column="x_col",
            y_column="y_col",
            x_min=None,
            x_max=None,
            y_min=None,
            y_max=None,
        )

        assert len(result) == 3
