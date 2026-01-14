"""Tests for percentile calculation utility."""

import numpy as np
import pandas as pd
import pytest

from src.ui.utils.percentile import calculate_iqr_bounds, calculate_percentile_bounds


class TestCalculatePercentileBounds:
    """Tests for calculate_percentile_bounds function."""

    def test_symmetric_percentile_95(self) -> None:
        """95th percentile clips 2.5% from each tail."""
        data = pd.Series(range(100))
        lower, upper = calculate_percentile_bounds(data, 95.0)
        assert lower == pytest.approx(2.475, rel=0.01)
        assert upper == pytest.approx(97.025, rel=0.01)

    def test_symmetric_percentile_99(self) -> None:
        """99th percentile clips 0.5% from each tail."""
        data = pd.Series(range(100))
        lower, upper = calculate_percentile_bounds(data, 99.0)
        assert lower == pytest.approx(0.495, rel=0.01)
        assert upper == pytest.approx(99.005, rel=0.01)

    def test_handles_extreme_outlier(self) -> None:
        """Clips extreme outlier at 13 trillion."""
        normal_data = list(range(-100, 101))  # -100 to 100
        normal_data.append(13_000_000_000_000)  # 13 trillion outlier
        data = pd.Series(normal_data)

        lower, upper = calculate_percentile_bounds(data, 99.0)
        # Should clip the outlier, upper bound should be close to 100
        assert upper < 1000  # Way below 13 trillion

    def test_handles_nan_values(self) -> None:
        """NaN values are ignored in calculation."""
        data = pd.Series([1.0, 2.0, np.nan, 3.0, 4.0, 5.0, np.nan])
        lower, upper = calculate_percentile_bounds(data, 95.0)
        assert not np.isnan(lower)
        assert not np.isnan(upper)

    def test_handles_inf_values(self) -> None:
        """Infinite values are ignored in calculation."""
        data = pd.Series([1.0, 2.0, np.inf, 3.0, 4.0, -np.inf, 5.0])
        lower, upper = calculate_percentile_bounds(data, 95.0)
        assert np.isfinite(lower)
        assert np.isfinite(upper)

    def test_empty_series_returns_none(self) -> None:
        """Empty series returns (None, None)."""
        data = pd.Series([], dtype=float)
        lower, upper = calculate_percentile_bounds(data, 95.0)
        assert lower is None
        assert upper is None

    def test_all_nan_returns_none(self) -> None:
        """All-NaN series returns (None, None)."""
        data = pd.Series([np.nan, np.nan, np.nan])
        lower, upper = calculate_percentile_bounds(data, 95.0)
        assert lower is None
        assert upper is None

    def test_single_value(self) -> None:
        """Single value returns same value for both bounds."""
        data = pd.Series([42.0])
        lower, upper = calculate_percentile_bounds(data, 95.0)
        assert lower == 42.0
        assert upper == 42.0


class TestCalculateIqrBounds:
    """Tests for IQR-based outlier detection."""

    def test_normal_distribution_no_outliers(self) -> None:
        """Normal data without outliers keeps full range."""
        data = pd.Series(range(1, 101))  # 1 to 100
        lower, upper = calculate_iqr_bounds(data)
        # Should include most of the data
        assert lower <= 1
        assert upper >= 100

    def test_detects_extreme_outlier(self) -> None:
        """Extreme outlier is excluded from bounds."""
        normal_data = list(range(-100, 101))  # -100 to 100
        normal_data.append(13_000_000_000_000)  # 13 trillion outlier
        data = pd.Series(normal_data)

        lower, upper = calculate_iqr_bounds(data)
        # Upper should exclude the 13T outlier
        assert upper < 1000

    def test_symmetric_outliers(self) -> None:
        """Handles outliers on both tails."""
        normal_data = list(range(0, 100))
        normal_data.extend([-1000, 1000])  # Outliers on both ends
        data = pd.Series(normal_data)

        lower, upper = calculate_iqr_bounds(data)
        assert lower > -500
        assert upper < 500

    def test_empty_returns_none(self) -> None:
        """Empty series returns (None, None)."""
        data = pd.Series([], dtype=float)
        lower, upper = calculate_iqr_bounds(data)
        assert lower is None
        assert upper is None

    def test_handles_nan_inf(self) -> None:
        """NaN and inf values are excluded."""
        data = pd.Series([1.0, 2.0, np.nan, 50.0, np.inf, 100.0])
        lower, upper = calculate_iqr_bounds(data)
        assert np.isfinite(lower)
        assert np.isfinite(upper)

    def test_custom_multiplier(self) -> None:
        """Custom IQR multiplier adjusts sensitivity."""
        data = pd.Series(list(range(100)) + [500])

        # Tight multiplier (1.0) excludes more
        lower_tight, upper_tight = calculate_iqr_bounds(data, multiplier=1.0)

        # Loose multiplier (3.0) includes more
        lower_loose, upper_loose = calculate_iqr_bounds(data, multiplier=3.0)

        assert upper_tight < upper_loose
