"""Unit tests for statistics calculations."""
import pytest

def test_statistics_module_imports():
    """Test that statistics module can be imported."""
    from src.core.statistics import (
        calculate_mae_before_win,
        calculate_mfe_before_loss,
        calculate_stop_loss_table,
        calculate_offset_table,
        calculate_scaling_table,
    )
    assert callable(calculate_mae_before_win)
    assert callable(calculate_mfe_before_loss)
    assert callable(calculate_stop_loss_table)
    assert callable(calculate_offset_table)
    assert callable(calculate_scaling_table)
