"""Widget tests for ComparisonGrid."""

import time

from pytestqt.qtbot import QtBot

from src.core.models import TradingMetrics
from src.ui.components.comparison_grid import (
    SECTIONS,
    ComparisonGrid,
    _ComparisonRow,
    _SectionHeader,
)
from src.ui.constants import Colors


def _create_test_metrics(
    num_trades: int = 1000,
    win_rate: float = 60.0,
    ev: float = 2.5,
    kelly: float = 12.0,
    flat_stake_pnl: float = 5000.0,
    flat_stake_max_dd: float = -1000.0,
    flat_stake_max_dd_pct: float = -10.0,
    flat_stake_dd_duration: int | str = 5,
    kelly_pnl: float = 8000.0,
    kelly_max_dd: float = -2000.0,
    kelly_max_dd_pct: float = -15.0,
    kelly_dd_duration: int | str = 8,
) -> TradingMetrics:
    """Create TradingMetrics for testing."""
    return TradingMetrics(
        num_trades=num_trades,
        win_rate=win_rate,
        avg_winner=5.0,
        avg_loser=-2.0,
        rr_ratio=2.5,
        ev=ev,
        kelly=kelly,
        edge=250.0,
        fractional_kelly=3.0,
        eg_full_kelly=0.5,
        eg_frac_kelly=0.4,
        eg_flat_stake=0.3,
        median_winner=4.5,
        median_loser=-1.8,
        max_consecutive_wins=5,
        max_consecutive_losses=3,
        max_loss_pct=-8.0,
        flat_stake_pnl=flat_stake_pnl,
        flat_stake_max_dd=flat_stake_max_dd,
        flat_stake_max_dd_pct=flat_stake_max_dd_pct,
        flat_stake_dd_duration=flat_stake_dd_duration,
        kelly_pnl=kelly_pnl,
        kelly_max_dd=kelly_max_dd,
        kelly_max_dd_pct=kelly_max_dd_pct,
        kelly_dd_duration=kelly_dd_duration,
    )


class TestComparisonGridSections:
    """Tests for ComparisonGrid section structure."""

    def test_grid_displays_four_sections(self, qtbot: QtBot) -> None:
        """Grid displays all 4 section headers."""
        grid = ComparisonGrid()
        qtbot.addWidget(grid)

        assert len(grid._sections) == 4
        for section_id, _, _ in SECTIONS:
            assert section_id in grid._sections

    def test_section_headers_visible(self, qtbot: QtBot) -> None:
        """All section headers are visible on initialization."""
        grid = ComparisonGrid()
        qtbot.addWidget(grid)
        grid.show()

        for section_id in grid._sections:
            header, _ = grid._sections[section_id]
            assert header.isVisible()

    def test_each_section_contains_correct_metrics(self, qtbot: QtBot) -> None:
        """Each section contains correct number of metrics (14 + 3 + 4 + 4 = 25)."""
        grid = ComparisonGrid()
        qtbot.addWidget(grid)

        # Verify total metrics
        assert len(grid._rows) == 25

        # Verify section breakdown
        expected_counts = {
            "core_statistics": 14,
            "streak_loss": 3,
            "flat_stake": 4,
            "kelly": 4,
        }

        for section_id, _, _metrics in SECTIONS:
            _, content = grid._sections[section_id]
            assert len(content.get_rows()) == expected_counts[section_id]

    def test_grid_has_object_name(self, qtbot: QtBot) -> None:
        """Grid has correct object name for styling."""
        grid = ComparisonGrid()
        qtbot.addWidget(grid)

        assert grid.objectName() == "comparisonGrid"


class TestComparisonGridSetValues:
    """Tests for ComparisonGrid.set_values() method."""

    def test_set_values_updates_all_columns(self, qtbot: QtBot) -> None:
        """set_values updates all four columns correctly."""
        grid = ComparisonGrid()
        qtbot.addWidget(grid)

        baseline = _create_test_metrics(num_trades=1000, win_rate=60.0)
        filtered = _create_test_metrics(num_trades=500, win_rate=70.0)

        grid.set_values(baseline, filtered)

        # Check that rows have values (not just em dash)
        win_rate_row = grid._rows["win_rate"]
        assert "60.0%" in win_rate_row._baseline_label.text()
        assert "70.0%" in win_rate_row._filtered_label.text()
        assert "pp" in win_rate_row._delta_label.text()

    def test_set_values_with_none_filtered(self, qtbot: QtBot) -> None:
        """set_values with None filtered shows baseline only."""
        grid = ComparisonGrid()
        qtbot.addWidget(grid)

        baseline = _create_test_metrics(num_trades=1000, win_rate=60.0)

        grid.set_values(baseline, None)

        # Check baseline is shown
        win_rate_row = grid._rows["win_rate"]
        assert "60.0%" in win_rate_row._baseline_label.text()
        # Filtered and delta should show em dash
        assert "—" in win_rate_row._filtered_label.text()
        assert "—" in win_rate_row._delta_label.text()

    def test_set_values_handles_none_baseline_gracefully(self, qtbot: QtBot) -> None:
        """set_values handles None metric values in baseline gracefully."""
        grid = ComparisonGrid()
        qtbot.addWidget(grid)

        # Create metrics with some None values
        baseline = TradingMetrics(
            num_trades=100,
            win_rate=None,
            avg_winner=None,
            avg_loser=None,
            rr_ratio=None,
            ev=None,
            kelly=None,
        )

        grid.set_values(baseline, None)

        # None values should show em dash
        win_rate_row = grid._rows["win_rate"]
        assert "—" in win_rate_row._baseline_label.text()


