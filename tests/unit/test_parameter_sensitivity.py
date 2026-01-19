# tests/unit/test_parameter_sensitivity.py
"""Tests for parameter sensitivity engine."""

import pytest
import numpy as np
import pandas as pd

from PyQt6.QtCore import QThread
from src.core.parameter_sensitivity import (
    ParameterSensitivityConfig,
    NeighborhoodResult,
    SweepResult,
    ParameterSensitivityEngine,
    ParameterSensitivityWorker,
)
from src.core.models import FilterCriteria


class TestParameterSensitivityConfig:
    """Tests for ParameterSensitivityConfig dataclass."""

    def test_default_config_valid(self):
        """Default configuration should be valid."""
        config = ParameterSensitivityConfig()
        assert config.mode == "neighborhood"
        assert config.perturbation_levels == (0.05, 0.10, 0.15)
        assert config.grid_resolution == 10
        assert "win_rate" in config.metrics

    def test_sweep_mode_config(self):
        """Sweep mode configuration should store filter settings."""
        config = ParameterSensitivityConfig(
            mode="sweep",
            sweep_filter_1="Entry Time",
            sweep_range_1=(9.0, 12.0),
            sweep_filter_2="Gap %",
            sweep_range_2=(2.0, 8.0),
            grid_resolution=15,
        )
        assert config.mode == "sweep"
        assert config.sweep_filter_1 == "Entry Time"
        assert config.grid_resolution == 15

    def test_invalid_mode_raises(self):
        """Invalid mode should raise ValueError."""
        with pytest.raises(ValueError, match="mode must be"):
            ParameterSensitivityConfig(mode="invalid")

    def test_invalid_grid_resolution_raises(self):
        """Grid resolution outside 5-25 should raise ValueError."""
        with pytest.raises(ValueError, match="grid_resolution"):
            ParameterSensitivityConfig(grid_resolution=3)
        with pytest.raises(ValueError, match="grid_resolution"):
            ParameterSensitivityConfig(grid_resolution=30)


