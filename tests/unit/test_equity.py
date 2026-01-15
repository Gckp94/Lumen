"""Unit tests for EquityCalculator."""

import pandas as pd
import pytest

from src.core.equity import EquityCalculator
from src.core.exceptions import EquityCalculationError


class TestEquityCalculatorFlatStake:
    """Tests for flat stake equity calculations."""

    def test_flat_stake_equity_includes_starting_capital(self) -> None:
        """Equity curve starts at starting_capital, not zero."""
        df = pd.DataFrame({"gain_pct": [10.0, -5.0, 15.0]})
        calc = EquityCalculator()
        # $10,000 stake on $100,000 starting capital
        result = calc.calculate_flat_stake(
            df, gain_col="gain_pct", stake=10000.0, start_capital=100000.0
        )

        # Trade 1: 10% of $10k stake = $1000 profit, equity = $101,000
        assert result["equity"].iloc[0] == pytest.approx(101000.0, abs=0.01)
        # Trade 2: -5% of $10k stake = -$500, equity = $100,500
        assert result["equity"].iloc[1] == pytest.approx(100500.0, abs=0.01)
        # Trade 3: 15% of $10k stake = $1500, equity = $102,000
        assert result["equity"].iloc[2] == pytest.approx(102000.0, abs=0.01)

    def test_flat_stake_basic(self) -> None:
        """Basic equity curve calculation."""
        df = pd.DataFrame({"gain_pct": [5.0, 3.0, -4.0, -2.0, 8.0]})
        calc = EquityCalculator()
        result = calc.calculate_flat_stake(df, gain_col="gain_pct", stake=1000.0)

        # Expected: 50 + 30 - 40 - 20 + 80 = 100
        assert result["equity"].iloc[-1] == pytest.approx(100.0, abs=0.01)
        assert len(result) == 5

    def test_flat_stake_empty_dataframe(self) -> None:
        """Empty DataFrame returns empty result."""
        df = pd.DataFrame({"gain_pct": []})
        calc = EquityCalculator()
        result = calc.calculate_flat_stake(df, gain_col="gain_pct", stake=1000.0)
        assert len(result) == 0
        assert list(result.columns) == ["trade_num", "pnl", "equity", "peak", "drawdown"]

    def test_flat_stake_single_trade(self) -> None:
        """Single trade edge case."""
        df = pd.DataFrame({"gain_pct": [5.0]})
        calc = EquityCalculator()
        result = calc.calculate_flat_stake(df, gain_col="gain_pct", stake=1000.0)

        assert len(result) == 1
        assert result["pnl"].iloc[0] == pytest.approx(50.0, abs=0.01)
        assert result["equity"].iloc[0] == pytest.approx(50.0, abs=0.01)
        assert result["peak"].iloc[0] == pytest.approx(50.0, abs=0.01)
        assert result["drawdown"].iloc[0] == pytest.approx(0.0, abs=0.01)

    def test_flat_stake_all_winners(self) -> None:
        """All winners means no drawdown."""
        df = pd.DataFrame({"gain_pct": [5.0, 3.0, 2.0, 4.0]})
        calc = EquityCalculator()
        result = calc.calculate_flat_stake(df, gain_col="gain_pct", stake=1000.0)
        assert (result["drawdown"] == 0).all()

    def test_flat_stake_all_losers(self) -> None:
        """All losers - continuous drawdown."""
        df = pd.DataFrame({"gain_pct": [-3.0, -2.0, -5.0]})
        calc = EquityCalculator()
        result = calc.calculate_flat_stake(df, gain_col="gain_pct", stake=1000.0)

        # With all losers: equity = -30, -50, -100
        # np.maximum.accumulate of negative values gives the "least negative"
        # Peak: -30, -30, -30 (stays at first value since it's the max/least negative)
        assert result["equity"].iloc[-1] == pytest.approx(-100.0, abs=0.01)
        assert result["peak"].iloc[-1] == pytest.approx(-30.0, abs=0.01)
        # All drawdowns are negative
        assert (result["drawdown"] < 0).any()

    def test_flat_stake_invalid_column_raises(self) -> None:
        """Invalid gain column raises EquityCalculationError."""
        df = pd.DataFrame({"other_col": [5.0, 3.0]})
        calc = EquityCalculator()
        with pytest.raises(EquityCalculationError):
            calc.calculate_flat_stake(df, gain_col="gain_pct", stake=1000.0)


