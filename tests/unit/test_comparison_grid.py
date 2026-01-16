"""Unit tests for ComparisonGrid delta calculation and color logic."""

from src.ui.components.comparison_grid import (
    METRIC_CONFIG,
    _calculate_delta,
    _format_value,
    _get_delta_color,
)
from src.ui.constants import Colors


class TestFormatValue:
    """Tests for _format_value helper function."""

    def test_format_none_returns_dash(self) -> None:
        """None values should return em dash."""
        assert _format_value(None, "win_rate") == "—"

    def test_format_count_metric(self) -> None:
        """Count metrics should format as integer with comma separator."""
        assert _format_value(1234, "num_trades") == "1,234"

    def test_format_percentage_metric(self) -> None:
        """Percentage metrics should format with % suffix."""
        assert _format_value(65.5, "win_rate") == "65.5%"

    def test_format_dollar_metric(self) -> None:
        """Dollar metrics should format with $ prefix and comma separator."""
        assert _format_value(1234.56, "flat_stake_pnl") == "$1,234.56"

    def test_format_ratio_metric(self) -> None:
        """Ratio metrics should format as decimal."""
        assert _format_value(2.5, "rr_ratio") == "2.50"

    def test_format_dd_duration_integer(self) -> None:
        """DD duration with integer should format as 'X days'."""
        assert _format_value(5, "flat_stake_dd_duration") == "5 days"

    def test_format_dd_duration_string(self) -> None:
        """DD duration with string should pass through."""
        assert _format_value("Not recovered", "flat_stake_dd_duration") == "Not recovered"
        assert _format_value("Blown", "kelly_dd_duration") == "Blown"


class TestCalculateDelta:
    """Tests for _calculate_delta helper function."""

    def test_calculate_delta_pp_format_positive(self) -> None:
        """Positive percentage point delta should format with + prefix."""
        delta, text = _calculate_delta(50.0, 55.0, "win_rate")
        assert delta == 5.0
        assert text == "+5.00pp"

    def test_calculate_delta_pp_format_negative(self) -> None:
        """Negative percentage point delta should format with - prefix."""
        delta, text = _calculate_delta(55.0, 50.0, "win_rate")
        assert delta == -5.0
        assert text == "-5.00pp"

    def test_calculate_delta_pp_format_zero(self) -> None:
        """Zero percentage point delta should show 0pp."""
        delta, text = _calculate_delta(50.0, 50.0, "win_rate")
        assert delta == 0.0
        assert text == "0pp"

    def test_calculate_delta_dollar_format_positive(self) -> None:
        """Positive dollar delta should format with +$ prefix."""
        delta, text = _calculate_delta(1000.0, 1500.0, "flat_stake_pnl")
        assert delta == 500.0
        assert text == "+$500.00"

    def test_calculate_delta_dollar_format_negative(self) -> None:
        """Negative dollar delta should format with -$ prefix."""
        delta, text = _calculate_delta(1500.0, 1000.0, "flat_stake_pnl")
        assert delta == -500.0
        assert text == "-$500.00"

    def test_calculate_delta_dollar_format_zero(self) -> None:
        """Zero dollar delta should show $0."""
        delta, text = _calculate_delta(1000.0, 1000.0, "flat_stake_pnl")
        assert delta == 0.0
        assert text == "$0"

    def test_calculate_delta_days_format_positive(self) -> None:
        """Positive days delta should format as '+X days'."""
        delta, text = _calculate_delta(5, 8, "flat_stake_dd_duration")
        assert delta == 3
        assert text == "+3 days"

    def test_calculate_delta_days_format_negative(self) -> None:
        """Negative days delta should format as '-X days'."""
        delta, text = _calculate_delta(8, 5, "flat_stake_dd_duration")
        assert delta == -3
        assert text == "-3 days"

    def test_calculate_delta_days_format_zero(self) -> None:
        """Zero days delta should show 0 days."""
        delta, text = _calculate_delta(5, 5, "flat_stake_dd_duration")
        assert delta == 0
        assert text == "0 days"

    def test_calculate_delta_count_format_positive(self) -> None:
        """Positive count delta should format as integer with + prefix."""
        delta, text = _calculate_delta(100, 150, "num_trades")
        assert delta == 50
        assert text == "+50"

    def test_calculate_delta_count_format_negative(self) -> None:
        """Negative count delta should format as integer with - prefix."""
        delta, text = _calculate_delta(150, 100, "num_trades")
        assert delta == -50
        assert text == "-50"

    def test_calculate_delta_ratio_format(self) -> None:
        """Ratio delta should format as decimal."""
        delta, text = _calculate_delta(2.0, 2.5, "rr_ratio")
        assert delta == 0.5
        assert text == "+0.50"

    def test_calculate_delta_none_baseline(self) -> None:
        """None baseline should return None delta and dash."""
        delta, text = _calculate_delta(None, 50.0, "win_rate")
        assert delta is None
        assert text == "—"

    def test_calculate_delta_none_filtered(self) -> None:
        """None filtered should return None delta and dash."""
        delta, text = _calculate_delta(50.0, None, "win_rate")
        assert delta is None
        assert text == "—"

    def test_calculate_delta_duration_string_baseline(self) -> None:
        """String baseline for duration should return None delta."""
        delta, text = _calculate_delta("Not recovered", 5, "flat_stake_dd_duration")
        assert delta is None
        assert text == "—"

    def test_calculate_delta_duration_string_filtered(self) -> None:
        """String filtered for duration should return None delta."""
        delta, text = _calculate_delta(5, "Blown", "kelly_dd_duration")
        assert delta is None
        assert text == "—"