class TestParameterSensitivityEngine:
    """Tests for ParameterSensitivityEngine."""

    @pytest.fixture
    def sample_df(self):
        """Create sample trading data."""
        np.random.seed(42)
        n = 100
        return pd.DataFrame({
            "gain_pct": np.random.uniform(-0.05, 0.10, n),
            "entry_time": np.random.uniform(9.0, 16.0, n),
            "gap_pct": np.random.uniform(1.0, 10.0, n),
        })

    @pytest.fixture
    def sample_filters(self):
        """Create sample filters."""
        return [
            FilterCriteria(column="entry_time", operator="between", min_val=9.5, max_val=11.0),
            FilterCriteria(column="gap_pct", operator="between", min_val=2.0, max_val=6.0),
        ]

    def test_engine_initialization(self, sample_df, sample_filters):
        """Engine should initialize with baseline data and filters."""
        engine = ParameterSensitivityEngine(
            baseline_df=sample_df,
            column_mapping={"gain": "gain_pct"},
            active_filters=sample_filters,
        )
        assert engine._baseline_df is not None
        assert len(engine._active_filters) == 2

    def test_engine_cancel(self, sample_df, sample_filters):
        """Engine should support cancellation."""
        engine = ParameterSensitivityEngine(
            baseline_df=sample_df,
            column_mapping={"gain": "gain_pct"},
            active_filters=sample_filters,
        )
        assert not engine._cancelled
        engine.cancel()
        assert engine._cancelled

    def test_generate_perturbations(self, sample_df, sample_filters):
        """Should generate perturbed filter configurations."""
        engine = ParameterSensitivityEngine(
            baseline_df=sample_df,
            column_mapping={"gain": "gain_pct"},
            active_filters=sample_filters,
        )

        # Test perturbation of entry_time filter (9.5 - 11.0, range = 1.5)
        original = sample_filters[0]
        perturbed = engine._generate_perturbations(original, level=0.10)

        # Should return 4 variations: shift down, shift up, expand, contract
        assert len(perturbed) == 4

        # Check shift down (both bounds - 10% of range = -0.15)
        assert perturbed[0].min_val == pytest.approx(9.35, abs=0.01)
        assert perturbed[0].max_val == pytest.approx(10.85, abs=0.01)

        # Check shift up (both bounds + 10% of range = +0.15)
        assert perturbed[1].min_val == pytest.approx(9.65, abs=0.01)
        assert perturbed[1].max_val == pytest.approx(11.15, abs=0.01)

    def test_calculate_metrics_for_config(self, sample_df, sample_filters):
        """Should calculate metrics for a filter configuration."""
        engine = ParameterSensitivityEngine(
            baseline_df=sample_df,
            column_mapping={"gain": "gain_pct"},
            active_filters=sample_filters,
        )

        metrics = engine._calculate_metrics_for_filters(sample_filters)

        assert "win_rate" in metrics
        assert "profit_factor" in metrics
        assert "expected_value" in metrics
        assert isinstance(metrics["win_rate"], float)

    def test_run_neighborhood_scan(self, sample_df, sample_filters):
        """Should run complete neighborhood scan and return results."""
        engine = ParameterSensitivityEngine(
            baseline_df=sample_df,
            column_mapping={"gain": "gain_pct"},
            active_filters=sample_filters,
        )
        config = ParameterSensitivityConfig(
            mode="neighborhood",
            perturbation_levels=(0.05, 0.10),
            metrics=("win_rate", "expected_value"),
        )

        results = engine.run_neighborhood_scan(config)

        # Should have result for each filter
        assert len(results) == 2

        # Check first result structure
        result = results[0]
        assert isinstance(result, NeighborhoodResult)
        assert result.filter_column == "entry_time"
        assert result.baseline_metrics is not None
        assert 0.05 in result.perturbations
        assert 0.10 in result.perturbations
        assert result.status in ("robust", "caution", "fragile")

    def test_neighborhood_scan_with_progress(self, sample_df, sample_filters):
        """Should call progress callback during scan."""
        engine = ParameterSensitivityEngine(
            baseline_df=sample_df,
            column_mapping={"gain": "gain_pct"},
            active_filters=sample_filters,
        )
        config = ParameterSensitivityConfig(mode="neighborhood")

        progress_calls = []
        def on_progress(current, total):
            progress_calls.append((current, total))

        engine.run_neighborhood_scan(config, progress_callback=on_progress)

        assert len(progress_calls) > 0
        # Final call should be complete
        assert progress_calls[-1][0] == progress_calls[-1][1]

    def test_run_parameter_sweep_1d(self, sample_df):
        """Should run 1D parameter sweep (single filter)."""
        engine = ParameterSensitivityEngine(
            baseline_df=sample_df,
            column_mapping={"gain": "gain_pct"},
            active_filters=[],
        )
        config = ParameterSensitivityConfig(
            mode="sweep",
            sweep_filter_1="entry_time",
            sweep_range_1=(9.0, 12.0),
            sweep_filter_2=None,
            sweep_range_2=None,
            grid_resolution=5,
            metrics=("win_rate", "expected_value"),
        )

        result = engine.run_parameter_sweep(config)

        assert isinstance(result, SweepResult)
        assert result.filter_1_name == "entry_time"
        assert len(result.filter_1_values) == 5
        assert result.filter_2_name is None
        assert result.filter_2_values is None
        assert "win_rate" in result.metric_grids
        assert result.metric_grids["win_rate"].shape == (5,)

    def test_run_parameter_sweep_2d(self, sample_df):
        """Should run 2D parameter sweep (two filters)."""
        engine = ParameterSensitivityEngine(
            baseline_df=sample_df,
            column_mapping={"gain": "gain_pct"},
            active_filters=[],
        )
        config = ParameterSensitivityConfig(
            mode="sweep",
            sweep_filter_1="entry_time",
            sweep_range_1=(9.0, 12.0),
            sweep_filter_2="gap_pct",
            sweep_range_2=(2.0, 8.0),
            grid_resolution=5,
            metrics=("win_rate",),
        )

        result = engine.run_parameter_sweep(config)

        assert result.filter_2_name == "gap_pct"
        assert len(result.filter_2_values) == 5
        assert result.metric_grids["win_rate"].shape == (5, 5)


class TestParameterSensitivityWorker:
    """Tests for async worker."""

    @pytest.fixture
    def sample_df(self):
        np.random.seed(42)
        n = 50
        return pd.DataFrame({
            "gain_pct": np.random.uniform(-0.05, 0.10, n),
            "entry_time": np.random.uniform(9.0, 16.0, n),
        })

    def test_worker_is_qthread(self, sample_df):
        """Worker should be a QThread subclass."""
        config = ParameterSensitivityConfig(mode="neighborhood")
        worker = ParameterSensitivityWorker(
            config=config,
            baseline_df=sample_df,
            column_mapping={"gain": "gain_pct"},
            active_filters=[],
        )
        assert isinstance(worker, QThread)

    def test_worker_has_signals(self, sample_df):
        """Worker should have progress, completed, and error signals."""
        config = ParameterSensitivityConfig(mode="neighborhood")
        worker = ParameterSensitivityWorker(
            config=config,
            baseline_df=sample_df,
            column_mapping={"gain": "gain_pct"},
            active_filters=[],
        )
        assert hasattr(worker, "progress")
        assert hasattr(worker, "completed")
        assert hasattr(worker, "error")