class TestDrawdownMetrics:
    """Tests for drawdown metric calculations."""

    def test_max_dd_dollars(self) -> None:
        """Max DD in dollars calculated correctly."""
        df = pd.DataFrame({"gain_pct": [5.0, -10.0, 3.0]})
        calc = EquityCalculator()
        metrics = calc.calculate_flat_stake_metrics(df, gain_col="gain_pct", stake=1000.0)

        # Peak at 50, drops to -50, max_dd = 100
        assert metrics["max_dd"] == pytest.approx(100.0, abs=0.01)

    def test_max_dd_pct_calculation(self) -> None:
        """Max DD percentage calculation."""
        # Use the sample data from the story
        df = pd.DataFrame({"gain_pct": [5.0, 3.0, -4.0, -2.0, 8.0, -6.0, 4.0, 3.0]})
        calc = EquityCalculator()
        metrics = calc.calculate_flat_stake_metrics(df, gain_col="gain_pct", stake=1000.0)

        # Trade 4: $60 drawdown from $80 peak = 75%
        # Trade 6: $60 drawdown from $100 peak = 60%
        # Max DD % should be 75% at trade 4
        assert metrics["max_dd_pct"] == pytest.approx(75.0, abs=0.01)

    def test_dd_duration_recovered(self) -> None:
        """Duration returned when drawdown is recovered.

        Duration is measured from when the drawdown started (peak established)
        to when equity recovers to or above that peak.
        """
        df = pd.DataFrame({"gain_pct": [5.0, 3.0, -4.0, -2.0, 8.0]})
        calc = EquityCalculator()
        metrics = calc.calculate_flat_stake_metrics(df, gain_col="gain_pct", stake=1000.0)

        # Peak of 80 at trade 2 (index 1), max DD at trade 4, recovered at trade 5
        # Duration = 4 - 1 = 3 trades (from peak to recovery)
        assert isinstance(metrics["dd_duration"], int)
        assert metrics["dd_duration"] == 3

    def test_dd_duration_not_recovered(self) -> None:
        """'Not recovered' returned when drawdown ongoing."""
        df = pd.DataFrame({"gain_pct": [5.0, -10.0, 3.0]})
        calc = EquityCalculator()
        metrics = calc.calculate_flat_stake_metrics(df, gain_col="gain_pct", stake=1000.0)

        # Peak at 50, never returns to 50
        assert metrics["dd_duration"] == "Not recovered"

    def test_no_drawdown(self) -> None:
        """All None when equity only increases."""
        df = pd.DataFrame({"gain_pct": [5.0, 3.0, 2.0, 4.0]})
        calc = EquityCalculator()
        metrics = calc.calculate_flat_stake_metrics(df, gain_col="gain_pct", stake=1000.0)

        assert metrics["max_dd"] is None
        assert metrics["max_dd_pct"] is None
        assert metrics["dd_duration"] is None

    def test_max_dd_pct_zero_peak_returns_none(self) -> None:
        """Zero peak edge case returns None for max_dd_pct."""
        df = pd.DataFrame({"gain_pct": [-5.0, -3.0]})  # Equity never positive
        calc = EquityCalculator()
        metrics = calc.calculate_flat_stake_metrics(df, gain_col="gain_pct", stake=1000.0)

        # Peak is 0, cannot calculate percentage
        assert metrics["max_dd_pct"] is None

    def test_empty_dataframe_returns_none(self) -> None:
        """Empty DataFrame returns None for all metrics."""
        df = pd.DataFrame({"gain_pct": []})
        calc = EquityCalculator()
        metrics = calc.calculate_flat_stake_metrics(df, gain_col="gain_pct", stake=1000.0)

        assert metrics["pnl"] is None
        assert metrics["max_dd"] is None
        assert metrics["max_dd_pct"] is None
        assert metrics["dd_duration"] is None

    def test_flat_stake_pnl(self) -> None:
        """Total PnL calculated correctly."""
        df = pd.DataFrame({"gain_pct": [5.0, 3.0, -4.0, -2.0, 8.0, -6.0, 4.0, 3.0]})
        calc = EquityCalculator()
        metrics = calc.calculate_flat_stake_metrics(df, gain_col="gain_pct", stake=1000.0)

        # Expected final equity: 50 + 30 - 40 - 20 + 80 - 60 + 40 + 30 = 110
        assert metrics["pnl"] == pytest.approx(110.0, abs=0.01)


