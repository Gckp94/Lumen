"""Visual regression tests for Monte Carlo chart components.

These tests capture screenshots of chart components and compare them
against baseline images to detect visual regressions.

Uses pytest-qt screenshot capabilities for image capture.
"""

from pathlib import Path

import numpy as np
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from src.ui.components.equity_confidence_chart import EquityConfidenceBandChart
from src.ui.components.mc_histogram import MonteCarloHistogram
from src.ui.components.monte_carlo_charts import MonteCarloChartsSection

# Directory for baseline screenshots
BASELINE_DIR = Path(__file__).parent / "baselines"


def create_sample_percentiles(num_trades: int = 100) -> np.ndarray:
    """Create sample percentile data for testing."""
    np.random.seed(42)
    base_equity = 100000

    x = np.arange(num_trades)
    noise_scale = 1000 * np.sqrt(x + 1)

    p50 = base_equity + 100 * x
    p25 = p50 - 0.5 * noise_scale
    p5 = p50 - 1.5 * noise_scale
    p75 = p50 + 0.5 * noise_scale
    p95 = p50 + 1.5 * noise_scale

    return np.column_stack([p5, p25, p50, p75, p95])


def create_sample_distribution(
    n: int = 1000, mean: float = 0.0, std: float = 1.0
) -> np.ndarray:
    """Create sample distribution data for testing."""
    np.random.seed(42)
    return np.random.normal(mean, std, n)


def capture_widget_screenshot(widget: QWidget, filename: str) -> Path:
    """Capture a screenshot of a widget.

    Args:
        widget: Widget to capture.
        filename: Output filename (without path).

    Returns:
        Path to the captured screenshot.
    """
    # Ensure baselines directory exists
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)

    screenshot_path = BASELINE_DIR / filename
    pixmap = widget.grab()
    pixmap.save(str(screenshot_path), "PNG")

    return screenshot_path


def compare_screenshots(actual: Path, baseline: Path, threshold: float = 0.01) -> bool:
    """Compare two screenshots for visual similarity.

    Args:
        actual: Path to actual screenshot.
        baseline: Path to baseline screenshot.
        threshold: Maximum allowed difference (0-1).

    Returns:
        True if images are similar within threshold.
    """
    from PyQt6.QtGui import QImage

    actual_img = QImage(str(actual))
    baseline_img = QImage(str(baseline))

    if actual_img.size() != baseline_img.size():
        return False

    # Compare pixel-by-pixel
    total_pixels = actual_img.width() * actual_img.height()
    diff_count = 0

    for x in range(actual_img.width()):
        for y in range(actual_img.height()):
            if actual_img.pixel(x, y) != baseline_img.pixel(x, y):
                diff_count += 1

    diff_ratio = diff_count / total_pixels
    return diff_ratio <= threshold


class TestEquityConfidenceBandChartScreenshots:
    """Visual regression tests for EquityConfidenceBandChart."""

    def test_confidence_bands_render_correctly(self, qtbot: QtBot) -> None:
        """Capture baseline screenshot of confidence band chart."""
        chart = EquityConfidenceBandChart()
        chart.setFixedSize(800, 300)
        qtbot.addWidget(chart)
        chart.show()

        percentiles = create_sample_percentiles(100)
        chart.set_data(percentiles)

        qtbot.wait(200)  # Allow rendering

        # Capture screenshot
        screenshot = capture_widget_screenshot(
            chart, "equity_confidence_bands.png"
        )

        assert screenshot.exists()
        assert screenshot.stat().st_size > 0

    def test_empty_chart_render(self, qtbot: QtBot) -> None:
        """Capture baseline screenshot of empty chart."""
        chart = EquityConfidenceBandChart()
        chart.setFixedSize(800, 300)
        qtbot.addWidget(chart)
        chart.show()

        qtbot.wait(200)

        screenshot = capture_widget_screenshot(
            chart, "equity_confidence_empty.png"
        )

        assert screenshot.exists()


