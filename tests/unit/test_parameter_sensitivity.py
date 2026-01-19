# tests/unit/test_parameter_sensitivity.py
"""Tests for parameter sensitivity engine."""

import pytest
import numpy as np
import pandas as pd

from src.core.parameter_sensitivity import (
    ParameterSensitivityConfig,
    NeighborhoodResult,
    SweepResult,
)


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