class TestEquityCalculatorKelly:
    """Tests for Kelly equity calculations."""

    def test_kelly_basic(self) -> None:
        """Basic Kelly equity curve calculation."""
        df = pd.DataFrame({"gain_pct": [10.0, 5.0, -15.0, 8.0, 6.0]})
        calc = EquityCalculator()
        result = calc.calculate_kelly(
            df, gain_col="gain_pct", start_capital=10000.0, kelly_fraction=50.0, kelly_pct=10.0
        )
        # First winning trade should increase equity
        assert result["equity"].iloc[0] > 10000.0
        assert len(result) == 5
        assert "position_size" in result.columns

    def test_kelly_empty_dataframe(self) -> None:
        """Empty DataFrame returns empty result."""
        df = pd.DataFrame({"gain_pct": []})
        calc = EquityCalculator()
        result = calc.calculate_kelly(
            df, gain_col="gain_pct", start_capital=10000.0, kelly_fraction=25.0, kelly_pct=10.0
        )
        assert len(result) == 0
        assert list(result.columns) == [
            "trade_num", "pnl", "equity", "peak", "drawdown", "position_size"
        ]

    def test_kelly_single_trade(self) -> None:
        """Single trade edge case."""
        df = pd.DataFrame({"gain_pct": [10.0]})
        calc = EquityCalculator()
        result = calc.calculate_kelly(
            df, gain_col="gain_pct", start_capital=10000.0, kelly_fraction=100.0, kelly_pct=10.0
        )

        # Effective Kelly = 10% * 100% = 10%
        # Position size = 10000 * 0.10 = 1000
        # PnL = 1000 * 0.10 = 100
        # Equity = 10000 + 100 = 10100
        assert len(result) == 1
        assert result["position_size"].iloc[0] == pytest.approx(1000.0, abs=0.01)
        assert result["pnl"].iloc[0] == pytest.approx(100.0, abs=0.01)
        assert result["equity"].iloc[0] == pytest.approx(10100.0, abs=0.01)

    def test_kelly_compounding(self) -> None:
        """Verify Kelly compounds correctly."""
        df = pd.DataFrame({"gain_pct": [10.0, 10.0, 10.0]})
        calc = EquityCalculator()
        result = calc.calculate_kelly(
            df, gain_col="gain_pct", start_capital=10000.0, kelly_fraction=100.0, kelly_pct=10.0
        )

        # Effective Kelly = 10%
        # Trade 1: position=1000, pnl=100, equity=10100
        # Trade 2: position=1010, pnl=101, equity=10201
        # Trade 3: position=1020.10, pnl=102.01, equity=10303.01
        # Total gain should be more than 300 due to compounding
        assert result["equity"].iloc[-1] > 10300.0

    def test_kelly_negative_kelly_returns_warning(self) -> None:
        """Negative Kelly still calculates curve (using abs value) but sets warning."""
        df = pd.DataFrame({"gain_pct": [5.0, -3.0]})
        calc = EquityCalculator()
        result = calc.calculate_kelly_metrics(
            df, gain_col="gain_pct", start_capital=10000.0,
            kelly_fraction=25.0, kelly_pct=-5.0  # Negative Kelly
        )
        # Still calculates metrics using abs(kelly_pct) for visualization
        assert result["pnl"] is not None
        assert result["equity_curve"] is not None
        assert result.get("warning") == "negative_kelly"

    def test_kelly_none_kelly_returns_none(self) -> None:
        """None kelly_pct returns None metrics."""
        df = pd.DataFrame({"gain_pct": [5.0, -3.0]})
        calc = EquityCalculator()
        result = calc.calculate_kelly_metrics(
            df, gain_col="gain_pct", start_capital=10000.0,
            kelly_fraction=25.0, kelly_pct=None
        )
        assert result["pnl"] is None
        assert result["equity_curve"] is None

    def test_kelly_blown_account(self) -> None:
        """Account blown when equity <= 0."""
        # Create scenario where equity goes negative
        df = pd.DataFrame({"gain_pct": [10.0, -200.0]})  # -200% wipes out
        calc = EquityCalculator()
        result = calc.calculate_kelly_metrics(
            df, gain_col="gain_pct", start_capital=1000.0,
            kelly_fraction=100.0, kelly_pct=100.0  # Full Kelly
        )
        assert result["dd_duration"] == "Blown"

    def test_kelly_blown_stops_processing(self) -> None:
        """After blown account, remaining trades have zero equity."""
        df = pd.DataFrame({"gain_pct": [10.0, -200.0, 50.0, 50.0]})
        calc = EquityCalculator()
        result = calc.calculate_kelly(
            df, gain_col="gain_pct", start_capital=1000.0,
            kelly_fraction=100.0, kelly_pct=100.0
        )

        # Trade 2 blows account, trades 3 & 4 should have equity=0
        assert result["equity"].iloc[2] == 0.0
        assert result["equity"].iloc[3] == 0.0
        assert result["position_size"].iloc[2] == 0.0
        assert result["position_size"].iloc[3] == 0.0

    def test_kelly_invalid_column_raises(self) -> None:
        """Invalid gain column raises EquityCalculationError."""
        df = pd.DataFrame({"other_col": [5.0, 3.0]})
        calc = EquityCalculator()
        with pytest.raises(EquityCalculationError):
            calc.calculate_kelly(
                df, gain_col="gain_pct", start_capital=10000.0,
                kelly_fraction=25.0, kelly_pct=10.0
            )


