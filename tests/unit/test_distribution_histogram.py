"""Unit tests for DistributionHistogram component."""

import numpy as np

from src.ui.components.distribution_histogram import DistributionHistogram


def create_sample_gains(n: int = 100, mean: float = 2.0, std: float = 3.0) -> list[float]:
    """Create sample gain percentages for testing.

    Args:
        n: Number of data points.
        mean: Mean of the distribution.
        std: Standard deviation.

    Returns:
        List of gain percentages.
    """
    np.random.seed(42)
    return list(np.random.normal(mean, std, n))


class TestCalculateBins:
    """Tests for DistributionHistogram._calculate_bins() method."""

    def test_calculate_bins_returns_edges_and_counts(self, qtbot):
        """_calculate_bins() returns bin edges and counts arrays."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        gains = create_sample_gains(50)
        bin_edges, counts = histogram._calculate_bins(gains, bin_size=1.0)

        assert isinstance(bin_edges, np.ndarray)
        assert isinstance(counts, np.ndarray)
        assert len(bin_edges) == len(counts) + 1  # n+1 edges for n bins

    def test_calculate_bins_auto_uses_freedman_diaconis(self, qtbot):
        """_calculate_bins() with auto bin size uses Freedman-Diaconis rule."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        gains = create_sample_gains(100)
        bin_edges, counts = histogram._calculate_bins(gains, bin_size=None)

        # Auto binning should create reasonable number of bins
        assert len(bin_edges) >= 2
        assert len(counts) >= 1
        # Total counts should equal data points
        assert np.sum(counts) == 100

    def test_calculate_bins_fixed_05_percent(self, qtbot):
        """_calculate_bins() with 0.5% bin size creates correct width bins."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        gains = [0.0, 0.5, 1.0, 1.5, 2.0]
        bin_edges, counts = histogram._calculate_bins(gains, bin_size=0.5)

        # Each bin should be 0.5 wide
        bin_widths = np.diff(bin_edges)
        np.testing.assert_allclose(bin_widths, 0.5, atol=1e-10)

    def test_calculate_bins_fixed_1_percent(self, qtbot):
        """_calculate_bins() with 1% bin size creates correct width bins."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        gains = [0.0, 1.0, 2.0, 3.0, 4.0]
        bin_edges, counts = histogram._calculate_bins(gains, bin_size=1.0)

        bin_widths = np.diff(bin_edges)
        np.testing.assert_allclose(bin_widths, 1.0, atol=1e-10)

    def test_calculate_bins_fixed_2_percent(self, qtbot):
        """_calculate_bins() with 2% bin size creates correct width bins."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        gains = [0.0, 2.0, 4.0, 6.0, 8.0]
        bin_edges, counts = histogram._calculate_bins(gains, bin_size=2.0)

        bin_widths = np.diff(bin_edges)
        np.testing.assert_allclose(bin_widths, 2.0, atol=1e-10)

    def test_calculate_bins_fixed_5_percent(self, qtbot):
        """_calculate_bins() with 5% bin size creates correct width bins."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        gains = [0.0, 5.0, 10.0, 15.0, 20.0]
        bin_edges, counts = histogram._calculate_bins(gains, bin_size=5.0)

        bin_widths = np.diff(bin_edges)
        np.testing.assert_allclose(bin_widths, 5.0, atol=1e-10)

    def test_calculate_bins_empty_data_returns_empty_arrays(self, qtbot):
        """_calculate_bins() with empty data returns empty arrays."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        bin_edges, counts = histogram._calculate_bins([], bin_size=1.0)

        assert len(bin_edges) == 0
        assert len(counts) == 0

    def test_calculate_bins_iqr_zero_fallback(self, qtbot):
        """_calculate_bins() handles IQR=0 (identical values) with fallback."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        # All identical values - IQR will be 0
        gains = [5.0] * 20
        bin_edges, counts = histogram._calculate_bins(gains, bin_size=None)

        # Should still produce valid bins
        assert len(bin_edges) >= 2
        assert np.sum(counts) == 20

    def test_calculate_bins_single_value_fallback(self, qtbot):
        """_calculate_bins() handles single value with fallback bin width."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        gains = [5.0]
        bin_edges, counts = histogram._calculate_bins(gains, bin_size=None)

        # Should still produce valid bins with 1.0 fallback width
        assert len(bin_edges) >= 2
        assert np.sum(counts) == 1


class TestSetBaseline:
    """Tests for DistributionHistogram.set_baseline() method."""

    def test_set_baseline_updates_bars(self, qtbot):
        """set_baseline() updates baseline BarGraphItem."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        gains = create_sample_gains(50, mean=3.0, std=2.0)
        histogram.set_baseline(gains, mean=3.0, median=2.8)

        # Verify baseline bars have data
        opts = histogram._baseline_bars.opts
        assert len(opts["x"]) > 0
        assert len(opts["height"]) > 0

    def test_set_baseline_none_clears_baseline(self, qtbot):
        """set_baseline(None) clears baseline bars."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        # First set data
        gains = create_sample_gains(50)
        histogram.set_baseline(gains, mean=2.0, median=1.8)

        # Then clear
        histogram.set_baseline(None, None, None)

        opts = histogram._baseline_bars.opts
        assert len(opts["x"]) == 0
        assert len(opts["height"]) == 0


class TestSetFiltered:
    """Tests for DistributionHistogram.set_filtered() method."""

    def test_set_filtered_updates_bars(self, qtbot):
        """set_filtered() updates filtered BarGraphItem."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        gains = create_sample_gains(30, mean=4.0, std=1.5)
        histogram.set_filtered(gains, mean=4.0, median=3.9)

        opts = histogram._filtered_bars.opts
        assert len(opts["x"]) > 0
        assert len(opts["height"]) > 0

    def test_set_filtered_none_clears_filtered(self, qtbot):
        """set_filtered(None) clears filtered bars."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        # First set data
        gains = create_sample_gains(30)
        histogram.set_filtered(gains, mean=2.0, median=1.8)

        # Then clear
        histogram.set_filtered(None, None, None)

        opts = histogram._filtered_bars.opts
        assert len(opts["x"]) == 0
        assert len(opts["height"]) == 0


class TestClear:
    """Tests for DistributionHistogram.clear() method."""

    def test_clear_resets_all_data(self, qtbot):
        """clear() resets all histogram data."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        # Set both baseline and filtered
        histogram.set_baseline(create_sample_gains(50), mean=2.0, median=1.8)
        histogram.set_filtered(create_sample_gains(30), mean=3.0, median=2.9)

        # Clear everything
        histogram.clear()

        # Verify both are cleared
        baseline_opts = histogram._baseline_bars.opts
        filtered_opts = histogram._filtered_bars.opts
        assert len(baseline_opts["x"]) == 0
        assert len(filtered_opts["x"]) == 0

        # Internal state cleared
        assert histogram._baseline_gains is None
        assert histogram._filtered_gains is None
        assert histogram._baseline_mean is None
        assert histogram._filtered_mean is None