class TestGetDeltaColor:
    """Tests for _get_delta_color helper function."""

    def test_improvement_direction_higher_positive(self) -> None:
        """Higher-is-better metric with positive delta should be cyan."""
        # win_rate has improvement="higher"
        assert _get_delta_color(5.0, "win_rate") == Colors.SIGNAL_CYAN

    def test_improvement_direction_higher_negative(self) -> None:
        """Higher-is-better metric with negative delta should be coral."""
        assert _get_delta_color(-5.0, "win_rate") == Colors.SIGNAL_CORAL

    def test_improvement_direction_lower_positive(self) -> None:
        """Lower-is-better metric with positive delta should be coral (decline)."""
        # max_consecutive_losses has improvement="lower"
        assert _get_delta_color(2.0, "max_consecutive_losses") == Colors.SIGNAL_CORAL

    def test_improvement_direction_lower_negative(self) -> None:
        """Lower-is-better metric with negative delta should be cyan (improvement)."""
        assert _get_delta_color(-2.0, "max_consecutive_losses") == Colors.SIGNAL_CYAN

    def test_num_trades_always_neutral_positive(self) -> None:
        """num_trades with positive delta should always be neutral."""
        assert _get_delta_color(50.0, "num_trades") == Colors.TEXT_SECONDARY

    def test_num_trades_always_neutral_negative(self) -> None:
        """num_trades with negative delta should always be neutral."""
        assert _get_delta_color(-50.0, "num_trades") == Colors.TEXT_SECONDARY

    def test_zero_delta_neutral(self) -> None:
        """Zero delta should always be neutral."""
        assert _get_delta_color(0.0, "win_rate") == Colors.TEXT_SECONDARY

    def test_none_delta_neutral(self) -> None:
        """None delta should always be neutral."""
        assert _get_delta_color(None, "win_rate") == Colors.TEXT_SECONDARY

    def test_ev_higher_is_better(self) -> None:
        """EV metric should use higher-is-better logic."""
        assert _get_delta_color(1.5, "ev") == Colors.SIGNAL_CYAN
        assert _get_delta_color(-1.5, "ev") == Colors.SIGNAL_CORAL

    def test_kelly_higher_is_better(self) -> None:
        """Kelly metric should use higher-is-better logic."""
        assert _get_delta_color(2.0, "kelly") == Colors.SIGNAL_CYAN
        assert _get_delta_color(-2.0, "kelly") == Colors.SIGNAL_CORAL

    def test_max_dd_lower_is_better(self) -> None:
        """Max DD metrics should use lower-is-better logic."""
        # Lower drawdown is better
        assert _get_delta_color(-100.0, "flat_stake_max_dd") == Colors.SIGNAL_CYAN
        assert _get_delta_color(100.0, "flat_stake_max_dd") == Colors.SIGNAL_CORAL

    def test_dd_duration_lower_is_better(self) -> None:
        """DD duration should use lower-is-better logic."""
        # Fewer days to recover is better
        assert _get_delta_color(-3.0, "flat_stake_dd_duration") == Colors.SIGNAL_CYAN
        assert _get_delta_color(3.0, "flat_stake_dd_duration") == Colors.SIGNAL_CORAL

    def test_avg_loser_higher_is_better(self) -> None:
        """Avg loser should use higher-is-better (less negative is better)."""
        # Less negative avg loser is improvement
        assert _get_delta_color(2.0, "avg_loser") == Colors.SIGNAL_CYAN
        assert _get_delta_color(-2.0, "avg_loser") == Colors.SIGNAL_CORAL


class TestMetricConfigCompleteness:
    """Tests to verify METRIC_CONFIG covers all expected metrics."""

    def test_config_has_26_metrics(self) -> None:
        """METRIC_CONFIG should have exactly 26 metrics (including stop_adjusted_kelly)."""
        assert len(METRIC_CONFIG) == 26

    def test_all_metrics_have_valid_improvement(self) -> None:
        """All metrics should have valid improvement direction."""
        valid_improvements = {"higher", "lower", "neutral"}
        for field_name, config in METRIC_CONFIG.items():
            _, _, _, improvement = config
            assert improvement in valid_improvements, f"{field_name} has invalid improvement"

    def test_all_metrics_have_valid_delta_type(self) -> None:
        """All metrics should have valid delta type."""
        valid_types = {"pp", "$", "ratio", "days", "count"}
        for field_name, config in METRIC_CONFIG.items():
            _, _, delta_type, _ = config
            assert delta_type in valid_types, f"{field_name} has invalid delta_type"