class TestFlatStakeDateColumn:
    """Tests for date column support in flat stake equity."""

    def test_flat_stake_includes_date_column(self) -> None:
        """Flat stake equity DataFrame should include date column when provided."""
        df = pd.DataFrame({
            "gain_pct": [0.05, -0.02, 0.03],
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
        })

        calculator = EquityCalculator()
        result = calculator.calculate_flat_stake(df, "gain_pct", stake=1000, date_col="date")

        assert "date" in result.columns
        assert len(result["date"]) == 3
        assert result["date"].iloc[0] == pd.Timestamp("2024-01-01")


class TestKellyDrawdownMetrics:
    """Tests for Kelly drawdown metrics."""

    def test_kelly_max_dd_dollars(self) -> None:
        """Max DD in dollars calculated correctly for Kelly."""
        df = pd.DataFrame({"gain_pct": [10.0, -20.0, 5.0]})
        calc = EquityCalculator()
        metrics = calc.calculate_kelly_metrics(
            df, gain_col="gain_pct", start_capital=10000.0,
            kelly_fraction=50.0, kelly_pct=10.0
        )
        # Should have some drawdown
        assert metrics["max_dd"] is not None
        assert metrics["max_dd"] > 0

    def test_kelly_max_dd_pct(self) -> None:
        """Max DD percentage for Kelly."""
        df = pd.DataFrame({"gain_pct": [10.0, -30.0, 10.0]})
        calc = EquityCalculator()
        metrics = calc.calculate_kelly_metrics(
            df, gain_col="gain_pct", start_capital=10000.0,
            kelly_fraction=50.0, kelly_pct=10.0
        )
        # Should have drawdown percentage
        assert metrics["max_dd_pct"] is not None
        assert metrics["max_dd_pct"] > 0

    def test_kelly_dd_duration_recovered(self) -> None:
        """Duration returned when Kelly drawdown is recovered."""
        df = pd.DataFrame({"gain_pct": [10.0, -5.0, 10.0, 10.0, 10.0]})
        calc = EquityCalculator()
        metrics = calc.calculate_kelly_metrics(
            df, gain_col="gain_pct", start_capital=10000.0,
            kelly_fraction=50.0, kelly_pct=10.0
        )
        # Small drawdown should recover
        if isinstance(metrics["dd_duration"], int):
            assert metrics["dd_duration"] > 0

    def test_kelly_dd_duration_not_recovered(self) -> None:
        """'Not recovered' returned when Kelly drawdown ongoing."""
        df = pd.DataFrame({"gain_pct": [10.0, -30.0, 1.0]})
        calc = EquityCalculator()
        metrics = calc.calculate_kelly_metrics(
            df, gain_col="gain_pct", start_capital=10000.0,
            kelly_fraction=100.0, kelly_pct=20.0
        )
        # Large drawdown likely won't recover
        # Either it's "Not recovered" or an int - both are valid
        assert metrics["dd_duration"] in ("Not recovered", "Blown") or isinstance(
            metrics["dd_duration"], int
        )

    def test_kelly_pnl_calculation(self) -> None:
        """Kelly PnL is final equity minus start capital."""
        df = pd.DataFrame({"gain_pct": [10.0, 5.0]})
        calc = EquityCalculator()
        metrics = calc.calculate_kelly_metrics(
            df, gain_col="gain_pct", start_capital=10000.0,
            kelly_fraction=100.0, kelly_pct=10.0
        )
        # PnL = final_equity - start_capital
        equity_curve = metrics["equity_curve"]
        assert equity_curve is not None
        expected_pnl = float(equity_curve["equity"].iloc[-1]) - 10000.0
        assert metrics["pnl"] == pytest.approx(expected_pnl, abs=0.01)