class TestMonteCarloHistogramScreenshots:
    """Visual regression tests for MonteCarloHistogram."""

    def test_basic_histogram_render(self, qtbot: QtBot) -> None:
        """Capture baseline screenshot of basic histogram."""
        histogram = MonteCarloHistogram(title="Test Distribution")
        histogram.setFixedSize(400, 200)
        qtbot.addWidget(histogram)
        histogram.show()

        data = create_sample_distribution(500, mean=10, std=2)
        histogram.set_data(data, mean=10.0, median=9.8)

        qtbot.wait(200)

        screenshot = capture_widget_screenshot(
            histogram, "mc_histogram_basic.png"
        )

        assert screenshot.exists()

    def test_gradient_histogram_render(self, qtbot: QtBot) -> None:
        """Capture baseline screenshot of gradient-colored histogram."""
        histogram = MonteCarloHistogram(
            title="Max Drawdown",
            color_gradient=True,
            x_format="percent",
        )
        histogram.setFixedSize(400, 200)
        qtbot.addWidget(histogram)
        histogram.show()

        # Create drawdown-like distribution (negative values)
        data = create_sample_distribution(500, mean=-15, std=5)
        histogram.set_data(data, median=-15.0)

        qtbot.wait(200)

        screenshot = capture_widget_screenshot(
            histogram, "mc_histogram_gradient.png"
        )

        assert screenshot.exists()

    def test_reference_colored_histogram_render(self, qtbot: QtBot) -> None:
        """Capture baseline screenshot of reference-colored histogram."""
        histogram = MonteCarloHistogram(
            title="Sharpe Ratio",
            x_format="ratio",
        )
        histogram.setFixedSize(400, 200)
        qtbot.addWidget(histogram)
        histogram.show()

        data = create_sample_distribution(500, mean=1.2, std=0.5)
        histogram.set_data(data, mean=1.2, median=1.15)
        histogram.set_reference_line(1.0, "good_threshold")
        histogram.set_color_by_reference(1.0)

        qtbot.wait(200)

        screenshot = capture_widget_screenshot(
            histogram, "mc_histogram_reference.png"
        )

        assert screenshot.exists()

    def test_histogram_with_confidence_shading(self, qtbot: QtBot) -> None:
        """Capture baseline screenshot of histogram with confidence shading."""
        histogram = MonteCarloHistogram(
            title="Final Equity",
            x_format="dollar",
        )
        histogram.setFixedSize(400, 200)
        qtbot.addWidget(histogram)
        histogram.show()

        data = create_sample_distribution(500, mean=120000, std=20000)
        histogram.set_data(data, mean=120000, median=118000)
        histogram.add_confidence_shading(80000, 160000)

        qtbot.wait(200)

        screenshot = capture_widget_screenshot(
            histogram, "mc_histogram_confidence.png"
        )

        assert screenshot.exists()


class TestMonteCarloChartsSectionScreenshots:
    """Visual regression tests for MonteCarloChartsSection."""

    def test_charts_section_layout(self, qtbot: QtBot) -> None:
        """Capture baseline screenshot of full charts section layout."""
        section = MonteCarloChartsSection()
        section.setFixedSize(1200, 700)
        qtbot.addWidget(section)
        section.show()

        qtbot.wait(200)

        screenshot = capture_widget_screenshot(
            section, "mc_charts_section_empty.png"
        )

        assert screenshot.exists()


@pytest.mark.slow
class TestVisualRegressionComparison:
    """Tests that compare current renders against baselines.

    These tests require baseline images to exist. Run capture tests
    first to generate baselines, then enable these for CI.
    """

    @pytest.mark.skip(reason="Baseline images not yet established")
    def test_confidence_bands_no_regression(self, qtbot: QtBot) -> None:
        """Verify confidence band chart matches baseline."""
        chart = EquityConfidenceBandChart()
        chart.setFixedSize(800, 300)
        qtbot.addWidget(chart)
        chart.show()

        percentiles = create_sample_percentiles(100)
        chart.set_data(percentiles)

        qtbot.wait(200)

        # Capture current screenshot
        current = capture_widget_screenshot(
            chart, "equity_confidence_bands_current.png"
        )

        baseline = BASELINE_DIR / "equity_confidence_bands.png"

        if baseline.exists():
            assert compare_screenshots(current, baseline), (
                "Visual regression detected in confidence band chart"
            )

    @pytest.mark.skip(reason="Baseline images not yet established")
    def test_histogram_no_regression(self, qtbot: QtBot) -> None:
        """Verify histogram matches baseline."""
        histogram = MonteCarloHistogram(title="Test Distribution")
        histogram.setFixedSize(400, 200)
        qtbot.addWidget(histogram)
        histogram.show()

        data = create_sample_distribution(500, mean=10, std=2)
        histogram.set_data(data, mean=10.0, median=9.8)

        qtbot.wait(200)

        current = capture_widget_screenshot(
            histogram, "mc_histogram_basic_current.png"
        )

        baseline = BASELINE_DIR / "mc_histogram_basic.png"

        if baseline.exists():
            assert compare_screenshots(current, baseline), (
                "Visual regression detected in histogram"
            )
