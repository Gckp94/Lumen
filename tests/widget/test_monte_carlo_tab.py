"""Widget tests for Monte Carlo tab components."""

from __future__ import annotations

import numpy as np
import pytest
from PyQt6.QtCore import Qt

from PyQt6.QtWidgets import QPushButton

from src.core.app_state import AppState
from src.core.monte_carlo import MonteCarloConfig, MonteCarloResults, PositionSizingMode
from src.ui.components.hero_metric_card import (
    HeroMetricCard,
    HeroMetricsPanel,
    get_drawdown_color,
    get_probability_color,
    get_risk_color,
)
from src.ui.components.monte_carlo_config import (
    MonteCarloConfigPanel,
    ProgressRing,
    RunButton,
    SimulationTypeToggle,
)
from src.ui.components.monte_carlo_section import (
    MonteCarloMetricCard,
    MonteCarloSection,
    MonteCarloSectionsContainer,
)
from src.ui.constants import Colors


@pytest.fixture
def app_state():
    """Create a fresh AppState for each test."""
    return AppState()


@pytest.fixture
def mock_results():
    """Create mock MonteCarloResults for testing."""
    config = MonteCarloConfig(num_simulations=1000)
    return MonteCarloResults(
        config=config,
        num_trades=100,
        # Drawdown
        median_max_dd=0.15,
        p95_max_dd=0.25,
        p99_max_dd=0.35,
        max_dd_distribution=np.zeros(1000),
        # Equity
        mean_final_equity=150000.0,
        std_final_equity=25000.0,
        p5_final_equity=100000.0,
        p95_final_equity=200000.0,
        probability_of_profit=0.75,
        final_equity_distribution=np.zeros(1000),
        # CAGR
        mean_cagr=0.15,
        median_cagr=0.12,
        cagr_distribution=np.zeros(1000),
        # Risk-Adjusted
        mean_sharpe=1.5,
        mean_sortino=2.0,
        mean_calmar=1.2,
        sharpe_distribution=np.zeros(1000),
        sortino_distribution=np.zeros(1000),
        calmar_distribution=np.zeros(1000),
        # Risk of Ruin
        risk_of_ruin=0.05,
        # Streaks
        mean_max_win_streak=5.0,
        max_max_win_streak=10,
        mean_max_loss_streak=3.0,
        max_max_loss_streak=7,
        win_streak_distribution=np.zeros(1000, dtype=np.int64),
        loss_streak_distribution=np.zeros(1000, dtype=np.int64),
        # Recovery
        mean_recovery_factor=2.5,
        recovery_factor_distribution=np.zeros(1000),
        # Profit Factor
        mean_profit_factor=1.8,
        profit_factor_distribution=np.zeros(1000),
        # Drawdown Duration
        mean_avg_dd_duration=10.0,
        mean_max_dd_duration=20.0,
        max_dd_duration_distribution=np.zeros(1000, dtype=np.int64),
        # VaR
        var=-0.02,
        cvar=-0.03,
        # Equity percentiles
        equity_percentiles=np.zeros((100, 5)),
    )


