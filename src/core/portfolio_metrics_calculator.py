# src/core/portfolio_metrics_calculator.py
"""Portfolio metrics calculator for quantitative strategy evaluation.

Calculates comprehensive metrics from equity curve data including:
- Standalone quality metrics (CAGR, Sharpe, Sortino, Calmar, etc.)
- Period-based metrics (day/week/month win rates and returns)
- Risk metrics (VaR, CVaR, max drawdown)
"""
import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class PeriodMetrics:
    """Metrics for a specific time period (day/week/month)."""

    avg_green_pct: float | None  # Average return on winning periods
    avg_red_pct: float | None  # Average return on losing periods
    win_pct: float | None  # Percentage of winning periods
    rr_ratio: float | None  # Reward:Risk ratio
    max_win_pct: float | None  # Maximum winning period return
    max_loss_pct: float | None  # Maximum losing period return


@dataclass
class CorrelationMetrics:
    """Correlation and diversification metrics between baseline and combined."""

    pearson_correlation: float | None  # Standard linear correlation
    rolling_correlation_current: float | None  # Current 60-day rolling correlation
    rolling_correlation_min: float | None  # Minimum rolling correlation
    rolling_correlation_max: float | None  # Maximum rolling correlation
    tail_correlation: float | None  # Correlation during stress periods
    drawdown_correlation: float | None  # Correlation of drawdown series
    lower_tail_dependence: float | None  # Joint extreme loss probability


@dataclass
class ContributionMetrics:
    """Portfolio contribution metrics showing impact of adding strategy."""

    # Marginal Sharpe
    sharpe_baseline: float | None
    sharpe_combined: float | None
    sharpe_improvement: float | None

    # VaR Contribution
    var_baseline: float | None
    var_combined: float | None
    var_marginal: float | None

    # CVaR Contribution
    cvar_baseline: float | None
    cvar_combined: float | None
    cvar_marginal: float | None


@dataclass
class PortfolioMetrics:
    """Complete portfolio metrics."""

    # Core statistics
    cagr: float | None
    sharpe_ratio: float | None
    sortino_ratio: float | None
    calmar_ratio: float | None
    win_rate: float | None
    profit_factor: float | None

    # Drawdown metrics
    max_drawdown_pct: float | None
    max_drawdown_dollars: float | None
    max_dd_duration_days: int | None
    time_underwater_pct: float | None

    # Statistical metrics
    t_statistic: float | None
    p_value: float | None

    # Period metrics
    daily: PeriodMetrics | None
    weekly: PeriodMetrics | None
    monthly: PeriodMetrics | None

    # Additional ratios
    var_95: float | None  # 95% Value at Risk
    cvar_95: float | None  # 95% Conditional VaR (Expected Shortfall)


