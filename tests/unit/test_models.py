"""Unit tests for data models."""

from src.core.models import ColumnMapping, DetectionResult, MetricsUserInputs, TradingMetrics


class TestColumnMapping:
    """Tests for ColumnMapping dataclass."""

    def test_validate_success(self) -> None:
        """Validate returns empty list for valid columns."""
        mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
        )
        errors = mapping.validate(["ticker", "date", "time", "gain_pct", "mae_pct"])
        assert errors == []

    def test_validate_missing_required(self) -> None:
        """Validate returns errors for missing required columns."""
        mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
        )
        errors = mapping.validate(["ticker", "date"])  # missing time, gain_pct, mae_pct

        assert len(errors) == 3
        assert "time" in errors[0]
        assert "gain_pct" in errors[1]
        assert "mae_pct" in errors[2]

    def test_validate_missing_win_loss(self) -> None:
        """Validate returns error for missing win_loss column when specified."""
        mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            win_loss="result",
        )
        errors = mapping.validate(["ticker", "date", "time", "gain_pct", "mae_pct"])

        assert len(errors) == 1
        assert "Win/Loss" in errors[0]
        assert "result" in errors[0]

    def test_validate_win_loss_none(self) -> None:
        """Validate passes when win_loss is None."""
        mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            win_loss=None,
        )
        errors = mapping.validate(["ticker", "date", "time", "gain_pct", "mae_pct"])
        assert errors == []

    def test_defaults(self) -> None:
        """Dataclass defaults are correct."""
        mapping = ColumnMapping(
            ticker="t",
            date="d",
            time="ti",
            gain_pct="g",
            mae_pct="m",
        )
        assert mapping.win_loss is None
        assert mapping.win_loss_derived is False
        assert mapping.breakeven_is_win is False

    def test_all_fields(self) -> None:
        """All fields can be set."""
        mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain",
            mae_pct="mae",
            win_loss="result",
            win_loss_derived=True,
            breakeven_is_win=True,
        )
        assert mapping.ticker == "ticker"
        assert mapping.date == "date"
        assert mapping.time == "time"
        assert mapping.gain_pct == "gain"
        assert mapping.mae_pct == "mae"
        assert mapping.win_loss == "result"
        assert mapping.win_loss_derived is True
        assert mapping.breakeven_is_win is True


class TestDetectionResult:
    """Tests for DetectionResult dataclass."""

    def test_defaults(self) -> None:
        """DetectionResult has correct defaults."""
        result = DetectionResult(mapping=None)
        assert result.mapping is None
        assert result.statuses == {}
        assert result.all_required_detected is False

    def test_with_mapping(self) -> None:
        """DetectionResult with mapping."""
        mapping = ColumnMapping(ticker="t", date="d", time="ti", gain_pct="g", mae_pct="m")
        result = DetectionResult(
            mapping=mapping,
            statuses={"ticker": "detected", "date": "detected"},
            all_required_detected=True,
        )
        assert result.mapping is not None
        assert result.mapping.ticker == "t"
        assert result.statuses["ticker"] == "detected"
        assert result.all_required_detected is True

    def test_partial_detection(self) -> None:
        """DetectionResult for partial detection."""
        result = DetectionResult(
            mapping=None,
            statuses={
                "ticker": "detected",
                "date": "detected",
                "time": "missing",
                "gain_pct": "guessed",
                "mae_pct": "missing",
            },
            all_required_detected=False,
        )
        assert result.mapping is None
        assert result.statuses["time"] == "missing"
        assert result.statuses["gain_pct"] == "guessed"
        assert result.statuses["mae_pct"] == "missing"
        assert result.all_required_detected is False


