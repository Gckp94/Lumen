# tests/conftest.py
"""Shared pytest fixtures for Lumen tests."""

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
import pytest

if TYPE_CHECKING:
    from src.core.cache_manager import CacheManager
    from src.core.models import ColumnMapping, FilterCriteria, TradingMetrics


@pytest.fixture
def sample_csv_file(tmp_path: Path) -> Path:
    """Create sample CSV file for testing."""
    csv_file = tmp_path / "trades.csv"
    df = pd.DataFrame(
        {
            "ticker": ["AAPL", "GOOGL", "MSFT"],
            "date": ["2024-01-01", "2024-01-01", "2024-01-02"],
            "time": ["09:30:00", "10:00:00", "09:35:00"],
            "gain_pct": [1.5, -0.8, 2.1],
        }
    )
    df.to_csv(csv_file, index=False)
    return csv_file


@pytest.fixture
def sample_excel_file(tmp_path: Path) -> Path:
    """Create sample Excel file for testing."""
    excel_file = tmp_path / "trades.xlsx"
    df = pd.DataFrame(
        {
            "ticker": ["AAPL", "GOOGL"],
            "date": ["2024-01-01", "2024-01-02"],
            "gain_pct": [1.5, 2.1],
        }
    )
    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False)
        df.to_excel(writer, sheet_name="Sheet2", index=False)
    return excel_file


@pytest.fixture
def sample_parquet_file(tmp_path: Path) -> Path:
    """Create sample Parquet file for testing."""
    parquet_file = tmp_path / "trades.parquet"
    df = pd.DataFrame(
        {
            "ticker": ["AAPL", "GOOGL"],
            "date": ["2024-01-01", "2024-01-02"],
            "gain_pct": [1.5, 2.1],
        }
    )
    df.to_parquet(parquet_file)
    return parquet_file


@pytest.fixture
def sample_column_mapping() -> "ColumnMapping":
    """Standard column mapping for testing."""
    from src.core.models import ColumnMapping

    return ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
        win_loss_derived=True,
    )


@pytest.fixture
def sample_columns() -> list[str]:
    """Standard DataFrame columns for testing."""
    return ["ticker", "date", "time", "gain_pct", "mae_pct", "win_loss", "volume", "price"]


@pytest.fixture
def cache_manager(tmp_path: Path) -> "CacheManager":
    """CacheManager with temp directory."""
    from src.core.cache_manager import CacheManager

    return CacheManager(cache_dir=tmp_path / ".lumen_cache")


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Sample DataFrame for testing column config panel."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "GOOGL", "MSFT", "TSLA"],
            "date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
            "time": ["09:30:00", "10:00:00", "09:35:00", "11:00:00"],
            "gain_pct": [1.5, -0.8, 2.1, 0.0],
            "mae_pct": [0.5, 1.2, 0.3, 0.0],
            "mfe_pct": [2.0, 0.5, 2.5, 0.0],
            "win_loss": ["W", "L", "W", "W"],
            "volume": [1000, 2000, 1500, 3000],
            "price": [150.0, 2800.0, 380.0, 250.0],
        }
    )


@pytest.fixture
def sample_trades() -> pd.DataFrame:
    """Sample trades DataFrame for filter testing."""
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "GOOGL", "MSFT", "TSLA", "META"],
            "date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
            "time": ["09:30:00", "10:00:00", "09:35:00", "11:00:00", "14:30:00"],
            "gain_pct": [-5.0, 0.0, 5.0, 10.0, 15.0],
            "mae_pct": [2.0, 1.0, 0.5, 1.5, 1.0],
            "mfe_pct": [0.5, 1.0, 6.0, 12.0, 16.0],
            "volume": [1000, 2000, 1500, 3000, 2500],
        }
    )


@pytest.fixture
def sample_filters() -> list["FilterCriteria"]:
    """Sample filter criteria for testing."""
    from src.core.models import FilterCriteria

    return [
        FilterCriteria(column="gain_pct", operator="between", min_val=0, max_val=10),
    ]


@pytest.fixture
def large_dataset_path(tmp_path: Path) -> Path:
    """Create large CSV file with 100k rows for performance testing."""
    import numpy as np

    csv_file = tmp_path / "large_trades.csv"
    np.random.seed(42)

    df = pd.DataFrame({
        "ticker": np.random.choice([f"TICK{i}" for i in range(50)], 100_000),
        "date": np.random.choice(
            pd.date_range("2024-01-01", periods=250).strftime("%Y-%m-%d"),
            100_000,
        ),
        "time": pd.to_datetime(
            np.random.randint(0, 86400, 100_000), unit="s"
        ).strftime("%H:%M:%S"),
        "gain_pct": np.random.normal(0.5, 3, 100_000),
        "volume": np.random.randint(100, 10000, 100_000),
    })
    df.to_csv(csv_file, index=False)
    return csv_file


@pytest.fixture
def sample_baseline_metrics() -> "TradingMetrics":
    """Sample baseline TradingMetrics for testing."""
    from src.core.models import TradingMetrics

    return TradingMetrics(
        num_trades=1000,
        win_rate=55.0,
        avg_winner=2.5,
        avg_loser=-1.5,
        rr_ratio=1.67,
        ev=0.7,
        kelly=10.5,
        winner_count=550,
        loser_count=450,
        winner_std=1.2,
        loser_std=0.8,
        winner_gains=[2.0, 2.5, 3.0],
        loser_gains=[-1.0, -1.5, -2.0],
        edge=700.0,
        fractional_kelly=5.25,
        eg_full_kelly=0.5,
        eg_frac_kelly=0.4,
        eg_flat_stake=0.3,
        median_winner=2.3,
        median_loser=-1.4,
        winner_min=0.1,
        winner_max=10.0,
        loser_min=-5.0,
        loser_max=-0.1,
        max_consecutive_wins=8,
        max_consecutive_losses=5,
        max_loss_pct=-5.0,
        flat_stake_pnl=7000.0,
        flat_stake_max_dd=-2000.0,
        flat_stake_max_dd_pct=-10.0,
        flat_stake_dd_duration=30,
        kelly_pnl=15000.0,
        kelly_max_dd=-4000.0,
        kelly_max_dd_pct=-20.0,
        kelly_dd_duration=45,
    )


@pytest.fixture
def sample_filtered_metrics() -> "TradingMetrics":
    """Sample filtered TradingMetrics for testing."""
    from src.core.models import TradingMetrics

    return TradingMetrics(
        num_trades=500,
        win_rate=60.0,
        avg_winner=3.0,
        avg_loser=-1.2,
        rr_ratio=2.5,
        ev=1.2,
        kelly=15.0,
        winner_count=300,
        loser_count=200,
        winner_std=1.0,
        loser_std=0.6,
        winner_gains=[2.5, 3.0, 3.5],
        loser_gains=[-0.8, -1.2, -1.5],
        edge=600.0,
        fractional_kelly=7.5,
        eg_full_kelly=0.8,
        eg_frac_kelly=0.6,
        eg_flat_stake=0.5,
        median_winner=2.8,
        median_loser=-1.1,
        winner_min=0.5,
        winner_max=8.0,
        loser_min=-3.0,
        loser_max=-0.2,
        max_consecutive_wins=10,
        max_consecutive_losses=3,
        max_loss_pct=-3.0,
        flat_stake_pnl=6000.0,
        flat_stake_max_dd=-1500.0,
        flat_stake_max_dd_pct=-7.5,
        flat_stake_dd_duration=20,
        kelly_pnl=12000.0,
        kelly_max_dd=-3000.0,
        kelly_max_dd_pct=-15.0,
        kelly_dd_duration=30,
    )