class TestSimulationTypeToggle:
    """Tests for SimulationTypeToggle widget."""

    def test_default_selection_is_resample(self, qtbot):
        """Toggle defaults to resample mode."""
        toggle = SimulationTypeToggle()
        qtbot.addWidget(toggle)
        assert toggle.simulation_type() == "resample"

    def test_set_simulation_type(self, qtbot):
        """Can set simulation type programmatically."""
        toggle = SimulationTypeToggle()
        qtbot.addWidget(toggle)

        toggle.set_simulation_type("reshuffle")
        assert toggle.simulation_type() == "reshuffle"

        toggle.set_simulation_type("resample")
        assert toggle.simulation_type() == "resample"

    def test_type_changed_signal(self, qtbot):
        """Toggle emits type_changed signal when clicked."""
        toggle = SimulationTypeToggle()
        qtbot.addWidget(toggle)
        toggle.show()  # Ensure widget is visible for proper geometry

        # Click on right side (reshuffle) - use topRight offset to ensure we're in reshuffle half
        from PyQt6.QtCore import QPoint
        right_pos = QPoint(toggle.width() - 20, toggle.height() // 2)

        with qtbot.waitSignal(toggle.type_changed, timeout=1000) as blocker:
            qtbot.mouseClick(toggle, Qt.MouseButton.LeftButton, pos=right_pos)

        # Signal should have been emitted with 'reshuffle'
        assert blocker.args[0] == "reshuffle"


class TestRunButton:
    """Tests for RunButton widget."""

    def test_initial_state_is_idle(self, qtbot):
        """Button starts in idle state."""
        btn = RunButton()
        qtbot.addWidget(btn)
        assert btn._is_running is False

    def test_set_running_changes_text(self, qtbot):
        """Setting running state changes button text."""
        btn = RunButton()
        qtbot.addWidget(btn)

        btn.set_running(True)
        assert btn._text_label.text() == "CANCEL"

        btn.set_running(False)
        assert btn._text_label.text() == "RUN SIM"

    def test_clicked_signal_in_idle_state(self, qtbot):
        """Click in idle state emits clicked signal."""
        btn = RunButton()
        qtbot.addWidget(btn)

        with qtbot.waitSignal(btn.clicked, timeout=1000):
            qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)

    def test_cancel_clicked_signal_in_running_state(self, qtbot):
        """Click in running state emits cancel_clicked signal."""
        btn = RunButton()
        qtbot.addWidget(btn)
        btn.set_running(True)

        with qtbot.waitSignal(btn.cancel_clicked, timeout=1000):
            qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)

    def test_disabled_button_does_not_emit(self, qtbot):
        """Disabled button doesn't emit signals."""
        btn = RunButton()
        qtbot.addWidget(btn)
        btn.set_enabled(False)

        clicked = False

        def on_click():
            nonlocal clicked
            clicked = True

        btn.clicked.connect(on_click)
        qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
        assert clicked is False


class TestProgressRing:
    """Tests for ProgressRing widget."""

    def test_initial_progress_is_zero(self, qtbot):
        """Progress ring starts at zero."""
        ring = ProgressRing()
        qtbot.addWidget(ring)
        assert ring._progress == 0.0

    def test_set_progress(self, qtbot):
        """Can set progress value."""
        ring = ProgressRing()
        qtbot.addWidget(ring)

        ring.set_progress(0.5)
        assert ring._progress == 0.5

    def test_progress_clamped_to_valid_range(self, qtbot):
        """Progress is clamped to 0.0-1.0."""
        ring = ProgressRing()
        qtbot.addWidget(ring)

        ring.set_progress(1.5)
        assert ring._progress == 1.0

        ring.set_progress(-0.5)
        assert ring._progress == 0.0