class TestTradingMetrics:
    """Tests for TradingMetrics dataclass."""

    def test_empty_returns_zero_values(self) -> None:
        """TradingMetrics.empty() returns all None/zero values."""
        metrics = TradingMetrics.empty()

        assert metrics.num_trades == 0
        assert metrics.win_rate is None
        assert metrics.avg_winner is None
        assert metrics.avg_loser is None
        assert metrics.rr_ratio is None
        assert metrics.ev is None
        assert metrics.kelly is None
        assert metrics.winner_count == 0
        assert metrics.loser_count == 0
        assert metrics.winner_std is None
        assert metrics.loser_std is None
        assert metrics.winner_gains == []
        assert metrics.loser_gains == []

    def test_dataclass_fields_typed(self) -> None:
        """All dataclass fields have correct types."""
        metrics = TradingMetrics(
            num_trades=100,
            win_rate=60.0,
            avg_winner=2.5,
            avg_loser=-1.25,
            rr_ratio=2.0,
            ev=0.875,
            kelly=40.0,
            winner_count=60,
            loser_count=40,
            winner_std=1.2,
            loser_std=0.8,
            winner_gains=[2.0, 2.5, 3.0],
            loser_gains=[-1.0, -1.5],
        )

        assert isinstance(metrics.num_trades, int)
        assert isinstance(metrics.win_rate, float)
        assert isinstance(metrics.avg_winner, float)
        assert isinstance(metrics.avg_loser, float)
        assert isinstance(metrics.rr_ratio, float)
        assert isinstance(metrics.ev, float)
        assert isinstance(metrics.kelly, float)
        assert isinstance(metrics.winner_count, int)
        assert isinstance(metrics.loser_count, int)
        assert isinstance(metrics.winner_std, float)
        assert isinstance(metrics.loser_std, float)
        assert isinstance(metrics.winner_gains, list)
        assert isinstance(metrics.loser_gains, list)

    def test_distribution_data_fields(self) -> None:
        """Distribution data fields (winner_gains, loser_gains lists)."""
        metrics = TradingMetrics(
            num_trades=5,
            win_rate=60.0,
            avg_winner=2.0,
            avg_loser=-1.0,
            rr_ratio=2.0,
            ev=0.8,
            kelly=40.0,
            winner_gains=[1.0, 2.0, 3.0],
            loser_gains=[-0.5, -1.5],
        )

        assert len(metrics.winner_gains) == 3
        assert len(metrics.loser_gains) == 2
        assert metrics.winner_gains[0] == 1.0
        assert metrics.loser_gains[1] == -1.5

    def test_defaults(self) -> None:
        """Optional fields have correct defaults."""
        metrics = TradingMetrics(
            num_trades=10,
            win_rate=50.0,
            avg_winner=1.0,
            avg_loser=-1.0,
            rr_ratio=1.0,
            ev=0.0,
            kelly=0.0,
        )

        assert metrics.winner_count is None
        assert metrics.loser_count is None
        assert metrics.winner_std is None
        assert metrics.loser_std is None
        assert metrics.winner_gains == []
        assert metrics.loser_gains == []

    def test_none_values_allowed(self) -> None:
        """None values are allowed for optional metrics."""
        metrics = TradingMetrics(
            num_trades=5,
            win_rate=None,
            avg_winner=None,
            avg_loser=None,
            rr_ratio=None,
            ev=None,
            kelly=None,
        )

        assert metrics.num_trades == 5
        assert metrics.win_rate is None
        assert metrics.avg_winner is None

    def test_extended_metrics_fields(self) -> None:
        """Extended metrics fields (Story 3.2) exist and have defaults."""
        metrics = TradingMetrics(
            num_trades=10,
            win_rate=50.0,
            avg_winner=5.0,
            avg_loser=-2.5,
            rr_ratio=2.0,
            ev=1.25,
            kelly=25.0,
        )

        # New fields default to None
        assert metrics.edge is None
        assert metrics.fractional_kelly is None
        assert metrics.eg_full_kelly is None
        assert metrics.eg_frac_kelly is None
        assert metrics.eg_flat_stake is None
        assert metrics.median_winner is None
        assert metrics.median_loser is None
        assert metrics.winner_min is None
        assert metrics.winner_max is None
        assert metrics.loser_min is None
        assert metrics.loser_max is None

    def test_extended_metrics_with_values(self) -> None:
        """Extended metrics fields can be set with values."""
        metrics = TradingMetrics(
            num_trades=10,
            win_rate=50.0,
            avg_winner=10.0,
            avg_loser=-4.0,
            rr_ratio=2.5,
            ev=3.0,
            kelly=30.0,
            edge=30.0,
            fractional_kelly=7.5,
            eg_full_kelly=0.5,
            eg_frac_kelly=0.15,
            eg_flat_stake=0.10,
            median_winner=10.0,
            median_loser=-4.0,
            winner_min=5.0,
            winner_max=15.0,
            loser_min=-6.0,
            loser_max=-2.0,
        )

        assert metrics.edge == 30.0
        assert metrics.fractional_kelly == 7.5
        assert metrics.eg_full_kelly == 0.5
        assert metrics.eg_frac_kelly == 0.15
        assert metrics.eg_flat_stake == 0.10
        assert metrics.median_winner == 10.0
        assert metrics.median_loser == -4.0
        assert metrics.winner_min == 5.0
        assert metrics.winner_max == 15.0
        assert metrics.loser_min == -6.0
        assert metrics.loser_max == -2.0

    def test_empty_includes_extended_fields(self) -> None:
        """TradingMetrics.empty() includes extended fields with None values."""
        metrics = TradingMetrics.empty()

        assert metrics.edge is None
        assert metrics.fractional_kelly is None
        assert metrics.eg_full_kelly is None
        assert metrics.eg_frac_kelly is None
        assert metrics.eg_flat_stake is None
        assert metrics.median_winner is None
        assert metrics.median_loser is None
        assert metrics.winner_min is None
        assert metrics.winner_max is None
        assert metrics.loser_min is None
        assert metrics.loser_max is None

    def test_streak_metrics_fields_default_to_none(self) -> None:
        """Streak metrics fields (Story 3.3) default to None."""
        metrics = TradingMetrics(
            num_trades=10,
            win_rate=50.0,
            avg_winner=5.0,
            avg_loser=-2.5,
            rr_ratio=2.0,
            ev=1.25,
            kelly=25.0,
        )

        assert metrics.max_consecutive_wins is None
        assert metrics.max_consecutive_losses is None
        assert metrics.max_loss_pct is None

    def test_streak_metrics_with_values(self) -> None:
        """Streak metrics fields can be set with values."""
        metrics = TradingMetrics(
            num_trades=10,
            win_rate=50.0,
            avg_winner=5.0,
            avg_loser=-2.5,
            rr_ratio=2.0,
            ev=1.25,
            kelly=25.0,
            max_consecutive_wins=3,
            max_consecutive_losses=2,
            max_loss_pct=-6.0,
        )

        assert metrics.max_consecutive_wins == 3
        assert metrics.max_consecutive_losses == 2
        assert metrics.max_loss_pct == -6.0

    def test_empty_includes_streak_fields(self) -> None:
        """TradingMetrics.empty() includes streak fields with None values."""
        metrics = TradingMetrics.empty()

        assert metrics.max_consecutive_wins is None
        assert metrics.max_consecutive_losses is None
        assert metrics.max_loss_pct is None