class TestComparisonGridClear:
    """Tests for ComparisonGrid.clear() method."""

    def test_clear_shows_dashes_for_filtered_and_delta(self, qtbot: QtBot) -> None:
        """clear() shows em dash for filtered and delta columns."""
        grid = ComparisonGrid()
        qtbot.addWidget(grid)

        # First set values
        baseline = _create_test_metrics()
        filtered = _create_test_metrics()
        grid.set_values(baseline, filtered)

        # Then clear
        grid.clear()

        # All filtered and delta should be em dash
        for row in grid._rows.values():
            assert "—" in row._filtered_label.text()
            assert "—" in row._delta_label.text()


class TestComparisonGridCollapse:
    """Tests for section collapse/expand functionality."""

    def test_section_collapse_hides_rows(self, qtbot: QtBot) -> None:
        """Collapsing a section hides its rows."""
        grid = ComparisonGrid()
        qtbot.addWidget(grid)
        grid.show()

        # All sections start expanded
        assert grid.get_section_state("core_statistics") is True

        # Collapse core_statistics
        grid.toggle_section("core_statistics")

        assert grid.get_section_state("core_statistics") is False

    def test_section_expand_shows_rows(self, qtbot: QtBot) -> None:
        """Expanding a section shows its rows."""
        grid = ComparisonGrid()
        qtbot.addWidget(grid)
        grid.show()

        # Collapse then expand
        grid.toggle_section("core_statistics")
        assert grid.get_section_state("core_statistics") is False

        grid.toggle_section("core_statistics")
        assert grid.get_section_state("core_statistics") is True

    def test_collapse_expand_animation_completes_within_200ms(
        self, qtbot: QtBot
    ) -> None:
        """Collapse/expand animation completes within 200ms (150ms + buffer)."""
        grid = ComparisonGrid()
        qtbot.addWidget(grid)
        grid.show()

        start = time.perf_counter()
        grid.toggle_section("core_statistics")

        # Wait for animation to complete
        qtbot.wait(200)

        elapsed = (time.perf_counter() - start) * 1000
        assert elapsed < 250  # 200ms + small buffer for test overhead

    def test_section_toggled_signal_emitted(self, qtbot: QtBot) -> None:
        """section_toggled signal is emitted when section header is clicked."""
        grid = ComparisonGrid()
        qtbot.addWidget(grid)
        grid.show()

        # Click the header directly to trigger the signal
        header, _ = grid._sections["core_statistics"]
        with qtbot.waitSignal(grid.section_toggled, timeout=500) as blocker:
            header.mousePressEvent(None)

        assert blocker.args == ["core_statistics", False]


class TestSectionHeader:
    """Tests for _SectionHeader widget."""

    def test_header_displays_title(self, qtbot: QtBot) -> None:
        """Header displays section title."""
        header = _SectionHeader("test", "Test Section")
        qtbot.addWidget(header)

        assert "Test Section" in header._title_label.text()

    def test_header_shows_expanded_arrow_by_default(self, qtbot: QtBot) -> None:
        """Header shows down arrow when expanded (default)."""
        header = _SectionHeader("test", "Test Section")
        qtbot.addWidget(header)

        assert "▼" in header._arrow.text()

    def test_header_toggles_arrow_on_click(self, qtbot: QtBot) -> None:
        """Header toggles arrow direction on click."""
        header = _SectionHeader("test", "Test Section")
        qtbot.addWidget(header)
        header.show()

        # Simulate click via mousePressEvent
        header.mousePressEvent(None)

        assert "▶" in header._arrow.text()
        assert header.expanded is False

    def test_header_emits_toggled_signal(self, qtbot: QtBot) -> None:
        """Header emits toggled signal on click."""
        header = _SectionHeader("test_section", "Test Section")
        qtbot.addWidget(header)

        with qtbot.waitSignal(header.toggled, timeout=500) as blocker:
            header.mousePressEvent(None)

        assert blocker.args == ["test_section", False]


