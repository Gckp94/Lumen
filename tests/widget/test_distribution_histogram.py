"""Widget tests for DistributionHistogram and HistogramDialog."""

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton
from pytestqt.qtbot import QtBot

from src.ui.components.distribution_histogram import (
    DistributionHistogram,
    HistogramDialog,
    _HistogramPanel,
)
from src.ui.constants import Colors


def create_sample_gains(n: int = 50, mean: float = 2.0, std: float = 3.0) -> list[float]:
    """Create sample gain percentages for testing."""
    np.random.seed(42)
    return list(np.random.normal(mean, std, n))


class TestDistributionHistogramBarColors:
    """Tests for histogram bar colors."""

    def test_baseline_bars_use_signal_blue_color(self, qtbot: QtBot) -> None:
        """Baseline bars use SIGNAL_BLUE color."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        histogram.set_baseline(create_sample_gains(50), mean=2.0, median=1.8)

        # Check brush color (74, 158, 255) is SIGNAL_BLUE (#4A9EFF)
        brush = histogram._baseline_bars.opts["brush"]
        color = brush.color()
        assert color.red() == 74
        assert color.green() == 158
        assert color.blue() == 255

    def test_baseline_bars_have_50_percent_alpha(self, qtbot: QtBot) -> None:
        """Baseline bars have 50% alpha (128)."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        histogram.set_baseline(create_sample_gains(50), mean=2.0, median=1.8)

        brush = histogram._baseline_bars.opts["brush"]
        color = brush.color()
        assert color.alpha() == 128

    def test_filtered_bars_use_signal_cyan_color(self, qtbot: QtBot) -> None:
        """Filtered bars use SIGNAL_CYAN color."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        histogram.set_filtered(create_sample_gains(30), mean=3.0, median=2.8)

        brush = histogram._filtered_bars.opts["brush"]
        color = brush.color()
        # SIGNAL_CYAN is #00FFD4 = (0, 255, 212)
        assert color.red() == 0
        assert color.green() == 255
        assert color.blue() == 212


class TestBinningDropdownInteraction:
    """Tests for binning dropdown interactions."""

    def test_binning_dropdown_changes_rebins_data(self, qtbot: QtBot) -> None:
        """Changing binning dropdown rebins histogram data."""
        panel = _HistogramPanel("winner")
        qtbot.addWidget(panel)

        panel.set_baseline(create_sample_gains(100), mean=2.0, median=1.8)

        # Change to 5% bins (should have fewer bins than auto)
        panel._bin_combo.setCurrentText("5%")

        # Verify rebinning occurred
        new_edges = panel._histogram._baseline_bin_edges
        new_bin_count = len(new_edges) - 1 if new_edges is not None else 0

        # With 5% bins, we expect fewer bins than auto
        assert new_bin_count > 0
        # Bin width should be 5.0
        if new_edges is not None and len(new_edges) > 1:
            bin_width = new_edges[1] - new_edges[0]
            np.testing.assert_allclose(bin_width, 5.0, atol=1e-10)

    def test_binning_dropdown_has_all_options(self, qtbot: QtBot) -> None:
        """Binning dropdown contains all required options."""
        panel = _HistogramPanel("winner")
        qtbot.addWidget(panel)

        options = [panel._bin_combo.itemText(i) for i in range(panel._bin_combo.count())]
        assert "Auto" in options
        assert "0.5%" in options
        assert "1%" in options
        assert "2%" in options
        assert "5%" in options

    def test_binning_dropdown_default_is_auto(self, qtbot: QtBot) -> None:
        """Binning dropdown defaults to Auto."""
        panel = _HistogramPanel("winner")
        qtbot.addWidget(panel)

        assert panel._bin_combo.currentText() == "Auto"


class TestShowBaselineToggle:
    """Tests for Show Baseline checkbox toggle."""

    def test_show_baseline_toggle_hides_baseline_bars(self, qtbot: QtBot) -> None:
        """Unchecking Show Baseline hides baseline bars."""
        panel = _HistogramPanel("winner")
        qtbot.addWidget(panel)

        panel.set_baseline(create_sample_gains(50), mean=2.0, median=1.8)

        # Initially visible
        assert panel._histogram._baseline_bars.isVisible()

        # Uncheck the checkbox
        panel._baseline_checkbox.setChecked(False)

        # Bars should be hidden
        assert not panel._histogram._baseline_bars.isVisible()

    def test_show_baseline_toggle_shows_baseline_bars(self, qtbot: QtBot) -> None:
        """Checking Show Baseline shows baseline bars."""
        panel = _HistogramPanel("winner")
        qtbot.addWidget(panel)

        panel.set_baseline(create_sample_gains(50), mean=2.0, median=1.8)

        # Uncheck then recheck
        panel._baseline_checkbox.setChecked(False)
        panel._baseline_checkbox.setChecked(True)

        assert panel._histogram._baseline_bars.isVisible()

    def test_show_baseline_default_is_checked(self, qtbot: QtBot) -> None:
        """Show Baseline checkbox is checked by default."""
        panel = _HistogramPanel("winner")
        qtbot.addWidget(panel)

        assert panel._baseline_checkbox.isChecked()


class TestTooltipOnHover:
    """Tests for tooltip on bar hover."""

    def test_tooltip_item_exists(self, qtbot: QtBot) -> None:
        """Tooltip TextItem exists on histogram."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        assert histogram._tooltip is not None

    def test_tooltip_initially_hidden(self, qtbot: QtBot) -> None:
        """Tooltip is initially hidden."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        assert not histogram._tooltip.isVisible()

    def test_get_bar_tooltip_returns_text_for_bar(self, qtbot: QtBot) -> None:
        """_get_bar_tooltip returns tooltip text when over a bar."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        gains = [1.0, 1.5, 2.0, 2.5, 3.0]
        histogram.set_baseline(gains, mean=2.0, median=2.0)

        # Get bin info - find a position inside a bin with count > 0
        if histogram._baseline_bin_edges is not None and len(histogram._baseline_bin_edges) > 1:
            # Use the first bin with a count
            for i, count in enumerate(histogram._baseline_counts):
                if count > 0:
                    bin_left = histogram._baseline_bin_edges[i]
                    bin_right = histogram._baseline_bin_edges[i + 1]
                    x = (bin_left + bin_right) / 2
                    y = count / 2  # Middle of bar height
                    tooltip = histogram._get_bar_tooltip(x, y)
                    assert tooltip is not None
                    assert "Bin:" in tooltip
                    assert "Count:" in tooltip
                    break

    def test_get_bar_tooltip_returns_none_outside_bars(self, qtbot: QtBot) -> None:
        """_get_bar_tooltip returns None when not over any bar."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        gains = [1.0, 2.0, 3.0]
        histogram.set_baseline(gains, mean=2.0, median=2.0)

        # Position way outside data range
        tooltip = histogram._get_bar_tooltip(100.0, 100.0)
        assert tooltip is None


class TestMeanLineVisual:
    """Tests for mean reference line visual properties."""

    def test_mean_line_is_visible_with_data(self, qtbot: QtBot) -> None:
        """Mean line is visible when mean value is set."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        histogram.set_baseline(create_sample_gains(50), mean=5.0, median=4.8)

        assert histogram._mean_line.isVisible()

    def test_mean_line_has_amber_color(self, qtbot: QtBot) -> None:
        """Mean line uses SIGNAL_AMBER color."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        pen = histogram._mean_line.pen
        color = pen.color()
        # SIGNAL_AMBER is #FFAA00 = (255, 170, 0)
        assert color.red() == 255
        assert color.green() == 170
        assert color.blue() == 0

    def test_mean_line_is_dashed(self, qtbot: QtBot) -> None:
        """Mean line uses dashed style."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        pen = histogram._mean_line.pen
        assert pen.style() == Qt.PenStyle.DashLine


