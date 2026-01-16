"""Tests for BreakdownTab user inputs integration."""
import pytest
from PyQt6.QtWidgets import QApplication
from unittest.mock import patch

from src.core.app_state import AppState
from src.core.models import MetricsUserInputs


@pytest.fixture(scope="module")
def app():
    """Create QApplication for tests."""
    application = QApplication.instance() or QApplication([])
    yield application


def test_breakdown_calculator_uses_user_inputs(app):
    """BreakdownCalculator should use flat_stake and starting_capital from app_state."""
    from src.tabs.breakdown import BreakdownTab

    app_state = AppState()
    app_state.metrics_user_inputs = MetricsUserInputs(
        flat_stake=5000.0,
        starting_capital=50000.0,
        fractional_kelly=25.0,
    )

    with patch("src.tabs.breakdown.BreakdownTab._setup_ui"):
        with patch("src.tabs.breakdown.BreakdownTab._connect_signals"):
            with patch("src.tabs.breakdown.BreakdownTab._initialize_from_state"):
                tab = BreakdownTab(app_state)

    assert tab._calculator._stake == 5000.0
    assert tab._calculator._start_capital == 50000.0


def test_breakdown_recalculates_on_user_inputs_change(app):
    """BreakdownTab should recalculate when user inputs change."""
    from src.tabs.breakdown import BreakdownTab

    app_state = AppState()
    app_state.metrics_user_inputs = MetricsUserInputs(
        flat_stake=5000.0,
        starting_capital=50000.0,
        fractional_kelly=25.0,
    )

    with patch("src.tabs.breakdown.BreakdownTab._setup_ui"):
        with patch("src.tabs.breakdown.BreakdownTab._connect_signals"):
            with patch("src.tabs.breakdown.BreakdownTab._initialize_from_state"):
                with patch.object(BreakdownTab, "_refresh_charts") as mock_refresh:
                    tab = BreakdownTab(app_state)

                    # Change user inputs (update app_state as the signal would)
                    new_inputs = MetricsUserInputs(
                        flat_stake=10000.0,
                        starting_capital=100000.0,
                        fractional_kelly=25.0,
                    )
                    app_state.metrics_user_inputs = new_inputs
                    tab._on_metrics_user_inputs_changed(new_inputs)

                    # Verify calculator was updated
                    assert tab._calculator._stake == 10000.0
                    assert tab._calculator._start_capital == 100000.0

                    # Verify charts were refreshed
                    mock_refresh.assert_called_once()