class PortfolioMetricsCalculator:
    """Calculates comprehensive portfolio metrics from equity curves."""

    def __init__(self, starting_capital: float = 100_000) -> None:
        """Initialize calculator.

        Args:
            starting_capital: Initial account value for calculations.
        """
        self.starting_capital = starting_capital

    def calculate_cagr(self, equity_curve: pd.DataFrame) -> float | None:
        """Calculate Compound Annual Growth Rate.

        CAGR = (Ending Value / Beginning Value)^(1/Years) - 1

        Args:
            equity_curve: DataFrame with 'equity' and 'date' columns.

        Returns:
            CAGR as percentage (e.g., 15.5 for 15.5%), or None if insufficient data.
        """
        if equity_curve.empty or len(equity_curve) < 2:
            return None

        beginning_value = self.starting_capital
        ending_value = equity_curve["equity"].iloc[-1]

        # Calculate years from date range
        dates = pd.to_datetime(equity_curve["date"])
        days = (dates.max() - dates.min()).days
        if days == 0:
            return None

        years = days / 365.25

        if beginning_value <= 0:
            return None

        # Handle negative ending value (blown account)
        if ending_value <= 0:
            return -100.0

        cagr = (ending_value / beginning_value) ** (1 / years) - 1
        return cagr * 100  # Convert to percentage

    def _calculate_daily_returns(self, equity_curve: pd.DataFrame) -> pd.Series:
        """Calculate daily returns from equity curve.

        Args:
            equity_curve: DataFrame with 'equity' column.

        Returns:
            Series of daily returns as decimals.
        """
        equities = equity_curve["equity"].astype(float)
        # Prepend starting capital for first return calculation
        with_start = pd.concat([pd.Series([self.starting_capital]), equities])
        returns = with_start.pct_change().dropna()
        return returns.reset_index(drop=True)

    def calculate_sharpe_ratio(
        self, equity_curve: pd.DataFrame, rf_rate: float = 0.0
    ) -> float | None:
        """Calculate annualized Sharpe ratio.

        Sharpe = (Mean Return - Risk Free Rate) / Std Dev of Returns
        Annualized = Daily Sharpe * sqrt(252)

        Args:
            equity_curve: DataFrame with 'equity' column.
            rf_rate: Annual risk-free rate (default 0).

        Returns:
            Annualized Sharpe ratio, or None if insufficient data.
        """
        returns = self._calculate_daily_returns(equity_curve)
        if len(returns) < 2:
            return None

        daily_rf = rf_rate / 252
        excess_returns = returns - daily_rf

        std = excess_returns.std()
        if std == 0:
            return None

        daily_sharpe = excess_returns.mean() / std
        return float(daily_sharpe * np.sqrt(252))

    def calculate_sortino_ratio(
        self, equity_curve: pd.DataFrame, target: float = 0.0
    ) -> float | None:
        """Calculate annualized Sortino ratio.

        Sortino = (Mean Return - Target) / Downside Deviation
        Downside deviation only considers returns below target.

        Args:
            equity_curve: DataFrame with 'equity' column.
            target: Target return (default 0).

        Returns:
            Annualized Sortino ratio, or None if insufficient data.
        """
        returns = self._calculate_daily_returns(equity_curve)
        if len(returns) < 2:
            return None

        # Calculate downside deviation (only negative deviations from target)
        downside = np.minimum(returns - target, 0)
        downside_std = np.sqrt(np.mean(downside**2))

        if downside_std == 0:
            return None

        daily_sortino = (returns.mean() - target) / downside_std
        return float(daily_sortino * np.sqrt(252))

    def calculate_max_drawdown(
        self, equity_curve: pd.DataFrame
    ) -> tuple[float | None, float | None]:
        """Calculate maximum drawdown in percentage and dollars.

        Args:
            equity_curve: DataFrame with 'equity' and 'peak' columns.

        Returns:
            Tuple of (max_dd_percent, max_dd_dollars), or (None, None) if no data.
        """
        if equity_curve.empty:
            return None, None

        equities = equity_curve["equity"].astype(float)
        peaks = equity_curve["peak"].astype(float)

        # Calculate drawdown at each point
        dd_dollars = equities - peaks
        dd_percent = (dd_dollars / peaks) * 100

        # Find maximum drawdown (most negative)
        max_dd_dollars = float(dd_dollars.min())
        max_dd_pct = float(dd_percent.min())

        return abs(max_dd_pct), abs(max_dd_dollars)

    def calculate_drawdown_duration(
        self, equity_curve: pd.DataFrame
    ) -> tuple[int | None, float | None]:
        """Calculate max drawdown duration and time underwater.

        Args:
            equity_curve: DataFrame with 'equity', 'peak', and 'date' columns.

        Returns:
            Tuple of (max_duration_days, time_underwater_pct).
        """
        if equity_curve.empty or len(equity_curve) < 2:
            return None, None

        equities = equity_curve["equity"].astype(float)
        peaks = equity_curve["peak"].astype(float)

        # Underwater when equity < peak
        underwater = equities < peaks
        time_underwater_pct = float(underwater.sum() / len(underwater) * 100)

        # Calculate drawdown periods (consecutive underwater days)
        periods = []
        current_period = 0
        for uw in underwater:
            if uw:
                current_period += 1
            else:
                if current_period > 0:
                    periods.append(current_period)
                current_period = 0
        if current_period > 0:
            periods.append(current_period)

        max_duration = max(periods) if periods else 0

        return max_duration, time_underwater_pct

    def calculate_calmar_ratio(self, equity_curve: pd.DataFrame) -> float | None:
        """Calculate Calmar ratio (CAGR / Max Drawdown).

        Args:
            equity_curve: DataFrame with equity data.

        Returns:
            Calmar ratio, or None if cannot be calculated.
        """
        cagr = self.calculate_cagr(equity_curve)
        max_dd_pct, _ = self.calculate_max_drawdown(equity_curve)

        if cagr is None or max_dd_pct is None or max_dd_pct == 0:
            return None

        return cagr / max_dd_pct

    def calculate_win_rate(self, equity_curve: pd.DataFrame) -> float | None:
        """Calculate win rate percentage.

        Args:
            equity_curve: DataFrame with 'pnl' or 'win' column.

        Returns:
            Win rate as percentage (e.g., 65.0 for 65%), or None.
        """
        if equity_curve.empty:
            return None

        if "win" in equity_curve.columns:
            wins = equity_curve["win"].sum()
            total = len(equity_curve)
        elif "pnl" in equity_curve.columns:
            pnls = equity_curve["pnl"].astype(float)
            wins = (pnls > 0).sum()
            total = len(pnls)
        else:
            return None

        if total == 0:
            return None

        return float(wins / total * 100)

    def calculate_profit_factor(self, equity_curve: pd.DataFrame) -> float | None:
        """Calculate profit factor (gross profits / gross losses).

        Args:
            equity_curve: DataFrame with 'pnl' column.

        Returns:
            Profit factor, or None if no losses.
        """
        if equity_curve.empty or "pnl" not in equity_curve.columns:
            return None

        pnls = equity_curve["pnl"].astype(float)
        gross_profit = pnls[pnls > 0].sum()
        gross_loss = abs(pnls[pnls < 0].sum())

        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else None

        return float(gross_profit / gross_loss)

    def calculate_t_statistic(
        self, equity_curve: pd.DataFrame
    ) -> tuple[float | None, float | None]:
        """Calculate t-statistic testing if mean return differs from zero.

        Args:
            equity_curve: DataFrame with equity data.

        Returns:
            Tuple of (t_statistic, p_value), or (None, None).
        """
        returns = self._calculate_daily_returns(equity_curve)
        if len(returns) < 2:
            return None, None

        t_stat, p_value = stats.ttest_1samp(returns, 0)
        return float(t_stat), float(p_value)

    def calculate_var_cvar(
        self, equity_curve: pd.DataFrame, confidence: float = 0.95
    ) -> tuple[float | None, float | None]:
        """Calculate Value at Risk and Conditional VaR (Expected Shortfall).

        Args:
            equity_curve: DataFrame with equity data.
            confidence: Confidence level (default 0.95 for 95%).

        Returns:
            Tuple of (VaR, CVaR) as percentages, or (None, None).
        """
        returns = self._calculate_daily_returns(equity_curve)
        if len(returns) < 2:
            return None, None

        # VaR is the quantile at (1 - confidence)
        var = float(returns.quantile(1 - confidence) * 100)

        # CVaR is mean of returns worse than VaR
        threshold = returns.quantile(1 - confidence)
        tail_returns = returns[returns <= threshold]
        cvar = var if len(tail_returns) == 0 else float(tail_returns.mean() * 100)

        return var, cvar

    def calculate_period_metrics(
        self, equity_curve: pd.DataFrame, period: str
    ) -> PeriodMetrics | None:
        """Calculate metrics for a specific time period.

        Args:
            equity_curve: DataFrame with date, pnl, equity columns.
            period: "daily", "weekly", or "monthly".

        Returns:
            PeriodMetrics dataclass, or None if insufficient data.
        """
        if equity_curve.empty or "pnl" not in equity_curve.columns:
            return None

        df = equity_curve.copy()
        df["date"] = pd.to_datetime(df["date"])

        # Sort by date and trade_num to ensure "first" aggregation gets chronologically first trade
        # trade_num is needed when multiple trades occur on the same date
        sort_cols = ["date"]
        if "trade_num" in df.columns:
            sort_cols.append("trade_num")
        df = df.sort_values(sort_cols).reset_index(drop=True)

        # Group by period
        if period == "daily":
            df["period"] = df["date"].dt.date
        elif period == "weekly":
            week = df["date"].dt.isocalendar().week.astype(str)
            year = df["date"].dt.year.astype(str)
            df["period"] = week + "-" + year
        elif period == "monthly":
            df["period"] = df["date"].dt.to_period("M")
        else:
            return None

        # Aggregate PnL by period and calculate return %
        period_data = df.groupby("period").agg({
            "pnl": ["sum", "first"],  # Total PnL and first trade's PnL
            "equity": "first",  # Equity after first trade in period
        }).reset_index()

        # Flatten column names after multi-aggregation
        period_data.columns = ["period", "pnl_sum", "pnl_first", "equity_first"]

        # Calculate period return % based on starting equity
        # Start equity = equity after first trade - first trade's PnL
        # This gives us the equity BEFORE any trades in this period
        period_data["start_equity"] = period_data["equity_first"] - period_data["pnl_first"]
        period_data["return_pct"] = (period_data["pnl_sum"] / period_data["start_equity"]) * 100

        returns = period_data["return_pct"]

        if len(returns) == 0:
            return None

        green_returns = returns[returns > 0]
        red_returns = returns[returns < 0]

        # Calculate metrics
        avg_green = float(green_returns.mean()) if len(green_returns) > 0 else None
        avg_red = float(red_returns.mean()) if len(red_returns) > 0 else None
        win_pct = float(len(green_returns) / len(returns) * 100) if len(returns) > 0 else None

        # R:R ratio
        if avg_green is not None and avg_red is not None and avg_red != 0:
            rr_ratio = abs(avg_green / avg_red)
        else:
            rr_ratio = None

        max_win = float(returns.max()) if len(returns) > 0 else None
        max_loss = float(returns.min()) if len(returns) > 0 else None


        return PeriodMetrics(
            avg_green_pct=avg_green,
            avg_red_pct=avg_red,
            win_pct=win_pct,
            rr_ratio=rr_ratio,
            max_win_pct=max_win,
            max_loss_pct=max_loss,
        )

    def calculate_all_metrics(self, equity_curve: pd.DataFrame) -> PortfolioMetrics | None:
        """Calculate all portfolio metrics.

        Args:
            equity_curve: DataFrame with date, trade_num, pnl, equity, peak, drawdown, win.

        Returns:
            PortfolioMetrics dataclass with all calculated values.
        """
        if equity_curve.empty:
            return None

        # Core statistics
        cagr = self.calculate_cagr(equity_curve)
        sharpe = self.calculate_sharpe_ratio(equity_curve)
        sortino = self.calculate_sortino_ratio(equity_curve)
        calmar = self.calculate_calmar_ratio(equity_curve)
        win_rate = self.calculate_win_rate(equity_curve)
        profit_factor = self.calculate_profit_factor(equity_curve)

        # Drawdown metrics
        max_dd_pct, max_dd_dollars = self.calculate_max_drawdown(equity_curve)
        max_dd_duration, time_underwater = self.calculate_drawdown_duration(equity_curve)

        # Statistical metrics
        t_stat, p_value = self.calculate_t_statistic(equity_curve)

        # VaR/CVaR
        var_95, cvar_95 = self.calculate_var_cvar(equity_curve)

        # Period metrics
        daily = self.calculate_period_metrics(equity_curve, "daily")
        weekly = self.calculate_period_metrics(equity_curve, "weekly")
        monthly = self.calculate_period_metrics(equity_curve, "monthly")

        return PortfolioMetrics(
            cagr=cagr,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            win_rate=win_rate,
            profit_factor=profit_factor,
            max_drawdown_pct=max_dd_pct,
            max_drawdown_dollars=max_dd_dollars,
            max_dd_duration_days=max_dd_duration,
            time_underwater_pct=time_underwater,
            t_statistic=t_stat,
            p_value=p_value,
            daily=daily,
            weekly=weekly,
            monthly=monthly,
            var_95=var_95,
            cvar_95=cvar_95,
        )

    def calculate_pearson_correlation(
        self, baseline_df: pd.DataFrame, combined_df: pd.DataFrame
    ) -> float | None:
        """Calculate Pearson correlation between daily returns.

        Args:
            baseline_df: Baseline equity curve with 'equity' column.
            combined_df: Combined equity curve with 'equity' column.

        Returns:
            Correlation coefficient (-1 to 1), or None if insufficient data.
        """
        baseline_returns = self._calculate_daily_returns(baseline_df)
        combined_returns = self._calculate_daily_returns(combined_df)

        if len(baseline_returns) < 10 or len(combined_returns) < 10:
            return None

        # Align lengths
        min_len = min(len(baseline_returns), len(combined_returns))
        baseline_returns = baseline_returns.iloc[:min_len]
        combined_returns = combined_returns.iloc[:min_len]

        return float(baseline_returns.corr(combined_returns))

    def calculate_rolling_correlation(
        self,
        baseline_df: pd.DataFrame,
        combined_df: pd.DataFrame,
        window: int = 60,
    ) -> tuple[float | None, float | None, float | None, pd.Series | None]:
        """Calculate rolling correlation over time.

        Args:
            baseline_df: Baseline equity curve.
            combined_df: Combined equity curve.
            window: Rolling window size in days (default 60).

        Returns:
            Tuple of (current, min, max, full_series) or (None, None, None, None).
        """
        baseline_returns = self._calculate_daily_returns(baseline_df)
        combined_returns = self._calculate_daily_returns(combined_df)

        min_len = min(len(baseline_returns), len(combined_returns))
        if min_len < window:
            return None, None, None, None

        baseline_returns = baseline_returns.iloc[:min_len].reset_index(drop=True)
        combined_returns = combined_returns.iloc[:min_len].reset_index(drop=True)

        rolling_corr = baseline_returns.rolling(window).corr(combined_returns)
        rolling_corr = rolling_corr.dropna()

        if len(rolling_corr) == 0:
            return None, None, None, None

        return (
            float(rolling_corr.iloc[-1]),
            float(rolling_corr.min()),
            float(rolling_corr.max()),
            rolling_corr,
        )

    def calculate_tail_correlation(
        self,
        baseline_df: pd.DataFrame,
        combined_df: pd.DataFrame,
        threshold_std: float = 1.0,
    ) -> float | None:
        """Calculate correlation during stress periods (bad days).

        Filters for days when baseline had large losses (beyond 1 std dev)
        and calculates correlation only on those days.

        Args:
            baseline_df: Baseline equity curve.
            combined_df: Combined equity curve.
            threshold_std: Number of std devs below mean to define "bad days".

        Returns:
            Tail correlation coefficient, or None if insufficient data.
        """
        baseline_returns = self._calculate_daily_returns(baseline_df)
        combined_returns = self._calculate_daily_returns(combined_df)

        min_len = min(len(baseline_returns), len(combined_returns))
        if min_len < 20:
            return None

        baseline_returns = baseline_returns.iloc[:min_len].reset_index(drop=True)
        combined_returns = combined_returns.iloc[:min_len].reset_index(drop=True)

        # Define threshold for "bad days"
        threshold = baseline_returns.mean() - threshold_std * baseline_returns.std()
        bad_days = baseline_returns < threshold

        if bad_days.sum() < 10:
            return None  # Insufficient stress events

        return float(baseline_returns[bad_days].corr(combined_returns[bad_days]))

    def _calculate_drawdown_series(self, equity_curve: pd.DataFrame) -> pd.Series:
        """Calculate drawdown series from equity curve.

        Args:
            equity_curve: DataFrame with 'equity' column.

        Returns:
            Series of drawdown percentages (negative values).
        """
        equities = equity_curve["equity"].astype(float)
        running_max = equities.cummax()
        drawdown = (equities - running_max) / running_max
        return drawdown

    def calculate_drawdown_correlation(
        self, baseline_df: pd.DataFrame, combined_df: pd.DataFrame
    ) -> float | None:
        """Calculate correlation between drawdown series.

        Directly measures whether strategies suffer simultaneously.

        Args:
            baseline_df: Baseline equity curve.
            combined_df: Combined equity curve.

        Returns:
            Drawdown correlation coefficient, or None if insufficient data.
        """
        baseline_dd = self._calculate_drawdown_series(baseline_df)
        combined_dd = self._calculate_drawdown_series(combined_df)

        min_len = min(len(baseline_dd), len(combined_dd))
        if min_len < 10:
            return None

        baseline_dd = baseline_dd.iloc[:min_len].reset_index(drop=True)
        combined_dd = combined_dd.iloc[:min_len].reset_index(drop=True)

        return float(baseline_dd.corr(combined_dd))

    def calculate_lower_tail_dependence(
        self,
        baseline_df: pd.DataFrame,
        combined_df: pd.DataFrame,
        quantile: float = 0.10,
    ) -> float | None:
        """Calculate lower tail dependence coefficient.

        Measures probability that combined is in its worst quantile
        given that baseline is in its worst quantile.

        Args:
            baseline_df: Baseline equity curve.
            combined_df: Combined equity curve.
            quantile: Threshold quantile (default 0.10 for worst 10%).

        Returns:
            Tail dependence coefficient (0-1), or None if insufficient data.
        """
        baseline_returns = self._calculate_daily_returns(baseline_df)
        combined_returns = self._calculate_daily_returns(combined_df)

        min_len = min(len(baseline_returns), len(combined_returns))
        if min_len < 50:
            return None

        baseline_returns = baseline_returns.iloc[:min_len].reset_index(drop=True)
        combined_returns = combined_returns.iloc[:min_len].reset_index(drop=True)

        threshold_baseline = baseline_returns.quantile(quantile)
        threshold_combined = combined_returns.quantile(quantile)

        baseline_below = baseline_returns < threshold_baseline
        combined_below = combined_returns < threshold_combined
        both_below = (baseline_below & combined_below).sum()
        baseline_below_count = baseline_below.sum()

        if baseline_below_count == 0:
            return 0.0

        return float(both_below / baseline_below_count)

    def calculate_marginal_sharpe_contribution(
        self, baseline_df: pd.DataFrame, combined_df: pd.DataFrame
    ) -> dict[str, float | None] | None:
        """Calculate marginal Sharpe contribution from adding strategy.

        Measures the improvement in Sharpe ratio when combining strategies.

        Args:
            baseline_df: Baseline equity curve with 'equity' column.
            combined_df: Combined equity curve with 'equity' column.

        Returns:
            Dict with sharpe_baseline, sharpe_combined, sharpe_improvement,
            or None if insufficient data.
        """
        sharpe_baseline = self.calculate_sharpe_ratio(baseline_df)
        sharpe_combined = self.calculate_sharpe_ratio(combined_df)

        if sharpe_baseline is None or sharpe_combined is None:
            return None

        return {
            "sharpe_baseline": sharpe_baseline,
            "sharpe_combined": sharpe_combined,
            "sharpe_improvement": sharpe_combined - sharpe_baseline,
        }

    def calculate_var_contribution(
        self, baseline_df: pd.DataFrame, combined_df: pd.DataFrame, confidence: float = 0.95
    ) -> dict[str, float | None] | None:
        """Calculate VaR contribution from adding strategy.

        Measures the change in Value at Risk when combining strategies.
        A positive marginal VaR indicates improved risk (less negative).

        Args:
            baseline_df: Baseline equity curve with 'equity' column.
            combined_df: Combined equity curve with 'equity' column.
            confidence: Confidence level (default 0.95 for 95%).

        Returns:
            Dict with var_baseline, var_combined, var_marginal,
            or None if insufficient data.
        """
        var_baseline, _ = self.calculate_var_cvar(baseline_df, confidence)
        var_combined, _ = self.calculate_var_cvar(combined_df, confidence)

        if var_baseline is None or var_combined is None:
            return None

        return {
            "var_baseline": var_baseline,
            "var_combined": var_combined,
            "var_marginal": var_combined - var_baseline,  # Positive if improved
        }

    def calculate_cvar_contribution(
        self, baseline_df: pd.DataFrame, combined_df: pd.DataFrame, confidence: float = 0.95
    ) -> dict[str, float | None] | None:
        """Calculate CVaR contribution from adding strategy.

        Measures the change in Conditional Value at Risk (Expected Shortfall)
        when combining strategies. A positive marginal CVaR indicates
        improved tail risk (less negative).

        Args:
            baseline_df: Baseline equity curve with 'equity' column.
            combined_df: Combined equity curve with 'equity' column.
            confidence: Confidence level (default 0.95 for 95%).

        Returns:
            Dict with cvar_baseline, cvar_combined, cvar_marginal,
            or None if insufficient data.
        """
        _, cvar_baseline = self.calculate_var_cvar(baseline_df, confidence)
        _, cvar_combined = self.calculate_var_cvar(combined_df, confidence)

        if cvar_baseline is None or cvar_combined is None:
            return None

        return {
            "cvar_baseline": cvar_baseline,
            "cvar_combined": cvar_combined,
            "cvar_marginal": cvar_combined - cvar_baseline,  # Positive if improved
        }

    def calculate_edge_decay(
        self, equity_curve: pd.DataFrame, window: int = 252
    ) -> dict[str, float | pd.Series | None] | None:
        """Calculate edge decay analysis via rolling Sharpe ratio and gain metrics.

        Compares early period Sharpe to recent Sharpe to detect decay.
        Also compares early vs recent average and median gain percentages.

        Args:
            equity_curve: Equity curve DataFrame with 'equity' column and optional 'gain_pct'.
            window: Rolling window size (default 252 = 1 year).

        Returns:
            Dict with Sharpe metrics, avg/median gain metrics, or None if insufficient data.
        """
        returns = self._calculate_daily_returns(equity_curve)

        if len(returns) < window * 2:
            return None

        # Calculate rolling Sharpe
        rolling_mean = returns.rolling(window).mean()
        rolling_std = returns.rolling(window).std()
        rolling_sharpe = np.sqrt(252) * rolling_mean / rolling_std
        rolling_sharpe = rolling_sharpe.dropna()

        if len(rolling_sharpe) < window:
            return None

        # Early period: first valid rolling Sharpe
        early_sharpe = float(rolling_sharpe.iloc[0])
        # Current period: most recent rolling Sharpe
        current_sharpe = float(rolling_sharpe.iloc[-1])

        # Calculate Sharpe decay percentage
        if early_sharpe != 0:
            decay_pct = ((current_sharpe - early_sharpe) / abs(early_sharpe)) * 100
        else:
            decay_pct = 0.0

        result: dict[str, float | pd.Series | None] = {
            "rolling_sharpe_current": current_sharpe,
            "rolling_sharpe_early": early_sharpe,
            "decay_pct": decay_pct,
            "rolling_sharpe_series": rolling_sharpe,
        }

        # Calculate avg/median gain metrics if gain_pct column exists
        if "gain_pct" in equity_curve.columns:
            gains = equity_curve["gain_pct"].astype(float)
            n = len(gains)

            if n >= window * 2:
                # Split into early and recent halves based on window
                early_gains = gains.iloc[:window]
                recent_gains = gains.iloc[-window:]

                avg_early = float(early_gains.mean())
                avg_recent = float(recent_gains.mean())
                median_early = float(early_gains.median())
                median_recent = float(recent_gains.median())

                # Calculate change percentages
                if avg_early != 0:
                    avg_change_pct = ((avg_recent - avg_early) / abs(avg_early)) * 100
                else:
                    avg_change_pct = 0.0

                if median_early != 0:
                    median_change_pct = ((median_recent - median_early) / abs(median_early)) * 100
                else:
                    median_change_pct = 0.0

                result["avg_gain_early"] = avg_early
                result["avg_gain_recent"] = avg_recent
                result["avg_gain_change_pct"] = avg_change_pct
                result["median_gain_early"] = median_early
                result["median_gain_recent"] = median_recent
                result["median_gain_change_pct"] = median_change_pct

        return result

    def calculate_ticker_overlap(
        self, baseline_df: pd.DataFrame, combined_df: pd.DataFrame
    ) -> dict[str, int | float] | None:
        """Calculate ticker overlap between baseline and combined portfolios.

        Args:
            baseline_df: Baseline trades with 'ticker' column.
            combined_df: Combined trades with 'ticker' column.

        Returns:
            Dict with counts and overlap percentage, or None if no ticker data.
        """
        if "ticker" not in baseline_df.columns or "ticker" not in combined_df.columns:
            return None

        baseline_tickers = set(baseline_df["ticker"].dropna().unique())
        combined_tickers = set(combined_df["ticker"].dropna().unique())

        if len(baseline_tickers) == 0 or len(combined_tickers) == 0:
            return None

        overlap = baseline_tickers.intersection(combined_tickers)
        overlap_pct = len(overlap) / min(len(baseline_tickers), len(combined_tickers)) * 100

        return {
            "baseline_ticker_count": len(baseline_tickers),
            "combined_ticker_count": len(combined_tickers),
            "overlapping_count": len(overlap),
            "overlap_pct": overlap_pct,
        }

    def calculate_concurrent_exposure(
        self, baseline_df: pd.DataFrame, combined_df: pd.DataFrame
    ) -> dict[str, int | float] | None:
        """Calculate same-day same-ticker concurrent exposure.

        Args:
            baseline_df: Baseline trades with 'date' and 'ticker' columns.
            combined_df: Combined trades with 'date' and 'ticker' columns.

        Returns:
            Dict with concurrent count and percentage, or None if no ticker data.
        """
        if "ticker" not in baseline_df.columns or "ticker" not in combined_df.columns:
            return None

        baseline_df = baseline_df.copy()
        combined_df = combined_df.copy()

        # Filter out rows with None tickers - we only count actual ticker overlap
        baseline_df = baseline_df[baseline_df["ticker"].notna()]
        combined_df = combined_df[combined_df["ticker"].notna()]

        # If no valid tickers in either dataframe, no ticker data available
        if len(baseline_df) == 0 or len(combined_df) == 0:
            return None

        baseline_df["date"] = pd.to_datetime(baseline_df["date"])
        combined_df["date"] = pd.to_datetime(combined_df["date"])

        # Merge on date and ticker
        merged = baseline_df.merge(
            combined_df,
            on=["date", "ticker"],
            how="inner",
            suffixes=("_baseline", "_combined"),
        )

        concurrent_count = len(merged)
        total_trades = len(baseline_df) + len(combined_df)

        if total_trades == 0:
            return None

        # Multiply by 2 because each concurrent trade counts in both portfolios
        concurrent_pct = (concurrent_count * 2 / total_trades) * 100

        return {
            "concurrent_count": concurrent_count,
            "concurrent_pct": concurrent_pct,
        }