class TestMedianLineVisual:
    """Tests for median reference line visual properties."""

    def test_median_line_is_visible_with_data(self, qtbot: QtBot) -> None:
        """Median line is visible when median value is set."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        histogram.set_baseline(create_sample_gains(50), mean=5.0, median=4.8)

        assert histogram._median_line.isVisible()

    def test_median_line_has_text_primary_color(self, qtbot: QtBot) -> None:
        """Median line uses TEXT_PRIMARY color."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        pen = histogram._median_line.pen
        color = pen.color()
        # TEXT_PRIMARY is #F4F4F8 = (244, 244, 248)
        assert color.red() == 244
        assert color.green() == 244
        assert color.blue() == 248

    def test_median_line_is_dotted(self, qtbot: QtBot) -> None:
        """Median line uses dotted style."""
        histogram = DistributionHistogram()
        qtbot.addWidget(histogram)

        pen = histogram._median_line.pen
        assert pen.style() == Qt.PenStyle.DotLine


class TestHistogramDialogTitle:
    """Tests for HistogramDialog title."""

    def test_dialog_winner_title(self, qtbot: QtBot) -> None:
        """Winner dialog has correct title."""
        dialog = HistogramDialog(
            card_type="winner",
            baseline_gains=create_sample_gains(50),
            filtered_gains=None,
            baseline_mean=2.0,
            baseline_median=1.8,
        )
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Winner Distribution"

    def test_dialog_loser_title(self, qtbot: QtBot) -> None:
        """Loser dialog has correct title."""
        dialog = HistogramDialog(
            card_type="loser",
            baseline_gains=create_sample_gains(50, mean=-3.0),
            filtered_gains=None,
            baseline_mean=-3.0,
            baseline_median=-2.8,
        )
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Loser Distribution"