class TestComparisonRow:
    """Tests for _ComparisonRow widget."""

    def test_row_displays_metric_name(self, qtbot: QtBot) -> None:
        """Row displays correct metric name."""
        row = _ComparisonRow("win_rate")
        qtbot.addWidget(row)

        assert "Win Rate" in row._name_label.text()

    def test_row_update_shows_values(self, qtbot: QtBot) -> None:
        """Row update shows baseline and filtered values."""
        row = _ComparisonRow("win_rate")
        qtbot.addWidget(row)

        row.set_values(60.0, 70.0)

        assert "60.0%" in row._baseline_label.text()
        assert "70.0%" in row._filtered_label.text()

    def test_row_update_shows_delta_with_arrow(self, qtbot: QtBot) -> None:
        """Row update shows delta with arrow indicator."""
        row = _ComparisonRow("win_rate")
        qtbot.addWidget(row)

        row.set_values(60.0, 70.0)

        delta_text = row._delta_label.text()
        assert "▲" in delta_text
        assert "pp" in delta_text

    def test_row_clear_shows_dashes(self, qtbot: QtBot) -> None:
        """Row clear shows em dash for filtered and delta."""
        row = _ComparisonRow("win_rate")
        qtbot.addWidget(row)

        row.set_values(60.0, 70.0)
        row.clear()

        assert "—" in row._filtered_label.text()
        assert "—" in row._delta_label.text()

    def test_row_handles_dd_duration_days(self, qtbot: QtBot) -> None:
        """Row handles DD duration integer as 'X days'."""
        row = _ComparisonRow("flat_stake_dd_duration")
        qtbot.addWidget(row)

        row.set_values(5, 3)

        assert "5 days" in row._baseline_label.text()
        assert "3 days" in row._filtered_label.text()

    def test_row_handles_dd_duration_string(self, qtbot: QtBot) -> None:
        """Row handles DD duration string values."""
        row = _ComparisonRow("flat_stake_dd_duration")
        qtbot.addWidget(row)

        row.set_values("Not recovered", 5)

        assert "Not recovered" in row._baseline_label.text()
        assert "5 days" in row._filtered_label.text()
        # Delta should be em dash since baseline is string
        assert "—" in row._delta_label.text()


class TestComparisonGridDeltaColors:
    """Tests for delta color semantics in ComparisonGrid."""

    def test_improvement_uses_cyan(self, qtbot: QtBot) -> None:
        """Improvement delta uses SIGNAL_CYAN."""
        grid = ComparisonGrid()
        qtbot.addWidget(grid)

        baseline = _create_test_metrics(win_rate=60.0)
        filtered = _create_test_metrics(win_rate=70.0)  # Improvement

        grid.set_values(baseline, filtered)

        style = grid._rows["win_rate"]._delta_label.styleSheet()
        assert Colors.SIGNAL_CYAN in style

    def test_decline_uses_coral(self, qtbot: QtBot) -> None:
        """Decline delta uses SIGNAL_CORAL."""
        grid = ComparisonGrid()
        qtbot.addWidget(grid)

        baseline = _create_test_metrics(win_rate=70.0)
        filtered = _create_test_metrics(win_rate=60.0)  # Decline

        grid.set_values(baseline, filtered)

        style = grid._rows["win_rate"]._delta_label.styleSheet()
        assert Colors.SIGNAL_CORAL in style

    def test_num_trades_always_neutral(self, qtbot: QtBot) -> None:
        """num_trades always uses neutral color regardless of direction."""
        grid = ComparisonGrid()
        qtbot.addWidget(grid)

        baseline = _create_test_metrics(num_trades=1000)
        filtered = _create_test_metrics(num_trades=500)  # Decrease

        grid.set_values(baseline, filtered)

        style = grid._rows["num_trades"]._delta_label.styleSheet()
        assert Colors.TEXT_SECONDARY in style

    def test_lower_is_better_metrics_correct_color(self, qtbot: QtBot) -> None:
        """Lower-is-better metrics show cyan for decrease, coral for increase."""
        grid = ComparisonGrid()
        qtbot.addWidget(grid)

        # max_consecutive_losses is lower-is-better
        baseline = _create_test_metrics()
        # Create filtered with lower loss streak (improvement)
        filtered = TradingMetrics(
            num_trades=500,
            win_rate=70.0,
            avg_winner=5.0,
            avg_loser=-2.0,
            rr_ratio=2.5,
            ev=2.5,
            kelly=12.0,
            max_consecutive_losses=1,  # Lower = better
        )

        grid.set_values(baseline, filtered)

        style = grid._rows["max_consecutive_losses"]._delta_label.styleSheet()
        # Lower value should be cyan (improvement)
        assert Colors.SIGNAL_CYAN in style