class TestMeanMedianLines:
    """Tests for mean/median reference lines."""

    def test_mean_line_updates_on_set_baseline(self, qtbot):
        """Mean line position updates when baseline is set."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        histogram.set_baseline(create_sample_gains(50), mean=5.5, median=5.0)

        assert histogram._mean_line.value() == 5.5
        assert histogram._mean_line.isVisible()

    def test_median_line_updates_on_set_baseline(self, qtbot):
        """Median line position updates when baseline is set."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        histogram.set_baseline(create_sample_gains(50), mean=5.5, median=5.0)

        assert histogram._median_line.value() == 5.0
        assert histogram._median_line.isVisible()

    def test_mean_line_uses_filtered_when_available(self, qtbot):
        """Mean line uses filtered value when filtered data is set."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        histogram.set_baseline(create_sample_gains(50), mean=5.0, median=4.8)
        histogram.set_filtered(create_sample_gains(30), mean=7.0, median=6.8)

        # Should use filtered mean
        assert histogram._mean_line.value() == 7.0

    def test_mean_line_hidden_when_no_data(self, qtbot):
        """Mean line is hidden when no mean value available."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        histogram.set_baseline(create_sample_gains(50), mean=None, median=None)

        assert not histogram._mean_line.isVisible()

    def test_median_line_hidden_when_no_data(self, qtbot):
        """Median line is hidden when no median value available."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        histogram.set_baseline(create_sample_gains(50), mean=5.0, median=None)

        assert not histogram._median_line.isVisible()


class TestRenderFailedSignal:
    """Tests for render_failed signal emission."""

    def test_render_failed_not_emitted_on_valid_data(self, qtbot):
        """render_failed signal not emitted for valid data."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        # Track signal emissions
        signals_received = []
        histogram.render_failed.connect(lambda msg: signals_received.append(msg))

        histogram.set_baseline(create_sample_gains(50), mean=2.0, median=1.8)

        assert len(signals_received) == 0

    def test_render_failed_signal_exists(self, qtbot):
        """render_failed signal is defined and connectable."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        # Should be able to connect without error
        handler_called = []
        histogram.render_failed.connect(lambda msg: handler_called.append(msg))
        assert histogram.render_failed is not None