class TestMonteCarloConfigPanel:
    """Tests for MonteCarloConfigPanel widget."""

    def test_default_config_values(self, qtbot):
        """Config panel has expected default values."""
        panel = MonteCarloConfigPanel()
        qtbot.addWidget(panel)

        config = panel.get_config()
        assert config.num_simulations == 5000
        assert config.initial_capital == 100000
        assert config.ruin_threshold_pct == 50
        assert config.var_confidence_pct == 5
        assert config.simulation_type == "resample"

    def test_config_changed_signal_on_spinbox_change(self, qtbot):
        """Changing spinbox emits config_changed signal."""
        panel = MonteCarloConfigPanel()
        qtbot.addWidget(panel)

        with qtbot.waitSignal(panel.config_changed, timeout=1000):
            panel._num_sims_spin.setValue(1000)

    def test_run_requested_signal(self, qtbot):
        """Run button click emits run_requested signal."""
        panel = MonteCarloConfigPanel()
        qtbot.addWidget(panel)

        with qtbot.waitSignal(panel.run_requested, timeout=1000):
            qtbot.mouseClick(panel._run_btn, Qt.MouseButton.LeftButton)

    def test_set_config_updates_widgets(self, qtbot):
        """set_config updates all widget values."""
        panel = MonteCarloConfigPanel()
        qtbot.addWidget(panel)

        new_config = MonteCarloConfig(
            num_simulations=2000,
            initial_capital=50000,
            ruin_threshold_pct=30,
            var_confidence_pct=10,
            simulation_type="reshuffle",
        )
        panel.set_config(new_config)

        result = panel.get_config()
        assert result.num_simulations == 2000
        assert result.initial_capital == 50000
        assert result.ruin_threshold_pct == 30
        assert result.var_confidence_pct == 10
        assert result.simulation_type == "reshuffle"

    def test_custom_position_button_exists(self, qtbot):
        """Test that Custom % button exists in position sizing section."""
        panel = MonteCarloConfigPanel()
        qtbot.addWidget(panel)

        # Find by text
        buttons = panel.findChildren(QPushButton)
        custom_btns = [b for b in buttons if b.text() == "Custom %"]
        assert len(custom_btns) == 1

    def test_custom_spinner_visibility_toggle(self, qtbot):
        """Test that custom percentage spinner shows/hides based on mode."""
        panel = MonteCarloConfigPanel()
        qtbot.addWidget(panel)
        panel.show()  # Must show panel for isVisible() to work correctly

        # Initially hidden (Kelly is default)
        assert not panel._custom_pct_spin.isVisible()

        # Select custom mode
        panel._on_position_mode_changed(PositionSizingMode.COMPOUNDED_CUSTOM)
        assert panel._custom_pct_spin.isVisible()

        # Select Kelly mode
        panel._on_position_mode_changed(PositionSizingMode.COMPOUNDED_KELLY)
        assert not panel._custom_pct_spin.isVisible()

        # Select flat stake mode
        panel._on_position_mode_changed(PositionSizingMode.FLAT_STAKE)
        assert not panel._custom_pct_spin.isVisible()

    def test_get_config_includes_custom_position_pct(self, qtbot):
        """Test that get_config returns custom_position_pct value."""
        panel = MonteCarloConfigPanel()
        qtbot.addWidget(panel)

        panel._on_position_mode_changed(PositionSizingMode.COMPOUNDED_CUSTOM)
        panel._custom_pct_spin.setValue(15.5)

        config = panel.get_config()

        assert config.position_sizing_mode == PositionSizingMode.COMPOUNDED_CUSTOM
        assert config.custom_position_pct == 15.5


class TestHeroMetricCard:
    """Tests for HeroMetricCard widget."""

    def test_initial_state_shows_placeholder(self, qtbot):
        """Card shows em dash initially."""
        card = HeroMetricCard("Test Metric")
        qtbot.addWidget(card)
        assert "\u2014" in card._value_widget.text()

    def test_update_value_displays_formatted_value(self, qtbot):
        """update_value formats and displays the value."""
        card = HeroMetricCard("Test Metric")
        qtbot.addWidget(card)

        card.update_value(75.5, format_str="{:.1f}%")
        assert "75.5%" in card._value_widget.text()

    def test_update_value_with_color(self, qtbot):
        """update_value applies semantic color."""
        card = HeroMetricCard("Test Metric")
        qtbot.addWidget(card)

        card.update_value(75.5, color=Colors.SIGNAL_CYAN)
        assert card._accent_color == Colors.SIGNAL_CYAN

    def test_clear_resets_to_placeholder(self, qtbot):
        """clear() resets the display."""
        card = HeroMetricCard("Test Metric")
        qtbot.addWidget(card)

        card.update_value(75.5)
        card.clear()
        assert "\u2014" in card._value_widget.text()


class TestHeroMetricsPanel:
    """Tests for HeroMetricsPanel widget."""

    def test_has_three_cards(self, qtbot):
        """Panel contains three metric cards."""
        panel = HeroMetricsPanel()
        qtbot.addWidget(panel)

        assert panel._prob_profit_card is not None
        assert panel._risk_ruin_card is not None
        assert panel._median_dd_card is not None

    def test_update_from_results(self, qtbot, mock_results):
        """update_from_results populates all cards."""
        panel = HeroMetricsPanel()
        qtbot.addWidget(panel)

        panel.update_from_results(mock_results)

        # Values should be populated (not placeholders)
        assert "\u2014" not in panel._prob_profit_card._value_widget.text()
        assert "\u2014" not in panel._risk_ruin_card._value_widget.text()
        assert "\u2014" not in panel._median_dd_card._value_widget.text()