class TestHistogramDialogContent:
    """Tests for HistogramDialog content."""

    def test_dialog_contains_histogram_panel(self, qtbot: QtBot) -> None:
        """Dialog contains a _HistogramPanel."""
        dialog = HistogramDialog(
            card_type="winner",
            baseline_gains=create_sample_gains(50),
            filtered_gains=None,
            baseline_mean=2.0,
            baseline_median=1.8,
        )
        qtbot.addWidget(dialog)

        assert dialog._panel is not None
        assert isinstance(dialog._panel, _HistogramPanel)

    def test_dialog_displays_baseline_data(self, qtbot: QtBot) -> None:
        """Dialog displays baseline histogram data."""
        baseline_gains = create_sample_gains(50)
        dialog = HistogramDialog(
            card_type="winner",
            baseline_gains=baseline_gains,
            filtered_gains=None,
            baseline_mean=2.0,
            baseline_median=1.8,
        )
        qtbot.addWidget(dialog)

        # Verify baseline data is set
        histogram = dialog._panel._histogram
        assert histogram._baseline_gains == baseline_gains

    def test_dialog_displays_filtered_data(self, qtbot: QtBot) -> None:
        """Dialog displays filtered histogram data when provided."""
        baseline_gains = create_sample_gains(50)
        filtered_gains = create_sample_gains(30, mean=3.0)
        dialog = HistogramDialog(
            card_type="winner",
            baseline_gains=baseline_gains,
            filtered_gains=filtered_gains,
            baseline_mean=2.0,
            baseline_median=1.8,
            filtered_mean=3.0,
            filtered_median=2.9,
        )
        qtbot.addWidget(dialog)

        histogram = dialog._panel._histogram
        assert histogram._filtered_gains == filtered_gains


class TestHistogramDialogCloseButton:
    """Tests for HistogramDialog close button."""

    def test_close_button_exists(self, qtbot: QtBot) -> None:
        """Dialog has a Close button."""
        dialog = HistogramDialog(
            card_type="winner",
            baseline_gains=create_sample_gains(50),
            filtered_gains=None,
            baseline_mean=2.0,
            baseline_median=1.8,
        )
        qtbot.addWidget(dialog)

        close_btn = dialog.findChild(QPushButton)
        assert close_btn is not None
        assert close_btn.text() == "Close"

    def test_close_button_dismisses_dialog(self, qtbot: QtBot) -> None:
        """Clicking Close button dismisses the dialog."""
        dialog = HistogramDialog(
            card_type="winner",
            baseline_gains=create_sample_gains(50),
            filtered_gains=None,
            baseline_mean=2.0,
            baseline_median=1.8,
        )
        qtbot.addWidget(dialog)
        dialog.show()

        close_btn = dialog.findChild(QPushButton)
        close_btn.click()

        # Dialog should be closed (result set)
        assert dialog.result() == 1  # QDialog.Accepted


class TestHistogramDialogSize:
    """Tests for HistogramDialog size."""

    def test_dialog_minimum_size(self, qtbot: QtBot) -> None:
        """Dialog has minimum size of 600x400."""
        dialog = HistogramDialog(
            card_type="winner",
            baseline_gains=create_sample_gains(50),
            filtered_gains=None,
            baseline_mean=2.0,
            baseline_median=1.8,
        )
        qtbot.addWidget(dialog)

        assert dialog.minimumWidth() == 600
        assert dialog.minimumHeight() == 400


class TestHistogramPanelTitleColor:
    """Tests for _HistogramPanel title color."""

    def test_winner_panel_has_cyan_title(self, qtbot: QtBot) -> None:
        """Winner panel title uses SIGNAL_CYAN color."""
        panel = _HistogramPanel("winner")
        qtbot.addWidget(panel)

        style = panel._title_label.styleSheet()
        assert Colors.SIGNAL_CYAN in style

    def test_loser_panel_has_coral_title(self, qtbot: QtBot) -> None:
        """Loser panel title uses SIGNAL_CORAL color."""
        panel = _HistogramPanel("loser")
        qtbot.addWidget(panel)

        style = panel._title_label.styleSheet()
        assert Colors.SIGNAL_CORAL in style
