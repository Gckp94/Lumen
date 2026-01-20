"""Tests for Parameter Sensitivity tab UI logic."""

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd

from src.core.parameter_sensitivity import ParameterSensitivityConfig


class TestSweepConfigConstruction:
    """Test sweep config construction from UI values."""

    def test_sweep_config_with_filter_1_only(self):
        """Sweep config should accept filter_1 without filter_2."""
        config = ParameterSensitivityConfig(
            mode="sweep",
            primary_metric="expected_value",
            grid_resolution=10,
            sweep_filter_1="gap_percent",
            sweep_range_1=(0.5, 2.0),
        )

        assert config.sweep_filter_1 == "gap_percent"
        assert config.sweep_range_1 == (0.5, 2.0)
        assert config.sweep_filter_2 is None
        assert config.sweep_range_2 is None

    def test_sweep_config_with_2d_filters(self):
        """Sweep config should accept both filter_1 and filter_2."""
        config = ParameterSensitivityConfig(
            mode="sweep",
            primary_metric="win_rate",
            grid_resolution=15,
            sweep_filter_1="gap_percent",
            sweep_range_1=(0.5, 2.0),
            sweep_filter_2="volume",
            sweep_range_2=(1000, 5000),
        )

        assert config.sweep_filter_1 == "gap_percent"
        assert config.sweep_range_1 == (0.5, 2.0)
        assert config.sweep_filter_2 == "volume"
        assert config.sweep_range_2 == (1000, 5000)

    def test_neighborhood_config_ignores_sweep_params(self):
        """Neighborhood mode should work without sweep parameters."""
        config = ParameterSensitivityConfig(
            mode="neighborhood",
            primary_metric="profit_factor",
        )

        assert config.mode == "neighborhood"
        assert config.sweep_filter_1 is None