class TestSemanticColoring:
    """Tests for semantic color functions."""

    def test_probability_color_high(self):
        """High probability (>60%) returns cyan."""
        assert get_probability_color(75) == Colors.SIGNAL_CYAN

    def test_probability_color_medium(self):
        """Medium probability (40-60%) returns amber."""
        assert get_probability_color(50) == Colors.SIGNAL_AMBER

    def test_probability_color_low(self):
        """Low probability (<40%) returns coral."""
        assert get_probability_color(30) == Colors.SIGNAL_CORAL

    def test_risk_color_low(self):
        """Low risk (<5%) returns cyan."""
        assert get_risk_color(3) == Colors.SIGNAL_CYAN

    def test_risk_color_medium(self):
        """Medium risk (5-15%) returns amber."""
        assert get_risk_color(10) == Colors.SIGNAL_AMBER

    def test_risk_color_high(self):
        """High risk (>15%) returns coral."""
        assert get_risk_color(20) == Colors.SIGNAL_CORAL

    def test_drawdown_color_low(self):
        """Low drawdown (<20%) returns cyan."""
        assert get_drawdown_color(0.15) == Colors.SIGNAL_CYAN

    def test_drawdown_color_medium(self):
        """Medium drawdown (20-35%) returns amber."""
        assert get_drawdown_color(0.25) == Colors.SIGNAL_AMBER

    def test_drawdown_color_high(self):
        """High drawdown (>35%) returns coral."""
        assert get_drawdown_color(0.40) == Colors.SIGNAL_CORAL


class TestMonteCarloMetricCard:
    """Tests for MonteCarloMetricCard widget."""

    def test_initial_state(self, qtbot):
        """Card shows placeholder initially."""
        card = MonteCarloMetricCard("Test")
        qtbot.addWidget(card)
        assert "\u2014" in card._value_widget.text()

    def test_update_value(self, qtbot):
        """update_value displays formatted value."""
        card = MonteCarloMetricCard("Test")
        qtbot.addWidget(card)

        card.update_value(123.45, "{:.1f}")
        assert "123.5" in card._value_widget.text()

    def test_update_value_with_hint(self, qtbot):
        """update_value can update hint text."""
        card = MonteCarloMetricCard("Test", hint="original")
        qtbot.addWidget(card)

        card.update_value(100, "{:.0f}", hint="updated")
        assert card._hint_widget.text() == "updated"


class TestMonteCarloSection:
    """Tests for MonteCarloSection widget."""

    def test_add_and_get_card(self, qtbot):
        """Can add cards and retrieve them by key."""
        section = MonteCarloSection("Test Section")
        qtbot.addWidget(section)

        card = section.add_card("test_key", "Test Label", row=0, col=0)
        assert section.get_card("test_key") is card

    def test_update_card(self, qtbot):
        """update_card updates the correct card."""
        section = MonteCarloSection("Test Section")
        qtbot.addWidget(section)

        section.add_card("metric1", "Metric 1", row=0, col=0)
        section.update_card("metric1", 42.5, "{:.1f}")

        card = section.get_card("metric1")
        assert "42.5" in card._value_widget.text()

    def test_clear_all(self, qtbot):
        """clear_all resets all cards."""
        section = MonteCarloSection("Test Section")
        qtbot.addWidget(section)

        section.add_card("m1", "M1", row=0, col=0)
        section.add_card("m2", "M2", row=0, col=1)
        section.update_card("m1", 100)
        section.update_card("m2", 200)

        section.clear_all()

        assert "\u2014" in section.get_card("m1")._value_widget.text()
        assert "\u2014" in section.get_card("m2")._value_widget.text()


class TestMonteCarloSectionsContainer:
    """Tests for MonteCarloSectionsContainer widget."""

    def test_has_all_sections(self, qtbot):
        """Container has all six sections."""
        container = MonteCarloSectionsContainer()
        qtbot.addWidget(container)

        assert container._drawdown_section is not None
        assert container._equity_section is not None
        assert container._growth_section is not None
        assert container._risk_adjusted_section is not None
        assert container._risk_section is not None
        assert container._streak_section is not None

    def test_update_from_results(self, qtbot, mock_results):
        """update_from_results populates all sections."""
        container = MonteCarloSectionsContainer()
        qtbot.addWidget(container)

        container.update_from_results(mock_results)

        # Check a card from each section is populated
        drawdown_card = container._drawdown_section.get_card("median_dd")
        assert drawdown_card is not None
        assert "\u2014" not in drawdown_card._value_widget.text()
