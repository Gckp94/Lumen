"""Unit tests for MCP server functions."""

import asyncio
import json

import pandas as pd
import pytest

from mcp_server.server import (
    GetBreakdownInput,
    GetPortfolioStatsInput,
    GetStatisticsInput,
    LoadedDataset,
    _datasets,
    lumen_get_breakdown,
    lumen_get_portfolio_stats,
    lumen_get_statistics,
)
from src.core.models import ColumnMapping


@pytest.fixture
def sample_df():
    """Create a sample DataFrame for testing."""
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=10, freq="D"),
        "time": ["09:30:00"] * 10,
        "ticker": ["AAPL"] * 10,
        "gain_pct": [0.05, -0.02, 0.03, -0.01, 0.04, -0.03, 0.02, -0.02, 0.06, -0.01],
        "mae_pct": [0.02, 0.03, 0.01, 0.02, 0.03, 0.04, 0.01, 0.03, 0.02, 0.02],
        "mfe_pct": [0.06, 0.01, 0.04, 0.01, 0.05, 0.02, 0.03, 0.01, 0.07, 0.01],
    })


@pytest.fixture
def sample_mapping():
    """Create a sample column mapping."""
    return ColumnMapping(
        ticker="ticker",
        date="date",
        time="time",
        gain_pct="gain_pct",
        mae_pct="mae_pct",
        mfe_pct="mfe_pct",
    )


@pytest.fixture
def loaded_dataset(sample_df, sample_mapping):
    """Create a loaded dataset in the global store."""
    alias = "test_data"
    _datasets[alias] = LoadedDataset(
        alias=alias,
        file_path="test.csv",
        df=sample_df,
        mapping=sample_mapping,
    )
    yield alias
    # Cleanup
    _datasets.pop(alias, None)


class TestLumenGetBreakdown:
    """Tests for lumen_get_breakdown function."""

    def test_yearly_breakdown(self, loaded_dataset):
        """Test yearly breakdown returns valid data."""
        params = GetBreakdownInput(alias=loaded_dataset, period="yearly")
        result = asyncio.run(lumen_get_breakdown(params))
        data = json.loads(result)

        assert data["alias"] == loaded_dataset
        assert data["period"] == "yearly"
        assert "breakdown" in data
        assert "2024" in data["breakdown"]

    def test_monthly_breakdown(self, loaded_dataset):
        """Test monthly breakdown for specific year."""
        params = GetBreakdownInput(alias=loaded_dataset, period="monthly", year=2024)
        result = asyncio.run(lumen_get_breakdown(params))
        data = json.loads(result)

        assert data["alias"] == loaded_dataset
        assert data["period"] == "monthly"
        assert data["year"] == 2024
        assert "breakdown" in data
        assert "Jan" in data["breakdown"]

    def test_missing_dataset(self):
        """Test error for missing dataset."""
        params = GetBreakdownInput(alias="nonexistent", period="yearly")
        result = asyncio.run(lumen_get_breakdown(params))
        assert "Error" in result

    def test_monthly_without_year(self, loaded_dataset):
        """Test error when monthly period requested without year."""
        params = GetBreakdownInput(alias=loaded_dataset, period="monthly")
        result = asyncio.run(lumen_get_breakdown(params))
        data = json.loads(result)
        assert "error" in data
        assert "Year is required" in data["error"]


class TestLumenGetPortfolioStats:
    """Tests for lumen_get_portfolio_stats function."""

    def test_basic_portfolio_stats(self, loaded_dataset):
        """Test basic portfolio stats calculation."""
        params = GetPortfolioStatsInput(alias=loaded_dataset)
        result = asyncio.run(lumen_get_portfolio_stats(params))
        data = json.loads(result)

        assert data["alias"] == loaded_dataset
        assert "metrics" in data
        metrics = data["metrics"]
        # Check some key metrics exist
        assert "sharpe_ratio" in metrics
        assert "sortino_ratio" in metrics
        assert "max_drawdown_pct" in metrics

    def test_missing_dataset(self):
        """Test error for missing dataset."""
        params = GetPortfolioStatsInput(alias="nonexistent")
        result = asyncio.run(lumen_get_portfolio_stats(params))
        assert "Error" in result


class TestLumenGetStatistics:
    """Tests for lumen_get_statistics function."""

    def test_all_tables(self, loaded_dataset):
        """Test getting all statistics tables."""
        params = GetStatisticsInput(alias=loaded_dataset)
        result = asyncio.run(lumen_get_statistics(params))
        data = json.loads(result)

        assert data["alias"] == loaded_dataset
        assert "tables" in data
        # Check some tables exist
        assert "mae_before_win" in data["tables"]
        assert "stop_loss" in data["tables"]

    def test_specific_tables(self, loaded_dataset):
        """Test getting specific tables only."""
        params = GetStatisticsInput(
            alias=loaded_dataset,
            tables=["stop_loss", "offset"],
        )
        result = asyncio.run(lumen_get_statistics(params))
        data = json.loads(result)

        assert "stop_loss" in data["tables"]
        assert "offset" in data["tables"]
        assert "scaling" not in data["tables"]

    def test_invalid_table_name(self, loaded_dataset):
        """Test error for invalid table name."""
        params = GetStatisticsInput(
            alias=loaded_dataset,
            tables=["invalid_table"],
        )
        result = asyncio.run(lumen_get_statistics(params))
        data = json.loads(result)
        assert "error" in data
        assert "Invalid table names" in data["error"]

    def test_missing_dataset(self):
        """Test error for missing dataset."""
        params = GetStatisticsInput(alias="nonexistent")
        result = asyncio.run(lumen_get_statistics(params))
        assert "Error" in result