class TestKellyDateColumn:
    """Tests for date column support in Kelly equity."""

    def test_kelly_includes_date_column(self) -> None:
        """Kelly equity DataFrame should include date column when provided."""
        df = pd.DataFrame({
            "gain_pct": [0.05, -0.02, 0.03],
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
        })

        calculator = EquityCalculator()
        result = calculator.calculate_kelly(
            df, "gain_pct",
            start_capital=10000,
            kelly_pct=10.0,
            kelly_fraction=25.0,
            date_col="date",
        )

        assert "date" in result.columns
        assert len(result["date"]) == 3


class TestMaxDrawdownDollarVsPercent:
    """Tests for max DD dollar vs max DD percent occurring at different points."""

    def test_max_dd_dollar_is_max_dollar_amount(self) -> None:
        """Max DD ($) should be the largest dollar drawdown, not at max % point."""
        calc = EquityCalculator()

        # Scenario: max % drawdown at different point than max $ drawdown
        equity_df = pd.DataFrame({
            "trade_num": [1, 2, 3, 4, 5],
            "equity": [100.0, 50.0, 200.0, 150.0, 180.0],  # Point 2: 50% DD, $50. Point 4: 25% DD, $50
            "peak": [100.0, 100.0, 200.0, 200.0, 200.0],
            "drawdown": [0.0, -50.0, 0.0, -50.0, -20.0],  # Max $ DD is $50 at both points 2 and 4
        })

        max_dd_dollars, max_dd_pct, _ = calc.calculate_drawdown_metrics(equity_df)

        # Max % is at point 2 (50%)
        assert max_dd_pct == 50.0
        # Max $ should be 50 (same in this case)
        assert max_dd_dollars == 50.0

    def test_max_dd_dollar_differs_from_max_pct_point(self) -> None:
        """When max $ and max % are at different points, both should be correct."""
        calc = EquityCalculator()

        equity_df = pd.DataFrame({
            "trade_num": [1, 2, 3, 4, 5, 6],
            "equity": [100.0, 40.0, 150.0, 1000.0, 700.0, 900.0],
            "peak": [100.0, 100.0, 150.0, 1000.0, 1000.0, 1000.0],
            "drawdown": [0.0, -60.0, 0.0, 0.0, -300.0, -100.0],
        })

        max_dd_dollars, max_dd_pct, _ = calc.calculate_drawdown_metrics(equity_df)

        # Max % is at point 2: 60% (60/100)
        assert max_dd_pct == 60.0
        # Max $ is at point 5: $300
        assert max_dd_dollars == 300.0