class TestAdjustmentParams:
    """Tests for AdjustmentParams dataclass."""

    def test_defaults(self) -> None:
        """AdjustmentParams has correct default values."""
        from src.core.models import AdjustmentParams

        params = AdjustmentParams()
        assert params.stop_loss == 8.0
        assert params.efficiency == 5.0

    def test_custom_values(self) -> None:
        """AdjustmentParams accepts custom values."""
        from src.core.models import AdjustmentParams

        params = AdjustmentParams(stop_loss=10.0, efficiency=3.0)
        assert params.stop_loss == 10.0
        assert params.efficiency == 3.0

    def test_calculate_adjusted_gain_no_stop_hit(self) -> None:
        """Calculate adjusted gain when stop not hit."""
        from src.core.models import AdjustmentParams

        params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
        # mae_pct (3) <= stop_loss (8), so stop not hit
        # stop_adjusted = 20, efficiency_adjusted = 20 - 5 = 15
        result = params.calculate_adjusted_gain(gain_pct=20.0, mae_pct=3.0)
        assert result == 15.0

    def test_calculate_adjusted_gain_stop_hit(self) -> None:
        """Calculate adjusted gain when stop is hit."""
        from src.core.models import AdjustmentParams

        params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
        # mae_pct (10) > stop_loss (8), so stop hit
        # stop_adjusted = -8, efficiency_adjusted = -8 - 5 = -13
        result = params.calculate_adjusted_gain(gain_pct=10.0, mae_pct=10.0)
        assert result == -13.0

    def test_calculate_adjusted_gain_stop_at_boundary(self) -> None:
        """Calculate adjusted gain when mae equals stop loss."""
        from src.core.models import AdjustmentParams

        params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
        # mae_pct (8) == stop_loss (8), NOT greater, so stop NOT hit
        # stop_adjusted = 10, efficiency_adjusted = 10 - 5 = 5
        result = params.calculate_adjusted_gain(gain_pct=10.0, mae_pct=8.0)
        assert result == 5.0

    def test_calculate_adjusted_gain_negative_gain(self) -> None:
        """Calculate adjusted gain for losing trade without stop hit."""
        from src.core.models import AdjustmentParams

        params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
        # mae_pct (5) <= stop_loss (8), stop not hit
        # stop_adjusted = -2, efficiency_adjusted = -2 - 5 = -7
        result = params.calculate_adjusted_gain(gain_pct=-2.0, mae_pct=5.0)
        assert result == -7.0

    def test_calculate_adjusted_gains_vectorized(self) -> None:
        """Calculate adjusted gains for DataFrame (vectorized).

        Note: gain_pct is in decimal format (0.20 = 20%), while mae_pct and
        stop_loss/efficiency are in percentage format (8.0 = 8%).
        """
        import pandas as pd

        from src.core.models import AdjustmentParams

        params = AdjustmentParams(stop_loss=8.0, efficiency=5.0)
        df = pd.DataFrame({
            # Gains in decimal format: 0.20 = 20%, 0.10 = 10%, etc.
            "gain_pct": [0.20, 0.10, -0.02, 0.05],
            "mae_pct": [3.0, 10.0, 5.0, 12.0],
        })

        result = params.calculate_adjusted_gains(df, "gain_pct", "mae_pct")

        # Expected (all results in decimal format):
        # Row 0: mae(3) <= 8, gain 20% - 5% eff = 15% -> 0.15
        # Row 1: mae(10) > 8, stop -8% - 5% eff = -13% -> -0.13
        # Row 2: mae(5) <= 8, gain -2% - 5% eff = -7% -> -0.07
        # Row 3: mae(12) > 8, stop -8% - 5% eff = -13% -> -0.13
        assert list(result) == [0.15, -0.13, -0.07, -0.13]

    def test_calculate_adjusted_gains_empty_dataframe(self) -> None:
        """Calculate adjusted gains for empty DataFrame."""
        import pandas as pd

        from src.core.models import AdjustmentParams

        params = AdjustmentParams()
        df = pd.DataFrame({"gain_pct": [], "mae_pct": []})

        result = params.calculate_adjusted_gains(df, "gain_pct", "mae_pct")
        assert len(result) == 0


