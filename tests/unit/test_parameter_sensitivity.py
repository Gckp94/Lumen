# tests/unit/test_parameter_sensitivity.py
"""Tests for parameter sensitivity engine."""

import pytest
import numpy as np
import pandas as pd

from src.core.parameter_sensitivity import (
    ParameterSensitivityConfig,
    NeighborhoodResult,
    SweepResult,
    ParameterSensitivityEngine,
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
