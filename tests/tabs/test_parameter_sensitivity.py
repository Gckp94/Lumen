"""Tests for Parameter Sensitivity tab."""

import pytest
from PyQt6.QtWidgets import QApplication

from src.core.app_state import AppState
from src.tabs.parameter_sensitivity import ParameterSensitivityTab


@pytest.fixture(scope="module")
def app():
    """Create QApplication for tests."""
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def app_state():
    """Create AppState instance."""
    return AppState()


class TestParameterSensitivityTab:
    """Tests for ParameterSensitivityTab widget."""

    def test_tab_creation(self, app, app_state):
        """Tab should create without errors."""
        tab = ParameterSensitivityTab(app_state)
        assert tab is not None

    def test_tab_has_run_button(self, app, app_state):
        """Tab should have a run analysis button."""
        tab = ParameterSensitivityTab(app_state)
        assert tab._run_btn is not None

    def test_tab_has_filter_dropdown(self, app, app_state):
        """Tab should have a filter dropdown."""
        tab = ParameterSensitivityTab(app_state)
        assert tab._filter_combo is not None

    def test_tab_has_step_spinbox(self, app, app_state):
        """Tab should have a step size spinbox."""
        tab = ParameterSensitivityTab(app_state)
        assert tab._step_spin is not None

    def test_tab_has_bound_toggle(self, app, app_state):
        """Tab should have a bound toggle container."""
        tab = ParameterSensitivityTab(app_state)
        assert tab._bound_container is not None

    def test_tab_has_results_table(self, app, app_state):
        """Tab should have a results table."""
        tab = ParameterSensitivityTab(app_state)
        assert tab._table is not None