class TestMetricsUserInputs:
    """Tests for MetricsUserInputs dataclass."""

    def test_default_values(self) -> None:
        """MetricsUserInputs has correct default values."""
        inputs = MetricsUserInputs()
        assert inputs.flat_stake == 10000.0
        assert inputs.starting_capital == 100000.0
        assert inputs.fractional_kelly == 25.0

    def test_custom_values(self) -> None:
        """MetricsUserInputs accepts custom values."""
        inputs = MetricsUserInputs(
            flat_stake=500.0,
            starting_capital=50000.0,
            fractional_kelly=50.0,
        )
        assert inputs.flat_stake == 500.0
        assert inputs.starting_capital == 50000.0
        assert inputs.fractional_kelly == 50.0

    def test_validate_valid_inputs(self) -> None:
        """validate() returns empty list for valid inputs."""
        inputs = MetricsUserInputs()
        errors = inputs.validate()
        assert errors == []

    def test_validate_non_positive_flat_stake(self) -> None:
        """validate() rejects non-positive flat_stake."""
        inputs = MetricsUserInputs(flat_stake=0.0)
        errors = inputs.validate()
        assert len(errors) == 1
        assert "Flat stake" in errors[0]

        inputs = MetricsUserInputs(flat_stake=-100.0)
        errors = inputs.validate()
        assert len(errors) == 1
        assert "Flat stake" in errors[0]

    def test_validate_non_positive_starting_capital(self) -> None:
        """validate() rejects non-positive starting_capital."""
        inputs = MetricsUserInputs(starting_capital=0.0)
        errors = inputs.validate()
        assert len(errors) == 1
        assert "Starting capital" in errors[0]

        inputs = MetricsUserInputs(starting_capital=-1000.0)
        errors = inputs.validate()
        assert len(errors) == 1
        assert "Starting capital" in errors[0]

    def test_validate_fractional_kelly_out_of_range(self) -> None:
        """validate() rejects fractional_kelly outside 1-100 range."""
        inputs = MetricsUserInputs(fractional_kelly=0.5)
        errors = inputs.validate()
        assert len(errors) == 1
        assert "Fractional Kelly" in errors[0]

        inputs = MetricsUserInputs(fractional_kelly=101.0)
        errors = inputs.validate()
        assert len(errors) == 1
        assert "Fractional Kelly" in errors[0]

    def test_validate_multiple_errors(self) -> None:
        """validate() returns all errors."""
        inputs = MetricsUserInputs(
            flat_stake=-100.0,
            starting_capital=0.0,
            fractional_kelly=150.0,
        )
        errors = inputs.validate()
        assert len(errors) == 3

    def test_to_dict(self) -> None:
        """to_dict() returns correct dictionary."""
        inputs = MetricsUserInputs(
            flat_stake=2000.0,
            starting_capital=25000.0,
            fractional_kelly=30.0,
        )
        result = inputs.to_dict()

        assert result == {
            "flat_stake": 2000.0,
            "starting_capital": 25000.0,
            "fractional_kelly": 30.0,
        }

    def test_from_dict(self) -> None:
        """from_dict() creates object from dictionary."""
        data = {
            "flat_stake": 3000.0,
            "starting_capital": 100000.0,
            "fractional_kelly": 50.0,
        }
        inputs = MetricsUserInputs.from_dict(data)

        assert inputs.flat_stake == 3000.0
        assert inputs.starting_capital == 100000.0
        assert inputs.fractional_kelly == 50.0

    def test_from_dict_with_defaults(self) -> None:
        """from_dict() uses defaults for missing keys."""
        data = {"flat_stake": 5000.0}
        inputs = MetricsUserInputs.from_dict(data)

        assert inputs.flat_stake == 5000.0
        assert inputs.starting_capital == 100000.0  # default
        assert inputs.fractional_kelly == 25.0  # default

    def test_from_dict_empty(self) -> None:
        """from_dict() with empty dict uses all defaults."""
        inputs = MetricsUserInputs.from_dict({})

        assert inputs.flat_stake == 10000.0
        assert inputs.starting_capital == 100000.0
        assert inputs.fractional_kelly == 25.0

    def test_round_trip(self) -> None:
        """Round-trip: from_dict(obj.to_dict()) equals original."""
        original = MetricsUserInputs(
            flat_stake=7500.0,
            starting_capital=150000.0,
            fractional_kelly=75.0,
        )
        recreated = MetricsUserInputs.from_dict(original.to_dict())

        assert recreated.flat_stake == original.flat_stake
        assert recreated.starting_capital == original.starting_capital
        assert recreated.fractional_kelly == original.fractional_kelly


def test_trading_metrics_has_eg_fields() -> None:
    """TradingMetrics has three expected growth fields."""
    metrics = TradingMetrics(
        num_trades=100,
        win_rate=60.0,
        avg_winner=2.0,
        avg_loser=-1.0,
        rr_ratio=2.0,
        ev=0.8,
        kelly=40.0,
        eg_full_kelly=0.15,
        eg_frac_kelly=0.04,
        eg_flat_stake=0.10,
    )
    assert metrics.eg_full_kelly == 0.15
    assert metrics.eg_frac_kelly == 0.04
    assert metrics.eg_flat_stake == 0.10
